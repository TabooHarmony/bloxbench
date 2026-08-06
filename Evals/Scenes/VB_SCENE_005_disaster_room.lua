--!nocheck
-- @fixture v1.scene.005
-- @track scene
-- @semantic SceneRoot,HazardSource,SafeRoute,GoalArea,WarningMarker,Refuge,ApproachStart,Viewpoint,SceneBounds
-- @runtime mode=edit
-- @evidence static=diagnostic video=not-applicable trace=not-applicable reset=required review=human-pairwise
-- @screenshot type=scene angles=3 primary=hero
-- @knowledge profile=roblox-core-v1
-- @provenance origin="corpus-derived design brief" record="a075-op-file-escape-tsunami,a081-pu-escape-tsunami,a113-survive-lava-for-cars" license=unknown
-- @judge_rubric focal="disaster escape diorama" relationships="hazard route warning refuge goal"

local eval = {}

eval.scenario_name = "v1.scene.005"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build a compact disaster-room escape diorama for a Roblox game level. Create exactly one top-level Model named BloxBenchCandidate and keep the entire build inside it. Include semantic components SceneRoot, HazardSource, SafeRoute, GoalArea, WarningMarker, Refuge, ApproachStart, Viewpoint, and SceneBounds. Make the hazard source visually legible, mark the danger without relying only on text, and create an open safe route from ApproachStart through a refuge toward GoalArea. The scene should communicate urgency while remaining readable from a fixed elevated camera. Use supported Roblox geometry, lighting, and effects; do not add hidden teleports, a real survival loop, damage logic, or unrelated progression.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "v1.scene.005")
    return {marker = "disaster-room-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "disaster-room-cleanup"}
end

local required = {"SceneRoot", "HazardSource", "SafeRoute", "GoalArea", "WarningMarker", "Refuge", "ApproachStart", "Viewpoint", "SceneBounds"}

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
    local hazard = position_of(model:FindFirstChild("HazardSource", true))
    local route = position_of(model:FindFirstChild("SafeRoute", true))
    local refuge = position_of(model:FindFirstChild("Refuge", true))
    local goal = position_of(model:FindFirstChild("GoalArea", true))
    local start = position_of(model:FindFirstChild("ApproachStart", true))
    local view = position_of(model:FindFirstChild("Viewpoint", true))
    assert(math.abs(hazard.X - boundsCFrame.Position.X) <= boundsSize.X * 0.5 + 1, "HazardSource is outside SceneBounds")
    assert((goal - start).Magnitude > 4, "ApproachStart and GoalArea are not distinct")
    assert((refuge - route).Magnitude < boundsSize.X + boundsSize.Z, "Refuge is disconnected from SafeRoute")
    assert((view - start).Magnitude > 4, "ApproachStart and Viewpoint are not distinct")
    return {
        marker = "disaster-room-scene-readback",
        required = present,
        bounds = {x = boundsSize.X, y = boundsSize.Y, z = boundsSize.Z},
        center = {x = boundsCFrame.Position.X, y = boundsCFrame.Position.Y, z = boundsCFrame.Position.Z},
        hazard = {x = hazard.X, y = hazard.Y, z = hazard.Z},
        route_to_refuge = (refuge - route).Magnitude,
    }
end

return eval
