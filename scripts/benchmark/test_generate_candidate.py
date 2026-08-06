from __future__ import annotations

import importlib.util
import unittest
from dataclasses import replace
from pathlib import Path

from scripts.benchmark.fixture_contract import parse_fixture

HERE = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location(
    "generate_candidate_under_test", HERE / "generate_candidate.py"
)
assert SPEC and SPEC.loader
GEN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GEN)


class LuauSyntaxGateTests(unittest.TestCase):
    def test_valid_source_returns_no_errors(self) -> None:
        src = """local module = {}\nlocal p = Instance.new("Part")\np.Size = Vector3.new(1, 1, 1)\nreturn module\n"""
        self.assertEqual(GEN.luau_syntax_errors(src), [])

    def test_unterminated_long_bracket_is_detected(self) -> None:
        src = 'local s = [[\nfunction f()\nreturn 1\nend\n'
        errors = GEN.luau_syntax_errors(src)
        self.assertTrue(errors, "unterminated [[ should be a syntax error")

    def test_invalid_expression_is_detected(self) -> None:
        src = "local x = if for end\n"
        errors = GEN.luau_syntax_errors(src)
        self.assertTrue(errors, "garbage expression should be a syntax error")

    def test_empty_source_is_valid(self) -> None:
        self.assertEqual(GEN.luau_syntax_errors(""), [])

    def test_active_knowledge_profile_is_versioned_and_capability_neutral(self) -> None:
        knowledge = GEN.load_knowledge_profile("roblox-core-v1")
        self.assertIn("ROBLOX CORE KNOWLEDGE PROFILE v1", knowledge)
        self.assertIn("does not prohibit UI", knowledge)
        self.assertNotIn("Avoid: Terrain", knowledge)

    def test_system_prompt_hash_context_includes_knowledge_profile(self) -> None:
        prompt = GEN.build_system_prompt("roblox-core-v1")
        self.assertIn("ROBLOX CORE KNOWLEDGE PROFILE v1", prompt)
        self.assertIn("does not prohibit UI", prompt)

    def test_prompt_uses_declared_candidate_root(self) -> None:
        fixture = parse_fixture(HERE.parents[1] / "Evals" / "Scenes" / "VB_SCENE_001_waterfall_landmark.lua")
        fixture = replace(fixture, candidate_root="PreviewRoot")
        prompt = GEN.make_prompt(fixture)
        self.assertIn("named `PreviewRoot`", prompt)


if __name__ == "__main__":
    unittest.main()
