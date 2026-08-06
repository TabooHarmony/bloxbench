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
        content = [[Build one compact deterministic break-wall or mining interaction for a Roblox game level. Create exactly one top-level Model named BloxBenchCandidate with semantic components BreakRoot, WallPanel, DamageMarker, BrokenOpening, RewardMarker, BreakInput, ResetPoint, and BreakBounds. Add a BindableEvent named BreakInput and a BloxBenchRuntime folder or equivalent attributes. Runtime logic must live in an executable Script or LocalScript body. Accept the exact commands damage, break, and reset. The initial/reset state is Intact with reward_visible false; damage enters Damaged; break enters Broken with a visible opening and reward marker; reset restores the intact wall. Record the ordered command trace. Do not claim an economy, persistence, mining balance, multiplayer behavior, or realistic destruction from this small deterministic contract.]]
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
    assert(size.X >= 10 and size.X <= 48 and size.Z >= 8 and size.Z <= 40, "BreakBounds is outside the review envelope")
    return {marker = "break-wall-scene-readback", required = present, bounds = {x = size.X, y = size.Y, z = size.Z}}
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
