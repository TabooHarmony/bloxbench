--!nocheck
-- @fixture control.lucky-block
-- @track control
-- @semantic LuckyBlock,Pedestal,Reward
-- @states damage1,damage2,damage3,break,reset
-- @runtime mode=play
-- @evidence static=required video=optional trace=required reset=required review=human-pairwise
-- @screenshot type=control angles=1 primary=hero
-- @judge_rubric focal="small interaction" relationships="block pedestal reward"

local eval = {}

eval.scenario_name = "control.lucky-block"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build one small Lucky Block interaction control on an open pedestal. Create exactly one top-level Model named BloxBenchCandidate with semantic components LuckyBlock, Pedestal, and Reward. The block must support three deterministic damage stages, one break, one physical reward reveal, one short effect burst, and reset. Keep the footprint compact and readable from one fixed elevated camera. Add a BloxBenchState attribute, a BindableEvent named LuckyBlockInput, and a BloxBenchTrace or equivalent ordered event record. LuckyBlockInput must accept the exact commands damage1, damage2, damage3, break, and reset. Do not add an inventory, economy, arena, progression system, or unrelated game loop. Use only supported Roblox classes and enums.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "control.lucky-block")
    return {marker = "lucky-block-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "lucky-block-cleanup"}
end

local function position_of(item)
    if item:IsA("BasePart") then
        return item.Position
    end
    if item:IsA("Model") then
        return item:GetPivot().Position
    end
    local part = item:FindFirstChildWhichIsA("BasePart", true)
    assert(part, "component has no spatial part: " .. item.Name)
    return part.Position
end

local function trace_last(trace)
    if not trace then
        return nil
    end
    local last = trace:GetAttribute("last_command")
    if type(last) == "string" then
        return last
    end
    local values = {}
    for _, item in ipairs(trace:GetChildren()) do
        if item:IsA("StringValue") then
            table.insert(values, item.Value)
        end
    end
    return values[#values]
end

local function attribute_of(item, name)
    if not item then
        return nil
    end
    return item:GetAttribute(name)
end

local function visible(item)
    if item:IsA("BasePart") then
        return item.Transparency < 1
    end
    for _, part in ipairs(item:GetDescendants()) do
        if part:IsA("BasePart") and part.Transparency < 1 then
            return true
        end
    end
    return false
end

local required = {"LuckyBlock", "Pedestal", "Reward"}

local function get_candidate()
    local candidate = workspace:FindFirstChild("BloxBenchCandidate")
    assert(candidate and candidate:IsA("Model"), "BloxBenchCandidate model is missing")
    return candidate
end

eval.check_scene = function()
    local candidate = get_candidate()
    local present = {}
    local positions = {}
    for _, name in ipairs(required) do
        local item = candidate:FindFirstChild(name, true)
        assert(item, "missing semantic component: " .. name)
        present[name] = item.ClassName
        positions[name] = position_of(item)
    end
    assert(positions.LuckyBlock.Y > positions.Pedestal.Y, "LuckyBlock is not above its pedestal")
    assert(candidate:GetAttribute("BloxBenchState") == "Idle", "Lucky Block does not begin in Idle")
    assert(not visible(candidate:FindFirstChild("Reward", true)), "Reward must begin hidden")
    local runtime = candidate:FindFirstChild("BloxBenchRuntime", true)
    local trace = candidate:FindFirstChild("BloxBenchTrace", true)
    assert(runtime and runtime:GetAttribute("reward_visible") == false and runtime:GetAttribute("effect_active") == false, "Lucky Block initial runtime state is invalid")
    assert(trace, "BloxBenchTrace is missing")
    local boundsCFrame, boundsSize = candidate:GetBoundingBox()
    return {
        marker = "lucky-block-scene-readback",
        required = present,
        state = "Idle",
        reward_visible = false,
        effect_active = false,
        bounds = {x = boundsSize.X, y = boundsSize.Y, z = boundsSize.Z},
        center = {x = boundsCFrame.Position.X, y = boundsCFrame.Position.Y, z = boundsCFrame.Position.Z},
    }
end

local commands = {damage1 = "damage1", damage2 = "damage2", damage3 = "damage3", ["break"] = "break", reset = "reset"}

local expected = {
    damage1 = {state = "Damaged1", reward_visible = false, effect_active = false},
    damage2 = {state = "Damaged2", reward_visible = false, effect_active = false},
    damage3 = {state = "Damaged3", reward_visible = false, effect_active = false},
    ["break"] = {state = "Broken", reward_visible = true, effect_active = true},
    reset = {state = "Idle", reward_visible = false, effect_active = false},
}

eval.run = function(mode)
    assert(commands[mode], "unknown Lucky Block input mode")
    local candidate = get_candidate()
    local input = candidate:FindFirstChild("LuckyBlockInput", true)
    assert(input and input:IsA("BindableEvent"), "LuckyBlockInput BindableEvent is missing")
    input:Fire(commands[mode])
    task.wait(0.35)
    local runtime = candidate:FindFirstChild("BloxBenchRuntime", true)
    local trace = candidate:FindFirstChild("BloxBenchTrace", true)
    local wanted = expected[mode]
    local observedState = candidate:GetAttribute("BloxBenchState") or "unset"
    local rewardVisible = attribute_of(runtime, "reward_visible")
    local effectActive = attribute_of(runtime, "effect_active")
    assert(wanted and observedState == wanted.state and rewardVisible == wanted.reward_visible and effectActive == wanted.effect_active, "Lucky Block state does not match the commanded transition")
    if mode == "break" then
        assert(visible(candidate:FindFirstChild("Reward", true)), "break did not reveal a physical Reward")
    else
        assert(not visible(candidate:FindFirstChild("Reward", true)), "Reward is visible before break or after reset")
    end
    assert(trace and trace_last(trace) == commands[mode], "Lucky Block trace does not record the latest command")
    return {
        marker = "lucky-block-input-observed",
        mode = mode,
        state = observedState,
        reward_visible = rewardVisible,
        effect_active = effectActive,
        trace_last = trace_last(trace),
    }
end

eval.check_game = function()
    local candidate = get_candidate()
    local runtime = candidate:FindFirstChild("BloxBenchRuntime", true)
    local trace = candidate:FindFirstChild("BloxBenchTrace", true)
    local state = candidate:GetAttribute("BloxBenchState") or "unset"
    local rewardVisible = attribute_of(runtime, "reward_visible")
    local effectActive = attribute_of(runtime, "effect_active")
    assert(state == "Idle" or state == "Damaged1" or state == "Damaged2" or state == "Damaged3" or state == "Broken", "invalid Lucky Block state")
    assert(type(rewardVisible) == "boolean" and type(effectActive) == "boolean", "Lucky Block runtime observations are invalid")
    assert(rewardVisible == (state == "Broken") and effectActive == (state == "Broken"), "Lucky Block runtime flags do not match state")
    assert(visible(candidate:FindFirstChild("Reward", true)) == rewardVisible, "Reward visibility does not match runtime state")
    assert(trace and trace_last(trace), "Lucky Block trace is missing")
    return {
        marker = "lucky-block-game-readback",
        state = state,
        reward_visible = rewardVisible,
        effect_active = effectActive,
        trace_last = trace_last(trace),
        trace_present = true,
    }
end

return eval
