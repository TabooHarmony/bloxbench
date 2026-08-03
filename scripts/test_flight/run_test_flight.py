#!/usr/bin/env python3
"""Run one unscored Charm Hyper Pi/RSC stability test flight."""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import signal
import select
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
PI = Path("/root/.cache/bloxbench/pi/0.83.0/node_modules/.bin/pi")
RSC_PROJECT = Path("/root/roblox-studio-control")
BRIDGE = ROOT / "scripts/test_flight/rsc_bridge.py"
MAX_PI_EVENT_LOG_BYTES = 25_000_000
DEFAULT_MAX_OUTPUT_TOKENS = 16_000
MAX_MAX_OUTPUT_TOKENS = 384_000
PI_TIMEOUT_SECONDS = 900.0
BRIDGE_TIMEOUT_SECONDS = 300.0
REFRESH_BRIDGE_TIMEOUT_SECONDS = 180.0
READINESS_TIMEOUT_SECONDS = 120.0
READINESS_POLL_INTERVAL_SECONDS = 2.0
PRE_REFRESH_READINESS_TIMEOUT_SECONDS = 20.0
READINESS_BRIDGE_TIMEOUT_SECONDS = 45.0
EXTENSION = ROOT / "scripts/test_flight/pi_output_extension.ts"
CALIBRATION_PROMPT = ROOT / "scripts/test_flight/calibration_prompt.txt"
PLACE = ROOT / "Places/baseplate.rbxl"

PROVIDER_ID = "charm-hyper"
PROVIDER_NAME = "Charm Hyper"
BASE_URL = "https://hyper.charm.land/v1"
MODELS = {
    "flash": {
        "id": "deepseek-v4-flash",
        "name": "DeepSeek V4 Flash",
        "input_price": 0.2,
        "output_price": 0.4,
        "cache_hit_price": 0.04,
    },
    "pro": {
        "id": "deepseek-v4-pro",
        "name": "DeepSeek V4 Pro",
        "input_price": 2.4,
        "output_price": 4.8,
        "cache_hit_price": 0.2,
    },
}

PROMPT = CALIBRATION_PROMPT.read_text(encoding="utf-8")

RESET_CODE = """local removed = 0
for _, item in ipairs(workspace:GetDescendants()) do
    if item:IsA(\"Model\") and item.Name == \"BloxBenchCandidate\" and item.Parent then
        item:Destroy()
        removed += 1
    end
end
local selection = game:GetService(\"Selection\")
selection:Set({})
return {marker = \"bloxbench-reset\", removed = removed}
"""

BOOTSTRAP_CODE = 'return {marker = "bloxbench-rsc-bootstrap", value = 1}'

VALIDATE_CODE = """local candidates = {}
for _, item in ipairs(workspace:GetChildren()) do
    if item:IsA(\"Model\") and item.Name == \"BloxBenchCandidate\" then
        table.insert(candidates, item)
    end
end
assert(#candidates == 1, \"expected exactly one top-level BloxBenchCandidate model\")
local candidate = candidates[1]
local required = {"FrontWheel", "RearWheel", "Frame", "Engine", "Exhaust", "Handlebars", "Seat", "FuelTank", "FrontFender", "RearFender"}
local present = {}
for _, name in ipairs(required) do
    local child = candidate:FindFirstChild(name, true)
    assert(child, \"missing required part: \" .. name)
    assert(child:IsA(\"BasePart\"), \"required item is not a BasePart: \" .. name)
    present[name] = child.ClassName
end
local partCount = 0
local anchored = true
for _, item in ipairs(candidate:GetDescendants()) do
    if item:IsA(\"BasePart\") then
        partCount += 1
        anchored = anchored and item.Anchored
    end
end
assert(partCount > 0, \"candidate has no BaseParts\")
local pivot = candidate:GetPivot().Position
local boundsCFrame, boundsSize = candidate:GetBoundingBox()
return {
    marker = \"bloxbench-validation\",
    name = candidate.Name,
    class_name = candidate.ClassName,
    part_count = partCount,
    anchored = anchored,
    pivot = {x = pivot.X, y = pivot.Y, z = pivot.Z},
    bounds = {x = boundsSize.X, y = boundsSize.Y, z = boundsSize.Z},
    required = present,
    bounds_center = {x = boundsCFrame.Position.X, y = boundsCFrame.Position.Y, z = boundsCFrame.Position.Z},
}
"""

CAMERA_CODES = {
    "front": """local candidate = workspace:FindFirstChild(\"BloxBenchCandidate\")
assert(candidate and candidate:IsA(\"Model\"), \"BloxBenchCandidate model is missing\")
local camera = workspace.CurrentCamera
assert(camera, \"CurrentCamera is unavailable\")
local boundsCFrame, boundsSize = candidate:GetBoundingBox()
local target = boundsCFrame.Position
local extent = math.max(boundsSize.X, boundsSize.Y, boundsSize.Z)
local distance = (extent * 0.5 / math.tan(math.rad(camera.FieldOfView) * 0.5)) * 1.6
camera.CameraType = Enum.CameraType.Scriptable
camera.CFrame = CFrame.lookAt(target + Vector3.new(11, 7, 13).Unit * distance, target)
return {marker = \"bloxbench-camera\", angle = \"front\"}
""",
    "side": """local candidate = workspace:FindFirstChild(\"BloxBenchCandidate\")
assert(candidate and candidate:IsA(\"Model\"), \"BloxBenchCandidate model is missing\")
local camera = workspace.CurrentCamera
assert(camera, \"CurrentCamera is unavailable\")
local boundsCFrame, boundsSize = candidate:GetBoundingBox()
local target = boundsCFrame.Position
local extent = math.max(boundsSize.X, boundsSize.Y, boundsSize.Z)
local distance = (extent * 0.5 / math.tan(math.rad(camera.FieldOfView) * 0.5)) * 1.6
camera.CameraType = Enum.CameraType.Scriptable
camera.CFrame = CFrame.lookAt(target + Vector3.new(-13, 6, 8).Unit * distance, target)
return {marker = \"bloxbench-camera\", angle = \"side\"}
""",
    "back": """local candidate = workspace:FindFirstChild(\"BloxBenchCandidate\")
assert(candidate and candidate:IsA(\"Model\"), \"BloxBenchCandidate model is missing\")
local camera = workspace.CurrentCamera
assert(camera, \"CurrentCamera is unavailable\")
local boundsCFrame, boundsSize = candidate:GetBoundingBox()
local target = boundsCFrame.Position
local extent = math.max(boundsSize.X, boundsSize.Y, boundsSize.Z)
local distance = (extent * 0.5 / math.tan(math.rad(camera.FieldOfView) * 0.5)) * 1.6
camera.CameraType = Enum.CameraType.Scriptable
camera.CFrame = CFrame.lookAt(target + Vector3.new(10, 8, -13).Unit * distance, target)
return {marker = \"bloxbench-camera\", angle = \"back\"}
""",
}


@dataclass
class ArmResult:
    arm: str
    state: str
    source_path: str | None = None
    instance_id: str | None = None
    error: dict[str, str] | None = None
    screenshots: dict[str, str] | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_metadata(path: Path) -> dict[str, Any]:
    """Return revision and dirty state without making git a runtime dependency."""
    metadata: dict[str, Any] = {"path": str(path), "revision": None, "dirty": None}
    try:
        revision = subprocess.run(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if revision.returncode != 0:
            return metadata
        metadata["revision"] = revision.stdout.strip() or None
        status = subprocess.run(
            ["git", "-C", str(path), "status", "--porcelain"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        metadata["dirty"] = status.returncode == 0 and bool(status.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        pass
    return metadata


def build_provenance(prompt_path: Path = CALIBRATION_PROMPT) -> dict[str, Any]:
    """Describe every source and repository revision that can affect a flight."""
    return {
        "launcher_sha256": sha256_file(Path(__file__).resolve()),
        "bridge_sha256": sha256_file(BRIDGE),
        "extension_sha256": sha256_file(EXTENSION),
        "prompt_sha256": sha256_file(prompt_path),
        "prompt_path": str(prompt_path.relative_to(ROOT)),
        "place_sha256": sha256_file(PLACE),
        "bloxbench": git_metadata(ROOT),
        "rsc": git_metadata(RSC_PROJECT),
    }


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def create_flight_dir(results_root: Path, *, stamp: str | None = None) -> Path:
    """Create a collision-safe run directory, including concurrent same-second starts."""
    results_root.mkdir(parents=True, exist_ok=True)
    base_stamp = stamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = results_root / f"test-flight-{base_stamp}"
    for suffix in range(1000):
        candidate = base if suffix == 0 else base.with_name(f"{base.name}-{suffix:03d}")
        try:
            candidate.mkdir(parents=False, exist_ok=False)
        except FileExistsError:
            continue
        return candidate
    raise RuntimeError(f"could not allocate a unique flight directory below {results_root}")


@contextlib.contextmanager
def flight_lock(results_root: Path):
    """Serialize runs that share the live Studio/RSC target."""
    results_root.mkdir(parents=True, exist_ok=True)
    lock_path = results_root / ".test-flight.lock"
    handle = lock_path.open("a+", encoding="utf-8")
    try:
        try:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise RuntimeError("another BloxBench test flight is already running") from exc
        yield
    finally:
        with contextlib.suppress(OSError):
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def _text_tail(value: Any, limit: int = 2000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode("utf-8", errors="replace")
    return str(value)[-limit:]


def _redacted_tail(value: Any, limit: int = 2000) -> str:
    return redact_text(_text_tail(value, limit))


def redact_text(value: str) -> str:
    redacted = value
    for key_name, key_value in os.environ.items():
        if not key_value or not isinstance(key_value, str):
            continue
        if key_name == "HYPER_API_KEY" or key_name.endswith(("_API_KEY", "_TOKEN", "_PASSWORD", "_SECRET")):
            redacted = redacted.replace(key_value, "[REDACTED]")
    return redacted


def compact_pi_event(event: dict[str, Any]) -> dict[str, Any]:
    """Keep provenance while dropping Pi's repeated full partial messages."""
    event_type = event.get("type")
    if event_type == "message_update":
        update = event.get("assistantMessageEvent")
        if isinstance(update, dict):
            return {
                "type": event_type,
                "assistantMessageEvent": {
                    key: update[key]
                    for key in ("type", "contentIndex", "delta")
                    if key in update
                },
            }
    if event_type in {"message_start", "message_end"}:
        message = event.get("message")
        if isinstance(message, dict):
            if event_type == "message_start" and message.get("role") == "user":
                return {"type": event_type, "role": "user"}
            return {
                "type": event_type,
                "message": {
                    key: message[key]
                    for key in ("role", "api", "provider", "model", "usage", "stopReason", "timestamp")
                    if key in message
                },
            }
    return event


def empty_usage_totals() -> dict[str, int | float]:
    return {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_tokens": 0,
        "cache_write_tokens": 0,
        "total_tokens": 0,
        "cost_input": 0,
        "cost_output": 0,
        "cost_cache_read": 0,
        "cost_cache_write": 0,
        "cost_total": 0,
    }


def add_usage_totals(total: dict[str, int | float], usage: dict[str, Any]) -> None:
    for destination, source in {
        "input_tokens": "input",
        "output_tokens": "output",
        "cache_read_tokens": "cacheRead",
        "cache_write_tokens": "cacheWrite",
        "total_tokens": "totalTokens",
    }.items():
        value = usage.get(source)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            total[destination] += value
    cost = usage.get("cost")
    if isinstance(cost, dict):
        for destination, source in {
            "cost_input": "input",
            "cost_output": "output",
            "cost_cache_read": "cacheRead",
            "cost_cache_write": "cacheWrite",
            "cost_total": "total",
        }.items():
            value = cost.get(source)
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                total[destination] += value


def tool_result_is_error(event: dict[str, Any]) -> bool | None:
    """Read Pi's top-level error flag, with compatibility for older nested events."""
    top_level = event.get("isError")
    if isinstance(top_level, bool):
        return top_level
    result = event.get("result")
    nested = result.get("isError") if isinstance(result, dict) else None
    return nested if isinstance(nested, bool) else None


def model_config(max_output_tokens: int) -> dict[str, Any]:
    models = []
    for item in MODELS.values():
        models.append(
            {
                "id": item["id"],
                "name": item["name"],
                "reasoning": True,
                "input": ["text"],
                "contextWindow": 1_000_000,
                "maxTokens": max_output_tokens,
                "cost": {
                    "input": item["input_price"],
                    "output": item["output_price"],
                    "cacheRead": item["cache_hit_price"],
                    "cacheWrite": 0,
                },
                "thinkingLevelMap": {
                    "off": None,
                    "minimal": None,
                    "low": None,
                    "medium": None,
                    "high": "high",
                    "xhigh": "xhigh",
                    "max": None,
                },
                "compat": {
                    "supportsDeveloperRole": False,
                    "supportsReasoningEffort": True,
                    "maxTokensField": "max_tokens",
                },
            }
        )
    return {
        "providers": {
            PROVIDER_ID: {
                "name": PROVIDER_NAME,
                "baseUrl": BASE_URL,
                "api": "openai-completions",
                "apiKey": "$HYPER_API_KEY",
                "models": models,
            }
        }
    }


def pi_command(model_id: str) -> list[str]:
    return [
        str(PI),
        "--mode",
        "rpc",
        "--provider",
        PROVIDER_ID,
        "--model",
        model_id,
        "--thinking",
        "high",
        "--system-prompt",
        "You are a focused Roblox Luau source generator. Use the one available output tool and stop after the final source is written.",
        "--no-session",
        "--no-context-files",
        "--no-extensions",
        "--no-skills",
        "--no-prompt-templates",
        "--no-themes",
        "--no-approve",
        "--no-builtin-tools",
        "--tools",
        "write_source",
        "--extension",
        str(EXTENSION),
    ]


def terminate_process_tree(process: subprocess.Popen[str]) -> None:
    """Terminate the Pi process and descendants without leaving a worker behind."""
    if process.poll() is not None:
        return
    if os.name == "posix":
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGTERM)
    else:
        process.terminate()
    try:
        process.wait(timeout=5)
        return
    except subprocess.TimeoutExpired:
        pass
    if os.name == "posix":
        with contextlib.suppress(ProcessLookupError):
            os.killpg(process.pid, signal.SIGKILL)
    with contextlib.suppress(ProcessLookupError):
        process.kill()
    process.wait(timeout=5)


def run_pi(
    model: dict[str, Any],
    arm_dir: Path,
    max_output_tokens: int,
    *,
    prompt: str,
    timeout_seconds: float = PI_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    worker_dir = arm_dir / "worker"
    home_dir = arm_dir / "home"
    pi_dir = arm_dir / "pi-agent"
    source_path = arm_dir / "source" / "candidate.luau"
    worker_dir.mkdir(parents=True, exist_ok=True)
    home_dir.mkdir(parents=True, exist_ok=True)
    pi_dir.mkdir(parents=True, exist_ok=True)
    (arm_dir / "source").mkdir(parents=True, exist_ok=True)
    write_json(pi_dir / "models.json", model_config(max_output_tokens))
    (arm_dir / "prompt.txt").write_text(prompt, encoding="utf-8")
    command = pi_command(model["id"])
    write_json(
        arm_dir / "pi-command.json",
        {
            "command": command,
            "provider": PROVIDER_ID,
            "model": model["id"],
            "thinking": "high",
            "max_output_tokens": max_output_tokens,
            "tool_allowlist": ["write_source"],
        },
    )

    api_key = os.environ.get("HYPER_API_KEY")
    if not api_key:
        raise RuntimeError("HYPER_API_KEY is not present in the launcher environment")
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith("PI_")
        and key not in {"LLM_API_BASE", "LLM_API_KEY"}
        and not key.endswith(("_API_KEY", "_TOKEN", "_PASSWORD", "_SECRET"))
    }
    env.update(
        {
            "HOME": str(home_dir),
            "PI_CODING_AGENT_DIR": str(pi_dir),
            "PI_OFFLINE": "1",
            "PI_TELEMETRY": "0",
            "BLOX_SOURCE_OUTPUT": str(source_path),
            "HYPER_API_KEY": api_key,
        }
    )

    stdout_path = arm_dir / "pi.jsonl"
    stderr_path = arm_dir / "pi.stderr"
    settled = False
    terminal_event: str | None = None
    terminal_ok = False
    successful_write_source_calls = 0
    post_terminal_termination = False
    event_counts: dict[str, int] = {}
    tool_calls: list[dict[str, Any]] = []
    pi_errors: list[str] = []
    usage_totals = empty_usage_totals()
    assistant_messages = 0
    turn_starts = 0
    first_message_timestamp: int | float | None = None
    last_message_timestamp: int | float | None = None
    event_log_bytes = 0
    abort_reason: str | None = None
    deadline = time.monotonic() + timeout_seconds
    with stdout_path.open("w", encoding="utf-8") as stdout_log, tempfile.TemporaryFile(
        mode="w+", encoding="utf-8"
    ) as stderr_log:
        process = subprocess.Popen(
            command,
            cwd=worker_dir,
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=stderr_log,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        assert process.stdin is not None
        assert process.stdout is not None
        try:
            process.stdin.write(
                json.dumps({"id": "flight-prompt", "type": "prompt", "message": prompt}) + "\n"
            )
            process.stdin.flush()
        except (BrokenPipeError, OSError):
            abort_reason = "pi_prompt_broken_pipe"

        while abort_reason is None and time.monotonic() < deadline:
            ready, _, _ = select.select([process.stdout], [], [], 1.0)
            if not ready:
                if process.poll() is not None:
                    break
                continue
            line = process.stdout.readline()
            if not line:
                if process.poll() is not None:
                    break
                continue
            try:
                parsed_event = json.loads(line)
                event = (
                    parsed_event
                    if isinstance(parsed_event, dict)
                    else {"type": "non_object_json", "value_type": type(parsed_event).__name__}
                )
            except json.JSONDecodeError:
                event = {"type": "non_json_stdout"}
            compact = compact_pi_event(event)
            serialized = redact_text(json.dumps(compact, separators=(",", ":"))) + "\n"
            serialized_bytes = len(serialized.encode("utf-8"))
            if event_log_bytes + serialized_bytes > MAX_PI_EVENT_LOG_BYTES:
                abort_reason = "pi_event_log_limit"
                break
            stdout_log.write(serialized)
            stdout_log.flush()
            event_log_bytes += serialized_bytes
            event_type = str(event.get("type", "unknown"))
            event_counts[event_type] = event_counts.get(event_type, 0) + 1
            if event_type == "turn_start":
                turn_starts += 1
            message = event.get("message")
            if event_type == "message_end" and isinstance(message, dict) and message.get("role") == "assistant":
                assistant_messages += 1
                raw_usage = message.get("usage")
                if isinstance(raw_usage, dict):
                    add_usage_totals(usage_totals, raw_usage)
                timestamp = message.get("timestamp")
                if isinstance(timestamp, (int, float)):
                    first_message_timestamp = (
                        timestamp
                        if first_message_timestamp is None
                        else min(first_message_timestamp, timestamp)
                    )
                    last_message_timestamp = (
                        timestamp
                        if last_message_timestamp is None
                        else max(last_message_timestamp, timestamp)
                    )
            error_message = event.get("errorMessage")
            if not isinstance(error_message, str) and isinstance(message, dict):
                error_message = message.get("errorMessage")
            if isinstance(error_message, str) and error_message and error_message not in pi_errors:
                pi_errors.append(_text_tail(error_message))
            if event_type == "tool_execution_end":
                is_error = tool_result_is_error(event)
                if event.get("toolName") == "write_source" and is_error is False:
                    successful_write_source_calls += 1
                tool_calls.append(
                    {
                        "toolName": event.get("toolName"),
                        "isError": is_error,
                    }
                )
            if event_type == "agent_settled":
                settled = True
                terminal_event = event_type
                terminal_ok = successful_write_source_calls == 1 and source_path.is_file()
                if not terminal_ok:
                    abort_reason = "pi_terminal_without_valid_source"
                break
            if event_type == "agent_end" and event.get("willRetry") is False:
                terminal_event = event_type
                terminal_ok = successful_write_source_calls == 1 and source_path.is_file()
                if not terminal_ok:
                    abort_reason = "pi_terminal_without_valid_source"
                break

        if not terminal_ok and abort_reason is None and time.monotonic() >= deadline:
            abort_reason = "pi_timeout"
        if not terminal_ok and abort_reason is None and process.poll() is not None:
            abort_reason = "pi_process_exited"
        try:
            process.stdin.close()
        except (BrokenPipeError, OSError):
            pass
        if abort_reason is not None and process.poll() is None:
            terminate_process_tree(process)
        else:
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                post_terminal_termination = terminal_ok
                terminate_process_tree(process)
        with contextlib.suppress(OSError):
            process.stdout.close()
        stderr_log.flush()
        stderr_log.seek(0)
        stderr_path.write_text(redact_text(stderr_log.read()), encoding="utf-8")

    source_entries = sorted((arm_dir / "source").iterdir(), key=lambda path: path.name)
    files = [path for path in source_entries if path.is_file()]
    elapsed_seconds: float | None = None
    if first_message_timestamp is not None and last_message_timestamp is not None:
        elapsed_seconds = round((last_message_timestamp - first_message_timestamp) / 1000.0, 3)
    result = {
        "process_returncode": process.returncode,
        "settled": settled,
        "terminal_event": terminal_event,
        "terminal_ok": terminal_ok,
        "post_terminal_termination": post_terminal_termination,
        "max_output_tokens": max_output_tokens,
        "event_counts": event_counts,
        "tool_calls": tool_calls,
        "pi_errors": pi_errors,
        "usage": usage_totals,
        "usage_available": assistant_messages > 0 and usage_totals["total_tokens"] > 0,
        "assistant_messages": assistant_messages,
        "rounds": turn_starts or assistant_messages,
        "elapsed_seconds": elapsed_seconds,
        "source_files": [str(path) for path in files],
        "source_entries": [str(path) for path in source_entries],
        "event_log_format": "compact-jsonl",
        "event_log_bytes": event_log_bytes,
    }
    if abort_reason is not None:
        result["abort_reason"] = abort_reason
    if len(files) == 1 and files[0] == source_path:
        result["source_sha256"] = sha256_file(source_path)
        result["source_bytes"] = source_path.stat().st_size
    return result


def bridge_call(
    arm_dir: Path,
    sequence: int,
    request: dict[str, Any],
    *,
    timeout: float = BRIDGE_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    rsc_dir = arm_dir / "rsc"
    rsc_dir.mkdir(parents=True, exist_ok=True)
    request_path = rsc_dir / f"{sequence:02d}-request.json"
    response_path = rsc_dir / f"{sequence:02d}-response.json"
    write_json(request_path, request)
    command = ["uv", "run", "--project", str(RSC_PROJECT), "python", str(BRIDGE)]
    stderr_path = rsc_dir / f"{sequence:02d}-stderr"
    bridge_process = subprocess.Popen(
        command,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    try:
        stdout, stderr = bridge_process.communicate(
            input=json.dumps(request) + "\n",
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        with contextlib.suppress(Exception):
            terminate_process_tree(bridge_process)
        stdout, stderr = bridge_process.communicate()
        redacted_stdout = redact_text(stdout or "")
        redacted_stderr = redact_text(stderr or "")
        stderr_path.write_text(redacted_stderr, encoding="utf-8")
        response = {
            "ok": False,
            "error": {
                "type": "bridge_timeout",
                "message": f"bridge exceeded its {timeout:.1f}s timeout",
                "timeout_seconds": timeout,
                "stdout_tail": _redacted_tail(redacted_stdout),
                "stderr_tail": _redacted_tail(redacted_stderr),
            },
            "bridge_returncode": bridge_process.returncode,
        }
        write_json(response_path, response)
        raise RuntimeError(json.dumps(response, sort_keys=True))
    except BaseException as exc:
        with contextlib.suppress(Exception):
            terminate_process_tree(bridge_process)
        response = {
            "ok": False,
            "error": {
                "type": "bridge_interrupted",
                "message": f"bridge interrupted by {type(exc).__name__}",
            },
            "bridge_returncode": bridge_process.returncode,
        }
        write_json(response_path, response)
        raise
    completed_returncode = bridge_process.returncode
    redacted_stdout = redact_text(stdout or "")
    redacted_stderr = redact_text(stderr or "")
    stderr_path.write_text(redacted_stderr, encoding="utf-8")
    lines = [line for line in redacted_stdout.splitlines() if line.strip()]
    response: dict[str, Any]
    if not lines:
        response = {
            "ok": False,
            "error": {
                "type": "empty_bridge_output",
                "message": redacted_stderr.strip() or f"bridge exited {completed_returncode}",
            },
        }
    else:
        protocol_response: dict[str, Any] | None = None
        for line in reversed(lines):
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and isinstance(parsed.get("ok"), bool):
                protocol_response = parsed
                break
        if protocol_response is None:
            response = {
                "ok": False,
                "error": {
                    "type": "invalid_bridge_output",
                    "message": "bridge emitted no protocol response object",
                    "stdout_tail": _redacted_tail(redacted_stdout),
                },
            }
        else:
            response = protocol_response
    if completed_returncode != 0:
        response = {
            "ok": False,
            "error": {
                "type": "bridge_process_error",
                "message": f"bridge exited {completed_returncode}",
                "stdout_tail": _redacted_tail(redacted_stdout),
                "stderr_tail": _redacted_tail(redacted_stderr),
            },
        }
    response["bridge_returncode"] = completed_returncode
    write_json(response_path, response)
    if not response.get("ok"):
        raise RuntimeError(json.dumps(response, sort_keys=True))
    return response


def require_job_success(response: dict[str, Any], label: str) -> dict[str, Any]:
    finished = response.get("finished") if isinstance(response, dict) else None
    if not isinstance(finished, dict) or finished.get("state") != "succeeded":
        raise RuntimeError(f"{label} did not succeed: {json.dumps(response, sort_keys=True)}")
    return response


def require_luau_success(
    response: dict[str, Any],
    label: str,
    expected_marker: str | None = None,
) -> dict[str, Any]:
    require_job_success(response, label)
    finished = response["finished"]
    result = finished.get("result")
    value = result.get("value") if isinstance(result, dict) else None
    success = isinstance(value, dict) and (
        value.get("success") is True or (
            value.get("ok") is True and isinstance(value.get("result"), str)
        )
    )
    if not success:
        raise RuntimeError(f"{label} returned a failed Luau result: {json.dumps(response, sort_keys=True)}")
    if expected_marker is not None:
        raw_return = value.get("returnValue")
        if raw_return is None:
            raw_return = value.get("result")
        try:
            returned = json.loads(raw_return) if isinstance(raw_return, str) else None
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{label} returned invalid JSON marker data: {raw_return!r}") from exc
        if not isinstance(returned, dict) or returned.get("marker") != expected_marker:
            raise RuntimeError(
                f"{label} returned the wrong marker: expected {expected_marker!r}, "
                f"got {returned!r}"
            )
    return response


def require_screenshot_success(response: dict[str, Any], label: str) -> dict[str, Any]:
    """Require both a completed job and a successful screenshot payload."""
    require_job_success(response, label)
    finished = response["finished"]
    result = finished.get("result")
    artifact = result.get("artifact") if isinstance(result, dict) else None
    if not isinstance(result, dict) or result.get("ok") is not True or not isinstance(artifact, dict):
        raise RuntimeError(f"{label} returned a failed screenshot result: {json.dumps(response, sort_keys=True)}")
    if not artifact.get("path") or not artifact.get("sha256") or not isinstance(artifact.get("size"), int):
        raise RuntimeError(f"{label} returned incomplete screenshot metadata: {json.dumps(response, sort_keys=True)}")
    return response


def select_instance(status_response: dict[str, Any]) -> str:
    status = status_response.get("status") if isinstance(status_response, dict) else None
    instances = status.get("instances") if isinstance(status, dict) else None
    if not isinstance(instances, list):
        raise RuntimeError("RSC status returned a non-list instances field")
    edit = [item for item in instances if isinstance(item, dict) and item.get("role") == "edit"]
    if edit:
        candidates = edit
    else:
        candidates = [item for item in instances if isinstance(item, dict) and "role" not in item]
    if len(candidates) != 1:
        raise RuntimeError(f"expected exactly one current Studio instance, found {len(candidates)}")
    record = candidates[0]
    instance_id = record.get("id") or record.get("instance_id")
    if not isinstance(instance_id, str) or not instance_id:
        raise RuntimeError(f"current Studio instance has no usable id: {record}")
    return instance_id


def wait_for_instance(
    arm_dir: Path,
    sequence: int,
    *,
    timeout: float = READINESS_TIMEOUT_SECONDS,
    poll_interval: float = READINESS_POLL_INTERVAL_SECONDS,
    clock: Any = None,
    sleeper: Any = None,
) -> tuple[str, dict[str, Any], int, list[dict[str, Any]]]:
    """Poll status after worker refresh until one attached Studio instance is ready."""
    if timeout <= 0 or poll_interval <= 0:
        raise ValueError("readiness timeout and poll interval must be greater than zero")
    clock_fn = time.monotonic if clock is None else clock
    sleep_fn = time.sleep if sleeper is None else sleeper
    deadline = clock_fn() + timeout
    attempts: list[dict[str, Any]] = []
    attempt = 0
    last_error = "unknown readiness failure"

    while True:
        attempt += 1
        request_sequence = sequence
        sequence += 1
        try:
            status_response = bridge_call(
                arm_dir,
                request_sequence,
                {"operation": "status"},
                timeout=READINESS_BRIDGE_TIMEOUT_SECONDS,
            )
            instance_id = select_instance(status_response)
        except RuntimeError as exc:
            last_error = _text_tail(redact_text(str(exc)))
            attempts.append({"attempt": attempt, "state": "not_ready", "error": last_error})
        else:
            attempts.append({"attempt": attempt, "state": "ready", "instance_id": instance_id})
            return instance_id, status_response, sequence, attempts

        remaining = deadline - clock_fn()
        if remaining <= 0:
            raise RuntimeError(
                f"Studio readiness timed out after {timeout:.1f}s; "
                f"last status failure: {last_error}"
            )
        sleep_fn(min(poll_interval, remaining))


def best_effort_cleanup(
    arm_dir: Path,
    sequence: int,
    instance_id: str,
    manifest: dict[str, Any],
) -> None:
    """Remove partial candidate state without masking the original failure."""
    cleanup_sequence = sequence + 1
    try:
        cleanup = bridge_call(
            arm_dir,
            cleanup_sequence,
            {
                "operation": "exec",
                "instance_id": instance_id,
                "target": "edit",
                "code": RESET_CODE,
            },
        )
        require_luau_success(cleanup, "failure cleanup", "bloxbench-reset")
        manifest["cleanup"] = cleanup
    except Exception as exc:
        manifest["cleanup_error"] = {
            "type": type(exc).__name__,
            "message": _text_tail(redact_text(str(exc))),
        }


@contextlib.contextmanager
def shutdown_signal_handler() -> Iterator[None]:
    """Route SIGTERM through run_arm's bounded cleanup path."""
    previous = signal.getsignal(signal.SIGTERM)

    def handle(signum: int, _frame: Any) -> None:
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, handle)
    try:
        yield
    finally:
        signal.signal(signal.SIGTERM, previous)


def run_arm(
    arm: str,
    flight_dir: Path,
    *,
    prompt: str,
    prompt_path: Path,
    source_only: bool = False,
    max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    provenance: dict[str, Any] | None = None,
) -> ArmResult:
    model = MODELS[arm]
    arm_dir = flight_dir / arm
    arm_dir.mkdir(parents=True, exist_ok=False)
    manifest: dict[str, Any] = {
        "kind": "bloxbench-stability-test-flight",
        "objective": "stability-and-consistency",
        "arm": arm,
        "provider": PROVIDER_NAME,
        "provider_id": PROVIDER_ID,
        "base_url": BASE_URL,
        "model": model["id"],
        "model_name": model["name"],
        "pi_version": "0.83.0",
        "prompt_path": str(prompt_path.relative_to(ROOT)),
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "place": str(PLACE.relative_to(ROOT)),
        "prompt_mode": "file-backed",
        "thinking": "high",
        "max_output_tokens": max_output_tokens,
        "candidate_has_rsc_access": False,
        "candidate_receives_screenshots": False,
        "one_source_file_contract": True,
        "provenance": provenance if provenance is not None else build_provenance(),
        "started_at": utc_now(),
    }
    write_json(arm_dir / "manifest.json", manifest)
    sequence = 0
    instance_id: str | None = None
    try:
        pi_result = run_pi(model, arm_dir, max_output_tokens, prompt=prompt)
        manifest["pi"] = pi_result
        terminal_ok = pi_result.get("terminal_ok")
        process_ok = pi_result.get("process_returncode") == 0 or (
            terminal_ok is True and pi_result.get("post_terminal_termination") is True
        )
        if terminal_ok is not True or not process_ok:
            raise RuntimeError(f"Pi process contract failed: {json.dumps(pi_result, sort_keys=True)}")
        source_path = arm_dir / "source" / "candidate.luau"
        source_entries = sorted((arm_dir / "source").iterdir(), key=lambda path: path.name)
        if not source_path.is_file() or source_entries != [source_path]:
            raise RuntimeError(f"source output contract failed: {json.dumps(pi_result, sort_keys=True)}")
        manifest["source_sha256"] = sha256_file(source_path)
        manifest["source_bytes"] = source_path.stat().st_size

        if source_only:
            manifest["studio_execution"] = "not-run"
            manifest["state"] = "source_only_completed"
            manifest["completed_at"] = utc_now()
            write_json(arm_dir / "manifest.json", manifest)
            return ArmResult(
                arm=arm,
                state="source_only_completed",
                source_path=str(source_path),
            )

        pre_refresh_error: str | None = None
        try:
            instance_id, status_response, sequence, pre_refresh_attempts = wait_for_instance(
                arm_dir,
                sequence,
                timeout=PRE_REFRESH_READINESS_TIMEOUT_SECONDS,
            )
            readiness_attempts = pre_refresh_attempts
            manifest["worker_refresh"] = {
                "skipped": True,
                "reason": "existing_mcp_session_ready",
            }
            manifest["readiness_phase"] = "pre_refresh"
        except RuntimeError as exc:
            pre_refresh_error = _text_tail(redact_text(str(exc)))
            worker_refresh = bridge_call(
                arm_dir,
                sequence,
                {"operation": "refresh_worker"},
                timeout=REFRESH_BRIDGE_TIMEOUT_SECONDS,
            )
            sequence += 1
            manifest["worker_refresh"] = worker_refresh
            try:
                instance_id, status_response, sequence, readiness_attempts = wait_for_instance(
                    arm_dir,
                    sequence,
                )
                manifest["readiness_phase"] = "post_refresh"
            except RuntimeError as readiness_exc:
                readiness_error = _text_tail(redact_text(str(readiness_exc)))
                log_discovery = bridge_call(arm_dir, sequence, {"operation": "discover_log_instance"})
                sequence += 1
                instance_id = log_discovery["instance_id"]
                manifest["log_instance_discovery"] = log_discovery
                status_response = {"status": {"instances": []}}
                readiness_attempts = [{"state": "timed_out", "error": readiness_error}]
                manifest["readiness_phase"] = "log_fallback"
            else:
                readiness_error = None
        else:
            readiness_error = None
        if pre_refresh_error is not None:
            manifest["pre_refresh_readiness_error"] = pre_refresh_error
        manifest["readiness"] = {
            "timeout_seconds": READINESS_TIMEOUT_SECONDS,
            "poll_interval_seconds": READINESS_POLL_INTERVAL_SECONDS,
            "attempts": readiness_attempts,
        }
        if readiness_error is not None:
            manifest["readiness_error"] = readiness_error
        manifest["instance_id"] = instance_id
        manifest["status_before_bootstrap"] = status_response

        bootstrap: dict[str, Any] | None = None
        bootstrap_attempts: list[dict[str, Any]] = []
        for bootstrap_attempt in range(2):
            try:
                bootstrap = bridge_call(
                    arm_dir,
                    sequence,
                    {
                        "operation": "exec",
                        "instance_id": instance_id,
                        "target": "edit",
                        "code": BOOTSTRAP_CODE,
                        "timeout": 120,
                    },
                )
                sequence += 1
                require_luau_success(bootstrap, "RSC bootstrap", "bloxbench-rsc-bootstrap")
                bootstrap_attempts.append(
                    {"attempt": bootstrap_attempt + 1, "instance_id": instance_id, "state": "succeeded"}
                )
                break
            except RuntimeError as exc:
                bootstrap_attempts.append(
                    {
                        "attempt": bootstrap_attempt + 1,
                        "instance_id": instance_id,
                        "state": "failed",
                        "error": _text_tail(redact_text(str(exc))),
                    }
                )
                if bootstrap_attempt == 1:
                    raise
                retry_status = bridge_call(arm_dir, sequence, {"operation": "status"})
                sequence += 1
                try:
                    retry_instance_id = select_instance(retry_status)
                except RuntimeError:
                    retry_log_discovery = bridge_call(
                        arm_dir,
                        sequence,
                        {"operation": "discover_log_instance"},
                    )
                    sequence += 1
                    retry_instance_id = retry_log_discovery["instance_id"]
                    manifest["bootstrap_retry_log_discovery"] = retry_log_discovery
                manifest["bootstrap_retry_status"] = retry_status
                if retry_instance_id == instance_id:
                    raise
                manifest["bootstrap_retry_from"] = instance_id
                instance_id = retry_instance_id
                manifest["instance_id"] = instance_id
        if bootstrap is None:
            raise RuntimeError("RSC bootstrap did not produce a response")
        manifest["bootstrap_attempts"] = bootstrap_attempts
        manifest["bootstrap"] = bootstrap

        reset = bridge_call(
            arm_dir,
            sequence,
            {"operation": "exec", "instance_id": instance_id, "target": "edit", "code": RESET_CODE},
        )
        sequence += 1
        require_luau_success(reset, "reset", "bloxbench-reset")
        manifest["reset"] = reset

        execute = bridge_call(
            arm_dir,
            sequence,
            {
                "operation": "exec",
                "instance_id": instance_id,
                "target": "edit",
                "code": source_path.read_text(encoding="utf-8"),
                "timeout": 180,
            },
        )
        sequence += 1
        require_luau_success(execute, "candidate execution")
        manifest["execution"] = execute

        validation = bridge_call(
            arm_dir,
            sequence,
            {"operation": "exec", "instance_id": instance_id, "target": "edit", "code": VALIDATE_CODE},
        )
        sequence += 1
        require_luau_success(validation, "validation", "bloxbench-validation")
        manifest["validation"] = validation

        screenshots: dict[str, str] = {}
        for angle, camera_code in CAMERA_CODES.items():
            camera = bridge_call(
                arm_dir,
                sequence,
                {"operation": "exec", "instance_id": instance_id, "target": "edit", "code": camera_code},
            )
            sequence += 1
            require_luau_success(camera, f"camera {angle}", "bloxbench-camera")
            screenshot = bridge_call(
                arm_dir,
                sequence,
                {
                    "operation": "screenshot",
                    "instance_id": instance_id,
                    "arguments": {"format": "png"},
                    "artifact_dir": str(arm_dir / "screenshots" / angle),
                },
            )
            sequence += 1
            require_screenshot_success(screenshot, f"screenshot {angle}")
            artifact_path = screenshot.get("artifact_path")
            if not isinstance(artifact_path, str) or not Path(artifact_path).is_file():
                raise RuntimeError(f"screenshot {angle} returned no local artifact: {screenshot}")
            artifact = ((screenshot.get("finished") or {}).get("result") or {}).get("artifact") or {}
            if (
                sha256_file(Path(artifact_path)) != artifact.get("sha256")
                or Path(artifact_path).stat().st_size != artifact.get("size")
            ):
                raise RuntimeError(f"screenshot {angle} local artifact metadata mismatch: {screenshot}")
            screenshots[angle] = artifact_path
        manifest["screenshots"] = screenshots
        manifest["state"] = "completed"
        manifest["completed_at"] = utc_now()
        write_json(arm_dir / "manifest.json", manifest)
        return ArmResult(
            arm=arm,
            state="completed",
            source_path=str(source_path),
            instance_id=instance_id,
            screenshots=screenshots,
        )
    except BaseException as exc:
        if instance_id is not None and not source_only:
            best_effort_cleanup(arm_dir, sequence, instance_id, manifest)
        manifest["state"] = "failed"
        manifest["error"] = {
            "type": type(exc).__name__,
            "message": _text_tail(redact_text(str(exc))),
        }
        manifest["completed_at"] = utc_now()
        write_json(arm_dir / "manifest.json", manifest)
        if isinstance(exc, (KeyboardInterrupt, SystemExit)):
            raise
        return ArmResult(
            arm=arm,
            state="failed",
            source_path=str(arm_dir / "source" / "candidate.luau")
            if (arm_dir / "source" / "candidate.luau").is_file()
            else None,
            instance_id=manifest.get("instance_id"),
            error=manifest["error"],
        )


def validate_runtime_inputs(*, source_only: bool, prompt_path: Path) -> None:
    required_files = [
        ("Pi executable", PI),
        ("prompt file", prompt_path),
        ("place file", PLACE),
        ("Pi output extension", EXTENSION),
    ]
    if not source_only:
        required_files.append(("RSC bridge", BRIDGE))
    missing = [f"{label}: {path}" for label, path in required_files if not path.is_file()]
    if missing:
        raise SystemExit("required flight file is missing or not regular:\n" + "\n".join(missing))
    if not source_only and not RSC_PROJECT.is_dir():
        raise SystemExit(f"RSC project directory not found: {RSC_PROJECT}")
    if not os.environ.get("HYPER_API_KEY"):
        raise SystemExit("HYPER_API_KEY must be supplied by the caller and is never written to artifacts")


def write_flight_summary(
    flight_dir: Path,
    arms: tuple[str, ...],
    results: list[ArmResult],
    *,
    source_only: bool,
    flight_error: BaseException | None = None,
) -> dict[str, Any]:
    successful_states = {"completed", "source_only_completed"}
    summary: dict[str, Any] = {
        "flight_dir": str(flight_dir),
        "arms": list(arms),
        "results": [result.__dict__ for result in results],
        "successful_arms": [result.arm for result in results if result.state in successful_states],
        "studio_completed_arms": [result.arm for result in results if result.state == "completed"],
        "failed_arms": [result.arm for result in results if result.state not in successful_states],
        "unattempted_arms": list(arms[len(results) :]),
        "mode": "source-only" if source_only else "full-parent-owned",
        "orchestration_state": "interrupted" if flight_error is not None else "completed",
        "note": "No scoring, judging, ranking, or model comparison was performed.",
        "completed_at": utc_now(),
    }
    if flight_error is not None:
        summary["flight_error"] = {
            "type": type(flight_error).__name__,
            "message": _text_tail(redact_text(str(flight_error))),
        }
    write_json(flight_dir / "summary.json", summary)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the unscored BloxBench stability test flight")
    parser.add_argument(
        "--source-only",
        action="store_true",
        help="run the selected Pi source-generation arm(s) but do not touch Roblox Studio",
    )
    parser.add_argument(
        "--arm",
        choices=("flash", "pro"),
        help="run only this model arm; omit to run both arms",
    )
    parser.add_argument(
        "--prompt-file",
        type=Path,
        default=CALIBRATION_PROMPT,
        help="task-specific source-generation prompt; default is the legacy calibration prompt",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=int,
        default=DEFAULT_MAX_OUTPUT_TOKENS,
        help="per-request output/reasoning ceiling (default: 16000)",
    )
    args = parser.parse_args()
    prompt_path = args.prompt_file.resolve()
    prompt = prompt_path.read_text(encoding="utf-8")
    if not prompt.strip():
        parser.error("--prompt-file must not be empty")
    if args.max_output_tokens < 1 or args.max_output_tokens > MAX_MAX_OUTPUT_TOKENS:
        parser.error(f"--max-output-tokens must be between 1 and {MAX_MAX_OUTPUT_TOKENS}")
    arms = (args.arm,) if args.arm else ("flash", "pro")
    validate_runtime_inputs(source_only=args.source_only, prompt_path=prompt_path)
    provenance = build_provenance(prompt_path)

    with shutdown_signal_handler(), flight_lock(ROOT / "results"):
        flight_dir = create_flight_dir(ROOT / "results")
        write_json(
            flight_dir / "flight.json",
            {
                "kind": "bloxbench-stability-test-flight",
                "objective": "stability-and-consistency",
                "provider": PROVIDER_NAME,
                "provider_id": PROVIDER_ID,
                "base_url": BASE_URL,
                "models": {arm: item["id"] for arm, item in MODELS.items()},
                "arms": list(arms),
                "prompt_path": str(prompt_path.relative_to(ROOT)),
                "place": str(PLACE.relative_to(ROOT)),
                "pi_version": "0.83.0",
                "thinking": "high",
                "max_output_tokens": args.max_output_tokens,
                "studio_execution": "not-run" if args.source_only else "parent-owned",
                "prompt_mode": "file-backed",
                "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                "provenance": provenance,
                "credential_source": "process environment HYPER_API_KEY",
                "started_at": utc_now(),
            },
        )

        results: list[ArmResult] = []
        flight_error: BaseException | None = None
        try:
            for arm in arms:
                results.append(
                    run_arm(
                        arm,
                        flight_dir,
                        prompt=prompt,
                        prompt_path=prompt_path,
                        source_only=args.source_only,
                        max_output_tokens=args.max_output_tokens,
                        provenance=provenance,
                    )
                )
        except BaseException as exc:
            flight_error = exc
            raise
        finally:
            summary = write_flight_summary(
                flight_dir,
                arms,
                results,
                source_only=args.source_only,
                flight_error=flight_error,
            )
            print(json.dumps(summary, indent=2, sort_keys=True))
        return 0 if all(result.state in {"completed", "source_only_completed"} for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
