from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.benchmark.fixture_contract import (
    FixtureContractError,
    discover_fixtures,
    parse_fixture,
    resolve_starter_place,
)


VALID = '''-- @fixture pilot.example_mechanism
-- @track mechanism
-- @semantic LeftSupport,RightSupport,Deck,DeckHinge,TopBeam,Winch,Crank,LeftCable,RightCable,ApproachPad,FarPad
-- @states lowered,halfway,raised,reset
-- @runtime mode=play
-- @evidence static=required video=optional trace=required reset=required review=human-pairwise
-- @screenshot type=mechanism angles=1 primary=hero
-- @judge_rubric focal="mechanism" relationships="cables"
local eval = {}
eval.scenario_name = "pilot.example_mechanism"
eval.place = "baseplate.rbxl"
eval.prompt = {
    {role = "user", content = [[Build a substantial connected mechanism spanning a visible gap, with two supports, a hinged deck, a top beam, a winch drum, a crank, paired cables, approach pads, and a traversable route. The deck must move around a stable hinge axis and the mechanism must expose deterministic lowered, halfway, raised, and reset states for parent-owned evidence capture.]]}
}
eval.setup = function() return true end
eval.cleanup = function() return true end
eval.check_scene = function() return {marker = "scene"} end
eval.check_game = function() return {marker = "game"} end
eval.run = function(state) return {state = state} end
return eval
'''


class FixtureContractTests(unittest.TestCase):
    def test_parse_extracts_contract_and_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "fixture.lua"
            path.write_text(VALID, encoding="utf-8")
            fixture = parse_fixture(path)
        self.assertEqual(fixture.fixture_id, "pilot.example_mechanism")
        self.assertEqual(fixture.track, "mechanism")
        self.assertEqual(fixture.states, ("lowered", "halfway", "raised", "reset"))
        self.assertEqual(fixture.runtime, "play")
        self.assertEqual(set(fixture.hooks), {"setup", "cleanup", "check_scene", "check_game", "run"})
        self.assertIn("connected mechanism", fixture.prompt)

    def test_parse_extracts_quoted_metadata_values(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "fixture.lua"
            source = VALID.replace('focal="mechanism"', 'focal="mechanism focal"').replace('relationships="cables"', 'relationships="cables and route"')
            path.write_text(source, encoding="utf-8")
            fixture = parse_fixture(path)
        self.assertEqual(fixture.rubric["focal"], "mechanism focal")
        self.assertEqual(fixture.rubric["relationships"], "cables and route")

    def test_discover_rejects_duplicate_fixture_ids(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            (root / "a.lua").write_text(VALID, encoding="utf-8")
            (root / "b.lua").write_text(VALID, encoding="utf-8")
            with self.assertRaisesRegex(FixtureContractError, "duplicate fixture_id"):
                discover_fixtures(root)

    def test_parse_rejects_missing_cleanup(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "fixture.lua"
            path.write_text(VALID.replace("eval.cleanup = function() return true end\n", ""), encoding="utf-8")
            with self.assertRaisesRegex(FixtureContractError, "cleanup"):
                parse_fixture(path)

    def test_parse_rejects_stateful_fixture_without_trace_or_reset(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "fixture.lua"
            source = VALID.replace("trace=required ", "").replace("reset=required ", "")
            path.write_text(source, encoding="utf-8")
            with self.assertRaisesRegex(FixtureContractError, "trace=required.*reset=required"):
                parse_fixture(path)

    def test_parse_accepts_future_tracks_and_repository_relative_starter_places(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "fixture.lua"
            source = (
                VALID
                .replace("@track mechanism", "@track vfx")
                .replace("static=required", "static=diagnostic")
                .replace("@screenshot type=mechanism", "@screenshot type=ui angles=1 primary=hero purpose=diagnostic")
                .replace('eval.place = "baseplate.rbxl"', 'eval.place = "starters/ui.rbxl"')
                .replace("-- @judge_rubric", "-- @knowledge profile=roblox-ui-v1\n-- @candidate root=PreviewRoot\n-- @provenance origin=real-world-atlas record=game-001 license=public\n-- @judge_rubric")
            )
            path.write_text(source, encoding="utf-8")
            fixture = parse_fixture(path)
        self.assertEqual(fixture.track, "vfx")
        self.assertEqual(fixture.screenshot_type, "ui")
        self.assertEqual(fixture.place, "starters/ui.rbxl")
        self.assertEqual(fixture.knowledge_profile, "roblox-ui-v1")
        self.assertEqual(fixture.candidate_root, "PreviewRoot")
        self.assertEqual(fixture.evidence["static"], "diagnostic")
        self.assertEqual(fixture.provenance["origin"], "real-world-atlas")
        self.assertEqual(fixture.provenance["record"], "game-001")

    def test_parse_accepts_play_fixture_without_video(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "fixture.lua"
            path.write_text(VALID, encoding="utf-8")
            fixture = parse_fixture(path)
        self.assertEqual(fixture.evidence["video"], "optional")

    def test_parse_accepts_presentation_only_fixture_without_screenshots(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "fixture.lua"
            source = VALID.replace("static=required", "static=not-applicable")
            source = source.replace("-- @screenshot type=mechanism angles=1 primary=hero\n", "")
            path.write_text(source, encoding="utf-8")
            fixture = parse_fixture(path)
        self.assertEqual(fixture.screenshot_angles, 0)
        self.assertEqual(fixture.screenshot_type, "")

    def test_resolves_repository_relative_and_legacy_starter_places(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            direct = root / "starters" / "ui.rbxl"
            direct.parent.mkdir(parents=True)
            direct.write_bytes(b"ui-place")
            legacy = root / "Places" / "baseplate.rbxl"
            legacy.parent.mkdir(parents=True)
            legacy.write_bytes(b"baseplate")
            self.assertEqual(resolve_starter_place(root, "starters/ui.rbxl"), direct)
            self.assertEqual(resolve_starter_place(root, "baseplate.rbxl"), legacy)

    def test_parse_rejects_unknown_screenshot_primary_angle(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "fixture.lua"
            path.write_text(VALID.replace("primary=hero", "primary=orbit"), encoding="utf-8")
            with self.assertRaisesRegex(FixtureContractError, "screenshot primary"):
                parse_fixture(path)

    def test_parse_rejects_non_human_review_declaration(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "fixture.lua"
            path.write_text(VALID.replace("review=human-pairwise", "review=automated"), encoding="utf-8")
            with self.assertRaisesRegex(FixtureContractError, "human-pairwise"):
                parse_fixture(path)


if __name__ == "__main__":
    unittest.main()
