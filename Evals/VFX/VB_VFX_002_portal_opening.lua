--!strict
-- @track vfx
-- @screenshot type=build angles=3 primary=front

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_VFX_002_portal_opening",
    prompt = {
        {
            {
                role = "user",
                content = [[Build a portal opening visual effect in Roblox. A swirling gateway that appears in mid-air: a rotating ring or frame, an inner swirl of energy or distortion, particles being pulled inward or spiraling, and a glow that lights the surrounding area.

The effect should read as "a doorway to another place" in a single screenshot. Use ParticleEmitters, Beams, transparent parts with rotation, and PointLights. The color palette is your choice, but it should feel otherworldly.

Set up the effect so it is visible in the Studio viewport. If it requires a script to animate, include the script and make the effect visible in its default state. Build on the baseplate near the origin.]],
                request_id = "vb_vfx_002"
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
