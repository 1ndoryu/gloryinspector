from __future__ import annotations

import unittest

from inspector.adapters.mock import MockScenario, MockTarget
from inspector.core.classification import classify_response
from inspector.replay import replay_request


REQUEST = {
    "schema": "inspector.record/v1", "record_id": "r-1", "session_id": "s-1", "correlation_id": "c-1",
    "sequence": 1, "ts": "2026-08-10T00:00:00Z", "kind": "request", "direction": "outbound",
    "url": "https://example.invalid/test", "method": "POST", "headers": {}, "query": {},
    "body": {"mode": "inline", "encoding": "json", "value": {"model": "requested"}},
    "meta": {"model_requested": "requested"}
}


class ReplayTests(unittest.TestCase):
    def test_200_downgrade_fails_identity_assertion(self):
        result = replay_request(REQUEST, target=MockTarget(MockScenario(model_effective="fallback-model")), expectations={"downgrade_is_failure": True})
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["classification"], "model_downgrade")

    def test_foreign_toolset_precedes_rate_limit(self):
        request = dict(REQUEST)
        request["body"] = {"mode": "inline", "encoding": "json", "value": {"model": "requested", "tools": [{"name": "x"}]}}
        result = replay_request(request)
        self.assertEqual(result["classification"], "foreign_toolset")
        self.assertEqual(result["response"]["status"], 429)

    def test_truncated_stream_is_typed(self):
        response = MockTarget(MockScenario(stream_truncated=True)).handle(REQUEST)
        self.assertEqual(classify_response(response).code, "stream_truncated")

    def test_timeout_is_tool_error_and_not_pass(self):
        result = replay_request(REQUEST, target=MockTarget(MockScenario(latency_ms=100)), timeout_ms=1)
        self.assertEqual(result["status"], "TOOL_ERROR")
        self.assertNotEqual(result["status"], "PASS")


if __name__ == "__main__":
    unittest.main()
