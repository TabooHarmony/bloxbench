--!nocheck
-- @fixture v1.vfx.001
-- @track vfx
-- @semantic EffectRoot,EmitterOrigin,ImpactMarker,PrimaryBurst,SecondaryGlow,VfxInput,ResetPoint,EffectBounds
-- @states idle,trigger,reset
-- @runtime mode=play
-- @evidence static=diagnostic video=not-applicable trace=required reset=required review=human-pairwise
-- @screenshot type=vfx angles=2 primary=hero
-- @knowledge profile=roblox-core-v1
-- @provenance origin="corpus-derived effect brief" record="a124-crossfire-ffa,particle-emitter-patterns" license=unknown
-- @judge_rubric focal="arcane impact burst" relationships="origin marker primary burst secondary glow trigger reset"

local eval = {}

eval.scenario_name = "v1.vfx.001"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build one compact arcane impact burst effect in a Roblox game scene. Create exactly one top-level Model named BloxBenchCandidate with semantic components EffectRoot, EmitterOrigin, ImpactMarker, PrimaryBurst, SecondaryGlow, VfxInput, ResetPoint, and EffectBounds. Add a BindableEvent named VfxInput and a BloxBenchRuntime folder or equivalent attributes. The runtime controller must live in an executable Script or LocalScript body, not only in the setup module. Accept the exact commands trigger and reset. The initial and reset state must be Idle with effect_active false; trigger must enter Burst with effect_active true and record an ordered trace. Use supported Roblox particles, beams, lights, and attachments without external asset IDs. Keep the effect compact and readable, and do not claim that machine checks prove timing or visual quality.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "v1.vfx.001")
    return {marker = "arcane-burst-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "arcane-burst-cleanup"}
end

local required = {"EffectRoot", "EmitterOrigin", "ImpactMarker", "PrimaryBurst", "SecondaryGlow", "VfxInput", "ResetPoint", "EffectBounds"}
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
    local input = model:FindFirstChild("VfxInput", true)
    assert(input:IsA("BindableEvent"), "VfxInput must be a BindableEvent")
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
    assert(size.X <= 32 and size.Z <= 32, "arcane effect is outside the compact review envelope")
    return {marker = "arcane-burst-scene-readback", required = present, bounds = {x = size.X, y = size.Y, z = size.Z}}
end

local commands = {idle = "reset", trigger = "trigger", reset = "reset"}
eval.run = function(mode)
    assert(commands[mode], "unknown arcane burst mode")
    local model = candidate()
    local input = model:FindFirstChild("VfxInput", true)
    assert(input and input:IsA("BindableEvent"), "VfxInput is missing")
    input:Fire(commands[mode])
    task.wait(0.25)
    local runtime = model:FindFirstChild("BloxBenchRuntime", true)
    local trace = model:FindFirstChild("BloxBenchTrace", true)
    local wanted = mode == "trigger" and "Burst" or "Idle"
    assert(model:GetAttribute("BloxBenchState") == wanted, "arcane burst state does not match the command")
    assert(attr(runtime, "effect_active") == (mode == "trigger"), "arcane burst effect_active is wrong")
    assert(trace and trace_last(trace) == commands[mode], "arcane burst trace is missing the latest command")
    return {marker = "arcane-burst-observed", mode = mode, state = model:GetAttribute("BloxBenchState"), effect_active = attr(runtime, "effect_active"), trace_last = trace_last(trace)}
end

eval.check_game = function()
    local model = candidate()
    local runtime = model:FindFirstChild("BloxBenchRuntime", true)
    local trace = model:FindFirstChild("BloxBenchTrace", true)
    local state = model:GetAttribute("BloxBenchState") or "unset"
    local active = attr(runtime, "effect_active")
    assert(state == "Idle" or state == "Burst", "invalid arcane burst state")
    assert(type(active) == "boolean", "arcane burst effect_active is not observable")
    assert(trace and trace_last(trace), "arcane burst trace is missing")
    return {marker = "arcane-burst-game-readback", state = state, effect_active = active, trace_last = trace_last(trace), trace_present = true}
end

return eval
