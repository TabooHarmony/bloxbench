--!nocheck
-- @fixture pilot.waterfall
-- @track scene
-- @semantic LandmarkRoot,WaterSource,WaterfallBody,ImpactPool,MistEmitter,ApproachStart,Viewpoint,WalkableRoute,SceneBounds
-- @states capture
-- @runtime mode=edit
-- @evidence static=required video=optional trace=required reset=required review=human-pairwise
-- @screenshot type=scene angles=1 primary=hero
-- @judge_rubric focal="waterfall landmark" relationships="source body pool route"

local eval = {}

eval.scenario_name = "pilot.waterfall"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build an open approximately 48 by 48 stud game-level landmark scene centered on a waterfall. Create exactly one top-level Model named BloxBenchCandidate and a SceneBounds component that makes the intended footprint legible. Water must descend from a raised WaterSource over a visible WaterfallBody into an ImpactPool, with a MistEmitter or spray effect concentrated near the impact. Include an ApproachStart, a Viewpoint or overlook, and a WalkableRoute that connects them without hidden teleports. Add terrain framing and a small number of supporting game-world details such as rocks, path markers, vegetation, a bridge, or a service platform, but keep the waterfall as the focal hierarchy.

The scene must be inspectable from one fixed elevated isometric camera. Keep the route open and walkable, make visible collision agree with the route, and avoid opaque roofs, deep interiors, and corridor mazes. Add a BloxBenchState attribute and a BloxBenchRuntime folder or attributes that report route_walkable and effect_active. Add a BloxBenchTrace folder or attributes for the capture readback. Use only supported Roblox classes and enums. The evaluator will observe the scene and effect; it must not create a replacement waterfall or infer beauty from part counts.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "pilot.waterfall")
    return {marker = "waterfall-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "waterfall-cleanup"}
end

local required = {
    "LandmarkRoot", "WaterSource", "WaterfallBody", "ImpactPool", "MistEmitter",
    "ApproachStart", "Viewpoint", "WalkableRoute", "SceneBounds",
}

local function get_candidate()
    local candidate = workspace:FindFirstChild("BloxBenchCandidate")
    assert(candidate and candidate:IsA("Model"), "BloxBenchCandidate model is missing")
    return candidate
end

local function get_required(candidate)
    local present = {}
    for _, name in ipairs(required) do
        local item = candidate:FindFirstChild(name, true)
        assert(item, "missing semantic component: " .. name)
        present[name] = item.ClassName
    end
    return present
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
    assert(part, "spatial component has no BasePart: " .. item.Name)
    return part.CFrame, part.Size
end

local function contains_xz(boundsCFrame, boundsSize, position)
    return math.abs(position.X - boundsCFrame.Position.X) <= boundsSize.X * 0.5 + 1
        and math.abs(position.Z - boundsCFrame.Position.Z) <= boundsSize.Z * 0.5 + 1
end

local function route_collision(route)
    if route:IsA("BasePart") then
        return route.CanCollide
    end
    for _, part in ipairs(route:GetDescendants()) do
        if part:IsA("BasePart") and part.CanCollide then
            return true
        end
    end
    return false
end

local function trace_last(trace)
    if not trace then
        return nil
    end
    local last = trace:GetAttribute("last_event")
    if type(last) == "string" then
        return last
    end
    local values = {}
    for _, item in ipairs(trace:GetChildren()) do
        if item:IsA("StringValue") then
            table.insert(values, item.Value)
        end
    end
    return values[#values]
end

local function effect_node(candidate)
    local node = candidate:FindFirstChild("MistEmitter", true)
    assert(node, "MistEmitter is missing")
    if node:IsA("ParticleEmitter") then
        return node
    end
    return node:FindFirstChildWhichIsA("ParticleEmitter", true) or node
end

eval.check_scene = function()
    local candidate = get_candidate()
    local present = get_required(candidate)
    local effect = effect_node(candidate)
    assert(effect:IsA("ParticleEmitter") or effect:GetAttribute("effect_active") ~= nil, "MistEmitter has no observable effect")
    local source = candidate:FindFirstChild("WaterSource", true)
    local body = candidate:FindFirstChild("WaterfallBody", true)
    local pool = candidate:FindFirstChild("ImpactPool", true)
    local approach = candidate:FindFirstChild("ApproachStart", true)
    local viewpoint = candidate:FindFirstChild("Viewpoint", true)
    local route = candidate:FindFirstChild("WalkableRoute", true)
    local bounds = candidate:FindFirstChild("SceneBounds", true)
    local sourcePosition = position_of(source)
    local bodyPosition = position_of(body)
    local poolPosition = position_of(pool)
    local approachPosition = position_of(approach)
    local viewpointPosition = position_of(viewpoint)
    assert(sourcePosition.Y > bodyPosition.Y, "water source is not above waterfall body")
    assert(bodyPosition.Y > poolPosition.Y, "waterfall body is not above impact pool")
    assert(route:IsA("BasePart") or route:IsA("Model"), "WalkableRoute is not spatial")
    assert(bounds:IsA("BasePart") or bounds:IsA("Model"), "SceneBounds is not spatial")
    local boundsCFrame, boundsSize = bounds_of(bounds)
    assert(boundsSize.X >= 32 and boundsSize.X <= 64 and boundsSize.Z >= 32 and boundsSize.Z <= 64, "SceneBounds is outside the review envelope")
    for _, position in ipairs({sourcePosition, bodyPosition, poolPosition, approachPosition, viewpointPosition}) do
        assert(contains_xz(boundsCFrame, boundsSize, position), "focal component is outside SceneBounds")
    end
    local routeCFrame, routeSize = bounds_of(route)
    assert(route_collision(route), "WalkableRoute has no collidable surface")
    assert(contains_xz(routeCFrame, routeSize, approachPosition) and contains_xz(routeCFrame, routeSize, viewpointPosition), "WalkableRoute does not span route endpoints")
    local effectParent = effect:IsA("ParticleEmitter") and effect.Parent or effect
    local effectPosition = position_of(effectParent)
    assert((effectPosition - poolPosition).Magnitude <= 12, "MistEmitter is not concentrated near ImpactPool")
    local runtime = candidate:FindFirstChild("BloxBenchRuntime", true)
    assert(runtime and runtime:GetAttribute("route_walkable") == true, "runtime route is not walkable")
    local effectActive = effect:IsA("ParticleEmitter") and effect.Enabled or effect:GetAttribute("effect_active") == true
    assert(effectActive and runtime:GetAttribute("effect_active") == true, "waterfall effect is not active")
    local candidateCFrame, candidateSize = candidate:GetBoundingBox()
    return {
        marker = "waterfall-scene-readback",
        required = present,
        effect_class = effect.ClassName,
        source_y = sourcePosition.Y,
        body_y = bodyPosition.Y,
        pool_y = poolPosition.Y,
        route_collision = true,
        route_spans_endpoints = true,
        effect_active = true,
        state = candidate:GetAttribute("BloxBenchState") or "unset",
        bounds = {x = candidateSize.X, y = candidateSize.Y, z = candidateSize.Z},
        scene_bounds = {x = boundsSize.X, y = boundsSize.Y, z = boundsSize.Z},
        center = {x = candidateCFrame.Position.X, y = candidateCFrame.Position.Y, z = candidateCFrame.Position.Z},
    }
end

eval.run = function(mode)
    assert(mode == "capture", "waterfall only exposes the capture mode")
    local candidate = get_candidate()
    local emitter = effect_node(candidate)
    local runtime = candidate:FindFirstChild("BloxBenchRuntime", true)
    local trace = candidate:FindFirstChild("BloxBenchTrace", true)
    local enabled = false
    if emitter and emitter:IsA("ParticleEmitter") then
        enabled = emitter.Enabled
    elseif emitter then
        enabled = emitter:GetAttribute("effect_active") == true
    end
    assert(enabled, "waterfall effect is disabled")
    assert(runtime and runtime:GetAttribute("effect_active") == true and runtime:GetAttribute("route_walkable") == true, "waterfall runtime observations are invalid")
    assert(trace and trace_last(trace) == "capture", "waterfall trace does not record capture")
    return {
        marker = "waterfall-capture-observed",
        effect_active = true,
        runtime_effect_active = true,
        route_walkable = true,
        trace_last = "capture",
        trace_present = true,
    }
end

eval.check_game = function()
    local candidate = get_candidate()
    local runtime = candidate:FindFirstChild("BloxBenchRuntime", true)
    local route = candidate:FindFirstChild("WalkableRoute", true)
    local emitter = effect_node(candidate)
    local effectActive = false
    if emitter and emitter:IsA("ParticleEmitter") then
        effectActive = emitter.Enabled
    elseif emitter then
        effectActive = emitter:GetAttribute("effect_active") == true
    end
    assert(route and route_collision(route), "walkable route lost collision")
    assert(runtime and runtime:GetAttribute("route_walkable") == true, "runtime route is not walkable")
    assert(effectActive and runtime:GetAttribute("effect_active") == true, "waterfall effect is not active")
    return {
        marker = "waterfall-runtime-readback",
        route_can_collide = true,
        route_walkable = true,
        effect_active = true,
        runtime_effect_active = true,
    }
end

return eval
