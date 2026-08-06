from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.benchmark.pairwise_packet import build_pairwise_packet
from scripts.benchmark.record_human_review import ingest_human_review


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

    def test_builds_blind_packet_and_separates_internal_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            run_a = self._run(root, "run-a", "source-a")
            run_b = self._run(root, "run-b", "source-b")
            output = build_pairwise_packet(run_a, run_b, root / "packet")
            packet = json.loads((output / "packet.json").read_text(encoding="utf-8"))
            self.assertEqual(packet["kind"], "bloxbench-pairwise-human-review-v3")
            self.assertEqual(set(packet["labels"]), {"A", "B"})
            self.assertIsNone(packet["human_decision"])
            self.assertNotIn("provenance_internal", packet)
            internal = json.loads((root / ".packet.provenance_internal.json").read_text(encoding="utf-8"))
            self.assertIn("A_run_dir", internal)
            review = (output / "human_review.md").read_text(encoding="utf-8")
            self.assertIn("A better", review)
            self.assertNotIn("source-a", review)
            self.assertTrue((output / "A" / "screenshots" / "hero.png").is_file())
            self.assertTrue((output / "B" / "video" / "video-0.mp4").is_file())
            place_artifacts = [artifact for label in packet["labels"].values() for artifact in label["artifacts"] if artifact["kind"] == "place"]
            self.assertEqual({artifact["format"] for artifact in place_artifacts}, {"rbxlx-xml"})

    def test_built_packet_round_trips_a_human_decision(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            run_a = self._run(root, "run-a", "source-a")
            run_b = self._run(root, "run-b", "source-b")
            output = build_pairwise_packet(run_a, run_b, root / "packet")
            form_path = output / "review_form.json"
            form = json.loads(form_path.read_text(encoding="utf-8"))
            form["label"] = "tie"
            form["reviewer"] = "reviewer-1"
            form["notes"] = "Both outputs are similarly reviewable."
            form_path.write_text(json.dumps(form), encoding="utf-8")
            ingest_human_review(output)
            packet = json.loads((output / "packet.json").read_text(encoding="utf-8"))
            decision = packet["human_decision"]
            self.assertEqual(decision["label"], "tie")
            self.assertEqual(decision["reviewer"], "reviewer-1")
            self.assertTrue((output / "human_decision.json").is_file())
            self.assertFalse(packet["automated_boundary"]["quality_scored"])

    def test_presentation_artifact_can_replace_diagnostic_screenshots(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            run_a = self._run(root, "run-a", "source-a")
            run_b = self._run(root, "run-b", "source-b")
            for run in (run_a, run_b):
                manifest_path = run / "manifest.json"
                manifest = json.loads(manifest_path.read_text())
                presentation = run / "presentation" / "game-view.webm"
                presentation.parent.mkdir(parents=True, exist_ok=True)
                presentation.write_bytes(f"presentation-{run.name}".encode())
                manifest["screenshots"] = {}
                manifest["videos"] = []
                manifest["presentation_artifacts"] = [{
                    "kind": "presentation-video",
                    "name": "game-view",
                    "role": "presentation",
                    "path": str(presentation),
                    "sha256": hashlib.sha256(presentation.read_bytes()).hexdigest(),
                    "bytes": presentation.stat().st_size,
                }]
                manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            output = build_pairwise_packet(run_a, run_b, root / "packet")
            packet = json.loads((output / "packet.json").read_text(encoding="utf-8"))
            self.assertTrue(all(label["diagnostics"]["warning_count"] == 0 for label in packet["labels"].values()))
            self.assertTrue(all(artifact["kind"] == "presentation-video" for label in packet["labels"].values() for artifact in label["artifacts"] if artifact["kind"] == "presentation-video"))
            self.assertTrue((output / "A" / "presentation" / "000-game-view.webm").is_file())

    def test_place_artifact_is_reviewable_without_screenshot_or_video(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            run_a = self._run(root, "run-a", "source-a")
            run_b = self._run(root, "run-b", "source-b")
            for run in (run_a, run_b):
                manifest_path = run / "manifest.json"
                manifest = json.loads(manifest_path.read_text())
                manifest["screenshots"] = {}
                manifest["videos"] = []
                manifest["presentation_artifacts"] = []
                manifest["evidence_state"] = "static evidence not collected"
                manifest_path.write_text(json.dumps(manifest))
            output = build_pairwise_packet(run_a, run_b, root / "packet")
            packet = json.loads((output / "packet.json").read_text())
            self.assertTrue(all(any(item["kind"] == "place" for item in label["artifacts"]) for label in packet["labels"].values()))
            self.assertIn("screenshots", packet["labels"]["A"]["evidence_gaps"])

    def test_direct_and_repaired_treatments_are_not_paired(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            run_a = self._run(root, "run-a", "source-a")
            run_b = self._run(root, "run-b", "source-b")
            manifest_path = run_b / "manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["candidate"]["treatment"] = "repaired"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "comparison context treatment"):
                build_pairwise_packet(run_a, run_b, root / "packet")

    def test_warning_bearing_completed_run_is_still_pairwise_reviewable(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            run_a = self._run(root, "run-a", "source-a")
            run_b = self._run(root, "run-b", "source-b")
            manifest = json.loads((run_a / "manifest.json").read_text())
            manifest["evidence_state"] = "completed with diagnostic warnings"
            (run_a / "manifest.json").write_text(json.dumps(manifest))
            output = build_pairwise_packet(run_a, run_b, root / "packet")
            self.assertTrue((output / "human_review.md").is_file())

    def test_uses_nested_converted_place_when_export_manifest_is_json(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            run_a = self._run(root, "run-a", "source-a")
            run_b = self._run(root, "run-b", "source-b")
            manifest = json.loads((run_a / "manifest.json").read_text())
            place_dir = run_a / "place"
            export_path = place_dir / "generated.json"
            export_path.write_text(json.dumps({"kind": "studio_build_export", "parts": []}))
            rbxlx_path = place_dir / "converted.rbxlx"
            rbxlx_path.write_text(
                '<?xml version="1.0" encoding="utf-8"?>'
                '<roblox version="4">'
                '<Item class="Workspace" referent="RBX1">'
                '<Properties><string name="Name">Workspace</string></Properties>'
                '</Item></roblox>',
                encoding="utf-8",
            )
            manifest["place"] = {
                "generated": True,
                "format": "roblox-bench-export-json",
                "path": str(export_path),
                "sha256": hashlib.sha256(export_path.read_bytes()).hexdigest(),
                "bytes": export_path.stat().st_size,
                "rbxlx": {"path": str(rbxlx_path), "bytes": rbxlx_path.stat().st_size},
            }
            (run_a / "manifest.json").write_text(json.dumps(manifest))
            output = build_pairwise_packet(run_a, run_b, root / "packet")
            artifacts = [
                artifact
                for label in json.loads((output / "packet.json").read_text())["labels"].values()
                for artifact in label["artifacts"]
            ]
            self.assertIn("rbxlx-xml", {artifact["format"] for artifact in artifacts if artifact["kind"] == "place"})
            self.assertTrue((output / "A" / "place" / "converted.rbxlx").is_file() or (output / "B" / "place" / "converted.rbxlx").is_file())

    def test_resolves_repository_relative_artifact_paths(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            run_a = self._run(root, "run-a", "source-a")
            run_b = self._run(root, "run-b", "source-b")
            for run in (run_a, run_b):
                manifest_path = run / "manifest.json"
                manifest = json.loads(manifest_path.read_text())
                manifest["screenshots"] = {"hero": f"{run.name}/screenshots/hero.png"}
                manifest["videos"][0]["path"] = f"{run.name}/videos/video.mp4"
                manifest["place"]["path"] = f"{run.name}/place/generated.rbxlx"
                manifest_path.write_text(json.dumps(manifest))
            output = build_pairwise_packet(run_a, run_b, root / "packet")
            self.assertTrue((output / "A" / "screenshots" / "hero.png").is_file())
            self.assertTrue((output / "B" / "video" / "video-0.mp4").is_file())

    def test_rejects_same_source_digest(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            run_a = self._run(root, "run-a", "same")
            run_b = self._run(root, "run-b", "same")
            with self.assertRaisesRegex(ValueError, "distinct candidate source"):
                build_pairwise_packet(run_a, run_b, root / "packet")


if __name__ == "__main__":
    unittest.main()
