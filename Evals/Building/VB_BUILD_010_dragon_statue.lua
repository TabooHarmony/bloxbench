--!strict
-- @judge_rubric correctness="body wings tail raised head" layout="limbs attached to body, wings spread or folded" aesthetics="dragon silhouette readable" completeness="body wings tail head"
-- @screenshot type=build angles=3 primary=front

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
local HttpService = game:GetService("HttpService")
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_BUILD_010_dragon_statue",
    prompt = {
        {
            {
                role = "user",
                content = [[A dragon statue with wings, tail, and a raised head. Make it one connected assembly: ground the pedestal, attach the body to it, attach the neck to the body, attach the head to the neck, and start each leg, wing, and tail chain from an existing body part.]],
                request_id = "vb_build_010"
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
