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
    if node == nil then
        return nil
    end
    if node:IsA("ParticleEmitter") then
        return node
    end
    return node:FindFirstChildWhichIsA("ParticleEmitter", true) or node
end

eval.check_scene = function()
    local candidate = get_candidate()
    local present = {}
    local warnings = {}
    for _, name in ipairs(required) do
        local item = candidate:FindFirstChild(name, true)
        if item then
            present[name] = item.ClassName
        else
            table.insert(warnings, "missing semantic component: " .. name)
        end
    end
    local effect = effect_node(candidate)
    if effect == nil then
        table.insert(warnings, "MistEmitter is missing")
    elseif not (effect:IsA("ParticleEmitter") or effect:GetAttribute("effect_active") ~= nil) then
        table.insert(warnings, "MistEmitter has no observable effect")
    end
    local source = candidate:FindFirstChild("WaterSource", true)
    local body = candidate:FindFirstChild("WaterfallBody", true)
    local pool = candidate:FindFirstChild("ImpactPool", true)
    local approach = candidate:FindFirstChild("ApproachStart", true)
    local viewpoint = candidate:FindFirstChild("Viewpoint", true)
    local route = candidate:FindFirstChild("WalkableRoute", true)
    local bounds = candidate:FindFirstChild("SceneBounds", true)

    local function position_of_or_nil(item)
        if item == nil then
            return nil
        end
        if item:IsA("BasePart") then
            return item.Position
        end
        if item:IsA("Model") then
            return item:GetPivot().Position
        end
        local part = item:FindFirstChildWhichIsA("BasePart", true)
        if part then
            return part.Position
        end
        return nil
    end

    local sourcePosition = position_of_or_nil(source)
    local bodyPosition = position_of_or_nil(body)
    local poolPosition = position_of_or_nil(pool)
    local approachPosition = position_of_or_nil(approach)
    local viewpointPosition = position_of_or_nil(viewpoint)
    local boundsCFrame, boundsSize

    if bounds and (bounds:IsA("BasePart") or bounds:IsA("Model")) then
        if bounds:IsA("BasePart") then
            boundsCFrame, boundsSize = bounds.CFrame, bounds.Size
        else
            boundsCFrame, boundsSize = bounds:GetBoundingBox()
        end
        local bx, bz = boundsSize.X, boundsSize.Z
        if bx < 32 or bx > 64 or bz < 32 or bz > 64 then
            table.insert(warnings, "SceneBounds outside 32-64 review envelope")
        end
    else
        table.insert(warnings, "SceneBounds is not spatial")
    end

    if sourcePosition and bodyPosition and sourcePosition.Y <= bodyPosition.Y then
        table.insert(warnings, "water source is not above waterfall body")
    end
    if bodyPosition and poolPosition and bodyPosition.Y <= poolPosition.Y then
        table.insert(warnings, "waterfall body is not above impact pool")
    end
    if route == nil then
        table.insert(warnings, "WalkableRoute is missing")
    elseif not route_collision(route) then
        table.insert(warnings, "WalkableRoute has no collidable surface")
    end

    local function in_bounds(position)
        if position == nil or boundsCFrame == nil then
            return false
        end
        return math.abs(position.X - boundsCFrame.Position.X) <= boundsSize.X * 0.5 + 1
            and math.abs(position.Z - boundsCFrame.Position.Z) <= boundsSize.Z * 0.5 + 1
    end

    if boundsCFrame then
        for _, position in ipairs({sourcePosition, bodyPosition, poolPosition, approachPosition, viewpointPosition}) do
            if position and not in_bounds(position) then
                table.insert(warnings, "focal component is outside SceneBounds")
            end
        end
    end

    local effectParent = effect and (effect:IsA("ParticleEmitter") and effect.Parent or effect)
    local effectPosition = effectParent and position_of_or_nil(effectParent)
    if effectPosition and poolPosition and (effectPosition - poolPosition).Magnitude > 12 then
        table.insert(warnings, "MistEmitter is not concentrated near ImpactPool")
    end

    local runtime = candidate:FindFirstChild("BloxBenchRuntime", true)
    local routeWalkable = runtime ~= nil and runtime:GetAttribute("route_walkable") == true
    local effectActive = effect ~= nil and (effect:IsA("ParticleEmitter") and effect.Enabled or effect:GetAttribute("effect_active") == true)
    if runtime == nil then
        table.insert(warnings, "BloxBenchRuntime folder is missing")
    elseif not routeWalkable then
        table.insert(warnings, "runtime route is not walkable")
    end
    if runtime and runtime:GetAttribute("effect_active") ~= true then
        table.insert(warnings, "runtime effect_active is not true")
    end
    if not effectActive then
        table.insert(warnings, "waterfall effect is not active")
    end

    local candidateCFrame, candidateSize = candidate:GetBoundingBox()
    return {
        marker = "waterfall-scene-readback",
        required = present,
        warnings = warnings,
        component_count = #present,
        effect_class = effect and effect.ClassName or nil,
        source_y = sourcePosition and sourcePosition.Y or nil,
        body_y = bodyPosition and bodyPosition.Y or nil,
        pool_y = poolPosition and poolPosition.Y or nil,
        route_collision = route ~= nil and route_collision(route) or false,
        effect_active = effectActive,
        route_walkable = routeWalkable,
        state = candidate:GetAttribute("BloxBenchState") or "unset",
        bounds = {x = candidateSize.X, y = candidateSize.Y, z = candidateSize.Z},
        scene_bounds = boundsSize and {x = boundsSize.X, y = boundsSize.Y, z = boundsSize.Z} or nil,
        center = {x = candidateCFrame.Position.X, y = candidateCFrame.Position.Y, z = candidateCFrame.Position.Z},
    }
end

eval.run = function(mode)
    assert(mode == "capture", "waterfall only exposes the capture mode")
    local candidate = get_candidate()
    local emitter = effect_node(candidate)
    local runtime = candidate:FindFirstChild("BloxBenchRuntime", true)
    local trace = candidate:FindFirstChild("BloxBenchTrace", true)
    local warnings = {}
    local enabled = false
    if emitter and emitter:IsA("ParticleEmitter") then
        enabled = emitter.Enabled
    elseif emitter then
        enabled = emitter:GetAttribute("effect_active") == true
    end
    if not enabled then
        table.insert(warnings, "waterfall effect is disabled")
    end
    local routeWalkable = runtime ~= nil and runtime:GetAttribute("route_walkable") == true
    local effectActive = runtime ~= nil and runtime:GetAttribute("effect_active") == true
    if not (routeWalkable and effectActive) then
        table.insert(warnings, "waterfall runtime observations are incomplete")
    end
    local traceLast = trace and trace_last(trace) or nil
    if traceLast ~= "capture" then
        table.insert(warnings, "waterfall trace does not record capture")
    end
    return {
        marker = "waterfall-capture-observed",
        effect_active = enabled,
        runtime_effect_active = effectActive,
        route_walkable = routeWalkable,
        trace_last = traceLast,
        trace_present = trace ~= nil,
        warnings = warnings,
    }
end

eval.check_game = function()
    local candidate = get_candidate()
    local runtime = candidate:FindFirstChild("BloxBenchRuntime", true)
    local route = candidate:FindFirstChild("WalkableRoute", true)
    local emitter = effect_node(candidate)
    local warnings = {}
    local effectActive = false
    if emitter and emitter:IsA("ParticleEmitter") then
        effectActive = emitter.Enabled
    elseif emitter then
        effectActive = emitter:GetAttribute("effect_active") == true
    end
    local routeCollision = route ~= nil and route_collision(route) or false
    local routeWalkable = runtime ~= nil and runtime:GetAttribute("route_walkable") == true
    local runtimeEffect = runtime ~= nil and runtime:GetAttribute("effect_active") == true
    if not routeCollision then
        table.insert(warnings, "walkable route lost collision")
    end
    if not routeWalkable then
        table.insert(warnings, "runtime route is not walkable")
    end
    if not (effectActive and runtimeEffect) then
        table.insert(warnings, "waterfall effect is not active")
    end
    return {
        marker = "waterfall-runtime-readback",
        route_can_collide = routeCollision,
        route_walkable = routeWalkable,
        effect_active = effectActive,
        runtime_effect_active = runtimeEffect,
        warnings = warnings,
    }
end

return eval
