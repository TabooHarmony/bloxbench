--!nocheck
-- @fixture v1.build.003
-- @track building
-- @semantic ArsenalRoot,MountPanel,PrimaryRack,SecondaryRack,DisplayWeapon01,DisplayWeapon02,SafeSign,DisplayBounds
-- @runtime mode=edit
-- @evidence static=diagnostic video=not-applicable trace=not-applicable reset=required review=human-pairwise
-- @screenshot type=building angles=3 primary=hero
-- @knowledge profile=roblox-core-v1
-- @provenance origin="corpus-derived design brief" record="a054-hiddenville-gun-system,a055-hood-gun-system" license=unknown
-- @judge_rubric focal="readable wall-mounted arsenal prop" relationships="panel racks displays safety sign"

local eval = {}

eval.scenario_name = "v1.build.003"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build one compact wall-mounted arsenal display prop for a Roblox game environment. Create exactly one top-level Model named BloxBenchCandidate and keep the entire build inside it. Include semantic components ArsenalRoot, MountPanel, PrimaryRack, SecondaryRack, DisplayWeapon01, DisplayWeapon02, SafeSign, and DisplayBounds. The rack must read as an organized display with visible mounting relationships, clear separation between primary and secondary storage, and a small safety or informational sign. Use placeholder geometry made from supported Roblox instances; do not use external asset IDs, a firing system, combat logic, inventory, or unrelated UI. Keep the prop stable and readable from one fixed elevated camera and from a side angle.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "v1.build.003")
    return {marker = "arsenal-rack-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "arsenal-rack-cleanup"}
end

local required = {"ArsenalRoot", "MountPanel", "PrimaryRack", "SecondaryRack", "DisplayWeapon01", "DisplayWeapon02", "SafeSign", "DisplayBounds"}

local function candidate()
    local model = workspace:FindFirstChild("BloxBenchCandidate")
    assert(model and model:IsA("Model"), "BloxBenchCandidate model is missing")
    return model
end

local function position_of(item)
    if item:IsA("BasePart") then
        return item.Position
    end
    if item:IsA("Model") then
        return item:GetPivot().Position
    end
    local part = item:FindFirstChildWhichIsA("BasePart", true)
    assert(part, "semantic component has no spatial part: " .. item.Name)
    return part.Position
end

eval.check_scene = function()
    local model = candidate()
    local present = {}
    for _, name in ipairs(required) do
        local item = model:FindFirstChild(name, true)
        assert(item, "missing semantic component: " .. name)
        present[name] = item.ClassName
    end
    local bounds = model:FindFirstChild("DisplayBounds", true)
    local boundsCFrame, boundsSize
    if bounds:IsA("BasePart") then
        boundsCFrame, boundsSize = bounds.CFrame, bounds.Size
    elseif bounds:IsA("Model") then
        boundsCFrame, boundsSize = bounds:GetBoundingBox()
    else
        local part = bounds:FindFirstChildWhichIsA("BasePart", true)
        assert(part, "bounds must contain a BasePart")
        boundsCFrame, boundsSize = part.CFrame, part.Size
    end
    assert(boundsSize.X >= 6 and boundsSize.X <= 32, "arsenal width is outside the review envelope")
    assert(boundsSize.Z >= 3 and boundsSize.Z <= 18, "arsenal depth is outside the review envelope")
    local panel = position_of(model:FindFirstChild("MountPanel", true))
    local primary = position_of(model:FindFirstChild("PrimaryRack", true))
    local secondary = position_of(model:FindFirstChild("SecondaryRack", true))
    assert(math.abs(panel.X - boundsCFrame.Position.X) <= boundsSize.X * 0.5 + 1, "MountPanel is outside DisplayBounds")
    assert(math.abs(primary.X - secondary.X) <= boundsSize.X + 1, "rack groups are not arranged together")
    for _, name in ipairs({"PrimaryRack", "SecondaryRack", "DisplayWeapon01", "DisplayWeapon02", "SafeSign"}) do
        local p = position_of(model:FindFirstChild(name, true))
        assert(math.abs(p.X - boundsCFrame.Position.X) <= boundsSize.X * 0.5 + 1, name .. " is outside DisplayBounds")
        assert(math.abs(p.Z - boundsCFrame.Position.Z) <= boundsSize.Z * 0.5 + 1, name .. " is outside DisplayBounds")
    end
    return {
        marker = "arsenal-rack-scene-readback",
        required = present,
        bounds = {x = boundsSize.X, y = boundsSize.Y, z = boundsSize.Z},
        center = {x = boundsCFrame.Position.X, y = boundsCFrame.Position.Y, z = boundsCFrame.Position.Z},
        panel = {x = panel.X, y = panel.Y, z = panel.Z},
    }
end

return eval
