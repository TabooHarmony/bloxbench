--!strict
-- @track vfx
-- @screenshot type=build angles=3 primary=front

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_VFX_001_arcane_explosion",
    prompt = {
        {
            {
                role = "user",
                content = [[Build an arcane explosion visual effect in Roblox. A burst of magical energy that expands outward from a central point: a bright core flash, expanding rings or shockwaves, particle sparks flying outward, and a lingering glow or smoke trail.

The effect should read as "magical explosion" in a single screenshot. Use ParticleEmitters, Beams, Lights, and transparent parts to create the effect. The color palette should suggest arcane energy: purple, blue, white, with bright highlights.

Set up the effect so it is visible in the Studio viewport. If it requires a script to trigger, include the script and make the effect visible in its default state (particles emitting, lights on). Build on the baseplate near the origin.]],
                request_id = "vb_vfx_001"
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
