--!nocheck
-- @fixture pilot.grapple
-- @track gameplay
-- @semantic StartPad,Anchor01,Anchor02,Anchor03,LandingPad01,LandingPad02,LandingPad03,TraversalBounds,GrappleController,ResetPoint
-- @states attach01,release01,attach02,release02,attach03,land03,invalid,reset
-- @runtime mode=play
-- @evidence static=required video=optional trace=required reset=required review=human-pairwise
-- @screenshot type=gameplay angles=1 primary=hero
-- @judge_rubric focal="traversal course" relationships="anchors pads route"

local eval = {}

eval.scenario_name = "pilot.grapple"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build a compact deterministic grapple traversal course across a visible gap or lower courtyard on an open approximately 48 by 48 stud layout. Create exactly one top-level Model named BloxBenchCandidate with a StartPad, three fixed grapple anchors named Anchor01, Anchor02, and Anchor03, three sequential landing pads named LandingPad01, LandingPad02, and LandingPad03, TraversalBounds, a GrappleController, and a ResetPoint. Make the intended route legible from one fixed elevated camera. Show the active hook, rope, cable, beam, or equivalent connection while attached.

Add a BloxBenchState attribute and expose one BindableEvent named GrappleInput. The controller must accept these exact commands: attach:Anchor01, release:LandingPad01, attach:Anchor02, release:LandingPad02, attach:Anchor03, land:LandingPad03, target:NotAnAnchor, and reset. The valid sequence must move through Idle, Attached, Swinging, Released, and Landed states. The invalid target must be rejected without destroying the current valid state. Record a compact ordered trace and expose active_anchor, active_connection, current_pad, and inside_bounds through BloxBenchRuntime attributes. Reset must return the player/controller to Idle and remove active connection visuals. Do not add missions, currency, inventory, collectibles, progression, or multiplayer combat. Use only supported Roblox classes and enums.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "pilot.grapple")
    return {marker = "grapple-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "grapple-cleanup"}
end

local required = {
    "StartPad", "Anchor01", "Anchor02", "Anchor03", "LandingPad01", "LandingPad02",
    "LandingPad03", "TraversalBounds", "GrappleController", "ResetPoint",
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
    assert(part, "bounds component has no BasePart: " .. item.Name)
    return part.CFrame, part.Size
end

local function contains_xz(boundsCFrame, boundsSize, position)
    return math.abs(position.X - boundsCFrame.Position.X) <= boundsSize.X * 0.5 + 1
        and math.abs(position.Z - boundsCFrame.Position.Z) <= boundsSize.Z * 0.5 + 1
end

local function trace_last(trace)
    if not trace then
        return nil
    end
    local last = trace:GetAttribute("last_command")
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

local function attribute_of(item, name)
    if not item then
        return nil
    end
    return item:GetAttribute(name)
end

local last_valid = {state = "Idle", active_anchor = "", active_connection = false, current_pad = "StartPad"}

eval.check_scene = function()
    local candidate = get_candidate()
    local present = get_required(candidate)
    local startPad = candidate:FindFirstChild("StartPad", true)
    local firstAnchor = candidate:FindFirstChild("Anchor01", true)
    local firstLanding = candidate:FindFirstChild("LandingPad01", true)
    local bounds = candidate:FindFirstChild("TraversalBounds", true)
    local controller = candidate:FindFirstChild("GrappleController", true)
    assert(controller:IsA("Script") or controller:IsA("LocalScript") or controller:IsA("ModuleScript"), "GrappleController is not executable")
    local startPosition = position_of(startPad)
    local anchorPosition = position_of(firstAnchor)
    local landingPosition = position_of(firstLanding)
    local boundsCFrame, boundsSize = bounds_of(bounds)
    assert(boundsSize.X >= 16 and boundsSize.X <= 64 and boundsSize.Z >= 16 and boundsSize.Z <= 64, "TraversalBounds is outside the review envelope")
    for _, name in ipairs({"StartPad", "Anchor01", "Anchor02", "Anchor03", "LandingPad01", "LandingPad02", "LandingPad03", "ResetPoint"}) do
        assert(contains_xz(boundsCFrame, boundsSize, position_of(candidate:FindFirstChild(name, true))), name .. " is outside TraversalBounds")
    end
    return {
        marker = "grapple-scene-readback",
        required = present,
        start = {x = startPosition.X, y = startPosition.Y, z = startPosition.Z},
        first_anchor = {x = anchorPosition.X, y = anchorPosition.Y, z = anchorPosition.Z},
        first_landing = {x = landingPosition.X, y = landingPosition.Y, z = landingPosition.Z},
        bounds_component = bounds.ClassName,
        bounds = {x = boundsSize.X, y = boundsSize.Y, z = boundsSize.Z},
        center = {x = boundsCFrame.Position.X, y = boundsCFrame.Position.Y, z = boundsCFrame.Position.Z},
    }
end

local commands = {
    attach01 = "attach:Anchor01",
    release01 = "release:LandingPad01",
    attach02 = "attach:Anchor02",
    release02 = "release:LandingPad02",
    attach03 = "attach:Anchor03",
    land03 = "land:LandingPad03",
    invalid = "target:NotAnAnchor",
    reset = "reset",
}

local expected = {
    attach01 = {state = "Attached", active_anchor = "Anchor01", active_connection = true, current_pad = "StartPad"},
    release01 = {state = "Released", active_anchor = "Anchor01", active_connection = false, current_pad = "LandingPad01"},
    attach02 = {state = "Attached", active_anchor = "Anchor02", active_connection = true, current_pad = "LandingPad01"},
    release02 = {state = "Released", active_anchor = "Anchor02", active_connection = false, current_pad = "LandingPad02"},
    attach03 = {state = "Attached", active_anchor = "Anchor03", active_connection = true, current_pad = "LandingPad02"},
    land03 = {state = "Landed", active_anchor = "Anchor03", active_connection = false, current_pad = "LandingPad03"},
    reset = {state = "Idle", active_anchor = "", active_connection = false, current_pad = "StartPad"},
}

eval.run = function(mode)
    assert(commands[mode], "unknown grapple input mode")
    local candidate = get_candidate()
    local input = candidate:FindFirstChild("GrappleInput", true)
    assert(input and input:IsA("BindableEvent"), "GrappleInput BindableEvent is missing")
    input:Fire(commands[mode])
    local transientState
    if string.sub(mode, 1, 6) == "attach" then
        task.wait(0.08)
        transientState = candidate:GetAttribute("BloxBenchState") or "unset"
    end
    task.wait(0.35)
    local runtime = candidate:FindFirstChild("BloxBenchRuntime", true)
    local trace = candidate:FindFirstChild("BloxBenchTrace", true)
    local observed = {
        state = candidate:GetAttribute("BloxBenchState") or "unset",
        active_anchor = attribute_of(runtime, "active_anchor"),
        active_connection = attribute_of(runtime, "active_connection"),
        current_pad = attribute_of(runtime, "current_pad"),
        inside_bounds = attribute_of(runtime, "inside_bounds"),
    }
    if mode == "invalid" then
        assert(attribute_of(runtime, "last_invalid") == commands[mode], "invalid target was not recorded as rejected")
        assert(observed.state == last_valid.state and observed.active_anchor == last_valid.active_anchor and observed.active_connection == last_valid.active_connection and observed.current_pad == last_valid.current_pad, "invalid target corrupted the valid grapple state")
    else
        local wanted = expected[mode]
        if string.sub(mode, 1, 6) == "attach" then
            assert(transientState == "Swinging", "valid attachment did not enter Swinging state")
        end
        assert(wanted and observed.state == wanted.state and observed.active_anchor == wanted.active_anchor and observed.active_connection == wanted.active_connection and observed.current_pad == wanted.current_pad, "grapple state does not match the commanded transition")
        last_valid = wanted
    end
    assert(observed.inside_bounds == true, "grapple traversal left TraversalBounds")
    assert(trace and trace_last(trace) == commands[mode], "grapple trace does not record the latest command")
    return {
        marker = "grapple-input-observed",
        mode = mode,
        command = commands[mode],
        state = observed.state,
        transient_state = transientState,
        active_anchor = observed.active_anchor,
        active_connection = observed.active_connection,
        current_pad = observed.current_pad,
        inside_bounds = observed.inside_bounds,
        trace_last = trace_last(trace),
    }
end

eval.check_game = function()
    local candidate = get_candidate()
    local runtime = candidate:FindFirstChild("BloxBenchRuntime", true)
    local trace = candidate:FindFirstChild("BloxBenchTrace", true)
    assert(runtime, "BloxBenchRuntime folder is missing")
    local state = candidate:GetAttribute("BloxBenchState") or "unset"
    assert(state == "Idle" or state == "Attached" or state == "Swinging" or state == "Released" or state == "Landed", "invalid grapple state")
    local activeConnection = runtime:GetAttribute("active_connection")
    local activeAnchor = runtime:GetAttribute("active_anchor")
    local currentPad = runtime:GetAttribute("current_pad")
    assert(type(activeConnection) == "boolean" and runtime:GetAttribute("inside_bounds") == true, "grapple runtime observations are invalid")
    if state == "Attached" or state == "Swinging" then
        assert(activeConnection and type(activeAnchor) == "string" and string.match(activeAnchor, "^Anchor%d%d$"), "attached state has no valid active anchor")
    else
        assert(not activeConnection, "inactive grapple state still has an active connection")
    end
    if state == "Landed" then
        assert(currentPad == "LandingPad03", "landed state is on the wrong pad")
    end
    assert(trace and trace_last(trace), "grapple trace is missing")
    return {
        marker = "grapple-game-readback",
        state = state,
        active_anchor = activeAnchor,
        active_connection = activeConnection,
        current_pad = currentPad,
        inside_bounds = true,
        trace_last = trace_last(trace),
        trace_present = true,
    }
end

return eval
