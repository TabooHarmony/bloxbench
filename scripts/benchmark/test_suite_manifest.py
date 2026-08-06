from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.benchmark.suite_manifest import build_suite_manifest, suite_reference, validate_suite_manifest


ROOT = Path(__file__).resolve().parents[2]


class SuiteManifestTests(unittest.TestCase):
    def test_manifest_is_deterministic_and_contains_task_identity(self) -> None:
        first = build_suite_manifest(ROOT / "Evals", "v1", "1.0", repo_root=ROOT, expected_count=25)
        second = build_suite_manifest(ROOT / "Evals", "v1", "1.0", repo_root=ROOT, expected_count=25)
        self.assertEqual(first, second)
        validate_suite_manifest(first)
        self.assertEqual(first["task_count"], 25)
        self.assertTrue(all(not task["path"].startswith("/") for task in first["tasks"]))
        self.assertTrue(all(task["sha256"] and task["prompt_sha256"] for task in first["tasks"]))

    def test_expected_count_is_enforced_without_encoding_task_ids(self) -> None:
        with self.assertRaisesRegex(ValueError, "expected 26 fixtures"):
            build_suite_manifest(ROOT / "Evals", "v1", "1.0", repo_root=ROOT, expected_count=26)

    def test_tampering_is_detected(self) -> None:
        manifest = build_suite_manifest(ROOT / "Evals", "v1", "1.0", repo_root=ROOT, expected_count=25)
        tampered = copy.deepcopy(manifest)
        tampered["tasks"][0]["track"] = "changed"
        with self.assertRaisesRegex(ValueError, "sha256"):
            validate_suite_manifest(tampered)


    def test_pinned_v1_manifest_is_valid(self) -> None:
        import json
        pinned = json.loads((ROOT / "suites" / "v1.json").read_text(encoding="utf-8"))
        validate_suite_manifest(pinned)
        self.assertEqual(pinned["task_count"], 5)
        self.assertEqual(pinned["suite_id"], "v1")
        self.assertTrue(pinned["sha256"])

    def test_reference_requires_matching_fixture_digest(self) -> None:
        manifest = build_suite_manifest(ROOT / "Evals", "v1", "1.0", repo_root=ROOT, expected_count=25)
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "suite.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            reference = suite_reference(path, manifest["tasks"][0]["id"], manifest["tasks"][0]["sha256"])
        self.assertEqual(reference["suite_sha256"], manifest["sha256"])
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "suite.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "digest"):
                suite_reference(path, manifest["tasks"][0]["id"], "wrong")


if __name__ == "__main__":
    unittest.main()
