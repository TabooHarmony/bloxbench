--!strict
-- Reference implementation for VB_BUILD_004_campfire
-- Hand-built correct solution for judge calibration and gate validation.
-- Run through the harness to verify: gate passes, judge scores >= 4/5.

local function build()
    -- Clear workspace (except baseplate)
    for _, obj in ipairs(workspace:GetChildren()) do
        if obj.Name ~= "Baseplate" and not obj:IsA("Terrain") then
            obj:Destroy()
        end
    end

    -- Fire pit (cylinder, dark, flat)
    local pit = Instance.new("Part")
    pit.Name = "FirePit"
    pit.Shape = Enum.PartType.Cylinder
    pit.Size = Vector3.new(1, 6, 6)  -- cylinder is oriented along X axis
    pit.Position = Vector3.new(0, 0.5, 0)
    pit.BrickColor = BrickColor.new("Dark stone grey")
    pit.Anchored = true
    pit.Parent = workspace

    -- Fire parts (3-5 stacked above pit)
    local fireColors = { BrickColor.new("Bright orange"), BrickColor.new("Bright red"), BrickColor.new("New Yeller") }
    for i = 1, 4 do
        local flame = Instance.new("Part")
        flame.Name = "Flame" .. i
        flame.Size = Vector3.new(2 + i * 0.5, 2 + i * 0.5, 2 + i * 0.5)
        flame.Position = Vector3.new(0, 1.5 + i * 1.5, 0)
        flame.BrickColor = fireColors[(i % 3) + 1]
        flame.Anchored = true
        flame.Parent = workspace
    end

    -- 4 seating logs (cylinders in square around pit)
    local logPositions = {
        { x = 6, z = 0 },
        { x = -6, z = 0 },
        { x = 0, z = 6 },
        { x = 0, z = -6 },
    }
    for i, pos in ipairs(logPositions) do
        local log = Instance.new("Part")
        log.Name = "Log" .. i
        log.Shape = Enum.PartType.Cylinder
        log.Size = Vector3.new(5, 2, 2)  -- length along X
        log.Position = Vector3.new(pos.x, 0.5, pos.z)
        log.BrickColor = BrickColor.new("Brown")
        log.Anchored = true
        log.Parent = workspace
    end

    -- Nature elements (4+ around scene)
    -- Tree 1 (trunk + leaves)
    local trunk1 = Instance.new("Part")
    trunk1.Name = "Trunk1"
    trunk1.Size = Vector3.new(2, 8, 2)
    trunk1.Position = Vector3.new(12, 4, 12)
    trunk1.BrickColor = BrickColor.new("Brown")
    trunk1.Anchored = true
    trunk1.Parent = workspace

    local leaves1 = Instance.new("Part")
    leaves1.Name = "Leaves1"
    leaves1.Shape = Enum.PartType.Ball
    leaves1.Size = Vector3.new(8, 8, 8)
    leaves1.Position = Vector3.new(12, 10, 12)
    leaves1.BrickColor = BrickColor.new("Bright green")
    leaves1.Anchored = true
    leaves1.Parent = workspace

    -- Rock 1
    local rock1 = Instance.new("Part")
    rock1.Name = "Rock1"
    rock1.Shape = Enum.PartType.Ball
    rock1.Size = Vector3.new(4, 4, 4)
    rock1.Position = Vector3.new(-12, 2, 12)
    rock1.BrickColor = BrickColor.new("Medium grey")
    rock1.Anchored = true
    rock1.Parent = workspace

    -- Bush 1
    local bush1 = Instance.new("Part")
    bush1.Name = "Bush1"
    bush1.Shape = Enum.PartType.Ball
    bush1.Size = Vector3.new(3, 3, 3)
    bush1.Position = Vector3.new(12, 1.5, -12)
    bush1.BrickColor = BrickColor.new("Dark green")
    bush1.Anchored = true
    bush1.Parent = workspace

    -- Rock 2 (wedge for variety)
    local rock2 = Instance.new("WedgePart")
    rock2.Name = "Rock2"
    rock2.Size = Vector3.new(3, 3, 3)
    rock2.Position = Vector3.new(-12, 1.5, -12)
    rock2.BrickColor = BrickColor.new("Dark grey")
    rock2.Anchored = true
    rock2.Parent = workspace
end

return build
