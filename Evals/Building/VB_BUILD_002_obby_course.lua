--!strict
-- @judge_rubric correctness="6+ obstacles, structurally different, progressing along one axis" layout="obstacles reach previous, gap < 15 studs" aesthetics="3+ colors, 2+ shapes" completeness="6+ obstacle sections with variety"
-- @screenshot type=build angles=3

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
local HttpService = game:GetService("HttpService")
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_BUILD_002_obby_course",
    prompt = {
        {
            {
                role = "user",
                content = [[Create an obstacle course starting at the origin and extending in one direction. Requirements:
- At least 6 obstacle sections, each different in structure (not copies of the same part)
- Obstacles should progress along a single axis (X or Z), getting further from origin
- At least 3 different colors used across obstacles
- At least 2 different part shapes (Part, Cylinder, WedgePart, etc.)
- Each obstacle should be reachable from the previous one (gap between obstacles < 15 studs)]],
                request_id = "vb_build_002"
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

    assert(#parts >= 6, string.format("Only %d parts found, need >= 6", #parts))

    -- Check for 2+ different part shapes
    local shapes = {}
    for _, p in ipairs(parts) do
        shapes[p.ClassName] = true
    end
    local shapeCount = 0
    for _ in pairs(shapes) do shapeCount = shapeCount + 1 end
    assert(shapeCount >= 2, string.format("Only %d part shapes found, need >= 2", shapeCount))

    -- Check for 3+ different colors
    local colors = {}
    for _, p in ipairs(parts) do
        if p.BrickColor then
            colors[tostring(p.BrickColor)] = true
        end
    end
    local colorCount = 0
    for _ in pairs(colors) do colorCount = colorCount + 1 end
    assert(colorCount >= 3, string.format("Only %d distinct BrickColors found, need >= 3", colorCount))

    -- Check progression along one axis: sort parts by X or Z and verify they spread
    local minX, maxX, minZ, maxZ = math.huge, -math.huge, math.huge, -math.huge
    for _, p in ipairs(parts) do
        minX = math.min(minX, p.Position.X)
        maxX = math.max(maxX, p.Position.X)
        minZ = math.min(minZ, p.Position.Z)
        maxZ = math.max(maxZ, p.Position.Z)
    end
    local xSpan = maxX - minX
    local zSpan = maxZ - minZ
    -- Should extend primarily along one axis
    assert(xSpan > 20 or zSpan > 20, string.format("Parts don't extend far enough (X span=%.1f, Z span=%.1f, need > 20 on one axis)", xSpan, zSpan))
end

eval.check_game = function()
end

return eval
