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
        content = [[Build one compact arcane impact burst effect in a Roblox game scene. Create exactly one top-level Model named BloxBenchCandidate. Inside that model, create Instance objects with the EXACT names EffectRoot, EmitterOrigin, ImpactMarker, PrimaryBurst, SecondaryGlow, VfxInput, ResetPoint, and EffectBounds — each as an Instance, not as attributes. VfxInput must be a BindableEvent. Create a Folder named BloxBenchRuntime and a Folder named BloxBenchTrace (both inside the model). The runtime controller must live in the Source of an executable Script or LocalScript placed in the candidate (not only in the module setup function).

Contract (implement exactly, case-sensitive):
- BloxBenchCandidate:SetAttribute("BloxBenchState") is "Idle" (initial/reset) or "Burst" (after trigger).
- BloxBenchRuntime:SetAttribute("effect_active") is a boolean: false when Idle, true when Burst.
- BloxBenchTrace:SetAttribute("last_command") is set to the exact command string most recently handled: "trigger" or "reset".
- Accept commands on VfxInput.Event: "trigger" and "reset" (exact strings). Keep the effect compact — EffectBounds footprint <= 32 by 32 — and readable from one fixed camera. Use supported Roblox particles/beams/lights/attachments without external asset IDs. Do not claim that machine checks prove timing or visual quality.

VFX instance guidance (use these types, not arbitrary Parts):
- PrimaryBurst and SecondaryGlow are visual effect instances: ParticleEmitter, Beam, PointLight, or Attachment-hosted emitters. Do not make both plain Parts with no effect — at least one should emit particles or glow.
- EffectRoot/EmitterOrigin/ImpactMarker are anchoring Parts or Attachments.
- ResetPoint and EffectBounds are Parts that mark the reset location and bounding footprint.]]
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
    -- Non-blocking: a too-large bounds still deserves a human vote.
    local envelope_ok = size.X <= 32 and size.Z <= 32
    if not envelope_ok then warn(("arcane effect outside ideal envelope (%.1f x %.1f) — non-blocking"):format(size.X, size.Z)) end
    return {marker = "arcane-burst-scene-readback", required = present, bounds = {x = size.X, y = size.Y, z = size.Z}, envelope_ok = envelope_ok}
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
