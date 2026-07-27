--!strict
-- @track scenes
-- @screenshot type=build angles=3 primary=front

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_SCENES_001_night_market_alley",
    prompt = {
        {
            {
                role = "user",
                content = [[Build a night market alley scene in Roblox. A narrow walkable street lined with small vendor stalls on both sides. Cloth awnings, hanging lanterns or string lights, crates of goods, and a few signs.

The scene should feel like a place you could walk through. Stalls should have depth (counter, back wall, roof). Lighting should suggest evening: warm lantern glow against a dark sky. The alley should have a clear path from one end to the other.

Build the full scene on the baseplate. Make it walkable at Roblox character scale.]],
                request_id = "vb_scenes_001"
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
