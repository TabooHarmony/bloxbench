--!nocheck
-- @fixture v1.build.005
-- @track building
-- @semantic TowerRoot,Foundation,LowerLevel,UpperPlatform,Ladder,Roof,Flag,Viewpoint,DisplayBounds
-- @runtime mode=edit
-- @evidence static=diagnostic video=not-applicable trace=not-applicable reset=required review=human-pairwise
-- @screenshot type=building angles=3 primary=hero
-- @knowledge profile=roblox-core-v1
-- @provenance origin="research-spatial-relation pilot" record="watchtower-relation-pilot" license=unknown
-- @judge_rubric focal="coherent watchtower" relationships="foundation levels ladder roof flag viewpoint"

local eval = {}

eval.scenario_name = "v1.build.005"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build one compact watchtower landmark for a Roblox game level. Create exactly one top-level Model named BloxBenchCandidate and keep the entire build inside it. Include semantic components TowerRoot, Foundation, LowerLevel, UpperPlatform, Ladder, Roof, Flag, Viewpoint, and DisplayBounds. The lower level must visibly support the upper platform, the ladder must connect the levels, the roof must sit over the upper platform, and the flag must read as attached rather than floating. Include a safe viewpoint or overlook. Keep the tower stable and legible from elevated, front, and side views. Use supported Roblox instances only; do not add NPCs, missions, or unrelated gameplay.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "v1.build.005")
    return {marker = "watchtower-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "watchtower-cleanup"}
end

local required = {"TowerRoot", "Foundation", "LowerLevel", "UpperPlatform", "Ladder", "Roof", "Flag", "Viewpoint", "DisplayBounds"}

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
    local _placement_ok = boundsSize.X >= 8 and boundsSize.X <= 36
    if not _placement_ok then warn("watchtower width is outside the review envelope — non-blocking") end
    local _placement_ok = boundsSize.Z >= 8 and boundsSize.Z <= 36
    if not _placement_ok then warn("watchtower depth is outside the review envelope — non-blocking") end
    local foundation = position_of(model:FindFirstChild("Foundation", true))
    local lower = position_of(model:FindFirstChild("LowerLevel", true))
    local upper = position_of(model:FindFirstChild("UpperPlatform", true))
    local roof = position_of(model:FindFirstChild("Roof", true))
    assert(lower.Y >= foundation.Y, "LowerLevel is below Foundation")
    assert(upper.Y > lower.Y, "UpperPlatform is not above LowerLevel")
    assert(roof.Y > upper.Y, "Roof is not above UpperPlatform")
    local viewpoint = position_of(model:FindFirstChild("Viewpoint", true))
    local _placement_ok = math.abs(viewpoint.X - boundsCFrame.Position.X) <= boundsSize.X * 0.5 + 1
    if not _placement_ok then warn("Viewpoint is outside DisplayBounds — non-blocking") end
    local _placement_ok = math.abs(viewpoint.Z - boundsCFrame.Position.Z) <= boundsSize.Z * 0.5 + 1
    if not _placement_ok then warn("Viewpoint is outside DisplayBounds — non-blocking") end
    local ladder = position_of(model:FindFirstChild("Ladder", true))
    local _placement_ok = math.abs(ladder.X - upper.X) <= boundsSize.X + 1 and math.abs(ladder.Z - upper.Z) <= boundsSize.Z + 1
    if not _placement_ok then warn("Ladder is disconnected from the tower — non-blocking") end
    return {
        marker = "watchtower-scene-readback",
        required = present,
        bounds = {x = boundsSize.X, y = boundsSize.Y, z = boundsSize.Z},
        center = {x = boundsCFrame.Position.X, y = boundsCFrame.Position.Y, z = boundsCFrame.Position.Z},
        foundation_y = foundation.Y,
        lower_y = lower.Y,
        upper_y = upper.Y,
        roof_y = roof.Y,
    }
end

return eval
