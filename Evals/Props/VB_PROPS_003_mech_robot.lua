--!strict
-- @track props
-- @screenshot type=build angles=3 primary=front

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_PROPS_003_mech_robot",
    prompt = {
        {
            {
                role = "user",
                content = [[Build a small mech robot as a Roblox model. Think of a cockpit-sized walking machine: two legs with visible joints, a torso with a cockpit hatch, two arms (one can be a weapon), and a head with a sensor eye.

The mech should look like it could walk. Joints should read as mechanical, not organic. Use materials that suggest metal, hydraulics, and armor plating. The silhouette should be recognizable as a bipedal robot from the front and side.

Build it as a single Model with named parts. Anchor it. Center it near the origin.]],
                request_id = "vb_props_003"
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
