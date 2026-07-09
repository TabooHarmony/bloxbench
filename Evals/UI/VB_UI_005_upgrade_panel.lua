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

Show a title at the top. Below it, three stat rows stacked vertically. Each row should show a stat name on the left, the current level in the middle, and an upgrade button on the right. At the bottom, show a close button. Use green for the upgrade buttons and red for the close button. Make it look polished with rounded corners on a dark background.]],
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

    -- Strengthened: container coverage
    local function findContainerFrame(sg)
        for _, d in ipairs(sg:GetDescendants()) do
            if d:IsA("Frame") then
                local sz = d.AbsoluteSize
                if sz.X >= 300 and sz.Y >= 200 then return d end
            end
        end
        return nil
    end
    local container = findContainerFrame(screenGui)
    assert(container, "No container-sized frame found (should be a panel)")

    -- Strengthened: button colors (green upgrade, red close)
    local upgradeBtn = nil
    for _, d in ipairs(screenGui:GetDescendants()) do
        if d:IsA("TextButton") and string.find(string.lower(d.Text), "upgrade") then
            upgradeBtn = d
            break
        end
    end
    if upgradeBtn then
        local c = upgradeBtn.BackgroundColor3
        assert(c.G > c.R and c.G > c.B, "Upgrade button should be greenish")
    end
    local closeBtn = nil
    for _, d in ipairs(screenGui:GetDescendants()) do
        if d:IsA("TextButton") and string.find(string.lower(d.Text), "close") then
            closeBtn = d
            break
        end
    end
    if closeBtn then
        local c = closeBtn.BackgroundColor3
        assert(c.R > c.G and c.R > c.B, "Close button should be reddish")
    endend

eval.check_game = function()
end

return eval
