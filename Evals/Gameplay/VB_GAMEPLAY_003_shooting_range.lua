--!nocheck
-- @fixture v1.gameplay.003
-- @track gameplay
-- @semantic RangeRoot,PlayerStart,Target01,Target02,Backstop,RangeInput,ScoreReadout,ResetPoint,RangeBounds
-- @states idle,fire,reset
-- @runtime mode=play
-- @evidence static=diagnostic video=not-applicable trace=required reset=required review=human-pairwise
-- @screenshot type=gameplay angles=2 primary=hero
-- @knowledge profile=roblox-core-v1
-- @provenance origin="corpus-derived gameplay brief" record="a124-crossfire-ffa,a046-fully-working-fps-game,a109-sniper-game" license=unknown
-- @judge_rubric focal="compact shooting range" relationships="start targets backstop input score reset"

local eval = {}

eval.scenario_name = "v1.gameplay.003"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build one compact deterministic shooting-range interaction for a Roblox game level. Create exactly one top-level Model named BloxBenchCandidate with semantic components RangeRoot, PlayerStart, Target01, Target02, Backstop, RangeInput, ScoreReadout, ResetPoint, and RangeBounds. Add a BindableEvent named RangeInput and a BloxBenchRuntime folder or equivalent attributes. Runtime logic must live in an executable Script or LocalScript body, not only in setup. Accept the exact commands fire and reset. The initial/reset state is Ready with hit_count zero; fire must activate one target, record a hit, expose a visible feedback state and increment hit_count, then remain inspectable. Do not claim multiplayer authority, weapon realism, or a meaningful score from one deterministic interaction. Do not use external asset IDs or unrelated combat systems.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "v1.gameplay.003")
    return {marker = "shooting-range-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "shooting-range-cleanup"}
end

local required = {"RangeRoot", "PlayerStart", "Target01", "Target02", "Backstop", "RangeInput", "ScoreReadout", "ResetPoint", "RangeBounds"}
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
    assert(model:FindFirstChild("RangeInput", true):IsA("BindableEvent"), "RangeInput must be a BindableEvent")
    local bounds = model:FindFirstChild("RangeBounds", true)
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
    local _placement_ok = size.X >= 12 and size.X <= 52 and size.Z >= 12 and size.Z <= 52
    if not _placement_ok then warn("RangeBounds is outside the review envelope — non-blocking") end
    return {marker = "shooting-range-scene-readback", required = present, bounds = {x = size.X, y = size.Y, z = size.Z}}
end

local commands = {idle = "reset", fire = "fire", reset = "reset"}
eval.run = function(mode)
    assert(commands[mode], "unknown shooting-range mode")
    local model = candidate()
    local input = model:FindFirstChild("RangeInput", true)
    assert(input and input:IsA("BindableEvent"), "RangeInput is missing")
    input:Fire(commands[mode])
    task.wait(0.25)
    local runtime = model:FindFirstChild("BloxBenchRuntime", true)
    local trace = model:FindFirstChild("BloxBenchTrace", true)
    local wanted = mode == "fire" and "Hit" or "Ready"
    assert(model:GetAttribute("BloxBenchState") == wanted, "shooting-range state does not match the command")
    assert(type(attr(runtime, "hit_count")) == "number", "shooting-range hit_count is not observable")
    if mode == "fire" then
        assert(attr(runtime, "hit_count") >= 1 and attr(runtime, "feedback_active") == true, "shooting-range fire did not record feedback")
    end
    assert(trace and trace_last(trace) == commands[mode], "shooting-range trace is missing the latest command")
    return {marker = "shooting-range-observed", mode = mode, state = model:GetAttribute("BloxBenchState"), hit_count = attr(runtime, "hit_count"), feedback_active = attr(runtime, "feedback_active"), trace_last = trace_last(trace)}
end

eval.check_game = function()
    local model = candidate()
    local runtime = model:FindFirstChild("BloxBenchRuntime", true)
    local trace = model:FindFirstChild("BloxBenchTrace", true)
    local state = model:GetAttribute("BloxBenchState") or "unset"
    assert(state == "Ready" or state == "Hit", "invalid shooting-range state")
    assert(type(attr(runtime, "hit_count")) == "number", "shooting-range hit_count is invalid")
    assert(trace and trace_last(trace), "shooting-range trace is missing")
    return {marker = "shooting-range-game-readback", state = state, hit_count = attr(runtime, "hit_count"), feedback_active = attr(runtime, "feedback_active"), trace_last = trace_last(trace), trace_present = true}
end

return eval
