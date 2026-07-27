--!strict
-- @track gameplay
-- @screenshot type=gameplay angles=3 primary=front

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
local HttpService = game:GetService("HttpService")
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_GAMEPLAY_001_ak47_shooting_range",
    prompt = {
        {
            {
                role = "user",
                content = [[Build a playable AK-47 shooting range in Roblox. The player spawns in front of a firing lane with targets downrange. They can pick up the AK-47, aim, fire, and see immediate feedback on every shot.

The experience must deliver a satisfying shooting loop within the first 3 shots. A voter should understand the controls instantly, interact for under two minutes, and want to try again to compare feel against another model's range.

Required interactions:
- Pick up or equip the AK-47
- Fire (hip and aimed/ADS)
- See and hear hit feedback on targets
- Reload

What you control:
- The gun's sound, recoil character, and feel
- Target types, layout, and how they react to hits
- The range environment and art direction
- Any scoring, streaks, or customization you think makes the loop more engaging
- Camera behavior, viewmodel animation, muzzle flash, shell casings

What matters to voters:
- Does the first shot feel punchy and responsive?
- Does the gun feel alive (recoil recovery, sway, ADS transition)?
- Do targets react satisfyingly?
- Is there a reason to keep shooting for 30 more seconds?

Do not build a full game. No progression, economy, lobby, matchmaking, or multiple weapons. One gun, one range, one loop. Make it feel good.]],
                request_id = "vb_gameplay_001"
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

-- No automated gate. Human pairwise evaluation is the judge.
eval.check_scene = function()
end

eval.check_game = function()
end

return eval
