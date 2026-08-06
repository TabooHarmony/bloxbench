--!nocheck
-- @fixture v1.ui.001
-- @track ui
-- @semantic UiRoot,WorldAnchor,Panel,SlotGrid,ItemSlot01,ItemSlot02,RarityCue,QuantityLabel,EmptyState,UiBounds
-- @runtime mode=edit
-- @evidence static=diagnostic video=not-applicable trace=not-applicable reset=required review=human-pairwise
-- @screenshot type=ui angles=3 primary=hero
-- @knowledge profile=roblox-core-v1
-- @provenance origin="corpus-derived interface brief" record="a001-40-pet-system,a022-charactercustom,a023-clickerkit" license=unknown
-- @judge_rubric focal="pet or egg inventory grid" relationships="anchor panel grid slots rarity quantity empty state"

local eval = {}

eval.scenario_name = "v1.ui.001"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build one world-space pet or egg inventory panel for a Roblox game-world presentation. Create exactly one top-level Model named BloxBenchCandidate and keep the entire build inside it. Do not rely on PlayerGui or a live client. Include semantic components UiRoot, WorldAnchor, Panel, SlotGrid, ItemSlot01, ItemSlot02, RarityCue, QuantityLabel, EmptyState, and UiBounds. Use a SurfaceGui, BillboardGui, or similarly inspectable world-space presentation attached to WorldAnchor. Show a clear slot hierarchy, at least two item states, a rarity cue, a quantity label, and an intentional empty-state treatment. Keep type and text hierarchy readable from the primary camera. Do not use external asset IDs, persistence, inventory authority, or hidden scripts.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "v1.ui.001")
    return {marker = "inventory-ui-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "inventory-ui-cleanup"}
end

local required = {"UiRoot", "WorldAnchor", "Panel", "SlotGrid", "ItemSlot01", "ItemSlot02", "RarityCue", "QuantityLabel", "EmptyState", "UiBounds"}
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
    local panel = spatial(model:FindFirstChild("Panel", true))
    assert(boundsSize.X >= 8 and boundsSize.X <= 40 and boundsSize.Z >= 2 and boundsSize.Z <= 28, "inventory UI bounds are outside the review envelope")
    assert((panel - anchor).Magnitude <= boundsSize.X + boundsSize.Z + 4, "inventory Panel is not attached to WorldAnchor")
    local slots = spatial(model:FindFirstChild("SlotGrid", true))
    assert((slots - panel).Magnitude <= boundsSize.X + boundsSize.Z + 4, "SlotGrid is not inside Panel")
    return {marker = "inventory-ui-readback", required = present, bounds = {x = boundsSize.X, y = boundsSize.Y, z = boundsSize.Z}, anchor_distance = (panel - anchor).Magnitude, slot_distance = (slots - panel).Magnitude, world_space = true, center = {x = boundsCFrame.Position.X, y = boundsCFrame.Position.Y, z = boundsCFrame.Position.Z}}
end

return eval
