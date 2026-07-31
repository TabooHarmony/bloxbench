--!strict
-- @track ui
-- @judge_rubric correctness="7 slots in horizontal row, day 3 highlighted, days 1-2 dimmed" layout="centered container, slots aligned" aesthetics="styled container with corners, slot borders" completeness="title + 7 day slots + claim + close"
-- @ui_visual_rubric hierarchy="current day and claim action are immediately dominant over completed and future days" composition="seven rewards read as one coherent progression without crowding or excessive empty space" spacing="slots, labels, and claim/close actions use consistent gaps and alignment" typography="day labels and reward text remain legible at the slot scale" contrast="current, completed, and future states are distinguishable without relying on color alone" state_clarity="day 3 active, days 1-2 completed, and future days are visually unambiguous" art_direction="the reward presentation feels celebratory and intentional rather than a generic row of boxes"
-- @screenshot type=ui angles=1

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
local HttpService = game:GetService("HttpService")
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_UI_002_daily_reward",
    prompt = {
        {
            {
                role = "user",
                content = [[Create a daily rewards popup for a 7-day streak system.

Show a title at the top, then 7 day slots in a horizontal row. Each slot should have a day number and a reward icon. Make day 3 the highlighted claimable day, show days 1 and 2 as already claimed and faded, and show later days as upcoming. Include a claim button below the row and a close button in the top-right corner. Make it look like a polished popup with rounded corners on a dark background.]],
                request_id = "vb_ui_002"
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

    -- Count Frames that could be day slots (small frames)
    local slotCount = 0
    for _, d in ipairs(screenGui:GetDescendants()) do
        if d:IsA("Frame") then
            local sz = d.AbsoluteSize
            -- Day slots are roughly 80x80, reward icons 40x40
            if sz.X >= 30 and sz.X <= 120 and sz.Y >= 30 and sz.Y <= 120 then
                slotCount = slotCount + 1
            end
        end
    end
    -- Need at least 7 slots (may include reward icon frames, so >= 7)
    assert(slotCount >= 7, string.format("Only %d slot-like frames found, need >= 7", slotCount))

    -- Find TextLabel with "Daily" or "Reward"
    local foundTitle = false
    for _, d in ipairs(screenGui:GetDescendants()) do
        if d:IsA("TextLabel") then
            local t = string.lower(d.Text)
            if string.find(t, "daily") or string.find(t, "reward") then
                foundTitle = true
                break
            end
        end
    end
    assert(foundTitle, "No TextLabel with 'Daily' or 'Reward' found")

    -- Find Claim button
    local foundClaim = false
    for _, d in ipairs(screenGui:GetDescendants()) do
        if d:IsA("TextButton") and string.find(string.lower(d.Text), "claim") then
            foundClaim = true
            break
        end
    end
    assert(foundClaim, "No TextButton with 'Claim' found")

    -- Find Close/X button
    local foundClose = false
    for _, d in ipairs(screenGui:GetDescendants()) do
        if d:IsA("TextButton") then
            local t = string.lower(d.Text)
            if string.find(t, "close") or t == "x" then
                foundClose = true
                break
            end
        end
    end
    assert(foundClose, "No close/X TextButton found")

    -- Strengthened: container coverage
    local function findLargeFrame(sg)
        for _, d in ipairs(sg:GetDescendants()) do
            if d:IsA("Frame") then
                local sz = d.AbsoluteSize
                if sz.X >= 300 and sz.Y >= 150 then return d end
            end
        end
        return nil
    end
    local container = findLargeFrame(screenGui)
    assert(container, "No container-sized frame found (should be a popup panel)")

    -- Strengthened: ZIndex ordering (container behind content)
    for _, d in ipairs(screenGui:GetDescendants()) do
        if d:IsA("TextLabel") or d:IsA("TextButton") then
            assert(d.ZIndex >= container.ZIndex, "Content elements should have ZIndex >= container")
        end
    end
end

eval.check_game = function()
end

return eval
