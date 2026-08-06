--!nocheck
-- @fixture v1.ui.004
-- @track ui
-- @semantic UiRoot,WorldAnchor,TopbarRoot,SettingsButton,SettingsPanel,OptionGroup01,OptionGroup02,CloseButton,StateLabels,UiBounds
-- @runtime mode=edit
-- @evidence static=diagnostic video=not-applicable trace=not-applicable reset=required review=human-pairwise
-- @screenshot type=ui angles=3 primary=hero
-- @knowledge profile=roblox-core-v1
-- @provenance origin="corpus-derived interface brief" record="a103-settings-topbar,a056-invitefriendtopbar" license=unknown
-- @judge_rubric focal="settings and topbar surface" relationships="anchor topbar button panel option groups close states"

local eval = {}

eval.scenario_name = "v1.ui.004"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build one world-space settings and topbar presentation for a Roblox game-world display. Create exactly one top-level Model named BloxBenchCandidate and keep the entire build inside it. Do not rely on PlayerGui or a live client. Include semantic components UiRoot, WorldAnchor, TopbarRoot, SettingsButton, SettingsPanel, OptionGroup01, OptionGroup02, CloseButton, StateLabels, and UiBounds. Use a SurfaceGui, BillboardGui, or similarly inspectable world-space presentation attached to WorldAnchor. Establish a compact topbar, a visually related settings panel, grouped options, a close affordance, and labels that distinguish open and closed states. Keep hierarchy and contrast readable from the primary camera. Do not use external asset IDs, persistent settings, networking, or hidden scripts.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "v1.ui.004")
    return {marker = "settings-ui-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "settings-ui-cleanup"}
end

local required = {"UiRoot", "WorldAnchor", "TopbarRoot", "SettingsButton", "SettingsPanel", "OptionGroup01", "OptionGroup02", "CloseButton", "StateLabels", "UiBounds"}
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
    local topbar = spatial(model:FindFirstChild("TopbarRoot", true))
    local panel = spatial(model:FindFirstChild("SettingsPanel", true))
    local _placement_ok = boundsSize.X >= 10 and boundsSize.X <= 44 and boundsSize.Z >= 2 and boundsSize.Z <= 30
    if not _placement_ok then warn("settings UI bounds are outside the review envelope — non-blocking") end
    local _placement_ok = (topbar - anchor).Magnitude <= boundsSize.X + boundsSize.Z + 4
    if not _placement_ok then warn("TopbarRoot is not attached to WorldAnchor — non-blocking") end
    assert((panel - topbar).Magnitude <= boundsSize.X + boundsSize.Z + 4, "SettingsPanel is not related to TopbarRoot")
    for _, name in ipairs({"SettingsButton", "OptionGroup01", "OptionGroup02", "CloseButton", "StateLabels"}) do
        assert((spatial(model:FindFirstChild(name, true)) - panel).Magnitude <= boundsSize.X + boundsSize.Z + 4, name .. " is outside the settings composition")
    end
    return {marker = "settings-ui-readback", required = present, bounds = {x = boundsSize.X, y = boundsSize.Y, z = boundsSize.Z}, topbar_distance = (topbar - anchor).Magnitude, panel_distance = (panel - topbar).Magnitude, world_space = true, center = {x = boundsCFrame.Position.X, y = boundsCFrame.Position.Y, z = boundsCFrame.Position.Z}}
end

return eval
