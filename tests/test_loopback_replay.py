from __future__ import annotations

import unittest

from inspector.adapters.loopback import LoopbackMockServer
from inspector.replay import replay_request, target_from_uri


class LoopbackReplayTests(unittest.TestCase):
    def test_local_http_target_is_allowed(self):
        request = {"body": {"mode": "inline", "encoding": "json", "value": {"model": "requested-model"}}, "meta": {"model_requested": "requested-model"}}
        with LoopbackMockServer() as server:
            result = replay_request(request, target=target_from_uri(server.url), expectations={"status": 200})
            self.assertEqual(result["status"], "PASS")

    def test_non_loopback_http_is_rejected(self):
        with self.assertRaises(ValueError):
            target_from_uri("http://example.invalid/test")


if __name__ == "__main__":
    unittest.main()
