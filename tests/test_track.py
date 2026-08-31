from __future__ import annotations

import unittest

from inspector.core.classification import classify_response
from inspector.track import compare_golden, track_request


GOLDEN = {"trace_id": "g", "observed": {"schema": "inspector.result/v1", "status": "PASS", "classification": "unknown", "model_effective": "requested-model", "stream_complete": True, "latency_bucket": "lt_100ms"}}
REQUEST = {"body": {"mode": "inline", "encoding": "json", "value": {"model": "requested-model"}}, "meta": {"model_requested": "requested-model"}}


class TrackTests(unittest.TestCase):
    def test_pass_and_minimal_fail(self):
        current = {"schema": "inspector.result/v1", "status": "PASS", "classification": "unknown", "trace_id": "c", "response": {"meta": {"model_effective": "requested-model", "stream_complete": True, "latency_ms": 10}}}
        self.assertEqual(compare_golden(GOLDEN, current)["status"], "PASS")
        drifted = dict(current)
        drifted["classification"] = "model_downgrade"
        drifted["response"] = {"meta": {"model_effective": "fallback-model", "stream_complete": True, "latency_ms": 10}}
        report = compare_golden(GOLDEN, drifted)
        self.assertEqual(report["status"], "FAIL")
        self.assertEqual({item["field"] for item in report["findings"]}, {"classification", "model_effective"})

    def test_latency_only_change_is_warning(self):
        current = {"schema": "inspector.result/v1", "status": "PASS", "classification": "unknown", "trace_id": "c", "response": {"meta": {"model_effective": "requested-model", "stream_complete": True, "latency_ms": 600}}}
        report = compare_golden(GOLDEN, current)
        self.assertEqual(report["status"], "WARN")

    def test_tool_error_and_not_run_are_not_pass(self):
        self.assertEqual(compare_golden(GOLDEN, {"status": "TOOL_ERROR", "trace_id": "x"})["status"], "TOOL_ERROR")
        self.assertEqual(compare_golden(GOLDEN, {"status": "NOT_RUN", "trace_id": "x"})["status"], "NOT_RUN")

    def test_real_mock_track(self):
        report = track_request(REQUEST, {"trace_id": "g", "observed": {"schema": "inspector.result/v1", "status": "PASS", "classification": "unknown", "model_effective": "requested-model", "stream_complete": True, "latency_bucket": "lt_100ms"}})
        self.assertEqual(report["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
