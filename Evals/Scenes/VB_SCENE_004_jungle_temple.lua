--!nocheck
-- @fixture v1.scene.004
-- @track scene
-- @semantic SceneRoot,TempleEntrance,Threshold,StairRoute,ShrineObject,FramingWall,ApproachStart,Viewpoint,SceneBounds
-- @runtime mode=edit
-- @evidence static=diagnostic video=not-applicable trace=not-applicable reset=required review=human-pairwise
-- @screenshot type=scene angles=3 primary=hero
-- @knowledge profile=roblox-core-v1
-- @provenance origin="corpus-derived design brief" record="a009-map-evidence,a010-map-evidence,a011-map-evidence,a012-map-evidence" license=unknown
-- @judge_rubric focal="jungle temple entrance" relationships="entrance threshold stairs shrine framing route"

local eval = {}

eval.scenario_name = "v1.scene.004"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build a jungle-temple entrance as a compact Roblox game-level landmark. Create exactly one top-level Model named BloxBenchCandidate and keep the entire build inside it. Include semantic components SceneRoot, TempleEntrance, Threshold, StairRoute, ShrineObject, FramingWall, ApproachStart, Viewpoint, and SceneBounds. The entrance must frame a readable threshold, the stair route must lead toward the shrine object, and the framing wall or environmental pieces must support the focal hierarchy without making a maze. Add restrained vegetation, stone, light, or atmospheric accents using supported Roblox instances only. Keep the route open and inspectable from a fixed camera. Do not use external asset IDs, NPC logic, hidden teleports, or unrelated progression systems.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "v1.scene.004")
    return {marker = "jungle-temple-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "jungle-temple-cleanup"}
end

local required = {"SceneRoot", "TempleEntrance", "Threshold", "StairRoute", "ShrineObject", "FramingWall", "ApproachStart", "Viewpoint", "SceneBounds"}

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
    local _placement_ok = boundsSize.X >= 24 and boundsSize.X <= 64 and boundsSize.Z >= 24 and boundsSize.Z <= 64
    if not _placement_ok then warn("SceneBounds is outside the review envelope — non-blocking") end
    local entrance = position_of(model:FindFirstChild("TempleEntrance", true))
    local threshold = position_of(model:FindFirstChild("Threshold", true))
    local shrine = position_of(model:FindFirstChild("ShrineObject", true))
    local start = position_of(model:FindFirstChild("ApproachStart", true))
    local view = position_of(model:FindFirstChild("Viewpoint", true))
    local _placement_ok = (threshold - entrance).Magnitude <= boundsSize.X + boundsSize.Z
    if not _placement_ok then warn("Threshold is disconnected from TempleEntrance — non-blocking") end
    assert(shrine.Y >= threshold.Y - 2, "ShrineObject is hidden below the entrance threshold")
    local _placement_ok = (view - start).Magnitude > 4
    if not _placement_ok then warn("ApproachStart and Viewpoint are not distinct — non-blocking") end
    for _, name in ipairs({"TempleEntrance", "Threshold", "ShrineObject", "FramingWall", "ApproachStart", "Viewpoint"}) do
        local p = position_of(model:FindFirstChild(name, true))
        assert(math.abs(p.X - boundsCFrame.Position.X) <= boundsSize.X * 0.5 + 1, name .. " is outside SceneBounds")
        assert(math.abs(p.Z - boundsCFrame.Position.Z) <= boundsSize.Z * 0.5 + 1, name .. " is outside SceneBounds")
    end
    return {
        marker = "jungle-temple-scene-readback",
        required = present,
        bounds = {x = boundsSize.X, y = boundsSize.Y, z = boundsSize.Z},
        center = {x = boundsCFrame.Position.X, y = boundsCFrame.Position.Y, z = boundsCFrame.Position.Z},
        entrance_to_threshold = (threshold - entrance).Magnitude,
        threshold_to_shrine = (shrine - threshold).Magnitude,
    }
end

return eval
