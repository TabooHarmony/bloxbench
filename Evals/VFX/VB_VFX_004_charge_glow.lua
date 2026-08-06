--!nocheck
-- @fixture v1.vfx.004
-- @track vfx
-- @semantic ChargeRoot,WeaponProp,ChargeOrigin,ChargeGlow,ReleaseBurst,VfxInput,ResetPoint,EffectBounds
-- @states idle,charge,release,reset
-- @runtime mode=play
-- @evidence static=diagnostic video=not-applicable trace=required reset=required review=human-pairwise
-- @screenshot type=vfx angles=2 primary=hero
-- @knowledge profile=roblox-core-v1
-- @provenance origin="corpus-derived effect brief" record="a005-advanced-gun-system-3-0,a094-realistic-advanced-gun-system" license=unknown
-- @judge_rubric focal="single-weapon charge glow" relationships="weapon origin glow release reset"

local eval = {}

eval.scenario_name = "v1.vfx.004"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build one compact single-weapon charge-up feedback effect. Create exactly one top-level Model named BloxBenchCandidate with semantic components ChargeRoot, WeaponProp, ChargeOrigin, ChargeGlow, ReleaseBurst, VfxInput, ResetPoint, and EffectBounds. Add a BindableEvent named VfxInput and a BloxBenchRuntime folder or equivalent attributes. Runtime logic must live in an executable Script or LocalScript body. Accept the exact commands charge, release, and reset. Idle/reset expose charge_state Idle and effect_active false; charge exposes Charging and effect_active true; release exposes Released and a release event in the ordered trace. Use supported Roblox particles, beams, lights, and attachments without external asset IDs. The machine checks must not claim to measure the quality or timing of the animation.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "v1.vfx.004")
    return {marker = "charge-glow-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "charge-glow-cleanup"}
end

local required = {"ChargeRoot", "WeaponProp", "ChargeOrigin", "ChargeGlow", "ReleaseBurst", "VfxInput", "ResetPoint", "EffectBounds"}
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
    assert(size.X <= 32 and size.Z <= 32, "charge effect is outside the review envelope")
    return {marker = "charge-glow-scene-readback", required = present, bounds = {x = size.X, y = size.Y, z = size.Z}}
end

local commands = {idle = "reset", charge = "charge", release = "release", reset = "reset"}
eval.run = function(mode)
    assert(commands[mode], "unknown charge-glow mode")
    local model = candidate()
    local input = model:FindFirstChild("VfxInput", true)
    assert(input and input:IsA("BindableEvent"), "VfxInput is missing")
    input:Fire(commands[mode])
    task.wait(0.25)
    local runtime = model:FindFirstChild("BloxBenchRuntime", true)
    local trace = model:FindFirstChild("BloxBenchTrace", true)
    local wanted = mode == "charge" and "Charging" or (mode == "release" and "Released" or "Idle")
    assert(model:GetAttribute("BloxBenchState") == wanted, "charge-glow state does not match the command")
    assert(attr(runtime, "effect_active") == (mode == "charge"), "charge-glow effect_active is wrong")
    assert(trace and trace_last(trace) == commands[mode], "charge-glow trace is missing the latest command")
    return {marker = "charge-glow-observed", mode = mode, state = model:GetAttribute("BloxBenchState"), effect_active = attr(runtime, "effect_active"), trace_last = trace_last(trace)}
end

eval.check_game = function()
    local model = candidate()
    local runtime = model:FindFirstChild("BloxBenchRuntime", true)
    local trace = model:FindFirstChild("BloxBenchTrace", true)
    local state = model:GetAttribute("BloxBenchState") or "unset"
    assert(state == "Idle" or state == "Charging" or state == "Released", "invalid charge-glow state")
    assert(type(attr(runtime, "effect_active")) == "boolean", "charge-glow effect_active is not observable")
    assert(trace and trace_last(trace), "charge-glow trace is missing")
    return {marker = "charge-glow-game-readback", state = state, effect_active = attr(runtime, "effect_active"), trace_last = trace_last(trace), trace_present = true}
end

return eval
