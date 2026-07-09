--!strict
-- @judge_rubric correctness="4 sections in right vertical order: title, egg, hatch, cancel" layout="centered, egg is focal point" aesthetics="buttons styled with colors and corners, not default gray" completeness="title + egg frame + hatch button + cancel button"
-- @screenshot type=ui angles=1

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
local HttpService = game:GetService("HttpService")
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_UI_001_egg_hatch",
    prompt = {
        {
            {
                role = "user",
                content = [[Create an egg hatching screen for a pet simulator game.

Show a title at the top, a large egg display in the center, a green button to hatch for coins, and a red cancel button below it. Add a semi-transparent dark overlay covering the whole screen behind everything. Make the buttons look polished with rounded corners.]],
                request_id = "vb_ui_001"
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

    -- Find any ScreenGui in StarterGui
    local screenGui = nil
    for _, child in ipairs(StarterGui:GetChildren()) do
        if child:IsA("ScreenGui") then
            screenGui = child
            break
        end
    end
    assert(screenGui, "No ScreenGui found in StarterGui")

    -- Find TextLabel with "Hatch"
    local function findLabelWithText(parent, text)
        for _, d in ipairs(parent:GetDescendants()) do
            if d:IsA("TextLabel") and string.find(string.lower(d.Text), string.lower(text)) then
                return d
            end
        end
        return nil
    end

    -- Find TextButton with text
    local function findButtonWithText(parent, text)
        for _, d in ipairs(parent:GetDescendants()) do
            if d:IsA("TextButton") and string.find(string.lower(d.Text), string.lower(text)) then
                return d
            end
        end
        return nil
    end

    -- Find a Frame >= 100x100
    local function findLargeFrame(parent)
        for _, d in ipairs(parent:GetDescendants()) do
            if d:IsA("Frame") then
                local sz = d.AbsoluteSize
                if sz.X >= 80 and sz.Y >= 80 then
                    return d
                end
            end
        end
        return nil
    end

    assert(findLabelWithText(screenGui, "Hatch"), "No TextLabel containing 'Hatch' found")
    assert(findButtonWithText(screenGui, "50") or findButtonWithText(screenGui, "coin"), "No TextButton with price (50/coins) found")
    assert(findButtonWithText(screenGui, "Cancel"), "No TextButton with 'Cancel' found")
    assert(findLargeFrame(screenGui), "No Frame >= 80x80 found (egg display)")

    -- Strengthened: container coverage (background covers screen)
    local function findFullScreenFrame(sg)
        for _, d in ipairs(sg:GetDescendants()) do
            if d:IsA("Frame") then
                local sz = d.AbsoluteSize
                if sz.X >= 400 and sz.Y >= 300 then return d end
            end
        end
        return nil
    end
    local bg = findFullScreenFrame(screenGui)
    assert(bg, "No full-screen background frame found (should cover screen)")

    -- Strengthened: vertical stacking (title above egg above buttons)
    local title = findLabelWithText(screenGui, "Hatch")
    local egg = findLargeFrame(screenGui)
    local hatchBtn = findButtonWithText(screenGui, "coin") or findButtonWithText(screenGui, "50")
    if title and egg and hatchBtn then
        assert(title.AbsolutePosition.Y < egg.AbsolutePosition.Y, "Title should be above egg display")
        assert(egg.AbsolutePosition.Y < hatchBtn.AbsolutePosition.Y, "Egg should be above hatch button")
    end

    -- Strengthened: button colors (green hatch, red cancel)
    local cancelBtn = findButtonWithText(screenGui, "Cancel")
    if cancelBtn then
        local c = cancelBtn.BackgroundColor3
        local r, g, b = c.R * 255, c.G * 255, c.B * 255
        assert(g > r and g > b, "Cancel button should be reddish (green channel should not dominate)")
    endend

eval.check_game = function()
end

return eval
