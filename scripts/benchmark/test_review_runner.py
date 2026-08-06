from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from scripts.benchmark.fixture_contract import parse_fixture
from scripts.benchmark.review_runner import (
    attach_presentation_artifacts,
    camera_code,
    copy_video,
    initial_manifest,
    run_review,
    screenshot_angle_names,
)


class ReviewRunnerTests(unittest.TestCase):
    def test_initial_manifest_marks_presentation_only_evidence(self) -> None:
        fixture = parse_fixture("Evals/Scenes/VB_SCENE_001_waterfall_landmark.lua")
        fixture = replace(
            fixture,
            evidence={**fixture.evidence, "static": "not-applicable"},
            screenshot_type="",
            screenshot_angles=0,
        )
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "candidate.luau"
            source.write_text("return Instance.new('Folder')\n", encoding="utf-8")
            manifest = initial_manifest(
                fixture,
                source,
                root / "run",
                generation={"is_model_evaluation": True},
            )
        self.assertFalse(manifest["screenshot_contract"]["enabled"])
        self.assertEqual(manifest["screenshot_contract"]["angle_names"], [])
        self.assertEqual(manifest["presentation_artifacts"], [])
        self.assertFalse(manifest["evidence_summary"]["quality_scored"])
        self.assertTrue(manifest["evidence_summary"]["diagnostic_only"])

    def test_missing_declared_starter_place_fails_before_studio_work(self) -> None:
        fixture = parse_fixture("Evals/Scenes/VB_SCENE_001_waterfall_landmark.lua")
        fixture = replace(fixture, place="starters/missing.rbxl")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "candidate.luau"
            source.write_text("return Instance.new('Folder')\n", encoding="utf-8")
            with self.assertRaisesRegex(FileNotFoundError, "declared starter place"):
                run_review(fixture, source, root / "run", plan_only=True)

    def test_attach_presentation_artifacts_accepts_binary_media(self) -> None:
        fixture = parse_fixture("Evals/Scenes/VB_SCENE_001_waterfall_landmark.lua")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            run_dir = root / "run"
            source = root / "candidate.luau"
            source.write_text("return Instance.new('Folder')\n", encoding="utf-8")
            manifest = initial_manifest(
                fixture,
                source,
                run_dir,
                generation={"is_model_evaluation": True},
            )
            manifest["state"] = "completed"
            manifest["evidence_state"] = "static evidence complete"
            run_dir.mkdir(parents=True)
            (run_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            artifact = root / "game-view.webm"
            artifact.write_bytes(b"\\x00binary-media")
            result = attach_presentation_artifacts(run_dir, (artifact,))
            self.assertEqual(result.manifest["presentation_artifacts"][0]["name"], "game-view.webm")
            self.assertTrue((run_dir / "presentation" / "artifact-0.webm").is_file())

    def test_full_edit_pipeline_with_fake_transport(self) -> None:
        fixture = parse_fixture("Evals/Scenes/VB_SCENE_001_waterfall_landmark.lua")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "candidate.luau"
            source.write_text("return Instance.new('Folder')\n", encoding="utf-8")
            video = root / "capture.mp4"
            video.write_bytes(b"test-media")
            run_dir = root / "run"
            calls: list[str] = []

            def fake_bridge(run_dir_arg: Path, sequence: int, request: dict[str, object], *, timeout: float) -> dict[str, object]:
                operation = str(request["operation"])
                calls.append(operation)
                if operation == "screenshot":
                    artifact_dir = Path(str(request["artifact_dir"]))
                    artifact_dir.mkdir(parents=True, exist_ok=True)
                    artifact_path = artifact_dir / "capture.png"
                    artifact_path.write_bytes(f"frame-{sequence}".encode("ascii"))
                    data = artifact_path.read_bytes()
                    artifact = {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}
                    return {
                        "ok": True,
                        "application_ok": True,
                        "artifact_path": str(artifact_path),
                        "finished": {"state": "succeeded", "result": {"artifact": artifact}},
                    }
                if "bloxbench-rsc-bootstrap" in str(request.get("code")):
                    marker = "bloxbench-rsc-bootstrap"
                elif "bloxbench-reset" in str(request.get("code")):
                    marker = "bloxbench-reset"
                elif "bloxbench-fixture-installed" in str(request.get("code")):
                    marker = "bloxbench-fixture-installed"
                elif "bloxbench-candidate-executed" in str(request.get("code")):
                    marker = "bloxbench-candidate-executed"
                elif "bloxbench-camera" in str(request.get("code")):
                    marker = "bloxbench-camera"
                else:
                    marker = "bloxbench-hook"
                payload = {
                    "marker": marker,
                    "hook": "fake",
                    "payload": json.dumps({"marker": marker, "route_walkable": True}),
                }
                value = {"success": True, "returnValue": json.dumps(payload)}
                return {
                    "ok": True,
                    "application_ok": True,
                    "finished": {"state": "succeeded", "result": {"value": value}},
                }

            with patch("scripts.benchmark.review_runner.qualified.bridge_call", side_effect=fake_bridge), patch(
                "scripts.benchmark.review_runner.qualified.require_screenshot_success"
            ):
                result = run_review(
                    fixture,
                    source,
                    run_dir,
                    instance_id="anon:12345678-1234-4234-8234-123456789abc",
                )

            self.assertEqual(result.state, "completed_unexported")
            self.assertEqual(result.evidence_state, "static evidence complete; generated place missing")
            self.assertNotIn("play_start", calls)
            expected_screenshots = 1 + len(fixture.states or []) * fixture.screenshot_angles
            self.assertEqual(calls.count("screenshot"), expected_screenshots)
            manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["state"], "completed_unexported")
            self.assertEqual(manifest["place"]["generated"], False)
            self.assertIn("check_scene", manifest["readbacks"])
            self.assertIn("check_game:capture", manifest["readbacks"])
            self.assertIn("cleanup", manifest["readbacks"])
            self.assertIn("final_reset", manifest)
            self.assertTrue((run_dir / "review_packet.md").is_file())
            self.assertTrue((run_dir / "evaluation.json").is_file())
            evidence = json.loads((run_dir / "evidence.json").read_text(encoding="utf-8"))
            self.assertEqual(evidence["format"], "bloxbench-structured-evidence-v1")
            self.assertFalse(evidence["quality_scored"])
            self.assertTrue(evidence["state_observations"][0]["screenshot"])
            self.assertTrue((run_dir / "README.md").is_file())
            self.assertTrue((run_dir / "screenshots" / "hero.png").is_file())
            self.assertTrue((run_dir / "trace" / "operations.jsonl").is_file())

    def test_multi_angle_contract_produces_deterministic_camera_codes(self) -> None:
        fixture = parse_fixture("Evals/Scenes/VB_SCENE_001_waterfall_landmark.lua")
        multi_angle = replace(fixture, screenshot_angles=4, screenshot_primary="side")
        self.assertEqual(screenshot_angle_names(multi_angle), ("side", "hero", "front", "rear"))
        self.assertIn("Vector3.new(18, 8, 0)", camera_code("side"))
        self.assertIn('angle = "side"', camera_code("side"))
        self.assertIn("task.wait(1.0)", camera_code("rear"))

    def test_desktop_video_requires_viewport_proof(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            video = root / "capture.mp4"
            video.write_bytes(b"desktop-capture")
            with self.assertRaisesRegex(ValueError, "viewport-only capture proof"):
                copy_video(video, root / "out.mp4", None)

    def test_video_without_proof_is_rejected_before_live_run(self) -> None:
        fixture = parse_fixture("Evals/Scenes/VB_SCENE_001_waterfall_landmark.lua")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "candidate.luau"
            source.write_text("return Instance.new('Folder')\n", encoding="utf-8")
            video = root / "capture.mp4"
            video.write_bytes(b"desktop-capture")
            run_dir = root / "run"
            with self.assertRaisesRegex(ValueError, "matching viewport-only capture proof"):
                run_review(fixture, source, run_dir, videos=(video,), video_proofs=())
            self.assertFalse(run_dir.exists())

    def test_invalid_place_file_is_rejected_before_bundle_creation(self) -> None:
        fixture = parse_fixture("Evals/Scenes/VB_SCENE_001_waterfall_landmark.lua")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "candidate.luau"
            source.write_text("return Instance.new('Folder')\n", encoding="utf-8")
            place = root / "fake.rbxl"
            place.write_bytes(b"not a Roblox place")
            run_dir = root / "run"
            with self.assertRaisesRegex(ValueError, "Roblox place"):
                run_review(fixture, source, run_dir, place_file=place, plan_only=True)
            self.assertFalse(run_dir.exists())

    def test_known_roblox_place_is_recorded_with_format_metadata(self) -> None:
        fixture = parse_fixture("Evals/Scenes/VB_SCENE_001_waterfall_landmark.lua")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "candidate.luau"
            source.write_text("return Instance.new('Folder')\n", encoding="utf-8")
            run_dir = root / "run"
            place = root / "candidate.rbxlx"
            place.write_text(
                '<?xml version="1.0" encoding="utf-8"?>'
                '<roblox version="4"><Item class="Workspace" referent="RBX1">'
                '<Properties><string name="Name">Workspace</string></Properties>'
                '</Item></roblox>',
                encoding="utf-8",
            )
            result = run_review(
                fixture,
                source,
                run_dir,
                place_file=place,
                plan_only=True,
            )
            self.assertEqual(result.state, "planned")
            self.assertEqual(result.manifest["place"]["format"], "rbxlx-xml")
            self.assertTrue(Path(result.manifest["place"]["path"]).is_file())

    def test_input_template_cannot_be_marked_as_generated_place(self) -> None:
        fixture = parse_fixture("Evals/Scenes/VB_SCENE_001_waterfall_landmark.lua")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "candidate.luau"
            source.write_text("return Instance.new('Folder')\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "unchanged input template"):
                run_review(
                    fixture,
                    source,
                    root / "run",
                    place_file=Path("Places/baseplate.rbxl"),
                    plan_only=True,
                )

    def test_source_with_credential_like_field_is_rejected_before_copy(self) -> None:
        fixture = parse_fixture("Evals/Scenes/VB_SCENE_001_waterfall_landmark.lua")
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            source = root / "candidate.luau"
            source.write_text("local API_KEY = 'do-not-save'\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "credential-like"):
                run_review(fixture, source, root / "run", plan_only=True)
            self.assertFalse((root / "run").exists())


if __name__ == "__main__":
    unittest.main()
