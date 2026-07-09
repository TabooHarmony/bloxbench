--[[
    SpatialHelpers v2 — create-and-place factories for Roblox building

    Prefer factories (H.block / H.cyl / H.ball / H.wedge). They create,
    style, place, and parent in one call. H.place moves an existing part.

    Placement opts (all optional fields):
      ground = true                 -- bottom on Y=0 (keeps X/Z unless at given)
      on_top = <BasePart>           -- bottom of self on top of target
      of = <BasePart>               -- reference for on/corner/face
      on = "top"|"bottom"|"ground"  -- with `of` (default "top" if of set)
      corner = "nw"|"ne"|"sw"|"se"  -- XZ corner of `of` / on_top target
      face = "north"|"south"|"east"|"west"  -- outside that face
      gap = number                  -- studs beyond face (default 0)
      at = Vector3 | {x,y,z}        -- absolute center (overrides other pose)
      offset = Vector3 | {x,y,z}    -- added after placement
]]

local SpatialHelpers = {}

local FACE_XZ = {
	north = Vector3.new(0, 0, -1),
	south = Vector3.new(0, 0, 1),
	east = Vector3.new(1, 0, 0),
	west = Vector3.new(-1, 0, 0),
}

local CORNER_XZ = {
	nw = Vector3.new(-1, 0, -1),
	ne = Vector3.new(1, 0, -1),
	sw = Vector3.new(-1, 0, 1),
	se = Vector3.new(1, 0, 1),
}

local MAT = {
	wood = "Wood",
	stone = "Slate",
	metal = "Metal",
	brick = "Brick",
	concrete = "Concrete",
	plastic = "Plastic",
	grass = "Grass",
	glass = "SmoothPlastic",
	neon = "Neon",
	ice = "Ice",
	sand = "Sand",
	snow = "Snow",
	fabric = "Fabric",
	ground = "Ground",
	asphalt = "Asphalt",
	marble = "Marble",
	slate = "Slate",
	woodplanks = "WoodPlanks",
}

local function vec3(v, default)
	if v == nil then
		return default
	end
	if typeof(v) == "Vector3" then
		return v
	end
	if type(v) == "table" then
		return Vector3.new(v[1] or v.x or v.X or 0, v[2] or v.y or v.Y or 0, v[3] or v.z or v.Z or 0)
	end
	error("expected Vector3 or {x,y,z}")
end

local function half(size)
	return size * 0.5
end

local function bounds(part)
	-- axis-aligned from Position/Size (good enough for axis-aligned builds)
	local p, s = part.Position, part.Size
	return {
		c = p,
		s = s,
		h = half(s),
		min = p - half(s),
		max = p + half(s),
	}
end

local function applyStyle(part, opts)
	opts = opts or {}
	if opts.name then
		part.Name = opts.name
	end
	if opts.color then
		local c = opts.color
		if typeof(c) == "Color3" then
			part.Color = c
		elseif type(c) == "table" then
			part.Color = Color3.fromRGB(c[1] or c.r or 0, c[2] or c.g or 0, c[3] or c.b or 0)
		end
	end
	if opts.material then
		local key = string.lower(tostring(opts.material))
		local resolved = MAT[key] or opts.material
		pcall(function()
			part.Material = Enum.Material[resolved]
		end)
	end
	if opts.transparency ~= nil then
		part.Transparency = opts.transparency
	end
	if opts.anchored ~= nil then
		part.Anchored = opts.anchored
	else
		part.Anchored = true
	end
	if opts.can_collide ~= nil then
		part.CanCollide = opts.can_collide
	end
	return part
end

local function resolveCenter(selfSize, opts)
	opts = opts or {}
	local sh = half(selfSize)

	if opts.at ~= nil then
		return vec3(opts.at)
	end

	local target = opts.of or opts.on_top
	local on = opts.on
	if opts.on_top and not opts.of then
		on = on or "top"
		target = opts.on_top
	end
	if opts.ground and not target and opts.at == nil then
		on = "ground"
	end

	local cx, cy, cz = 0, sh.Y, 0 -- default: grounded at origin

	if target then
		local tb = bounds(target)
		cx, cy, cz = tb.c.X, tb.c.Y, tb.c.Z
		on = on or "top"

		if on == "top" then
			cy = tb.max.Y + sh.Y
		elseif on == "bottom" then
			cy = tb.min.Y - sh.Y
		elseif on == "ground" then
			cy = sh.Y
		end

		if opts.corner then
			local k = CORNER_XZ[string.lower(opts.corner)]
			if not k then
				error("corner must be nw|ne|sw|se")
			end
			cx = tb.c.X + k.X * (tb.h.X - sh.X)
			cz = tb.c.Z + k.Z * (tb.h.Z - sh.Z)
		elseif opts.face then
			local f = FACE_XZ[string.lower(opts.face)]
			if not f then
				error("face must be north|south|east|west")
			end
			local gap = opts.gap or 0
			if f.X ~= 0 then
				cx = tb.c.X + f.X * (tb.h.X + sh.X + gap)
				cz = tb.c.Z
			else
				cz = tb.c.Z + f.Z * (tb.h.Z + sh.Z + gap)
				cx = tb.c.X
			end
		elseif opts.next_to then
			-- allow next_to as alias via face+gap already; keep target center xz if only on_top
		end
	elseif opts.ground then
		cy = sh.Y
		if opts.x then
			cx = opts.x
		end
		if opts.z then
			cz = opts.z
		end
	end

	-- next_to: of + face (explicit)
	if opts.next_to then
		local tb = bounds(opts.next_to)
		local dir = string.lower(opts.dir or opts.face or "north")
		local f = FACE_XZ[dir]
		if not f then
			error("next_to dir must be north|south|east|west")
		end
		local gap = opts.gap or 0
		if f.X ~= 0 then
			cx = tb.c.X + f.X * (tb.h.X + sh.X + gap)
			cz = tb.c.Z
		else
			cz = tb.c.Z + f.Z * (tb.h.Z + sh.Z + gap)
			cx = tb.c.X
		end
		if not opts.on and not opts.on_top then
			cy = sh.Y -- ground-aligned next_to by default
		end
	end

	local center = Vector3.new(cx, cy, cz)
	if opts.offset then
		center = center + vec3(opts.offset)
	end
	return center
end

function SpatialHelpers.place(part, opts)
	opts = opts or {}
	local size = part.Size
	local center = resolveCenter(size, opts)
	local cf = CFrame.new(center)
	if opts.rotation then
		local r = opts.rotation
		if typeof(r) == "CFrame" then
			cf = CFrame.new(center) * (r - r.Position)
		elseif type(r) == "table" then
			cf = CFrame.new(center) * CFrame.Angles(math.rad(r[1] or 0), math.rad(r[2] or 0), math.rad(r[3] or 0))
		end
	end
	part.CFrame = cf
	return part
end

local function parentOf(opts)
	return (opts and opts.parent) or workspace
end

function SpatialHelpers.block(size, opts)
	opts = opts or {}
	local s = vec3(size)
	local part = Instance.new("Part")
	part.Size = s
	part.TopSurface = Enum.SurfaceType.Smooth
	part.BottomSurface = Enum.SurfaceType.Smooth
	applyStyle(part, opts)
	if opts.ground == nil and opts.at == nil and opts.of == nil and opts.on_top == nil and opts.next_to == nil then
		opts = table.clone(opts)
		opts.ground = true
	end
	SpatialHelpers.place(part, opts)
	part.Parent = parentOf(opts)
	return part
end

function SpatialHelpers.cyl(diameter, height, opts)
	opts = opts or {}
	local d = diameter
	local h = height
	local part = Instance.new("Part")
	part.Shape = Enum.PartType.Cylinder
	-- Roblox cylinder axis is +X; size = (height_along_axis, diam, diam)
	-- We want vertical (Y), so size and rotate
	part.Size = Vector3.new(h, d, d)
	applyStyle(part, opts)
	if opts.ground == nil and opts.at == nil and opts.of == nil and opts.on_top == nil and opts.next_to == nil then
		opts = table.clone(opts)
		opts.ground = true
	end
	local placeOpts = opts
	-- place using visual upright size (d, h, d) for bounds
	local visualSize = Vector3.new(d, h, d)
	local center = resolveCenter(visualSize, placeOpts)
	local rot = CFrame.Angles(0, 0, math.rad(90)) -- X-axis cylinder -> vertical Y
	if opts.rotation then
		-- additional yaw etc.
		local r = opts.rotation
		if type(r) == "table" then
			rot = CFrame.Angles(math.rad(r[1] or 0), math.rad(r[2] or 0), math.rad(r[3] or 0)) * rot
		end
	end
	part.CFrame = CFrame.new(center) * rot
	part.Parent = parentOf(opts)
	return part
end

function SpatialHelpers.ball(diameter, opts)
	opts = opts or {}
	local d = diameter
	local part = Instance.new("Part")
	part.Shape = Enum.PartType.Ball
	part.Size = Vector3.new(d, d, d)
	applyStyle(part, opts)
	if opts.ground == nil and opts.at == nil and opts.of == nil and opts.on_top == nil and opts.next_to == nil then
		opts = table.clone(opts)
		opts.ground = true
	end
	SpatialHelpers.place(part, opts)
	part.Parent = parentOf(opts)
	return part
end

function SpatialHelpers.wedge(size, opts)
	opts = opts or {}
	local s = vec3(size)
	local part = Instance.new("WedgePart")
	part.Size = s
	applyStyle(part, opts)
	if opts.ground == nil and opts.at == nil and opts.of == nil and opts.on_top == nil and opts.next_to == nil then
		opts = table.clone(opts)
		opts.ground = true
	end
	SpatialHelpers.place(part, opts)
	part.Parent = parentOf(opts)
	return part
end

-- Back-compat thin wrappers (prefer factories)
function SpatialHelpers.ground(part)
	return SpatialHelpers.place(part, { ground = true, x = part.Position.X, z = part.Position.Z })
end

function SpatialHelpers.on_top(part, target)
	return SpatialHelpers.place(part, { of = target, on = "top" })
end

function SpatialHelpers.at_corner(part, target, corner)
	return SpatialHelpers.place(part, { of = target, on = "top", corner = corner })
end

function SpatialHelpers.on_face(part, target, face)
	return SpatialHelpers.place(part, { of = target, on = "top", face = face })
end

function SpatialHelpers.next_to(part, target, direction, gap)
	return SpatialHelpers.place(part, { next_to = target, dir = direction, gap = gap or 0, ground = true })
end

function SpatialHelpers.center_on(part, target)
	return SpatialHelpers.place(part, {
		at = Vector3.new(target.Position.X, part.Position.Y, target.Position.Z),
	})
end

function SpatialHelpers.name(part, name)
	part.Name = name
	return part
end

function SpatialHelpers.color(part, r, g, b)
	part.Color = Color3.fromRGB(r, g, b)
	return part
end

function SpatialHelpers.material(part, mat)
	return applyStyle(part, { material = mat })
end

function SpatialHelpers.distribute_around(partTemplate, target, count, radius)
	radius = radius or 5
	local results = {}
	local step = 360 / count
	for i = 1, count do
		local ang = math.rad((i - 1) * step)
		local x = target.Position.X + radius * math.cos(ang)
		local z = target.Position.Z + radius * math.sin(ang)
		local clone = partTemplate:Clone()
		clone.CFrame = CFrame.new(x, partTemplate.Position.Y, z)
		clone.Parent = workspace
		table.insert(results, clone)
	end
	return results
end

return SpatialHelpers
