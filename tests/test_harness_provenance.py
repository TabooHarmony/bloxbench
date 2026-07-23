import hashlib
import tempfile
import unittest
from pathlib import Path

from harness import (
    build_source_provenance,
    load_style_reference_context,
    parse_eval,
    sha256_file,
)
from scripts.windev.repair_core_qualification import REPAIR_SNIPPETS, discover_repair_core_evals


class ProvenanceTests(unittest.TestCase):
    def test_sha256_file_matches_fixture_bytes(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "fixture.bin"
            data = b"repair-core fixture\x00"
            path.write_bytes(data)
            self.assertEqual(sha256_file(path), hashlib.sha256(data).hexdigest())

    def test_provenance_has_relative_eval_hash(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            harness_path = root / "harness.py"
            eval_path = root / "Evals" / "example.lua"
            harness_path.write_text("harness", encoding="utf-8")
            eval_path.parent.mkdir()
            eval_path.write_text("eval", encoding="utf-8")
            provenance = build_source_provenance(root, harness_path, [eval_path])
            self.assertEqual(set(provenance["evals"]), {"Evals/example.lua"})
            self.assertEqual(len(provenance["evals"]["Evals/example.lua"]), 64)

    def test_provenance_has_harness_hash(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            harness_path = root / "harness.py"
            harness_path.write_text("harness", encoding="utf-8")
            provenance = build_source_provenance(root, harness_path, [])
            self.assertEqual(len(provenance["harness_sha256"]), 64)

    def test_non_git_directory_returns_null_git_fields(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            harness_path = root / "harness.py"
            harness_path.write_text("harness", encoding="utf-8")
            provenance = build_source_provenance(root, harness_path, [])
            self.assertIsNone(provenance["git_commit"])
            self.assertIsNone(provenance["git_dirty"])

    def test_repair_core_has_exactly_three_evals(self):
        paths = discover_repair_core_evals()
        self.assertEqual(len(paths), 3)
        self.assertEqual({path.stem for path in paths}, set(REPAIR_SNIPPETS))

    def test_each_scenario_has_one_repair_snippet(self):
        paths = discover_repair_core_evals()
        self.assertEqual({path.stem for path in paths}, set(REPAIR_SNIPPETS))
        self.assertEqual(len(REPAIR_SNIPPETS), 3)
        self.assertTrue(all(REPAIR_SNIPPETS[path.stem].strip() for path in paths))

    def test_style_reference_context_is_observation_labeled(self):
        paths = [
            "Reference/VB_UI_002_daily_reward_ref.lua",
            "Reference/VB_UI_003_trade_window_ref.lua",
        ]
        profile, prompt = load_style_reference_context(paths)
        self.assertEqual(len(profile["sources"]), 2)
        self.assertIn("local observations", prompt)
        self.assertIn("do not copy blindly", prompt)

    def test_repair_core_evals_parse(self):
        for path in discover_repair_core_evals():
            parsed = parse_eval(str(path))
            self.assertEqual(parsed.scenario_name, path.stem)
            self.assertEqual(parsed.place, "baseplate.rbxl")
            self.assertTrue(parsed.prompt_text)

    def test_repair_snippets_have_no_intervention_calls(self):
        forbidden = ("model", "api", "http", "judge", "spatial", "helper", "primitive", "verifier")
        for snippet in REPAIR_SNIPPETS.values():
            lowered = snippet.lower()
            for term in forbidden:
                self.assertNotIn(term, lowered)


if __name__ == "__main__":
    unittest.main()
