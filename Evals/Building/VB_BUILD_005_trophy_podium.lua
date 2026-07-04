--!strict
-- @judge_rubric correctness="3 tiers at different heights, 1st tallest and centered, gold/silver/bronze colors" layout="stepped structure, 1st place in center" aesthetics="decorations on 1st place, 3 distinct top colors" completeness="3 platforms + decorations + correct coloring"
-- @screenshot type=build angles=3

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
local HttpService = game:GetService("HttpService")
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_BUILD_005_trophy_podium",
    prompt = {
        {
            {
                role = "user",
                content = [[Build a 3-tier winner's podium for a racing game. Requirements:
- 3 platform parts at different heights: 1st place tallest (6 studs), 2nd place (4 studs), 3rd place (2 studs)
- Each platform is 8x8 studs, flat on top
- 1st place platform is in the center, 2nd and 3rd are on either side
- Each platform has a different top color: 1st = gold/yellow, 2nd = silver/gray, 3rd = bronze/orange
- At least 2 decorative elements: flags or pillars on the 1st place platform, minimum 4 studs tall]],
                request_id = "vb_build_005"
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

    assert(#parts >= 3, string.format("Only %d parts found, need >= 3 (platforms)", #parts))

    -- Check for 3+ different colors (gold/silver/bronze)
    local colors = {}
    for _, p in ipairs(parts) do
        if p.BrickColor then
            colors[tostring(p.BrickColor)] = true
        end
    end
    local colorCount = 0
    for _ in pairs(colors) do colorCount = colorCount + 1 end
    assert(colorCount >= 3, string.format("Only %d distinct BrickColors found, need >= 3 (gold/silver/bronze)", colorCount))

    -- Find 3 platform parts at different Y heights
    -- Sort by Y position and check ascending
    local yPositions = {}
    for _, p in ipairs(parts) do
        table.insert(yPositions, p.Position.Y)
    end
    table.sort(yPositions)

    -- Should have at least 3 distinct Y levels (with some tolerance)
    local distinctY = {}
    for _, y in ipairs(yPositions) do
        local found = false
        for _, dy in ipairs(distinctY) do
            if math.abs(y - dy) < 1 then
                found = true
                break
            end
        end
        if not found then
            table.insert(distinctY, y)
        end
    end
    assert(#distinctY >= 2, string.format("Only %d distinct Y heights found, need >= 2 (different tier heights)", #distinctY))

    -- Check for decorations: parts above the tallest platform
    local maxY = yPositions[#yPositions]
    local decoCount = 0
    for _, p in ipairs(parts) do
        if p.Position.Y > maxY + 2 then
            decoCount = decoCount + 1
        end
    end
    -- Decorations might be thin parts on top, check for parts near maxY but above
    if decoCount < 2 then
        for _, p in ipairs(parts) do
            if p.Position.Y > maxY + 0.5 and p.Position.Y <= maxY + 2 then
                decoCount = decoCount + 1
            end
        end
    end
    assert(decoCount >= 2, string.format("Only %d decoration parts found above tallest platform, need >= 2", decoCount))
end

eval.check_game = function()
end

return eval
