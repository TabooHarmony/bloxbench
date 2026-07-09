--!strict
-- Reference implementation for VB_UI_002_daily_reward
-- Hand-built correct solution for judge calibration and gate validation.
-- Run through the harness to verify: gate passes, judge scores >= 4/5.

local function build()
    local StarterGui = game:GetService("StarterGui")
    local HttpService = game:GetService("HttpService")

    -- Remove existing children
    StarterGui:ClearAllChildren()

    local sg = Instance.new("ScreenGui")
    sg.Name = "DailyRewardsGui"
    sg.ResetOnSpawn = false
    sg.Parent = StarterGui

    -- Container
    local container = Instance.new("Frame")
    container.Name = "Container"
    container.Size = UDim2.new(0, 700, 0, 300)
    container.Position = UDim2.new(0.5, -350, 0.5, -150)
    container.BackgroundColor3 = Color3.fromRGB(30, 30, 40)
    container.Parent = sg
    local containerCorner = Instance.new("UICorner")
    containerCorner.CornerRadius = UDim.new(0, 12)
    containerCorner.Parent = container

    -- Title
    local title = Instance.new("TextLabel")
    title.Name = "Title"
    title.Size = UDim2.new(1, 0, 0, 40)
    title.Position = UDim2.new(0, 0, 0, 10)
    title.BackgroundTransparency = 1
    title.Text = "Daily Rewards"
    title.TextColor3 = Color3.fromRGB(255, 255, 255)
    title.Font = Enum.Font.GothamBold
    title.TextSize = 28
    title.Parent = container

    -- 7 day slots
    local slotColors = {
        Color3.fromRGB(100, 150, 200),
        Color3.fromRGB(150, 100, 200),
        Color3.fromRGB(200, 200, 100),
        Color3.fromRGB(100, 200, 150),
        Color3.fromRGB(200, 150, 100),
        Color3.fromRGB(150, 200, 200),
        Color3.fromRGB(200, 100, 150),
    }
    local startX = 20
    local slotSize = 80
    local gap = 5
    for i = 1, 7 do
        local slot = Instance.new("Frame")
        slot.Name = "Day" .. i
        slot.Size = UDim2.new(0, slotSize, 0, slotSize)
        slot.Position = UDim2.new(0, startX + (i - 1) * (slotSize + gap), 0, 60)
        slot.BackgroundColor3 = Color3.fromRGB(50, 50, 60)
        slot.Parent = container
        local slotCorner = Instance.new("UICorner")
        slotCorner.CornerRadius = UDim.new(0, 6)
        slotCorner.Parent = slot

        -- Days 1-2 faded (already claimed)
        if i <= 2 then
            slot.BackgroundTransparency = 0.5
        end

        -- Day 3 highlighted with yellow border
        if i == 3 then
            local stroke = Instance.new("UIStroke")
            stroke.Color = Color3.fromRGB(255, 220, 50)
            stroke.Thickness = 3
            stroke.Parent = slot
        end

        -- Day number
        local dayLabel = Instance.new("TextLabel")
        dayLabel.Name = "DayLabel"
        dayLabel.Size = UDim2.new(1, 0, 0, 20)
        dayLabel.Position = UDim2.new(0, 0, 0, 5)
        dayLabel.BackgroundTransparency = 1
        dayLabel.Text = "Day " .. i
        dayLabel.TextColor3 = Color3.fromRGB(255, 255, 255)
        dayLabel.Font = Enum.Font.Gotham
        dayLabel.TextSize = 14
        dayLabel.Parent = slot

        -- Reward icon
        local icon = Instance.new("Frame")
        icon.Name = "RewardIcon"
        icon.Size = UDim2.new(0, 40, 0, 40)
        icon.Position = UDim2.new(0.5, -20, 0, 30)
        icon.BackgroundColor3 = slotColors[i]
        icon.Parent = slot
        local iconCorner = Instance.new("UICorner")
        iconCorner.CornerRadius = UDim.new(0, 4)
        iconCorner.Parent = icon
    end

    -- Claim button
    local claimBtn = Instance.new("TextButton")
    claimBtn.Name = "ClaimButton"
    claimBtn.Size = UDim2.new(0, 200, 0, 50)
    claimBtn.Position = UDim2.new(0.5, -100, 0, 160)
    claimBtn.BackgroundColor3 = Color3.fromRGB(80, 200, 100)
    claimBtn.Text = "Claim Day 3"
    claimBtn.TextColor3 = Color3.fromRGB(255, 255, 255)
    claimBtn.Font = Enum.Font.GothamBold
    claimBtn.TextSize = 18
    claimBtn.Parent = container
    local claimCorner = Instance.new("UICorner")
    claimCorner.CornerRadius = UDim.new(0, 8)
    claimCorner.Parent = claimBtn

    -- Close button (X in top-right)
    local closeBtn = Instance.new("TextButton")
    closeBtn.Name = "CloseButton"
    closeBtn.Size = UDim2.new(0, 40, 0, 40)
    closeBtn.Position = UDim2.new(1, -45, 0, 5)
    closeBtn.BackgroundColor3 = Color3.fromRGB(60, 60, 70)
    closeBtn.Text = "X"
    closeBtn.TextColor3 = Color3.fromRGB(255, 255, 255)
    closeBtn.Font = Enum.Font.GothamBold
    closeBtn.TextSize = 20
    closeBtn.Parent = container
    local closeCorner = Instance.new("UICorner")
    closeCorner.CornerRadius = UDim.new(0, 6)
    closeCorner.Parent = closeBtn
end

return build
