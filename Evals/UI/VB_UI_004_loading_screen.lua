--!strict
-- @track ui
-- @judge_rubric correctness="loading bar fill inside container, title at top, tip below bar" layout="bar centered horizontally, title above, tip below" aesthetics="dark background, bar styled with color and corners" completeness="title + bar container + fill + tip text"
-- @ui_visual_rubric hierarchy="loading title and progress state are immediately understandable" composition="title, progress bar, and tip form a calm centered sequence" spacing="title, bar, and tip have deliberate breathing room" typography="loading message and tip remain legible without competing with progress" contrast="progress fill is clearly distinguishable from its track and background" state_clarity="the interface communicates that work is active and progress is measurable" art_direction="the loading treatment fits the experience context without unnecessary decoration"
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
                content = [[Create a loading screen for a space-themed tycoon game.

Show the game title at the top. In the middle, show a loading bar that is partially filled. Below the loading bar, show a tip for new players. Use a dark, space-themed color scheme with a bright accent color on the loading bar fill. The background should cover the entire screen with no close button.]],
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

    -- Strengthened: full-screen background coverage
    local function findFullScreenFrame(sg)
        for _, d in ipairs(sg:GetDescendants()) do
            if d:IsA("Frame") then
                local sz = d.AbsoluteSize
                if sz.X >= 500 and sz.Y >= 300 then return d end
            end
        end
        return nil
    end
    local bg = findFullScreenFrame(screenGui)
    assert(bg, "No full-screen background frame found")

    -- Strengthened: title above loading bar above tip
    local title = nil
    local tip = nil
    for _, d in ipairs(screenGui:GetDescendants()) do
        if d:IsA("TextLabel") then
            local t = string.lower(d.Text)
            if string.find(t, "galaxy") or string.find(t, "tycoon") then title = d end
            if string.find(t, "tip") then tip = d end
        end
    end
    if title and tip then
        assert(title.AbsolutePosition.Y < tip.AbsolutePosition.Y, "Title should be above tip text")
    endend

eval.check_game = function()
end

return eval
