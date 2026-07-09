--!strict
-- Reference implementation for VB_UI_003_trade_window
-- Hand-built correct solution for judge calibration and gate validation.
-- Run through the harness to verify: gate passes, judge scores >= 4/5.

local function build()
    local StarterGui = game:GetService("StarterGui")
    StarterGui:ClearAllChildren()

    local sg = Instance.new("ScreenGui")
    sg.Name = "TradeGui"
    sg.ResetOnSpawn = false
    sg.Parent = StarterGui

    -- Container
    local container = Instance.new("Frame")
    container.Name = "Container"
    container.Size = UDim2.new(0, 640, 0, 400)
    container.Position = UDim2.new(0.5, -320, 0.5, -200)
    container.BackgroundColor3 = Color3.fromRGB(30, 30, 40)
    container.Parent = sg
    local containerCorner = Instance.new("UICorner")
    containerCorner.CornerRadius = UDim.new(0, 10)
    containerCorner.Parent = container

    -- Header
    local header = Instance.new("TextLabel")
    header.Name = "Header"
    header.Size = UDim2.new(1, 0, 0, 40)
    header.Position = UDim2.new(0, 0, 0, 10)
    header.BackgroundTransparency = 1
    header.Text = "Trade with Player1"
    header.TextColor3 = Color3.fromRGB(255, 255, 255)
    header.Font = Enum.Font.GothamBold
    header.TextSize = 22
    header.Parent = container

    -- Left panel (You)
    local leftPanel = Instance.new("Frame")
    leftPanel.Name = "LeftPanel"
    leftPanel.Size = UDim2.new(0, 300, 0, 250)
    leftPanel.Position = UDim2.new(0, 10, 0, 60)
    leftPanel.BackgroundColor3 = Color3.fromRGB(45, 45, 60)
    leftPanel.Parent = container
    local leftCorner = Instance.new("UICorner")
    leftCorner.CornerRadius = UDim.new(0, 8)
    leftCorner.Parent = leftPanel

    local leftLabel = Instance.new("TextLabel")
    leftLabel.Name = "YouLabel"
    leftLabel.Size = UDim2.new(1, 0, 0, 25)
    leftLabel.Position = UDim2.new(0, 0, 0, 5)
    leftLabel.BackgroundTransparency = 1
    leftLabel.Text = "You"
    leftLabel.TextColor3 = Color3.fromRGB(255, 255, 255)
    leftLabel.Font = Enum.Font.GothamBold
    leftLabel.TextSize = 18
    leftLabel.Parent = leftPanel

    -- Left 2x2 grid of item slots
    for i = 0, 3 do
        local slot = Instance.new("Frame")
        slot.Name = "LeftSlot" .. (i + 1)
        slot.Size = UDim2.new(0, 60, 0, 60)
        local col = i % 2
        local row = math.floor(i / 2)
        slot.Position = UDim2.new(0, 30 + col * 70, 0, 40 + row * 70)
        slot.BackgroundColor3 = Color3.fromRGB(60, 60, 75)
        slot.Parent = leftPanel
        local slotCorner = Instance.new("UICorner")
        slotCorner.CornerRadius = UDim.new(0, 4)
        slotCorner.Parent = slot
    end

    local leftCoins = Instance.new("TextLabel")
    leftCoins.Name = "LeftCoins"
    leftCoins.Size = UDim2.new(1, 0, 0, 25)
    leftCoins.Position = UDim2.new(0, 0, 0, 215)
    leftCoins.BackgroundTransparency = 1
    leftCoins.Text = "1,250"
    leftCoins.TextColor3 = Color3.fromRGB(255, 220, 100)
    leftCoins.Font = Enum.Font.GothamBold
    leftCoins.TextSize = 16
    leftCoins.Parent = leftPanel

    -- Right panel (Them)
    local rightPanel = Instance.new("Frame")
    rightPanel.Name = "RightPanel"
    rightPanel.Size = UDim2.new(0, 300, 0, 250)
    rightPanel.Position = UDim2.new(0, 330, 0, 60)
    rightPanel.BackgroundColor3 = Color3.fromRGB(45, 45, 60)
    rightPanel.Parent = container
    local rightCorner = Instance.new("UICorner")
    rightCorner.CornerRadius = UDim.new(0, 8)
    rightCorner.Parent = rightPanel

    local rightLabel = Instance.new("TextLabel")
    rightLabel.Name = "ThemLabel"
    rightLabel.Size = UDim2.new(1, 0, 0, 25)
    rightLabel.Position = UDim2.new(0, 0, 0, 5)
    rightLabel.BackgroundTransparency = 1
    rightLabel.Text = "Them"
    rightLabel.TextColor3 = Color3.fromRGB(255, 255, 255)
    rightLabel.Font = Enum.Font.GothamBold
    rightLabel.TextSize = 18
    rightLabel.Parent = rightPanel

    -- Right 2x2 grid of item slots
    for i = 0, 3 do
        local slot = Instance.new("Frame")
        slot.Name = "RightSlot" .. (i + 1)
        slot.Size = UDim2.new(0, 60, 0, 60)
        local col = i % 2
        local row = math.floor(i / 2)
        slot.Position = UDim2.new(0, 30 + col * 70, 0, 40 + row * 70)
        slot.BackgroundColor3 = Color3.fromRGB(60, 60, 75)
        slot.Parent = rightPanel
        local slotCorner = Instance.new("UICorner")
        slotCorner.CornerRadius = UDim.new(0, 4)
        slotCorner.Parent = slot
    end

    local rightCoins = Instance.new("TextLabel")
    rightCoins.Name = "RightCoins"
    rightCoins.Size = UDim2.new(1, 0, 0, 25)
    rightCoins.Position = UDim2.new(0, 0, 0, 215)
    rightCoins.BackgroundTransparency = 1
    rightCoins.Text = "0"
    rightCoins.TextColor3 = Color3.fromRGB(255, 220, 100)
    rightCoins.Font = Enum.Font.GothamBold
    rightCoins.TextSize = 16
    rightCoins.Parent = rightPanel

    -- Accept button (green)
    local acceptBtn = Instance.new("TextButton")
    acceptBtn.Name = "AcceptButton"
    acceptBtn.Size = UDim2.new(0, 150, 0, 45)
    acceptBtn.Position = UDim2.new(0.5, -160, 0, 330)
    acceptBtn.BackgroundColor3 = Color3.fromRGB(80, 200, 100)
    acceptBtn.Text = "Accept"
    acceptBtn.TextColor3 = Color3.fromRGB(255, 255, 255)
    acceptBtn.Font = Enum.Font.GothamBold
    acceptBtn.TextSize = 18
    acceptBtn.Parent = container
    local acceptCorner = Instance.new("UICorner")
    acceptCorner.CornerRadius = UDim.new(0, 8)
    acceptCorner.Parent = acceptBtn

    -- Cancel button (red)
    local cancelBtn = Instance.new("TextButton")
    cancelBtn.Name = "CancelButton"
    cancelBtn.Size = UDim2.new(0, 150, 0, 45)
    cancelBtn.Position = UDim2.new(0.5, 10, 0, 330)
    cancelBtn.BackgroundColor3 = Color3.fromRGB(200, 80, 80)
    cancelBtn.Text = "Cancel"
    cancelBtn.TextColor3 = Color3.fromRGB(255, 255, 255)
    cancelBtn.Font = Enum.Font.GothamBold
    cancelBtn.TextSize = 18
    cancelBtn.Parent = container
    local cancelCorner = Instance.new("UICorner")
    cancelCorner.CornerRadius = UDim.new(0, 8)
    cancelCorner.Parent = cancelBtn
end

return build
