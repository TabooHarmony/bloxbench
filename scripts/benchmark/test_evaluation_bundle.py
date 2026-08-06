from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "evaluation_bundle_under_test", HERE / "evaluation_bundle.py"
)
assert SPEC and SPEC.loader
EB = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EB)


class GenerationManifestLookupTests(unittest.TestCase):
    def test_top_level_usage_is_reported_for_direct_generation_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            generation = Path(tmp)
            (generation / "manifest.json").write_text(
                json.dumps(
                    {
                        "schema": "bloxbench-generation-v1",
                        "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
                        "elapsed_seconds": 1.25,
                    }
                )
            )
            summary = EB.summarize_generation(generation)
            self.assertTrue(summary["usage_available"])
            self.assertEqual(summary["usage"]["input_tokens"], 10)
            self.assertEqual(summary["usage"]["output_tokens"], 5)
            self.assertEqual(summary["rounds"], 1)

    def test_repair_lineage_is_summarized_and_copied_from_arm_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            arm = Path(tmp) / "arm"
            generation = arm / "generation"
            repair = arm / "repair"
            generation.mkdir(parents=True)
            repair.mkdir()
            (generation / "manifest.json").write_text(
                json.dumps({"schema": "bloxbench-generation-v1", "usage": {"totalTokens": 3}})
            )
            (generation / "prompt.txt").write_text("prompt")
            (generation / "system_prompt.txt").write_text("system prompt")
            (repair / "manifest.json").write_text(
                json.dumps(
                    {
                        "schema": "bloxbench-repair-v1",
                        "original_source_sha256": "original-sha",
                        "error_text": "runtime detail",
                    }
                )
            )
            summary = EB.summarize_generation(arm)
            self.assertTrue(summary["repair"]["is_repaired"])
            self.assertEqual(summary["repair"]["original_source_sha256"], "original-sha")
            destination = Path(tmp) / "bundle"
            copied = EB.copy_generation_bundle(arm, destination)
            self.assertTrue((destination / "manifest.json").is_file())
            self.assertTrue((destination / "system_prompt.txt").is_file())
            self.assertTrue((destination / "repair" / "manifest.json").is_file())
            self.assertTrue(any(item["name"] == "repair/manifest.json" for item in copied["copied_files"]))

    def test_arm_root_direct_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            arm = Path(tmp)
            (arm / "manifest.json").write_text(json.dumps({"schema": "bloxbench-generation-v1"}))
            path, manifest = EB._generation_manifest(arm)
            self.assertIsNotNone(path)
            self.assertEqual(manifest["schema"], "bloxbench-generation-v1")

    def test_repaired_arm_nested_generation_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            arm = Path(tmp)
            gen = arm / "generation"
            gen.mkdir()
            (gen / "manifest.json").write_text(json.dumps({"is_model_evaluation": True}))
            path, manifest = EB._generation_manifest(arm)
            self.assertIsNotNone(path)
            self.assertTrue(manifest["is_model_evaluation"])
            self.assertEqual(path, gen / "manifest.json")

    def test_nested_dir_passed_directly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            arm = Path(tmp)
            gen = arm / "generation"
            gen.mkdir()
            (gen / "manifest.json").write_text(json.dumps({"is_model_evaluation": True}))
            path, manifest = EB._generation_manifest(gen)
            self.assertIsNotNone(path)
            self.assertTrue(manifest["is_model_evaluation"])

    def test_missing_returns_none(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path, manifest = EB._generation_manifest(Path(tmp))
            self.assertIsNone(path)
            self.assertEqual(manifest, {})


if __name__ == "__main__":
    unittest.main()
