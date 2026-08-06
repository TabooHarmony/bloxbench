--!nocheck
-- @fixture v1.scene.002
-- @track scene
-- @semantic SceneRoot,MarketEntrance,ShopFront01,ShopFront02,FocalSign,Stall,WalkableRoute,ApproachStart,Viewpoint,SceneBounds
-- @runtime mode=edit
-- @evidence static=diagnostic video=not-applicable trace=not-applicable reset=required review=human-pairwise
-- @screenshot type=scene angles=3 primary=hero
-- @knowledge profile=roblox-core-v1
-- @provenance origin="corpus-derived design brief" record="a006-ai-test,urban-shop-patterns" license=unknown
-- @judge_rubric focal="night-market alley" relationships="entrance shops sign stall route viewpoint"

local eval = {}

eval.scenario_name = "v1.scene.002"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build an open night-market alley scene as a compact Roblox game-level environment. Create exactly one top-level Model named BloxBenchCandidate and keep the entire build inside it. Include semantic components SceneRoot, MarketEntrance, ShopFront01, ShopFront02, FocalSign, Stall, WalkableRoute, ApproachStart, Viewpoint, and SceneBounds. Establish a readable entrance and a focal sign, give the two shop fronts a coherent street rhythm, and add one stall or display that supports the market identity. Use layered but restrained lighting or emissive accents. Make the route visibly walkable from ApproachStart to Viewpoint, keep the scene open enough for inspection, and avoid opaque corridor mazes. Do not use external asset IDs, hidden teleports, NPC logic, economy systems, or extra top-level models.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "v1.scene.002")
    return {marker = "night-market-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "night-market-cleanup"}
end

local required = {"SceneRoot", "MarketEntrance", "ShopFront01", "ShopFront02", "FocalSign", "Stall", "WalkableRoute", "ApproachStart", "Viewpoint", "SceneBounds"}

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

local function bounds_of(item)
    if item:IsA("BasePart") then
        return item.CFrame, item.Size
    end
    if item:IsA("Model") then
        return item:GetBoundingBox()
    end
    local part = item:FindFirstChildWhichIsA("BasePart", true)
    assert(part, "SceneBounds has no spatial part")
    return part.CFrame, part.Size
end

eval.check_scene = function()
    local model = candidate()
    local present = {}
    for _, name in ipairs(required) do
        local item = model:FindFirstChild(name, true)
        assert(item, "missing semantic component: " .. name)
        present[name] = item.ClassName
    end
    local boundsCFrame, boundsSize = bounds_of(model:FindFirstChild("SceneBounds", true))
    assert(boundsSize.X >= 24 and boundsSize.X <= 64 and boundsSize.Z >= 24 and boundsSize.Z <= 64, "SceneBounds is outside the review envelope")
    local entrance = position_of(model:FindFirstChild("MarketEntrance", true))
    local sign = position_of(model:FindFirstChild("FocalSign", true))
    local shop1 = position_of(model:FindFirstChild("ShopFront01", true))
    local shop2 = position_of(model:FindFirstChild("ShopFront02", true))
    local start = position_of(model:FindFirstChild("ApproachStart", true))
    local view = position_of(model:FindFirstChild("Viewpoint", true))
    assert(math.abs(entrance.X - boundsCFrame.Position.X) <= boundsSize.X * 0.5 + 1, "MarketEntrance is outside SceneBounds")
    assert(math.abs(sign.X - boundsCFrame.Position.X) <= boundsSize.X * 0.5 + 1, "FocalSign is outside SceneBounds")
    assert(math.abs(shop1.Z - shop2.Z) <= boundsSize.Z + 1, "shop fronts are not part of one alley composition")
    assert((view - start).Magnitude > 4, "ApproachStart and Viewpoint are not distinct")
    return {
        marker = "night-market-scene-readback",
        required = present,
        bounds = {x = boundsSize.X, y = boundsSize.Y, z = boundsSize.Z},
        center = {x = boundsCFrame.Position.X, y = boundsCFrame.Position.Y, z = boundsCFrame.Position.Z},
        entrance = {x = entrance.X, y = entrance.Y, z = entrance.Z},
        focal_sign = {x = sign.X, y = sign.Y, z = sign.Z},
    }
end

return eval
