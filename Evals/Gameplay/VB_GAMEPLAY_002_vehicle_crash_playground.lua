--!strict
-- @track gameplay
-- @screenshot type=gameplay angles=3 primary=front

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
local HttpService = game:GetService("HttpService")
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_GAMEPLAY_002_vehicle_crash_playground",
    prompt = {
        {
            {
                role = "user",
                content = [[Build a vehicle crash playground in Roblox. The player spawns near a ramp or launch point with a vehicle. They can drive, hit ramps, crash into destructible structures, and watch the wreckage fly.

The experience must be fun within the first 10 seconds. A voter should immediately understand "drive fast, hit things, watch stuff break" without any tutorial.

Required interactions:
- Enter and drive a vehicle
- Hit something and see it break or fly apart
- Reset or get a new vehicle easily

What you control:
- The vehicle type, handling, and speed feel
- What gets destroyed and how (buildings, walls, ramps, stacks of objects)
- The environment layout and art direction
- Camera behavior during crashes
- Any scoring, slow-motion, or replay moments you think add excitement
- Sound design for impacts, engines, and destruction

What matters to voters:
- Does driving feel responsive and fun immediately?
- Are crashes satisfying (parts flying, sound impact, camera shake)?
- Is there variety in what you can hit?
- Can you reset and go again in under 5 seconds?

Do not build a full game. No progression, garage, multiplayer lobby, or mission structure. One vehicle, one playground, one loop of drive-crash-reset. Make it feel good.]],
                request_id = "vb_gameplay_002"
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
