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

Layout (top to bottom):
- Title TextLabel: "Hatch an Egg!" at the top, centered, font GothamBold, size 36
- Egg display: a large Frame (200x200) in the center, colored light blue
- Price TextButton below the egg: "Hatch (50 Coins)", green background, white text, 200x50
- Cancel TextButton below that: "Cancel", red background, white text, 200x50

All elements inside a ScreenGui in StarterGui. Use UICorner on buttons with radius 8. Background should be a semi-transparent dark frame covering the full screen.]],
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
end

eval.check_game = function()
end

return eval
