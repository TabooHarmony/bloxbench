--!strict
-- @judge_rubric correctness="loading bar fill inside container, title at top, tip below bar" layout="bar centered horizontally, title above, tip below" aesthetics="dark background, bar styled with color and corners" completeness="title + bar container + fill + tip text"
-- @screenshot type=ui angles=1

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
local HttpService = game:GetService("HttpService")
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_UI_004_loading_screen",
    prompt = {
        {
            {
                role = "user",
                content = [[Create a loading screen shown when players join the game.

Layout:
- Full-screen dark background Frame (RGB 15,15,20), covers entire screen
- Game title TextLabel: "Galaxy Tycoon" at top, centered, font GothamBlack, size 42, color white
- Loading bar container: Frame 400x20, centered horizontally, positioned ~60% down the screen, background RGB 40,40,50
- Loading bar fill: Frame inside the container, width 60% of container, height 100%, background RGB 100,200,255, UICorner radius 4
- Tip TextLabel below the bar: "Tip: Press E to interact with objects.", size 16, color RGB 150,150,160

ScreenGui in StarterGui, IgnoreGuiInset = true. No close button — this is a loading screen.]],
                request_id = "vb_ui_004"
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

    -- Find title TextLabel with "Galaxy" or "Tycoon"
    local foundTitle = false
    for _, d in ipairs(screenGui:GetDescendants()) do
        if d:IsA("TextLabel") then
            local t = string.lower(d.Text)
            if string.find(t, "galaxy") or string.find(t, "tycoon") then
                foundTitle = true
                break
            end
        end
    end
    assert(foundTitle, "No TextLabel with 'Galaxy' or 'Tycoon' found")

    -- Find tip TextLabel
    local foundTip = false
    for _, d in ipairs(screenGui:GetDescendants()) do
        if d:IsA("TextLabel") and string.find(string.lower(d.Text), "tip") then
            foundTip = true
            break
        end
    end
    assert(foundTip, "No TextLabel with 'Tip' found")

    -- Find at least 2 Frames (bar container + fill)
    -- Container should be wide and short, fill should be inside and smaller width
    local frames = {}
    for _, d in ipairs(screenGui:GetDescendants()) do
        if d:IsA("Frame") then
            table.insert(frames, d)
        end
    end
    assert(#frames >= 2, string.format("Only %d Frames found, need >= 2 (bar container + fill)", #frames))

    -- Find a wide-short frame (the bar container)
    local foundBar = false
    for _, f in ipairs(frames) do
        local sz = f.AbsoluteSize
        if sz.X >= 100 and sz.Y <= 50 and sz.Y >= 5 then
            foundBar = true
            break
        end
    end
    assert(foundBar, "No loading bar-shaped frame found (wide and short)")
end

eval.check_game = function()
end

return eval
