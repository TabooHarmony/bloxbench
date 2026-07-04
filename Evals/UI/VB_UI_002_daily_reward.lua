--!strict
-- @judge_rubric correctness="7 slots in horizontal row, day 3 highlighted, days 1-2 dimmed" layout="centered container, slots aligned" aesthetics="styled container with corners, slot borders" completeness="title + 7 day slots + claim + close"
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

Layout:
- Title TextLabel: "Daily Rewards" at the top, centered
- 7 day slots in a horizontal row, each 80x80:
  - Day number TextLabel (1-7) at top of each slot
  - Reward icon Frame below the number (40x40, different color per day)
  - Day 3 slot should have a yellow border (UIStroke, 3px) to indicate claimable
  - Days 1-2 should be slightly transparent (0.5) to show already claimed
- Claim TextButton: "Claim Day 3" below the row, green, 200x50
- Close TextButton: "X" in the top-right corner, 40x40

ScreenGui in StarterGui. Container frame should be 700x300, centered, dark background with UICorner radius 12.]],
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
end

eval.check_game = function()
end

return eval
