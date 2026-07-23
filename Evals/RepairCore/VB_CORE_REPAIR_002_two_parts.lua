local eval = {}
local EPSILON = 0.001

local function near(a, b)
    return math.abs(a - b) <= EPSILON
end

local function assert_vector(actual, expected, label)
    assert(near(actual.X, expected.X), label .. ".X")
    assert(near(actual.Y, expected.Y), label .. ".Y")
    assert(near(actual.Z, expected.Z), label .. ".Z")
end

local function assert_cframe(actual, expected, label)
    local a = {actual:GetComponents()}
    local e = {expected:GetComponents()}
    for i = 1, #e do
        assert(near(a[i], e[i]), label .. " component " .. i)
    end
end

local function assert_color(actual, expected, label)
    assert(near(actual.R, expected.R), label .. ".R")
    assert(near(actual.G, expected.G), label .. ".G")
    assert(near(actual.B, expected.B), label .. ".B")
end

local function make_part(parent, name, size, cframe, material, color)
    local part = Instance.new("Part")
    part.Name = name
    part.Size = size
    part.CFrame = cframe
    part.Anchored = true
    part.Material = material
    part.Color = color
    part.Transparency = 0
    part.CanCollide = true
    part.Parent = parent
    return part
end

local COLORS = {
    stone = Color3.fromRGB(105, 108, 112),
    wood = Color3.fromRGB(115, 73, 43),
    fabric = Color3.fromRGB(150, 35, 45),
}

local EXPECTED = {
    Foundation = {size = Vector3.new(12, 1, 12), material = Enum.Material.Slate, color = COLORS.stone, cframe = CFrame.new(0, 0.5, 0)},
    TowerShaft = {size = Vector3.new(6, 6, 6), material = Enum.Material.Cobblestone, color = COLORS.stone, cframe = CFrame.new(0, 4, 0)},
    LooseRoof = {size = Vector3.new(8, 1, 8), material = Enum.Material.WoodPlanks, color = COLORS.wood, cframe = CFrame.new(0, 7.5, 0)},
    Flagpole = {size = Vector3.new(0.4, 7, 0.4), material = Enum.Material.Metal, color = COLORS.stone, cframe = CFrame.new(0, 11, 0)},
    LooseFlag = {size = Vector3.new(2.5, 1.5, 0.1), material = Enum.Material.Fabric, color = COLORS.fabric, cframe = CFrame.new(1.3, 12.5, 0)},
}

eval.scenario_name = "VB_CORE_REPAIR_002_two_parts"
eval.description = "move two independent existing parts to exact attachment positions"
eval.place = "baseplate.rbxl"
eval.prompt = [[
Two existing parts are misplaced: LooseRoof and LooseFlag. Move both, and only those two parts, to their exact correct positions.
LooseRoof must be at (0, 7.5, 0). LooseFlag must be at (1.3, 12.5, 0) with identity rotation.
Fixing only one defect is failure. Do not create, delete, decorate, resize, recolor, or change materials or other properties.
]]

eval.setup = function()
    local old = workspace:FindFirstChild("RepairTarget")
    if old then old:Destroy() end
    local target = Instance.new("Model")
    target.Name = "RepairTarget"
    target.Parent = workspace
    make_part(target, "Foundation", EXPECTED.Foundation.size, EXPECTED.Foundation.cframe, EXPECTED.Foundation.material, EXPECTED.Foundation.color)
    make_part(target, "TowerShaft", EXPECTED.TowerShaft.size, EXPECTED.TowerShaft.cframe, EXPECTED.TowerShaft.material, EXPECTED.TowerShaft.color)
    make_part(target, "LooseRoof", EXPECTED.LooseRoof.size, CFrame.new(8, 7.5, 0), EXPECTED.LooseRoof.material, EXPECTED.LooseRoof.color)
    make_part(target, "Flagpole", EXPECTED.Flagpole.size, EXPECTED.Flagpole.cframe, EXPECTED.Flagpole.material, EXPECTED.Flagpole.color)
    make_part(target, "LooseFlag", EXPECTED.LooseFlag.size, CFrame.new(3, 12.5, 0), EXPECTED.LooseFlag.material, EXPECTED.LooseFlag.color)
end

eval.check_scene = function()
    local target = workspace:FindFirstChild("RepairTarget")
    assert(target and target:IsA("Model"), "RepairTarget missing")
    assert(#target:GetDescendants() == 5, "RepairTarget must contain exactly five descendants")
    for name, spec in pairs(EXPECTED) do
        local part = target:FindFirstChild(name)
        assert(part and part:IsA("BasePart"), name .. " missing or not a BasePart")
        assert(part.ClassName == "Part", name .. " class changed")
        assert(part.Name == name, name .. " name changed")
        assert(part.Parent == target, name .. " parent changed")
        assert_vector(part.Size, spec.size, name .. ".Size")
        assert(part.Material == spec.material, name .. " material changed")
        assert(part.Anchored == true, name .. " anchored changed")
        assert_color(part.Color, spec.color, name .. ".Color")
        assert(near(part.Transparency, 0), name .. " transparency changed")
        assert(part.CanCollide == true, name .. " collision changed")
        assert_cframe(part.CFrame, spec.cframe, name .. ".CFrame")
    end
    local pole = target.Flagpole
    local flag = target.LooseFlag
    local overlap = math.min(pole.Position.X + pole.Size.X / 2, flag.Position.X + flag.Size.X / 2) - math.max(pole.Position.X - pole.Size.X / 2, flag.Position.X - flag.Size.X / 2)
    assert(overlap >= 0.1, "LooseFlag must intersect Flagpole along X by at least 0.1 studs")
end

return eval
