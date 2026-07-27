--!strict
-- @track gameplay
-- @screenshot type=gameplay angles=3 primary=front

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
local HttpService = game:GetService("HttpService")
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_GAMEPLAY_005_physics_salvage_room",
    prompt = {
        {
            {
                role = "user",
                content = [[Build a physics-based salvage room in Roblox. The player is in a room full of objects (crates, furniture, machines, junk) and has a tool to grab, throw, stack, or launch them.

The fun is in the physics. Objects should tumble, bounce, stack precariously, and collide satisfyingly. The player should experiment with "what happens if I throw this at that?"

Required interactions:
- Grab and move objects with a physics tool (gravity gun, telekinesis, magnet, or hands)
- Throw or launch objects and watch them collide
- Stack or arrange objects and see them topple

What you control:
- The grab tool and how it feels (weight, range, throw power)
- The room contents (variety of shapes, sizes, materials)
- Room size, lighting, and art direction
- Object physics (bounciness, friction, mass differences)
- Any targets, domino chains, or Rube Goldberg setups
- Sound design for grabs, impacts, breaking, and toppling

What matters to voters:
- Does grabbing and throwing feel tactile and responsive?
- Do objects behave in satisfying, physical ways?
- Is there variety in what you can interact with?
- Can you create your own chain reactions or experiments?

Do not build a full game. No puzzles with solutions, no scoring, no timer. One room, one tool, physics toys. Make playing with objects feel good.]],
                request_id = "vb_gameplay_005"
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
