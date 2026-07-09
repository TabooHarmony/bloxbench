--[[
    StructuralFixer — Post-hoc structural repair for Roblox builds

    Runs AFTER the model finishes building. Detects and fixes:
    - Floating parts: snaps down to nearest support surface or ground
    - Overlapping parts: separates vertically (pushes the upper one up)

    Usage:
        local Fixer = require(game.ReplicatedStorage.StructuralFixer)
        local report = Fixer.fix()
        -- report = { fixed = N, floating_fixed = N, overlaps_fixed = N, details = {...} }
]]

local StructuralFixer = {}

function StructuralFixer.fix()
    local parts = {}
    for _, obj in ipairs(workspace:GetChildren()) do
        if obj:IsA("BasePart") and obj.Name ~= "Baseplate" and not obj:IsA("Terrain") and obj.Name ~= "SpawnLocation" then
            table.insert(parts, obj)
        elseif obj:IsA("Folder") or obj:IsA("Model") or obj:IsA("Configuration") then
            for _, d in ipairs(obj:GetDescendants()) do
                if d:IsA("BasePart") and not d:IsA("Terrain") then
                    table.insert(parts, d)
                end
            end
        end
    end

    local report = {
        total_parts = #parts,
        fixed = 0,
        floating_fixed = 0,
        overlaps_fixed = 0,
        details = {},
    }

    -- Phase 1: Fix floating parts (snap down to support)
    -- Process from ground up: fix lowest floating parts first so they can support others
    table.sort(parts, function(a, b)
        return (a.Position.Y - a.Size.Y/2) < (b.Position.Y - b.Size.Y/2)
    end)

    for _, p in ipairs(parts) do
        local bottom = p.Position.Y - p.Size.Y/2
        if bottom <= 0.5 then
            -- already on ground, skip
        else
            -- find highest support surface beneath this part
            local bestSupportTop = 0  -- ground level
            for _, q in ipairs(parts) do
                if q ~= p then
                    local qtop = q.Position.Y + q.Size.Y/2
                    -- support must be below this part's bottom
                    if qtop <= bottom + 0.5 and qtop > bestSupportTop then
                        -- check X/Z overlap
                        local dx = math.abs(p.Position.X - q.Position.X)
                        local dz = math.abs(p.Position.Z - q.Position.Z)
                        if dx < (p.Size.X + q.Size.X)/2 and dz < (p.Size.Z + q.Size.Z)/2 then
                            bestSupportTop = qtop
                        end
                    end
                end
            end
            -- if best support is significantly below the part, snap it down
            if bestSupportTop < bottom - 1.0 then
                local newY = bestSupportTop + p.Size.Y/2
                p.Position = Vector3.new(p.Position.X, newY, p.Position.Z)
                report.fixed = report.fixed + 1
                report.floating_fixed = report.floating_fixed + 1
                table.insert(report.details, string.format(
                    "FLOAT FIX: %s dropped from Y=%.1f to Y=%.1f (settled on surface at Y=%.1f)",
                    p.Name, bottom, newY - p.Size.Y/2, bestSupportTop
                ))
            end
        end
    end

    -- Phase 2: Fix overlapping parts (push upper part up to sit on lower)
    for i, p in ipairs(parts) do
        for j = i+1, #parts do
            local q = parts[j]
            local dx = math.abs(p.Position.X - q.Position.X)
            local dy = math.abs(p.Position.Y - q.Position.Y)
            local dz = math.abs(p.Position.Z - q.Position.Z)
            if dx < (p.Size.X + q.Size.X)/2 - 0.1 and
               dy < (p.Size.Y + q.Size.Y)/2 - 0.1 and
               dz < (p.Size.Z + q.Size.Z)/2 - 0.1 then
                -- overlap detected. push the upper one up to sit on the lower
                local pCenter = p.Position.Y
                local qCenter = q.Position.Y
                local upper, lower
                if pCenter >= qCenter then
                    upper = p
                    lower = q
                else
                    upper = q
                    lower = p
                end
                local lowerTop = lower.Position.Y + lower.Size.Y/2
                local newUpperY = lowerTop + upper.Size.Y/2
                upper.Position = Vector3.new(upper.Position.X, newUpperY, upper.Position.Z)
                report.fixed = report.fixed + 1
                report.overlaps_fixed = report.overlaps_fixed + 1
                table.insert(report.details, string.format(
                    "OVERLAP FIX: %s pushed up to Y=%.1f to clear %s",
                    upper.Name, newUpperY - upper.Size.Y/2, lower.Name
                ))
            end
        end
    end

    -- Build summary string for logging
    report.summary = string.format(
        "Fixed %d issues: %d floating, %d overlapping (out of %d parts)",
        report.fixed, report.floating_fixed, report.overlaps_fixed, report.total_parts
    )

    return report
end

return StructuralFixer
