--!nocheck
-- @fixture v1.ui.002
-- @track ui
-- @semantic UiRoot,WorldAnchor,RewardPanel,DayProgress,ClaimedState,AvailableState,PrimaryAction,CalendarIcon,UiBounds
-- @runtime mode=edit
-- @evidence static=diagnostic video=not-applicable trace=not-applicable reset=required review=human-pairwise
-- @screenshot type=ui angles=3 primary=hero
-- @knowledge profile=roblox-core-v1
-- @provenance origin="corpus-derived interface brief" record="a096-reward-screen-by-arnavdabest,reward-pattern-corpus" license=unknown
-- @judge_rubric focal="daily reward panel" relationships="anchor panel progress claimed available action icon"

local eval = {}

eval.scenario_name = "v1.ui.002"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build one world-space daily-reward panel for a Roblox game-world presentation. Create exactly one top-level Model named BloxBenchCandidate and keep the entire build inside it. Do not rely on PlayerGui or a live client. Include semantic components UiRoot, WorldAnchor, RewardPanel, DayProgress, ClaimedState, AvailableState, PrimaryAction, CalendarIcon, and UiBounds. Use a SurfaceGui, BillboardGui, or similarly inspectable world-space presentation attached to WorldAnchor. Show day progression, clearly distinguish claimed and available states, and make one primary action visually dominant without claiming it is functional. Keep the panel readable and visually balanced from the primary camera. Do not use external asset IDs, persistence, economy authority, or hidden scripts.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "v1.ui.002")
    return {marker = "reward-ui-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "reward-ui-cleanup"}
end

local required = {"UiRoot", "WorldAnchor", "RewardPanel", "DayProgress", "ClaimedState", "AvailableState", "PrimaryAction", "CalendarIcon", "UiBounds"}
local function candidate()
    local model = workspace:FindFirstChild("BloxBenchCandidate")
    assert(model and model:IsA("Model"), "BloxBenchCandidate model is missing")
    return model
end
local function spatial(item)
    if item:IsA("BasePart") then return item.Position end
    if item:IsA("Model") then return item:GetPivot().Position end
    local part = item:FindFirstChildWhichIsA("BasePart", true)
    assert(part, "UI component has no world-space part: " .. item.Name)
    return part.Position
end
local function bounds_of(item)
    if item:IsA("BasePart") then return item.CFrame, item.Size end
    if item:IsA("Model") then return item:GetBoundingBox() end
    local part = item:FindFirstChildWhichIsA("BasePart", true)
    assert(part, "UiBounds has no spatial part")
    return part.CFrame, part.Size
end

eval.check_scene = function()
    local model = candidate()
    local present = {}
    for _, name in ipairs(required) do
        local item = model:FindFirstChild(name, true)
        assert(item, "missing semantic component: " .. name)
        present[name] = item.ClassName
    end
    local boundsCFrame, boundsSize = bounds_of(model:FindFirstChild("UiBounds", true))
    local anchor = spatial(model:FindFirstChild("WorldAnchor", true))
    local panel = spatial(model:FindFirstChild("RewardPanel", true))
    assert(boundsSize.X >= 8 and boundsSize.X <= 40 and boundsSize.Z >= 2 and boundsSize.Z <= 28, "reward UI bounds are outside the review envelope")
    assert((panel - anchor).Magnitude <= boundsSize.X + boundsSize.Z + 4, "RewardPanel is not attached to WorldAnchor")
    assert((spatial(model:FindFirstChild("DayProgress", true)) - panel).Magnitude <= boundsSize.X + boundsSize.Z + 4, "DayProgress is not inside RewardPanel")
    assert((spatial(model:FindFirstChild("PrimaryAction", true)) - panel).Magnitude <= boundsSize.X + boundsSize.Z + 4, "PrimaryAction is not inside RewardPanel")
    return {marker = "reward-ui-readback", required = present, bounds = {x = boundsSize.X, y = boundsSize.Y, z = boundsSize.Z}, anchor_distance = (panel - anchor).Magnitude, world_space = true, center = {x = boundsCFrame.Position.X, y = boundsCFrame.Position.Y, z = boundsCFrame.Position.Z}}
end

return eval
