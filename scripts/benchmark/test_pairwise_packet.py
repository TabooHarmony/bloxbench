from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.benchmark.pairwise_packet import build_pairwise_packet


class PairwisePacketTests(unittest.TestCase):
    def _run(self, root: Path, name: str, source_sha: str) -> Path:
        run = root / name
        screenshot = run / "screenshots" / "hero.png"
        video = run / "videos" / "video.mp4"
        screenshot.parent.mkdir(parents=True)
        video.parent.mkdir(parents=True)
        screenshot.write_bytes(f"screenshot-{name}".encode())
        video.write_bytes(f"video-{name}".encode())
        video_sha = hashlib.sha256(video.read_bytes()).hexdigest()
        place = run / "place" / "generated.rbxlx"
        place.parent.mkdir(parents=True)
        place.write_text(
            '<?xml version="1.0" encoding="utf-8"?>'
            '<roblox version="4">'
            '<Item class="Workspace" referent="RBX1">'
            '<Properties><string name="Name">Workspace</string></Properties>'
            '</Item></roblox>',
            encoding="utf-8",
        )
        place_sha = hashlib.sha256(place.read_bytes()).hexdigest()
        manifest = {
            "state": "completed",
            "evidence_state": "valid reviewable result",
            "final_reset": {"marker": "bloxbench-reset"},
            "candidate": {"origin": "model", "is_model_evaluation": True},
            "place": {"generated": True, "format": "rbxlx-xml", "path": str(place), "sha256": place_sha, "bytes": place.stat().st_size},
            "fixture": {
                "id": "pilot.drawbridge",
                "scenario_name": "pilot.drawbridge",
                "sha256": "fixture-sha",
                "prompt_sha256": "prompt-sha",
                "place": "baseplate.rbxl",
            },
            "source": {"sha256": source_sha},
            "screenshots": {"hero": str(screenshot)},
            "videos": [{"path": str(video), "sha256": video_sha, "size": video.stat().st_size, "reviewable": True}],
            "readbacks": {"cleanup": {"marker": "cleanup"}},
        }
        (run / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
        return run

    def test_builds_blind_packet_and_preserves_internal_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            run_a = self._run(root, "run-a", "source-a")
            run_b = self._run(root, "run-b", "source-b")
            output = build_pairwise_packet(run_a, run_b, root / "packet")
            packet = json.loads((output / "packet.json").read_text(encoding="utf-8"))
            self.assertEqual(packet["kind"], "bloxbench-pairwise-human-review-v1")
            self.assertEqual(set(packet["labels"]), {"A", "B"})
            self.assertIsNone(packet["automated_boundary"]["final_label"])
            self.assertIn("A_run_dir", packet["provenance_internal"])
            review = (output / "human_review.md").read_text(encoding="utf-8")
            self.assertIn("A better", review)
            self.assertNotIn("source-a", review)
            self.assertTrue((output / "A" / "screenshots" / "hero.png").is_file())
            self.assertTrue((output / "B" / "video" / "video-0.mp4").is_file())
            place_artifacts = [artifact for label in packet["labels"].values() for artifact in label["artifacts"] if artifact["kind"] == "place"]
            self.assertEqual({artifact["format"] for artifact in place_artifacts}, {"rbxlx-xml"})

    def test_rejects_same_source_digest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            run_a = self._run(root, "run-a", "same")
            run_b = self._run(root, "run-b", "same")
            with self.assertRaisesRegex(ValueError, "distinct candidate source"):
                build_pairwise_packet(run_a, run_b, root / "packet")


if __name__ == "__main__":
    unittest.main()
