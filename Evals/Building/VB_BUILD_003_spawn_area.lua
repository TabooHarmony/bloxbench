--!strict
-- @judge_rubric correctness="spawn pad + arch above + path leading away + 2+ decorative elements" layout="path leads away from spawn, arch above spawn" aesthetics="3+ colors, decorative elements distinct" completeness="spawn + arch + path + decoration"
-- @screenshot type=build angles=3

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
local HttpService = game:GetService("HttpService")
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_BUILD_003_spawn_area",
    prompt = {
        {
            {
                role = "user",
                content = [[Build a spawn area for a game. Requirements:
- A spawn pad: a flat part at ground level, at least 10x10 studs, named "SpawnLocation" or "Spawn"
- A decorative arch or gateway above the spawn pad (minimum 3 parts, height >= 8 studs)
- A path: at least 4 flat parts leading away from the spawn pad in one direction, each at least 6x2 studs
- At least 2 decorative elements beside the path (trees, rocks, lamps — use parts/cylinders/spheres)
- Use at least 3 different colors]],
                request_id = "vb_build_003"
            }
        }
    },
    place = "baseplate.rbxl"
}

local SelectionContextJson = "[]"
local TableSelectionContext = HttpService:JSONDecode(SelectionContextJson)

eval.setup = function()
    local selectionService = game:GetService("Selection")
    selectionService:Set({})
end

eval.reference = function()
end

eval.check_scene = function()
    local parts = {}
    for _, obj in ipairs(workspace:GetChildren()) do
        if obj:IsA("BasePart") and obj.Name ~= "Baseplate" then
            table.insert(parts, obj)
        elseif obj:IsA("Model") then
            for _, d in ipairs(obj:GetDescendants()) do
                if d:IsA("BasePart") then
                    table.insert(parts, d)
                end
            end
        end
    end

    assert(#parts >= 9, string.format("Only %d parts found, need >= 9 (spawn + 3 arch + 4 path + 2 deco)", #parts))

    -- Find spawn part
    local spawnPart = nil
    for _, p in ipairs(parts) do
        local name = string.lower(p.Name)
        if string.find(name, "spawn") then
            spawnPart = p
            break
        end
    end
    assert(spawnPart, "No part named 'Spawn' or containing 'Spawn' found")

    -- Check for parts above the spawn (arch, Y > 8)
    local archCount = 0
    for _, p in ipairs(parts) do
        if p.Position.Y > 8 then
            archCount = archCount + 1
        end
    end
    assert(archCount >= 3, string.format("Only %d parts above Y=8 found, need >= 3 (arch)", archCount))

    -- Check for 3+ colors
    local colors = {}
    for _, p in ipairs(parts) do
        if p.BrickColor then
            colors[tostring(p.BrickColor)] = true
        end
    end
    local colorCount = 0
    for _ in pairs(colors) do colorCount = colorCount + 1 end
    assert(colorCount >= 3, string.format("Only %d distinct BrickColors found, need >= 3", colorCount))
end

eval.check_game = function()
end

return eval
