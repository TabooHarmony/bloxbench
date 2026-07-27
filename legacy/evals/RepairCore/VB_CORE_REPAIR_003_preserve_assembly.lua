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

local STONE = Color3.fromRGB(105, 108, 112)
local WOOD = Color3.fromRGB(115, 73, 43)
local RELATIVE = {
    CornerNW = CFrame.new(-3.5, 1.5, -3.5),
    CornerNE = CFrame.new(3.5, 1.5, -3.5),
    CornerSW = CFrame.new(-3.5, 1.5, 3.5),
    CornerSE = CFrame.new(3.5, 1.5, 3.5),
    Cap = CFrame.new(0, 3, 0),
}
local PART_NAMES = {"Foundation", "TowerShaft", "Platform", "CornerNW", "CornerNE", "CornerSW", "CornerSE", "Cap"}

eval.scenario_name = "VB_CORE_REPAIR_003_preserve_assembly"
eval.description = "translate one existing upper assembly while preserving its child transforms and identity"
eval.place = "baseplate.rbxl"
eval.prompt = [[
Only the existing UpperAssembly may move. It is a rigid group whose pivot is displaced 10 studs on X.
Translate that assembly left by 10 studs. Do not rebuild, replace, delete, add, decorate, resize, or edit any child relationship.
Foundation and TowerShaft must remain unchanged, and every child must keep its exact transform relative to Platform.
]]

eval.setup = function()
    local old = workspace:FindFirstChild("RepairTarget")
    if old then old:Destroy() end
    local old_identity = game:GetService("ServerStorage"):FindFirstChild("RepairCoreIdentity")
    if old_identity then old_identity:Destroy() end

    local target = Instance.new("Model")
    target.Name = "RepairTarget"
    target.Parent = workspace
    make_part(target, "Foundation", Vector3.new(12, 1, 12), CFrame.new(0, 0.5, 0), Enum.Material.Slate, STONE)
    make_part(target, "TowerShaft", Vector3.new(6, 6, 6), CFrame.new(0, 4, 0), Enum.Material.Cobblestone, STONE)

    local assembly = Instance.new("Model")
    assembly.Name = "UpperAssembly"
    assembly.Parent = target
    local platform = make_part(assembly, "Platform", Vector3.new(8, 1, 8), CFrame.new(0, 7.5, 0), Enum.Material.WoodPlanks, WOOD)
    for name, relative in pairs(RELATIVE) do
        local size = name == "Cap" and Vector3.new(6, 1, 6) or Vector3.new(1, 2, 1)
        local material = name == "Cap" and Enum.Material.WoodPlanks or Enum.Material.Slate
        local color = name == "Cap" and WOOD or STONE
        make_part(assembly, name, size, CFrame.new(0, 7.5, 0) * relative, material, color)
    end
    assembly.PrimaryPart = platform
    assembly:PivotTo(CFrame.new(10, 7.5, 0))

    local identity = Instance.new("Folder")
    identity.Name = "RepairCoreIdentity"
    identity.Parent = game:GetService("ServerStorage")
    for _, name in ipairs(PART_NAMES) do
        local value = Instance.new("ObjectValue")
        value.Name = name
        value.Value = target:FindFirstChild(name, true)
        value.Parent = identity
    end
end

eval.check_scene = function()
    local target = workspace:FindFirstChild("RepairTarget")
    assert(target and target:IsA("Model"), "RepairTarget missing")
    local assembly = target:FindFirstChild("UpperAssembly")
    assert(assembly and assembly:IsA("Model"), "UpperAssembly missing")
    assert(#target:GetDescendants() == 9, "RepairTarget has unexpected descendants")
    assert(#assembly:GetDescendants() == 6, "UpperAssembly has unexpected descendants")
    assert_cframe(assembly:GetPivot(), CFrame.new(0, 7.5, 0), "UpperAssembly pivot")

    local foundation = target:FindFirstChild("Foundation")
    local shaft = target:FindFirstChild("TowerShaft")
    assert(foundation and shaft, "fixed tower parts missing")
    assert(foundation.ClassName == "Part" and shaft.ClassName == "Part", "fixed tower class changed")
    assert(foundation.Name == "Foundation" and shaft.Name == "TowerShaft", "fixed tower name changed")
    assert(foundation.Parent == target and shaft.Parent == target, "fixed tower parent changed")
    assert_vector(foundation.Size, Vector3.new(12, 1, 12), "Foundation.Size")
    assert_vector(shaft.Size, Vector3.new(6, 6, 6), "TowerShaft.Size")
    assert(foundation.Material == Enum.Material.Slate and shaft.Material == Enum.Material.Cobblestone, "fixed tower material changed")
    assert(foundation.Anchored == true and shaft.Anchored == true, "fixed tower anchored changed")
    assert_color(foundation.Color, STONE, "Foundation.Color")
    assert_color(shaft.Color, STONE, "TowerShaft.Color")
    assert(near(foundation.Transparency, 0) and near(shaft.Transparency, 0), "fixed tower transparency changed")
    assert(foundation.CanCollide == true and shaft.CanCollide == true, "fixed tower collision changed")
    assert_cframe(foundation.CFrame, CFrame.new(0, 0.5, 0), "Foundation.CFrame")
    assert_cframe(shaft.CFrame, CFrame.new(0, 4, 0), "TowerShaft.CFrame")

    local platform = assembly:FindFirstChild("Platform")
    assert(platform and platform:IsA("BasePart"), "Platform missing")
    assert(platform.ClassName == "Part" and platform.Name == "Platform", "Platform identity changed")
    assert(platform.Parent == assembly, "Platform parent changed")
    assert_vector(platform.Size, Vector3.new(8, 1, 8), "Platform.Size")
    assert(platform.Material == Enum.Material.WoodPlanks, "Platform material changed")
    assert(platform.Anchored == true and platform.CanCollide == true, "Platform properties changed")
    assert(near(platform.Transparency, 0), "Platform transparency changed")
    assert_color(platform.Color, WOOD, "Platform.Color")
    assert_cframe(platform.CFrame, CFrame.new(0, 7.5, 0), "Platform.CFrame")

    for name, relative in pairs(RELATIVE) do
        local part = assembly:FindFirstChild(name)
        assert(part and part:IsA("BasePart"), name .. " missing")
        assert(part.ClassName == "Part" and part.Name == name, name .. " identity changed")
        assert(part.Parent == assembly, name .. " parent changed")
        local size = name == "Cap" and Vector3.new(6, 1, 6) or Vector3.new(1, 2, 1)
        local material = name == "Cap" and Enum.Material.WoodPlanks or Enum.Material.Slate
        local color = name == "Cap" and WOOD or STONE
        assert_vector(part.Size, size, name .. ".Size")
        assert(part.Material == material, name .. " material changed")
        assert(part.Anchored == true and part.CanCollide == true, name .. " properties changed")
        assert(near(part.Transparency, 0), name .. " transparency changed")
        assert_color(part.Color, color, name .. ".Color")
        assert_cframe(platform.CFrame:ToObjectSpace(part.CFrame), relative, name .. " relative CFrame")
    end

    local identity = game:GetService("ServerStorage"):FindFirstChild("RepairCoreIdentity")
    assert(identity and identity:IsA("Folder"), "RepairCoreIdentity missing")
    assert(#identity:GetChildren() == #PART_NAMES, "identity record count changed")
    for _, name in ipairs(PART_NAMES) do
        local record = identity:FindFirstChild(name)
        local live = target:FindFirstChild(name, true)
        assert(record and record:IsA("ObjectValue") and record.Value == live, name .. " identity changed")
        if name == "Foundation" or name == "TowerShaft" then
            assert(live.Parent == target, name .. " parent changed")
        else
            assert(live.Parent == assembly, name .. " parent changed")
        end
    end
end

return eval
