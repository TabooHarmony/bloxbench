--!strict
-- @judge_rubric correctness="4 walls + roof + door gap + transparent display window" layout="square footprint, walls aligned, roof on top" aesthetics="2+ colors, window is transparent" completeness="walls + roof + door gap + display window"
-- @screenshot type=build angles=3

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
local HttpService = game:GetService("HttpService")
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_BUILD_001_pet_shop",
    prompt = {
        {
            {
                role = "user",
                content = [[Build a pet shop building on a baseplate. Requirements:
- 4 walls forming a square structure, minimum 20x20 studs footprint
- A roof on top of the walls
- A door opening in the front wall (minimum 4 studs wide, 5 studs tall — leave a gap, don't add a door part)
- A display window: a transparent part (Transparency 0.7) in the front wall, at least 6x4 studs
- Use at least 2 different colors across the structure]],
                request_id = "vb_build_001"
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
    -- Collect all parts in workspace (excluding baseplate)
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

    assert(#parts >= 5, string.format("Only %d parts found (excluding baseplate), need >= 5", #parts))

    -- Check for at least 2 different colors
    local colors = {}
    for _, p in ipairs(parts) do
        local c = p.BrickColor
        if c then
            colors[tostring(c)] = true
        end
    end
    local colorCount = 0
    for _ in pairs(colors) do colorCount = colorCount + 1 end
    assert(colorCount >= 2, string.format("Only %d distinct BrickColors found, need >= 2", colorCount))

    -- Check for a transparent part (display window)
    local hasTransparent = false
    for _, p in ipairs(parts) do
        if p.Transparency > 0.5 then
            hasTransparent = true
            break
        end
    end
    assert(hasTransparent, "No transparent part found (display window should have Transparency > 0.5)")

    -- Check for a roof: a part whose Y is higher than the average wall Y
    local maxY = 0
    local allY = {}
    for _, p in ipairs(parts) do
        table.insert(allY, p.Position.Y)
        if p.Position.Y > maxY then
            maxY = p.Position.Y
        end
    end
    -- At least one part should be notably higher (roof)
    local avgY = 0
    for _, y in ipairs(allY) do avgY = avgY + y end
    avgY = avgY / #allY
    assert(maxY > avgY + 3, string.format("No part found significantly above average Y (roof check). MaxY=%.1f AvgY=%.1f", maxY, avgY))
end

eval.check_game = function()
end

return eval
