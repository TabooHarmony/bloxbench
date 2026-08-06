from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.benchmark.benchmark_lock import build_benchmark_lock, lock_digest, validate_benchmark_lock
from scripts.benchmark.suite_manifest import build_suite_manifest


ROOT = Path(__file__).resolve().parents[2]


class BenchmarkLockTests(unittest.TestCase):
    def _suite(self) -> dict:
        return build_suite_manifest(ROOT / "Evals", "v1", "1.0", repo_root=ROOT, expected_count=25)

    def _pinned_suite(self) -> dict:
        import json
        return json.loads((ROOT / "suites" / "v1.json").read_text(encoding="utf-8"))

    def test_lock_records_suite_knowledge_code_and_treatment_identity(self) -> None:
        lock = build_benchmark_lock(self._suite(), repo_root=ROOT)
        validate_benchmark_lock(lock, repo_root=ROOT)
        self.assertEqual(lock["schema"], "bloxbench-benchmark-lock-v1")
        self.assertEqual(lock["suite"]["suite_sha256"], self._suite()["sha256"])
        self.assertEqual(lock["suite"]["task_count"], 25)
        self.assertEqual(lock["treatment"]["primary"], "direct")
        self.assertEqual(lock["treatment"]["repair_track"], "separate")
        self.assertEqual(lock["generation"]["knowledge"][0]["name"], "roblox-core-v1")
        self.assertTrue(lock["generation"]["knowledge"][0]["sha256"])
        self.assertEqual(set(lock["generation"]["models"]), {"flash", "pro"})
        self.assertTrue(lock["evaluation"]["reviewer_labels"])
        self.assertTrue(lock["sha256"])

    def test_pinned_v1_lock_is_valid(self) -> None:
        import json
        pinned = json.loads((ROOT / "suites" / "v1.json").read_text(encoding="utf-8"))
        pinned_lock = json.loads((ROOT / "suites" / "v1.lock.json").read_text(encoding="utf-8"))
        validate_benchmark_lock(pinned_lock, repo_root=ROOT)
        self.assertEqual(pinned_lock["suite"]["task_count"], 5)
        self.assertEqual(pinned_lock["suite"]["suite_sha256"], pinned["sha256"])

    def test_lock_digest_and_referenced_file_hashes_are_checked(self) -> None:
        lock = build_benchmark_lock(self._suite(), repo_root=ROOT)
        tampered = copy.deepcopy(lock)
        tampered["treatment"]["primary"] = "repaired"
        with self.assertRaisesRegex(ValueError, "sha256"):
            validate_benchmark_lock(tampered, repo_root=ROOT)

        tampered = copy.deepcopy(lock)
        tampered["generation"]["generator"]["sha256"] = "wrong"
        tampered["sha256"] = lock_digest(tampered)
        with self.assertRaisesRegex(ValueError, "generator"):
            validate_benchmark_lock(tampered, repo_root=ROOT)

    def test_lock_round_trips_through_json(self) -> None:
        lock = build_benchmark_lock(self._suite(), repo_root=ROOT)
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "benchmark-lock.json"
            path.write_text(json.dumps(lock, sort_keys=True), encoding="utf-8")
            loaded = json.loads(path.read_text(encoding="utf-8"))
        validate_benchmark_lock(loaded, repo_root=ROOT)


if __name__ == "__main__":
    unittest.main()
