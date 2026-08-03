from __future__ import annotations

import base64
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from roblox_studio_control import RemoteConfig, RemoteControlClient


REFRESH_GUEST_TIMEOUT = 30.0
STATUS_GUEST_TIMEOUT = 45.0
STATUS_INSTANCE_WAIT_TIMEOUT = 15.0
STATUS_POLL_INTERVAL = 0.5
DEFAULT_ATTACHED_TIMEOUT = 120.0
MAX_ATTACHED_TIMEOUT = 600.0
INSTANCE_ID_PATTERN = re.compile(r"^anon:[0-9a-f-]{36}$")
RSC_CLI = "C:/Users/Admin/rsc/venv/Scripts/rsc.exe"


def emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(payload, separators=(",", ":"), sort_keys=True) + "\n")
    sys.stdout.flush()


def admin_health_status(client: RemoteControlClient) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Read the Admin-session MCP health view when SYSTEM-scoped RSC status is empty."""
    health = client.transport.run(
        [
            "C:/Windows/System32/curl.exe",
            "-sS",
            "--max-time",
            "10",
            "http://127.0.0.1:3002/health",
        ],
        timeout=STATUS_GUEST_TIMEOUT,
    )
    if not isinstance(health, dict) or health.get("pluginConnected") is not True:
        return None
    raw_instances = health.get("instances")
    if not isinstance(raw_instances, list):
        return None

    instances: list[dict[str, Any]] = []
    for raw_instance in raw_instances:
        if not isinstance(raw_instance, dict):
            continue
        instance_id = raw_instance.get("instanceId") or raw_instance.get("id") or raw_instance.get("instance_id")
        if not isinstance(instance_id, str) or not instance_id:
            continue
        instance = dict(raw_instance)
        instance.setdefault("id", instance_id)
        instances.append(instance)
    if not instances:
        return None
    return {"instances": instances}, health


def status_snapshot(client: RemoteControlClient) -> dict[str, Any]:
    """Keep one MCP stdio session alive while waiting for Studio to register."""
    raw = client._rsc(
        "status",
        "--wait",
        "--wait-timeout",
        str(STATUS_INSTANCE_WAIT_TIMEOUT),
        "--poll-interval",
        str(STATUS_POLL_INTERVAL),
    )
    if not isinstance(raw, dict):
        return {"instances": [], "raw": raw}
    instance = raw.get("instance")
    if isinstance(instance, dict):
        normalized_instance = dict(instance)
        instance_id = (
            normalized_instance.get("id")
            or normalized_instance.get("instanceId")
            or normalized_instance.get("instance_id")
        )
        if isinstance(instance_id, str) and instance_id:
            normalized_instance.setdefault("id", instance_id)
            normalized = dict(raw)
            normalized.pop("instance", None)
            normalized["instances"] = [normalized_instance]
            return normalized
    return raw


def discover(client: RemoteControlClient) -> tuple[str, dict[str, Any]]:
    status_error: str | None = None
    health_error: str | None = None
    health: dict[str, Any] | None = None
    try:
        health_status = admin_health_status(client)
    except Exception as exc:
        health_status = None
        health_error = str(exc)
    if health_status is not None:
        status, health = health_status
    else:
        try:
            status = status_snapshot(client)
        except Exception as exc:
            status = {"instances": []}
            status_error = str(exc) or health_error
    instances = status.get("instances", []) if isinstance(status, dict) else []
    if not isinstance(instances, list):
        raise RuntimeError("RSC status returned a non-list instances field")

    if not instances and health is None:
        health_status = admin_health_status(client)
        if health_status is not None:
            status, health = health_status
            instances = status["instances"]

    edit = [item for item in instances if isinstance(item, dict) and item.get("role") == "edit"]
    if edit:
        candidates = edit
    else:
        candidates = [item for item in instances if isinstance(item, dict) and "role" not in item]
    if len(candidates) != 1:
        message = f"expected exactly one attached Studio instance, found {len(candidates)}"
        if status_error:
            message += f"; status wait failed: {status_error}"
        raise RuntimeError(message)

    record = candidates[0]
    instance_id = record.get("id") or record.get("instance_id")
    if not isinstance(instance_id, str) or not instance_id:
        raise RuntimeError("attached Studio instance has no usable id")
    discovery: dict[str, Any] = {"status": status, "instance": record}
    if health is not None:
        discovery["health"] = health
        discovery["source"] = "mcp_health"
    return instance_id, discovery


def application_result_ok(finished_result: Any) -> bool:
    """Require transport success and, when present, nested Luau success."""
    if not isinstance(finished_result, dict) or finished_result.get("ok") is not True:
        return False
    value = finished_result.get("value")
    if isinstance(value, dict) and "success" in value:
        return value.get("success") is True
    return True


def finish_job(
    client: RemoteControlClient,
    submitted: dict[str, Any],
    *,
    timeout: float,
    artifact_dir: str | None = None,
) -> dict[str, Any]:
    job_id = submitted.get("id")
    if not isinstance(job_id, str) or not job_id:
        raise RuntimeError(f"RSC submission returned no job id: {submitted}")
    try:
        finished = client.wait(job_id, timeout=timeout + 30.0)
    except TimeoutError as exc:
        cancel_error: Exception | None = None
        try:
            client.job("cancel", job_id)
        except Exception as cancel_exc:
            cancel_error = cancel_exc
        message = f"RSC job {job_id} exceeded its wait timeout and cancellation was requested"
        if cancel_error is not None:
            message += f" but failed: {cancel_error}"
        raise TimeoutError(message) from exc
    if not isinstance(finished, dict):
        raise RuntimeError(f"RSC wait returned a non-object: {finished!r}")
    result = client.job("result", job_id)
    response: dict[str, Any] = {
        "submitted": submitted,
        "finished": finished,
        "result": result,
    }
    finished_result = finished.get("result")
    application_ok = application_result_ok(finished_result)
    response["application_ok"] = application_ok
    response["ok"] = finished.get("state") == "succeeded" and application_ok
    if artifact_dir is not None and finished.get("state") == "succeeded" and application_ok:
        artifact = client.fetch_artifact(job_id, output_dir=Path(artifact_dir))
        response["artifact_path"] = str(artifact)
    return response


def refresh_run(client: RemoteControlClient, argv: list[str]) -> Any:
    return client.transport.run(argv, timeout=REFRESH_GUEST_TIMEOUT)


def attached_timeout(request: dict[str, Any]) -> float:
    raw = request.get("timeout", DEFAULT_ATTACHED_TIMEOUT)
    if isinstance(raw, bool):
        raise ValueError("timeout must be a finite number")
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("timeout must be a finite number") from exc
    if not math.isfinite(value) or value <= 0 or value > MAX_ATTACHED_TIMEOUT:
        raise ValueError(f"timeout must be greater than 0 and at most {MAX_ATTACHED_TIMEOUT:g} seconds")
    return value


def validate_instance_id(value: Any) -> str:
    if not isinstance(value, str) or not INSTANCE_ID_PATTERN.fullmatch(value):
        raise ValueError("instance_id must match anon:<uuid>")
    return value


def run(request: dict[str, Any]) -> dict[str, Any]:
    operation = request.get("operation")
    guest_timeout = STATUS_GUEST_TIMEOUT if operation in {"status", "discover_log_instance", "refresh_worker"} else 120.0
    client = RemoteControlClient(config=RemoteConfig(guest_timeout=guest_timeout))
    if operation == "status":
        status_error: str | None = None
        health_error: str | None = None
        health: dict[str, Any] | None = None
        try:
            health_status = admin_health_status(client)
        except Exception as exc:
            health_status = None
            health_error = str(exc)
        if health_status is not None:
            status, health = health_status
        else:
            try:
                status = status_snapshot(client)
            except Exception as exc:
                status = {"instances": []}
                status_error = str(exc) or health_error
        response: dict[str, Any] = {
            "ok": True,
            "status": status,
            "status_source": "mcp_health" if health is not None else "rsc",
        }
        if health is not None:
            response["health"] = health
        if status_error:
            response["status_error"] = status_error
        instances = status.get("instances", []) if isinstance(status, dict) else []
        if isinstance(instances, list) and not instances and health is None:
            health_status = admin_health_status(client)
            if health_status is not None:
                normalized_status, health = health_status
                response["status"] = normalized_status
                response["health"] = health
                response["status_source"] = "mcp_health"
        return response
    if operation == "discover_log_instance":
        lines = client.transport.run(
            [
                "C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
                "-NoProfile",
                "-Command",
                "$log=Get-ChildItem C:\\Users\\Admin\\AppData\\Local\\Roblox\\logs -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1; if ($log) { Select-String -Path $log.FullName -Pattern 'anon:[0-9a-f-]{36}/edit' | Select-Object -Last 20 -ExpandProperty Line }",
            ],
            timeout=REFRESH_GUEST_TIMEOUT,
        )
        matches = re.findall(r"anon:[0-9a-f-]{36}", str(lines))
        if not matches:
            raise RuntimeError("no current anon Studio instance id found in the latest Studio log")
        return {"ok": True, "instance_id": matches[-1], "source": "latest_studio_log"}
    if operation == "refresh_worker":
        stale_cleanup = refresh_run(
            client,
            [
                "C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
                "-NoProfile",
                "-Command",
                "$p=Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object { ($_.Name -eq 'StudioMCP.exe') -or ($_.Name -eq 'node.exe' -and $_.CommandLine -match '(?i)robloxstudio-mcp|StudioMCP') }; $p | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; exit 0",
            ],
        )
        stop = refresh_run(
            client,
            [
                "C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
                "-NoProfile",
                "-Command",
                "& C:/Windows/System32/schtasks.exe /End /TN RSC-Worker | Out-Null; exit 0",
            ],
        )
        worker_cleanup = refresh_run(
            client,
            [
                "C:/Windows/System32/WindowsPowerShell/v1.0/powershell.exe",
                "-NoProfile",
                "-Command",
                "$p=Get-Process -Name rsc -ErrorAction SilentlyContinue; if ($p) { $p | Stop-Process -Force }; exit 0",
            ],
        )
        lease_reset = refresh_run(
            client,
            [
                "C:/Program Files/Python312/python.exe",
                "-c",
                "import sqlite3; db=sqlite3.connect(r\"C:\\Users\\Admin\\.rsc\\rsc.sqlite3\", timeout=5); n=db.execute(\"delete from worker_lease where singleton=1\").rowcount; db.commit(); print({\"deleted\":n})",
            ],
        )
        start = refresh_run(
            client,
            ["C:/Windows/System32/schtasks.exe", "/Run", "/TN", "RSC-Worker"],
        )
        return {
            "ok": True,
            "refresh_worker": {
                "stale_session0_cleanup": stale_cleanup,
                "stop": stop,
                "worker_process_cleanup": worker_cleanup,
                "lease_reset": lease_reset,
                "run": start,
            },
        }
    if operation not in {"exec", "eval", "play_start", "play_stop", "logs", "screenshot", "export_build"}:
        raise ValueError(f"unsupported operation: {operation!r}")

    timeout = attached_timeout(request)

    instance_id = request.get("instance_id")
    discovery: dict[str, Any] | None = None
    if instance_id is None:
        instance_id, discovery = discover(client)
    else:
        instance_id = validate_instance_id(instance_id)

    if operation in {"exec", "eval", "play_start", "play_stop", "logs"}:
        code = request.get("code")
        if operation in {"exec", "eval"} and (not isinstance(code, str) or not code):
            raise ValueError(f"{operation} requires non-empty code")
        submitted = client.submit_attached(
            operation,
            instance_id=instance_id,
            code=code,
            target=request.get("target"),
            arguments=request.get("arguments") or {},
            timeout=timeout,
            idempotency_key=request.get("idempotency_key"),
        )
        response = finish_job(client, submitted, timeout=timeout)
    elif operation == "screenshot":
        submitted = client.submit_attached(
            "screenshot",
            instance_id=instance_id,
            arguments=request.get("arguments") or {},
            timeout=timeout,
            idempotency_key=request.get("idempotency_key"),
        )
        response = finish_job(
            client,
            submitted,
            timeout=timeout,
            artifact_dir=request.get("artifact_dir"),
        )
    elif operation == "export_build":
        # Export through the queued attached path so the SAME connected
        # StudioSession handles it (the worker's AttachedExecutor supports
        # export_build). A direct `rsc call` would start a second MCP server
        # that proxies and conflicts with the primary on 58741.
        export_args = dict(request.get("arguments") or {})
        if "instance_path" in export_args and "instancePath" not in export_args:
            export_args["instancePath"] = export_args.pop("instance_path")
        if "output_id" in export_args and "outputId" not in export_args:
            export_args["outputId"] = export_args.pop("output_id")
        if "instancePath" not in export_args:
            export_args["instancePath"] = "game.Workspace.BloxBenchCandidate"
        if "outputId" not in export_args:
            raise ValueError("export_build requires an output_id (destination .rbxl path)")
        submitted = client.submit_attached(
            "export_build",
            instance_id=instance_id,
            arguments=export_args,
            timeout=timeout,
            idempotency_key=request.get("idempotency_key"),
        )
        response = finish_job(client, submitted, timeout=timeout)
        # The worker returns the build JSON content base64-embedded; decode locally.
        saved_to = ""
        artifact_b64 = ""
        result = ((response.get("finished") or {}).get("result") or {})
        inner = result.get("value") if isinstance(result, dict) else None
        if isinstance(inner, dict):
            saved_to = inner.get("saved_to") or inner.get("savedTo") or ""
            artifact_b64 = inner.get("artifact_b64") or ""
        output_name = Path(str(export_args.get("outputId", "build"))).name
        local_artifact = Path(request.get("artifact_dir") or ".") / f"{output_name}.json"
        local_artifact.parent.mkdir(parents=True, exist_ok=True)
        if artifact_b64:
            local_artifact.write_bytes(base64.b64decode(artifact_b64.encode("ascii")))
        else:
            # Fallback: scp the build JSON from the VM.
            if not saved_to:
                saved_to = rf"C:\Users\Admin\.robloxstudio-mcp\build-library\{output_name}.json"
            saved_to_clean = saved_to.replace("\\", "/")
            ssh_pass = os.environ.get("WINDEV_SSH_PASS", "")
            if not ssh_pass:
                raise RuntimeError("export_build requires WINDEV_SSH_PASS to fetch the build JSON")
            scp_cmd = [
                "sshpass", "-p", ssh_pass, "scp",
                "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=8",
                f"Admin@192.168.40.250:{saved_to_clean}",
                str(local_artifact),
            ]
            scp_done = subprocess.run(scp_cmd, capture_output=True, text=True, timeout=guest_timeout)
            if scp_done.returncode != 0:
                raise RuntimeError(f"export_build scp failed: {scp_done.stderr[:300]}")
        data = local_artifact.read_bytes()
        response["artifact_path"] = str(local_artifact)
        response["bytes"] = len(data)
        response["export"] = {
            "instance_path": export_args.get("instancePath"),
            "output_id": export_args.get("outputId"),
            "saved_to": saved_to,
        }
    else:
        raise ValueError(f"unsupported operation: {operation!r}")

    if response.get("ok") is not True:
        raise RuntimeError(f"RSC operation did not succeed: {response}")
    response["instance_id"] = instance_id
    if discovery is not None:
        response["discovery"] = discovery
    return response


def main() -> int:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            request = json.loads(line)
            if not isinstance(request, dict):
                raise ValueError("request must be a JSON object")
            emit(run(request))
        except Exception as exc:
            emit({"ok": False, "error": {"type": type(exc).__name__, "message": str(exc)}})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
