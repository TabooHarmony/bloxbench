--!strict
-- @track props
-- @screenshot type=build angles=3 primary=front

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_PROPS_002_street_food_cart",
    prompt = {
        {
            {
                role = "user",
                content = [[Build a street food cart as a Roblox model. Think of a hot dog or taco cart you would see on a city sidewalk: a rectangular body on wheels, a flat cooking surface, a small awning or umbrella, and a handle for pushing.

Add small details that sell the fantasy: a condiment tray, a menu board, a propane tank, maybe steam or a small light. The cart should look functional, like someone actually cooks on it.

Build it as a single Model with named parts. Anchor it. Center it near the origin.]],
                request_id = "vb_props_002"
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
