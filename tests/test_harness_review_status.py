import unittest

from harness import EvalMetrics, aggregate_results


class ReviewStatusTests(unittest.TestCase):
    def test_one_passed_scored_result(self):
        summary = aggregate_results([EvalMetrics(passed=True)])
        self.assertEqual(summary["passed"], 1)
        self.assertEqual(summary["review_required"], 0)
        self.assertEqual(summary["scored_evals"], 1)
        self.assertEqual(summary["pass_rate"], 100.0)

    def test_one_failed_scored_result(self):
        summary = aggregate_results([EvalMetrics(passed=False)])
        self.assertEqual(summary["passed"], 0)
        self.assertEqual(summary["review_required"], 0)
        self.assertEqual(summary["scored_evals"], 1)
        self.assertEqual(summary["pass_rate"], 0.0)

    def test_one_unjudged_result(self):
        summary = aggregate_results([EvalMetrics(review_required=True)])
        self.assertEqual(summary["passed"], 0)
        self.assertEqual(summary["review_required"], 1)
        self.assertEqual(summary["scored_evals"], 0)
        self.assertIsNone(summary["pass_rate"])

    def test_passed_plus_unjudged_result(self):
        summary = aggregate_results([EvalMetrics(passed=True), EvalMetrics(review_required=True)])
        self.assertEqual(summary["passed"], 1)
        self.assertEqual(summary["review_required"], 1)
        self.assertEqual(summary["scored_evals"], 1)
        self.assertEqual(summary["pass_rate"], 100.0)


if __name__ == "__main__":
    unittest.main()
