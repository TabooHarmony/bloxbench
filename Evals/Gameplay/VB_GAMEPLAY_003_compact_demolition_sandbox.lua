--!strict
-- @track gameplay
-- @screenshot type=gameplay angles=3 primary=front

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
local HttpService = game:GetService("HttpService")
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_GAMEPLAY_003_compact_demolition_sandbox",
    prompt = {
        {
            {
                role = "user",
                content = [[Build a compact demolition sandbox in Roblox. The player spawns in a small arena with a tool or weapon that can destroy structures. There are buildings, towers, or stacked objects waiting to be demolished.

The player should feel powerful immediately. One swing, one shot, or one explosion should send parts flying. The destruction should be physical and visible, not just a disappearing act.

Required interactions:
- Use a demolition tool (hammer, explosive, wrecking ball, or similar)
- Destroy at least one structure and see physical debris
- Get more targets or reset the scene

What you control:
- The demolition tool and how it feels to use
- What structures exist and how they break apart
- The arena size, lighting, and art direction
- Debris behavior (bounce, scatter, pile up)
- Sound design for impacts and crumbling
- Any combo or chain-reaction mechanics

What matters to voters:
- Does the first hit feel impactful?
- Is the destruction physical and satisfying (parts flying, not just vanishing)?
- Is there enough to destroy that you want to keep going?
- Does the tool feel weighty and responsive?

Do not build a full game. No levels, story, or progression. One arena, one tool, things to break. Make destruction feel good.]],
                request_id = "vb_gameplay_003"
            }
        }
    },
    place = "baseplate.rbxl"
}

eval.setup = function()
    game:GetService("Selection"):Set({})
end

eval.reference = function()
end

eval.check_scene = function()
end

eval.check_game = function()
end

return eval
