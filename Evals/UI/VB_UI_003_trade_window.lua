--!nocheck
-- @fixture v1.ui.003
-- @track ui
-- @semantic UiRoot,WorldAnchor,TradePanel,OfferLeft,OfferRight,ConfirmAction,CancelAction,StatusText,UiBounds
-- @runtime mode=edit
-- @evidence static=diagnostic video=not-applicable trace=not-applicable reset=required review=human-pairwise
-- @screenshot type=ui angles=3 primary=hero
-- @knowledge profile=roblox-core-v1
-- @provenance origin="corpus-derived interface brief" record="trade-inventory-patterns,a001-40-pet-system" license=unknown
-- @judge_rubric focal="two-sided trade window" relationships="anchor panel offers confirm cancel status"

local eval = {}

eval.scenario_name = "v1.ui.003"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build one world-space two-sided trade-window presentation for a Roblox game-world display. Create exactly one top-level Model named BloxBenchCandidate and keep the entire build inside it. Do not rely on PlayerGui, networking, or a live client. Include semantic components UiRoot, WorldAnchor, TradePanel, OfferLeft, OfferRight, ConfirmAction, CancelAction, StatusText, and UiBounds. Use a SurfaceGui, BillboardGui, or similarly inspectable world-space presentation attached to WorldAnchor. Give the two offer areas distinct visual ownership, show clear confirmation and cancellation affordances, and include a status treatment that can communicate waiting or ready without claiming to implement a trade. Keep the hierarchy readable from the primary camera. Do not use external asset IDs, network authority, persistence, or hidden scripts.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "v1.ui.003")
    return {marker = "trade-ui-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "trade-ui-cleanup"}
end

local required = {"UiRoot", "WorldAnchor", "TradePanel", "OfferLeft", "OfferRight", "ConfirmAction", "CancelAction", "StatusText", "UiBounds"}
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
    local panel = spatial(model:FindFirstChild("TradePanel", true))
    local left = spatial(model:FindFirstChild("OfferLeft", true))
    local right = spatial(model:FindFirstChild("OfferRight", true))
    local _placement_ok = boundsSize.X >= 10 and boundsSize.X <= 44 and boundsSize.Z >= 2 and boundsSize.Z <= 30
    if not _placement_ok then warn("trade UI bounds are outside the review envelope — non-blocking") end
    local _placement_ok = (panel - anchor).Magnitude <= boundsSize.X + boundsSize.Z + 4
    if not _placement_ok then warn("TradePanel is not attached to WorldAnchor — non-blocking") end
    local _placement_ok = (left - right).Magnitude > 0.05
    if not _placement_ok then warn("OfferLeft and OfferRight are not distinct areas — non-blocking") end
    for _, name in ipairs({"OfferLeft", "OfferRight", "ConfirmAction", "CancelAction", "StatusText"}) do
        assert((spatial(model:FindFirstChild(name, true)) - panel).Magnitude <= boundsSize.X + boundsSize.Z + 4, name .. " is outside TradePanel")
    end
    return {marker = "trade-ui-readback", required = present, bounds = {x = boundsSize.X, y = boundsSize.Y, z = boundsSize.Z}, anchor_distance = (panel - anchor).Magnitude, offer_separation = (left - right).Magnitude, world_space = true, center = {x = boundsCFrame.Position.X, y = boundsCFrame.Position.Y, z = boundsCFrame.Position.Z}}
end

return eval
