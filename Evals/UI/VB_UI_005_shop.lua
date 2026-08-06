--!nocheck
-- @fixture v1.ui.005
-- @track ui
-- @semantic UiRoot,WorldAnchor,ShopRoot,BuyTab,SellTab,CurrencyReadout,ItemRow01,ItemRow02,DisabledAffordance,UiBounds
-- @runtime mode=edit
-- @evidence static=diagnostic video=not-applicable trace=not-applicable reset=required review=human-pairwise
-- @screenshot type=ui angles=3 primary=hero
-- @knowledge profile=roblox-core-v1
-- @provenance origin="corpus-derived interface brief" record="a049-gtagunshopsystem,a115-tycoonwithrebirths-1,a123-youtube-simulator-fixed-working" license=unknown
-- @judge_rubric focal="simulator shop panel" relationships="anchor shop tabs currency rows disabled affordance"

local eval = {}

eval.scenario_name = "v1.ui.005"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {
        role = "user",
        content = [[Build one world-space simulator-shop panel for a Roblox game-world presentation. Create exactly one top-level Model named BloxBenchCandidate and keep the entire build inside it. Do not rely on PlayerGui, persistence, or a live client. Include semantic components UiRoot, WorldAnchor, ShopRoot, BuyTab, SellTab, CurrencyReadout, ItemRow01, ItemRow02, DisabledAffordance, and UiBounds. Use a SurfaceGui, BillboardGui, or similarly inspectable world-space presentation attached to WorldAnchor. Show distinct buy and sell tabs, a readable currency readout, item rows with hierarchy, and one intentionally disabled affordance. The panel should look like one coherent shop rather than scattered labels. Do not claim an economy, purchase behavior, networking, or persistence. Do not use external asset IDs or hidden scripts.]]
    }
}

eval.setup = function()
    workspace:SetAttribute("BloxBenchFixture", "v1.ui.005")
    return {marker = "shop-ui-setup"}
end

eval.cleanup = function()
    workspace:SetAttribute("BloxBenchFixture", nil)
    return {marker = "shop-ui-cleanup"}
end

local required = {"UiRoot", "WorldAnchor", "ShopRoot", "BuyTab", "SellTab", "CurrencyReadout", "ItemRow01", "ItemRow02", "DisabledAffordance", "UiBounds"}
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
    local shop = spatial(model:FindFirstChild("ShopRoot", true))
    local buy = spatial(model:FindFirstChild("BuyTab", true))
    local sell = spatial(model:FindFirstChild("SellTab", true))
    assert(boundsSize.X >= 10 and boundsSize.X <= 44 and boundsSize.Z >= 2 and boundsSize.Z <= 30, "shop UI bounds are outside the review envelope")
    assert((shop - anchor).Magnitude <= boundsSize.X + boundsSize.Z + 4, "ShopRoot is not attached to WorldAnchor")
    assert((buy - sell).Magnitude > 0.05, "BuyTab and SellTab are not distinct")
    for _, name in ipairs({"BuyTab", "SellTab", "CurrencyReadout", "ItemRow01", "ItemRow02", "DisabledAffordance"}) do
        assert((spatial(model:FindFirstChild(name, true)) - shop).Magnitude <= boundsSize.X + boundsSize.Z + 4, name .. " is outside the shop composition")
    end
    return {marker = "shop-ui-readback", required = present, bounds = {x = boundsSize.X, y = boundsSize.Y, z = boundsSize.Z}, tab_separation = (buy - sell).Magnitude, world_space = true, center = {x = boundsCFrame.Position.X, y = boundsCFrame.Position.Y, z = boundsCFrame.Position.Z}}
end

return eval
