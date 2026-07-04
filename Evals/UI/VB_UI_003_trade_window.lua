--!strict
-- @judge_rubric correctness="two side-by-side panels with item slots, Accept/Cancel at bottom" layout="panels side by side, buttons centered below" aesthetics="container styled with dark bg and corners" completeness="header + 2 panels + item slots + coin display + buttons"
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

Layout:
- Header TextLabel: "Trade with Player1" at the top, centered
- Two side-by-side panels (300x250 each, 20px gap):
  - Left panel: "You" label at top, 4 item slot Frames (60x60 each, 2x2 grid) below, coin count TextLabel "1,250" at bottom
  - Right panel: "Them" label at top, 4 item slot Frames (60x60 each, 2x2 grid) below, coin count TextLabel "0" at bottom
- Bottom row: "Accept" TextButton (green, 150x45) and "Cancel" TextButton (red, 150x45), centered with 20px gap

ScreenGui in StarterGui. Container 640x400, centered, dark background (RGB 30,30,40), UICorner radius 10. Panel backgrounds slightly lighter (RGB 45,45,60).]],
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
end

eval.check_game = function()
end

return eval
