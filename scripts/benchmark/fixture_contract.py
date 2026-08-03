from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


HOOKS = ("setup", "cleanup", "check_scene", "check_game", "run")
REQUIRED_COMMON_HOOKS = ("setup", "cleanup", "check_scene")
SCREENSHOT_ANGLE_NAMES = ("hero", "front", "side", "rear", "top")


class FixtureContractError(ValueError):
    """A fixture is not executable or does not declare the review contract."""


@dataclass(frozen=True)
class Fixture:
    path: Path
    source: str
    fixture_id: str
    scenario_name: str
    track: str
    place: str
    prompt: str
    hooks: tuple[str, ...]
    semantic_components: tuple[str, ...]
    states: tuple[str, ...]
    runtime: str
    screenshot_type: str
    screenshot_angles: int
    screenshot_primary: str
    evidence: dict[str, str]
    rubric: dict[str, str]

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.source.encode("utf-8")).hexdigest()

    @property
    def stateful(self) -> bool:
        return bool(self.states) or self.runtime == "play"


def _first(pattern: str, source: str, *, flags: int = 0) -> str | None:
    match = re.search(pattern, source, flags)
    return match.group(1) if match else None


def _prompt(source: str) -> str:
    patterns = (
        r"content\s*=\s*\[\[(.*?)\]\]",
        r"content\s*=\s*\"([^\"]+)\"",
        r"eval\.prompt\s*=\s*\[\[(.*?)\]\]",
        r"eval\.prompt\s*=\s*\"([^\"]+)\"",
    )
    for pattern in patterns:
        value = _first(pattern, source, flags=re.DOTALL)
        if value is not None:
            return value.strip()
    return ""


def _comment_value(name: str, source: str) -> str | None:
    return _first(rf"^\s*--\s*@{re.escape(name)}\s+(.+?)\s*$", source, flags=re.MULTILINE)


def _csv(value: str | None) -> tuple[str, ...]:
    if not value:
        return ()
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _key_values(value: str | None) -> dict[str, str]:
    if not value:
        return {}
    return {key: raw for key, raw in re.findall(r"([A-Za-z_][\w-]*)=([^\s]+)", value)}


def parse_fixture(path: str | Path) -> Fixture:
    fixture_path = Path(path)
    source = fixture_path.read_text(encoding="utf-8")
    scenario_name = _first(r"scenario_name\s*=\s*\"([^\"]+)\"", source)
    if not scenario_name:
        raise FixtureContractError(f"{fixture_path}: missing scenario_name")
    fixture_id = _first(r"^\s*--\s*@fixture\s+([A-Za-z0-9_.-]+)\s*$", source, flags=re.MULTILINE)
    if not fixture_id:
        raise FixtureContractError(f"{fixture_path}: missing @fixture declaration")
    track = _first(r"^\s*--\s*@track\s+([\w-]+)\s*$", source, flags=re.MULTILINE)
    place = _first(r"place\s*=\s*\"([^\"]+)\"", source)
    hooks = tuple(
        hook
        for hook in HOOKS
        if re.search(rf"eval\.{hook}\s*=\s*function\s*\(", source)
    )
    semantic_components = _csv(_comment_value("semantic", source))
    states = _csv(_comment_value("states", source))
    evidence = _key_values(_comment_value("evidence", source))
    runtime_values = _key_values(_comment_value("runtime", source))
    runtime = runtime_values.get("mode", "edit")
    screenshot = _key_values(_comment_value("screenshot", source))
    screenshot_type = screenshot.get("type", "")
    try:
        screenshot_angles = int(screenshot.get("angles", "1"))
    except ValueError as exc:
        raise FixtureContractError(f"{fixture_path}: screenshot angles must be an integer") from exc
    rubric = _key_values(_comment_value("judge_rubric", source))
    fixture = Fixture(
        path=fixture_path,
        source=source,
        fixture_id=fixture_id,
        scenario_name=scenario_name,
        track=track or "",
        place=place or "",
        prompt=_prompt(source),
        hooks=hooks,
        semantic_components=semantic_components,
        states=states,
        runtime=runtime,
        screenshot_type=screenshot_type,
        screenshot_angles=screenshot_angles,
        screenshot_primary=screenshot.get("primary", "hero"),
        evidence=evidence,
        rubric=rubric,
    )
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: Fixture) -> None:
    errors: list[str] = []
    if not fixture.track:
        errors.append("missing @track")
    if fixture.track not in {"mechanism", "scene", "gameplay", "control"}:
        errors.append("@track must be mechanism, scene, gameplay, or control")
    if fixture.place != "baseplate.rbxl":
        errors.append("place must be baseplate.rbxl")
    if len(fixture.prompt) < 200:
        errors.append("prompt is too short for a benchmark fixture")
    if fixture.scenario_name != fixture.fixture_id:
        errors.append("scenario_name must match @fixture")
    missing_hooks = [hook for hook in REQUIRED_COMMON_HOOKS if hook not in fixture.hooks]
    if missing_hooks:
        errors.append(f"missing required hooks: {', '.join(missing_hooks)}")
    if fixture.stateful and "check_game" not in fixture.hooks:
        errors.append("stateful fixture requires check_game")
    if fixture.states and "run" not in fixture.hooks:
        errors.append("fixture with @states requires run")
    if len(set(fixture.semantic_components)) != len(fixture.semantic_components):
        errors.append("@semantic contains duplicate component names")
    if not fixture.semantic_components:
        errors.append("missing @semantic declaration")
    if fixture.screenshot_type not in {"scene", "mechanism", "gameplay", "control"}:
        errors.append("@screenshot type must be scene, mechanism, gameplay, or control")
    if fixture.screenshot_angles < 1 or fixture.screenshot_angles > 4:
        errors.append("screenshot angles must be between 1 and 4")
    if fixture.screenshot_primary not in SCREENSHOT_ANGLE_NAMES:
        errors.append("screenshot primary must be hero, front, side, rear, or top")
    if fixture.evidence.get("review") != "human-pairwise":
        errors.append("@evidence must declare review=human-pairwise")
    if fixture.evidence.get("static") != "required":
        errors.append("@evidence must declare static=required")
    if fixture.stateful and fixture.evidence.get("trace") != "required":
        errors.append("stateful fixture must declare trace=required")
    if fixture.stateful and fixture.evidence.get("reset") != "required":
        errors.append("stateful fixture must declare reset=required")
    if fixture.evidence.get("video") not in {"optional", "required"}:
        errors.append("fixture must declare video=optional or video=required")
    if fixture.runtime not in {"edit", "play"}:
        errors.append("@runtime mode must be edit or play")
    if errors:
        raise FixtureContractError(f"{fixture.path}: " + "; ".join(errors))


def discover_fixtures(root: str | Path) -> list[Fixture]:
    paths = sorted(Path(root).rglob("*.lua"))
    fixtures = [parse_fixture(path) for path in paths]
    validate_fixture_set(fixtures)
    return fixtures


def validate_fixture_set(fixtures: Iterable[Fixture]) -> None:
    items = list(fixtures)
    errors: list[str] = []
    for field in ("fixture_id", "scenario_name"):
        seen: dict[str, Path] = {}
        for fixture in items:
            value = getattr(fixture, field)
            if value in seen:
                errors.append(f"duplicate {field} {value!r}: {seen[value]} and {fixture.path}")
            seen[value] = fixture.path
    if errors:
        raise FixtureContractError("; ".join(errors))
