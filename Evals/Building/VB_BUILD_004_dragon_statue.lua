--!nocheck
-- @fixture v1.build.004
-- @track building
-- @semantic StatueRoot,Pedestal,Body,Head,HornLeft,HornRight,WingLeft,WingRight,Tail,DisplayBounds
-- @runtime mode=edit
-- @evidence static=diagnostic video=not-applicable trace=not-applicable reset=required review=human-pairwise
-- @screenshot type=building angles=3 primary=hero
-- @knowledge profile=roblox-core-v1
-- @provenance origin="corpus-derived design brief" record="a026-combat-omega,a047-gag-v8,a048-garden-horizons" license=unknown
-- @judge_rubric focal="stylized dragon statue" relationships="pedestal body head horns wings tail"

local eval = {}

eval.scenario_name = "v1.build.004"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build one stylized dragon statue as a readable Roblox game-world landmark. Create exactly one top-level Model named BloxBenchCandidate and keep the entire build inside it. Include semantic components StatueRoot, Pedestal, Body, Head, HornLeft, HornRight, WingLeft, WingRight, Tail, and DisplayBounds. The body must visibly sit on the pedestal, the head and horns must establish a clear facing direction, and the wings and tail must support a coherent silhouette from front and three-quarter views. Use supported primitive or mesh instances without external asset IDs. Do not add NPC AI, combat, animation, or unrelated systems. Keep the statue stable, framed, and compact enough for a fixed camera to inspect.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "v1.build.004")
    return {marker = "dragon-statue-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "dragon-statue-cleanup"}
end

local required = {"StatueRoot", "Pedestal", "Body", "Head", "HornLeft", "HornRight", "WingLeft", "WingRight", "Tail", "DisplayBounds"}

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
    assert(boundsSize.X >= 8 and boundsSize.X <= 36, "statue width is outside the review envelope")
    assert(boundsSize.Z >= 8 and boundsSize.Z <= 36, "statue depth is outside the review envelope")
    local pedestal = position_of(model:FindFirstChild("Pedestal", true))
    local body = position_of(model:FindFirstChild("Body", true))
    local head = position_of(model:FindFirstChild("Head", true))
    assert(body.Y > pedestal.Y, "Body is not above the pedestal")
    assert(head.Y > body.Y, "Head is not above the body")
    local leftHorn = position_of(model:FindFirstChild("HornLeft", true))
    local rightHorn = position_of(model:FindFirstChild("HornRight", true))
    assert(math.abs(leftHorn.X - rightHorn.X) > 0.05 or math.abs(leftHorn.Z - rightHorn.Z) > 0.05, "horns are not distinct spatial components")
    for _, name in ipairs({"Pedestal", "Body", "Head", "WingLeft", "WingRight", "Tail"}) do
        local p = position_of(model:FindFirstChild(name, true))
        assert(math.abs(p.X - boundsCFrame.Position.X) <= boundsSize.X * 0.5 + 1, name .. " is outside DisplayBounds")
        assert(math.abs(p.Z - boundsCFrame.Position.Z) <= boundsSize.Z * 0.5 + 1, name .. " is outside DisplayBounds")
    end
    return {
        marker = "dragon-statue-scene-readback",
        required = present,
        bounds = {x = boundsSize.X, y = boundsSize.Y, z = boundsSize.Z},
        center = {x = boundsCFrame.Position.X, y = boundsCFrame.Position.Y, z = boundsCFrame.Position.Z},
        pedestal_y = pedestal.Y,
        body_y = body.Y,
        head_y = head.Y,
    }
end

return eval
