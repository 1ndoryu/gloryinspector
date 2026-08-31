from __future__ import annotations

import json
import tempfile
import unittest
import urllib.request
from pathlib import Path

from inspector.adapters.loopback import LoopbackMockServer
from inspector.capture import import_capture
from inspector.core.records import read_jsonl


class CaptureTests(unittest.TestCase):
    def test_har_import_redacts_before_persisting(self):
        document = {
            "log": {
                "entries": [{
                    "startedDateTime": "2026-08-10T00:00:00Z",
                    "request": {
                        "method": "POST",
                        "url": "https://example.invalid/test",
                        "headers": [{"name": "Authorization", "value": "Bearer abcdefghijklmnop"}],
                        "postData": {"text": json.dumps({"email": "person@example.invalid"})},
                    },
                    "response": {"status": 200, "headers": [], "content": {"text": json.dumps({"ok": True})}},
                }]
            }
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "capture.har"
            source.write_text(json.dumps(document), encoding="utf-8")
            manifest = import_capture(source, root / "out")
            records = read_jsonl(root / "out" / "import-session.jsonl")
            self.assertEqual(manifest["record_count"], 2)
            self.assertNotIn("person@example.invalid", json.dumps(records))
            self.assertNotIn("Bearer abcdefghijklmnop", json.dumps(records))

    def test_record_list_import_redacts_before_persisting(self):
        record = {
            "schema": "inspector.record/v1", "record_id": "r-1", "session_id": "s-1", "correlation_id": "c-1", "sequence": 1,
            "ts": "2026-08-10T00:00:00Z", "kind": "request", "direction": "outbound", "url": "https://example.invalid/test",
            "method": "POST", "headers": {"Authorization": "Bearer abcdefghijklmnop"}, "query": {},
            "body": {"mode": "inline", "encoding": "json", "value": {"email": "person@example.invalid"}}, "meta": {}
        }
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "records.json"
            source.write_text(json.dumps([record]), encoding="utf-8")
            import_capture(source, root / "out", session_id="s-1")
            records = read_jsonl(root / "out" / "s-1.jsonl")
            self.assertNotIn("Bearer abcdefghijklmnop", json.dumps(records))
            self.assertNotIn("person@example.invalid", json.dumps(records))

    def test_loopback_binds_only_to_127(self):
        with LoopbackMockServer() as server:
            self.assertTrue(server.url.startswith("http://127.0.0.1:"))
            request = urllib.request.Request(server.url, data=b'{"model":"requested-model"}', method="POST", headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=2) as response:
                self.assertEqual(response.status, 200)
            self.assertEqual(len(server.captured), 1)
            self.assertEqual(server.capabilities["websockets"], False)


if __name__ == "__main__":
    unittest.main()
