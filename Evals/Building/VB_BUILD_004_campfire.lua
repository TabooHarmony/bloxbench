--!strict
-- @judge_rubric correctness="cylinder fire pit + flame parts above + 4 seating logs around pit" layout="logs arranged in square around fire, nature elements around scene" aesthetics="4+ colors, fire colors are orange/red/yellow" completeness="fire pit + fire + 4 logs + 4 nature elements"
-- @screenshot type=build angles=3

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
local HttpService = game:GetService("HttpService")
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_BUILD_004_campfire",
    prompt = {
        {
            {
                role = "user",
                content = [[Build a campfire scene. Requirements:
- Fire pit: a Cylinder part, radius ~3 studs, height ~1 stud, dark color (black or dark gray)
- Fire: 3-5 parts stacked above the pit representing flames, colored orange/red/yellow, different sizes
- 4 seating logs: Cylinder parts arranged in a square around the fire pit, radius ~1, length ~5 studs, brown color
- At least 4 nature elements (trees, rocks, bushes) around the scene using different part shapes
- Use at least 4 different colors total]],
                request_id = "vb_build_004"
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

    -- Need: 1 pit + 3 fire + 4 logs + 4 nature = 12 minimum
    assert(#parts >= 12, string.format("Only %d parts found, need >= 12 (pit + fire + logs + nature)", #parts))

    -- Find at least 1 cylinder (fire pit)
    local cylCount = 0
    for _, p in ipairs(parts) do
        if p:IsA("Part") and p.Shape == Enum.PartType.Cylinder then
            cylCount = cylCount + 1
        elseif p.ClassName == "Part" and p.Shape == Enum.PartType.Cylinder then
            cylCount = cylCount + 1
        end
    end
    -- Cylinders in Roblox can be Part with Shape=Cylinder or just check ClassName
    -- Also check for Cylinder class directly
    for _, p in ipairs(parts) do
        if p.Shape == Enum.PartType.Cylinder then
            cylCount = cylCount + 1
            break -- already counted, just need one
        end
    end
    assert(cylCount >= 1, "No cylinder part found (fire pit should be a cylinder)")

    -- Check for 4+ different colors
    local colors = {}
    for _, p in ipairs(parts) do
        if p.BrickColor then
            colors[tostring(p.BrickColor)] = true
        end
    end
    local colorCount = 0
    for _ in pairs(colors) do colorCount = colorCount + 1 end
    assert(colorCount >= 4, string.format("Only %d distinct BrickColors found, need >= 4", colorCount))

    -- Check for parts above ground level (fire + nature)
    local aboveCount = 0
    for _, p in ipairs(parts) do
        if p.Position.Y > 1.5 then
            aboveCount = aboveCount + 1
        end
    end
    assert(aboveCount >= 3, string.format("Only %d parts above Y=1.5, need >= 3 (fire parts)", aboveCount))
end

eval.check_game = function()
end

return eval
