--!nocheck
-- @fixture v1.gameplay.004
-- @track gameplay
-- @semantic CrashRoot,VehicleProp,ImpactZone,DebrisMarker,DamageState,CrashInput,ResetPoint,CrashBounds
-- @states idle,impact,reset
-- @runtime mode=play
-- @evidence static=diagnostic video=not-applicable trace=required reset=required review=human-pairwise
-- @screenshot type=gameplay angles=2 primary=hero
-- @knowledge profile=roblox-core-v1
-- @provenance origin="corpus-derived gameplay brief" record="a021-car-crash-system,a020-car-place" license=unknown
-- @judge_rubric focal="vehicle crash playground" relationships="vehicle impact debris damage reset"

local eval = {}

eval.scenario_name = "v1.gameplay.004"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build one compact vehicle-crash playground interaction for a Roblox game level. Create exactly one top-level Model named BloxBenchCandidate with semantic components CrashRoot, VehicleProp, ImpactZone, DebrisMarker, DamageState, CrashInput, ResetPoint, and CrashBounds. Add a BindableEvent named CrashInput and a BloxBenchRuntime folder or equivalent attributes. Runtime logic must live in an executable Script or LocalScript body. Accept the exact commands impact and reset. The initial/reset state is Intact with damage_visible false; impact must enter Damaged, expose damage_visible true, record impact_count, and leave a readable debris or impact marker. Use deterministic proxy motion or state changes rather than claiming realistic vehicle physics. Do not use external asset IDs, multiplayer, economy, or an open-ended driving system.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "v1.gameplay.004")
    return {marker = "crash-playground-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "crash-playground-cleanup"}
end

local required = {"CrashRoot", "VehicleProp", "ImpactZone", "DebrisMarker", "DamageState", "CrashInput", "ResetPoint", "CrashBounds"}
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
    assert(model:FindFirstChild("CrashInput", true):IsA("BindableEvent"), "CrashInput must be a BindableEvent")
    local bounds = model:FindFirstChild("CrashBounds", true)
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
    if not _placement_ok then warn("CrashBounds is outside the review envelope — non-blocking") end
    return {marker = "crash-playground-scene-readback", required = present, bounds = {x = size.X, y = size.Y, z = size.Z}}
end

local commands = {idle = "reset", impact = "impact", reset = "reset"}
eval.run = function(mode)
    assert(commands[mode], "unknown crash-playground mode")
    local model = candidate()
    local input = model:FindFirstChild("CrashInput", true)
    assert(input and input:IsA("BindableEvent"), "CrashInput is missing")
    input:Fire(commands[mode])
    task.wait(0.25)
    local runtime = model:FindFirstChild("BloxBenchRuntime", true)
    local trace = model:FindFirstChild("BloxBenchTrace", true)
    local wanted = mode == "impact" and "Damaged" or "Intact"
    assert(model:GetAttribute("BloxBenchState") == wanted, "crash-playground state does not match the command")
    assert(attr(runtime, "damage_visible") == (mode == "impact"), "crash-playground damage_visible is wrong")
    assert(type(attr(runtime, "impact_count")) == "number", "crash-playground impact_count is not observable")
    assert(trace and trace_last(trace) == commands[mode], "crash-playground trace is missing the latest command")
    return {marker = "crash-playground-observed", mode = mode, state = model:GetAttribute("BloxBenchState"), damage_visible = attr(runtime, "damage_visible"), impact_count = attr(runtime, "impact_count"), trace_last = trace_last(trace)}
end

eval.check_game = function()
    local model = candidate()
    local runtime = model:FindFirstChild("BloxBenchRuntime", true)
    local trace = model:FindFirstChild("BloxBenchTrace", true)
    local state = model:GetAttribute("BloxBenchState") or "unset"
    assert(state == "Intact" or state == "Damaged", "invalid crash-playground state")
    assert(type(attr(runtime, "damage_visible")) == "boolean" and type(attr(runtime, "impact_count")) == "number", "crash-playground runtime is invalid")
    assert(trace and trace_last(trace), "crash-playground trace is missing")
    return {marker = "crash-playground-game-readback", state = state, damage_visible = attr(runtime, "damage_visible"), impact_count = attr(runtime, "impact_count"), trace_last = trace_last(trace), trace_present = true}
end

return eval
