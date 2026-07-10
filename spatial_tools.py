"""Local spatial observation tools for the BloxBench harness.

These tools intentionally do not create or move geometry. They call the existing
Roblox Studio execute_luau tool to produce a compact scene snapshot, then keep a
small per-eval intent ledger for model-directed repair.
"""

from __future__ import annotations

import json
from typing import Awaitable, Callable


ToolCaller = Callable[[str, dict], Awaitable[tuple[object, str]]]


class SpatialTooling:
    """Expose observation and intent tools without adding a builder API."""

    LOCAL_TOOL_NAMES = {"spatial_snapshot", "spatial_intent_add", "spatial_intent_check", "spatial_lint"}

    def __init__(self, call_tool: ToolCaller):
        self._call_tool = call_tool
        self.intents: list[dict] = []

    @classmethod
    def handles(cls, name: str) -> bool:
        return name in cls.LOCAL_TOOL_NAMES

    @staticmethod
    def tool_definitions() -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "spatial_snapshot",
                    "description": (
                        "Inspect the current Roblox scene without changing it. Returns a compact "
                        "spatial summary with named parts, bounds, grounding, attributes, and "
                        "connected components. Use this before repairing an existing build or "
                        "when the scene state is uncertain."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "root": {
                                "type": "string",
                                "description": "Workspace or a Workspace child path to inspect. Default Workspace.",
                            },
                            "max_parts": {
                                "type": "integer",
                                "description": "Maximum BaseParts to include, from 10 to 120. Default 80.",
                            },
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "spatial_intent_add",
                    "description": (
                        "Register one expected scene component for later checking. This records "
                        "intent only and does not create geometry. Use stable names and roles such "
                        "as tower_shaft, lookout_platform, door, or battlements."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Expected object or role name."},
                            "role": {"type": "string", "description": "Semantic role, such as primary_mass or detail."},
                            "parent": {"type": "string", "description": "Expected parent or supporting object name."},
                            "relation": {"type": "string", "description": "Expected relation: grounded, attached, or on_top."},
                            "required": {"type": "boolean", "description": "Whether absence should be reported as a failure. Default true."},
                        },
                        "required": ["name"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "spatial_intent_check",
                    "description": (
                        "Check registered scene intent against the current Roblox scene. Returns "
                        "missing expected objects, attachment and grounding problems, and the "
                        "current connected-component summary. Does not modify the scene."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "root": {"type": "string", "description": "Workspace or a Workspace child path. Default Workspace."},
                        },
                        "required": [],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "spatial_lint",
                    "description": (
                        "Lint every actual BasePart in the selected scene for disconnected components. "
                        "It reports components that are disconnected from the largest grounded component, "
                        "not legitimate elevated parts that are connected to the tower. "
                        "Unlike spatial_intent_check, this does not depend on what the model registered. "
                        "Use it after geometry edits and before claiming a repair is complete."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "root": {"type": "string", "description": "Workspace or a Workspace child path. Default Workspace."},
                        },
                        "required": [],
                    },
                },
            },
        ]

    async def handle(self, name: str, args: dict) -> str:
        if name == "spatial_snapshot":
            return await self._snapshot(args)
        if name == "spatial_intent_add":
            return self._intent_add(args)
        if name == "spatial_intent_check":
            return await self._intent_check(args)
        if name == "spatial_lint":
            return await self._lint(args)
        return f"Tool error: unknown local spatial tool {name}"

    async def _snapshot(self, args: dict) -> str:
        root = str(args.get("root") or "Workspace")
        max_parts = max(10, min(120, int(args.get("max_parts") or 80)))
        code = self._snapshot_luau(root, max_parts)
        result, text = await self._call_tool("execute_luau", {"datamodel_type": "Edit", "code": code})
        del result
        if not text or text.startswith("Tool error:") or text.startswith("Error:"):
            return f"Tool error: spatial_snapshot could not inspect the scene: {text[:500]}"
        return text

    def _intent_add(self, args: dict) -> str:
        name = str(args.get("name") or "").strip()
        if not name:
            return "Tool error: spatial_intent_add requires a non-empty name"
        intent = {
            "name": name,
            "role": str(args.get("role") or ""),
            "parent": str(args.get("parent") or ""),
            "relation": str(args.get("relation") or ""),
            "required": bool(args.get("required", True)),
        }
        self.intents = [item for item in self.intents if item["name"] != name]
        self.intents.append(intent)
        return json.dumps({"status": "registered", "intent": intent, "intent_count": len(self.intents)})

    async def _intent_check(self, args: dict) -> str:
        snapshot_text = await self._snapshot(args)
        if snapshot_text.startswith("Tool error:"):
            return snapshot_text
        try:
            snapshot = json.loads(snapshot_text)
        except json.JSONDecodeError:
            return "Tool error: spatial_intent_check received an invalid scene snapshot"

        parts = snapshot.get("parts", [])
        by_name = {str(part.get("name")): part for part in parts}
        by_role = {str(part.get("build_role")): part for part in parts if part.get("build_role")}
        statuses = []
        for intent in self.intents:
            subject = by_name.get(intent["name"]) or by_role.get(intent.get("role", ""))
            status = {
                "name": intent["name"],
                "required": intent["required"],
                "present": subject is not None,
                "role": intent.get("role", ""),
                "parent": intent.get("parent", ""),
                "relation": intent.get("relation", ""),
                "issues": [],
            }
            if subject is None:
                status["issues"].append("missing")
                statuses.append(status)
                continue

            if intent.get("relation") == "grounded" and float(subject.get("bottom_y", 9999)) > 0.45:
                status["issues"].append("not_grounded")
            parent = by_name.get(intent.get("parent", "")) or by_role.get(intent.get("parent", ""))
            if intent.get("parent") and parent is None:
                status["issues"].append("parent_missing")
            elif parent is not None and intent.get("relation") in {"attached", "on_top"}:
                if not self._boxes_near(subject, parent, tolerance=0.5):
                    status["issues"].append("not_attached_to_parent")
                if intent.get("relation") == "on_top" and float(subject.get("bottom_y", -9999)) < float(parent.get("top_y", 9999)) - 0.75:
                    status["issues"].append("not_on_top_of_parent")
            statuses.append(status)

        scene_issues = []
        components = list(snapshot.get("components", []))
        if len(components) > 1:
            scene_issues.append(
                {
                    "type": "disconnected_components",
                    "component_count": len(components),
                    "components": components,
                }
            )
        failures = [item for item in statuses if item["required"] and (not item["present"] or item["issues"])]
        all_failures = failures + scene_issues
        return json.dumps(
            {
                "status": "issues" if all_failures else "ok",
                "failures": all_failures,
                "intents": statuses,
                "scene_issues": scene_issues,
                "scene": {
                    "root": snapshot.get("root"),
                    "part_count": len(parts),
                    "components": components,
                },
            },
            separators=(",", ":"),
        )

    async def _lint(self, args: dict) -> str:
        snapshot_text = await self._snapshot(args)
        if snapshot_text.startswith("Tool error:"):
            return snapshot_text
        try:
            snapshot = json.loads(snapshot_text)
        except json.JSONDecodeError:
            return "Tool error: spatial_lint received an invalid scene snapshot"

        components = list(snapshot.get("components", []))
        components.sort(key=lambda component: int(component.get("count", 0)), reverse=True)
        issues = []
        grounded_id = next(
            (component.get("id") for component in components if component.get("grounded", False)),
            None,
        )
        if len(components) > 1:
            for component in components:
                if component.get("id") == grounded_id:
                    continue
                issues.append(
                    {
                        "type": "disconnected_component",
                        "component_id": component.get("id"),
                        "count": component.get("count", 0),
                        "grounded": component.get("grounded", False),
                        "names": component.get("names", []),
                        "min_y": component.get("min_y"),
                        "max_y": component.get("max_y"),
                    }
                )
        if grounded_id is None:
            issues.append(
                {
                    "type": "no_grounded_component",
                    "component_count": len(components),
                    "components": components,
                }
            )
        return json.dumps(
            {
                "status": "issues" if issues else "ok",
                "root": snapshot.get("root"),
                "part_count": len(snapshot.get("parts", [])),
                "component_count": len(components),
                "issues": issues,
                "components": components,
                "instruction": "Do not claim completion while this reports issues; repair the named parts and lint again.",
            },
            separators=(",", ":"),
        )

    @staticmethod
    def _boxes_near(a: dict, b: dict, tolerance: float) -> bool:
        ap, az = a.get("position", {}), a.get("size", {})
        bp, bz = b.get("position", {}), b.get("size", {})
        for axis in ("x", "y", "z"):
            if abs(float(ap.get(axis, 0)) - float(bp.get(axis, 0))) > (float(az.get(axis, 0)) + float(bz.get(axis, 0))) / 2 + tolerance:
                return False
        return True

    @staticmethod
    def _snapshot_luau(root: str, max_parts: int) -> str:
        root_child = root.removeprefix("game.").removeprefix("Workspace").lstrip(".")
        root_literal = json.dumps(root_child)
        return f'''local HttpService = game:GetService("HttpService")
local root = workspace
local rootChild = {root_literal}
if rootChild ~= "" then
    for segment in string.gmatch(rootChild, "[^.]+") do
        root = root:FindFirstChild(segment)
        if not root then
            return HttpService:JSONEncode({{error = "root_not_found", root = rootChild}})
        end
    end
end
local maxParts = {max_parts}
local parts = {{}}
for _, obj in ipairs(root:GetDescendants()) do
    if obj:IsA("BasePart") and obj.Name ~= "Baseplate" and obj.Name ~= "SpawnLocation" then
        if #parts < maxParts then
            local p = obj.Position
            local s = obj.Size
            table.insert(parts, {{
                name = obj.Name,
                class_name = obj.ClassName,
                path = obj:GetFullName(),
                parent = obj.Parent and obj.Parent.Name or "",
                position = {{x = p.X, y = p.Y, z = p.Z}},
                size = {{x = s.X, y = s.Y, z = s.Z}},
                bottom_y = p.Y - s.Y / 2,
                top_y = p.Y + s.Y / 2,
                anchored = obj.Anchored,
                build_role = obj:GetAttribute("BuildRole") or "",
                build_parent = obj:GetAttribute("BuildParent") or "",
            }})
        end
    end
end
local function near(a, b, tolerance)
    return math.abs(a.position.x - b.position.x) <= (a.size.x + b.size.x) / 2 + tolerance
       and math.abs(a.position.y - b.position.y) <= (a.size.y + b.size.y) / 2 + tolerance
       and math.abs(a.position.z - b.position.z) <= (a.size.z + b.size.z) / 2 + tolerance
end
local parent = {{}}
for i = 1, #parts do parent[i] = i end
local function find(i)
    while parent[i] ~= i do
        parent[i] = parent[parent[i]]
        i = parent[i]
    end
    return i
end
local function join(a, b)
    local ra, rb = find(a), find(b)
    if ra ~= rb then parent[rb] = ra end
end
for i = 1, #parts do
    for j = i + 1, #parts do
        if near(parts[i], parts[j], 0.35) then join(i, j) end
    end
end
local groups = {{}}
for i, part in ipairs(parts) do
    local id = find(i)
    groups[id] = groups[id] or {{count = 0, names = {{}}, min_y = 999999, max_y = -999999, grounded = false}}
    local g = groups[id]
    g.count += 1
    if #g.names < 8 then table.insert(g.names, part.name) end
    if part.bottom_y < g.min_y then g.min_y = part.bottom_y end
    if part.top_y > g.max_y then g.max_y = part.top_y end
    if part.bottom_y <= 0.45 then g.grounded = true end
    part.component = id
end
local components = {{}}
for id, group in pairs(groups) do
    group.id = id
    table.insert(components, group)
end
table.sort(components, function(a, b) return a.count > b.count end)
return HttpService:JSONEncode({{root = root:GetFullName(), parts = parts, components = components, truncated = #parts >= maxParts}})'''
