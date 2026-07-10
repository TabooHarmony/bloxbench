--!strict
-- @judge_rubric correctness="repair the detached roof while preserving the existing watchtower" layout="roof centered over the lookout column and platform" aesthetics="coherent stone and wood materials" completeness="complete readable watchtower with no unnecessary edits"
-- @screenshot type=build angles=3 primary=side

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_REPAIR_002_roof_attachment",
    prompt = {
        {
            {
                role = "user",
                content = [[
Repair one specific defect in the existing watchtower: the roof is detached from the lookout assembly.

Move or repair only the part named LooseRoof so it is centered over the lookout column and platform.
Preserve the foundation, tower shaft, door, lookout platform, column, battlements, flagpole, and flag.
Do not rebuild the tower or redesign valid geometry. Inspect the existing scene before editing, use raw
execute_luau for the repair, and verify that the roof is supported and centered before finishing.
]],
                request_id = "vb_repair_002"
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
    local flagColor = Color3.fromRGB(150, 35, 35)

    part("Foundation", Vector3.new(12, 1, 12), CFrame.new(0, 0.5, 0), Enum.Material.Slate, stone)
    part("TowerShaft", Vector3.new(8, 14, 8), CFrame.new(0, 7.5, 0), Enum.Material.Cobblestone, stone)
    part("Door", Vector3.new(2.5, 4, 0.4), CFrame.new(0, 2.5, -4.2), Enum.Material.Wood, wood)
    part("LookoutPlatform", Vector3.new(12, 1, 12), CFrame.new(0, 15, 0), Enum.Material.WoodPlanks, wood)

    part("LookoutColumn", Vector3.new(4, 8, 4), CFrame.new(0, 19.5, 0), Enum.Material.Cobblestone, stone)

    -- only this part is intentionally misplaced
    local roof = part("LooseRoof", Vector3.new(10, 1, 10), CFrame.new(10, 24, 0), Enum.Material.WoodPlanks, wood)
    roof.Transparency = 0.1

    local battlementPositions = {
        Vector3.new(-4.5, 16.5, -5.5), Vector3.new(-1.5, 16.5, -5.5),
        Vector3.new(1.5, 16.5, -5.5), Vector3.new(4.5, 16.5, -5.5),
        Vector3.new(-4.5, 16.5, 5.5), Vector3.new(-1.5, 16.5, 5.5),
        Vector3.new(1.5, 16.5, 5.5), Vector3.new(4.5, 16.5, 5.5),
    }
    for index, position in ipairs(battlementPositions) do
        part("Battlement_" .. tostring(index), Vector3.new(2, 2, 2), CFrame.new(position), Enum.Material.Slate, stone)
    end

    part("Flagpole", Vector3.new(0.4, 6, 0.4), CFrame.new(0, 27, 0), Enum.Material.Wood, wood)
    part("Flag", Vector3.new(2.5, 1.5, 0.1), CFrame.new(1.3, 28.5, 0), Enum.Material.Fabric, flagColor)
end

eval.reference = function()
end

eval.check_scene = function()
    local target = workspace:FindFirstChild("RepairTarget")
    assert(target, "RepairTarget missing")
    local roof = target:FindFirstChild("LooseRoof")
    local column = target:FindFirstChild("LookoutColumn")
    assert(roof and roof:IsA("BasePart"), "LooseRoof missing")
    assert(column and column:IsA("BasePart"), "LookoutColumn missing")
    assert(math.abs(roof.Position.X) < 0.25, string.format("Roof x offset remains %.2f", roof.Position.X))
    assert(math.abs(roof.Position.Z) < 0.25, string.format("Roof z offset remains %.2f", roof.Position.Z))
    assert(math.abs(roof.Position.Y - 24) < 0.25, string.format("Roof y offset remains %.2f", roof.Position.Y))
    local count = 0
    for _, obj in ipairs(target:GetDescendants()) do
        if obj:IsA("BasePart") then count += 1 end
    end
    assert(count >= 16, string.format("Preservation failure, only %d parts remain", count))
end

eval.check_game = function()
end

return eval
