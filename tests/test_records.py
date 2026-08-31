from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from inspector.adapters.mock import MockTarget
from inspector.core.records import RecordError, SessionWriter, body_descriptor, canonical_json_bytes, read_jsonl, validate_record


REQUEST = {
    "schema": "inspector.record/v1", "record_id": "r-1", "session_id": "s-1", "correlation_id": "c-1",
    "sequence": 1, "ts": "2026-08-10T00:00:00Z", "kind": "request", "direction": "outbound",
    "url": "https://example.invalid/test", "method": "POST", "headers": {}, "query": {},
    "body": {"mode": "inline", "encoding": "json", "value": {"model": "m"}}, "meta": {}
}

RESPONSE = {
    "schema": "inspector.record/v1", "record_id": "r-2", "session_id": "s-1", "correlation_id": "c-1",
    "sequence": 2, "ts": "2026-08-10T00:00:01Z", "kind": "response", "direction": "inbound",
    "url": "https://example.invalid/test", "status": 200, "headers": {},
    "body": {"mode": "inline", "encoding": "json", "value": {"ok": True}}, "meta": {}
}


class RecordTests(unittest.TestCase):
    def test_canonical_json_is_deterministic(self):
        self.assertEqual(canonical_json_bytes({"b": 1, "a": 2}), canonical_json_bytes({"a": 2, "b": 1}))

    def test_large_body_uses_hashed_blob(self):
        with tempfile.TemporaryDirectory() as directory:
            descriptor, digest = body_descriptor({"payload": "x" * (2 * 1024 * 1024)}, Path(directory))
            self.assertEqual(descriptor["mode"], "blob")
            self.assertEqual(descriptor["sha256"], digest)
            self.assertTrue((Path(directory) / descriptor["path"]).exists())

    def test_session_round_trip_and_correlation(self):
        with tempfile.TemporaryDirectory() as directory:
            writer = SessionWriter(Path(directory), "s-1")
            writer.append(REQUEST)
            writer.append(RESPONSE)
            manifest = writer.close()
            self.assertEqual(manifest["record_count"], 2)
            self.assertEqual(read_jsonl(Path(directory) / "s-1.jsonl"), [REQUEST, RESPONSE])

    def test_same_input_produces_same_jsonl_and_manifest_hash(self):
        with tempfile.TemporaryDirectory() as first_dir, tempfile.TemporaryDirectory() as second_dir:
            first = SessionWriter(Path(first_dir), "s-1")
            second = SessionWriter(Path(second_dir), "s-1")
            for writer in (first, second):
                writer.append(REQUEST)
                writer.append(RESPONSE)
                writer.close()
            self.assertEqual((Path(first_dir) / "s-1.jsonl").read_bytes(), (Path(second_dir) / "s-1.jsonl").read_bytes())
            self.assertEqual(json.loads((Path(first_dir) / "s-1.manifest.json").read_text())["records_sha256"], json.loads((Path(second_dir) / "s-1.manifest.json").read_text())["records_sha256"])

    def test_blob_path_traversal_is_rejected(self):
        invalid = copy.deepcopy(REQUEST)
        invalid["body"] = {"mode": "blob", "path": "../secret.blob", "sha256": "sha256:" + "0" * 64}
        with self.assertRaises(RecordError):
            validate_record(invalid)

    def test_response_without_request_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            writer = SessionWriter(Path(directory), "s-1")
            with self.assertRaises(RecordError):
                writer.append(RESPONSE)

    def test_mock_is_deterministic_and_network_free(self):
        first = MockTarget().handle(REQUEST)
        second = MockTarget().handle(REQUEST)
        self.assertEqual(first, second)
        self.assertEqual(first["status"], 200)


if __name__ == "__main__":
    unittest.main()
