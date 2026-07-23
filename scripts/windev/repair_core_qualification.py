#!/usr/bin/env python3
"""Zero-token qualification for the three repair-core fixtures."""
from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import os
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPAIR_CORE_DIR = ROOT / "Evals" / "RepairCore"
REPAIR_SNIPPETS = {
    "VB_CORE_REPAIR_001_single_part": "workspace.RepairTarget.LooseRoof.CFrame = CFrame.new(0, 7.5, 0)",
    "VB_CORE_REPAIR_002_two_parts": "workspace.RepairTarget.LooseRoof.CFrame = CFrame.new(0, 7.5, 0)\nworkspace.RepairTarget.LooseFlag.CFrame = CFrame.new(1.3, 12.5, 0)",
    "VB_CORE_REPAIR_003_preserve_assembly": "workspace.RepairTarget.UpperAssembly:PivotTo(workspace.RepairTarget.UpperAssembly:GetPivot() * CFrame.new(-10, 0, 0))",
}


def discover_repair_core_evals(root: Path = ROOT) -> list[Path]:
    return sorted((root / "Evals" / "RepairCore").glob("VB_CORE_REPAIR_*.lua"))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def text_of(result) -> str:
    chunks = []
    for item in getattr(result, "content", []) or []:
        if hasattr(item, "text"):
            chunks.append(item.text)
    return "\n".join(chunks)


def image_of(result) -> bytes | None:
    for item in getattr(result, "content", []) or []:
        if hasattr(item, "data"):
            return base64.b64decode(item.data)
    return None


async def call(session, name: str, arguments: dict, timeout: float = 60) -> str:
    result = await asyncio.wait_for(session.call_tool(name, arguments), timeout=timeout)
    value = text_of(result)
    if getattr(result, "isError", False):
        raise RuntimeError(f"{name}: {value}")
    return value


async def capture(session, path: Path, capture_id: str) -> None:
    result = await asyncio.wait_for(session.call_tool("screen_capture", {"capture_id": capture_id}), timeout=60)
    if getattr(result, "isError", False):
        raise RuntimeError(f"screen_capture: {text_of(result)}")
    image_bytes = image_of(result)
    if image_bytes is None:
        raise RuntimeError(f"screen_capture returned no image for {capture_id}")
    path.write_bytes(image_bytes)


async def qualify_one(session, eval_path: Path, output_dir: Path) -> dict:
    scenario = eval_path.stem
    repair = REPAIR_SNIPPETS[scenario]
    source = eval_path.read_text(encoding="utf-8")
    await call(session, "execute_luau", {
        "datamodel_type": "Edit",
        "code": 'local old = game.ReplicatedStorage:FindFirstChild("_RepairCoreEval"); if old then old:Destroy() end; return "clean"',
    })
    await call(session, "multi_edit", {
        "file_path": "game.ReplicatedStorage._RepairCoreEval",
        "className": "ModuleScript",
        "datamodel_type": "Edit",
        "edits": [{"old_string": "", "new_string": source}],
    }, timeout=60)

    bad_check = await call(session, "execute_luau", {
        "datamodel_type": "Edit",
        "code": 'local eval = require(game.ReplicatedStorage:WaitForChild("_RepairCoreEval")); eval.setup(); local ok, message = pcall(eval.check_scene); if ok then return "__BAD_STATE_PASSED__" end; return tostring(message)',
    })
    if "__BAD_STATE_PASSED__" in bad_check:
        raise RuntimeError(f"{scenario}: seeded broken state passed")

    camera_code = 'local camera = workspace.CurrentCamera; if camera then camera.CFrame = CFrame.lookAt(Vector3.new(30, 20, 40), Vector3.new(0, 5, 0)); camera.FieldOfView = 50 end; return "camera_set"'
    await call(session, "execute_luau", {"datamodel_type": "Edit", "code": camera_code})
    bad_path = output_dir / f"{scenario}_bad.png"
    await capture(session, bad_path, f"{scenario}_bad")

    good_check = await call(session, "execute_luau", {
        "datamodel_type": "Edit",
        "code": f'local eval = require(game.ReplicatedStorage:WaitForChild("_RepairCoreEval")); {repair}; local ok, message = pcall(eval.check_scene); if not ok then error(tostring(message)) end; return "good_state_passed"',
    })
    await call(session, "execute_luau", {"datamodel_type": "Edit", "code": camera_code})
    good_path = output_dir / f"{scenario}_good.png"
    await capture(session, good_path, f"{scenario}_good")

    return {
        "scenario": scenario,
        "eval_sha256": sha256_file(eval_path),
        "bad_check": bad_check,
        "good_check": good_check,
        "bad_screenshot": str(bad_path),
        "good_screenshot": str(good_path),
    }


async def main() -> int:
    run_dir = ROOT / "results" / f"repair_core_qualification_{time.strftime('%Y%m%d_%H%M%S')}"
    screenshot_dir = run_dir / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    report = {"status": "error", "run_dir": str(run_dir), "scenarios": [], "model_calls": 0, "api_calls": 0}
    harness = None
    current_scenario = None
    try:
        eval_paths = discover_repair_core_evals()
        if len(eval_paths) != 3 or {path.stem for path in eval_paths} != set(REPAIR_SNIPPETS):
            raise RuntimeError(f"expected exactly three repair-core evals, found {[path.name for path in eval_paths]}")

        local_appdata = os.environ.get("LOCALAPPDATA")
        if not local_appdata:
            raise RuntimeError("LOCALAPPDATA is not set")
        versions = Path(local_appdata) / "Roblox" / "Versions"
        candidates = sorted(
            (path / "RobloxStudioBeta.exe" for path in versions.glob("version-*")),
            key=lambda path: path.parent.name,
            reverse=True,
        )
        studio_exe = next((path for path in candidates if path.exists()), None)
        if studio_exe is None:
            raise RuntimeError(f"RobloxStudioBeta.exe not found under {versions}")

        import sys
        sys.path.insert(0, str(ROOT))
        import harness
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client

        studio = harness.StudioConfig(
            exe_path=str(studio_exe),
            mcp_path=str(Path.home() / "studio-mcp.bat"),
            startup_wait=45,
        )
        place = ROOT / "Places" / "baseplate.rbxl"
        if not await harness.launch_studio(studio, str(place)):
            raise RuntimeError("Studio launch failed")

        params = StdioServerParameters(command="cmd.exe", args=["/c", studio.mcp_path])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                # Studio starts its MCP WebSocket client during startup and may
                # need one retry interval after the proxy begins listening.
                await asyncio.sleep(15)
                await asyncio.wait_for(session.initialize(), timeout=60)
                ready = ""
                for _ in range(8):
                    ready = await call(session, "execute_luau", {"datamodel_type": "Edit", "code": 'return "ready"'}, timeout=15)
                    if "ready" in ready:
                        break
                    await asyncio.sleep(3)
                if "ready" not in ready:
                    raise RuntimeError(f"Studio MCP did not become ready: {ready}")

                for eval_path in eval_paths:
                    current_scenario = eval_path.stem
                    report["scenarios"].append(await qualify_one(session, eval_path, screenshot_dir))

        report["status"] = "completed"
        report["scenario_count"] = len(report["scenarios"])
        return_code = 0
    except Exception as exc:
        report["scenario"] = current_scenario
        report["reason"] = str(exc)
        return_code = 1
    finally:
        if harness is not None:
            harness.kill_studio()
        (run_dir / "qualification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
    return return_code


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
