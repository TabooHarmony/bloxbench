--[[
    PartPrimitives v1 — structural composition blocks for Roblox building

    Unlike SpatialHelpers (placement helpers), PartPrimitives create CONNECTED
    subassemblies. Walls seat on floors. Roofs seat on walls. Limbs chain
    segments. Stacks seat levels on previous levels.

    P is auto-injected into every execute_luau call by the harness.
    Do NOT require() it, do NOT script_read this module.

    Primitives:
      P.floor(size, opts)              — ground-seated platform/foundation
      P.wall(size, opts)               — wall seated on floor/walls, with optional door/window openings
      P.roof(size, opts)               — pitched or flat roof seated on walls
      P.limb(segments, opts)           — connected chain of parts (tails, legs, branches)
      P.stack(levels, opts)            — stacked structure, each level on previous
      P.block(size, opts)              — simple block (when you just need a box)
      P.cyl(diameter, height, opts)    — vertical cylinder
      P.ball(diameter, opts)           — sphere
      P.wedge(size, opts)              — wedge part

    Placement opts (all optional):
      on = <BasePart>                  — seat this part on top of target
      at = {x, y, z}                   — absolute position (overrides on)
      offset = {x, y, z}              — offset after placement
      rotation = {rx, ry, rz}         — rotation in degrees

    Style opts:
      name, color={r,g,b}, material (string), transparency, anchored (default true)

    Wall-specific opts:
      door = {w=3, h=4, side="center"} — cut a door opening (real gap, not decal)
      door = {w=3, h=4, side="left"}   — side: "left", "right", "center"
      windows = {{w=2, h=2, y=3, side="center"}, ...} — cut window openings

    Roof-specific opts:
      style = "pitched" | "flat"       — pitched = A-frame from wedges
      direction = "x" | "z"            — ridge axis for pitched roof

    Limb-specific opts:
      origin = <BasePart>              — where the chain starts
      angle = degrees                  — initial upward angle
      yaw = degrees                    — horizontal rotation
      curve = degrees                  — per-segment angle change (for tails)

    Return value: all primitives return the first/main part (or a Model for stack).
    You can pass the return value as `on=` to the next primitive.
]]

local P = {}

-- ── helpers ──────────────────────────────────────────────────────

local MAT = {
    wood = "Wood", stone = "Slate", metal = "Metal", brick = "Brick",
    concrete = "Concrete", plastic = "Plastic", grass = "Grass",
    glass = "SmoothPlastic", neon = "Neon", ice = "Ice", sand = "Sand",
    snow = "Snow", fabric = "Fabric", ground = "Ground", asphalt = "Asphalt",
    marble = "Marble", slate = "Slate", woodplanks = "WoodPlanks",
    cobblestone = "Cobblestone", granite = "Granite", limestone = "Limestone",
    leafygrass = "LeafyGrass", diamondplate = "DiamondPlate",
    corrodedmetal = "CorrodedMetal", foil = "Foil", leather = "Leather",
    plaster = "Plaster", rubber = "Rubber", carpet = "Carpet",
    clayrooftiles = "ClayRoofTiles", roofshingles = "RoofShingles",
}

local function vec3(v, default)
    if v == nil then return default end
    if typeof(v) == "Vector3" then return v end
    if type(v) == "table" then
        return Vector3.new(v[1] or v.x or v.X or 0, v[2] or v.y or v.Y or 0, v[3] or v.z or v.Z or 0)
    end
    error("expected Vector3 or {x,y,z}")
end

local function resolveMaterial(name)
    if not name then return nil end
    local key = string.lower(tostring(name))
    local resolved = MAT[key]
    if resolved then
        local ok, mat = pcall(function() return Enum.Material[resolved] end)
        if ok then return mat end
    end
    local ok, mat = pcall(function() return Enum.Material[tostring(name)] end)
    if ok then return mat end
    return nil
end

local function applyStyle(part, opts)
    opts = opts or {}
    if opts.name then part.Name = opts.name end
    if opts.color then
        local c = opts.color
        if typeof(c) == "Color3" then
            part.Color = c
        elseif type(c) == "table" then
            part.Color = Color3.fromRGB(c[1] or c.r or 0, c[2] or c.g or 0, c[3] or c.b or 0)
        end
    end
    if opts.material then
        local mat = resolveMaterial(opts.material)
        if mat then part.Material = mat end
    end
    if opts.transparency ~= nil then part.Transparency = opts.transparency end
    if opts.anchored ~= nil then
        part.Anchored = opts.anchored
    else
        part.Anchored = true
    end
    if opts.can_collide ~= nil then part.CanCollide = opts.can_collide end
    return part
end

local function resolvePosition(selfSize, opts)
    opts = opts or {}
    local sh = selfSize * 0.5

    if opts.at ~= nil then
        local pos = vec3(opts.at)
        if opts.offset then pos = pos + vec3(opts.offset) end
        return pos
    end

    -- seat on top of target
    local target = opts.on
    if target then
        local tp, ts = target.Position, target.Size
        local cx, cz = tp.X, tp.Z
        local cy = (tp.Y + ts.Y * 0.5) + sh.Y  -- on top

        -- align XZ to target if no explicit position
        -- but respect size differences: center on target
        if opts.offset then
            return Vector3.new(cx, cy, cz) + vec3(opts.offset)
        end
        return Vector3.new(cx, cy, cz)
    end

    -- ground at origin
    local cx, cy, cz = 0, sh.Y, 0
    if opts.offset then
        return Vector3.new(cx, cy, cz) + vec3(opts.offset)
    end
    return Vector3.new(cx, cy, cz)
end

local function applyRotation(cf, opts)
    if not opts or not opts.rotation then return cf end
    local r = opts.rotation
    if type(r) == "table" then
        return cf * CFrame.Angles(
            math.rad(r[1] or 0),
            math.rad(r[2] or 0),
            math.rad(r[3] or 0)
        )
    end
    return cf
end

local function alignLengthAxis(position, direction, axis)
    local d = direction.Unit
    local reference = Vector3.new(0, 1, 0)
    if math.abs(d:Dot(reference)) > 0.99 then
        reference = Vector3.new(1, 0, 0)
    end

    local xAxis, yAxis
    if axis == "X" then
        xAxis = d
        yAxis = (reference - d * reference:Dot(d)).Unit
    elseif axis == "Z" then
        xAxis = (reference - d * reference:Dot(d)).Unit
        yAxis = d:Cross(xAxis).Unit
    else
        xAxis = reference:Cross(d).Unit
        yAxis = d
    end
    return CFrame.fromMatrix(position, xAxis, yAxis)
end

local function parentOf(opts)
    return (opts and opts.parent) or workspace
end

-- Build a wall by subtracting rectangular openings from its 2D footprint.
-- Opening coordinates are relative to the wall center on the span axis and
-- relative to the wall bottom on the vertical axis.
local function wallPanels(s, opts, wallPos, dir, openings)
    local span = dir == "x" and s.X or s.Z
    local thick = dir == "x" and s.Z or s.X
    local height = s.Y
    local xBounds = {-span * 0.5, span * 0.5}
    local yBounds = {0, height}

    local function addBound(bounds, value, minimum, maximum)
        value = math.max(minimum, math.min(value, maximum))
        for _, existing in ipairs(bounds) do
            if math.abs(existing - value) < 0.001 then return end
        end
        table.insert(bounds, value)
    end

    local validOpenings = {}
    for _, opening in ipairs(openings) do
        local x1 = math.max(-span * 0.5, math.min(opening.x1, span * 0.5))
        local x2 = math.max(-span * 0.5, math.min(opening.x2, span * 0.5))
        local y1 = math.max(0, math.min(opening.y1, height))
        local y2 = math.max(0, math.min(opening.y2, height))
        if x2 - x1 > 0.1 and y2 - y1 > 0.1 then
            table.insert(validOpenings, {x1 = x1, x2 = x2, y1 = y1, y2 = y2})
            addBound(xBounds, x1, -span * 0.5, span * 0.5)
            addBound(xBounds, x2, -span * 0.5, span * 0.5)
            addBound(yBounds, y1, 0, height)
            addBound(yBounds, y2, 0, height)
        end
    end

    if #validOpenings == 0 then
        return P.block(s, opts)
    end

    table.sort(xBounds)
    table.sort(yBounds)
    local parts = {}
    local panelIndex = 0
    for yi = 1, #yBounds - 1 do
        local y1, y2 = yBounds[yi], yBounds[yi + 1]
        for xi = 1, #xBounds - 1 do
            local x1, x2 = xBounds[xi], xBounds[xi + 1]
            local cx, cy = (x1 + x2) * 0.5, (y1 + y2) * 0.5
            local insideOpening = false
            for _, opening in ipairs(validOpenings) do
                if cx > opening.x1 and cx < opening.x2 and
                   cy > opening.y1 and cy < opening.y2 then
                    insideOpening = true
                    break
                end
            end

            if not insideOpening then
                panelIndex = panelIndex + 1
                local part = Instance.new("Part")
                if dir == "x" then
                    part.Size = Vector3.new(x2 - x1, y2 - y1, thick)
                    part.CFrame = CFrame.new(wallPos.X + cx, wallPos.Y - height * 0.5 + cy, wallPos.Z)
                else
                    part.Size = Vector3.new(thick, y2 - y1, x2 - x1)
                    part.CFrame = CFrame.new(wallPos.X, wallPos.Y - height * 0.5 + cy, wallPos.Z + cx)
                end
                part.CFrame = applyRotation(part.CFrame, opts)
                applyStyle(part, opts)
                part.Name = (opts.name or "Wall") .. "_Panel_" .. tostring(panelIndex)
                part.Parent = parentOf(opts)
                table.insert(parts, part)
            end
        end
    end

    return parts[1] or P.block(s, opts)
end

-- ── primitives ───────────────────────────────────────────────────

-- Simple block (like H.block but without placement vocabulary)
function P.block(size, opts)
    opts = opts or {}
    local s = vec3(size)
    local part = Instance.new("Part")
    part.Size = s
    part.TopSurface = Enum.SurfaceType.Smooth
    part.BottomSurface = Enum.SurfaceType.Smooth
    applyStyle(part, opts)
    local pos = resolvePosition(s, opts)
    local cf = CFrame.new(pos)
    cf = applyRotation(cf, opts)
    part.CFrame = cf
    part.Parent = parentOf(opts)
    return part
end

-- Floor / foundation / platform — seats on ground by default
function P.floor(size, opts)
    opts = opts or {}
    -- force ground seating unless explicit position given
    if opts.on == nil and opts.at == nil then
        -- ground: bottom at Y=0
        local s = vec3(size)
        local pos = Vector3.new(0, s.Y * 0.5, 0)
        if opts.offset then pos = pos + vec3(opts.offset) end
        if opts.at then pos = vec3(opts.at) end
        opts = table.clone(opts)
        opts.at = pos
    end
    return P.block(size, opts)
end

-- Vertical cylinder
function P.cyl(diameter, height, opts)
    opts = opts or {}
    local part = Instance.new("Part")
    part.Shape = Enum.PartType.Cylinder
    part.Size = Vector3.new(height, diameter, diameter)
    applyStyle(part, opts)
    -- cylinder axis is +X, rotate to vertical (Y)
    local visualSize = Vector3.new(diameter, height, diameter)
    local pos = resolvePosition(visualSize, opts)
    local cf = CFrame.new(pos) * CFrame.Angles(0, 0, math.rad(90))
    cf = applyRotation(cf, opts)
    part.CFrame = cf
    part.Parent = parentOf(opts)
    return part
end

-- Sphere
function P.ball(diameter, opts)
    opts = opts or {}
    local part = Instance.new("Part")
    part.Shape = Enum.PartType.Ball
    part.Size = Vector3.new(diameter, diameter, diameter)
    applyStyle(part, opts)
    local pos = resolvePosition(Vector3.new(diameter, diameter, diameter), opts)
    local cf = CFrame.new(pos)
    cf = applyRotation(cf, opts)
    part.CFrame = cf
    part.Parent = parentOf(opts)
    return part
end

-- Wedge
function P.wedge(size, opts)
    opts = opts or {}
    local s = vec3(size)
    local part = Instance.new("WedgePart")
    part.Size = s
    applyStyle(part, opts)
    local pos = resolvePosition(s, opts)
    local cf = CFrame.new(pos)
    cf = applyRotation(cf, opts)
    part.CFrame = cf
    part.Parent = parentOf(opts)
    return part
end

--[[
    P.wall — wall with optional door and window openings

    Creates wall panels with REAL gaps for doors/windows (not decals).
    If door specified, the wall is split into panels around the opening.
    Wall auto-seats on top of `on` target (floor or another wall).

    opts:
      on = <part>           seat on top of this
      door = {w=3, h=4, side="center"}   cut door gap
      windows = {{w=2, h=2, y=3, side="center"}, ...}
      direction = "x" | "z"  wall orientation (default "z" = wall faces north/south)
      offset = {x,y,z}
]]
function P.wall(size, opts)
    opts = opts or {}
    local s = vec3(size)
    local dir = opts.direction or "z"

    -- if no door/windows, just make a simple block
    if not opts.door and not opts.windows then
        return P.block(s, opts)
    end

    -- wall with openings: create multiple panels
    local parts = {}
    local parent = parentOf(opts)

    -- determine wall position
    local wallPos
    if opts.on then
        local tp, ts = opts.on.Position, opts.on.Size
        wallPos = Vector3.new(tp.X, (tp.Y + ts.Y * 0.5) + s.Y * 0.5, tp.Z)
    elseif opts.at then
        wallPos = vec3(opts.at)
    else
        wallPos = Vector3.new(0, s.Y * 0.5, 0)
    end
    if opts.offset then
        wallPos = wallPos + vec3(opts.offset)
    end

    -- wall spans along dir axis, thickness on the other
    local spanAxis, thickAxis
    if dir == "x" then
        spanAxis, thickAxis = "X", "Z"
    else
        spanAxis, thickAxis = "Z", "X"
    end

    local span = s[spanAxis]
    local thick = s[thickAxis]
    local height = s.Y

    -- door opening
    local door = opts.door
    local doorW, doorH, doorSide
    if door then
        doorW = door.w or 3
        doorH = door.h or 4
        doorSide = door.side or "center"
    end

    -- calculate door X/Z position along span
    local doorCenter = 0  -- relative to wall center
    if door then
        if doorSide == "left" then
            doorCenter = -(span / 2) + (doorW / 2)
        elseif doorSide == "right" then
            doorCenter = (span / 2) - (doorW / 2)
        else
            doorCenter = 0  -- center
        end
    end

    -- Windows need the same real-gap treatment as doors. When both are
    -- supplied, subtract both from one wall grid so they cannot overlap.
    if type(opts.windows) == "table" then
        local openings = {}
        if door then
            table.insert(openings, {
                x1 = doorCenter - doorW * 0.5,
                x2 = doorCenter + doorW * 0.5,
                y1 = 0,
                y2 = doorH,
            })
        end
        for _, window in ipairs(opts.windows) do
            if type(window) == "table" then
                local windowW = window.w or 2
                local windowH = window.h or 2
                local windowSide = window.side or "center"
                local windowCenter = window.x or window.center
                if windowCenter == nil then
                    if windowSide == "left" then
                        windowCenter = -(span * 0.5) + windowW * 0.5
                    elseif windowSide == "right" then
                        windowCenter = span * 0.5 - windowW * 0.5
                    else
                        windowCenter = 0
                    end
                end
                local windowY = window.y or (height * 0.5)
                table.insert(openings, {
                    x1 = windowCenter - windowW * 0.5,
                    x2 = windowCenter + windowW * 0.5,
                    y1 = windowY - windowH * 0.5,
                    y2 = windowY + windowH * 0.5,
                })
            end
        end
        return wallPanels(s, opts, wallPos, dir, openings)
    end

    -- build panels around the door opening
    if door then
        -- bottom panel (below door)
        if doorH < height then
            local bottomH = doorH
            local bottomPanel = Instance.new("Part")
            bottomPanel.Size = Vector3.new(
                dir == "x" and span or thick,
                bottomH,
                dir == "x" and thick or span
            )
            local bottomPos = Vector3.new(
                wallPos.X + (dir == "x" and 0 or 0),
                wallPos.Y - (height / 2) + (bottomH / 2),
                wallPos.Z + (dir == "z" and 0 or 0)
            )
            -- adjust for door position along span
            if dir == "x" then
                bottomPos = Vector3.new(wallPos.X + doorCenter, bottomPos.Y, wallPos.Z)
            else
                bottomPos = Vector3.new(wallPos.X, bottomPos.Y, wallPos.Z + doorCenter)
            end
            bottomPanel.CFrame = CFrame.new(bottomPos)
            applyStyle(bottomPanel, opts)
            bottomPanel.Name = (opts.name or "Wall") .. "_Bottom"
            bottomPanel.Parent = parent
            table.insert(parts, bottomPanel)
        end

        -- left panel (left of door, looking at wall)
        local leftW
        if doorSide == "center" then
            leftW = (span - doorW) / 2
        elseif doorSide == "left" then
            leftW = span - doorW
        else
            leftW = 0  -- door is on the right, no left panel beyond what center gives
        end

        if leftW > 0.1 then
            local leftPanel = Instance.new("Part")
            leftPanel.Size = Vector3.new(
                dir == "x" and leftW or thick,
                height - doorH,
                dir == "x" and thick or leftW
            )
            local leftCenter
            if doorSide == "center" then
                leftCenter = -(span / 2) + (leftW / 2)
            elseif doorSide == "left" then
                leftCenter = doorCenter + (doorW / 2) + (leftW / 2)
            else
                leftCenter = -(span / 2) + (leftW / 2)
            end
            local leftPos = Vector3.new(
                wallPos.X + (dir == "x" and leftCenter or 0),
                wallPos.Y + (doorH / 2) - (height / 2) + ((height - doorH) / 2),
                wallPos.Z + (dir == "z" and leftCenter or 0)
            )
            leftPanel.CFrame = CFrame.new(leftPos)
            applyStyle(leftPanel, opts)
            leftPanel.Name = (opts.name or "Wall") .. "_Left"
            leftPanel.Parent = parent
            table.insert(parts, leftPanel)
        end

        -- right panel (right of door)
        local rightW
        if doorSide == "center" then
            rightW = (span - doorW) / 2
        elseif doorSide == "right" then
            rightW = span - doorW
        else
            rightW = 0
        end

        if rightW > 0.1 then
            local rightPanel = Instance.new("Part")
            rightPanel.Size = Vector3.new(
                dir == "x" and rightW or thick,
                height - doorH,
                dir == "x" and thick or rightW
            )
            local rightCenter
            if doorSide == "center" then
                rightCenter = (span / 2) - (rightW / 2)
            elseif doorSide == "right" then
                rightCenter = doorCenter - (doorW / 2) - (rightW / 2)
            else
                rightCenter = (span / 2) - (rightW / 2)
            end
            local rightPos = Vector3.new(
                wallPos.X + (dir == "x" and rightCenter or 0),
                wallPos.Y + (doorH / 2) - (height / 2) + ((height - doorH) / 2),
                wallPos.Z + (dir == "z" and rightCenter or 0)
            )
            rightPanel.CFrame = CFrame.new(rightPos)
            applyStyle(rightPanel, opts)
            rightPanel.Name = (opts.name or "Wall") .. "_Right"
            rightPanel.Parent = parent
            table.insert(parts, rightPanel)
        end

        -- top panel (above door, full span)
        local topH = height - doorH
        if topH > 0.1 then
            local topPanel = Instance.new("Part")
            topPanel.Size = Vector3.new(
                dir == "x" and doorW or thick,
                topH,
                dir == "x" and thick or doorW
            )
            local topPos = Vector3.new(
                wallPos.X + (dir == "x" and doorCenter or 0),
                wallPos.Y + (height / 2) - (topH / 2),
                wallPos.Z + (dir == "z" and doorCenter or 0)
            )
            topPanel.CFrame = CFrame.new(topPos)
            applyStyle(topPanel, opts)
            topPanel.Name = (opts.name or "Wall") .. "_Top"
            topPanel.Parent = parent
            table.insert(parts, topPanel)
        end
    else
        -- no door, just simple wall
        local panel = Instance.new("Part")
        panel.Size = s
        panel.CFrame = CFrame.new(wallPos)
        applyStyle(panel, opts)
        panel.Name = opts.name or "Wall"
        panel.Parent = parent
        table.insert(parts, panel)
    end

    -- return the first (main) part for chaining
    return parts[1] or P.block(s, opts)
end

--[[
    P.roof — pitched or flat roof seated on walls

    opts:
      on = <part>           seat on top of this (usually a wall)
      style = "pitched" | "flat"  (default "pitched")
      direction = "x" | "z"  ridge axis (default "x")
      overhang = number      how far roof extends past walls (default 1)
]]
function P.roof(size, opts)
    opts = opts or {}
    local s = vec3(size)
    local style = opts.style or "pitched"
    local dir = opts.direction or "x"
    local overhang = opts.overhang or 1
    local parent = parentOf(opts)

    -- roofPos is the bottom plane for pitched roofs. Flat roofs use its
    -- center after adding half the thickness below.
    local roofPos
    if opts.on then
        local tp, ts = opts.on.Position, opts.on.Size
        roofPos = Vector3.new(tp.X, tp.Y + ts.Y * 0.5, tp.Z)
    elseif opts.at then
        roofPos = vec3(opts.at)
    else
        roofPos = Vector3.new(0, 0, 0)
    end
    if opts.offset then
        roofPos = roofPos + vec3(opts.offset)
    end

    if style == "flat" then
        local panel = Instance.new("Part")
        panel.Size = Vector3.new(s.X + overhang * 2, s.Y, s.Z + overhang * 2)
        panel.CFrame = CFrame.new(roofPos + Vector3.new(0, s.Y * 0.5, 0))
        applyStyle(panel, opts)
        panel.Name = opts.name or "Roof"
        panel.Parent = parent
        return panel
    end

    -- pitched roof: two wedges forming A-frame
    -- ridge runs along dir axis
    local span, depth
    if dir == "x" then
        span, depth = s.X, s.Z
    else
        span, depth = s.Z, s.X
    end

    local halfSpan = (span + overhang * 2) / 2
    local roofHeight = s.Y
    local roofDepth = depth + overhang * 2

    -- two wedge panels
    local wedge1 = Instance.new("WedgePart")
    local wedge2 = Instance.new("WedgePart")

    -- wedges: width = roofDepth, height = roofHeight, length = halfSpan
    -- WedgePart slopes up from one end to the other
    if dir == "x" then
        -- ridge along X, slopes on Z
        wedge1.Size = Vector3.new(span + overhang * 2, roofHeight, roofDepth / 2)
        wedge2.Size = Vector3.new(span + overhang * 2, roofHeight, roofDepth / 2)
        -- wedge1: front slope (faces -Z), wedge2: back slope (faces +Z)
        -- WedgePart default: thin end at -Z, thick end at +Z
        -- For front slope: thick at center (ridge), thin at edge
        -- We need to rotate wedge1 so thick end is at center
        wedge1.CFrame = CFrame.new(roofPos.X, roofPos.Y + roofHeight / 2, roofPos.Z - roofDepth / 4)
            * CFrame.Angles(0, math.rad(180), 0)
        wedge2.CFrame = CFrame.new(roofPos.X, roofPos.Y + roofHeight / 2, roofPos.Z + roofDepth / 4)
    else
        -- ridge along Z, slopes on X
        wedge1.Size = Vector3.new(roofDepth / 2, roofHeight, span + overhang * 2)
        wedge2.Size = Vector3.new(roofDepth / 2, roofHeight, span + overhang * 2)
        wedge1.CFrame = CFrame.new(roofPos.X - roofDepth / 4, roofPos.Y + roofHeight / 2, roofPos.Z)
            * CFrame.Angles(0, math.rad(90), 0)
        wedge2.CFrame = CFrame.new(roofPos.X + roofDepth / 4, roofPos.Y + roofHeight / 2, roofPos.Z)
            * CFrame.Angles(0, math.rad(-90), 0)
    end

    applyStyle(wedge1, opts)
    applyStyle(wedge2, opts)
    wedge1.Name = (opts.name or "Roof") .. "_Front"
    wedge2.Name = (opts.name or "Roof") .. "_Back"
    wedge1.Parent = parent
    wedge2.Parent = parent

    return wedge1
end

--[[
    P.limb — connected chain of segments for tails, legs, branches, necks

    segments = {{w, h, d}, {w, h, d}, ...}  sizes of each segment (tapering)
    opts:
      origin = <part>       where chain starts (seats on top of this)
      angle = degrees       initial upward angle from horizontal (0 = horizontal, 90 = straight up)
      yaw = degrees         horizontal rotation (0 = +X direction)
      curve = degrees       per-segment angle change (positive = curves up)
      offset = {x,y,z}     offset from origin

    Returns the first segment part for chaining.
]]
function P.limb(segments, opts)
    opts = opts or {}
    local parent = parentOf(opts)
    local angle = math.rad(opts.angle or 0)
    local yaw = math.rad(opts.yaw or 0)
    local curve = math.rad(opts.curve or 0)

    -- starting position: on top of origin
    local startX, startY, startZ
    if opts.origin then
        local tp, ts = opts.origin.Position, opts.origin.Size
        startX = tp.X
        startY = tp.Y + ts.Y * 0.5
        startZ = tp.Z
    else
        startX, startY, startZ = 0, 0, 0
    end
    if opts.offset then
        local o = vec3(opts.offset)
        startX, startY, startZ = startX + o.X, startY + o.Y, startZ + o.Z
    end

    local firstPart = nil
    local currentAngle = angle
    local currentYaw = yaw
    local prevX, prevY, prevZ = startX, startY, startZ

    for i, seg in ipairs(segments) do
        local sw, sh, sd = seg[1] or 2, seg[2] or 2, seg[3] or 2
        -- taper: if single number given, use as diameter
        if type(seg) == "number" then
            sw, sh, sd = seg, seg, seg
        end

        local part = Instance.new("Part")
        part.Size = Vector3.new(sw, sh, sd)
        applyStyle(part, opts)
        if opts.name then
            part.Name = opts.name .. "_" .. tostring(i)
        else
            part.Name = "Limb_" .. tostring(i)
        end

        -- compute position: segment extends from prev point at currentAngle/currentYaw
        -- direction vector
        local dirX = math.cos(currentAngle) * math.cos(currentYaw)
        local dirY = math.sin(currentAngle)
        local dirZ = math.cos(currentAngle) * math.sin(currentYaw)

        -- Align the longest physical axis with the chain direction. This
        -- preserves the documented {width, height, depth} sizes while making
        -- {4,3,3} a four-stud horizontal segment instead of a three-stud one.
        local lengthAxis = "Y"
        if sw > sh and sw >= sd then
            lengthAxis = "X"
        elseif sd > sh then
            lengthAxis = "Z"
        end
        local segLen = lengthAxis == "X" and sw or (lengthAxis == "Z" and sd or sh)
        local halfLen = segLen * 0.5

        local cx = prevX + dirX * halfLen
        local cy = prevY + dirY * halfLen
        local cz = prevZ + dirZ * halfLen

        local direction = Vector3.new(dirX, dirY, dirZ)
        if direction.Magnitude > 0.01 then
            part.CFrame = alignLengthAxis(Vector3.new(cx, cy, cz), direction, lengthAxis)
        else
            part.CFrame = CFrame.new(cx, cy, cz)
        end

        if opts.rotation then
            part.CFrame = applyRotation(part.CFrame, opts)
        end

        part.Parent = parent

        if not firstPart then firstPart = part end

        -- next segment starts at the end of this one
        prevX = cx + dirX * halfLen
        prevY = cy + dirY * halfLen
        prevZ = cz + dirZ * halfLen

        -- apply curve for next segment
        currentAngle = currentAngle + curve
    end

    return firstPart
end

--[[
    P.stack — stacked structure, each level seated on previous

    levels = {{w, h, d}, ...} or {{w, h, d, material=...}, ...}
    opts:
      at = {x,y,z}          starting position (bottom level center)
      on = <part>            seat first level on top of this
      material, color, etc.  applied to all levels (overridden per-level if specified)

    Returns a Model containing all level parts.
]]
function P.stack(levels, opts)
    opts = opts or {}
    local parent = parentOf(opts)
    local model = Instance.new("Model")
    model.Name = opts.name or "Stack"
    model.Parent = parent

    local baseY
    if opts.on then
        local tp, ts = opts.on.Position, opts.on.Size
        baseY = tp.Y + ts.Y * 0.5
    elseif opts.at then
        local a = vec3(opts.at)
        baseY = a.Y
    else
        baseY = 0
    end

    local cx = 0
    local cz = 0
    if opts.on then
        cx = opts.on.Position.X
        cz = opts.on.Position.Z
    end
    if opts.at then
        local a = vec3(opts.at)
        cx, cz = a.X, a.Z
    end

    local currentY = baseY
    local parts = {}

    for i, level in ipairs(levels) do
        local lw, lh, ld
        local levelOpts = {}

        if type(level) == "table" then
            lw = level[1] or 4
            lh = level[2] or 4
            ld = level[3] or 4
            -- per-level overrides
            if level.material then levelOpts.material = level.material end
            if level.color then levelOpts.color = level.color end
            if level.name then levelOpts.name = level.name end
        elseif type(level) == "number" then
            lw, lh, ld = level, level, level
        end

        -- merge base opts with per-level opts
        local mergedOpts = {}
        for k, v in pairs(opts) do mergedOpts[k] = v end
        for k, v in pairs(levelOpts) do mergedOpts[k] = v end
        mergedOpts.parent = model
        if not mergedOpts.name then
            mergedOpts.name = (opts.name or "Stack") .. "_L" .. tostring(i)
        end

        local part = Instance.new("Part")
        part.Size = Vector3.new(lw, lh, ld)
        part.TopSurface = Enum.SurfaceType.Smooth
        part.BottomSurface = Enum.SurfaceType.Smooth
        applyStyle(part, mergedOpts)
        -- seat on top of previous level
        local centerY = currentY + lh * 0.5
        part.CFrame = CFrame.new(cx, centerY, cz)
        if mergedOpts.rotation then
            part.CFrame = applyRotation(part.CFrame, mergedOpts)
        end
        part.Parent = model
        table.insert(parts, part)

        currentY = currentY + lh
    end

    -- set model primary part for positioning
    if parts[1] then
        model.PrimaryPart = parts[1]
    end

    return model
end

return P
