--!strict
-- @track scenes
-- @screenshot type=build angles=3 primary=front

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_SCENES_003_clifftop_shrine",
    prompt = {
        {
            {
                role = "user",
                content = [[Build a clifftop shrine scene in Roblox. A small stone platform on the edge of a cliff, with a torii gate or simple arch, a few stone lanterns, and a path of stepping stones leading to it. Below the cliff, suggest a valley or ocean with terrain or a large plane.

The scene should feel serene and elevated. The shrine is the focal point. Use natural materials: stone, wood, moss. The lighting should suggest golden hour or early morning. The cliff edge should feel like a real drop.

Build the full scene on the baseplate. Make it walkable at Roblox character scale.]],
                request_id = "vb_scenes_003"
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
