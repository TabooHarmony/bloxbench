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
        content = [[Build one world-space daily-reward panel for a Roblox game-world presentation. Create exactly one top-level Model named BloxBenchCandidate and keep the entire build inside it. Do not rely on PlayerGui or a live client. Inside that model, create Instance objects with the EXACT names UiRoot, WorldAnchor, RewardPanel, DayProgress, ClaimedState, AvailableState, PrimaryAction, CalendarIcon, and UiBounds.

What each name must be (use these instance types, not arbitrary Parts):
- WorldAnchor: a Part (Anchored, about 1x1x1) that anchors the presentation in the world. Position it near Vector3.new(0,5,0).
- UiRoot: a BillboardGui or SurfaceGui whose Adornee is WorldAnchor (so the UI is world-space, not PlayerGui).
- RewardPanel, DayProgress, ClaimedState, AvailableState, PrimaryAction, CalendarIcon: GuiObjects (Frame/TextLabel/TextButton/ImageLabel) parented inside UiRoot (inside RewardPanel where sensible), not Parts. DayProgress should show a day progression (e.g. "Day 3 / 7"). ClaimedState and AvailableState should be two distinct visuals for claimed vs available. PrimaryAction should be a large dominant button (TextButton).
- UiBounds: a Part near WorldAnchor (roughly 8-40 wide X by 2-28 deep Z, footprint only — Y can be thin) so the scene is reviewable from one fixed camera. This is guidance, not a quality score.

Show day progression, clearly distinguish claimed and available states, and make one primary action visually dominant without claiming it is functional. Keep the panel readable and visually balanced from the primary camera. Do not use external asset IDs, persistence, economy authority, or hidden scripts.]]
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
    if item:IsA("GuiObject") then
        -- GuiObjects have no world position; find their hosting Part via the Gui's Adornee
        local gui = item:FindFirstAncestorWhichIsA("BillboardGui") or item:FindFirstAncestorWhichIsA("SurfaceGui")
        if gui and gui.Adornee and gui.Adornee:IsA("BasePart") then return gui.Adornee.Position end
        local parentPart = item.Parent and item.Parent:FindFirstAncestorWhichIsA("BasePart")
        if parentPart then return parentPart.Position end
    end
    local part = item:FindFirstChildWhichIsA("BasePart", true)
    if part then return part.Position end
    local gui = item:FindFirstAncestorWhichIsA("BillboardGui") or item:FindFirstAncestorWhichIsA("SurfaceGui")
    if gui and gui.Adornee and gui.Adornee:IsA("BasePart") then return gui.Adornee.Position end
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
    -- Non-blocking diagnostics for the review envelope and proximity:
    -- frontier models can produce a slightly out-of-frame or loosely-anchored
    -- panel and still deserve a fair human vote on the place file.
    local envelope_ok = boundsSize.X >= 8 and boundsSize.X <= 40 and boundsSize.Z >= 2 and boundsSize.Z <= 28
    local attached = (panel - anchor).Magnitude <= boundsSize.X + boundsSize.Z + 4
    local day_inside = (spatial(model:FindFirstChild("DayProgress", true)) - panel).Magnitude <= boundsSize.X + boundsSize.Z + 4
    local action_inside = (spatial(model:FindFirstChild("PrimaryAction", true)) - panel).Magnitude <= boundsSize.X + boundsSize.Z + 4
    if not envelope_ok then warn(("reward UI bounds outside ideal envelope (%.1f x %.1f) — non-blocking"):format(boundsSize.X, boundsSize.Z)) end
    if not attached then warn("RewardPanel is not attached to WorldAnchor — non-blocking") end
    if not day_inside then warn("DayProgress is not inside RewardPanel — non-blocking") end
    if not action_inside then warn("PrimaryAction is not inside RewardPanel — non-blocking") end
    return {marker = "reward-ui-readback", required = present, bounds = {x = boundsSize.X, y = boundsSize.Y, z = boundsSize.Z}, anchor_distance = (panel - anchor).Magnitude, world_space = true, center = {x = boundsCFrame.Position.X, y = boundsCFrame.Position.Y, z = boundsCFrame.Position.Z}, envelope_ok = envelope_ok, attached = attached}
end

return eval
