--!nocheck
-- @fixture v1.vfx.005
-- @track vfx
-- @semantic PortalRoot,PortalFrame,PortalSurface,GroundCircle,ArrivalMarker,VfxInput,ResetPoint,EffectBounds
-- @states closed,open,reset
-- @runtime mode=play
-- @evidence static=diagnostic video=not-applicable trace=required reset=required review=human-pairwise
-- @screenshot type=vfx angles=2 primary=hero
-- @knowledge profile=roblox-core-v1
-- @provenance origin="corpus-derived effect brief" record="a013-brainrot-rng-v1-0,a097-rng-1,a118-upd-6-gamzzs-rng-1" license=unknown
-- @judge_rubric focal="summon circle or portal" relationships="frame surface ground circle arrival marker open reset"

local eval = {}

eval.scenario_name = "v1.vfx.005"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build one compact summon-circle or portal opening effect. Create exactly one top-level Model named BloxBenchCandidate with semantic components PortalRoot, PortalFrame, PortalSurface, GroundCircle, ArrivalMarker, VfxInput, ResetPoint, and EffectBounds. Add a BindableEvent named VfxInput and a BloxBenchRuntime folder or equivalent attributes. Runtime logic must live in an executable Script or LocalScript body. Accept the exact commands open and reset. The initial/reset state is Closed with effect_active false; open enters Open with effect_active true and records a trace. Use supported Roblox particles, beams, lights, decals, and attachments without external asset IDs. Keep the portal bounded, readable, and nonfunctional; machine checks do not prove teleportation, timing, or visual quality.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "v1.vfx.005")
    return {marker = "portal-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "portal-cleanup"}
end

local required = {"PortalRoot", "PortalFrame", "PortalSurface", "GroundCircle", "ArrivalMarker", "VfxInput", "ResetPoint", "EffectBounds"}
local function candidate()
    local model = workspace:FindFirstChild("BloxBenchCandidate")
    assert(model and model:IsA("Model"), "BloxBenchCandidate model is missing")
    return model
end
local function attr(item, name)
    return item and item:GetAttribute(name)
end
local function trace_last(trace)
    return trace and (trace:GetAttribute("last_command") or trace:GetAttribute("last_event")) or nil
end

eval.check_scene = function()
    local model = candidate()
    local controller = model:FindFirstChildWhichIsA("Script", true) or model:FindFirstChildWhichIsA("LocalScript", true)
    assert(controller, "play fixture requires executable Script or LocalScript")
    local present = {}
    for _, name in ipairs(required) do
        local item = model:FindFirstChild(name, true)
        assert(item, "missing semantic component: " .. name)
        present[name] = item.ClassName
    end
    assert(model:FindFirstChild("VfxInput", true):IsA("BindableEvent"), "VfxInput must be a BindableEvent")
    local bounds = model:FindFirstChild("EffectBounds", true)
    local size
    if bounds:IsA("BasePart") then
        size = bounds.Size
    elseif bounds:IsA("Model") then
        local _, modelSize = bounds:GetBoundingBox()
        size = modelSize
    else
        local part = bounds:FindFirstChildWhichIsA("BasePart", true)
        assert(part, "bounds must contain a BasePart")
        size = part.Size
    end
    local _placement_ok = size.X <= 32 and size.Z <= 32
    if not _placement_ok then warn("portal effect is outside the review envelope — non-blocking") end
    return {marker = "portal-scene-readback", required = present, bounds = {x = size.X, y = size.Y, z = size.Z}}
end

local commands = {closed = "reset", open = "open", reset = "reset"}
eval.run = function(mode)
    assert(commands[mode], "unknown portal mode")
    local model = candidate()
    local input = model:FindFirstChild("VfxInput", true)
    assert(input and input:IsA("BindableEvent"), "VfxInput is missing")
    input:Fire(commands[mode])
    task.wait(0.25)
    local runtime = model:FindFirstChild("BloxBenchRuntime", true)
    local trace = model:FindFirstChild("BloxBenchTrace", true)
    local wanted = mode == "open" and "Open" or "Closed"
    assert(model:GetAttribute("BloxBenchState") == wanted, "portal state does not match the command")
    assert(attr(runtime, "effect_active") == (mode == "open"), "portal effect_active is wrong")
    assert(trace and trace_last(trace) == commands[mode], "portal trace is missing the latest command")
    return {marker = "portal-observed", mode = mode, state = model:GetAttribute("BloxBenchState"), effect_active = attr(runtime, "effect_active"), trace_last = trace_last(trace)}
end

eval.check_game = function()
    local model = candidate()
    local runtime = model:FindFirstChild("BloxBenchRuntime", true)
    local trace = model:FindFirstChild("BloxBenchTrace", true)
    local state = model:GetAttribute("BloxBenchState") or "unset"
    assert(state == "Closed" or state == "Open", "invalid portal state")
    assert(type(attr(runtime, "effect_active")) == "boolean", "portal effect_active is not observable")
    assert(trace and trace_last(trace), "portal trace is missing")
    return {marker = "portal-game-readback", state = state, effect_active = attr(runtime, "effect_active"), trace_last = trace_last(trace), trace_present = true}
end

return eval
