--!strict
-- @track vfx
-- @screenshot type=build angles=3 primary=front

local LoadedCode = game:FindFirstChild("LoadedCode")
assert(LoadedCode, "Failed to find LoadedCode")

local types = require(LoadedCode.EvalUtils.types)
type BaseEval = types.BaseEval

local eval: BaseEval = {
    scenario_name = "VB_VFX_003_lightning_storm",
    prompt = {
        {
            {
                role = "user",
                content = [[Build a lightning storm visual effect in Roblox. A small diorama: a dark ground plane, a few simple structures or rocks, and lightning bolts striking from above. Bolts should branch, flash brightly, and cast sharp shadows or light on the ground.

The effect should read as "violent electrical storm" in a single screenshot. Use Beams or thin bright parts for bolts, ParticleEmitters for rain or sparks, and brief intense PointLights or SpotLights for the flash. The sky or background should be dark.

Set up the effect so it is visible in the Studio viewport. If it requires a script to trigger strikes, include the script and make at least one bolt visible in the default state. Build on the baseplate near the origin.]],
                request_id = "vb_vfx_003"
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
