import hashlib
import tempfile
import unittest
from pathlib import Path

from harness import (
    build_source_provenance,
    parse_eval,
    sha256_file,
)


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


class FixtureParseTests(unittest.TestCase):
    """Verify all active eval fixtures parse correctly."""

    EVALS_DIR = Path(__file__).parent.parent / "Evals"

    def test_all_fixtures_parse(self):
        lua_files = sorted(self.EVALS_DIR.rglob("*.lua"))
        # Exclude evalutils type stubs
        lua_files = [f for f in lua_files if "evalutils" not in str(f)]
        self.assertGreater(len(lua_files), 0, "No eval fixtures found")
        for path in lua_files:
            parsed = parse_eval(str(path))
            self.assertTrue(parsed.scenario_name, f"Empty scenario_name in {path.name}")
            self.assertTrue(parsed.prompt_text, f"Empty prompt in {path.name}")
            self.assertEqual(parsed.place, "baseplate.rbxl", f"Wrong place in {path.name}")

    def test_gameplay_fixture_exists(self):
        gameplay = list((self.EVALS_DIR / "Gameplay").glob("*.lua"))
        self.assertGreater(len(gameplay), 0, "No Gameplay fixtures found")

    def test_building_fixtures_exist(self):
        building = list((self.EVALS_DIR / "Building").glob("*.lua"))
        self.assertGreater(len(building), 0, "No Building fixtures found")

    def test_ui_fixtures_exist(self):
        ui = list((self.EVALS_DIR / "UI").glob("*.lua"))
        self.assertGreater(len(ui), 0, "No UI fixtures found")


if __name__ == "__main__":
    unittest.main()
