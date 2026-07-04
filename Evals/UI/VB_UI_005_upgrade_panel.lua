--!strict
-- @judge_rubric correctness="3 stat rows with label+level+button, prices on buttons" layout="vertical stack, consistent row sizing" aesthetics="rows styled with bg and corners, not default" completeness="title + 3 rows with upgrade buttons + close"
-- @screenshot type=ui angles=1

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
local HttpService = game:GetService("HttpService")
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_UI_005_upgrade_panel",
    prompt = {
        {
            {
                role = "user",
                content = [[Build an upgrades panel for a simulator game.

Layout:
- Title TextLabel: "Upgrades" at the top, centered, font GothamBold, size 28
- 3 stat rows, each 400x60, stacked vertically with 10px spacing:
  - Row 1: TextLabel "WalkSpeed" on left (200px wide), TextLabel "Lv. 3" next to it, TextButton "Upgrade - 500" on right (green, 150x50)
  - Row 2: TextLabel "Coin Multiplier" on left, TextLabel "Lv. 2" next, TextButton "Upgrade - 750" (green, 150x50)
  - Row 3: TextLabel "Backpack Size" on left, TextLabel "Lv. 1" next, TextButton "Upgrade - 300" (green, 150x50)
- Close TextButton: "Close" at bottom-right, 100x40, red background

ScreenGui in StarterGui. Container 480x350, centered, dark background (RGB 25,25,35), UICorner radius 8. Row backgrounds RGB 40,40,55 with UICorner radius 6.]],
                request_id = "vb_ui_005"
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

    -- Find title with "Upgrade"
    local foundTitle = false
    for _, d in ipairs(screenGui:GetDescendants()) do
        if d:IsA("TextLabel") and string.find(string.lower(d.Text), "upgrade") then
            foundTitle = true
            break
        end
    end
    assert(foundTitle, "No TextLabel with 'Upgrade' found")

    -- Count TextButtons (3 upgrade + 1 close = 4, but be lenient)
    local buttonCount = 0
    for _, d in ipairs(screenGui:GetDescendants()) do
        if d:IsA("TextButton") then
            buttonCount = buttonCount + 1
        end
    end
    assert(buttonCount >= 3, string.format("Only %d TextButtons found, need >= 3 (upgrade buttons + close)", buttonCount))

    -- Find Close button
    local foundClose = false
    for _, d in ipairs(screenGui:GetDescendants()) do
        if d:IsA("TextButton") and string.find(string.lower(d.Text), "close") then
            foundClose = true
            break
        end
    end
    assert(foundClose, "No TextButton with 'Close' found")
end

eval.check_game = function()
end

return eval
