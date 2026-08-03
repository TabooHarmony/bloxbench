#!/usr/bin/env python3
"""Run one BloxBench candidate through reset, probes, capture, and review packaging.

This is deliberately parent-owned. It consumes an already-produced Luau source file;
it does not ask a model for code, repair a candidate, or score visual quality.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import hashlib
import json
import os
import re
import shutil
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.benchmark.fixture_contract import SCREENSHOT_ANGLE_NAMES, Fixture, parse_fixture  # noqa: E402
from scripts.benchmark.evaluation_bundle import (  # noqa: E402
    artifact_record,
    copy_generation_bundle,
    sha256_file as bundle_sha256_file,
    summarize_generation,
    validate_place_file,
    write_bundle_readme,
    write_evaluation_summary,
)
from scripts.test_flight import run_test_flight as qualified  # noqa: E402


RUNNER_VERSION = "bloxbench-review-runner-v2"
DEFAULT_OUTPUT_ROOT = ROOT / "results" / "evaluations"
INSTANCE_PATTERN = re.compile(r"^anon:[0-9a-f-]{36}$")
SENSITIVE_SOURCE = re.compile(
    r"(?i)(api[_-]?key|access[_-]?token|secret[_-]?key|password|authorization\s*[:=]|begin [^-]+ private key)"
)

RESET_CODE = r'''local removed = 0
local function remove(parent, name)
    local item = parent:FindFirstChild(name)
    if item then
        item:Destroy()
        removed += 1
    end
end
remove(workspace, "BloxBenchCandidate")
remove(workspace, "_BloxBenchCapture")
remove(game:GetService("ReplicatedStorage"), "_BloxBenchFixtureCode")
remove(game:GetService("ReplicatedStorage"), "_BloxBenchRuntime")
remove(game:GetService("ServerScriptService"), "_BloxBenchRuntime")
local selection = game:GetService("Selection")
selection:Set({})
local camera = workspace.CurrentCamera
if camera then
    camera.CameraType = Enum.CameraType.Custom
end
return {marker = "bloxbench-reset", removed = removed}
'''

BOOTSTRAP_CODE = 'return {marker = "bloxbench-rsc-bootstrap", value = 1}'

CAMERA_ANGLES: dict[str, tuple[int, int, int]] = {
    "hero": (13, 9, 15),
    "front": (0, 8, 18),
    "side": (18, 8, 0),
    "rear": (-15, 9, -14),
    "top": (0, 20, 1),
}


def camera_code(angle: str = "hero") -> str:
    safe_angle = angle if angle in CAMERA_ANGLES else "hero"
    x, y, z = CAMERA_ANGLES[safe_angle]
    return f'''local candidate = workspace:FindFirstChild("BloxBenchCandidate")
assert(candidate and candidate:IsA("Model"), "BloxBenchCandidate model is missing")
local camera = workspace.CurrentCamera
assert(camera, "CurrentCamera is unavailable")
local boundsCFrame, boundsSize = candidate:GetBoundingBox()
local target = boundsCFrame.Position
local extent = math.max(boundsSize.X, math.max(boundsSize.Y, boundsSize.Z))
local distance = (extent * 0.5 / math.tan(math.rad(camera.FieldOfView) * 0.5)) * 1.8
camera.CameraType = Enum.CameraType.Scriptable
camera.CFrame = CFrame.lookAt(target + Vector3.new({x}, {y}, {z}).Unit * distance, target)
task.wait(1.0)
return {{marker = "bloxbench-camera", angle = "{safe_angle}", target = {{x = target.X, y = target.Y, z = target.Z}}}}
'''


CAMERA_CODE = camera_code()


def screenshot_angle_names(fixture: Fixture) -> tuple[str, ...]:
    primary = fixture.screenshot_primary if fixture.screenshot_primary in CAMERA_ANGLES else "hero"
    names = [primary]
    for angle in SCREENSHOT_ANGLE_NAMES:
        if len(names) >= fixture.screenshot_angles:
            break
        if angle not in names:
            names.append(angle)
    return tuple(names)


@dataclass
class RunResult:
    run_dir: Path
    state: str
    evidence_state: str
    manifest: dict[str, Any]


@dataclass
class ReviewRun:
    fixture: Fixture
    source_path: Path
    run_dir: Path
    instance_id: str | None = None
    sequence: int = 0
    manifest: dict[str, Any] = field(default_factory=dict)
    execution_started: bool = False
    _lock_handle: Any = None

    def next_sequence(self) -> int:
        value = self.sequence
        self.sequence += 1
        return value

    def write_manifest(self) -> None:
        atomic_json(self.run_dir / "manifest.json", self.manifest)

    def bridge(self, request: dict[str, Any], *, timeout: float = 300.0) -> dict[str, Any]:
        started = time.perf_counter()
        sequence = self.next_sequence()
        response = qualified.bridge_call(
            self.run_dir,
            sequence,
            request,
            timeout=timeout,
        )
        elapsed_seconds = round(time.perf_counter() - started, 3)
        record = {
            "sequence": sequence,
            "operation": request.get("operation"),
            "target": request.get("target"),
            "job_id": ((response.get("finished") or {}).get("id") or (response.get("submitted") or {}).get("id")),
            "response_ok": response.get("ok"),
            "application_ok": response.get("application_ok"),
            "elapsed_seconds": elapsed_seconds,
        }
        if isinstance(request.get("code"), str):
            record["code_sha256"] = bundle_sha256_file_from_text(request["code"])
        self.manifest.setdefault("operations", []).append(record)
        trace_path = self.run_dir / "trace" / "operations.jsonl"
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        with trace_path.open("a", encoding="utf-8") as trace:
            trace.write(json.dumps(record, sort_keys=True) + "\n")
        self.manifest.setdefault("trace", {})["operations_path"] = str(trace_path)
        self.write_manifest()
        return response

    def require_luau(self, response: dict[str, Any], label: str, marker: str) -> dict[str, Any]:
        qualified.require_luau_success(response, label, marker)
        finished = response["finished"]
        result = finished["result"]
        value = result["value"]
        raw = value.get("returnValue")
        if raw is None:
            raw = value.get("result")
        if not isinstance(raw, str):
            raise RuntimeError(f"{label} did not return a JSON payload")
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{label} returned invalid JSON: {raw!r}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError(f"{label} returned a non-object payload")
        nested = payload.get("payload")
        if isinstance(nested, str):
            with contextlib.suppress(json.JSONDecodeError):
                decoded = json.loads(nested)
                payload["observation"] = decoded
        return payload

    def require_remote(self, response: dict[str, Any], label: str) -> dict[str, Any]:
        if response.get("ok") is not True or response.get("application_ok") is not True:
            raise RuntimeError(f"{label} did not succeed: {json.dumps(response, sort_keys=True, default=str)}")
        return response


def compact_job(response: dict[str, Any]) -> dict[str, Any]:
    """Reduce a raw RSC job response to the few fields a human cares about.

    The full raw submitted/finished blobs (with all Luau source, worker ids,
    timestamps, retry counters) stay in the run's rsc/ trace directory; the
    manifest should only carry the outcome.
    """
    finished = response.get("finished") if isinstance(response, dict) else None
    result = finished.get("result") if isinstance(finished, dict) else None
    value = result.get("value") if isinstance(result, dict) else None
    return_value = ""
    if isinstance(value, dict):
        raw = value.get("returnValue") or value.get("result")
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                return_value = parsed if isinstance(parsed, (dict, list)) else raw
            except json.JSONDecodeError:
                return_value = raw[:200]
    return {
        "ok": response.get("ok") is True,
        "application_ok": response.get("application_ok") is True,
        "job_id": finished.get("id") if isinstance(finished, dict) else None,
        "state": finished.get("state") if isinstance(finished, dict) else None,
        "result": return_value,
    }


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bundle_sha256_file_from_text(value: str) -> str:
    return sha256_bytes(value.encode("utf-8"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def png_dimensions(path: Path) -> tuple[int, int] | None:
    data = path.read_bytes()
    if len(data) < 24 or data[:8] != b"\\x89PNG\\r\\n\\x1a\\n" or data[12:16] != b"IHDR":
        return None
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    return width, height


def atomic_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def lua_long_string(value: str) -> str:
    for count in range(0, 32):
        opening = "[" + ("=" * count) + "["
        closing = "]" + ("=" * count) + "]"
        if closing not in value:
            return opening + value + closing
    raise ValueError("fixture/source contains too many Lua long-string delimiters")


def fixture_module_code(source: str) -> str:
    return f'''local rs = game:GetService("ReplicatedStorage")
local old = rs:FindFirstChild("_BloxBenchFixtureCode")
if old then old:Destroy() end
local module = Instance.new("ModuleScript")
module.Name = "_BloxBenchFixtureCode"
module.Source = {lua_long_string(source)}
module.Parent = rs
local ok, value = pcall(require, module)
assert(ok and type(value) == "table", "fixture module failed to load: " .. tostring(value))
return {{marker = "bloxbench-fixture-installed", hooks = #module:GetChildren()}}
'''


def hook_code(hook: str, argument: str | None = None) -> str:
    argument_lua = "nil" if argument is None else json.dumps(argument)
    return f'''local rs = game:GetService("ReplicatedStorage")
local module = rs:FindFirstChild("_BloxBenchFixtureCode")
assert(module and module:IsA("ModuleScript"), "fixture module is missing")
local ok, eval = pcall(require, module)
assert(ok and type(eval) == "table", "fixture require failed: " .. tostring(eval))
local fn = eval[{json.dumps(hook)}]
assert(type(fn) == "function", "fixture hook is missing: {hook}")
local called, value = xpcall(function()
    return fn({argument_lua})
end, function(err)
    return debug.traceback(tostring(err), 2)
end)
assert(called, value)
local encodedOk, payload = pcall(function()
    return game:GetService("HttpService"):JSONEncode(value)
end)
if not encodedOk then
    payload = tostring(value)
end
return {{marker = "bloxbench-hook", hook = {json.dumps(hook)}, payload = payload}}
'''


def screenshot_local_artifact(response: dict[str, Any], label: str) -> str:
    qualified.require_screenshot_success(response, label)
    artifact_path = response.get("artifact_path")
    if not isinstance(artifact_path, str) or not Path(artifact_path).is_file():
        raise RuntimeError(f"{label} returned no local artifact")
    artifact = ((response.get("finished") or {}).get("result") or {}).get("artifact") or {}
    path = Path(artifact_path)
    if sha256_file(path) != artifact.get("sha256") or path.stat().st_size != artifact.get("size"):
        raise RuntimeError(f"{label} local artifact metadata mismatch")
    return artifact_path


def store_screenshot(
    response: dict[str, Any],
    label: str,
    destination: Path,
    *,
    scope: str,
) -> dict[str, Any]:
    source = Path(screenshot_local_artifact(response, label))
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    record = artifact_record(destination, kind="screenshot", scope=scope)
    dimensions = png_dimensions(destination)
    if dimensions is not None:
        record["width"], record["height"] = dimensions
    return record


def runtime_client_role(response: dict[str, Any]) -> str:
    status = response.get("status") if isinstance(response, dict) else None
    instances = status.get("instances") if isinstance(status, dict) else None
    roles = [
        item.get("role")
        for item in instances or []
        if isinstance(item, dict) and isinstance(item.get("role"), str) and item["role"].startswith("client-")
    ]
    if len(roles) != 1 or not isinstance(roles[0], str):
        raise RuntimeError(f"expected exactly one active runtime client role, found {roles!r}")
    return roles[0]


def copy_video(video: Path, destination: Path, proof_path: Path | None) -> dict[str, Any]:
    if not video.is_file():
        raise FileNotFoundError(video)
    if proof_path is None or not proof_path.is_file():
        raise ValueError(
            "video evidence is withheld unless a viewport-only capture proof is supplied; "
            "desktop-level recordings are not reviewable"
        )
    try:
        proof = json.loads(proof_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid video proof JSON: {proof_path}") from exc
    if not isinstance(proof, dict):
        raise ValueError("video proof must be a JSON object")
    source_sha256 = sha256_file(video)
    if proof.get("scope") != "roblox-viewport":
        raise ValueError("video proof scope must be roblox-viewport")
    if proof.get("desktop_visible") is not False or proof.get("console_visible") is not False:
        raise ValueError("video proof does not establish a clean viewport-only capture")
    if proof.get("video_sha256") != source_sha256:
        raise ValueError("video proof SHA-256 does not match the supplied video")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(video, destination)
    return {
        **artifact_record(destination, kind="video", scope="roblox-viewport"),
        "reviewable": True,
        "proof": artifact_record(proof_path, kind="video-capture-proof"),
    }


def validate_source(source_path: Path) -> None:
    if not source_path.is_file():
        raise FileNotFoundError(source_path)
    if source_path.stat().st_size == 0:
        raise ValueError("candidate source is empty")
    source = source_path.read_text(encoding="utf-8")
    if SENSITIVE_SOURCE.search(source):
        raise ValueError("candidate source contains a credential-like token or authorization field")


def initial_manifest(
    fixture: Fixture,
    source_path: Path,
    run_dir: Path,
    *,
    generation: dict[str, Any],
) -> dict[str, Any]:
    runner_path = Path(__file__).resolve()
    is_model = generation.get("is_model_evaluation") is True
    return {
        "framework": RUNNER_VERSION,
        "evaluation_id": run_dir.name,
        "state": "not_run",
        "evidence_state": "not run",
        "created_at": utc_now(),
        "run_dir": str(run_dir.resolve()),
        "fixture": {
            "id": fixture.fixture_id,
            "scenario_name": fixture.scenario_name,
            "path": str(fixture.path.resolve()),
            "sha256": fixture.sha256,
            "prompt_sha256": sha256_bytes(fixture.prompt.encode("utf-8")),
            "place": fixture.place,
            "track": fixture.track,
            "states": list(fixture.states),
            "runtime": fixture.runtime,
            "semantic_components": list(fixture.semantic_components),
            "evidence": fixture.evidence,
        },
        "candidate": {
            "origin": "model" if is_model else "unattributed",
            "is_model_evaluation": is_model,
            "label": "model candidate" if is_model else "synthetic_or_unattributed_candidate",
        },
        "source": {
            "path": str(source_path.resolve()),
            "sha256": sha256_file(source_path),
            "bytes": source_path.stat().st_size,
        },
        "runner": {"path": str(runner_path), "sha256": sha256_file(runner_path)},
        "generation": generation,
        "place": None,
        "operations": [],
        "trace": {},
        "readbacks": {},
        "screenshot_contract": {
            "type": fixture.screenshot_type,
            "angles": fixture.screenshot_angles,
            "angle_names": list(screenshot_angle_names(fixture)),
            "primary": fixture.screenshot_primary,
            "states": list(fixture.states),
        },
        "screenshot_metadata": {},
        "screenshots": {},
        "videos": [],
        "human_review": {
            "protocol": "blind-pairwise",
            "allowed_labels": ["A better", "B better", "tie", "both bad"],
            "quality_label_assigned": False,
        },
    }


def write_review_packet(run: ReviewRun) -> None:
    manifest = run.manifest
    evidence = manifest.get("evidence_state", "not run")
    lines = [
        "# BloxBench human review packet",
        "",
        f"- fixture: `{run.fixture.fixture_id}`",
        f"- scenario: {run.fixture.scenario_name}",
        f"- run state: `{manifest.get('state')}`",
        f"- evidence state: `{evidence}`",
        f"- candidate source: `{manifest['source']['sha256']}`",
        f"- candidate origin: `{(manifest.get('candidate') or {}).get('origin', 'unknown')}`",
        f"- generated place: `{bool((manifest.get('place') or {}).get('generated'))}`",
        "",
        "## generation metadata",
        "",
    ]
    generation = manifest.get("generation") or {}
    if generation.get("is_model_evaluation"):
        lines.extend(
            [
                f"- model: `{generation.get('model_name') or generation.get('model', 'unknown')}`",
                f"- provider: `{generation.get('provider') or generation.get('provider_id', 'unknown')}`",
                f"- route: `{generation.get('route') or generation.get('base_url', 'unknown')}`",
                f"- rounds: `{generation.get('rounds', 'unknown')}`",
                f"- input tokens: `{(generation.get('usage') or {}).get('input_tokens', 'unknown')}`",
                f"- output tokens: `{(generation.get('usage') or {}).get('output_tokens', 'unknown')}`",
                f"- elapsed seconds: `{generation.get('elapsed_seconds', 'unknown')}`",
            ]
        )
    else:
        lines.append("- no model generation manifest supplied; this is not a model-evaluation result")
    lines.extend(
        [
        "",
        "## automated observations",
        "",
        "These are execution and evidence facts only. They are not quality scores.",
        "",
        ]
    )
    readbacks = manifest.get("readbacks") or {}
    if readbacks:
        for name, value in readbacks.items():
            lines.append(f"- `{name}`: `{json.dumps(value, sort_keys=True, default=str)}`")
    else:
        lines.append("- none recorded")
    lines.extend(["", "## evidence files", ""])
    for name, value in (manifest.get("screenshots") or {}).items():
        lines.append(f"- screenshot `{name}`: `{value}`")
    for value in manifest.get("videos") or []:
        lines.append(f"- video: `{value.get('path')}`")
    if not (manifest.get("screenshots") or manifest.get("videos")):
        lines.append("- none")
    lines.extend(
        [
            "",
            "## human protocol",
            "",
            "Compare matched A/B outputs using exactly one label: `A better`, `B better`, `tie`, or `both bad`.",
            "Judge visual quality, coherence, completeness, legibility, and gameplay/animation feel from the attached evidence.",
            "Do not infer quality from the automated observations above.",
        ]
    )
    (run.run_dir / "review_packet.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _set_failure(manifest: dict[str, Any], exc: BaseException, *, execution_started: bool) -> None:
    manifest["state"] = "failed"
    manifest["evidence_state"] = "ran but evidence invalid" if execution_started else "not run"
    manifest["error"] = {
        "type": type(exc).__name__,
        "message": qualified._text_tail(qualified.redact_text(str(exc))),
    }
    manifest["completed_at"] = utc_now()


def create_run_dir(output_root: Path, fixture_id: str) -> Path:
    fixture_root = output_root / fixture_id.replace(".", "_")
    fixture_root.mkdir(parents=True, exist_ok=True)
    for _ in range(10):
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        candidate = fixture_root / f"evaluation-{stamp}-{uuid.uuid4().hex[:8]}"
        if not candidate.exists():
            return candidate
    raise RuntimeError("could not allocate a unique evaluation directory")


def run_review(
    fixture: Fixture,
    source_path: Path,
    run_dir: Path,
    *,
    instance_id: str | None = None,
    plan_only: bool = False,
    videos: tuple[Path, ...] = (),
    video_proofs: tuple[Path, ...] = (),
    place_file: Path | None = None,
    generation_dir: Path | None = None,
    readiness_timeout: float = 120.0,
    require_video: bool = False,
) -> RunResult:
    validate_source(source_path)
    if videos and len(videos) != len(video_proofs):
        raise ValueError("every supplied video must have a matching viewport-only capture proof")
    if video_proofs and not videos:
        raise ValueError("video proof cannot be supplied without a matching video")
    place_info: dict[str, Any] | None = None
    if place_file is not None:
        template_place = ROOT / "Places" / fixture.place
        place_info = validate_place_file(place_file, template_path=template_place)
    if run_dir.exists():
        raise FileExistsError(f"run directory already exists: {run_dir}")
    run_dir.mkdir(parents=True)
    (run_dir / "source").mkdir()
    (run_dir / "fixture").mkdir()
    (run_dir / "generation").mkdir()
    (run_dir / "place").mkdir()
    (run_dir / "screenshots").mkdir()
    (run_dir / "trace").mkdir()
    generation_summary = summarize_generation(generation_dir)
    run = ReviewRun(fixture=fixture, source_path=source_path, run_dir=run_dir)
    run.manifest = initial_manifest(fixture, source_path, run_dir, generation=generation_summary)
    copied_generation = copy_generation_bundle(generation_dir, run_dir / "generation")
    run.manifest["generation"] = copied_generation
    shutil.copy2(source_path, run_dir / "source" / "candidate.luau")
    shutil.copy2(fixture.path, run_dir / "fixture" / fixture.path.name)
    run.manifest["source"]["captured_path"] = str((run_dir / "source" / "candidate.luau").resolve())
    run.manifest["fixture"]["captured_path"] = str((run_dir / "fixture" / fixture.path.name).resolve())

    template_place = ROOT / "Places" / fixture.place
    if template_place.is_file():
        template_copy = run_dir / "place" / f"input-{template_place.name}"
        shutil.copy2(template_place, template_copy)
        run.manifest["place"] = {
            "generated": False,
            "kind": "input_template",
            "path": str(template_copy.resolve()),
            "sha256": sha256_file(template_copy),
            "bytes": template_copy.stat().st_size,
            "note": "This is the input template, not the generated candidate result.",
        }
    if place_file is not None:
        assert place_info is not None
        generated_place = run_dir / "place" / f"generated-{fixture.fixture_id.replace('.', '_')}{place_file.suffix.lower()}"
        shutil.copy2(place_file, generated_place)
        run.manifest["place"] = {
            "generated": True,
            "kind": "exported_playable_place",
            "format": place_info["format"],
            "path": str(generated_place.resolve()),
            "sha256": sha256_file(generated_place),
            "bytes": generated_place.stat().st_size,
        }
    run.write_manifest()

    lock_path = run_dir / ".run.lock"
    run._lock_handle = lock_path.open("w", encoding="utf-8")
    fcntl.flock(run._lock_handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        if plan_only:
            run.manifest["state"] = "planned"
            run.manifest["completed_at"] = utc_now()
            run.write_manifest()
            write_evaluation_summary(run.run_dir, run.manifest)
            write_bundle_readme(run.run_dir, run.manifest)
            write_review_packet(run)
            return RunResult(run_dir, "planned", "not run", run.manifest)

        if instance_id is not None and not INSTANCE_PATTERN.fullmatch(instance_id):
            raise ValueError("instance_id must match anon:<uuid>")

        if instance_id is None:
            instance_id, status, next_sequence, attempts = qualified.wait_for_instance(
                run_dir,
                run.sequence,
                timeout=readiness_timeout,
            )
            run.sequence = next_sequence
            run.instance_id = instance_id
            run.manifest["readiness"] = {"status": status, "attempts": attempts}
        else:
            run.instance_id = instance_id
            run.manifest["readiness"] = {"source": "explicit_instance_id"}

        run.manifest["instance_id"] = run.instance_id
        bootstrap = run.bridge(
            {
                "operation": "exec",
                "instance_id": run.instance_id,
                "target": "edit",
                "code": BOOTSTRAP_CODE,
                "timeout": 120,
            },
            timeout=180,
        )
        run.require_luau(bootstrap, "RSC bootstrap", "bloxbench-rsc-bootstrap")
        run.manifest["bootstrap"] = compact_job(bootstrap)

        reset = run.bridge(
            {"operation": "exec", "instance_id": run.instance_id, "target": "edit", "code": RESET_CODE},
            timeout=180,
        )
        run.require_luau(reset, "initial reset", "bloxbench-reset")
        run.manifest["reset"] = compact_job(reset)

        install = run.bridge(
            {
                "operation": "exec",
                "instance_id": run.instance_id,
                "target": "edit",
                "code": fixture_module_code(fixture.source),
                "timeout": 180,
            },
            timeout=240,
        )
        run.require_luau(install, "fixture install", "bloxbench-fixture-installed")
        setup = run.bridge(
            {
                "operation": "exec",
                "instance_id": run.instance_id,
                "target": "edit",
                "code": hook_code("setup"),
                "timeout": 120,
            },
            timeout=180,
        )
        setup_payload = run.require_luau(setup, "fixture setup", "bloxbench-hook")
        run.manifest["readbacks"]["setup"] = setup_payload

        execution = run.bridge(
            {
                "operation": "exec",
                "instance_id": run.instance_id,
                "target": "edit",
                "code": f'''local ok, value = xpcall(function()\n{source_path.read_text(encoding="utf-8")}\nend, function(err) return debug.traceback(tostring(err), 2) end)\nassert(ok, value)\nreturn {{marker = "bloxbench-candidate-executed"}}\n''',
                "timeout": 300,
            },
            timeout=360,
        )
        run.require_luau(execution, "candidate execution", "bloxbench-candidate-executed")
        run.execution_started = True
        run.manifest["execution"] = compact_job(execution)

        scene = run.bridge(
            {
                "operation": "exec",
                "instance_id": run.instance_id,
                "target": "edit",
                "code": hook_code("check_scene"),
                "timeout": 180,
            },
            timeout=240,
        )
        run.manifest["readbacks"]["check_scene"] = run.require_luau(scene, "scene check", "bloxbench-hook")

        modes = list(fixture.states) if fixture.states else ["capture"]
        playing = False
        client_role: str | None = None
        if fixture.runtime == "play":
            started = run.bridge(
                {
                    "operation": "play_start",
                    "instance_id": run.instance_id,
                    "arguments": {"mode": "play"},
                    "timeout": 180,
                },
                timeout=240,
            )
            run.require_remote(started, "playtest start")
            playing = True
            runtime_attempts: list[dict[str, Any]] = []
            for attempt in range(1, 4):
                runtime_status = run.bridge(
                    {"operation": "status"},
                    timeout=180,
                )
                try:
                    client_role = runtime_client_role(runtime_status)
                except RuntimeError as role_error:
                    runtime_attempts.append({"attempt": attempt, "error": str(role_error)})
                    if attempt < 3:
                        time.sleep(1.0)
                    continue
                runtime_attempts.append({"attempt": attempt, "role": client_role})
                break
            if client_role is None:
                run.manifest["runtime_client_discovery"] = runtime_attempts
                raise RuntimeError(f"runtime client did not become ready: {runtime_attempts!r}")
            run.manifest["runtime_client_discovery"] = runtime_attempts
        try:
            angles = screenshot_angle_names(fixture)
            primary_angle = angles[0]
            hero_operation = "eval" if playing else "exec"
            hero_target = client_role if playing else "edit"
            camera = run.bridge(
                {
                    "operation": hero_operation,
                    "instance_id": run.instance_id,
                    "target": hero_target,
                    "code": camera_code(primary_angle),
                    "timeout": 180,
                },
                timeout=240,
            )
            run.require_luau(camera, "hero camera", "bloxbench-camera")
            screenshot = run.bridge(
                {
                    "operation": "screenshot",
                    "instance_id": run.instance_id,
                    "arguments": {"format": "png"},
                    "artifact_dir": str(run_dir / "screenshots" / "raw" / "initial" / primary_angle),
                },
                timeout=240,
            )
            hero_record = store_screenshot(
                screenshot,
                "hero screenshot",
                run_dir / "screenshots" / f"initial-{primary_angle}.png",
                scope="roblox-client-viewport" if playing else "roblox-studio-window",
            )
            run.manifest["screenshots"][f"initial_{primary_angle}"] = hero_record["path"]
            run.manifest["screenshot_metadata"][f"initial_{primary_angle}"] = hero_record

            for mode in modes:
                target = "server" if playing else "edit"
                operation = "eval" if playing else "exec"
                run_response = run.bridge(
                    {
                        "operation": operation,
                        "instance_id": run.instance_id,
                        "target": target,
                        "code": hook_code("run", mode),
                        "timeout": 180,
                    },
                    timeout=240,
                )
                run.manifest["readbacks"][f"run:{mode}"] = run.require_luau(
                    run_response, f"run hook {mode}", "bloxbench-hook"
                )
                check_response = run.bridge(
                    {
                        "operation": operation,
                        "instance_id": run.instance_id,
                        "target": target,
                        "code": hook_code("check_game"),
                        "timeout": 180,
                    },
                    timeout=240,
                )
                run.manifest["readbacks"][f"check_game:{mode}"] = run.require_luau(
                    check_response, f"game check {mode}", "bloxbench-hook"
                )
                for angle in angles:
                    frame_operation = "eval" if playing else "exec"
                    frame_target = client_role if playing else "edit"
                    frame_camera = run.bridge(
                        {
                            "operation": frame_operation,
                            "instance_id": run.instance_id,
                            "target": frame_target,
                            "code": camera_code(angle),
                            "timeout": 120,
                        },
                        timeout=180,
                    )
                    run.require_luau(frame_camera, f"camera {mode}/{angle}", "bloxbench-camera")
                    frame = run.bridge(
                        {
                            "operation": "screenshot",
                            "instance_id": run.instance_id,
                            "arguments": {"format": "png"},
                            "artifact_dir": str(run_dir / "screenshots" / "raw" / f"state-{mode}" / angle),
                        },
                        timeout=240,
                    )
                    angle_suffix = "" if len(angles) == 1 else f"-{angle}"
                    screenshot_key = f"state-{mode}{angle_suffix}"
                    frame_record = store_screenshot(
                        frame,
                        f"state screenshot {mode}/{angle}",
                        run_dir / "screenshots" / f"{screenshot_key}.png",
                        scope="roblox-client-viewport" if playing else "roblox-studio-window",
                    )
                    run.manifest["screenshots"][screenshot_key] = frame_record["path"]
                    run.manifest["screenshot_metadata"][screenshot_key] = frame_record

            primary_mode = modes[0] if modes else None
            if primary_mode is not None:
                primary_suffix = "" if len(angles) == 1 else f"-{primary_angle}"
                primary_key = f"state-{primary_mode}{primary_suffix}"
                primary_source = run_dir / "screenshots" / f"{primary_key}.png"
                primary_destination = run_dir / "screenshots" / "hero.png"
                shutil.copy2(primary_source, primary_destination)
                primary_record = artifact_record(
                    primary_destination,
                    kind="screenshot",
                    scope="roblox-client-viewport" if playing else "roblox-studio-window",
                )
                dimensions = png_dimensions(primary_destination)
                if dimensions is not None:
                    primary_record["width"], primary_record["height"] = dimensions
                primary_record["derived_from"] = primary_key
                run.manifest["screenshots"]["hero"] = primary_record["path"]
                run.manifest["screenshot_metadata"]["hero"] = primary_record

            # Export the candidate from Studio as a playable artifact. This is
            # best-effort: screenshots + readbacks remain the review evidence,
            # but a successful export lets a human open the actual place.
            if not run.manifest.get("place") or not (run.manifest.get("place") or {}).get("generated"):
                try:
                    export_response = run.bridge(
                        {
                            "operation": "export_build",
                            "instance_id": run.instance_id,
                            "arguments": {
                                "instance_path": "game.Workspace.BloxBenchCandidate",
                                "output_id": f"bloxbench_{fixture.fixture_id.replace('.', '_')}_{uuid.uuid4().hex[:8]}",
                            },
                            "artifact_dir": str(run_dir / "place" / "export"),
                            "timeout": 180,
                        },
                        timeout=240,
                    )
                    artifact_path = export_response.get("artifact_path")
                    if isinstance(artifact_path, str) and Path(artifact_path).is_file():
                        exported = Path(artifact_path)
                        place_dest = run_dir / "place" / f"generated-{fixture.fixture_id.replace('.', '_')}.json"
                        shutil.copy2(exported, place_dest)
                        run.manifest["place"] = {
                            "generated": True,
                            "kind": "studio_build_export",
                            "format": "roblox-bench-export-json",
                            "path": str(place_dest.resolve()),
                            "sha256": sha256_file(place_dest),
                            "bytes": place_dest.stat().st_size,
                            "note": "Studio build export (parts/material manifest from the live candidate).",
                        }
                        run.manifest["export"] = export_response.get("export", {})
                except Exception as export_exc:
                    run.manifest["export_error"] = {
                        "type": type(export_exc).__name__,
                        "message": qualified._text_tail(qualified.redact_text(str(export_exc))),
                    }
        finally:
            if playing:
                stopped = run.bridge(
                    {"operation": "play_stop", "instance_id": run.instance_id, "timeout": 180},
                    timeout=240,
                )
                run.require_remote(stopped, "playtest stop")

        cleanup = run.bridge(
            {
                "operation": "exec",
                "instance_id": run.instance_id,
                "target": "edit",
                "code": hook_code("cleanup"),
                "timeout": 120,
            },
            timeout=180,
        )
        run.manifest["readbacks"]["cleanup"] = run.require_luau(cleanup, "fixture cleanup", "bloxbench-hook")
        final_reset = run.bridge(
            {"operation": "exec", "instance_id": run.instance_id, "target": "edit", "code": RESET_CODE},
            timeout=180,
        )
        run.require_luau(final_reset, "final reset", "bloxbench-reset")
        run.manifest["final_reset"] = compact_job(final_reset)

        for index, video in enumerate(videos):
            if index >= len(video_proofs):
                raise ValueError(f"video {index} has no viewport-only capture proof")
            run.manifest["videos"].append(
                copy_video(video, run_dir / "videos" / f"video-{index}{video.suffix.lower()}", video_proofs[index])
            )
        if require_video and fixture.evidence.get("video") == "required" and not run.manifest["videos"]:
            raise RuntimeError("fixture requires video evidence; pass --video and --video-proof")
        if not run.manifest["videos"]:
            run.manifest["video_policy"] = "withheld_until_viewport_only_capture"

        place_generated = bool((run.manifest.get("place") or {}).get("generated"))
        model_candidate = (run.manifest.get("candidate") or {}).get("is_model_evaluation") is True
        run.manifest["state"] = "completed" if place_generated else "completed_unexported"
        if place_generated and model_candidate and (not require_video or bool(run.manifest["videos"])):
            run.manifest["evidence_state"] = "valid reviewable result"
        elif not place_generated:
            run.manifest["evidence_state"] = "static evidence complete; generated place missing"
        elif not model_candidate:
            run.manifest["evidence_state"] = "execution complete; candidate origin is unattributed"
        else:
            run.manifest["evidence_state"] = "static evidence complete; video withheld"
        run.manifest["completed_at"] = utc_now()
        run.write_manifest()
        write_evaluation_summary(run.run_dir, run.manifest)
        write_bundle_readme(run.run_dir, run.manifest)
        write_review_packet(run)
        return RunResult(run_dir, run.manifest["state"], run.manifest["evidence_state"], run.manifest)
    except BaseException as exc:
        _set_failure(run.manifest, exc, execution_started=run.execution_started)
        if run.instance_id is not None:
            if run.execution_started and "cleanup" not in run.manifest.get("readbacks", {}):
                try:
                    cleanup = run.bridge(
                        {
                            "operation": "exec",
                            "instance_id": run.instance_id,
                            "target": "edit",
                            "code": hook_code("cleanup"),
                            "timeout": 120,
                        },
                        timeout=180,
                    )
                    run.manifest["readbacks"]["cleanup"] = run.require_luau(
                        cleanup, "failure fixture cleanup", "bloxbench-hook"
                    )
                except Exception as cleanup_exc:
                    run.manifest["failure_fixture_cleanup_error"] = {
                        "type": type(cleanup_exc).__name__,
                        "message": qualified._text_tail(qualified.redact_text(str(cleanup_exc))),
                    }
            with contextlib.suppress(Exception):
                cleanup = run.bridge(
                    {
                        "operation": "exec",
                        "instance_id": run.instance_id,
                        "target": "edit",
                        "code": RESET_CODE,
                        "timeout": 120,
                    },
                    timeout=180,
                )
                run.manifest["failure_cleanup"] = compact_job(cleanup)
        run.write_manifest()
        write_evaluation_summary(run.run_dir, run.manifest)
        write_bundle_readme(run.run_dir, run.manifest)
        write_review_packet(run)
        return RunResult(run_dir, run.manifest["state"], run.manifest["evidence_state"], run.manifest)
    finally:
        if run._lock_handle is not None:
            fcntl.flock(run._lock_handle.fileno(), fcntl.LOCK_UN)
            run._lock_handle.close()


def attach_videos(
    run_dir: Path,
    videos: tuple[Path, ...],
    video_proofs: tuple[Path, ...],
) -> RunResult:
    manifest_path = run_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("state") != "failed":
        raise ValueError("only a failed run can receive post-capture video evidence")
    error_message = str((manifest.get("error") or {}).get("message", ""))
    if "requires video evidence" not in error_message:
        raise ValueError("run did not fail at the missing-video evidence boundary")
    if not videos:
        raise ValueError("at least one video is required")
    fixture = parse_fixture(manifest["fixture"]["path"])
    source_path = Path(manifest["source"]["path"])
    run = ReviewRun(fixture=fixture, source_path=source_path, run_dir=run_dir)
    run.manifest = manifest
    previous_error = run.manifest.pop("error", None)
    for index, video in enumerate(videos):
        if index >= len(video_proofs):
            raise ValueError(f"video {index} has no viewport-only capture proof")
        run.manifest.setdefault("videos", []).append(
            copy_video(video, run_dir / "videos" / f"video-{index}{video.suffix.lower()}", video_proofs[index])
        )
    run.manifest["resolution"] = {
        "type": "post-capture-video-attachment",
        "previous_error": previous_error,
        "attached_at": utc_now(),
    }
    run.manifest["state"] = "completed"
    run.manifest["evidence_state"] = "valid reviewable result"
    run.manifest["completed_at"] = utc_now()
    run.write_manifest()
    write_evaluation_summary(run.run_dir, run.manifest)
    write_bundle_readme(run.run_dir, run.manifest)
    write_review_packet(run)
    return RunResult(run_dir, "completed", "valid reviewable result", run.manifest)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", required=True, type=Path)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--instance-id")
    parser.add_argument("--video", action="append", type=Path, default=[])
    parser.add_argument("--video-proof", action="append", type=Path, default=[])
    parser.add_argument("--place-file", type=Path, help="verified exported .rbxl/.rbxlx candidate place")
    parser.add_argument("--generation-dir", type=Path, help="model generation arm directory containing manifest.json")
    parser.add_argument("--require-video", action="store_true")
    parser.add_argument("--plan-only", action="store_true")
    parser.add_argument("--readiness-timeout", type=float, default=120.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    fixture = parse_fixture(args.fixture)
    run_dir = args.run_dir or create_run_dir(args.output_root, fixture.fixture_id)
    result = run_review(
        fixture,
        args.source,
        run_dir,
        instance_id=args.instance_id,
        plan_only=args.plan_only,
        videos=tuple(args.video),
        video_proofs=tuple(args.video_proof),
        place_file=args.place_file,
        generation_dir=args.generation_dir,
        readiness_timeout=args.readiness_timeout,
        require_video=args.require_video,
    )
    print(json.dumps({"run_dir": str(result.run_dir), "state": result.state, "evidence_state": result.evidence_state}))
    if result.state == "planned":
        return 0
    if result.state == "completed" and result.evidence_state == "valid reviewable result":
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
