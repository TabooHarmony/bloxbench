--!strict
-- @track props
-- @screenshot type=build angles=3 primary=front

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_PROPS_001_fantasy_sword",
    prompt = {
        {
            {
                role = "user",
                content = [[Build a fantasy sword as a Roblox model. It should look like a weapon from a dark fantasy game: a long blade with a fuller, a crossguard with slight curves, a wrapped grip, and a pommel.

The sword should read clearly as a sword from any angle. Use materials and colors that suggest metal and leather. The proportions should feel like a real weapon, not a cartoon toy.

Build it as a single Model with named parts. Anchor it. Center it near the origin so it is easy to inspect.]],
                request_id = "vb_props_001"
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
