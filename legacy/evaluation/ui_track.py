"""Scoring helpers for the separate Roblox UI visual track."""

from __future__ import annotations

from collections.abc import Iterable
from numbers import Real

UI_TRACK_NAME = "ui"
UI_TRACK_VERSION = "1"
UI_VISUAL_PASS_THRESHOLD = 3.0

DEFAULT_UI_VISUAL_RUBRIC = {
    "hierarchy": "clear visual hierarchy with an obvious focal point and readable grouping",
    "composition": "balanced composition that uses the requested screen area without awkward dead space",
    "spacing": "consistent padding, gaps, alignment, and sizing relationships",
    "typography": "legible text with intentional scale, weight, wrapping, and alignment",
    "contrast": "sufficient contrast and clearly distinguishable controls, surfaces, and states",
    "state_clarity": "requested states and affordances are visually obvious, including active, disabled, or progress states",
    "art_direction": "intentional visual direction with coherent color, shape, and surface treatment rather than default primitives",
}


def default_ui_visual_rubric() -> dict[str, str]:
    """Return a fresh copy so callers cannot mutate the shared rubric."""
    return dict(DEFAULT_UI_VISUAL_RUBRIC)


def _value(result, key: str, default=None):
    if isinstance(result, dict):
        return result.get(key, default)
    return getattr(result, key, default)


def _is_review_required(result) -> bool:
    return bool(_value(result, "review_required", False))


def _is_functionally_passing(result) -> bool:
    return not _is_review_required(result) and bool(_value(result, "passed", False))


def _visual_score(result) -> float | None:
    explicit = _value(result, "visual_score")
    if isinstance(explicit, Real):
        return float(explicit)
    return None


def aggregate_ui_results(
    results: Iterable,
    visual_pass_threshold: float = UI_VISUAL_PASS_THRESHOLD,
) -> dict:
    """Separate functional, conditional visual, and confirmed combined outcomes.

    Visual judging is currently conditional on a functional pass. Therefore the
    visual rate is not an end-to-end rate. Functional passes without a visual
    score remain unresolved and produce an evidence interval for combined rate.
    """
    items = list(results)
    functional_scored = [item for item in items if not _is_review_required(item)]
    functional_passed = [item for item in functional_scored if bool(_value(item, "passed", False))]

    scored_visual = []
    for item in functional_passed:
        score = _visual_score(item)
        if score is not None:
            scored_visual.append((item, score))

    visual_passed = [item for item, score in scored_visual if score >= visual_pass_threshold]
    visual_review_required = len(functional_passed) - len(scored_visual)

    total_determinate = len(functional_scored)
    functional_pass_count = len(functional_passed)
    visual_pass_count = len(visual_passed)

    def rate(numerator: int, denominator: int):
        return round(numerator / denominator * 100, 2) if denominator else None

    conditional_visual_pass_rate = rate(visual_pass_count, len(scored_visual))
    visual_evidence_coverage = rate(len(scored_visual), functional_pass_count)
    confirmed_combined_pass_rate = rate(visual_pass_count, total_determinate)
    combined_upper_bound = rate(visual_pass_count + visual_review_required, total_determinate)

    dimension_totals: dict[str, list[float]] = {}
    for item, _ in scored_visual:
        scores = _value(item, "judge_scores") or {}
        for dimension, value in scores.items():
            if isinstance(value, Real):
                dimension_totals.setdefault(dimension, []).append(float(value))

    return {
        "track": UI_TRACK_NAME,
        "version": UI_TRACK_VERSION,
        "visual_pass_threshold": visual_pass_threshold,
        "functional_scored_evals": total_determinate,
        "functional_passed": functional_pass_count,
        "functional_failed": total_determinate - functional_pass_count,
        "functional_pass_rate": rate(functional_pass_count, total_determinate),
        "visual_scored_evals": len(scored_visual),
        "visual_passed": visual_pass_count,
        "conditional_visual_pass_rate": conditional_visual_pass_rate,
        # Backward-compatible alias. New consumers should use the explicit name.
        "visual_pass_rate": conditional_visual_pass_rate,
        "visual_evidence_coverage": visual_evidence_coverage,
        "visual_review_required": visual_review_required,
        "confirmed_combined_scored_evals": total_determinate,
        "confirmed_combined_passed": visual_pass_count,
        "confirmed_combined_pass_rate": confirmed_combined_pass_rate,
        "combined_pass_rate_lower_bound": confirmed_combined_pass_rate,
        "combined_pass_rate_upper_bound": combined_upper_bound,
        # This field now means confirmed end-to-end rate, not conditional visual rate.
        "combined_scored_evals": total_determinate,
        "combined_passed": visual_pass_count,
        "combined_pass_rate": confirmed_combined_pass_rate,
        "avg_visual_score": round(sum(score for _, score in scored_visual) / len(scored_visual), 2)
        if scored_visual
        else None,
        "avg_visual_dimensions": {
            dimension: round(sum(values) / len(values), 2)
            for dimension, values in sorted(dimension_totals.items())
        },
    }
