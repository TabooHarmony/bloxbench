--!nocheck
-- @fixture v1.build.002
-- @track building
-- @semantic AircraftRoot,Fuselage,Cockpit,WingLeft,WingRight,TailFin,LandingSupport,DisplayBounds
-- @runtime mode=edit
-- @evidence static=diagnostic video=not-applicable trace=not-applicable reset=required review=human-pairwise
-- @screenshot type=building angles=3 primary=hero
-- @knowledge profile=roblox-core-v1
-- @provenance origin="corpus-derived design brief" record="a016-build-a-plane,a017-build-a-plane" license=unknown
-- @judge_rubric focal="coherent fighter-jet silhouette" relationships="fuselage cockpit wings tail support"

local eval = {}

eval.scenario_name = "v1.build.002"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build one compact stylized fighter-jet display model as a Roblox game-world prop. Create exactly one top-level Model named BloxBenchCandidate and keep the entire build inside it. Include semantic components named AircraftRoot, Fuselage, Cockpit, WingLeft, WingRight, TailFin, LandingSupport, and DisplayBounds. The fuselage, cockpit, wings, and tail must read as one connected aircraft from elevated, front, and side views. Include a stable landing support or display mount, but do not add a flight system, weapons, external asset IDs, hidden teleports, or unrelated gameplay. Keep the silhouette legible and the footprint compact enough for one fixed review camera.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "v1.build.002")
    return {marker = "fighter-jet-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "fighter-jet-cleanup"}
end

local required = {"AircraftRoot", "Fuselage", "Cockpit", "WingLeft", "WingRight", "TailFin", "LandingSupport", "DisplayBounds"}

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
    assert(boundsSize.X >= 10 and boundsSize.X <= 44, "aircraft width is outside the review envelope")
    assert(boundsSize.Z >= 8 and boundsSize.Z <= 44, "aircraft depth is outside the review envelope")
    local fuselage = position_of(model:FindFirstChild("Fuselage", true))
    local cockpit = position_of(model:FindFirstChild("Cockpit", true))
    local left = position_of(model:FindFirstChild("WingLeft", true))
    local right = position_of(model:FindFirstChild("WingRight", true))
    assert(math.abs(cockpit.X - fuselage.X) <= boundsSize.X * 0.5 + 1, "Cockpit is outside the aircraft bounds")
    assert(math.abs(left.Z - right.Z) <= boundsSize.Z + 2, "wings are not arranged as a matched pair")
    for _, name in ipairs({"Fuselage", "Cockpit", "WingLeft", "WingRight", "TailFin", "LandingSupport"}) do
        local p = position_of(model:FindFirstChild(name, true))
        assert(math.abs(p.X - boundsCFrame.Position.X) <= boundsSize.X * 0.5 + 1, name .. " is outside DisplayBounds")
        assert(math.abs(p.Z - boundsCFrame.Position.Z) <= boundsSize.Z * 0.5 + 1, name .. " is outside DisplayBounds")
    end
    return {
        marker = "fighter-jet-scene-readback",
        required = present,
        bounds = {x = boundsSize.X, y = boundsSize.Y, z = boundsSize.Z},
        center = {x = boundsCFrame.Position.X, y = boundsCFrame.Position.Y, z = boundsCFrame.Position.Z},
        fuselage = {x = fuselage.X, y = fuselage.Y, z = fuselage.Z},
    }
end

return eval
