"""
generate_report.py — BloxBench results report generator.

Takes a results.json from a BloxBench run and produces a detailed markdown report
with model profiles, per-eval breakdowns, and behavioral patterns.

Usage:
    python generate_report.py results/vanilla_0702_1200/results.json --output reports/model_report.md
    python generate_report.py results/a.json results/b.json --compare --output reports/comparison.md
"""

import argparse
import json
import sys
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime


def load_results(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.loads(f.read())


def fmt_ms(ms):
    if ms is None:
        return "N/A"
    if ms < 1000:
        return f"{ms}ms"
    s = ms / 1000
    if s < 60:
        return f"{s:.1f}s"
    m = s / 60
    return f"{m:.1f}m"


def fmt_score(score):
    if score is None:
        return "N/A"
    return f"{score:.1f}"


# ============================================================
# Single-run report
# ============================================================

def generate_single_report(data: dict) -> str:
    lines = []
    model_name = data.get("model", {}).get("name", "Unknown")
    config = data.get("config", {})
    summary = data.get("summary", {})
    evals = data.get("evals", [])
    ui_track = summary.get("ui_track")

    # Header
    lines.append(f"# BloxBench Report: {model_name}")
    lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Config: Pass@{config.get('pass_n', 1)}, Max rounds: {config.get('max_rounds', 25)}")
    if config.get("track"):
        lines.append(f"Track: {config['track']}")

    # Executive Summary
    lines.append("\n## Executive Summary\n")
    total = summary.get("total_evals", 0)
    passed = summary.get("passed", 0)
    gate_rate = summary.get("pass_rate", 0)
    
    judge_evals = summary.get("judge_evals", 0)
    lines.append(f"- **Structural gate pass rate**: {gate_rate}% ({passed}/{total})")
    
    if judge_evals and not ui_track:
        lines.append(f"- **Judge-scored evals**: {judge_evals}")
        lines.append(f"- **Avg judge overall**: {fmt_score(summary.get('avg_judge_overall'))}")
        lines.append(f"- **Avg correctness**: {fmt_score(summary.get('avg_judge_correctness'))}")
        lines.append(f"- **Avg layout**: {fmt_score(summary.get('avg_judge_layout'))}")
        lines.append(f"- **Avg aesthetics**: {fmt_score(summary.get('avg_judge_aesthetics'))}")
        lines.append(f"- **Avg completeness**: {fmt_score(summary.get('avg_judge_completeness'))}")
    elif not judge_evals:
        lines.append("- **Judge scoring**: not enabled or no evals passed gate")
    else:
        lines.append(f"- **UI visual judge-scored evals**: {judge_evals}")

    lines.append(f"- **Avg LLM calls**: {summary.get('avg_llm_calls', 0)}")
    lines.append(f"- **Avg tokens in**: {summary.get('avg_tokens_in', 0)}")
    lines.append(f"- **Avg tokens out**: {summary.get('avg_tokens_out', 0)}")
    lines.append(f"- **Avg tool calls**: {round(sum(e.get('tool_calls', 0) for e in evals) / max(1, total), 1)}")
    lines.append(f"- **Tool error rate**: {summary.get('tool_error_rate', 0)}%")
    lines.append(f"- **Avg rounds**: {round(sum(e.get('rounds_used', 0) for e in evals) / max(1, total), 1)}")
    lines.append(f"- **Avg edits**: {summary.get('avg_edit_count', 0)}")
    lines.append(f"- **Avg peak context**: {summary.get('avg_max_context_tokens', 0)} tokens")
    lines.append(f"- **Avg tool sequence length**: {summary.get('avg_tool_call_sequence_len', 0)}")
    lines.append(f"- **Avg created scripts**: {summary.get('avg_created_scripts', 0)}")
    lines.append(f"- **Avg LLM time**: {fmt_ms(summary.get('avg_time_llm', 0))}")
    lines.append(f"- **Avg screenshot time**: {fmt_ms(summary.get('avg_time_screenshot', 0))}")

    # Error breakdown
    err_bd = summary.get("error_breakdown", {})
    non_none = {k: v for k, v in err_bd.items() if k != "none"}
    if non_none:
        lines.append(f"- **Errors**: {non_none}")

    # Judge score profile (radar-style text)
    if judge_evals and not ui_track:
        lines.append("\n### Judge Score Profile\n")
        dims = ["correctness", "layout", "aesthetics", "completeness"]
        for dim in dims:
            val = summary.get(f"avg_judge_{dim}")
            if val is not None:
                bar = "█" * int(val) + "░" * (5 - int(val))
                lines.append(f"- {dim:15s} {bar} {val:.1f}/5")

    # Separate UI track summary
    if ui_track:
        lines.append("\n## UI Track\n")
        lines.append("Functional correctness remains the hard scene/game gate. Visual scoring is conditional on functional passes; unresolved visual evidence is reported separately.")
        lines.append(f"- **Functional pass rate**: {ui_track.get('functional_pass_rate')}% ({ui_track.get('functional_passed')}/{ui_track.get('functional_scored_evals')})")
        lines.append(f"- **Conditional visual pass rate**: {ui_track.get('conditional_visual_pass_rate', ui_track.get('visual_pass_rate'))}% ({ui_track.get('visual_passed')}/{ui_track.get('visual_scored_evals')})")
        lines.append(f"- **Visual evidence coverage**: {ui_track.get('visual_evidence_coverage')}% of functional passes")
        lines.append(f"- **Confirmed combined pass rate**: {ui_track.get('confirmed_combined_pass_rate', ui_track.get('combined_pass_rate'))}% ({ui_track.get('confirmed_combined_passed', ui_track.get('combined_passed'))}/{ui_track.get('confirmed_combined_scored_evals', ui_track.get('combined_scored_evals'))})")
        lines.append(f"- **Combined pass evidence bounds**: {ui_track.get('combined_pass_rate_lower_bound')}%–{ui_track.get('combined_pass_rate_upper_bound')}%")
        lines.append(f"- **Visual review required**: {ui_track.get('visual_review_required', 0)}")
        lines.append(f"- **Average visual score**: {fmt_score(ui_track.get('avg_visual_score'))}/5")
        dimensions = ui_track.get("avg_visual_dimensions", {})
        if dimensions:
            lines.append("\n### UI Visual Dimensions\n")
            for dimension, score in dimensions.items():
                lines.append(f"- **{dimension}**: {fmt_score(score)}/5")

    # Per-eval results
    lines.append("\n## Per-Eval Results\n")
    if ui_track:
        lines.append("| Eval | Functional | Visual | Hierarchy | Composition | Spacing | Typography | Contrast | State | Art direction |")
        lines.append("|------|------------|--------|----------|-------------|---------|------------|----------|-------|--------------|")
    else:
        lines.append("| Eval | Gate | Judge | Correct | Layout | Aesth | Compl | Rounds | Tokens In | Edits | Time |")
        lines.append("|------|------|-------|---------|--------|-------|-------|--------|-----------|-------|------|")

    for e in sorted(evals, key=lambda x: x.get("scenario", "")):
        scenario = e.get("scenario", "")
        gate = "✓" if e.get("passed") else "✗"
        js = e.get("judge_scores") or {}
        overall = e.get("judge_overall")
        if ui_track:
            visual = e.get("visual_score", overall)
            visual_status = fmt_score(visual) if visual is not None else "review"
            dimensions = [fmt_score(js.get(key)) if js.get(key) is not None else "—" for key in (
                "hierarchy", "composition", "spacing", "typography", "contrast", "state_clarity", "art_direction"
            )]
            lines.append("| " + " | ".join([scenario, gate, visual_status, *dimensions]) + " |")
            continue

        j_str = fmt_score(overall) if overall else "—"
        corr = fmt_score(js.get("correctness")) if js.get("correctness") else "—"
        layout = fmt_score(js.get("layout")) if js.get("layout") else "—"
        aesth = fmt_score(js.get("aesthetics")) if js.get("aesthetics") else "—"
        compl = fmt_score(js.get("completeness")) if js.get("completeness") else "—"
        rounds = e.get("rounds_used", 0)
        tok_in = e.get("total_tokens_in", 0)
        edits = e.get("edit_count", 0)
        time = fmt_ms(e.get("total_time_ms", 0))
        lines.append(f"| {scenario} | {gate} | {j_str} | {corr} | {layout} | {aesth} | {compl} | {rounds} | {tok_in:,} | {edits} | {time} |")

    # Behavioral patterns
    lines.append("\n## Behavioral Patterns\n")

    # Strategy: explore-first vs edit-blind
    explore_first = 0
    edit_blind = 0
    for e in evals:
        seq = e.get("tool_call_sequence", [])
        if not seq:
            continue
        # Check if first 3 calls include search_game_tree or script_read
        first_3 = seq[:3]
        if any("search" in t or "read" in t or "list" in t for t in first_3):
            explore_first += 1
        elif any("edit" in t or "execute" in t for t in first_3):
            edit_blind += 1
    
    lines.append(f"### Model Strategy\n")
    lines.append(f"- Explore-first (searched before editing): {explore_first}/{len(evals)} evals")
    lines.append(f"- Edit-blind (started editing immediately): {edit_blind}/{len(evals)} evals")

    # Efficiency: rounds vs judge score
    lines.append(f"\n### Efficiency\n")
    for e in evals:
        if e.get("judge_overall") and e.get("rounds_used"):
            seq_len = len(e.get("tool_call_sequence", []))
            lines.append(f"- {e['scenario']}: {e['rounds_used']} rounds, {seq_len} tool calls, judge={e['judge_overall']}/5, {fmt_ms(e.get('total_time_ms', 0))}")

    # Functional vs visual quality
    if ui_track:
        lines.append("\n### Functional vs Visual Quality\n")
        for e in evals:
            visual = e.get("visual_score")
            if visual is None:
                continue
            functional = "pass" if e.get("passed") else "fail"
            visual_label = "pass" if visual >= ui_track.get("visual_pass_threshold", 3.0) else "fail"
            lines.append(f"- {e['scenario']}: functional={functional}, visual={visual_label} ({visual:.1f}/5)")
    else:
        lines.append(f"\n### Code vs Visual Quality\n")
        for e in evals:
            js = e.get("judge_scores") or {}
            script_count = (e.get("created_scripts") or {}).get("_count", 0)
            if js and script_count:
                corr = js.get("correctness", 0)
                aesth = js.get("aesthetics", 0)
                gap = corr - aesth
                profile = ""
                if gap > 1:
                    profile = "functional but ugly"
                elif gap < -1:
                    profile = "pretty but broken"
                elif corr >= 4 and aesth >= 4:
                    profile = "well-rounded"
                lines.append(f"- {e['scenario']}: {script_count} scripts, correctness={corr}/5, aesthetics={aesth}/5 → {profile}")

    # Per-eval judge reasoning (if available)
    lines.append("\n## Judge Reasoning\n")
    for e in evals:
        reasoning = e.get("judge_reasoning")
        if reasoning:
            scenario = e.get("scenario", "")
            overall = e.get("judge_overall", "?")
            issues = e.get("judge_issues", [])
            lines.append(f"\n### {scenario} (overall: {overall}/5)\n")
            lines.append(f"**Reasoning**: {reasoning}")
            if issues:
                lines.append(f"\n**Issues**:")
                for issue in issues:
                    if isinstance(issue, str):
                        lines.append(f"- {issue}")

    # Screenshots reference
    lines.append("\n## Screenshots\n")
    for e in evals:
        ss_paths = e.get("screenshot_paths", [])
        if ss_paths:
            scenario = e.get("scenario", "")
            lines.append(f"\n### {scenario}\n")
            for i, p in enumerate(ss_paths):
                lines.append(f"- Angle {i}: `{p}`")

    return "\n".join(lines)


# ============================================================
# Multi-run comparison report
# ============================================================

def generate_comparison_report(all_data: list[dict], labels: list[str]) -> str:
    lines = []
    lines.append(f"# BloxBench Comparison Report")
    lines.append(f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Models: {', '.join(labels)}")

    # Summary table
    lines.append("\n## Summary Comparison\n")
    lines.append("| Metric | " + " | ".join(labels) + " |")
    lines.append("|--------|" + "|".join(["--------"] * len(labels)) + "|")
    ui_comparison = [data.get("summary", {}).get("ui_track") for data in all_data]

    metrics = [
        ("Gate pass rate", "pass_rate", "%"),
    ]
    if not any(ui_comparison):
        metrics.extend([
            ("Avg judge overall", "avg_judge_overall", "score"),
            ("Avg correctness", "avg_judge_correctness", "score"),
            ("Avg layout", "avg_judge_layout", "score"),
            ("Avg aesthetics", "avg_judge_aesthetics", "score"),
            ("Avg completeness", "avg_judge_completeness", "score"),
        ])
    metrics.extend([
        ("Avg LLM calls", "avg_llm_calls", "num"),
        ("Avg tokens in", "avg_tokens_in", "num"),
        ("Avg tokens out", "avg_tokens_out", "num"),
        ("Tool error rate", "tool_error_rate", "%"),
        ("Avg rounds", None, "num"),  # computed
        ("Avg edits", "avg_edit_count", "num"),
        ("Avg peak context", "avg_max_context_tokens", "num"),
        ("Avg tool sequence len", "avg_tool_call_sequence_len", "num"),
        ("Avg created scripts", "avg_created_scripts", "num"),
        ("Avg LLM time", "avg_time_llm", "ms"),
    ])

    for label, key, fmt in metrics:
        vals = []
        for data in all_data:
            s = data.get("summary", {})
            if key:
                v = s.get(key)
            else:
                # computed metrics
                evals = data.get("evals", [])
                total = len(evals)
                if label == "Avg rounds":
                    v = round(sum(e.get("rounds_used", 0) for e in evals) / max(1, total), 1) if total else 0
                else:
                    v = 0
            if v is None:
                vals.append("N/A")
            elif fmt == "%":
                vals.append(f"{v}%")
            elif fmt == "score":
                vals.append(f"{v:.1f}" if v else "N/A")
            elif fmt == "ms":
                vals.append(fmt_ms(v))
            else:
                vals.append(str(v))
        lines.append(f"| {label} | " + " | ".join(vals) + " |")

    if any(ui_comparison):
        lines.append("\n## UI Track Comparison\n")
        lines.append("| Metric | " + " | ".join(labels) + " |")
        lines.append("|--------|" + "|".join(["--------"] * len(labels)) + "|")
        for label, key in [
            ("Functional pass rate", "functional_pass_rate"),
            ("Conditional visual pass rate", "conditional_visual_pass_rate"),
            ("Visual evidence coverage", "visual_evidence_coverage"),
            ("Confirmed combined pass rate", "confirmed_combined_pass_rate"),
            ("Combined lower bound", "combined_pass_rate_lower_bound"),
            ("Combined upper bound", "combined_pass_rate_upper_bound"),
            ("Average visual score", "avg_visual_score"),
            ("Visual review required", "visual_review_required"),
        ]:
            vals = []
            for ui_summary in ui_comparison:
                value = ui_summary.get(key) if ui_summary else None
                if value is None:
                    vals.append("N/A")
                elif "rate" in key or "coverage" in key:
                    vals.append(f"{value}%")
                elif key == "avg_visual_score":
                    vals.append(f"{value:.1f}/5")
                else:
                    vals.append(str(value))
            lines.append(f"| {label} | " + " | ".join(vals) + " |")

    # Per-eval pairwise
    lines.append("\n## Per-Eval Comparison\n")
    
    # Build eval lookup
    eval_maps = []
    for data in all_data:
        emap = {e.get("scenario"): e for e in data.get("evals", [])}
        eval_maps.append(emap)
    
    # Get all scenario names
    all_scenarios = set()
    for em in eval_maps:
        all_scenarios.update(em.keys())
    
    lines.append("| Eval | " + " | ".join([f"{l} Gate" for l in labels]) + " | " + " | ".join([f"{l} Judge" for l in labels]) + " |")
    lines.append("|------|" + "|".join(["--------"] * len(labels) * 2) + "|")

    for scenario in sorted(all_scenarios):
        row = [scenario]
        # Gate columns
        for em in eval_maps:
            e = em.get(scenario)
            row.append("✓" if e and e.get("passed") else "✗")
        # Judge columns
        for em in eval_maps:
            e = em.get(scenario)
            if e and e.get("judge_overall"):
                row.append(f"{e['judge_overall']}/5")
            else:
                row.append("—")
        lines.append("| " + " | ".join(row) + " |")

    # Strategy comparison
    lines.append("\n## Strategy Comparison\n")
    for i, (data, label) in enumerate(zip(all_data, labels)):
        evals = data.get("evals", [])
        explore = 0
        blind = 0
        for e in evals:
            seq = e.get("tool_call_sequence", [])
            if not seq:
                continue
            first_3 = seq[:3]
            if any("search" in t or "read" in t or "list" in t for t in first_3):
                explore += 1
            elif any("edit" in t or "execute" in t for t in first_3):
                blind += 1
        lines.append(f"- **{label}**: explore-first={explore}, edit-blind={blind}, total evals={len(evals)}")

    # Time efficiency comparison
    lines.append("\n## Efficiency Comparison\n")
    lines.append("| Eval | " + " | ".join([f"{l} time" for l in labels]) + " | " + " | ".join([f"{l} rounds" for l in labels]) + " |")
    lines.append("|------|" + "|".join(["--------"] * len(labels) * 2) + "|")
    for scenario in sorted(all_scenarios):
        row = [scenario]
        for em in eval_maps:
            e = em.get(scenario)
            row.append(fmt_ms(e.get("total_time_ms", 0)) if e else "N/A")
        for em in eval_maps:
            e = em.get(scenario)
            row.append(str(e.get("rounds_used", 0)) if e else "N/A")
        lines.append("| " + " | ".join(row) + " |")

    return "\n".join(lines)


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Generate BloxBench results report")
    parser.add_argument("results", nargs="+", help="Path(s) to results.json file(s)")
    parser.add_argument("--output", "-o", required=True, help="Output markdown file path")
    parser.add_argument("--compare", action="store_true", help="Generate comparison report for multiple results")
    parser.add_argument("--label", "-l", nargs="+", help="Labels for comparison (defaults to model names)")
    args = parser.parse_args()

    all_data = []
    for path in args.results:
        data = load_results(path)
        all_data.append(data)

    if args.compare and len(all_data) > 1:
        labels = args.label or [d.get("model", {}).get("name", f"model_{i}") for i, d in enumerate(all_data)]
        report = generate_comparison_report(all_data, labels)
    else:
        report = generate_single_report(all_data[0])

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    print(f"Report written to {output_path} ({len(report)} chars)")


if __name__ == "__main__":
    main()
