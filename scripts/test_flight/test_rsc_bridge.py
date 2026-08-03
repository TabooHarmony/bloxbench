from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch


HERE = Path(__file__).resolve().parent
RSC_SRC = Path("/root/roblox-studio-control/src")
if str(RSC_SRC) not in sys.path:
    sys.path.insert(0, str(RSC_SRC))
SPEC = importlib.util.spec_from_file_location("rsc_bridge_under_test", HERE / "rsc_bridge.py")
assert SPEC and SPEC.loader
BRIDGE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BRIDGE
SPEC.loader.exec_module(BRIDGE)


class FakeClient:
    def __init__(self) -> None:
        self.fetch_called = False

    def wait(self, job_id: str, *, timeout: float) -> dict[str, object]:
        return {
            "state": "succeeded",
            "result": {"ok": False, "error": "capture failed"},
        }

    def job(self, operation: str, job_id: str) -> dict[str, object]:
        return {"ok": False, "error": "capture failed"}

    def fetch_artifact(self, job_id: str, *, output_dir: Path) -> Path:
        self.fetch_called = True
        raise AssertionError("failed screenshot payload must not fetch an artifact")


class TimeoutClient:
    def __init__(self) -> None:
        self.cancelled: list[tuple[str, str]] = []

    def wait(self, job_id: str, *, timeout: float) -> dict[str, object]:
        raise TimeoutError("wait expired")

    def job(self, operation: str, job_id: str) -> dict[str, object]:
        self.cancelled.append((operation, job_id))
        return {"ok": True}


class SuccessClient:
    def __init__(self) -> None:
        self.fetch_called = False

    def wait(self, job_id: str, *, timeout: float) -> dict[str, object]:
        return {"state": "succeeded", "result": {"ok": True, "value": {"success": True}}}

    def job(self, operation: str, job_id: str) -> dict[str, object]:
        return {"ok": True}

    def fetch_artifact(self, job_id: str, *, output_dir: Path) -> Path:
        self.fetch_called = True
        return output_dir / "unused.png"


class BridgeContractTests(unittest.TestCase):
    def test_attached_timeout_rejects_nonfinite_and_out_of_range_values(self) -> None:
        for value in (True, "nan", "inf", 0, -1, BRIDGE.MAX_ATTACHED_TIMEOUT + 1):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    BRIDGE.attached_timeout({"timeout": value})

    def test_instance_id_validation_rejects_arbitrary_strings(self) -> None:
        self.assertEqual(
            BRIDGE.validate_instance_id("anon:00000000-0000-0000-0000-000000000000"),
            "anon:00000000-0000-0000-0000-000000000000",
        )
        with self.assertRaises(ValueError):
            BRIDGE.validate_instance_id("old-instance-id")

    def test_finish_job_does_not_fetch_failed_screenshot_artifact(self) -> None:
        client = FakeClient()
        response = BRIDGE.finish_job(
            client,
            {"id": "job-1"},
            timeout=1,
            artifact_dir="/tmp/does-not-matter",
        )
        self.assertNotIn("artifact_path", response)
        self.assertFalse(client.fetch_called)

    def test_finish_job_marks_nested_application_failure_as_not_ok(self) -> None:
        client = FakeClient()
        response = BRIDGE.finish_job(client, {"id": "job-1"}, timeout=1)
        self.assertFalse(response["ok"])

    def test_finish_job_exec_path_returns_nested_success_without_artifact_fetch(self) -> None:
        client = SuccessClient()
        response = BRIDGE.finish_job(client, {"id": "job-1"}, timeout=1)
        self.assertTrue(response["ok"])
        self.assertTrue(response["application_ok"])
        self.assertFalse(client.fetch_called)

    def test_finish_job_requests_cancellation_after_wait_timeout(self) -> None:
        client = TimeoutClient()
        with self.assertRaisesRegex(TimeoutError, "cancellation was requested"):
            BRIDGE.finish_job(client, {"id": "job-timeout"}, timeout=1)
        self.assertEqual(client.cancelled, [("cancel", "job-timeout")])

    def test_run_does_not_promote_nested_application_failure_to_bridge_success(self) -> None:
        client = Mock()
        client.submit_attached.return_value = {"id": "job-1"}
        with patch.object(BRIDGE, "RemoteControlClient", return_value=client), patch.object(
            BRIDGE,
            "finish_job",
            return_value={"ok": False, "finished": {"state": "succeeded", "result": {"ok": False}}},
        ):
            with self.assertRaisesRegex(RuntimeError, "did not succeed"):
                BRIDGE.run(
                    {
                        "operation": "exec",
                        "instance_id": "anon:00000000-0000-0000-0000-000000000000",
                        "code": "return 1",
                    }
                )

    def test_status_uses_a_bounded_guest_timeout(self) -> None:
        fake_client = Mock()
        fake_client._rsc.return_value = {"instances": []}
        with patch.object(BRIDGE, "RemoteControlClient", return_value=fake_client) as constructor:
            result = BRIDGE.run({"operation": "status"})
        self.assertTrue(result["ok"])
        config = constructor.call_args.kwargs["config"]
        self.assertEqual(config.guest_timeout, BRIDGE.STATUS_GUEST_TIMEOUT)
        fake_client._rsc.assert_called_once_with(
            "status",
            "--wait",
            "--wait-timeout",
            str(BRIDGE.STATUS_INSTANCE_WAIT_TIMEOUT),
            "--poll-interval",
            str(BRIDGE.STATUS_POLL_INTERVAL),
        )

    def test_status_normalizes_waited_instance_shape(self) -> None:
        instance_id = "anon:00000000-0000-0000-0000-000000000000"
        fake_client = Mock()
        fake_client._rsc.return_value = {
            "tools": ["execute_luau"],
            "instance": {"instance_id": instance_id, "role": "edit"},
        }
        with patch.object(BRIDGE, "RemoteControlClient", return_value=fake_client):
            result = BRIDGE.run({"operation": "status"})
        self.assertEqual(result["status_source"], "rsc")
        self.assertEqual(result["status"]["instances"], [{"id": instance_id, "instance_id": instance_id, "role": "edit"}])

    def test_status_falls_back_to_health_when_waited_client_fails(self) -> None:
        fake_client = Mock()
        fake_client._rsc.side_effect = RuntimeError("MCP client exited")
        health = {
            "status": "ok",
            "pluginConnected": True,
            "instanceCount": 1,
            "instances": [{"instanceId": "anon:00000000-0000-0000-0000-000000000000", "role": "edit"}],
        }
        fake_client.transport.run.side_effect = [{"pluginConnected": False}, health]
        with patch.object(BRIDGE, "RemoteControlClient", return_value=fake_client):
            result = BRIDGE.run({"operation": "status"})
        self.assertEqual(result["status_source"], "mcp_health")
        self.assertEqual(result["status"]["instances"][0]["id"], "anon:00000000-0000-0000-0000-000000000000")
        self.assertEqual(result["status_error"], "MCP client exited")

    def test_status_uses_admin_health_when_system_status_has_no_instances(self) -> None:
        fake_client = Mock()
        fake_client._rsc.return_value = {"instances": [], "tools": ["execute_luau"]}
        health = {
            "status": "ok",
            "pluginConnected": True,
            "instanceCount": 1,
            "instances": [
                {
                    "instanceId": "anon:00000000-0000-0000-0000-000000000000",
                    "role": "edit",
                    "placeName": "baseplate.rbxl",
                }
            ],
        }
        fake_client.transport.run.return_value = health

        with patch.object(BRIDGE, "RemoteControlClient", return_value=fake_client):
            result = BRIDGE.run({"operation": "status"})

        self.assertTrue(result["ok"])
        self.assertEqual(result["status_source"], "mcp_health")
        self.assertEqual(
            result["status"]["instances"][0]["id"],
            "anon:00000000-0000-0000-0000-000000000000",
        )
        self.assertEqual(result["health"], health)
        command = fake_client.transport.run.call_args.args[0]
        self.assertEqual(command[0], "C:/Windows/System32/curl.exe")
        self.assertEqual(command[-1], "http://127.0.0.1:3002/health")

    def test_invalid_attached_timeout_is_rejected_before_discovery(self) -> None:
        with patch.object(BRIDGE, "discover", side_effect=AssertionError("discovery must not run")):
            with patch.object(BRIDGE, "RemoteControlClient", return_value=Mock()):
                with self.assertRaises(ValueError):
                    BRIDGE.run(
                        {
                            "operation": "exec",
                            "instance_id": "anon:00000000-0000-0000-0000-000000000000",
                            "code": "return 1",
                            "timeout": "nan",
                        }
                    )

    def test_invalid_present_instance_id_is_rejected_before_discovery(self) -> None:
        with patch.object(BRIDGE, "discover", side_effect=AssertionError("discovery must not run")):
            with patch.object(BRIDGE, "RemoteControlClient", return_value=Mock()):
                with self.assertRaises(ValueError):
                    BRIDGE.run(
                        {
                            "operation": "exec",
                            "instance_id": "old-instance-id",
                            "code": "return 1",
                        }
                    )

    def test_discover_rejects_non_edit_role_when_role_is_present(self) -> None:
        client = Mock()
        client._rsc.return_value = {"instances": [{"role": "client", "id": "anon:00000000-0000-0000-0000-000000000000"}]}
        with self.assertRaisesRegex(RuntimeError, "exactly one"):
            BRIDGE.discover(client)
    def test_refresh_worker_cleans_mcp_node_processes_by_command_line(self) -> None:
        calls: list[list[str]] = []

        def fake_refresh(_client: object, argv: list[str]) -> str:
            calls.append(argv)
            return ""

        with patch.object(BRIDGE, "RemoteControlClient", return_value=Mock()), patch.object(
            BRIDGE, "refresh_run", side_effect=fake_refresh
        ):
            result = BRIDGE.run({"operation": "refresh_worker"})

        self.assertTrue(result["ok"])
        commands = [" ".join(argv) for argv in calls]
        self.assertTrue(any("Get-CimInstance Win32_Process" in command for command in commands))
        self.assertTrue(any("robloxstudio-mcp" in command for command in commands))


if __name__ == "__main__":
    unittest.main()
