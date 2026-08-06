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
        content = [[Build a compact disaster-room escape diorama for a Roblox game level. Create exactly one top-level Model named BloxBenchCandidate and keep the entire build inside it. Inside that model, create Instance objects with the EXACT names SceneRoot, HazardSource, SafeRoute, GoalArea, WarningMarker, Refuge, ApproachStart, Viewpoint, and SceneBounds.

What each name must be (all are Instances, not attributes):
- SceneRoot: a Part or Model that is the room floor/ground (e.g. a Part named SceneRoot, Size roughly 24-64 square, Anchored, positioned at the center). The model MUST contain an Instance literally named "SceneRoot" — do not use an attribute.
- SceneBounds: a Part or Model whose footprint is 24-64 wide (X) by 24-64 deep (Z), marking the scene bounds for the camera (can be the same footprint as SceneRoot).
- HazardSource, SafeRoute, GoalArea, WarningMarker, Refuge, ApproachStart, Viewpoint: Instances (Parts or small Models containing Parts/decals/particles) with those exact names.

Make the hazard source visually legible, mark the danger without relying only on text, and create an open safe route from ApproachStart through a refuge toward GoalArea. The scene should communicate urgency while remaining readable from a fixed elevated camera. Use supported Roblox geometry, lighting, and effects; do not add hidden teleports, a real survival loop, damage logic, or unrelated progression.]]
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
    -- Non-blocking: envelope guidance, not a gate. A diorama slightly out of
    -- the ideal frame still deserves a human vote via the place file.
    local envelope_ok = boundsSize.X >= 24 and boundsSize.X <= 64 and boundsSize.Z >= 24 and boundsSize.Z <= 64
    if not envelope_ok then warn(("SceneBounds outside ideal envelope (%.1f x %.1f) — non-blocking"):format(boundsSize.X, boundsSize.Z)) end
    local hazard = position_of(model:FindFirstChild("HazardSource", true))
    local route = position_of(model:FindFirstChild("SafeRoute", true))
    local refuge = position_of(model:FindFirstChild("Refuge", true))
    local goal = position_of(model:FindFirstChild("GoalArea", true))
    local start = position_of(model:FindFirstChild("ApproachStart", true))
    local view = position_of(model:FindFirstChild("Viewpoint", true))
    local hazard_inside = math.abs(hazard.X - boundsCFrame.Position.X) <= boundsSize.X * 0.5 + 1
    local distinct_start_goal = (goal - start).Magnitude > 4
    local refuge_connected = (refuge - route).Magnitude < boundsSize.X + boundsSize.Z
    local distinct_view_start = (view - start).Magnitude > 4
    if not hazard_inside then warn("HazardSource is outside SceneBounds — non-blocking") end
    if not distinct_start_goal then warn("ApproachStart and GoalArea are not distinct — non-blocking") end
    if not refuge_connected then warn("Refuge is disconnected from SafeRoute — non-blocking") end
    if not distinct_view_start then warn("ApproachStart and Viewpoint are not distinct — non-blocking") end
    return {
        marker = "disaster-room-scene-readback",
        required = present,
        bounds = {x = boundsSize.X, y = boundsSize.Y, z = boundsSize.Z},
        center = {x = boundsCFrame.Position.X, y = boundsCFrame.Position.Y, z = boundsCFrame.Position.Z},
        hazard = {x = hazard.X, y = hazard.Y, z = hazard.Z},
        route_to_refuge = (refuge - route).Magnitude,
        envelope_ok = envelope_ok,
        hazard_inside = hazard_inside,
    }
end

return eval
