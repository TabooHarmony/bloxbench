"""Extract concrete, project-local UI style signals from reference Lua files.

This is deliberately a conservative prototype. It reports observed tokens and
layout conventions; it does not infer a universal design system or score taste.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable


_INSTANCE_RE = re.compile(r'local\s+(\w+)\s*=\s*Instance\.new\("([^"]+)"\)')
_COLOR_RE = re.compile(
    r'(\w+)\.(BackgroundColor3|TextColor3|Color)\s*=\s*'
    r'Color3\.fromRGB\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)'
)
_FONT_RE = re.compile(r'(\w+)\.Font\s*=\s*Enum\.Font\.(\w+)')
_TEXT_SIZE_RE = re.compile(r'(\w+)\.TextSize\s*=\s*(\d+(?:\.\d+)?)')
_CORNER_RE = re.compile(r'(\w+)\.CornerRadius\s*=\s*UDim\.new\(\s*0\s*,\s*(\d+(?:\.\d+)?)\s*\)')
_STROKE_RE = re.compile(r'(\w+)\.Thickness\s*=\s*(\d+(?:\.\d+)?)')
_UDIM2_RE = re.compile(r'(\w+)\.(Size|Position)\s*=\s*UDim2\.new\(([^)]*)\)')
_TRANSPARENCY_RE = re.compile(
    r'(\w+)\.(BackgroundTransparency|TextTransparency)\s*=\s*(\d+(?:\.\d+)?)'
)
_PARENT_RE = re.compile(r'(\w+)\.Parent\s*=\s*(\w+)')
_NAME_RE = re.compile(r'(\w+)\.Name\s*=\s*"([^"]+)"')


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _number_tokens(raw: str) -> list[float]:
    values = []
    for token in raw.split(","):
        token = token.strip()
        if token:
            try:
                values.append(float(token))
            except ValueError:
                return []
    return values


def _key(value: float) -> str:
    return str(int(value)) if value.is_integer() else str(value)


def _increment(mapping: Counter, key: str, amount: int = 1) -> None:
    mapping[key] += amount


def _merge_counts(target: dict, source: Counter | dict) -> None:
    for key, value in source.items():
        target[key] = target.get(key, 0) + int(value)


def _merge_observed(target: dict, key: str, value: str, context: str) -> None:
    entry = target.setdefault(key, {"count": 0, "contexts": []})
    entry["count"] += 1
    if context not in entry["contexts"]:
        entry["contexts"].append(context)


def _extract_file(path: Path) -> dict:
    data = path.read_bytes()
    text = data.decode("utf-8")

    components = Counter()
    variables: dict[str, str] = {}
    for variable, class_name in _INSTANCE_RE.findall(text):
        variables[variable] = class_name
        components[class_name] += 1

    names = dict(_NAME_RE.findall(text))
    colors: dict = {}
    fonts = Counter()
    text_sizes = Counter()
    corners = Counter()
    strokes = Counter()
    transparencies = Counter()
    layout = Counter()

    for variable, property_name, r, g, b in _COLOR_RE.findall(text):
        color_key = f"{r},{g},{b}"
        context = f"{variables.get(variable, 'unknown')}.{property_name}"
        _merge_observed(colors, color_key, property_name, context)

    for variable, font in _FONT_RE.findall(text):
        _increment(fonts, font)

    for _, size in _TEXT_SIZE_RE.findall(text):
        _increment(text_sizes, size)

    for _, radius in _CORNER_RE.findall(text):
        _increment(corners, radius)

    for _, thickness in _STROKE_RE.findall(text):
        _increment(strokes, thickness)

    for _, property_name, value in _TRANSPARENCY_RE.findall(text):
        _increment(transparencies, f"{property_name}={value}")

    for variable, property_name, raw_values in _UDIM2_RE.findall(text):
        values = _number_tokens(raw_values)
        if len(values) != 4:
            continue
        x_scale, x_offset, y_scale, y_offset = values
        prefix = property_name.lower()
        if x_scale or y_scale:
            _increment(layout, f"{prefix}_uses_scale")
        if x_offset or y_offset:
            _increment(layout, f"{prefix}_uses_offset")
        if property_name == "Position" and x_scale == 0.5:
            _increment(layout, "horizontal_center_anchor")
        if property_name == "Position" and y_scale == 0.5:
            _increment(layout, "vertical_center_anchor")

    parent_edges = [
        {"child": child, "parent": parent, "child_class": variables.get(child), "parent_class": variables.get(parent)}
        for child, parent in _PARENT_RE.findall(text)
    ]

    return {
        "source": {
            "path": str(path),
            "sha256": _sha256(data),
        },
        "component_counts": dict(components),
        "colors": colors,
        "font_usage": dict(fonts),
        "text_sizes": dict(text_sizes),
        "corner_radii_px": dict(corners),
        "stroke_thickness_px": dict(strokes),
        "transparency_values": dict(transparencies),
        "layout_signals": dict(layout),
        "named_components": {
            variable: {"class": variables[variable], "name": name}
            for variable, name in names.items()
            if variable in variables
        },
        "parent_edges": parent_edges,
    }


def _merge_file_profile(profile: dict, extracted: dict) -> None:
    profile["sources"].append(extracted["source"])
    _merge_counts(profile["component_counts"], extracted["component_counts"])
    _merge_counts(profile["font_usage"], extracted["font_usage"])
    _merge_counts(profile["text_sizes"], extracted["text_sizes"])
    _merge_counts(profile["corner_radii_px"], extracted["corner_radii_px"])
    _merge_counts(profile["stroke_thickness_px"], extracted["stroke_thickness_px"])
    _merge_counts(profile["transparency_values"], extracted["transparency_values"])
    _merge_counts(profile["layout_signals"], extracted["layout_signals"])

    for color, observed in extracted["colors"].items():
        entry = profile["colors"].setdefault(color, {"count": 0, "contexts": []})
        entry["count"] += observed["count"]
        for context in observed["contexts"]:
            if context not in entry["contexts"]:
                entry["contexts"].append(context)

    profile["named_components"].extend(
        {
            **value,
            "variable": variable,
            "source": extracted["source"]["path"],
        }
        for variable, value in extracted["named_components"].items()
    )
    profile["parent_edges"].extend(
        {
            **edge,
            "source": extracted["source"]["path"],
        }
        for edge in extracted["parent_edges"]
    )


def extract_style_profile(paths: Iterable[str | Path]) -> dict:
    """Extract and merge concrete style observations from reference files."""
    profile = {
        "schema_version": "1",
        "sources": [],
        "component_counts": {},
        "colors": {},
        "font_usage": {},
        "text_sizes": {},
        "corner_radii_px": {},
        "stroke_thickness_px": {},
        "transparency_values": {},
        "layout_signals": {},
        "named_components": [],
        "parent_edges": [],
    }

    normalized = [Path(path) for path in paths]
    if not normalized:
        raise ValueError("at least one reference file is required")
    for path in normalized:
        if not path.is_file():
            raise FileNotFoundError(path)
        _merge_file_profile(profile, _extract_file(path))
    return profile


def _top_counts(values: dict, limit: int = 12) -> list[str]:
    return [key for key, _ in sorted(values.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def style_profile_prompt(profile: dict) -> str:
    """Render a compact context block for a construction agent."""
    colors = _top_counts({key: value["count"] for key, value in profile["colors"].items()})
    fonts = _top_counts(profile["font_usage"])
    sizes = _top_counts(profile["text_sizes"])
    radii = _top_counts(profile["corner_radii_px"])
    components = _top_counts(profile["component_counts"])

    lines = [
        "## reference-derived style signals",
        "these are local observations from known-good project references, not universal requirements.",
        "use them as a local prior only, preserve the task's intent, and do not copy blindly.",
        "",
        f"observed components: {', '.join(components) or 'none'}",
        f"observed colors (rgb): {', '.join(colors) or 'none'}",
        f"observed fonts: {', '.join(fonts) or 'none'}",
        f"observed text sizes: {', '.join(sizes) or 'none'}",
        f"observed corner radii (px): {', '.join(radii) or 'none'}",
        f"observed layout signals: {', '.join(_top_counts(profile['layout_signals'])) or 'none'}",
        "",
        "these observations do not prove responsiveness, accessibility, input support, or visual quality on their own.",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract project-local Roblox UI style observations")
    parser.add_argument("references", nargs="+", help="Reference Lua files")
    parser.add_argument("--output", "-o", help="Write the extracted JSON profile here")
    parser.add_argument("--prompt-output", help="Write the compact agent context here")
    args = parser.parse_args()

    profile = extract_style_profile(args.references)
    rendered = json.dumps(profile, indent=2, sort_keys=True)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    if args.prompt_output:
        Path(args.prompt_output).write_text(style_profile_prompt(profile) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
