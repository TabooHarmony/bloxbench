--!nocheck
-- @fixture v1.build.001
-- @track building
-- @semantic VehicleRoot,Chassis,Cockpit,WheelFrontLeft,WheelFrontRight,WheelRearLeft,WheelRearRight,DriverSeat,ControlPanel,DisplayBounds
-- @runtime mode=edit
-- @evidence static=diagnostic video=not-applicable trace=not-applicable reset=required review=human-pairwise
-- @screenshot type=building angles=3 primary=hero
-- @knowledge profile=roblox-core-v1
-- @provenance origin="corpus-derived design brief" record="a020-car-place,a021-car-crash-system" license=unknown
-- @judge_rubric focal="readable off-road vehicle" relationships="chassis cockpit wheels seat controls"

local eval = {}

eval.scenario_name = "v1.build.001"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build one compact open-top off-road buggy as a readable Roblox game-world prop. Create exactly one top-level Model named BloxBenchCandidate and keep the entire build inside it. The model must contain semantic components named VehicleRoot, Chassis, Cockpit, WheelFrontLeft, WheelFrontRight, WheelRearLeft, WheelRearRight, DriverSeat, ControlPanel, and DisplayBounds. Use ordinary supported Roblox instances and make the four wheels visibly correspond to the chassis rather than floating as unrelated decorations. Place DriverSeat inside the cockpit and make ControlPanel legible from the primary view. Keep the vehicle stable, coherent from front and side views, and small enough to inspect in a fixed elevated camera. Do not use external asset IDs, hidden teleports, extra top-level models, unrelated gameplay systems, or a fake score based on part counts.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "v1.build.001")
    return {marker = "offroad-buggy-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "offroad-buggy-cleanup"}
end

local required = {
    "VehicleRoot", "Chassis", "Cockpit", "WheelFrontLeft", "WheelFrontRight",
    "WheelRearLeft", "WheelRearRight", "DriverSeat", "ControlPanel", "DisplayBounds",
}

local function get_candidate()
    local candidate = workspace:FindFirstChild("BloxBenchCandidate")
    assert(candidate and candidate:IsA("Model"), "BloxBenchCandidate model is missing")
    return candidate
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

local function bounds_of(item)
    if item:IsA("BasePart") then
        return item.CFrame, item.Size
    end
    if item:IsA("Model") then
        return item:GetBoundingBox()
    end
    local part = item:FindFirstChildWhichIsA("BasePart", true)
    assert(part, "DisplayBounds has no spatial part")
    return part.CFrame, part.Size
end

eval.check_scene = function()
    local candidate = get_candidate()
    local present = {}
    for _, name in ipairs(required) do
        local item = candidate:FindFirstChild(name, true)
        assert(item, "missing semantic component: " .. name)
        present[name] = item.ClassName
    end
    local boundsCFrame, boundsSize = bounds_of(candidate:FindFirstChild("DisplayBounds", true))
    assert(boundsSize.X >= 8 and boundsSize.X <= 36, "DisplayBounds width is outside the compact review envelope")
    assert(boundsSize.Z >= 6 and boundsSize.Z <= 30, "DisplayBounds depth is outside the compact review envelope")
    local chassis = position_of(candidate:FindFirstChild("Chassis", true))
    local cockpit = position_of(candidate:FindFirstChild("Cockpit", true))
    local seat = position_of(candidate:FindFirstChild("DriverSeat", true))
    assert(math.abs(cockpit.X - chassis.X) <= boundsSize.X * 0.5 + 1, "Cockpit is outside DisplayBounds")
    assert(math.abs(seat.X - cockpit.X) <= 8 and math.abs(seat.Z - cockpit.Z) <= 8, "DriverSeat is not inside the cockpit area")
    local wheelNames = {"WheelFrontLeft", "WheelFrontRight", "WheelRearLeft", "WheelRearRight"}
    local wheelPositions = {}
    for _, name in ipairs(wheelNames) do
        local position = position_of(candidate:FindFirstChild(name, true))
        wheelPositions[name] = {x = position.X, y = position.Y, z = position.Z}
        assert(math.abs(position.X - boundsCFrame.Position.X) <= boundsSize.X * 0.5 + 1, name .. " is outside DisplayBounds")
        assert(math.abs(position.Z - boundsCFrame.Position.Z) <= boundsSize.Z * 0.5 + 1, name .. " is outside DisplayBounds")
    end
    local root = candidate:FindFirstChild("VehicleRoot", true)
    assert(root, "VehicleRoot is missing")
    return {
        marker = "offroad-buggy-scene-readback",
        required = present,
        bounds = {x = boundsSize.X, y = boundsSize.Y, z = boundsSize.Z},
        center = {x = boundsCFrame.Position.X, y = boundsCFrame.Position.Y, z = boundsCFrame.Position.Z},
        wheel_positions = wheelPositions,
        root_class = root.ClassName,
    }
end

return eval
