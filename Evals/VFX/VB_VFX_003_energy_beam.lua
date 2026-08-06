--!nocheck
-- @fixture v1.vfx.003
-- @track vfx
-- @semantic BeamRoot,EmitterOrigin,BeamTarget,EnergyBeam,TargetMarker,VfxInput,ResetPoint,EffectBounds
-- @states idle,fire,reset
-- @runtime mode=play
-- @evidence static=diagnostic video=not-applicable trace=required reset=required review=human-pairwise
-- @screenshot type=vfx angles=2 primary=hero
-- @knowledge profile=roblox-core-v1
-- @provenance origin="corpus-derived effect brief" record="a006-ai-test,a061-kaizen,a116-type-soul" license=unknown
-- @judge_rubric focal="energy beam attack prop" relationships="origin beam target marker trigger reset"

local eval = {}

eval.scenario_name = "v1.vfx.003"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build one compact energy-beam attack prop with a clear source and target. Create exactly one top-level Model named BloxBenchCandidate with semantic components BeamRoot, EmitterOrigin, BeamTarget, EnergyBeam, TargetMarker, VfxInput, ResetPoint, and EffectBounds. Add a BindableEvent named VfxInput and a BloxBenchRuntime folder or equivalent attributes. Runtime logic must live in an executable Script or LocalScript body. Accept the exact commands fire and reset. The initial/reset state is Idle with effect_active false; fire enters Firing with effect_active true, active_target set to BeamTarget, and a trace record. Use supported Beam, Attachment, particle, and light instances without external asset IDs. Do not claim the machine checks prove beam timing or attack quality.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "v1.vfx.003")
    return {marker = "energy-beam-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "energy-beam-cleanup"}
end

local required = {"BeamRoot", "EmitterOrigin", "BeamTarget", "EnergyBeam", "TargetMarker", "VfxInput", "ResetPoint", "EffectBounds"}
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
    assert(size.X <= 36 and size.Z <= 36, "energy beam is outside the review envelope")
    return {marker = "energy-beam-scene-readback", required = present, bounds = {x = size.X, y = size.Y, z = size.Z}}
end

local commands = {idle = "reset", fire = "fire", reset = "reset"}
eval.run = function(mode)
    assert(commands[mode], "unknown energy-beam mode")
    local model = candidate()
    local input = model:FindFirstChild("VfxInput", true)
    assert(input and input:IsA("BindableEvent"), "VfxInput is missing")
    input:Fire(commands[mode])
    task.wait(0.25)
    local runtime = model:FindFirstChild("BloxBenchRuntime", true)
    local trace = model:FindFirstChild("BloxBenchTrace", true)
    local wanted = mode == "fire" and "Firing" or "Idle"
    assert(model:GetAttribute("BloxBenchState") == wanted, "energy-beam state does not match the command")
    assert(attr(runtime, "effect_active") == (mode == "fire"), "energy-beam effect_active is wrong")
    if mode == "fire" then
        assert(attr(runtime, "active_target") == "BeamTarget", "energy-beam active_target is wrong")
    end
    assert(trace and trace_last(trace) == commands[mode], "energy-beam trace is missing the latest command")
    return {marker = "energy-beam-observed", mode = mode, state = model:GetAttribute("BloxBenchState"), effect_active = attr(runtime, "effect_active"), active_target = attr(runtime, "active_target"), trace_last = trace_last(trace)}
end

eval.check_game = function()
    local model = candidate()
    local runtime = model:FindFirstChild("BloxBenchRuntime", true)
    local trace = model:FindFirstChild("BloxBenchTrace", true)
    local state = model:GetAttribute("BloxBenchState") or "unset"
    assert(state == "Idle" or state == "Firing", "invalid energy-beam state")
    assert(type(attr(runtime, "effect_active")) == "boolean", "energy-beam effect_active is not observable")
    assert(trace and trace_last(trace), "energy-beam trace is missing")
    return {marker = "energy-beam-game-readback", state = state, effect_active = attr(runtime, "effect_active"), active_target = attr(runtime, "active_target"), trace_last = trace_last(trace), trace_present = true}
end

return eval
