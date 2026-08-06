from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("run_test_flight_under_test", HERE / "run_test_flight.py")
assert SPEC and SPEC.loader
HARNESS = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = HARNESS
SPEC.loader.exec_module(HARNESS)


class HarnessContractTests(unittest.TestCase):
    def test_prompt_whitelists_runtime_materials(self) -> None:
        for material in ("Metal", "SmoothPlastic", "Plastic", "Wood", "Fabric"):
            self.assertIn(f"Enum.Material.{material}", HARNESS.PROMPT)
        for material in ("Brass", "Leather", "CastIron", "WoodPlank"):
            self.assertNotIn(f"Enum.Material.{material}", HARNESS.PROMPT)

    def test_prompt_whitelists_runtime_instance_classes(self) -> None:
        for class_name in ("Model", "Part", "WedgePart"):
            self.assertIn(f'Instance.new("{class_name}")', HARNESS.PROMPT)
        for class_name in ("Block", "Ball", "Cylinder", "Wedge"):
            self.assertNotIn(f'Instance.new("{class_name}")', HARNESS.PROMPT)
        self.assertIn("Enum.PartType.Ball", HARNESS.PROMPT)
        self.assertIn("Enum.PartType.Cylinder", HARNESS.PROMPT)
        self.assertIn("branch before assignment", HARNESS.PROMPT)
        self.assertIn("never assign a nil Position or CFrame", HARNESS.PROMPT)

    def test_compact_event_preserves_malformed_message_payload(self) -> None:
        event = {"type": "message_start", "message": "malformed"}
        self.assertEqual(HARNESS.compact_pi_event(event), event)

    def test_compact_event_handles_all_message_shapes_without_dropping_type(self) -> None:
        self.assertEqual(
            HARNESS.compact_pi_event(
                {"type": "message_update", "assistantMessageEvent": {"type": "text_delta", "delta": "x"}}
            ),
            {"type": "message_update", "assistantMessageEvent": {"type": "text_delta", "delta": "x"}},
        )
        self.assertEqual(
            HARNESS.compact_pi_event({"type": "message_update", "assistantMessageEvent": "malformed"}),
            {"type": "message_update", "assistantMessageEvent": "malformed"},
        )
        self.assertEqual(
            HARNESS.compact_pi_event({"type": "message_start", "message": {"role": "user", "content": []}}),
            {"type": "message_start", "role": "user"},
        )
        self.assertEqual(
            HARNESS.compact_pi_event({"type": "message_end", "message": {"role": "assistant", "stopReason": "stop"}}),
            {"type": "message_end", "message": {"role": "assistant", "stopReason": "stop"}},
        )

    def test_tool_result_error_flag_uses_top_level_protocol_field(self) -> None:
        self.assertIs(HARNESS.tool_result_is_error({"isError": False, "result": {"isError": True}}), False)
        self.assertIs(HARNESS.tool_result_is_error({"result": {"isError": True}}), True)
        self.assertIsNone(HARNESS.tool_result_is_error({"result": "malformed"}))

    def test_redaction_only_replaces_sensitive_values(self) -> None:
        with patch.dict(HARNESS.os.environ, {"TEST_TOKEN": "secret", "TEST_TOKENIZED": "other"}, clear=False):
            self.assertEqual(HARNESS.redact_text("secret other"), "[REDACTED] other")

    def test_extension_uses_exclusive_write_without_a_preflight_race(self) -> None:
        extension = (HERE / "pi_output_extension.ts").read_text(encoding="utf-8")
        self.assertNotIn("pathExists", extension)
        self.assertIn('flag: "wx"', extension)
        self.assertIn('errorCode(error) === "EEXIST"', extension)

    def test_bridge_call_ignores_trailing_non_protocol_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            arm_dir = Path(raw_dir) / "flash"

            class FakeBridgeProcess:
                returncode = 0

                def communicate(self, *, input: str | None = None, timeout: float | None = None) -> tuple[str, str]:
                    return '{"ok":true,"value":42}\nbridge debug noise\n', ""

            with patch.object(HARNESS.subprocess, "Popen", return_value=FakeBridgeProcess()) as popen:
                response = HARNESS.bridge_call(arm_dir, 0, {"operation": "status"})
            self.assertTrue(popen.call_args.kwargs["start_new_session"])
            self.assertTrue(response["ok"])
            self.assertEqual(response["value"], 42)

    def test_bridge_diagnostics_are_redacted_before_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            arm_dir = Path(raw_dir) / "flash"

            class FakeBridgeProcess:
                returncode = 0

                def communicate(self, *, input: str | None = None, timeout: float | None = None) -> tuple[str, str]:
                    return '{"ok":true}\n', "bridge secret-token"

            with patch.dict(HARNESS.os.environ, {"TEST_TOKEN": "secret-token"}, clear=False):
                with patch.object(HARNESS.subprocess, "Popen", return_value=FakeBridgeProcess()):
                    HARNESS.bridge_call(arm_dir, 0, {"operation": "status"})
            persisted = (arm_dir / "rsc" / "00-stderr").read_text(encoding="utf-8")
            self.assertNotIn("secret-token", persisted)
            self.assertIn("[REDACTED]", persisted)

    def test_wait_for_instance_polls_until_status_has_one_edit_instance(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            arm_dir = Path(raw_dir) / "flash"
            instance_id = "anon:00000000-0000-0000-0000-000000000000"
            responses = [
                {"status": {"instances": []}},
                {"status": {"instances": [{"role": "edit", "id": instance_id}]}},
            ]
            now = [0.0]
            calls: list[tuple[int, dict[str, object], object]] = []

            def fake_bridge(
                _arm_dir: Path,
                sequence: int,
                request: dict[str, object],
                **kwargs: object,
            ) -> dict[str, object]:
                calls.append((sequence, request, kwargs["timeout"]))
                return responses.pop(0)

            def fake_sleep(seconds: float) -> None:
                now[0] += seconds

            with patch.object(HARNESS, "bridge_call", side_effect=fake_bridge):
                result = HARNESS.wait_for_instance(
                    arm_dir,
                    7,
                    timeout=5,
                    poll_interval=2,
                    clock=lambda: now[0],
                    sleeper=fake_sleep,
                )

            found_id, status, next_sequence, attempts = result
            self.assertEqual(found_id, instance_id)
            self.assertEqual(status["status"]["instances"][0]["id"], instance_id)
            self.assertEqual(next_sequence, 9)
            self.assertEqual([call[0] for call in calls], [7, 8])
            self.assertEqual(calls[0][2], HARNESS.READINESS_BRIDGE_TIMEOUT_SECONDS)
            self.assertEqual([item["state"] for item in attempts], ["not_ready", "ready"])

    def test_wait_for_instance_recovers_after_transient_bridge_failures(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            arm_dir = Path(raw_dir) / "flash"
            instance_id = "anon:00000000-0000-0000-0000-000000000000"
            now = [0.0]
            calls: list[int] = []

            def fake_bridge(
                _arm_dir: Path,
                sequence: int,
                _request: dict[str, object],
                **_kwargs: object,
            ) -> dict[str, object]:
                calls.append(sequence)
                if len(calls) < 3:
                    raise RuntimeError(f"transient MCP failure {len(calls)}")
                return {"status": {"instances": [{"role": "edit", "id": instance_id}]}}

            def fake_sleep(seconds: float) -> None:
                now[0] += seconds

            with patch.object(HARNESS, "bridge_call", side_effect=fake_bridge):
                found_id, _status, next_sequence, attempts = HARNESS.wait_for_instance(
                    arm_dir,
                    11,
                    timeout=10,
                    poll_interval=1,
                    clock=lambda: now[0],
                    sleeper=fake_sleep,
                )

            self.assertEqual(found_id, instance_id)
            self.assertEqual(next_sequence, 14)
            self.assertEqual(calls, [11, 12, 13])
            self.assertEqual([item["state"] for item in attempts], ["not_ready", "not_ready", "ready"])

    def test_run_arm_rejects_unsettled_pi_even_when_source_exists(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            flight_dir = Path(raw_dir) / "flight"

            def fake_run_pi(model: dict[str, object], arm_dir: Path, max_output_tokens: int, *, prompt: str) -> dict[str, object]:
                source = arm_dir / "source" / "candidate.luau"
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text("return {}\n", encoding="utf-8")
                return {"settled": False, "process_returncode": 0, "source_files": [str(source)]}

            with patch.object(HARNESS, "run_pi", side_effect=fake_run_pi):
                result = HARNESS.run_arm("flash", flight_dir, source_only=True, max_output_tokens=32, prompt=HARNESS.PROMPT, prompt_path=HARNESS.CALIBRATION_PROMPT)

            self.assertEqual(result.state, "failed")
            self.assertIn("Pi process contract failed", result.error["message"])

    def test_run_arm_rejects_nonzero_pi_even_when_settled(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            flight_dir = Path(raw_dir) / "flight"

            def fake_run_pi(model: dict[str, object], arm_dir: Path, max_output_tokens: int, *, prompt: str) -> dict[str, object]:
                source = arm_dir / "source" / "candidate.luau"
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text("return {}\n", encoding="utf-8")
                return {"settled": True, "terminal_ok": True, "process_returncode": 17, "source_files": [str(source)]}

            with patch.object(HARNESS, "run_pi", side_effect=fake_run_pi):
                result = HARNESS.run_arm("flash", flight_dir, source_only=True, max_output_tokens=32, prompt=HARNESS.PROMPT, prompt_path=HARNESS.CALIBRATION_PROMPT)

            self.assertEqual(result.state, "failed")
            self.assertIn("Pi process contract failed", result.error["message"])

    def test_run_arm_rejects_a_reused_arm_directory(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            flight_dir = Path(raw_dir) / "flight"
            arm_dir = flight_dir / "flash"
            (arm_dir / "source").mkdir(parents=True)
            (arm_dir / "source" / "candidate.luau").write_text("stale\n", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                HARNESS.run_arm("flash", flight_dir, source_only=True, max_output_tokens=32, prompt=HARNESS.PROMPT, prompt_path=HARNESS.CALIBRATION_PROMPT)

    def test_preflight_reports_a_missing_extension_before_source_generation(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            missing = Path(raw_dir) / "missing-extension.ts"
            with patch.object(HARNESS, "EXTENSION", missing), patch.dict(
                HARNESS.os.environ, {"HYPER_API_KEY": "test-only"}
            ):
                with self.assertRaisesRegex(SystemExit, "Pi output extension"):
                    HARNESS.validate_runtime_inputs(source_only=True, prompt_path=HARNESS.CALIBRATION_PROMPT)

    def test_run_arm_rejects_hidden_or_extra_source_entries(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            flight_dir = Path(raw_dir) / "flight"

            def fake_run_pi(model: dict[str, object], arm_dir: Path, max_output_tokens: int, *, prompt: str) -> dict[str, object]:
                source = arm_dir / "source" / "candidate.luau"
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text("return {}\n", encoding="utf-8")
                (source.parent / ".DS_Store").write_bytes(b"metadata")
                return {"terminal_ok": True, "process_returncode": 0, "source_files": [str(source)]}

            with patch.object(HARNESS, "run_pi", side_effect=fake_run_pi):
                result = HARNESS.run_arm("flash", flight_dir, source_only=True, max_output_tokens=32, prompt=HARNESS.PROMPT, prompt_path=HARNESS.CALIBRATION_PROMPT)

            self.assertEqual(result.state, "failed")
            self.assertIn("source output contract failed", result.error["message"])

    def test_bridge_timeout_is_preserved_and_terminates_the_process_group(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            arm_dir = Path(raw_dir) / "flash"

            class FakeBridgeProcess:
                returncode = None

                def __init__(self) -> None:
                    self.communicate_calls = 0

                def communicate(self, *, input: str | None = None, timeout: float | None = None) -> tuple[str, str]:
                    self.communicate_calls += 1
                    if self.communicate_calls == 1:
                        raise subprocess.TimeoutExpired(["uv"], timeout or 7, output="partial", stderr="stuck")
                    self.returncode = -15
                    return "partial", "stuck"

            fake_process = FakeBridgeProcess()
            with patch.object(HARNESS.subprocess, "Popen", return_value=fake_process) as popen:
                with patch.object(HARNESS, "terminate_process_tree") as terminate:
                    with self.assertRaises(RuntimeError):
                        HARNESS.bridge_call(
                            arm_dir,
                            0,
                            {"operation": "status"},
                            timeout=7,
                        )

            self.assertTrue(popen.call_args.kwargs["start_new_session"])
            terminate.assert_called_once_with(fake_process)
            response = json.loads((arm_dir / "rsc" / "00-response.json").read_text())
            self.assertFalse(response["ok"])
            self.assertEqual(response["error"]["type"], "bridge_timeout")
            self.assertEqual(response["error"]["timeout_seconds"], 7)
            self.assertIn("partial", response["error"]["stdout_tail"])

    def test_screenshot_requires_application_level_success(self) -> None:
        failed = {
            "finished": {
                "state": "succeeded",
                "result": {"ok": False, "error": "capture failed"},
            }
        }
        with self.assertRaises(RuntimeError):
            HARNESS.require_screenshot_success(failed, "screenshot front")

    def test_screenshot_requires_artifact_metadata(self) -> None:
        missing_artifact = {
            "finished": {
                "state": "succeeded",
                "result": {"ok": True},
            }
        }
        with self.assertRaises(RuntimeError):
            HARNESS.require_screenshot_success(missing_artifact, "screenshot front")

    def test_luau_contract_rejects_malformed_nested_results(self) -> None:
        malformed = (
            {},
            {"finished": []},
            {"finished": {"state": "succeeded", "result": []}},
            {"finished": {"state": "succeeded", "result": {"value": "not-an-object"}}},
            {
                "finished": {
                    "state": "succeeded",
                    "result": {"value": {"success": True, "returnValue": "not-json"}},
                }
            },
        )
        for response in malformed:
            with self.subTest(response=response):
                with self.assertRaises(RuntimeError):
                    HARNESS.require_luau_success(response, "test", "marker")

    def test_luau_contract_accepts_runtime_eval_result_field(self) -> None:
        runtime_eval = {
            "finished": {
                "state": "succeeded",
                "result": {
                    "value": {"ok": True, "result": json.dumps({"marker": "runtime-marker"})}
                },
            }
        }
        self.assertIs(
            HARNESS.require_luau_success(runtime_eval, "runtime eval", "runtime-marker"),
            runtime_eval,
        )

    def test_live_arm_rejects_a_local_screenshot_hash_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            flight_dir = Path(raw_dir) / "flight"

            def fake_run_pi(model: dict[str, object], arm_dir: Path, max_output_tokens: int, *, prompt: str) -> dict[str, object]:
                source = arm_dir / "source" / "candidate.luau"
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text("return {}\n", encoding="utf-8")
                return {"settled": True, "terminal_ok": True, "process_returncode": 0, "source_files": [str(source)]}

            def luau_success(marker: str) -> dict[str, object]:
                return {
                    "finished": {
                        "state": "succeeded",
                        "result": {"value": {"success": True, "returnValue": json.dumps({"marker": marker})}},
                    }
                }

            def fake_bridge(
                arm_dir: Path,
                sequence: int,
                request: dict[str, object],
                **kwargs: object,
            ) -> dict[str, object]:
                operation = request.get("operation")
                if operation == "refresh_worker":
                    return {"ok": True}
                if operation == "status":
                    return {"status": {"instances": [{"role": "edit", "id": "anon:00000000-0000-0000-0000-000000000000"}]}}
                code = request.get("code")
                if code == HARNESS.BOOTSTRAP_CODE:
                    return luau_success("bloxbench-rsc-bootstrap")
                if code == HARNESS.RESET_CODE:
                    return luau_success("bloxbench-reset")
                if code == HARNESS.VALIDATE_CODE:
                    return luau_success("bloxbench-validation")
                if operation == "screenshot":
                    path = Path(str(request["artifact_dir"])) / "screenshot.png"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(b"actual")
                    return {
                        "artifact_path": str(path),
                        "finished": {
                            "state": "succeeded",
                            "result": {
                                "ok": True,
                                "artifact": {"path": "C:/job/screenshot.png", "sha256": "0" * 64, "size": 6},
                            },
                        },
                    }
                if code in HARNESS.CAMERA_CODES.values():
                    return luau_success("bloxbench-camera")
                return luau_success("unexpected")

            with patch.object(HARNESS, "run_pi", side_effect=fake_run_pi), patch.object(
                HARNESS, "bridge_call", side_effect=fake_bridge
            ):
                result = HARNESS.run_arm("flash", flight_dir, max_output_tokens=32, prompt=HARNESS.PROMPT, prompt_path=HARNESS.CALIBRATION_PROMPT)

            self.assertEqual(result.state, "failed")
            self.assertIn("local artifact metadata mismatch", result.error["message"])

    def test_bootstrap_retries_after_instance_id_changes(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            flight_dir = Path(raw_dir) / "flight"
            first_id = "anon:11111111-1111-1111-1111-111111111111"
            second_id = "anon:22222222-2222-2222-2222-222222222222"
            state = {"status_calls": 0, "bootstrap_calls": 0, "bootstrap_ids": []}

            def fake_run_pi(model: dict[str, object], arm_dir: Path, max_output_tokens: int, *, prompt: str) -> dict[str, object]:
                source = arm_dir / "source" / "candidate.luau"
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text("return {}\n", encoding="utf-8")
                return {
                    "settled": True,
                    "terminal_ok": True,
                    "process_returncode": 0,
                    "source_files": [str(source)],
                }

            def fake_bridge(
                arm_dir: Path,
                sequence: int,
                request: dict[str, object],
                **kwargs: object,
            ) -> dict[str, object]:
                operation = request.get("operation")
                if operation == "refresh_worker":
                    return {"ok": True}
                if operation == "status":
                    state["status_calls"] += 1
                    instance_id = first_id if state["status_calls"] == 1 else second_id
                    return {"status": {"instances": [{"role": "edit", "id": instance_id}]}}
                if operation == "exec" and request.get("code") == HARNESS.BOOTSTRAP_CODE:
                    state["bootstrap_calls"] += 1
                    state["bootstrap_ids"].append(request["instance_id"])
                    if state["bootstrap_calls"] == 1:
                        raise RuntimeError("stale instance")
                if operation == "screenshot":
                    path = Path(str(request["artifact_dir"])) / "screenshot.png"
                    path.parent.mkdir(parents=True, exist_ok=True)
                    data = b"valid screenshot"
                    path.write_bytes(data)
                    return {
                        "artifact_path": str(path),
                        "finished": {
                            "state": "succeeded",
                            "result": {
                                "ok": True,
                                "artifact": {
                                    "sha256": hashlib.sha256(data).hexdigest(),
                                    "size": len(data),
                                },
                            },
                        },
                    }
                return {}

            with patch.object(HARNESS, "run_pi", side_effect=fake_run_pi), patch.object(
                HARNESS, "bridge_call", side_effect=fake_bridge
            ), patch.object(HARNESS, "require_luau_success"), patch.object(
                HARNESS, "require_screenshot_success"
            ):
                result = HARNESS.run_arm("flash", flight_dir, max_output_tokens=32, prompt=HARNESS.PROMPT, prompt_path=HARNESS.CALIBRATION_PROMPT)

            self.assertEqual(result.state, "completed")
            self.assertEqual(state["bootstrap_ids"], [first_id, second_id])
            manifest = json.loads((flight_dir / "flash" / "manifest.json").read_text())
            self.assertEqual(manifest["bootstrap_retry_from"], first_id)
            self.assertEqual([item["state"] for item in manifest["bootstrap_attempts"]], ["failed", "succeeded"])

    def test_run_directories_do_not_collide_on_the_same_second(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            results_root = Path(raw_dir)
            first = HARNESS.create_flight_dir(results_root, stamp="20260801T000000Z")
            second = HARNESS.create_flight_dir(results_root, stamp="20260801T000000Z")
            self.assertNotEqual(first, second)
            self.assertTrue(first.is_dir())
            self.assertTrue(second.is_dir())

    def test_run_directories_are_unique_under_concurrent_creation(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            results_root = Path(raw_dir)
            with ThreadPoolExecutor(max_workers=8) as executor:
                paths = list(
                    executor.map(
                        lambda _: HARNESS.create_flight_dir(results_root, stamp="20260801T000000Z"),
                        range(8),
                    )
                )
            self.assertEqual(len(set(paths)), 8)

    def test_provenance_contains_code_and_fixture_digests(self) -> None:
        provenance = HARNESS.build_provenance()
        for key in (
            "launcher_sha256",
            "bridge_sha256",
            "extension_sha256",
            "prompt_sha256",
            "place_sha256",
            "prompt_path",
        ):
            if key == "prompt_path":
                self.assertIsInstance(provenance[key], str)
            else:
                self.assertRegex(provenance[key], r"^[0-9a-f]{64}$")

    def test_interrupted_flight_summary_preserves_partial_results(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            flight_dir = Path(raw_dir) / "flight"
            summary = HARNESS.write_flight_summary(
                flight_dir,
                ("flash", "pro"),
                [HARNESS.ArmResult(arm="flash", state="failed")],
                source_only=False,
                flight_error=SystemExit(143),
            )
            self.assertEqual(summary["orchestration_state"], "interrupted")
            self.assertEqual(summary["unattempted_arms"], ["pro"])
            persisted = json.loads((flight_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(persisted["flight_error"]["type"], "SystemExit")

    def test_flight_lock_rejects_a_second_live_run(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            results_root = Path(raw_dir)
            with HARNESS.flight_lock(results_root):
                with self.assertRaisesRegex(RuntimeError, "already running"):
                    with HARNESS.flight_lock(results_root):
                        pass

    def test_sigterm_handler_routes_through_cleanup_exception(self) -> None:
        previous = signal.getsignal(signal.SIGTERM)
        with HARNESS.shutdown_signal_handler():
            handler = signal.getsignal(signal.SIGTERM)
            if not callable(handler):
                self.fail("SIGTERM handler was not callable")
            with self.assertRaises(SystemExit) as raised:
                handler(signal.SIGTERM, None)
            self.assertEqual(raised.exception.code, 128 + signal.SIGTERM)
        self.assertIs(signal.getsignal(signal.SIGTERM), previous)

    def test_failed_pi_process_is_recorded_without_leaking_the_child(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            fake_pi = Path(raw_dir) / "fake-pi"
            fake_pi.write_text(
                "#!/usr/bin/env python3\n"
                "import os, sys\n"
                "sys.stdin.close()\n"
                "os._exit(17)\n",
                encoding="utf-8",
            )
            fake_pi.chmod(0o755)
            arm_dir = Path(raw_dir) / "arm"
            with patch.object(HARNESS, "PI", fake_pi), patch.dict(HARNESS.os.environ, {"HYPER_API_KEY": "test-only"}):
                result = HARNESS.run_pi(
                    HARNESS.MODELS["flash"],
                    arm_dir,
                    max_output_tokens=32,
                    timeout_seconds=5,
                    prompt=HARNESS.PROMPT,
                )
            self.assertEqual(result["process_returncode"], 17)
            self.assertEqual(result["abort_reason"], "pi_process_exited")

    def test_pi_timeout_terminates_the_process_group(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            root = Path(raw_dir)
            fake_pi = root / "fake-pi"
            child_pid_file = root / "child.pid"
            fake_pi.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, pathlib, subprocess, sys, time\n"
                "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
                "pathlib.Path(os.environ['CHILD_PID_FILE']).write_text(str(child.pid))\n"
                "print(json.dumps({'type': 'thinking_delta', 'delta': 'running'}), flush=True)\n"
                "time.sleep(60)\n",
                encoding="utf-8",
            )
            fake_pi.chmod(0o755)
            arm_dir = root / "arm"
            env = {"HYPER_API_KEY": "test-only", "CHILD_PID_FILE": str(child_pid_file)}
            started = time.monotonic()
            with patch.object(HARNESS, "PI", fake_pi), patch.dict(HARNESS.os.environ, env):
                result = HARNESS.run_pi(
                    HARNESS.MODELS["flash"],
                    arm_dir,
                    max_output_tokens=32,
                    timeout_seconds=0.3,
                    prompt=HARNESS.PROMPT,
                )
            elapsed = time.monotonic() - started
            self.assertEqual(result["abort_reason"], "pi_timeout")
            self.assertLess(elapsed, 5.0)
            child_pid = int(child_pid_file.read_text())
            for _ in range(40):
                try:
                    os.kill(child_pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.05)
            else:
                self.fail(f"Pi descendant {child_pid} survived process-group termination")

    def test_non_object_json_event_does_not_abort_the_launcher(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            root = Path(raw_dir)
            fake_pi = root / "fake-pi"
            fake_pi.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, pathlib\n"
                "pathlib.Path(os.environ['BLOX_SOURCE_OUTPUT']).write_text('return {}\\n')\n"
                "print('[]', flush=True)\n"
                "print(json.dumps({'type': 'turn_end', 'errorMessage': 'provider failed'}), flush=True)\n"
                "print(json.dumps({'type': 'tool_execution_end', 'toolName': 'write_source', 'isError': False}), flush=True)\n"
                "print(json.dumps({'type': 'agent_settled'}), flush=True)\n"
                "os._exit(0)\n",
                encoding="utf-8",
            )
            fake_pi.chmod(0o755)
            with patch.object(HARNESS, "PI", fake_pi), patch.dict(HARNESS.os.environ, {"HYPER_API_KEY": "test-only"}):
                result = HARNESS.run_pi(
                    HARNESS.MODELS["flash"],
                    root / "arm",
                    max_output_tokens=32,
                    timeout_seconds=5,
                    prompt=HARNESS.PROMPT,
                )
            self.assertTrue(result["settled"])
            self.assertTrue(result["terminal_ok"])
            self.assertEqual(result["event_counts"]["non_object_json"], 1)
            self.assertEqual(result["pi_errors"], ["provider failed"])

    def test_nonretrying_agent_end_after_one_successful_source_write_is_terminal(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            root = Path(raw_dir)
            fake_pi = root / "fake-pi"
            fake_pi.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, pathlib\n"
                "path = pathlib.Path(os.environ['BLOX_SOURCE_OUTPUT'])\n"
                "path.write_text('return {}\\n')\n"
                "print(json.dumps({'type': 'tool_execution_end', 'toolName': 'write_source', 'result': {'isError': False}}), flush=True)\n"
                "print(json.dumps({'type': 'agent_end', 'willRetry': False}), flush=True)\n",
                encoding="utf-8",
            )
            fake_pi.chmod(0o755)
            with patch.object(HARNESS, "PI", fake_pi), patch.dict(HARNESS.os.environ, {"HYPER_API_KEY": "test-only"}):
                result = HARNESS.run_pi(
                    HARNESS.MODELS["flash"],
                    root / "arm",
                    max_output_tokens=32,
                    timeout_seconds=5,
                    prompt=HARNESS.PROMPT,
                )
            self.assertFalse(result["settled"])
            self.assertEqual(result["terminal_event"], "agent_end")
            self.assertTrue(result["terminal_ok"])
            self.assertEqual(result["process_returncode"], 0)

    def test_malformed_source_write_result_cannot_promote_agent_end(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            root = Path(raw_dir)
            fake_pi = root / "fake-pi"
            fake_pi.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, pathlib\n"
                "pathlib.Path(os.environ['BLOX_SOURCE_OUTPUT']).write_text('return {}\\n')\n"
                "print(json.dumps({'type': 'tool_execution_end', 'toolName': 'write_source', 'result': 'malformed'}), flush=True)\n"
                "print(json.dumps({'type': 'agent_end', 'willRetry': False}), flush=True)\n"
                "os._exit(0)\n",
                encoding="utf-8",
            )
            fake_pi.chmod(0o755)
            with patch.object(HARNESS, "PI", fake_pi), patch.dict(HARNESS.os.environ, {"HYPER_API_KEY": "test-only"}):
                result = HARNESS.run_pi(
                    HARNESS.MODELS["flash"],
                    root / "arm",
                    max_output_tokens=32,
                    timeout_seconds=5,
                    prompt=HARNESS.PROMPT,
                )
            self.assertFalse(result["terminal_ok"])
            self.assertEqual(result["abort_reason"], "pi_terminal_without_valid_source")
            self.assertIsNone(result["tool_calls"][0]["isError"])

    def test_nonretrying_agent_end_without_source_fails_immediately(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            root = Path(raw_dir)
            fake_pi = root / "fake-pi"
            fake_pi.write_text(
                "#!/usr/bin/env python3\n"
                "import json\n"
                "print(json.dumps({'type': 'agent_end', 'willRetry': False}), flush=True)\n",
                encoding="utf-8",
            )
            fake_pi.chmod(0o755)
            with patch.object(HARNESS, "PI", fake_pi), patch.dict(HARNESS.os.environ, {"HYPER_API_KEY": "test-only"}):
                result = HARNESS.run_pi(
                    HARNESS.MODELS["flash"],
                    root / "arm",
                    max_output_tokens=32,
                    timeout_seconds=5,
                    prompt=HARNESS.PROMPT,
                )
            self.assertFalse(result["terminal_ok"])
            self.assertEqual(result["abort_reason"], "pi_terminal_without_valid_source")

    def test_pi_environment_keeps_only_the_selected_provider_key(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            root = Path(raw_dir)
            fake_pi = root / "fake-pi"
            snapshot = root / "env.keys"
            fake_pi.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os\n"
                "open(os.environ['ENV_SNAPSHOT'], 'w').write(json.dumps(sorted(os.environ)))\n"
                "print(json.dumps({'type': 'agent_settled'}), flush=True)\n",
                encoding="utf-8",
            )
            fake_pi.chmod(0o755)
            env = {
                "HYPER_API_KEY": "hyper-test-secret",
                "LLM_API_KEY": "other-test-secret",
                "LLM_API_BASE": "https://wrong.example/v1",
                "ENV_SNAPSHOT": str(snapshot),
            }
            with patch.object(HARNESS, "PI", fake_pi), patch.dict(HARNESS.os.environ, env):
                HARNESS.run_pi(
                    HARNESS.MODELS["flash"],
                    root / "arm",
                    max_output_tokens=32,
                    timeout_seconds=5,
                    prompt=HARNESS.PROMPT,
                )
                self.assertEqual(HARNESS.redact_text("prefix hyper-test-secret suffix"), "prefix [REDACTED] suffix")
            keys = set(json.loads(snapshot.read_text()))
            self.assertIn("HYPER_API_KEY", keys)
            self.assertNotIn("LLM_API_KEY", keys)
            self.assertNotIn("LLM_API_BASE", keys)

    def test_pi_stderr_is_redacted_before_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            root = Path(raw_dir)
            fake_pi = root / "fake-pi"
            fake_pi.write_text(
                "#!/usr/bin/env python3\n"
                "import json, os, pathlib, sys\n"
                "sys.stderr.write('secret-token\\n')\n"
                "pathlib.Path(os.environ['BLOX_SOURCE_OUTPUT']).write_text('return {}\\n')\n"
                "print(json.dumps({'type': 'tool_execution_end', 'toolName': 'write_source', 'isError': False}), flush=True)\n"
                "print(json.dumps({'type': 'agent_end', 'willRetry': False}), flush=True)\n",
                encoding="utf-8",
            )
            fake_pi.chmod(0o755)
            with patch.object(HARNESS, "PI", fake_pi), patch.dict(
                HARNESS.os.environ,
                {"HYPER_API_KEY": "test-only", "TEST_TOKEN": "secret-token"},
            ):
                HARNESS.run_pi(
                    HARNESS.MODELS["flash"],
                    root / "arm",
                    max_output_tokens=32,
                    timeout_seconds=5,
                    prompt=HARNESS.PROMPT,
                )
            persisted = (root / "arm" / "pi.stderr").read_text(encoding="utf-8")
            self.assertNotIn("secret-token", persisted)
            self.assertIn("[REDACTED]", persisted)

    def test_failed_live_arm_attempts_parent_cleanup_without_masking_error(self) -> None:
        with tempfile.TemporaryDirectory() as raw_dir:
            flight_dir = Path(raw_dir) / "flight"
            calls: list[tuple[int, dict[str, object]]] = []

            def fake_run_pi(model: dict[str, object], arm_dir: Path, max_output_tokens: int, *, prompt: str) -> dict[str, object]:
                source = arm_dir / "source" / "candidate.luau"
                source.parent.mkdir(parents=True, exist_ok=True)
                source.write_text("return {}\n", encoding="utf-8")
                return {"settled": True, "terminal_ok": True, "process_returncode": 0, "source_files": [str(source)]}

            def luau_success(marker: str) -> dict[str, object]:
                return {
                    "finished": {
                        "state": "succeeded",
                        "result": {"value": {"success": True, "returnValue": json.dumps({"marker": marker})}},
                    }
                }

            def fake_bridge(
                arm_dir: Path,
                sequence: int,
                request: dict[str, object],
                **kwargs: object,
            ) -> dict[str, object]:
                calls.append((sequence, request))
                operation = request.get("operation")
                if operation == "refresh_worker":
                    return {"ok": True}
                if operation == "status":
                    return {"status": {"instances": [{"role": "edit", "id": "anon:00000000-0000-0000-0000-000000000000"}]}}
                if operation == "screenshot":
                    raise AssertionError("screenshots must not run after candidate failure")
                code = request.get("code")
                if code == HARNESS.BOOTSTRAP_CODE:
                    return luau_success("bloxbench-rsc-bootstrap")
                if code == HARNESS.RESET_CODE:
                    return luau_success("bloxbench-reset")
                if code == HARNESS.VALIDATE_CODE:
                    return luau_success("bloxbench-validation")
                return {
                    "finished": {
                        "state": "succeeded",
                        "result": {"value": {"success": False, "error": "candidate failed"}},
                    }
                }

            with patch.object(HARNESS, "run_pi", side_effect=fake_run_pi), patch.object(
                HARNESS, "bridge_call", side_effect=fake_bridge
            ):
                result = HARNESS.run_arm("flash", flight_dir, max_output_tokens=32, prompt=HARNESS.PROMPT, prompt_path=HARNESS.CALIBRATION_PROMPT)

            self.assertEqual(result.state, "failed")
            self.assertIn("candidate execution", result.error["message"])
            manifest = json.loads((flight_dir / "flash" / "manifest.json").read_text())
            self.assertIn("cleanup", manifest)
            self.assertEqual(calls[-1][0], max(sequence for sequence, _request in calls))
            self.assertEqual(len({sequence for sequence, _request in calls}), len(calls))
            self.assertEqual(calls[-1][1]["code"], HARNESS.RESET_CODE)


if __name__ == "__main__":
    unittest.main()
