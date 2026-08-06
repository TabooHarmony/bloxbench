--!nocheck
-- @fixture v1.scene.003
-- @track scene
-- @semantic SceneRoot,StationEntrance,MachineCore,ControlConsole,ObservationWindow,WalkableRoute,ApproachStart,Viewpoint,SceneBounds
-- @runtime mode=edit
-- @evidence static=diagnostic video=not-applicable trace=not-applicable reset=required review=human-pairwise
-- @screenshot type=scene angles=3 primary=hero
-- @knowledge profile=roblox-core-v1
-- @provenance origin="corpus-derived design brief" record="a032-deepwoken,a052-hellverse,a053-hellverse" license=unknown
-- @judge_rubric focal="abandoned space station room" relationships="entrance machinery console window route"

local eval = {}

eval.scenario_name = "v1.scene.003"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build one abandoned space-station room as a compact Roblox game-level scene. Create exactly one top-level Model named BloxBenchCandidate and keep the entire build inside it. Include semantic components SceneRoot, StationEntrance, MachineCore, ControlConsole, ObservationWindow, WalkableRoute, ApproachStart, Viewpoint, and SceneBounds. Make the entrance, central machinery, console, and observation window establish a readable story and spatial hierarchy. Use restrained sci-fi lighting, beams, panels, or warning accents without filling the scene with opaque clutter. Keep ApproachStart and Viewpoint connected by an open route. Do not use external asset IDs, NPCs, data systems, hidden teleports, or extra top-level models.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "v1.scene.003")
    return {marker = "space-station-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "space-station-cleanup"}
end

local required = {"SceneRoot", "StationEntrance", "MachineCore", "ControlConsole", "ObservationWindow", "WalkableRoute", "ApproachStart", "Viewpoint", "SceneBounds"}

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
    local bounds = model:FindFirstChild("SceneBounds", true)
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
    assert(boundsSize.X >= 24 and boundsSize.X <= 64 and boundsSize.Z >= 24 and boundsSize.Z <= 64, "SceneBounds is outside the review envelope")
    local entrance = position_of(model:FindFirstChild("StationEntrance", true))
    local machine = position_of(model:FindFirstChild("MachineCore", true))
    local console = position_of(model:FindFirstChild("ControlConsole", true))
    local window = position_of(model:FindFirstChild("ObservationWindow", true))
    local start = position_of(model:FindFirstChild("ApproachStart", true))
    local view = position_of(model:FindFirstChild("Viewpoint", true))
    assert(math.abs(entrance.X - boundsCFrame.Position.X) <= boundsSize.X * 0.5 + 1, "StationEntrance is outside SceneBounds")
    assert(math.abs(machine.X - boundsCFrame.Position.X) <= boundsSize.X * 0.5 + 1, "MachineCore is outside SceneBounds")
    assert((console - machine).Magnitude < boundsSize.X + boundsSize.Z, "ControlConsole is disconnected from the machine area")
    assert((view - start).Magnitude > 4, "ApproachStart and Viewpoint are not distinct")
    assert(math.abs(window.Y - machine.Y) <= boundsSize.Y + 4, "ObservationWindow is not part of the scene composition")
    return {
        marker = "space-station-scene-readback",
        required = present,
        bounds = {x = boundsSize.X, y = boundsSize.Y, z = boundsSize.Z},
        center = {x = boundsCFrame.Position.X, y = boundsCFrame.Position.Y, z = boundsCFrame.Position.Z},
        machine = {x = machine.X, y = machine.Y, z = machine.Z},
        console_distance = (console - machine).Magnitude,
    }
end

return eval
