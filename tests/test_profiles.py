from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from inspector.core.profiles import ProfileError, load_profile


ROOT = Path(__file__).resolve().parents[1]


class ProfileTests(unittest.TestCase):
    def test_template_and_historical_profile_load(self):
        self.assertEqual(load_profile(ROOT / "profiles" / "_template.json")["id"], "template")
        self.assertEqual(load_profile(ROOT / "profiles" / "historical-case.json")["id"], "historical-case")

    def test_inline_credential_and_non_https_are_rejected(self):
        profile = json.loads((ROOT / "profiles" / "_template.json").read_text(encoding="utf-8"))
        profile["targets"]["chat"]["auth"]["value"] = "secret"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaises(ProfileError):
                load_profile(path)
        profile = json.loads((ROOT / "profiles" / "_template.json").read_text(encoding="utf-8"))
        profile["targets"]["chat"]["url_template"] = "http://127.0.0.1/test"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text(json.dumps(profile), encoding="utf-8")
            with self.assertRaises(ProfileError):
                load_profile(path)


if __name__ == "__main__":
    unittest.main()
