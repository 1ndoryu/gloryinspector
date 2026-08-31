from __future__ import annotations

import json
import unittest
from pathlib import Path

from inspector.core.mutations import MutationError, MutationSpec
from inspector.diff import run_diff


ROOT = Path(__file__).resolve().parents[1]


class DiffTests(unittest.TestCase):
    def test_historical_case_has_stable_order_and_three_branches(self):
        case = json.loads((ROOT / "fixtures" / "historical-case.json").read_text(encoding="utf-8"))
        matrix = run_diff(case["base"], MutationSpec.from_dict(case["mutation"]))
        self.assertEqual([item["variant_index"] for item in matrix], [0, 1, 2])
        self.assertEqual([item["classification"] for item in matrix], ["foreign_toolset", "foreign_toolset", "unknown"])
        self.assertTrue(all(item["variable"] == "tool_signature" for item in matrix))

    def test_multiple_variables_are_rejected(self):
        with self.assertRaises(MutationError):
            MutationSpec.from_dict({"variable": "x", "path": "$.x", "variants": [1], "second": "bad"})

    def test_wildcard_and_budget_are_rejected(self):
        with self.assertRaises(MutationError):
            MutationSpec.from_dict({"variable": "x", "path": "$.x[*]", "variants": [1]})
        with self.assertRaises(MutationError):
            MutationSpec.from_dict({"variable": "x", "path": "$.x", "variants": list(range(33))})


if __name__ == "__main__":
    unittest.main()
