--!strict
-- @track gameplay
-- @screenshot type=gameplay angles=3 primary=front

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
local HttpService = game:GetService("HttpService")
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_GAMEPLAY_004_momentum_swing_district",
    prompt = {
        {
            {
                role = "user",
                content = [[Build a momentum-based swinging experience in Roblox. The player can grapple, swing, or slingshot between anchor points across a district of buildings, towers, or floating platforms.

The core fantasy is speed and flow. The player should feel like they are building momentum, chaining swings, and covering distance fast. Missing a swing should be recoverable, not punishing.

Required interactions:
- Attach a grapple or swing to an anchor point
- Build and maintain momentum across multiple swings
- Land or recover after a missed swing

What you control:
- The swing mechanic (grapple hook, web, rope, vine, or similar)
- The district layout (building heights, gaps, anchor placement)
- Camera behavior during swings (FOV changes, speed lines, tilt)
- The art direction and environment theme
- Any speed boost, combo, or style mechanics
- Sound design for whoosh, attach, release, and landing

What matters to voters:
- Does the first swing feel exhilarating?
- Can you chain 3+ swings without stopping?
- Does speed build naturally and feel rewarding?
- Is the camera work exciting without being nauseating?

Do not build a full game. No missions, collectibles, enemies, or leaderboard. One district, one movement mechanic, pure flow. Make swinging feel amazing.]],
                request_id = "vb_gameplay_004"
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
