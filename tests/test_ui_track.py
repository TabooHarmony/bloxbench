import asyncio
import struct
import tempfile
import unittest
from pathlib import Path

from harness import EvalMetrics, parse_eval
from judge import VisualJudge, validate_score_result
from ui_track import aggregate_ui_results


class UiTrackTests(unittest.TestCase):
    def test_parse_eval_reads_ui_track_and_visual_rubric(self):
        source = '''
-- @track ui
-- @ui_visual_rubric hierarchy="clear focal hierarchy" composition="balanced composition"
-- @screenshot type=ui angles=1
local eval = {
    scenario_name = "VB_UI_test",
    prompt = {{content = [[Build a popup.]]}},
    place = "baseplate.rbxl"
}
'''
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw) / "test.lua"
            path.write_text(source, encoding="utf-8")
            parsed = parse_eval(str(path))

        self.assertEqual(parsed.track, "ui")
        self.assertEqual(parsed.ui_visual_rubric["hierarchy"], "clear focal hierarchy")
        self.assertEqual(parsed.ui_visual_rubric["composition"], "balanced composition")

    def test_ui_aggregation_separates_functional_and_visual_scores(self):
        results = [
            EvalMetrics(
                scenario="good",
                passed=True,
                judge_overall=4,
                judge_scores={"hierarchy": 4},
                visual_passed=True,
                visual_score=4,
            ),
            EvalMetrics(
                scenario="functional_only",
                passed=True,
            ),
            EvalMetrics(
                scenario="bad",
                passed=False,
                judge_overall=2,
                judge_scores={"hierarchy": 2},
                visual_passed=False,
                visual_score=2,
            ),
            EvalMetrics(scenario="review", review_required=True),
        ]

        summary = aggregate_ui_results(results)

        self.assertEqual(summary["functional_scored_evals"], 3)
        self.assertEqual(summary["functional_passed"], 2)
        self.assertEqual(summary["functional_pass_rate"], 66.67)
        self.assertEqual(summary["visual_scored_evals"], 1)
        self.assertEqual(summary["visual_passed"], 1)
        self.assertEqual(summary["conditional_visual_pass_rate"], 100.0)
        self.assertEqual(summary["visual_evidence_coverage"], 50.0)
        self.assertEqual(summary["visual_review_required"], 1)
        self.assertEqual(summary["confirmed_combined_passed"], 1)
        self.assertEqual(summary["confirmed_combined_pass_rate"], 33.33)
        self.assertEqual(summary["combined_pass_rate_lower_bound"], 33.33)
        self.assertEqual(summary["combined_pass_rate_upper_bound"], 66.67)
        self.assertEqual(summary["combined_pass_rate"], 33.33)

    def test_ui_aggregation_marks_missing_visual_judges_for_review(self):
        summary = aggregate_ui_results([EvalMetrics(passed=True)])

        self.assertEqual(summary["functional_pass_rate"], 100.0)
        self.assertEqual(summary["visual_scored_evals"], 0)
        self.assertIsNone(summary["visual_pass_rate"])
        self.assertEqual(summary["visual_review_required"], 1)
        self.assertEqual(summary["combined_pass_rate"], 0.0)
        self.assertEqual(summary["combined_pass_rate_lower_bound"], 0.0)
        self.assertEqual(summary["combined_pass_rate_upper_bound"], 100.0)


    def test_visual_judge_prompt_uses_ui_dimensions(self):
        judge = VisualJudge("model", "http://example.test", "key")
        messages = judge._build_score_messages(
            task_prompt="Build a popup.",
            rubric={"hierarchy": "clear focal hierarchy", "spacing": "consistent spacing"},
            screenshots=[],
        )

        instruction = messages[0]["content"][0]["text"]
        self.assertIn('"hierarchy": N', instruction)
        self.assertIn('"spacing": N', instruction)
        self.assertNotIn('"correctness": N', instruction)


    def test_judge_validation_rejects_missing_or_out_of_range_scores(self):
        rubric = {"hierarchy": "clear", "spacing": "consistent"}
        base = {
            "scores": {"hierarchy": 4, "spacing": 3},
            "overall": 4,
            "reasoning": "clear",
            "issues": [],
        }
        self.assertEqual(validate_score_result(base, rubric), base)

        with self.assertRaises(ValueError):
            validate_score_result({**base, "scores": {"hierarchy": 4}}, rubric)
        with self.assertRaises(ValueError):
            validate_score_result({**base, "scores": {"hierarchy": 6, "spacing": 3}}, rubric)
        with self.assertRaises(ValueError):
            validate_score_result({**base, "scores": {"hierarchy": 4.5, "spacing": 3}}, rubric)


    def test_judge_score_records_validated_provenance(self):
        judge = VisualJudge("model", "http://example.test", "key")
        rubric = {"hierarchy": "clear"}
        response = {
            "scores": {"hierarchy": 4},
            "overall": 4,
            "reasoning": "clear",
            "issues": [],
        }

        async def fake_call(messages):
            judge.last_attempt_count = 2
            return dict(response)

        judge._call_vision_api = fake_call
        with tempfile.TemporaryDirectory() as raw:
            screenshot = Path(raw) / "shot.png"
            screenshot.write_bytes(
                b"\x89PNG\r\n\x1a\n" + b"\x00" * 8 + struct.pack(">II", 320, 180)
            )
            result = asyncio.run(
                judge.score("Build a popup.", rubric, [str(screenshot)], "structure")
            )

        self.assertEqual(result["_provenance"]["validation_status"], "valid")
        self.assertEqual(result["_provenance"]["judge_attempt_count"], 2)
        self.assertEqual(result["_provenance"]["screenshots"][0]["dimensions"], [320, 180])
        self.assertEqual(result["_provenance"]["structure_dump_sha256"] is not None, True)


    def test_ui_aggregation_does_not_promote_generic_judge_fields(self):
        summary = aggregate_ui_results([
            EvalMetrics(
                passed=True,
                judge_overall=5,
                judge_scores={"hierarchy": 1},
            )
        ])

        self.assertEqual(summary["visual_scored_evals"], 0)
        self.assertEqual(summary["visual_review_required"], 1)
        self.assertIsNone(summary["conditional_visual_pass_rate"])


if __name__ == "__main__":
    unittest.main()
