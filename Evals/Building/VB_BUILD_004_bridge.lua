--!strict
-- @judge_rubric correctness="two banks gap bridge railings supports" layout="span over empty gap, banks on ends" aesthetics="wood materials" completeness="banks gap span railings supports"
-- @screenshot type=build angles=3 primary=side

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
local HttpService = game:GetService("HttpService")
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_BUILD_004_bridge",
    prompt = {
        {
            {
                role = "user",
                content = [[A wooden bridge spanning a gap between two raised banks, with railings and supports underneath]],
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

-- Minimal sanity only: built something non-trivial. Human is the real judge.
eval.check_scene = function()
    local parts = {}
    for _, obj in ipairs(workspace:GetChildren()) do
        if obj:IsA("BasePart") and obj.Name ~= "Baseplate" and not obj:IsA("Terrain") and obj.Name ~= "SpawnLocation" then
            table.insert(parts, obj)
        elseif obj:IsA("Folder") or obj:IsA("Model") or obj:IsA("Configuration") then
            for _, d in ipairs(obj:GetDescendants()) do
                if d:IsA("BasePart") and not d:IsA("Terrain") then
                    table.insert(parts, d)
                end
            end
        end
    end
    assert(#parts >= 8, string.format("Only %d parts found (excluding baseplate), need >= 8", #parts))
end

eval.check_game = function()
end

return eval
