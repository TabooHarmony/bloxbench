--!nocheck
-- @fixture v1.vfx.002
-- @track vfx
-- @semantic StormRoot,StrikeOrigin,StrikeTarget,LightningBeam,FlashLight,VfxInput,ResetPoint,EffectBounds
-- @states idle,strike,reset
-- @runtime mode=play
-- @evidence static=diagnostic video=not-applicable trace=required reset=required review=human-pairwise
-- @screenshot type=vfx angles=2 primary=hero
-- @knowledge profile=roblox-core-v1
-- @provenance origin="corpus-derived effect brief" record="lightning-pattern-corpus" license=unknown
-- @judge_rubric focal="lightning strike" relationships="origin target beam flash trigger reset"

local eval = {}

eval.scenario_name = "v1.vfx.002"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build one compact lightning-strike or storm-cell effect. Create exactly one top-level Model named BloxBenchCandidate with semantic components StormRoot, StrikeOrigin, StrikeTarget, LightningBeam, FlashLight, VfxInput, ResetPoint, and EffectBounds. Add a BindableEvent named VfxInput and a BloxBenchRuntime folder or equivalent attributes. Runtime logic must live in an executable Script or LocalScript body. Accept the exact commands strike and reset. Idle and reset must expose effect_active false; strike must expose effect_active true, a readable active_target, and an ordered trace. Use supported Roblox beams, particles, lights, and attachments without external asset IDs. Keep the effect bounded and visually coherent. Machine checks must not be treated as proof of timing, sound, or visual quality.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "v1.vfx.002")
    return {marker = "lightning-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "lightning-cleanup"}
end

local required = {"StormRoot", "StrikeOrigin", "StrikeTarget", "LightningBeam", "FlashLight", "VfxInput", "ResetPoint", "EffectBounds"}
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
    local _placement_ok = size.X <= 36 and size.Z <= 36
    if not _placement_ok then warn("lightning effect is outside the review envelope — non-blocking") end
    return {marker = "lightning-scene-readback", required = present, bounds = {x = size.X, y = size.Y, z = size.Z}}
end

local commands = {idle = "reset", strike = "strike", reset = "reset"}
eval.run = function(mode)
    assert(commands[mode], "unknown lightning mode")
    local model = candidate()
    local input = model:FindFirstChild("VfxInput", true)
    assert(input and input:IsA("BindableEvent"), "VfxInput is missing")
    input:Fire(commands[mode])
    task.wait(0.25)
    local runtime = model:FindFirstChild("BloxBenchRuntime", true)
    local trace = model:FindFirstChild("BloxBenchTrace", true)
    local wanted = mode == "strike" and "Striking" or "Idle"
    assert(model:GetAttribute("BloxBenchState") == wanted, "lightning state does not match the command")
    assert(attr(runtime, "effect_active") == (mode == "strike"), "lightning effect_active is wrong")
    if mode == "strike" then
        assert(type(attr(runtime, "active_target")) == "string", "lightning active_target is missing")
    end
    assert(trace and trace_last(trace) == commands[mode], "lightning trace is missing the latest command")
    return {marker = "lightning-observed", mode = mode, state = model:GetAttribute("BloxBenchState"), effect_active = attr(runtime, "effect_active"), active_target = attr(runtime, "active_target"), trace_last = trace_last(trace)}
end

eval.check_game = function()
    local model = candidate()
    local runtime = model:FindFirstChild("BloxBenchRuntime", true)
    local trace = model:FindFirstChild("BloxBenchTrace", true)
    local state = model:GetAttribute("BloxBenchState") or "unset"
    assert(state == "Idle" or state == "Striking", "invalid lightning state")
    assert(type(attr(runtime, "effect_active")) == "boolean", "lightning effect_active is not observable")
    assert(trace and trace_last(trace), "lightning trace is missing")
    return {marker = "lightning-game-readback", state = state, effect_active = attr(runtime, "effect_active"), active_target = attr(runtime, "active_target"), trace_last = trace_last(trace), trace_present = true}
end

return eval
