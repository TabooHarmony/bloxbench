--!strict
-- @track ui
-- @judge_rubric correctness="two side-by-side panels with item slots, Accept/Cancel at bottom" layout="panels side by side, buttons centered below" aesthetics="container styled with dark bg and corners" completeness="header + 2 panels + item slots + coin display + buttons"
-- @ui_visual_rubric hierarchy="trade header, both participants, offered items, and accept action have clear priority" composition="the two sides read as a balanced comparison with shared actions below" spacing="panel, slot, coin, and button spacing is symmetrical where comparison requires it" typography="participant, item, coin, and action text remain legible and scannable" contrast="the two sides, item slots, coin totals, and action states are distinguishable" state_clarity="accept, cancel, empty slots, and offer ownership are visually obvious" art_direction="the trade surface communicates exchange and trust rather than generic card decoration"
-- @screenshot type=ui angles=1

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
local HttpService = game:GetService("HttpService")
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_UI_003_trade_window",
    prompt = {
        {
            {
                role = "user",
                content = [[Build a player-to-player trade window for a simulator game.

Show a header at the top with the trade partner's name. Below it, two side-by-side panels: one labeled "You" and one labeled "Them". Each panel should have a 2x2 grid of item slots and a coin display at the bottom. At the very bottom, show an accept button (green) and a cancel button (red). Make it look polished with rounded corners on a dark background.]],
                request_id = "vb_ui_003"
            }
        }
    },
    place = "baseplate.rbxl"
}

local SelectionContextJson = "[]"
local TableSelectionContext = HttpService:JSONDecode(SelectionContextJson)

eval.setup = function()
    local selectionService = game:GetService("Selection")
    selectionService:Set({})
end

eval.reference = function()
end

eval.check_scene = function()
    local StarterGui = game:GetService("StarterGui")

    local screenGui = nil
    for _, child in ipairs(StarterGui:GetChildren()) do
        if child:IsA("ScreenGui") then
            screenGui = child
            break
        end
    end
    assert(screenGui, "No ScreenGui found in StarterGui")

    -- Find TextLabel with "Trade"
    local foundTrade = false
    for _, d in ipairs(screenGui:GetDescendants()) do
        if d:IsA("TextLabel") and string.find(string.lower(d.Text), "trade") then
            foundTrade = true
            break
        end
    end
    assert(foundTrade, "No TextLabel with 'Trade' found")

    -- Find Accept button
    local foundAccept = false
    for _, d in ipairs(screenGui:GetDescendants()) do
        if d:IsA("TextButton") and string.find(string.lower(d.Text), "accept") then
            foundAccept = true
            break
        end
    end
    assert(foundAccept, "No TextButton with 'Accept' found")

    -- Find Cancel button
    local foundCancel = false
    for _, d in ipairs(screenGui:GetDescendants()) do
        if d:IsA("TextButton") and string.find(string.lower(d.Text), "cancel") then
            foundCancel = true
            break
        end
    end
    assert(foundCancel, "No TextButton with 'Cancel' found")

    -- Count panels: Frames that are large enough to be panels (>= 200x150)
    local panelCount = 0
    for _, d in ipairs(screenGui:GetDescendants()) do
        if d:IsA("Frame") then
            local sz = d.AbsoluteSize
            if sz.X >= 150 and sz.Y >= 100 then
                panelCount = panelCount + 1
            end
        end
    end
    assert(panelCount >= 2, string.format("Only %d panel-sized frames found, need >= 2", panelCount))

    -- Strengthened: vertical stacking (header above panels above buttons)
    local header = nil
    for _, d in ipairs(screenGui:GetDescendants()) do
        if d:IsA("TextLabel") and string.find(string.lower(d.Text), "trade") then
            header = d
            break
        end
    end
    local acceptBtn = nil
    for _, d in ipairs(screenGui:GetDescendants()) do
        if d:IsA("TextButton") and string.find(string.lower(d.Text), "accept") then
            acceptBtn = d
            break
        end
    end
    if header and acceptBtn then
        assert(header.AbsolutePosition.Y < acceptBtn.AbsolutePosition.Y, "Header should be above accept button")
    end

    -- Strengthened: button colors (green accept, red cancel)
    if acceptBtn then
        local c = acceptBtn.BackgroundColor3
        assert(c.G > c.R and c.G > c.B, "Accept button should be greenish")
    end
    local cancelBtn = nil
    for _, d in ipairs(screenGui:GetDescendants()) do
        if d:IsA("TextButton") and string.find(string.lower(d.Text), "cancel") then
            cancelBtn = d
            break
        end
    end
    if cancelBtn then
        local c = cancelBtn.BackgroundColor3
        assert(c.R > c.G and c.R > c.B, "Cancel button should be reddish")
    end
end

eval.check_game = function()
end

return eval
