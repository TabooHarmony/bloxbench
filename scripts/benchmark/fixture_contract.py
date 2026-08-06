from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


HOOKS = ("setup", "cleanup", "check_scene", "check_game", "run")
REQUIRED_COMMON_HOOKS = ("setup", "cleanup", "check_scene")
SCREENSHOT_ANGLE_NAMES = ("hero", "front", "side", "rear", "top")
IDENTIFIER_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
INSTANCE_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
EVIDENCE_OPTIONAL_VALUES = {"optional", "required", "diagnostic", "not-applicable"}


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
    screenshot_purpose: str
    knowledge_profile: str
    candidate_root: str
    provenance: dict[str, str]
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
    values: dict[str, str] = {}
    pattern = re.compile(r'([A-Za-z_][\w-]*)=(?:"([^"]*)"|([^\s]+))')
    for match in pattern.finditer(value):
        values[match.group(1)] = match.group(2) if match.group(2) is not None else match.group(3)
    return values


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
    knowledge = _key_values(_comment_value("knowledge", source))
    candidate = _key_values(_comment_value("candidate", source))
    provenance = _key_values(_comment_value("provenance", source))
    screenshot_type = screenshot.get("type", "")
    default_screenshot_angles = "0" if not screenshot_type and evidence.get("static") == "not-applicable" else "1"
    try:
        screenshot_angles = int(screenshot.get("angles", default_screenshot_angles))
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
        screenshot_purpose=screenshot.get("purpose", "diagnostic"),
        knowledge_profile=knowledge.get("profile", "roblox-core-v1"),
        candidate_root=candidate.get("root", "BloxBenchCandidate"),
        provenance=provenance or {"origin": "hand-authored"},
        evidence=evidence,
        rubric=rubric,
    )
    validate_fixture(fixture)
    return fixture


def validate_fixture(fixture: Fixture) -> None:
    errors: list[str] = []
    if not fixture.track:
        errors.append("missing @track")
    if not IDENTIFIER_PATTERN.fullmatch(fixture.track):
        errors.append("@track must be a lowercase identifier")
    if not fixture.place:
        errors.append("fixture must declare a starter place")
    elif Path(fixture.place).is_absolute() or ".." in Path(fixture.place).parts:
        errors.append("place must be a repository-relative path")
    if not IDENTIFIER_PATTERN.fullmatch(fixture.knowledge_profile):
        errors.append("@knowledge profile must be a lowercase identifier")
    if not INSTANCE_NAME_PATTERN.fullmatch(fixture.candidate_root):
        errors.append("@candidate root must be an instance name")
    if any(not key or not value for key, value in fixture.provenance.items()):
        errors.append("@provenance values must be non-empty")
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
    static_evidence = fixture.evidence.get("static")
    if static_evidence != "not-applicable":
        if not IDENTIFIER_PATTERN.fullmatch(fixture.screenshot_type):
            errors.append("@screenshot type must be a lowercase identifier")
        if fixture.screenshot_angles < 1 or fixture.screenshot_angles > 4:
            errors.append("screenshot angles must be between 1 and 4")
        if fixture.screenshot_primary not in SCREENSHOT_ANGLE_NAMES:
            errors.append("screenshot primary must be hero, front, side, rear, or top")
    elif fixture.screenshot_type or fixture.screenshot_angles != 0:
        errors.append("static=not-applicable cannot declare screenshot capture")
    if fixture.evidence.get("review") != "human-pairwise":
        errors.append("@evidence must declare review=human-pairwise")
    if fixture.stateful and fixture.evidence.get("trace") != "required":
        errors.append("stateful fixture must declare trace=required")
    if fixture.stateful and fixture.evidence.get("reset") != "required":
        errors.append("stateful fixture must declare reset=required")
    if fixture.screenshot_purpose not in {"diagnostic", "presentation"}:
        errors.append("screenshot purpose must be diagnostic or presentation")
    if fixture.evidence.get("static") not in EVIDENCE_OPTIONAL_VALUES:
        errors.append("fixture must declare static=optional, required, diagnostic, or not-applicable")
    if fixture.evidence.get("video") not in EVIDENCE_OPTIONAL_VALUES:
        errors.append("fixture must declare video=optional, required, diagnostic, or not-applicable")
    if fixture.runtime not in {"edit", "play"}:
        errors.append("@runtime mode must be edit or play")
    if errors:
        raise FixtureContractError(f"{fixture.path}: " + "; ".join(errors))


def resolve_starter_place(repository_root: str | Path, place: str) -> Path:
    """Resolve a repository-relative starter place, with legacy Places fallback."""
    raw = Path(place)
    if raw.is_absolute() or ".." in raw.parts:
        raise FixtureContractError("starter place must be repository-relative")
    root = Path(repository_root)
    candidates = (root / raw, root / "Places" / raw)
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    # Return the canonical repository-relative location so callers can report
    # the useful missing path without silently inventing another location.
    return candidates[0]


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
