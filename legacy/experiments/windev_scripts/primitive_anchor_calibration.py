#!/usr/bin/env python3
"""Zero-token Studio calibration for PartPrimitives limb origin faces."""
from __future__ import annotations

import asyncio
import base64
import json
import os
import sys
import time
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[2]


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


async def main() -> int:
    sys.path.insert(0, str(ROOT))
    import harness

    versions = Path(os.environ["LOCALAPPDATA"]) / "Roblox" / "Versions"
    studio_candidates = sorted(
        (p / "RobloxStudioBeta.exe" for p in versions.glob("version-*")),
        key=lambda p: p.parent.name,
        reverse=True,
    )
    studio_exe = next((p for p in studio_candidates if p.exists()), None)
    if studio_exe is None:
        raise RuntimeError(f"RobloxStudioBeta.exe not found under {versions}")

    place = ROOT / "Places" / "baseplate.rbxl"
    run_dir = ROOT / "results" / f"anchor_calibration_{time.strftime('%m%d_%H%M%S')}"
    run_dir.mkdir(parents=True, exist_ok=True)

    studio = harness.StudioConfig(
        exe_path=str(studio_exe),
        mcp_path=str(Path.home() / "studio-mcp.bat"),
        startup_wait=45,
    )

    module_source = (ROOT / "PartPrimitives.lua").read_text(encoding="utf-8")
    build_code = r'''
local RS = game:GetService("ReplicatedStorage")
local P = require(RS:WaitForChild("PartPrimitives"))
local function kill(name)
    local old = workspace:FindFirstChild(name)
    if old then old:Destroy() end
end
for _, name in ipairs({"CalFloor", "CalBody", "CalNeck_1", "CalNeck_2", "CalLeg_1", "CalLeg_2", "CalLeftWing_1", "CalLeftWing_2", "CalRightWing_1", "CalRightWing_2", "CalTail_1", "CalTail_2"}) do
    kill(name)
end
P.block({40, 1, 40}, {name="CalFloor", at={0, 0.5, 0}, material="Concrete"})
local body = P.block({10, 5, 12}, {name="CalBody", at={0, 5, 0}, material="Slate"})
P.limb({{2, 2, 2}, {1.5, 1.5, 1.5}}, {name="CalNeck", origin=body, anchor="top", angle=90, material="Concrete"})
P.limb({{2, 2, 2}, {1.5, 1.5, 1.5}}, {name="CalLeg", origin=body, anchor="bottom", angle=-90, material="Concrete"})
P.limb({{4, 1, 1}, {3, 0.8, 0.8}}, {name="CalLeftWing", origin=body, anchor="left", yaw=180, angle=0, material="WoodPlanks"})
P.limb({{4, 1, 1}, {3, 0.8, 0.8}}, {name="CalRightWing", origin=body, anchor="right", yaw=0, angle=0, material="WoodPlanks"})
P.limb({{4, 1, 1}, {3, 0.8, 0.8}}, {name="CalTail", origin=body, anchor="back", yaw=-90, angle=0, material="Slate"})
local cam = workspace.CurrentCamera
if cam then
    cam.CFrame = CFrame.lookAt(Vector3.new(24, 17, 28), Vector3.new(0, 4, 0))
    cam.FieldOfView = 45
end
return "calibration_built"
'''

    dump_code = r'''
local names = {"CalFloor", "CalBody", "CalNeck_1", "CalNeck_2", "CalLeg_1", "CalLeg_2", "CalLeftWing_1", "CalLeftWing_2", "CalRightWing_1", "CalRightWing_2", "CalTail_1", "CalTail_2"}
local NL = string.char(10)
local out = {}
for _, name in ipairs(names) do
    local p = workspace:FindFirstChild(name)
    if p and p:IsA("BasePart") then
        table.insert(out, string.format("%s pos=(%.2f,%.2f,%.2f) size=(%.2f,%.2f,%.2f) cframe=%s", name, p.Position.X, p.Position.Y, p.Position.Z, p.Size.X, p.Size.Y, p.Size.Z, tostring(p.CFrame)))
    else
        table.insert(out, name .. " MISSING")
    end
end
local parts = {}
for _, obj in ipairs(workspace:GetChildren()) do
    if obj:IsA("BasePart") and obj.Name ~= "Baseplate" and obj.Name ~= "SpawnLocation" and not obj:IsA("Terrain") then table.insert(parts, obj) end
end
local floating, overlaps = {}, {}
local ground = false
for i, p in ipairs(parts) do
    local bottom = p.Position.Y - p.Size.Y / 2
    if bottom <= 0.5 then ground = true end
    if bottom > 1.0 then
        local supported = false
        for _, q in ipairs(parts) do
            if q ~= p then
                local qtop = q.Position.Y + q.Size.Y / 2
                if math.abs(qtop - bottom) < 1.5 and math.abs(p.Position.X - q.Position.X) < (p.Size.X + q.Size.X) / 2 and math.abs(p.Position.Z - q.Position.Z) < (p.Size.Z + q.Size.Z) / 2 then supported = true break end
            end
        end
        if not supported then table.insert(floating, p.Name) end
    end
    for j = i + 1, #parts do
        local q = parts[j]
        if math.abs(p.Position.X - q.Position.X) < (p.Size.X + q.Size.X) / 2 - 0.1 and math.abs(p.Position.Y - q.Position.Y) < (p.Size.Y + q.Size.Y) / 2 - 0.1 and math.abs(p.Position.Z - q.Position.Z) < (p.Size.Z + q.Size.Z) / 2 - 0.1 then table.insert(overlaps, p.Name .. "<->" .. q.Name) end
    end
end
table.insert(out, "ground_contact=" .. tostring(ground))
table.insert(out, "floating_parts=" .. tostring(#floating) .. " " .. table.concat(floating, ","))
table.insert(out, "overlaps=" .. tostring(#overlaps) .. " " .. table.concat(overlaps, ","))
return table.concat(out, NL)
'''

    try:
        if not await harness.launch_studio(studio, str(place)):
            raise RuntimeError("Studio launch failed")

        params = StdioServerParameters(command="cmd.exe", args=["/c", studio.mcp_path])
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await asyncio.wait_for(session.initialize(), timeout=60)
                ready = ""
                for _ in range(8):
                    ready = await call(session, "execute_luau", {"datamodel_type": "Edit", "code": 'return "ready"'}, timeout=15)
                    if "ready" in ready:
                        break
                    await asyncio.sleep(3)
                if "ready" not in ready:
                    raise RuntimeError(f"Studio MCP did not become ready: {ready}")

                await call(session, "execute_luau", {"datamodel_type": "Edit", "code": 'local m=game.ReplicatedStorage:FindFirstChild("PartPrimitives"); if m then m:Destroy() end; return "clean"'})
                upload = await call(session, "multi_edit", {
                    "file_path": "game.ReplicatedStorage.PartPrimitives",
                    "className": "ModuleScript",
                    "datamodel_type": "Edit",
                    "edits": [{"old_string": "", "new_string": module_source}],
                }, timeout=60)
                built = await call(session, "execute_luau", {"datamodel_type": "Edit", "code": build_code}, timeout=60)
                dump = await call(session, "execute_luau", {"datamodel_type": "Edit", "code": dump_code}, timeout=60)
                image_result = await session.call_tool("screen_capture", {"capture_id": "anchor_calibration"})
                image_bytes = image_of(image_result)
                if image_bytes is None:
                    raise RuntimeError(f"screen_capture: {text_of(image_result)}")
                screenshot = run_dir / "anchor_calibration.png"
                screenshot.write_bytes(image_bytes)

        report = {
            "status": "completed",
            "run_dir": str(run_dir),
            "studio": str(studio_exe),
            "upload": upload,
            "build": built,
            "dump": dump,
            "screenshot": str(screenshot),
        }
        (run_dir / "calibration.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0
    finally:
        harness.kill_studio()


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except Exception as exc:
        print(json.dumps({"status": "error", "reason": str(exc)}))
        raise
