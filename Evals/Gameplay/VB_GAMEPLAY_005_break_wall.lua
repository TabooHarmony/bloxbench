--!nocheck
-- @fixture v1.gameplay.005
-- @track gameplay
-- @semantic BreakRoot,WallPanel,DamageMarker,BrokenOpening,RewardMarker,BreakInput,ResetPoint,BreakBounds
-- @states intact,damage,break,reset
-- @runtime mode=play
-- @evidence static=diagnostic video=not-applicable trace=required reset=required review=human-pairwise
-- @screenshot type=gameplay angles=2 primary=hero
-- @knowledge profile=roblox-core-v1
-- @provenance origin="corpus-derived gameplay brief" record="a126-break-wall-simulator,a067-mine-a-template,a119-mine-a-template" license=unknown
-- @judge_rubric focal="deterministic break-wall loop" relationships="wall damage opening reward reset"

local eval = {}

eval.scenario_name = "v1.gameplay.005"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build one compact deterministic break-wall or mining interaction for a Roblox game level. Create exactly one top-level Model named BloxBenchCandidate. Inside that model, create Instance objects with the EXACT names BreakRoot, WallPanel, DamageMarker, BrokenOpening, RewardMarker, BreakInput, ResetPoint, and BreakBounds — each as an Instance (Part/Model/Folder/BindableEvent as appropriate), not as attributes on the model. BreakInput must be a BindableEvent. Add a Folder named BloxBenchRuntime and a Folder named BloxBenchTrace (both inside the model). Runtime logic must live in the Source of an executable Script or LocalScript placed in the candidate — do not put the state machine only in the module setup function.

Contract for the evaluator to read (implement exactly, case-sensitive):
- BloxBenchCandidate:SetAttribute("BloxBenchState") must be one of "Intact", "Damaged", "Broken" (exact strings).
- BloxBenchRuntime:SetAttribute("reward_visible") is a boolean (true only when Broken, otherwise false).
- BloxBenchRuntime:SetAttribute("opening_visible") is a boolean (true only when Broken, otherwise false).
- BloxBenchTrace:SetAttribute("last_command") is set to the exact command string most recently handled: "damage", "break", or "reset".
- Accept commands on BreakInput.Event: "damage", "break", "reset" (exact lower-case strings). The initial/reset state is Intact with reward_visible false; damage enters Damaged; break enters Broken with a visible opening and reward marker; reset restores the intact wall. Keep BreakBounds roughly 10-48 wide (X) by 8-40 deep (Z) — a small Anchored Part or Model with a BasePart — so the scene is reviewable from one fixed camera. Do not claim an economy, persistence, mining balance, multiplayer behavior, or realistic destruction from this small deterministic contract.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "v1.gameplay.005")
    return {marker = "break-wall-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "break-wall-cleanup"}
end

local required = {"BreakRoot", "WallPanel", "DamageMarker", "BrokenOpening", "RewardMarker", "BreakInput", "ResetPoint", "BreakBounds"}
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
    assert(model:FindFirstChild("BreakInput", true):IsA("BindableEvent"), "BreakInput must be a BindableEvent")
    local bounds = model:FindFirstChild("BreakBounds", true)
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
    -- Non-blocking diagnostic: bounds outside the ideal review envelope do not fail
    -- the candidate — frontier builds can be slightly out of frame and still get
    -- a fair human review. The envelope is guidance in the prompt, not a gate.
    local envelope_ok = size.X >= 10 and size.X <= 48 and size.Z >= 8 and size.Z <= 40
    if not envelope_ok then
        warn(("BreakBounds is outside the ideal review envelope (%.1f x %.1f) — non-blocking"):format(size.X, size.Z))
    end
    return {marker = "break-wall-scene-readback", required = present, bounds = {x = size.X, y = size.Y, z = size.Z}, envelope_ok = envelope_ok}
end

local commands = {intact = "reset", damage = "damage", ["break"] = "break", reset = "reset"}
eval.run = function(mode)
    assert(commands[mode], "unknown break-wall mode")
    local model = candidate()
    local input = model:FindFirstChild("BreakInput", true)
    assert(input and input:IsA("BindableEvent"), "BreakInput is missing")
    input:Fire(commands[mode])
    task.wait(0.25)
    local runtime = model:FindFirstChild("BloxBenchRuntime", true)
    local trace = model:FindFirstChild("BloxBenchTrace", true)
    local wanted = mode == "damage" and "Damaged" or (mode == "break" and "Broken" or "Intact")
    assert(model:GetAttribute("BloxBenchState") == wanted, "break-wall state does not match the command")
    assert(attr(runtime, "reward_visible") == (mode == "break"), "break-wall reward_visible is wrong")
    if mode == "break" then
        assert(attr(runtime, "opening_visible") == true, "break-wall opening is not observable")
    end
    assert(trace and trace_last(trace) == commands[mode], "break-wall trace is missing the latest command")
    return {marker = "break-wall-observed", mode = mode, state = model:GetAttribute("BloxBenchState"), reward_visible = attr(runtime, "reward_visible"), opening_visible = attr(runtime, "opening_visible"), trace_last = trace_last(trace)}
end

eval.check_game = function()
    local model = candidate()
    local runtime = model:FindFirstChild("BloxBenchRuntime", true)
    local trace = model:FindFirstChild("BloxBenchTrace", true)
    local state = model:GetAttribute("BloxBenchState") or "unset"
    assert(state == "Intact" or state == "Damaged" or state == "Broken", "invalid break-wall state")
    assert(type(attr(runtime, "reward_visible")) == "boolean" and type(attr(runtime, "opening_visible")) == "boolean", "break-wall runtime is invalid")
    assert(trace and trace_last(trace), "break-wall trace is missing")
    return {marker = "break-wall-game-readback", state = state, reward_visible = attr(runtime, "reward_visible"), opening_visible = attr(runtime, "opening_visible"), trace_last = trace_last(trace), trace_present = true}
end

return eval
