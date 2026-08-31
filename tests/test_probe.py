from __future__ import annotations

import unittest
from pathlib import Path

from inspector.core.schema import load_schema, validate
from inspector.probe import ProbeCache, ProbePolicyError, STATES, ensure_live_allowed, probe_mock

ROOT = Path(__file__).resolve().parents[1]


class ProbeTests(unittest.TestCase):
    def test_all_mock_states_have_explicit_result(self):
        for state in STATES:
            with self.subTest(state=state):
                result = probe_mock(state)
                self.assertIn(result.status, {"PASS", "FAIL", "TOOL_ERROR"})
                validate(result.as_dict(), load_schema(ROOT / "schemas" / "result-v1.json"))
                self.assertGreaterEqual(result.exit_code, 0)
                if state != "ok":
                    self.assertNotEqual(result.exit_code, 0)

    def test_cache_is_bounded_and_reuses_result(self):
        cache = ProbeCache(max_entries=1)
        first = probe_mock("ok", cache=cache)
        second = probe_mock("ok", cache=cache)
        self.assertEqual(first, second)
        probe_mock("banned", cache=cache)
        self.assertIsNone(cache.get("mock:ok:mock"))

    def test_live_requires_confirmation_and_is_not_silent(self):
        with self.assertRaises(ProbePolicyError):
            ensure_live_allowed(live=True, confirm_live=False, host="example.invalid", allowlist=["example.invalid"])
        with self.assertRaises(ProbePolicyError):
            ensure_live_allowed(live=True, confirm_live=True, host="example.invalid", allowlist=["example.invalid"])


if __name__ == "__main__":
    unittest.main()
