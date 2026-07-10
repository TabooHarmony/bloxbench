--!strict
-- @judge_rubric correctness="repair partial watchtower, connected shaft, lookout, door, battlements" layout="grounded tower, platform on shaft, door at base, battlements at top" aesthetics="coherent stone and wood materials" completeness="complete readable watchtower repair"
-- @screenshot type=build angles=3 primary=side

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_REPAIR_001_watchtower",
    prompt = {
        {
            {
                role = "user",
                content = [[
Repair the existing partial watchtower in the workspace rather than starting from an empty scene.

Make it a coherent medieval stone watchtower with:
- a grounded tower shaft and foundation
- a door at the base
- a lookout platform attached to the top
- battlements around the lookout
- a flag or flagpole if the existing structure supports it

Inspect the existing scene before editing. Preserve useful geometry, remove or reposition clearly
 disconnected pieces, and use raw execute_luau for all geometry changes. Finish by checking that the
 main tower, lookout, door, and battlements are present and visibly connected.
]],
                request_id = "vb_repair_001"
            }
        }
    },
    place = "baseplate.rbxl"
}

eval.setup = function()
    local target = Instance.new("Model")
    target.Name = "RepairTarget"
    target.Parent = workspace

    local function part(name: string, size: Vector3, cframe: CFrame, material: Enum.Material, color: Color3): Part
        local p = Instance.new("Part")
        p.Name = name
        p.Size = size
        p.CFrame = cframe
        p.Anchored = true
        p.Material = material
        p.Color = color
        p.Parent = target
        return p
    end

    local stone = Color3.fromRGB(105, 108, 112)
    local wood = Color3.fromRGB(115, 73, 43)

    part("Foundation", Vector3.new(12, 1, 12), CFrame.new(0, 0.5, 0), Enum.Material.Slate, stone)
    part("TowerShaft", Vector3.new(8, 14, 8), CFrame.new(0, 7.5, 0), Enum.Material.Cobblestone, stone)
    part("Door", Vector3.new(2.5, 4, 0.4), CFrame.new(0, 2.5, -4.2), Enum.Material.Wood, wood)

    -- intentionally misplaced upper assembly for the agent to diagnose and repair
    part("LookoutPlatform", Vector3.new(12, 1, 12), CFrame.new(9, 16, 1), Enum.Material.WoodPlanks, wood)
    local column = part("LookoutColumn", Vector3.new(4, 8, 4), CFrame.new(9, 20.5, 1), Enum.Material.Cobblestone, stone)
    column.Shape = Enum.PartType.Cylinder
    local roof = part("LooseRoof", Vector3.new(10, 1, 10), CFrame.new(9, 25, 1), Enum.Material.WoodPlanks, wood)
    roof.Transparency = 0.1
    part("LooseBattlement", Vector3.new(2, 2, 2), CFrame.new(14, 18, 1), Enum.Material.Slate, stone)
end

eval.reference = function()
end

eval.check_scene = function()
    local count = 0
    for _, obj in ipairs(workspace:GetDescendants()) do
        if obj:IsA("BasePart") and obj.Name ~= "Baseplate" and obj.Name ~= "SpawnLocation" then
            count += 1
        end
    end
    assert(count >= 8, string.format("Only %d repair parts found, need >= 8", count))
end

eval.check_game = function()
end

return eval
