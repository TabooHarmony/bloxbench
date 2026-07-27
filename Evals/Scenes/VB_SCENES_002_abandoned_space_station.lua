--!strict
-- @track scenes
-- @screenshot type=build angles=3 primary=front

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_SCENES_002_abandoned_space_station",
    prompt = {
        {
            {
                role = "user",
                content = [[Build an abandoned space station interior in Roblox. A small room or corridor that feels derelict: exposed panels, flickering or dead lights, scattered debris, a cracked viewport showing stars, and at least one piece of broken equipment.

The scene should tell a story of abandonment without any text. Use lighting to create mood: dark corners, one emergency light casting red or amber, the cold blue of starlight through the viewport. The space should feel enclosed and slightly unsettling.

Build the full scene on the baseplate. Make it walkable at Roblox character scale.]],
                request_id = "vb_scenes_002"
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
