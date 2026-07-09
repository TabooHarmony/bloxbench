#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#     "aiohttp",
#     "mcp",
#     "python-dotenv",
# ]
# ///
"""
OpenGameEval Local Harness
Runs OpenGameEval evals locally against Roblox Studio via MCP.
Supports skills injection for benchmarking LLMs with/without context.
"""

import asyncio
import base64
import json
import time
import os
import re
import subprocess
import sys
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Auto-route skills based on eval prompt content
try:
    from skill_router import SkillRouter
except ImportError:
    SkillRouter = None
# Visual judge support
try:
    from judge import VisualJudge
except ImportError:
    VisualJudge = None

from dataclasses import dataclass, field, asdict
from typing import Optional

from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp import ClientSession
import aiohttp
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def fmt_time(ms: int) -> str:
    """Format milliseconds as human-readable duration."""
    if ms < 1000:
        return f"{ms}ms"
    s = ms / 1000
    if s < 60:
        return f"{s:.1f}s"
    m = s / 60
    if m < 60:
        return f"{m:.1f}m"
    h = m / 60
    return f"{h:.1f}h"


# �"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?
# Config
# �"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?

@dataclass
class ModelConfig:
    name: str
    api_base: str
    api_key: str


@dataclass
class StudioConfig:
    exe_path: str
    mcp_path: str
    startup_wait: int = 45


@dataclass
class RunConfig:
    evals_dir: str
    places_dir: str
    max_tool_rounds: int = 25
    pass_n: int = 1
    output_dir: str = "results"
    screenshots: bool = False
    verbose: bool = False
    eval_timeout: int = 600
    run_dir: str = ""
    skill_loader: Optional["SkillLoader"] = None
    skill_router: Optional["SkillRouter"] = None
    skills_index: Optional[str] = None
    judge: Optional[object] = None
    judge_enabled: bool = False
    temperature: float = 0
    max_tokens_per_eval: int = 500000
    solver_code: Optional[str] = None  # SpatialSolver.lua source (solver mode)
    no_gate: bool = False  # Skip check_scene, capture everything for human review
    fixer: bool = False  # Run StructuralFixer after build, before screenshots
    fixer_code: Optional[str] = None  # StructuralFixer.lua source
    helpers_code: Optional[str] = None  # SpatialHelpers.lua source (helpers mode)
    primitives_code: Optional[str] = None  # PartPrimitives.lua source (primitives mode)


# �"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?
# Skill Loader
# �"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?

class SkillLoader:
    """Serves skill content on demand via the skill_view tool."""

    def __init__(self, skills_source: str):
        self.source = Path(skills_source)
        self.skills: dict[str, str] = {}
        self._load()

    def _load(self):
        for md in sorted(self.source.rglob("SKILL.md")):
            name = md.parent.name
            content = md.read_text(encoding="utf-8")
            # Strip YAML frontmatter
            if content.startswith("---"):
                end = content.find("---", 3)
                if end != -1:
                    content = content[end + 3:].strip()
            self.skills[name] = content
            logger.debug(f"  Loaded skill: {name} ({len(content)} chars)")

    def get_skill(self, name: str) -> str:
        if name in self.skills:
            return self.skills[name]
        available = ", ".join(sorted(self.skills.keys()))
        return f"Skill '{name}' not found. Available: {available}"

    @staticmethod
    def tool_definition() -> dict:
        return {
            "type": "function",
            "function": {
                "name": "skill_view",
                "description": "Load a domain knowledge skill by name. Returns rules, code patterns, and anti-patterns for Roblox development.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Skill name, e.g. roblox-building, roblox-physics, roblox-gui",
                        }
                    },
                    "required": ["name"],
                },
            },
        }


# �"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?
# Eval Parser
# �"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?

@dataclass
class EvalFile:
    path: str
    scenario_name: str
    prompt_text: str
    place: str
    script: str
    judge_rubric: dict = field(default_factory=dict)
    screenshot_type: str = ""
    screenshot_angles: int = 1
    screenshot_primary: str = "front"
    check_game_empty: bool = True


def parse_eval(path: str) -> EvalFile:
    content = Path(path).read_text(encoding="utf-8")

    name_m = re.search(r'scenario_name\s*=\s*"([^"]+)"', content)
    place_m = re.search(r'place\s*=\s*"([^"]+)"', content)

    # prompt can be [[multi-line]] or "single-line"
    prompt_m = re.search(r'content\s*=\s*\[\[(.+?)\]\]', content, re.DOTALL)
    if not prompt_m:
        prompt_m = re.search(r'content\s*=\s*"([^"]+)"', content)

    # Parse judge rubric from comments
    rubric = {}
    rubric_m = re.search(r'--\s*@judge_rubric\s+(.*)', content)
    if rubric_m:
        for match in re.finditer(r'(\w+)="([^"]*)"', rubric_m.group(1)):
            rubric[match.group(1)] = match.group(2)

    # Parse screenshot config
    ss_type = ""
    ss_angles = 1
    ss_primary = "front"
    ss_m = re.search(r'--\s*@screenshot\s+type=(\w+)\s+angles=(\d+)(?:\s+primary=(\w+))?', content)
    if ss_m:
        ss_type = ss_m.group(1)
        ss_angles = int(ss_m.group(2))
        if ss_m.group(3):
            ss_primary = ss_m.group(3)

    # Detect if check_game has a non-empty body
    check_game_empty = True
    cg_m = re.search(r'eval\.check_game\s*=\s*function\(\)\s*\n(.*?)\nend', content, re.DOTALL)
    if cg_m:
        body = cg_m.group(1).strip()
        if body and not body.startswith("--") and len(body) > 5:
            check_game_empty = False

    return EvalFile(
        path=path,
        scenario_name=name_m.group(1) if name_m else Path(path).stem,
        prompt_text=prompt_m.group(1).strip() if prompt_m else "",
        place=place_m.group(1) if place_m else "",
        script=content,
        judge_rubric=rubric,
        screenshot_type=ss_type,
        screenshot_angles=ss_angles,
        screenshot_primary=ss_primary,
        check_game_empty=check_game_empty,
    )


# �"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?
# Metrics
# �"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?

@dataclass
class EvalMetrics:
    scenario: str = ""
    place: str = ""
    passed: bool = False
    passed_cons: bool = False   # Cons@5: >=3/5 passes
    passed_all: bool = False    # All@5: 5/5 passes
    scene_passed: Optional[bool] = None
    game_passed: Optional[bool] = None
    error: Optional[str] = None
    llm_calls: int = 0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    llm_latency_ms: int = 0
    tool_calls: int = 0
    tool_errors: int = 0
    total_time_ms: int = 0
    rounds_used: int = 0
    screenshot_path: Optional[str] = None
    error_category: str = ""
    retried: bool = False
    tools_used: list = field(default_factory=list)  # unique tool names called
    edit_count: int = 0      # multi_edit + script-creating execute_luau calls
    max_context_tokens: int = 0  # peak prompt_tokens in final LLM round
    skills_used: list = field(default_factory=list)  # skill files injected for this eval
    tool_errors_by_type: dict = field(default_factory=dict)  # {tool_name: error_count}
    tool_calls_by_type: dict = field(default_factory=dict)   # {tool_name: call_count}
    harness_tool_calls: int = 0
    harness_tool_errors: int = 0
    harness_tool_calls_by_type: dict = field(default_factory=dict)
    harness_tool_errors_by_type: dict = field(default_factory=dict)
    judge_scores: Optional[dict] = None
    judge_overall: Optional[int] = None
    judge_reasoning: Optional[str] = None
    judge_issues: list = field(default_factory=list)
    screenshot_paths: list = field(default_factory=list)
    structure_dump: Optional[str] = None
    created_scripts: dict = field(default_factory=dict)  # name -> source code
    tool_call_sequence: list = field(default_factory=list)  # ordered tool names
    time_breakdown: dict = field(default_factory=dict)  # {llm_ms, tool_ms, screenshot_ms, setup_ms}
    final_response_text: Optional[str] = None  # model's last message
    fixer_report: Optional[str] = None  # StructuralFixer output log


# �"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?
# LLM Bridge
# �"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?

def mcp_tools_to_openai(tools) -> list:
    """Convert MCP tool definitions to OpenAI function calling format."""
    openai_tools = []
    for tool in tools:
        schema = tool.inputSchema if hasattr(tool, "inputSchema") and tool.inputSchema else {"type": "object", "properties": {}}
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": schema,
            },
        })
    return openai_tools


async def llm_chat(
    config: ModelConfig,
    messages: list,
    tools: list,
    timeout: int = 120,
    max_retries: int = 5,
    temperature: float = 0,
) -> dict:
    """Call an OpenAI-compatible chat completions endpoint with retry.

    Uses exponential backoff: 2s, 4s, 8s, 16s, 32s.
    Better error unwrapping for ExceptionGroup/TaskGroup errors.

    Handles Cline Pass API which wraps responses in {"data": {...}, "success": true}.
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {config.api_key}",
    }
    payload = {
        "model": config.name,
        "messages": messages,
        "temperature": temperature,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    last_error = None
    for attempt in range(max_retries):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{config.api_base}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(
                        total=timeout,
                        connect=15,
                        sock_read=timeout,
                    ),
                ) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        if resp.status == 429:
                            raise RuntimeError(f"429_RATE_LIMIT: {body[:200]}")
                        raise RuntimeError(f"LLM API error {resp.status}: {body[:500]}")
                    data = await resp.json()
                    # Cline Pass wraps response in {"data": {...}, "success": true}
                    # Unwrap if needed so downstream code sees standard OpenAI format
                    if "data" in data and "choices" not in data and "choices" in data.get("data", {}):
                        data = data["data"]
                    return data
        except (aiohttp.ClientError, asyncio.TimeoutError, RuntimeError) as e:
            last_error = e
            err_msg = str(e)
            if hasattr(e, 'exceptions') and e.exceptions:
                err_msg = str(e.exceptions[0])
            if not err_msg:
                err_msg = type(e).__name__
            if attempt < max_retries - 1:
                if "429" in err_msg:
                    wait = min(2 ** attempt, 8)
                else:
                    wait = 2 ** attempt
                logger.warning(f"LLM call failed (attempt {attempt+1}/{max_retries}): {err_msg[:100]}. Retrying in {wait}s...")
                await asyncio.sleep(wait)
            else:
                logger.error(f"LLM call failed (attempt {attempt+1}/{max_retries}): {err_msg[:200]}")
    raise last_error or RuntimeError("LLM call failed after all retries")


# �"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?
# �"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?
# Error Categorization
# �"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?

def categorize_error(error_text: str) -> str:
    """Categorize an error message into a standard category.

    Returns one of: "model_fail", "timeout", "transient_error",
                    "setup_error", "infra_error", "harness_error"
    """
    if not error_text:
        return ""
    err = error_text.upper()
    if "TIMEOUT" in err:
        return "timeout"
    if "TOOL ERROR" in err:
        return "transient_error"
    # Setup failures (eval-specific, not harness code bugs)
    if "SETUP_ERROR" in err or "SETUP FAILED" in err:
        return "setup_error"
    # Eval assertion failures = model didn't accomplish the task
    if "CHECK_SCENE FAILED" in err or "CHECK_GAME FAILED" in err:
        return "model_fail"
    # External infrastructure failures — check BEFORE generic keywords
    # because HTTP 429 text may contain "expected" etc.
    if any(kw in err for kw in ["HTTP 403", "HTTP 404", "HTTP 429", "HTTP 500",
                                  "HTTP 502", "HTTP 503", "HTTP 504",
                                  "FORBIDDEN", "USER IS MODERATED",
                                  "STUDIO PROCESS NOT FOUND",
                                  "FAILED TO LAUNCH STUDIO"]):
        return "infra_error"
    # Network/connection errors — check BEFORE generic keywords
    if any(kw in err for kw in ["CONNECTION", "NETWORK", "ECONNRESET", "ECONNREFUSED",
                                  "ETIMEDOUT", "SOCKET", "DNS", "SSL", "CERTIFICATE",
                                  "BROKEN PIPE", "REMOTE DISCONNECT",
                                  "TASKGROUP", "CLOSEDRESOURCE", "BROKENRESOURCE"]):
        return "transient_error"
    # Generic model failure keywords — checked LAST
    if any(kw in error_text for kw in ["is not", "isn't", "expected", "should be",
                                        "not properly", "hasn't", "has not been",
                                        "was not", "wasn't", "did not", "didn't",
                                        "missing", "incorrect"]):
        return "model_fail"
    return "harness_error"


# �"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?
# Studio Lifecycle
# �"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?

async def launch_studio(studio: StudioConfig, place_path: str) -> bool:
    """Launch Studio on the interactive desktop via schtasks.

    SSH sessions run in Windows Session 0 (non-interactive). subprocess.Popen
    from SSH creates GUI processes that never render. schtasks /it forces the
    process onto the logged-on user's interactive desktop.
    """
    abs_place = str(Path(place_path).resolve())
    logger.info(f"Launching Studio with {abs_place}")

    # Clean up stale lock file (previous force-kill may have left it)
    lock_file = abs_place + ".lock"
    if os.path.exists(lock_file):
        try:
            os.remove(lock_file)
            logger.info(f"Removed stale lock file: {lock_file}")
        except OSError:
            pass

    # Restore cookies before launch (in case previous kill corrupted them)
    restore_cookies()

    exe = studio.exe_path
    cmd = f'"{exe}" -localPlaceFile "{abs_place}"'
    task_name = f"HarnessStudio_{int(time.time())}"

    # Create scheduled task targeting interactive desktop
    # NOTE: do NOT use /rl highest — elevation changes the user token context,
    # which makes WebView2 use a different cookie store (Studio loses auth).
    create = subprocess.run(
        ["schtasks", "/create", "/tn", task_name, "/tr", cmd,
         "/sc", "once", "/st", "00:00", "/f", "/it"],
        capture_output=True, text=True,
    )
    if create.returncode != 0:
        logger.error(f"schtasks create failed: {create.stderr.strip()}")
        return False

    # Run it immediately
    run = subprocess.run(
        ["schtasks", "/run", "/tn", task_name],
        capture_output=True, text=True,
    )
    if run.returncode != 0:
        logger.error(f"schtasks run failed: {run.stderr.strip()}")
        return False

    # Clean up the task definition (the process keeps running)
    subprocess.run(
        ["schtasks", "/delete", "/tn", task_name, "/f"],
        capture_output=True, text=True,
    )

    logger.info(f"Waiting {studio.startup_wait}s for Studio to load...")
    await asyncio.sleep(studio.startup_wait)
    return True

# WebView2 cookie protection �?" force-killing Studio can corrupt the SQLite
# cookie database, causing Studio to lose auth on next launch.
_COOKIES_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", r"C:\Users\Admin\AppData\Local"),
    "Roblox", "RobloxStudio", "WebView2", "EBWebView", "Default", "Network",
)
_COOKIES_BACKUP = _COOKIES_DIR + ".bak"


def backup_cookies():
    """Snapshot WebView2 cookies before Studio launch.

    Best-effort: Studio may hold an exclusive lock on the SQLite database,
    causing WinError 32. In that case we skip the backup and continue.
    """
    import shutil
    cookies = os.path.join(_COOKIES_DIR, "Cookies")
    journal = os.path.join(_COOKIES_DIR, "Cookies-journal")
    if os.path.exists(cookies):
        try:
            shutil.copy2(cookies, _COOKIES_BACKUP)
            if os.path.exists(journal):
                shutil.copy2(journal, _COOKIES_BACKUP + "-journal")
            logger.info("cookies backed up")
        except OSError as e:
            logger.debug(f"cookies backup skipped (file locked): {e}")


def restore_cookies():
    """Restore cookies from backup if current ones are missing/corrupt."""
    import shutil
    cookies = os.path.join(_COOKIES_DIR, "Cookies")
    backup = _COOKIES_BACKUP
    if os.path.exists(backup) and (not os.path.exists(cookies) or os.path.getsize(cookies) == 0):
        shutil.copy2(backup, cookies)
        bj = backup + "-journal"
        cj = cookies + "-journal"
        if os.path.exists(bj):
            shutil.copy2(bj, cj)
        logger.info("cookies restored from backup")
    elif os.path.exists(cookies):
        logger.info("cookies file exists, no restore needed")


def kill_studio(_unused=None):
    """Kill all Roblox/Studio processes and wait until they're actually gone.

    Cookie backup/restore (called in launch_studio) handles auth persistence.
    Must kill StudioMCP and CrashHandler too �?" they can hold locks on resources.
    """
    for proc_name in ("StudioMCP.exe", "RobloxStudioBeta.exe", "RobloxCrashHandler.exe"):
        subprocess.run(
            ["taskkill", "/f", "/im", proc_name],
            capture_output=True, text=True,
        )
    # Wait until all Roblox processes are actually dead (max 10s)
    for _ in range(20):
        time.sleep(0.5)
        check = subprocess.run(
            ["tasklist", "/fi", "imagename eq RobloxStudioBeta.exe", "/nh"],
            capture_output=True, text=True,
        )
        if "RobloxStudioBeta.exe" not in check.stdout:
            return
    logger.warning("Studio still alive after 10s of force kills, trying again")
    subprocess.run(
        ["taskkill", "/f", "/im", "RobloxStudioBeta.exe"],
        capture_output=True, text=True,
    )
    time.sleep(2)


# �"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?
# Eval Runner
# �"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?

# EvalUtils module implementations (reverse-engineered from eval script usage)
# Loaded from evalutils/ directory at startup

def _load_evalutils_modules():
    """Load EvalUtils Lua modules from evalutils/ directory."""
    modules = {}
    evalutils_dir = Path(__file__).parent / "evalutils"
    for lua_file in sorted(evalutils_dir.glob("*.lua")):
        modules[lua_file.stem] = lua_file.read_text(encoding="utf-8")
    return modules

_EVALUTILS_MODULES = _load_evalutils_modules()

def _build_evalutils_inject_lua():
    """Build Lua code that creates LoadedCode + EvalUtils ModuleScripts."""
    # Build a Lua table of name -> source using long strings [[...]]
    module_entries = []
    for name, source in _EVALUTILS_MODULES.items():
        # Use Lua long string to avoid escaping issues
        # Replace any ]] in source with ]=] to avoid closing the long string
        safe_source = source.replace("]]", "] ]")
        module_entries.append(f'["{name}"] = [[{safe_source}]]')

    modules_table = "{\n" + ",\n".join(module_entries) + "\n}"

    return f"""
local LoadedCode = game:FindFirstChild("LoadedCode")
if not LoadedCode then
    LoadedCode = Instance.new("ModuleScript")
    LoadedCode.Name = "LoadedCode"
    LoadedCode.Source = "return {{}}"
    LoadedCode.Parent = game
end

-- Enable loadstring for game scripts (identity 2)
pcall(function()
    game:GetService("ServerScriptService").LoadStringEnabled = true
end)

local eu = LoadedCode:FindFirstChild("EvalUtils")
if not eu then
    eu = Instance.new("Folder")
    eu.Name = "EvalUtils"
    eu.Parent = LoadedCode
end

local modules = {modules_table}

for name, source in pairs(modules) do
    -- Destroy and recreate (do NOT just overwrite .Source): a ModuleScript whose
    -- .Source is overwritten after it has already been require()'d keeps its stale
    -- compiled state, which can surface as "module experienced an error while loading"
    -- on later evals. Recreating forces a clean compile every eval.
    local existing = eu:FindFirstChild(name)
    if existing then existing:Destroy() end
    local mod = Instance.new("ModuleScript")
    mod.Name = name
    mod.Source = source
    mod.Parent = eu
end
return "ok"
"""

ENSURE_LOADED_CODE = _build_evalutils_inject_lua()

# Full rebuild: destroy LoadedCode entirely, then re-inject. Used to recover from
# stale/corrupted module state left by a previous eval's model phase.
REBUILD_LOADED_CODE = """
local existing = game:FindFirstChild("LoadedCode")
if existing then existing:Destroy() end
""" + ENSURE_LOADED_CODE

# Bridge script for server-side check_game execution.
# This Script runs in the game server context during play mode (not plugin context).
# It loads eval code from ReplicatedStorage, runs check_game, and returns the result
# via StudioTestService:EndTest().
BRIDGE_SCRIPT_LUA = r"""
-- Wrap entire bridge in pcall for error reporting
local bridgeOk, bridgeErr = pcall(function()
local Players = game:GetService("Players")
local RS = game:GetService("ReplicatedStorage")
local STS = game:GetService("StudioTestService")

-- Timeout: auto-end test after 60s
local timedOut = false
task.delay(60, function()
    timedOut = true
    pcall(function() STS:EndTest("false|TIMEOUT: check_game exceeded 60s") end)
end)

-- Wait for game to be ready (non-blocking)
print("[bridge] script started")
task.wait(2)  -- brief settle instead of blocking game.Loaded:Wait()
print("[bridge] after settle")

-- Wait for player �?" try multiple methods
local player = nil
if #Players:GetPlayers() > 0 then
    player = Players:GetPlayers()[1]
else
    print("[bridge] waiting for player...")
    local conn
    conn = Players.PlayerAdded:Connect(function(p)
        player = p
        if conn then conn:Disconnect() end
    end)
    -- Also check if a player sneaked in between the check and connect
    if #Players:GetPlayers() > 0 then
        player = Players:GetPlayers()[1]
        if conn then conn:Disconnect() end
    end
    if not player then
        -- Wait up to 10s for a player
        for i = 1, 20 do
            task.wait(0.5)
            if player then break end
            if #Players:GetPlayers() > 0 then
                player = Players:GetPlayers()[1]
                break
            end
        end
    end
    if conn then pcall(function() conn:Disconnect() end) end
end

if not player then
    print("[bridge] ERROR: no player after 10s")
    STS:EndTest("false|NO_PLAYER: no player joined within 10s")
    return
end
print("[bridge] player: " .. player.Name)

-- Brief settle for character
task.wait(2)
print("[bridge] loading eval code...")

-- Load eval code from ReplicatedStorage
local evalMc = RS:FindFirstChild("_HarnessEvalCode")
if not evalMc then
    STS:EndTest("false|NO_EVAL_MODULE: _HarnessEvalCode not found in ReplicatedStorage")
    return
end

local ok, eval = pcall(require, evalMc)
if not ok then
    print("[bridge] require error: " .. tostring(eval))
    STS:EndTest("false|REQUIRE_ERROR: " .. tostring(eval))
    return
end
if type(eval) ~= "table" then
    STS:EndTest("false|EVAL_NOT_TABLE: " .. type(eval))
    return
end
if not eval.check_game then
    print("[bridge] no check_game function, skipping")
    STS:EndTest("true|NO_CHECK")
    return
end

print("[bridge] running check_game...")
local cok, cerr = pcall(eval.check_game)
if timedOut then return end  -- timeout handler already called EndTest
if cok then
    print("[bridge] check_game PASSED")
    STS:EndTest("true|pass")
else
    print("[bridge] check_game FAILED: " .. tostring(cerr))
    STS:EndTest("false|" .. tostring(cerr))
end
end)  -- end of pcall

-- If the bridge errored and EndTest was never called, report the error
if not bridgeOk then
    print("[bridge] FATAL ERROR: " .. tostring(bridgeErr))
    pcall(function()
        game:GetService("StudioTestService"):EndTest("false|BRIDGE_ERROR: " .. tostring(bridgeErr))
    end)
end
"""

async def run_check_game_sts(session, ev: EvalFile, m: EvalMetrics, timeout: float = 120.0) -> Optional[str]:
    """Run check_game via StudioTestService bridge.

    Stores eval code in ReplicatedStorage, creates a server-side Script
    in ServerScriptService that executes check_game in the game server context,
    then uses StudioTestService:ExecutePlayModeAsync to run play mode and
    collect the result via EndTest().

    Returns the result string (e.g. "true|pass", "false|error") or None on failure.
    """
    eval_code = ev.script

    # 0. Ensure Studio is in edit mode BEFORE creating anything.
    #    If the model called start_stop_play during the eval, the play DataModel
    #    is active. Creating the bridge here then stopping play would discard it
    #    (play DataModel is destroyed on stop). We must be in edit mode first so
    #    the bridge lives in the edit DataModel that ExecutePlayModeAsync clones.
    try:
        await session.call_tool("start_stop_play", {"is_start": False})
        await asyncio.sleep(2)  # let Studio settle out of play mode
    except Exception as e:
        logger.debug(f"  pre-stop play mode failed (non-fatal): {e}")

    # 1. Store eval code as ModuleScript in ReplicatedStorage
    store_lua = f"""
local existing = game:GetService("ReplicatedStorage"):FindFirstChild("_HarnessEvalCode")
if existing then existing:Destroy() end
local mc = Instance.new("ModuleScript")
mc.Name = "_HarnessEvalCode"
mc.Source = [==[{eval_code}]==]
mc.Parent = game:GetService("ReplicatedStorage")
return "ok"
"""
    r, store_text = await harness_call_tool(session, "execute_luau", {"datamodel_type": "Edit", "code": store_lua}, m)
    if "ok" not in (store_text or ""):
        logger.warning(f"  Failed to store eval code: {store_text}")
        return None

    # 2. Create bridge Script in ServerScriptService
    bridge_safe = BRIDGE_SCRIPT_LUA.replace("]]", "] ]")
    create_script_lua = f"""
local SSS = game:GetService("ServerScriptService")
local existing = SSS:FindFirstChild("_HarnessBridge")
if existing then existing:Destroy() end
local s = Instance.new("Script")
s.Name = "_HarnessBridge"
s.Source = [[{bridge_safe}]]
s.Parent = SSS
-- Verify it was created
local check = SSS:FindFirstChild("_HarnessBridge")
if check then
    return "ok|source_len=" .. #check.Source
else
    return "error|script not found after creation"
end
"""
    r, bridge_status = await harness_call_tool(session, "execute_luau", {"datamodel_type": "Edit", "code": create_script_lua}, m)
    bridge_status = bridge_status or ""
    logger.info(f"  bridge script: {bridge_status}")
    if "ok" not in bridge_status:
        logger.warning(f"  Failed to create bridge script: {bridge_status}")
        return None

    # 3. Use StudioTestService:ExecutePlayModeAsync to start play mode
    #    This blocks until the server script calls EndTest()
    run_lua = f"""
local STS = game:GetService("StudioTestService")
local ok, result = pcall(function()
    return STS:ExecutePlayModeAsync({{source = "harness"}})
end)
if ok then
    return tostring(result)
else
    return "false|EXECUTE_PLAY_ERROR: " .. tostring(result)
end
"""
    logger.info("  Starting play mode via StudioTestService...")
    try:
        r, play_text = await asyncio.wait_for(
            harness_call_tool(session, "execute_luau", {"datamodel_type": "Edit", "code": run_lua}, m),
            timeout=timeout,
        )
        result = play_text or "false|no_response"
    except asyncio.TimeoutError:
        logger.warning(f"  StudioTestService timed out after {timeout}s")
        # Diagnose: check if bridge script exists and is running
        try:
            diag = await session.call_tool("execute_luau", {"datamodel_type": "Edit", "code": """
local s = game:GetService("ServerScriptService"):FindFirstChild("_HarnessBridge")
if s then
    return "bridge_exists|disabled=" .. tostring(s.Disabled) .. "|runcontext=" .. tostring(s.RunContext)
else
    return "bridge_missing"
end
"""})
            logger.info(f"  bridge diagnostic: {get_tool_text(diag)}")
        except Exception as e:
            logger.info(f"  bridge diagnostic failed: {e}")
        # Force stop play mode
        try:
            await session.call_tool("start_stop_play", {"is_start": False})
        except Exception:
            pass
        result = "false|TIMEOUT"

    # Capture bridge debug output from Studio console
    try:
        console = await session.call_tool("get_console_output", {})
        console_text = get_tool_text(console) or ""
        # Extract bridge lines
        for line in console_text.split("\n"):
            if "[bridge]" in line:
                logger.info(f"  {line.strip()}")
    except Exception:
        pass

    # 4. Cleanup
    try:
        await session.call_tool("execute_luau", {"datamodel_type": "Edit", "code": """
local c = game:GetService("ReplicatedStorage"):FindFirstChild("_HarnessEvalCode")
if c then c:Destroy() end
local s = game:GetService("ServerScriptService"):FindFirstChild("_HarnessBridge")
if s then s:Destroy() end
"""})
    except Exception:
        pass

    logger.info(f"  check_game result: {result}")
    return result


def get_tool_text(result) -> str:
    """Extract text from MCP tool result, handling different content types."""
    if not result or not result.content:
        return ""
    for c in result.content:
        if hasattr(c, "text"):
            return c.text
    return str(result.content[0])


def is_tool_error(result, tool_text: str = "") -> bool:
    """Check if an MCP tool result indicates an error.
    
    Checks both the MCP isError flag and common error patterns in text.
    """
    # MCP protocol's isError flag
    if hasattr(result, 'isError') and result.isError:
        return True
    # Text-based error detection for tools that don't set isError properly
    if tool_text:
        text_lower = tool_text.lower().strip()
        # Only flag clear error patterns, not normal game/script errors
        error_prefixes = ('tool error:', 'error: mcp connection', 'tool not found:',
                          'datamodel_type is required', 'unable to find an active studio')
        if any(text_lower.startswith(p) for p in error_prefixes):
            return True
    return False


def track_tool_error(m: EvalMetrics, tool_name: str, is_error: bool):
    """Track per-tool-type call counts and errors."""
    m.tool_calls_by_type[tool_name] = m.tool_calls_by_type.get(tool_name, 0) + 1
    if is_error:
        m.tool_errors_by_type[tool_name] = m.tool_errors_by_type.get(tool_name, 0) + 1
        m.tool_errors += 1


async def harness_call_tool(session, tool_name: str, args: dict, m: EvalMetrics):
    """Call an MCP tool from harness code with error tracking.

    Separate from LLM tool_call tracking so harness errors don't inflate model metrics.
    Returns (result, text) tuple.
    """
    m.harness_tool_calls += 1
    m.harness_tool_calls_by_type[tool_name] = m.harness_tool_calls_by_type.get(tool_name, 0) + 1
    try:
        result = await session.call_tool(tool_name, args)
        text = get_tool_text(result)
        is_err = is_tool_error(result, text)
        if is_err:
            m.harness_tool_errors += 1
            m.harness_tool_errors_by_type[tool_name] = m.harness_tool_errors_by_type.get(tool_name, 0) + 1
            logger.warning(f"[harness] {tool_name} returned error: {text[:200]}")
        return result, text
    except Exception as e:
        m.harness_tool_errors += 1
        m.harness_tool_errors_by_type[tool_name] = m.harness_tool_errors_by_type.get(tool_name, 0) + 1
        logger.error(f"[harness] {tool_name} exception: {e}")
        raise


async def _run_single_eval_inner(
    ev: EvalFile,
    model: ModelConfig,
    studio: StudioConfig,
    run: RunConfig,
) -> EvalMetrics:
    """Inner eval logic, called by run_single_eval with timeout wrapping."""
    m = EvalMetrics(scenario=ev.scenario_name, place=ev.place)
    t0 = time.time()

    place_path = Path(run.places_dir) / ev.place
    if not place_path.exists():
        m.error = f"Place file not found: {place_path}"
        m.error_category = categorize_error(m.error)
        m.total_time_ms = int((time.time() - t0) * 1000)
        return m

    studio_proc = None
    try:
        # 1. Launch Studio on interactive desktop (with retry)
        studio_launched = False
        for launch_attempt in range(3):
            if launch_attempt > 0:
                logger.warning(f"[{ev.scenario_name}] Studio launch retry {launch_attempt+1}/3")
                kill_studio()  # clean up any partial launch
                await asyncio.sleep(5)
            if not await launch_studio(studio, str(place_path)):
                continue

            # 1b. Verify Studio is actually running (poll for up to 30s)
            studio_found = False
            for _ in range(6):
                check = subprocess.run(
                    ["tasklist", "/fi", "imagename eq RobloxStudioBeta.exe", "/nh"],
                    capture_output=True, text=True,
                )
                if "RobloxStudioBeta.exe" in check.stdout:
                    studio_found = True
                    break
                await asyncio.sleep(5)

            if studio_found:
                studio_launched = True
                break
            logger.warning(f"[{ev.scenario_name}] Studio process not found, will retry")

        if not studio_launched:
            m.error = "Studio process not found after 3 launch attempts"
            m.error_category = categorize_error(m.error)
            m.total_time_ms = int((time.time() - t0) * 1000)
            return m
        logger.info(f"[{ev.scenario_name}] Studio confirmed running")
        # Snapshot cookies while Studio is alive (auth is freshly loaded)
        backup_cookies()

        # 2. Connect MCP (with timeout on initialize �?" StudioMCP can hang if Studio isn't ready)
        server_params = StdioServerParameters(
            command="cmd.exe",
            args=["/c", studio.mcp_path],
        )

        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                try:
                    await asyncio.wait_for(session.initialize(), timeout=60)
                except asyncio.TimeoutError:
                    logger.error(f"[{ev.scenario_name}] MCP initialize timed out after 60s")
                    m.error = "MCP initialize timed out"
                    m.error_category = categorize_error(m.error)
                    m.total_time_ms = int((time.time() - t0) * 1000)
                    return m
                logger.info(f"[{ev.scenario_name}] MCP connected")
                tools_result = await session.list_tools()
                openai_tools = mcp_tools_to_openai(tools_result.tools)
                # Exclude vision-only tools (screen_capture returns base64 images that
                # non-vision models cannot interpret, wasting massive context tokens)
                _EXCLUDED_TOOLS = {"screen_capture"}
                openai_tools = [t for t in openai_tools if t["function"]["name"] not in _EXCLUDED_TOOLS]
                # Append skill_view tool for skills mode
                if run.skill_loader:
                    openai_tools.append(SkillLoader.tool_definition())
                    logger.info(f"[{ev.scenario_name}] skill_view tool appended ({len(run.skill_loader.skills)} skills available)")
                logger.info(f"[{ev.scenario_name}] {len(openai_tools)} tools available")

                # Studio readiness probe: wait until execute_luau actually works
                for probe_attempt in range(6):
                    try:
                        _, probe_text = await asyncio.wait_for(
                            harness_call_tool(session, "execute_luau", {"datamodel_type": "Edit", "code": 'return "ready"'}, m),
                            timeout=10,
                        )
                        if "ready" in probe_text:
                            logger.info(f"[{ev.scenario_name}] Studio ready (probe {probe_attempt+1})")
                            break
                    except Exception as probe_err:
                        logger.warning(f"[{ev.scenario_name}] Studio not ready (probe {probe_attempt+1}): {str(probe_err)[:100]}")
                    if probe_attempt < 5:
                        await asyncio.sleep(5)
                else:
                    logger.error(f"[{ev.scenario_name}] Studio never became ready after 30s")


                # 4. Ensure LoadedCode exists
                await harness_call_tool(session, "execute_luau", {"datamodel_type": "Edit", "code": ENSURE_LOADED_CODE}, m)

                # 4a. Remove SpawnLocation so it doesn't appear in screenshots or confuse gates
                await harness_call_tool(session, "execute_luau", {"datamodel_type": "Edit", "code": """
local sl = workspace:FindFirstChild("SpawnLocation")
if sl then sl:Destroy() end
return "spawn_removed"
"""}, m)

                # 4b. Solver mode: upload SpatialSolver module to ReplicatedStorage
                if run.solver_code:
                    solver_upload = f"""
local RS = game:GetService("ReplicatedStorage")
local existing = RS:FindFirstChild("SpatialSolver")
if existing then existing:Destroy() end
local mod = Instance.new("ModuleScript")
mod.Name = "SpatialSolver"
mod.Source = [==[{run.solver_code}]==]
mod.Parent = RS
return "solver_uploaded"
"""
                    _, solver_text = await harness_call_tool(
                        session, "execute_luau",
                        {"datamodel_type": "Edit", "code": solver_upload}, m
                    )
                    logger.info(f"[{ev.scenario_name}] Solver module uploaded: {solver_text[:60]}")

                # 4c. Helpers mode: upload SpatialHelpers module to ReplicatedStorage
                if run.helpers_code:
                    helpers_upload = f"""
local RS = game:GetService("ReplicatedStorage")
local existing = RS:FindFirstChild("SpatialHelpers")
if existing then existing:Destroy() end
local mod = Instance.new("ModuleScript")
mod.Name = "SpatialHelpers"
mod.Source = [==[{run.helpers_code}]==]
mod.Parent = RS
return "helpers_uploaded"
"""
                    _, helpers_text = await harness_call_tool(
                        session, "execute_luau",
                        {"datamodel_type": "Edit", "code": helpers_upload}, m
                    )
                    logger.info(f"[{ev.scenario_name}] SpatialHelpers module uploaded: {helpers_text[:60]}")

                # 4c-b. Primitives mode: upload PartPrimitives module to ReplicatedStorage
                if run.primitives_code:
                    primitives_upload = """
local RS = game:GetService("ReplicatedStorage")
local existing = RS:FindFirstChild("PartPrimitives")
if existing then existing:Destroy() end
local mod = Instance.new("ModuleScript")
mod.Name = "PartPrimitives"
mod.Source = [==[""" + run.primitives_code + """]==]
mod.Parent = RS
return "primitives_uploaded"
"""
                    _, primitives_text = await harness_call_tool(
                        session, "execute_luau",
                        {"datamodel_type": "Edit", "code": primitives_upload}, m
                    )
                    logger.info(f"[{ev.scenario_name}] PartPrimitives module uploaded: {primitives_text[:60]}")

                # 5. Run eval setup (via ModuleScript �?" loadstring unavailable at plugin identity)
                setup_lua = f"""
local evalMod = Instance.new("ModuleScript")
evalMod.Name = "_HarnessEvalSetup"
evalMod.Source = [==[{ev.script}]==]
evalMod.Parent = game
local ok, eval = pcall(require, evalMod)
evalMod:Destroy()
if not ok then return "SETUP_ERROR: " .. tostring(eval) end
if eval.setup then
    local sok, serr = pcall(eval.setup)
    if not sok then return "SETUP_ERROR: " .. tostring(serr) end
end
return "ok"
"""
                setup_text = ""
                for setup_attempt in range(3):
                    setup_result, _ = await harness_call_tool(session, "execute_luau", {"datamodel_type": "Edit", "code": setup_lua}, m)
                    setup_text = get_tool_text(setup_result)
                    if "SETUP_ERROR" not in setup_text:
                        break
                    # On a setup failure, the prior eval's model phase may have left
                    # LoadedCode / EvalUtils modules in a stale or corrupted state.
                    # Force a full rebuild of LoadedCode before retrying so the
                    # next attempt starts clean (fresh compile, no cached errors).
                    logger.warning(f"[{ev.scenario_name}] Setup failed (attempt {setup_attempt+1}/3): {setup_text[:120]}")
                    await harness_call_tool(session, "execute_luau", {"datamodel_type": "Edit", "code": REBUILD_LOADED_CODE}, m)
                    if setup_attempt < 2:
                        await asyncio.sleep(3)
                if "SETUP_ERROR" in setup_text:
                    m.error = f"Setup failed: {setup_text}"
                    m.error_category = categorize_error(m.error)
                    m.total_time_ms = int((time.time() - t0) * 1000)
                    return m

                m.time_breakdown["setup_ms"] = int((time.time() - t0) * 1000)
                # 6. Build messages for LLM
                messages = []
                # Skills mode: use skill index as system prompt
                if run.skills_index:
                    messages.append({"role": "system", "content": run.skills_index})

                # Auto-route relevant skills based on eval prompt content
                if run.skill_router is not None:
                    routed_skills = run.skill_router.route(ev.prompt_text, top_n=2)
                    if routed_skills:
                        for skill_name in routed_skills:
                            skill_content = run.skill_router.get_skill_content(skill_name)
                            if skill_content:
                                # Truncate to prevent context bloat (max 3K chars per skill)
                                truncated = skill_content[:3000]
                                messages.append({"role": "system", "content": f'## Relevant Skill: {skill_name}\n\n{truncated}'})
                                logger.info(f"[{ev.scenario_name}] auto-routed skill: {skill_name} ({len(skill_content)} chars)")
                    logger.info(f"[{ev.scenario_name}] skill index injected ({len(run.skills_index or '')} chars)")
                # Luau constraints + building style guidance (always on for research splinter)
                LUAU_SYSTEM_PROMPT = (
                    "You are working in Roblox Studio edit mode on an empty baseplate. "
                    "Your task is to build what is described using execute_luau with datamodel_type='Edit'. "
                    "The workspace contains only a Baseplate. "
                    "UI elements (ScreenGuis) go in StarterGui. "
                    "Scripts go in ServerScriptService or StarterPlayerScripts. "
                    "Use execute_luau with datamodel_type='Edit' to create and modify instances. "
                    "loadstring() is available in this environment. "
                    "Use require() with ModuleScripts for modular code.\n\n"
                    "## Building guidance\n"
                    "Build with Roblox Parts (Part, WedgePart, MeshPart if needed). Anchored = true for static builds.\n"
                    "Y is up. Place structures on the baseplate (bottom near Y=0 unless the prompt says otherwise).\n"
                    "Order: (1) main masses and silhouette, (2) secondary parts (limbs, roofs, masts, seats), "
                    "(3) small details. Do not detail a weak primary form.\n"
                    "Prefer true 3D structure: parts that protrude, recess, and connect in space. "
                    "Avoid a single box with colors painted on one face.\n"
                    "Use Size/Position/CFrame deliberately. Vary Material and Color so parts read as distinct.\n"
                    "Openings (doors, windows) should be real gaps or transparent parts, not flat decals.\n"
                    "The build should be recognizable from front, side, and top."
                )
                # Solver mode: append spec vocabulary
                if run.solver_code:
                    LUAU_SYSTEM_PROMPT += (
                        "\n\n"
                        "## SpatialSolver Module\n\n"
                        "A SpatialSolver module is available at `game.ReplicatedStorage.SpatialSolver`. "
                        "It lets you describe structures declaratively instead of computing CFrames manually.\n\n"
                        "Usage:\n"
                        "```lua\n"
                        "local Solver = require(game.ReplicatedStorage.SpatialSolver)\n"
                        "local result = Solver.build({\n"
                        "    components = {\n"
                        "        {name = \"base\", shape = \"block\", size = {20, 2, 20}, material = \"Stone\"},\n"
                        "        {name = \"tower_nw\", shape = \"cylinder\", diameter = 6, height = 20,\n"
                        "         position = {relative = \"base\", at = \"corner_nw\", offset_y = 10}},\n"
                        "        {name = \"door\", type = \"csg_subtract\", target = \"base\", shape = \"block\",\n"
                        "         size = {3, 4, 1}, position = {relative = \"base\", at = \"on_face_s\", center_x = true}},\n"
                        "    }\n"
                        "})\n"
                        "-- result = { success = true, parts = {...}, bounds = {...}, errors = {} }\n"
                        "```\n\n"
                        "### Shapes\n"
                        "block, cylinder (diameter+height), ball (diameter), wedge, cone (size)\n\n"
                        "### Position\n"
                        "{ relative = \"<name>\", at = \"<anchor>\", offset_x = N, offset_y = N, offset_z = N }\n"
                        "OR { absolute = {x, y, z} }\n\n"
                        "### Anchors\n"
                        "on_top, on_bottom, at_corner_nw/ne/sw/se, on_face_n/s/e_w/center, center\n"
                        "around_circumference (with count, radius, level_y, start_angle)\n\n"
                        "### CSG\n"
                        "{ type = \"csg_subtract\", target = \"<name>\", shape = \"block\", size = {...}, position = {...} }\n"
                        "{ type = \"csg_union\", target = \"<name>\", ... }\n\n"
                        "### Properties\n"
                        "material, color (RGB table or hex string), anchored, can_collide, transparency, name\n\n"
                        "The solver computes all CFrames. You never touch coordinates. "
                        "Describe what you want and where it goes relative to other parts."
                    )
                # Helpers v2: short factory API (H is auto-injected into execute_luau)
                if run.helpers_code:
                    LUAU_SYSTEM_PROMPT += (
                        "\n\n"
                        "## SpatialHelpers v2 (use these to build)\n\n"
                        "`H` is already available inside every execute_luau call. "
                        "Do NOT require it, do NOT script_read SpatialHelpers, do NOT invent coordinates by hand when H can place.\n\n"
                        "Factories create + style + place + parent in one call:\n"
                        "```lua\n"
                        "local floor = H.block({20, 1, 20}, {name=\"Floor\", material=\"Concrete\", color={150,150,150}, ground=true})\n"
                        "local wall = H.block({20, 8, 1}, {name=\"Wall\", material=\"Brick\", color={180,100,80}, of=floor, on=\"top\", face=\"south\"})\n"
                        "local pillar = H.block({2, 10, 2}, {name=\"Pillar\", of=floor, on=\"top\", corner=\"nw\"})\n"
                        "local post = H.cyl(1.5, 6, {name=\"Post\", material=\"Wood\", next_to=floor, dir=\"east\", gap=2})\n"
                        "local roof = H.wedge({20, 4, 12}, {name=\"Roof\", of=wall, on=\"top\"})\n"
                        "local ball = H.ball(3, {name=\"Orb\", of=pillar, on=\"top\", color={255,200,50}, material=\"Neon\"})\n"
                        "```\n\n"
                        "Placement fields on opts: `ground=true` | `at={x,y,z}` | `of=part` + `on=\"top\"|\"bottom\"|\"ground\"` | "
                        "`corner=\"nw|ne|sw|se\"` | `face=\"north|south|east|west\"` | `next_to=part` + `dir=` + `gap=` | `offset={x,y,z}`.\n"
                        "Style fields: `name`, `color={r,g,b}`, `material` (string), `transparency`.\n"
                        "Also: `H.place(part, opts)` for an existing part; `H.color` / `H.material`.\n"
                        "Prefer a few H.block/H.cyl calls over many raw Instance.new parts."
                    )
                # Primitives mode: structural composition API (P is auto-injected)
                if run.primitives_code:
                    LUAU_SYSTEM_PROMPT += (
                        "\n\n"
                        "## PartPrimitives (use these to build connected structures)\n\n"
                        "`P` is already available inside every execute_luau call. "
                        "Do NOT require it, do NOT script_read PartPrimitives.\n\n"
                        "These create CONNECTED subassemblies, not isolated parts:\n"
                        "```lua\n"
                        "-- floor seats on ground\n"
                        "local floor = P.floor({20, 1, 20}, {name=\"Floor\", material=\"Concrete\"})\n"
                        "-- wall seats on floor, with real door gap\n"
                        "local wall = P.wall({20, 8, 1}, {name=\"FrontWall\", on=floor, material=\"Brick\",\n"
                        "    door={w=3, h=4, side=\"center\"}})\n"
                        "-- pitched roof seats on wall\n"
                        "local roof = P.roof({20, 4, 12}, {name=\"Roof\", on=wall, style=\"pitched\", material=\"WoodPlanks\"})\n"
                        "-- connected tail/branch chain (3 tapering segments, curving up)\n"
                        "local tail = P.limb({{4,3,3}, {3,2,2}, {2,1.5,1.5}}, {origin=body, angle=0, curve=15,\n"
                        "    name=\"Tail\", material=\"Slate\"})\n"
                        "-- stacked tower (3 levels, each on previous)\n"
                        "local tower = P.stack({{10,10,8}, {8,8,8}, {6,6,6}}, {name=\"Tower\", material=\"Slate\"})\n"
                        "-- simple block/cyl/ball/wedge also available\n"
                        "local pillar = P.cyl(1.5, 10, {name=\"Pillar\", on=floor, material=\"Wood\"})\n"
                        "```\n\n"
                        "Placement: `on=<part>` seats on top | `at={x,y,z}` absolute | `offset={x,y,z}` after placement | `rotation={rx,ry,rz}`.\n"
                        "Style: `name`, `color={r,g,b}`, `material` (string), `transparency`.\n"
                        "Wall: `door={w,h,side}` cuts real gap (side: left/right/center) | `direction=\"x\"|\"z\"` | `windows={{w,h,y,side}}`.\n"
                        "Roof: `style=\"pitched\"|\"flat\"` | `direction=\"x\"|\"z\"` ridge axis | `overhang=N`.\n"
                        "Limb: `origin=<part>` start point | `angle=N` upward degrees | `yaw=N` horizontal | `curve=N` per-segment bend.\n"
                        "Stack: `levels={{w,h,d},...}` each level auto-seated on previous.\n\n"
                        "Use P.wall for walls with doors, P.roof for roofs, P.limb for tails/legs/branches/necks, "
                        "P.stack for towers/buildings. Use P.block/cyl/ball/wedge for simple parts. "
                        "Chain primitives by passing the return value as `on=` to the next."
                    )
                messages.append({"role": "system", "content": LUAU_SYSTEM_PROMPT})
                messages.append({"role": "user", "content": ev.prompt_text})

                # 7. LLM tool-use loop
                llm_start = time.time()
                round_idx = 0
                LLM_CALL_TIMEOUT = 90  # per-call timeout (seconds)
                LLM_CALL_RETRIES = 2   # retries on per-call timeout
                _mcp_dead = False
                for round_idx in range(run.max_tool_rounds):
                    # Check if MCP connection is still alive before calling LLM
                    if m.tool_errors >= 2 and m.tool_errors == m.tool_calls:
                        logger.error(f"[{ev.scenario_name}] All {m.tool_errors} tool calls failed, MCP connection likely dead. Aborting.")
                        m.error = f"MCP connection dead after {m.tool_errors} consecutive tool failures"
                        break
                    if _mcp_dead:
                        logger.error(f"[{ev.scenario_name}] MCP dead, aborting LLM loop at round {round_idx}")
                        break
                    logger.info(f"[{ev.scenario_name}] LLM round {round_idx + 1}")
                    # Per-call timeout with retry (separate from eval timeout)
                    response = None
                    for call_attempt in range(LLM_CALL_RETRIES + 1):
                        try:
                            response = await asyncio.wait_for(
                                llm_chat(model, messages, openai_tools, temperature=run.temperature),
                                timeout=LLM_CALL_TIMEOUT,
                            )
                            break
                        except asyncio.TimeoutError:
                            if call_attempt < LLM_CALL_RETRIES:
                                logger.warning(f"[{ev.scenario_name}] LLM call timed out after {LLM_CALL_TIMEOUT}s (attempt {call_attempt+1}/{LLM_CALL_RETRIES+1}), retrying...")
                            else:
                                logger.error(f"[{ev.scenario_name}] LLM call timed out after {LLM_CALL_RETRIES+1} attempts of {LLM_CALL_TIMEOUT}s each")
                                raise
                    m.llm_calls += 1

                    usage = response.get("usage", {})
                    m.total_tokens_in += usage.get("prompt_tokens", 0)
                    m.total_tokens_out += usage.get("completion_tokens", 0)
                    m.max_context_tokens = max(m.max_context_tokens, usage.get("prompt_tokens", 0))

                    # Per-eval token cap guardrail
                    if m.total_tokens_in > run.max_tokens_per_eval:
                        logger.warning(f"[{ev.scenario_name}] Token cap exceeded: {m.total_tokens_in} > {run.max_tokens_per_eval}")
                        m.error = f"token_budget_exceeded: {m.total_tokens_in} tokens"
                        m.error_category = "token_budget_exceeded"
                        break

                    choice = response["choices"][0]
                    message = choice["message"]
                    messages.append(message)
                    finish = choice.get("finish_reason", "")

                    if finish == "tool_calls" and message.get("tool_calls"):
                        for tc in message["tool_calls"]:
                            m.tool_calls += 1
                            func = tc["function"]
                            tool_name = func["name"]
                            if tool_name not in m.tools_used:
                                m.tools_used.append(tool_name)
                            m.tool_call_sequence.append(tool_name)
                            # Count edit operations
                            if tool_name == "multi_edit":
                                m.edit_count += 1
                            try:
                                args = json.loads(func["arguments"])
                            except json.JSONDecodeError:
                                args = {}
                            # Helpers v2: inject H into every execute_luau so the model never
                            # script_reads SpatialHelpers or forgets require().
                            if run.helpers_code and tool_name == "execute_luau":
                                code = args.get("code", "") or ""
                                inject = "local H = require(game.ReplicatedStorage.SpatialHelpers)\n"
                                if code and "ReplicatedStorage.SpatialHelpers" not in code:
                                    args = dict(args)
                                    args["code"] = inject + code
                            # Primitives: inject P into every execute_luau
                            if run.primitives_code and tool_name == "execute_luau":
                                code = args.get("code", "") or ""
                                inject = "local P = require(game.ReplicatedStorage.PartPrimitives)\n"
                                if code and "ReplicatedStorage.PartPrimitives" not in code:
                                    args = dict(args)
                                    args["code"] = inject + code
                            # execute_luau that creates/modifies scripts counts as edit
                            if tool_name == "execute_luau":
                                code = args.get("code", "")
                                edit_markers = (
                                    "Instance.new", ".Source", "multi_edit",
                                    "H.block", "H.cyl", "H.ball", "H.wedge",
                                    "P.block", "P.cyl", "P.ball", "P.wedge",
                                    "P.wall", "P.roof", "P.limb", "P.stack", "P.floor",
                                )
                                if any(marker in code for marker in edit_markers):
                                    m.edit_count += 1
                            # Handle skill_view locally (not an MCP tool)
                            if tool_name == "skill_view" and run.skill_loader:
                                skill_name = args.get("name", "")
                                tool_out = run.skill_loader.get_skill(skill_name)
                                logger.info(f"[{ev.scenario_name}] skill_view({skill_name}) -> {len(tool_out)} chars")
                                if skill_name not in m.skills_used:
                                    m.skills_used.append(skill_name)
                            else:
                                try:
                                    result = await session.call_tool(func["name"], args)
                                    tool_out = get_tool_text(result)
                                    tool_is_err = is_tool_error(result, tool_out)
                                    track_tool_error(m, func["name"], tool_is_err)
                                    if tool_is_err:
                                        logger.warning(f"[{ev.scenario_name}] tool {func['name']} returned error: {tool_out[:200]}")
                                except Exception as e:
                                    err_str = str(e) or type(e).__name__
                                    logger.warning(f"[{ev.scenario_name}] tool {func['name']} failed: {err_str[:200]}")
                                    if "ClosedResource" in err_str or "BrokenResource" in err_str:
                                        # MCP connection is dead, no point retrying
                                        tool_out = f"Tool error: MCP connection closed: {e}"
                                        m.tool_errors += 1
                                        logger.error(f"[{ev.scenario_name}] MCP connection dead, aborting eval")
                                        _mcp_dead = True
                                        break
                                    # Retry once on transient errors
                                    try:
                                        result = await session.call_tool(func["name"], args)
                                        tool_out = get_tool_text(result)
                                        tool_is_err = is_tool_error(result, tool_out)
                                        track_tool_error(m, func["name"], tool_is_err)
                                        logger.info(f"[{ev.scenario_name}] tool {func['name']} retry OK (isError={tool_is_err})")
                                    except Exception as e2:
                                        tool_out = f"Tool error: {e2}"
                                        m.tool_errors += 1
                                        logger.warning(f"[{ev.scenario_name}] tool {func['name']} retry fail: {str(e2)[:200]}")

                            # Truncate tool results to prevent context bloat
                            if len(tool_out) > 4000:
                                tool_out = tool_out[:4000] + "\n... [truncated, full result in tool log]"
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tc["id"],
                                "content": tool_out,
                            })
                    else:
                        # LLM finished (stop, length, or content)
                        if message.get("content"):
                            m.final_response_text = str(message["content"])[:2000]
                        break

                m.llm_latency_ms = int((time.time() - llm_start) * 1000)
                m.rounds_used = round_idx + 1
                m.time_breakdown["llm_ms"] = m.llm_latency_ms

                # 9. Re-inject LoadedCode + EvalUtils (LLM may have wiped them)
                await harness_call_tool(session, "execute_luau", {"datamodel_type": "Edit", "code": ENSURE_LOADED_CODE}, m)

                # 10. Exit play mode if LLM left Studio in it
                try:
                    await session.call_tool("start_stop_play", {"is_start": False})
                    await asyncio.sleep(3)
                except Exception:
                    pass

                # 10a. Run StructuralFixer if enabled (after build, before screenshots)
                if run.fixer and run.fixer_code:
                    try:
                        fixer_lua = f"""
local NL = string.char(10)
local mod = Instance.new("ModuleScript")
mod.Name = "_StructuralFixer"
mod.Source = [==[{run.fixer_code}]==]
mod.Parent = game
local ok, Fixer = pcall(require, mod)
mod:Destroy()
if not ok then return "ERROR: " .. tostring(Fixer) end
local report = Fixer.fix()
local result = report.summary or "done"
for _, d in ipairs(report.details or {{}}) do
    result = result .. NL .. "  " .. d
end
return result
"""
                        fixer_result, _ = await harness_call_tool(
                            session, "execute_luau",
                            {"datamodel_type": "Edit", "code": fixer_lua}, m
                        )
                        fixer_text = get_tool_text(fixer_result) or ""
                        logger.info(f"  StructuralFixer: {fixer_text[:200]}")
                        m.fixer_report = fixer_text
                    except Exception as e:
                        logger.warning(f"  StructuralFixer failed: {e}")
                        m.fixer_report = f"FIXER_ERROR: {e}"

                # 10b. Run check_scene (edit mode) — gate before screenshots/judge
                # Skip entirely in --no-gate mode (human is the judge)
                if run.no_gate:
                    m.scene_passed = None
                    logger.info(f"  check_scene skipped (--no-gate)")
                else:
                    check_scene_lua = f"""
local evalMod = Instance.new("ModuleScript")
evalMod.Name = "_HarnessEvalCheck"
evalMod.Source = [==[{ev.script}]==]
evalMod.Parent = game
local ok, eval = pcall(require, evalMod)
evalMod:Destroy()
if not ok then return "false|PARSE_ERROR: " .. tostring(eval) end
if not eval.check_scene then return "true|NO_CHECK" end
local cok, cerr = pcall(eval.check_scene)
if cok then return "true|pass" else return "false|" .. tostring(cerr) end
"""
                    scene_result, _ = await harness_call_tool(session, "execute_luau", {"datamodel_type": "Edit", "code": check_scene_lua}, m)
                    scene_text = get_tool_text(scene_result) or "false|no_response"
                    m.scene_passed = scene_text.startswith("true")
                    if not m.scene_passed:
                        m.error = f"check_scene failed: {scene_text}"

                # 10b-screenshots. Capture screenshots EVEN IF gate failed, for diagnostic purposes.
                # Gate-failed evals still get screenshots but no judge scoring.
                if run.screenshots:
                    try:
                        if ev.screenshot_type == "ui":
                            await session.call_tool("start_stop_play", {"is_start": True})
                            await asyncio.sleep(3)
                            ss, _ = await harness_call_tool(session, "screen_capture", {"capture_id": ev.scenario_name}, m)
                            await session.call_tool("start_stop_play", {"is_start": False})
                            await asyncio.sleep(2)
                        else:
                            ss, _ = await harness_call_tool(session, "screen_capture", {"capture_id": ev.scenario_name}, m)
                        img_data = None
                        if ss and ss.content:
                            for c in ss.content:
                                if hasattr(c, 'data') and c.data:
                                    try: img_data = base64.b64decode(c.data); break
                                    except: pass
                                if hasattr(c, 'text') and c.text:
                                    clean = c.text.strip()
                                    if clean.startswith("data:"): clean = clean.split(",", 1)[1] if "," in clean else clean
                                    try: img_data = base64.b64decode(clean); break
                                    except: pass
                        if img_data and len(img_data) > 100:
                            ss_dir = Path(run.run_dir) / "screenshots"
                            ss_dir.mkdir(parents=True, exist_ok=True)
                            ss_path = ss_dir / f"{ev.scenario_name}.png"
                            ss_path.write_bytes(img_data)
                            m.screenshot_path = str(ss_path)
                            logger.debug(f"  Screenshot saved: {ss_path}")
                    except Exception as e:
                        logger.debug(f"  Screenshot failed: {e}")

                # 10c. Run check_game (play mode) via StudioTestService bridge
                if run.no_gate:
                    m.game_passed = None
                    logger.info(f"  check_game skipped (--no-gate)")
                elif m.scene_passed is not False:
                    if ev.check_game_empty:
                        m.game_passed = None
                        logger.info(f"  check_game skipped (empty body)")
                    else:
                        try:
                            game_text = await run_check_game_sts(session, ev, m)
                            if game_text is None:
                                m.game_passed = None
                                logger.info(f"  check_game skipped (bridge unavailable)")
                            elif game_text.startswith("skip"):
                                m.game_passed = None
                                logger.info(f"  check_game skipped")
                            else:
                                m.game_passed = game_text.startswith("true")
                                if not m.game_passed:
                                    m.error = f"check_game failed: {game_text}"
                        except Exception as e:
                            m.game_passed = False
                            m.error = f"Play mode error: {str(e) or type(e).__name__}"

                # In --no-gate mode, passed = True (everything captured for human review)
                if run.no_gate:
                    m.passed = True
                else:
                    m.passed = (m.scene_passed is True) and (m.game_passed is not False)

                # 11. Visual pipeline: screenshots + structure dump for ALL evals
                # Judge scoring only for gate-passed evals.
                _ss_start = time.time()

                # 11b. Visual bench: camera framing + multi-screenshot (all evals)
                if ev.screenshot_type:
                    try:
                        if ev.screenshot_type == "build":
                            bbox_lua = """
local parts = {}
for _, obj in ipairs(workspace:GetChildren()) do
    if obj:IsA("BasePart") and obj.Name ~= "Baseplate" and not obj:IsA("Terrain") and obj.Name ~= "SpawnLocation" then
        table.insert(parts, obj)
    elseif obj:IsA("Folder") or obj:IsA("Model") or obj:IsA("Configuration") then
        for _, d in ipairs(obj:GetDescendants()) do
            if d:IsA("BasePart") and not d:IsA("Terrain") then table.insert(parts, d) end
        end
    end
end
if #parts == 0 then return "0|0|0|0|0" end
local minX, maxX, minY, maxY, minZ, maxZ = math.huge, -math.huge, math.huge, -math.huge, math.huge, -math.huge
for _, p in ipairs(parts) do
    minX = math.min(minX, p.Position.X - p.Size.X/2)
    maxX = math.max(maxX, p.Position.X + p.Size.X/2)
    minY = math.min(minY, p.Position.Y - p.Size.Y/2)
    maxY = math.max(maxY, p.Position.Y + p.Size.Y/2)
    minZ = math.min(minZ, p.Position.Z - p.Size.Z/2)
    maxZ = math.max(maxZ, p.Position.Z + p.Size.Z/2)
end
local cx = (minX + maxX) / 2
local cy = (minY + maxY) / 2
local cz = (minZ + maxZ) / 2
local maxDim = math.max(maxX - minX, maxY - minY, maxZ - minZ)
if maxDim < 1 then maxDim = 10 end
return string.format("%.1f|%.1f|%.1f|%.1f|%d", cx, cy, cz, maxDim, #parts)
"""
                            _, bbox_text = await harness_call_tool(
                                session, "execute_luau",
                                {"datamodel_type": "Edit", "code": bbox_lua}, m
                            )
                            bx = (bbox_text or "").split("|")
                            if len(bx) >= 4 and int(bx[4]) > 0:
                                cx, cy, cz, maxDim = float(bx[0]), float(bx[1]), float(bx[2]), float(bx[3])
                                await harness_call_tool(session, "execute_luau",
                                    {"datamodel_type": "Edit", "code": 'workspace.CurrentCamera.CameraType = Enum.CameraType.Scriptable'}, m)
                                await asyncio.sleep(0.5)
                                angles = [
                                    f'workspace.CurrentCamera.CFrame = CFrame.lookAt(Vector3.new({cx + maxDim*0.8}, {cy + maxDim*0.4}, {cz + maxDim*0.8}), Vector3.new({cx}, {cy}, {cz}))',
                                    f'workspace.CurrentCamera.CFrame = CFrame.lookAt(Vector3.new({cx - maxDim*0.8}, {cy + maxDim*0.4}, {cz + maxDim*0.8}), Vector3.new({cx}, {cy}, {cz}))',
                                    f'workspace.CurrentCamera.CFrame = CFrame.lookAt(Vector3.new({cx}, {cy + maxDim*1.2}, {cz + 0.1}), Vector3.new({cx}, {cy}, {cz}))',
                                ]
                                for ai, cam_lua in enumerate(angles):
                                    await harness_call_tool(session, "execute_luau",
                                        {"datamodel_type": "Edit", "code": cam_lua}, m)
                                    await asyncio.sleep(1)
                                    ss, _ = await harness_call_tool(session, "screen_capture",
                                        {"capture_id": f"{ev.scenario_name}_a{ai}"}, m)
                                    img_data = None
                                    if ss and ss.content:
                                        for c in ss.content:
                                            if hasattr(c, 'data') and c.data:
                                                try: img_data = base64.b64decode(c.data); break
                                                except: pass
                                            if hasattr(c, 'text') and c.text:
                                                clean = c.text.strip()
                                                if clean.startswith("data:"): clean = clean.split(",", 1)[1] if "," in clean else clean
                                                try: img_data = base64.b64decode(clean); break
                                                except: pass
                                    if img_data and len(img_data) > 100:
                                        ss_dir = Path(run.run_dir) / "screenshots"
                                        ss_dir.mkdir(parents=True, exist_ok=True)
                                        ss_path = ss_dir / f"{ev.scenario_name}_a{ai}.png"
                                        ss_path.write_bytes(img_data)
                                        m.screenshot_paths.append(str(ss_path))
                            else:
                                logger.info(f"  No parts found for bbox, skipping multi-angle screenshots")
                        elif ev.screenshot_type == "ui":
                            if m.screenshot_path:
                                m.screenshot_paths.append(m.screenshot_path)
                    except Exception as e:
                        logger.warning(f"  Visual bench screenshot failed: {e}")

                m.time_breakdown["screenshot_ms"] = int((time.time() - _ss_start) * 1000)

                # 11c. Structure dump (all evals)
                if ev.screenshot_type:
                    try:
                        if ev.screenshot_type == "ui":
                            dump_lua = """
local function dumpTree(parent, depth)
    local NL = string.char(10)
    local result = ""
    for _, child in ipairs(parent:GetChildren()) do
        local props = ""
        if child:IsA("GuiObject") then
            props = string.format("Size=%s Pos=%s ZIndex=%d Transp=%.2f", tostring(child.Size), tostring(child.Position), child.ZIndex, child.BackgroundTransparency)
        end
        if child:IsA("TextLabel") or child:IsA("TextButton") then
            props = props .. string.format(" Text='%s' Font=%s TextSize=%d TextColor=%s", child.Text, tostring(child.Font), child.TextSize, tostring(child.TextColor3))
        end
        if child:IsA("Frame") then
            props = props .. " Bg=" .. tostring(child.BackgroundColor3)
        end
        for _, d in ipairs(child:GetChildren()) do
            if d:IsA("UICorner") then
                props = props .. string.format(" UICorner=%s", tostring(d.CornerRadius))
            elseif d:IsA("UIStroke") then
                props = props .. string.format(" UIStroke(color=%s thickness=%d)", tostring(d.Color), d.Thickness)
            end
        end
        result = result .. string.rep("  ", depth) .. child.ClassName .. ":" .. child.Name .. " " .. props .. NL
        result = result .. dumpTree(child, depth + 1)
    end
    return result
end
return dumpTree(game:GetService("StarterGui"), 0)
"""
                        else:
                            dump_lua = """
local parts = {}
local NL = string.char(10)
local function collect(parent, depth)
    for _, obj in ipairs(parent:GetChildren()) do
        if obj:IsA("BasePart") and obj.Name ~= "Baseplate" and not obj:IsA("Terrain") and obj.Name ~= "SpawnLocation" then
            table.insert(parts, obj)
        end
        if obj:IsA("Folder") or obj:IsA("Model") or obj:IsA("Configuration") or obj:IsA("Accessory") then
            collect(obj, depth + 1)
        end
    end
end
collect(workspace, 0)
local result = ""
for _, p in ipairs(parts) do
    local parentName = p.Parent and p.Parent.Name or "?"
    local mat = tostring(p.Material)
    result = result .. string.format("%s:%s parent=%s Pos=(%.1f,%.1f,%.1f) Size=(%.1f,%.1f,%.1f) Mat=%s Anchored=%s" .. NL,
        p.ClassName, p.Name, parentName, p.Position.X, p.Position.Y, p.Position.Z,
        p.Size.X, p.Size.Y, p.Size.Z, mat, tostring(p.Anchored))
end

-- Structural soundness checks
local floating = {}
local overlaps = {}
local groundContact = false
for i, p in ipairs(parts) do
    local bottom = p.Position.Y - p.Size.Y/2
    if bottom <= 0.5 then groundContact = true end
    if bottom > 1.0 then
        local supported = false
        for _, q in ipairs(parts) do
            if q ~= p then
                local qtop = q.Position.Y + q.Size.Y/2
                if math.abs(qtop - bottom) < 1.5 then
                    local dx = math.abs(p.Position.X - q.Position.X)
                    local dz = math.abs(p.Position.Z - q.Position.Z)
                    if dx < (p.Size.X + q.Size.X)/2 and dz < (p.Size.Z + q.Size.Z)/2 then
                        supported = true
                        break
                    end
                end
            end
        end
        if not supported then
            table.insert(floating, p.Name .. "(y=" .. string.format("%.1f", bottom) .. ")")
        end
    end
    for j = i+1, #parts do
        local q = parts[j]
        local dx = math.abs(p.Position.X - q.Position.X)
        local dy = math.abs(p.Position.Y - q.Position.Y)
        local dz = math.abs(p.Position.Z - q.Position.Z)
        if dx < (p.Size.X + q.Size.X)/2 - 0.1 and
           dy < (p.Size.Y + q.Size.Y)/2 - 0.1 and
           dz < (p.Size.Z + q.Size.Z)/2 - 0.1 then
            table.insert(overlaps, p.Name .. " <-> " .. q.Name)
        end
    end
end
local function summarize(items, limit)
    local shown = {}
    local count = math.min(#items, limit)
    for i = 1, count do table.insert(shown, items[i]) end
    if #items > limit then
        table.insert(shown, "... +" .. tostring(#items - limit) .. " more")
    end
    return table.concat(shown, ", ")
end
local flags = "--- structural_flags ---" .. NL
flags = flags .. "floating_parts:" .. #floating .. NL
if #floating > 0 then flags = flags .. "  " .. summarize(floating, 50) .. NL end
flags = flags .. "overlaps:" .. #overlaps .. NL
if #overlaps > 0 then flags = flags .. "  " .. summarize(overlaps, 50) .. NL end
flags = flags .. "ground_contact:" .. tostring(groundContact) .. NL
flags = flags .. "total_parts:" .. #parts .. NL
return flags .. "parts:" .. #parts .. NL .. result
"""
                        dump_text = ""
                        for dump_attempt in range(3):
                            _, dump_text = await harness_call_tool(
                                session, "execute_luau",
                                {"datamodel_type": "Edit", "code": dump_lua}, m
                            )
                            if dump_text and "Failed to parse" not in dump_text:
                                break
                            logger.warning(f"  Structure dump attempt {dump_attempt+1} failed, retrying...")
                            await asyncio.sleep(1)
                        m.structure_dump = (dump_text or "")[:15000]
                    except Exception as e:
                        logger.warning(f"  Structure dump failed: {e}")

                # 11d. Capture created scripts (all evals)
                if ev.screenshot_type:
                    try:
                        scripts_lua = """
local NL = string.char(10)
local scripts = {}
for _, obj in ipairs(game:GetDescendants()) do
    if obj:IsA("Script") or obj:IsA("LocalScript") or obj:IsA("ModuleScript") then
        if obj.Source and #obj.Source > 10 then
            scripts[obj:GetFullName()] = obj.Source
        end
    end
end
local StarterPlayer = game:GetService("StarterPlayer")
if StarterPlayer then
    for _, d in ipairs(StarterPlayer:GetDescendants()) do
        if (d:IsA("Script") or d:IsA("LocalScript") or d:IsA("ModuleScript")) and d.Source and #d.Source > 10 then
            scripts[d:GetFullName()] = d.Source
        end
    end
end
local count = 0
local result = ""
for name, src in pairs(scripts) do
    count = count + 1
    if count <= 10 then
        result = result .. "=== " .. name .. " ===" .. NL .. src:sub(1, 500) .. NL .. NL
    end
end
return tostring(count) .. "|" .. result
"""
                        scripts_text = ""
                        for script_attempt in range(3):
                            _, scripts_text = await harness_call_tool(
                                session, "execute_luau",
                                {"datamodel_type": "Edit", "code": scripts_lua}, m
                            )
                            if scripts_text and "Failed to parse" not in scripts_text:
                                break
                            logger.warning(f"  Script capture attempt {script_attempt+1} failed, retrying...")
                            await asyncio.sleep(1)
                        if scripts_text and "|" in scripts_text:
                            parts = scripts_text.split("|", 1)
                            m.created_scripts["_count"] = int(parts[0])
                            m.created_scripts["_sources"] = parts[1][:10000]
                    except Exception as e:
                        logger.warning(f"  Script capture failed: {e}")

                # 11e. Judge scoring — ONLY for gate-passed evals
                if m.scene_passed is not False and run.judge_enabled and run.judge and ev.judge_rubric:
                    if m.screenshot_paths:
                        try:
                            primary_idx = {"front": 0, "side": 1, "top": 2}.get(ev.screenshot_primary, 0)
                            if primary_idx < len(m.screenshot_paths):
                                judge_screenshots = [m.screenshot_paths[primary_idx]]
                            else:
                                judge_screenshots = m.screenshot_paths[:1]
                            judge_result = await run.judge.score(
                                task_prompt=ev.prompt_text,
                                rubric=ev.judge_rubric,
                                screenshots=judge_screenshots,
                                structure_dump=m.structure_dump or "",
                            )
                            m.judge_scores = judge_result.get("scores", {})
                            m.judge_overall = judge_result.get("overall")
                            m.judge_reasoning = judge_result.get("reasoning", "")
                            m.judge_issues = judge_result.get("issues", [])
                            logger.info(f"  Judge: overall={m.judge_overall} scores={m.judge_scores}")
                        except Exception as e:
                            logger.warning(f"  Judge scoring failed: {e}")

    except asyncio.TimeoutError:
        m.error = f"Eval timed out after {run.eval_timeout}s"
        m.error_category = "timeout"
        logger.error(f"[{ev.scenario_name}] Eval timed out after {run.eval_timeout}s")
    except Exception as e:
        # Unwrap ExceptionGroup / TaskGroup to get the actual sub-exception
        err_msg = str(e)
        if hasattr(e, 'exceptions') and e.exceptions:
            err_msg = str(e.exceptions[0])
        if not err_msg:
            err_msg = type(e).__name__
        m.error = f"Fatal: {err_msg}"
        logger.error(f"[{ev.scenario_name}] Fatal: {err_msg}")
        if hasattr(e, "exceptions"):
            for i, sub in enumerate(e.exceptions):
                logger.error(f"[{ev.scenario_name}]   sub[{i}]: {type(sub).__name__}: {str(sub)[:300]}")
    finally:
        kill_studio()

    m.total_time_ms = int((time.time() - t0) * 1000)

    # Categorize error if present
    if m.error and not m.error_category:
        m.error_category = categorize_error(m.error)

    return m


async def run_single_eval(
    ev: EvalFile,
    model: ModelConfig,
    studio: StudioConfig,
    run: RunConfig,
) -> EvalMetrics:
    """Run a single eval with timeout wrapping."""
    m = EvalMetrics(scenario=ev.scenario_name, place=ev.place)
    try:
        result = await asyncio.wait_for(
            _run_single_eval_inner(ev, model, studio, run),
            timeout=run.eval_timeout,
        )
        return result
    except asyncio.TimeoutError:
        m.error = "Eval timed out"
        m.error_category = "timeout"
        m.total_time_ms = run.eval_timeout * 1000
        logger.error(f"[{ev.scenario_name}] Eval timed out after {run.eval_timeout}s")
        return m


# �"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?
# Aggregation
# �"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?


def _compute_tool_error_rates(results) -> dict:
    """Compute per-tool-type error rates from eval results."""
    all_tool_names = set()
    for r in results:
        all_tool_names.update(r.tool_calls_by_type.keys())
    rates = {}
    for name in sorted(all_tool_names):
        total_calls = sum(r.tool_calls_by_type.get(name, 0) for r in results)
        total_errors = sum(r.tool_errors_by_type.get(name, 0) for r in results)
        if total_calls > 0:
            rates[name] = round(total_errors / total_calls * 100, 2)
    return rates


def aggregate_results(results: list[EvalMetrics], pass_n: int = 1) -> dict:
    total = len(results)
    passed = sum(1 for r in results if r.passed)
    errors = sum(1 for r in results if r.error and "Fatal" in (r.error or ""))
    tool_errors = sum(r.tool_errors for r in results)
    total_tool_calls = sum(r.tool_calls for r in results)

    # Error breakdown by category
    error_breakdown = {}
    for r in results:
        cat = r.error_category or "none"
        error_breakdown[cat] = error_breakdown.get(cat, 0) + 1

    summary = {
        "total_evals": total,
        "passed": passed,
        "pass_rate": round(passed / total * 100, 2) if total else 0,
        "fatal_errors": errors,
        "tool_error_rate": round(tool_errors / total_tool_calls * 100, 2) if total_tool_calls else 0,
        "tool_errors_by_type": _compute_tool_error_rates(results),
        "avg_llm_calls": round(sum(r.llm_calls for r in results) / total, 1) if total else 0,
        "avg_tokens_in": round(sum(r.total_tokens_in for r in results) / total) if total else 0,
        "avg_tokens_out": round(sum(r.total_tokens_out for r in results) / total) if total else 0,
        "avg_latency_ms": round(sum(r.llm_latency_ms for r in results) / total) if total else 0,
        "avg_total_time_ms": round(sum(r.total_time_ms for r in results) / total) if total else 0,
        "total_time_ms": sum(r.total_time_ms for r in results),
        "avg_edit_count": round(sum(r.edit_count for r in results) / total, 1) if total else 0,
        "avg_max_context_tokens": round(sum(r.max_context_tokens for r in results) / total) if total else 0,
        "judge_evals": sum(1 for r in results if r.judge_scores is not None),
        "avg_judge_overall": round(sum(r.judge_overall for r in results if r.judge_overall) / max(1, sum(1 for r in results if r.judge_overall)), 2) if any(r.judge_overall for r in results) else None,
        "avg_judge_correctness": round(sum(r.judge_scores.get("correctness", 0) for r in results if r.judge_scores) / max(1, sum(1 for r in results if r.judge_scores)), 2) if any(r.judge_scores for r in results) else None,
        "avg_judge_layout": round(sum(r.judge_scores.get("layout", 0) for r in results if r.judge_scores) / max(1, sum(1 for r in results if r.judge_scores)), 2) if any(r.judge_scores for r in results) else None,
        "avg_judge_aesthetics": round(sum(r.judge_scores.get("aesthetics", 0) for r in results if r.judge_scores) / max(1, sum(1 for r in results if r.judge_scores)), 2) if any(r.judge_scores for r in results) else None,
        "avg_judge_completeness": round(sum(r.judge_scores.get("completeness", 0) for r in results if r.judge_scores) / max(1, sum(1 for r in results if r.judge_scores)), 2) if any(r.judge_scores for r in results) else None,
        "avg_tool_call_sequence_len": round(sum(len(r.tool_call_sequence) for r in results) / total, 1) if total else 0,
        "avg_created_scripts": round(sum(r.created_scripts.get("_count", 0) for r in results) / total, 1) if total else 0,
        "avg_time_llm": round(sum(r.time_breakdown.get("llm_ms", 0) for r in results) / total) if total else 0,
        "avg_time_screenshot": round(sum(r.time_breakdown.get("screenshot_ms", 0) for r in results) / total) if total else 0,
        "error_breakdown": error_breakdown,
    }

    # Harness tool errors (separate from LLM tool errors)
    harness_tool_calls = sum(r.harness_tool_calls for r in results)
    harness_tool_errors = sum(r.harness_tool_errors for r in results)
    if harness_tool_calls > 0:
        summary["harness_tool_error_rate"] = round(harness_tool_errors / harness_tool_calls * 100, 2)
        summary["harness_tool_errors_by_type"] = {}
        all_harness_names = set()
        for r in results:
            all_harness_names.update(r.harness_tool_calls_by_type.keys())
        for name in sorted(all_harness_names):
            tc = sum(r.harness_tool_calls_by_type.get(name, 0) for r in results)
            te = sum(r.harness_tool_errors_by_type.get(name, 0) for r in results)
            summary["harness_tool_errors_by_type"][name] = round(te / tc * 100, 2) if tc > 0 else 0

    if pass_n == 5:
        summary["pass_at_5"] = round(passed / total * 100, 2) if total else 0  # >=1/5
        summary["cons_at_5"] = round(sum(1 for r in results if r.passed_cons) / total * 100, 2) if total else 0  # >=3/5
        summary["all_at_5"] = round(sum(1 for r in results if r.passed_all) / total * 100, 2) if total else 0  # 5/5

    return summary


# �"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?
# CLI
# �"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?�"?

def parse_args():
    p = argparse.ArgumentParser(description="OpenGameEval Local Harness")
    p.add_argument("--evals-dir", required=True, help="Path to Evals/ directory")
    p.add_argument("--debug-evals-dir", default=None, help="Path to DebugEvals/ directory (optional, for debug benchmark)")
    p.add_argument("--judge", action="store_true", default=False, help="Enable visual judge scoring")
    p.add_argument("--judge-model", default=None, help="Judge model name (default: JUDGE_MODEL env)")
    p.add_argument("--judge-api-base", default=None, help="Judge API base (default: JUDGE_API_BASE env)")
    p.add_argument("--judge-api-key", default=None, help="Judge API key (default: JUDGE_API_KEY env)")
    p.add_argument("--places-dir", required=True, help="Path to Places/ directory")
    p.add_argument("--studio-exe", required=True, help="Path to RobloxStudioBeta.exe")
    p.add_argument("--mcp-bat", required=True, help="Path to mcp.bat")
    p.add_argument("--model-name", required=True, help="Model name for API")
    p.add_argument("--api-base", default=None, help="OpenAI-compatible API base URL (or set LLM_API_BASE env)")
    p.add_argument("--api-key", default=None, help="API key (or set LLM_API_KEY env)")
    p.add_argument("--skills-dir", default=None, help="Path to skills source dir for skills mode (default: roblox-brain/skills)")
    p.add_argument("--skills", action="store_true", help="--skills mode: model gets skill index + skill_view tool, loads skills itself")
    p.add_argument("--solver", action="store_true", help="Solver mode: upload SpatialSolver.lua to ReplicatedStorage + inject spec vocabulary into system prompt")
    p.add_argument("--solver-path", default=None, help="Path to SpatialSolver.lua (default: ../spatial-solver/SpatialSolver.lua)")
    p.add_argument("--pass-n", type=int, default=1, choices=[1, 5], help="Pass@1 or Pass@5")
    p.add_argument("--max-rounds", type=int, default=25, help="Max LLM tool-use rounds per eval")
    p.add_argument("--startup-wait", type=int, default=45, help="Seconds to wait for Studio")
    p.add_argument("--output-dir", default="results", help="Output directory")
    p.add_argument("--screenshots", action="store_true", help="Capture screenshots")
    p.add_argument("--verbose", action="store_true", help="Verbose logging")
    p.add_argument("--eval-filter", default=None, help="Regex filter for eval scenario names")
    p.add_argument("--eval-timeout", type=int, default=600, help="Per-eval timeout in seconds")
    p.add_argument("--no-gate", action="store_true", help="Skip check_scene gate entirely. Screenshots + structure dump still captured. Use when human is the judge.")
    p.add_argument("--fixer", action="store_true", help="Run legacy/StructuralFixer.lua after model build, before screenshots. Fixes floating/overlapping parts.")
    p.add_argument("--helpers", action="store_true", help="Upload legacy/SpatialHelpers.lua to ReplicatedStorage + inject helper API into system prompt. Model calls helper functions instead of computing coordinates.")
    p.add_argument("--helpers-path", default=None, help="Path to SpatialHelpers.lua (default: ./legacy/SpatialHelpers.lua)")
    p.add_argument("--primitives", action="store_true", help="Upload PartPrimitives.lua to ReplicatedStorage + inject composition API into system prompt. Model calls P.wall/P.roof/P.limb/P.stack for connected structures.")
    p.add_argument("--primitives-path", default=None, help="Path to PartPrimitives.lua (default: ./PartPrimitives.lua)")
    p.add_argument("--temperature", type=float, default=0, help="LLM temperature (default 0 for reproducibility)")
    p.add_argument("--max-tokens-per-eval", type=int, default=500000, help="Max total input tokens per eval before abort")
    return p.parse_args()


async def main():
    load_dotenv()
    args = parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Resolve API base
    api_base = args.api_base or os.getenv("LLM_API_BASE")
    if not api_base:
        print("Error: --api-base or LLM_API_BASE env required")
        sys.exit(1)

    # Resolve API key
    api_key = args.api_key or os.getenv("LLM_API_KEY")
    if not api_key:
        print("Error: --api-key or LLM_API_KEY env required")
        sys.exit(1)

    # Load skills mode
    skill_loader = None
    skill_router = None
    skills_index = None
    if args.skills:
        skills_source = args.skills_dir or str(Path(__file__).parent.parent / "roblox-brain" / "skills")
        skill_loader = SkillLoader(skills_source)
        logger.info(f"Loaded skill loader ({len(skill_loader.skills)} skills from {skills_source})")
        skill_router = None
        if SkillRouter is not None:
            try:
                skill_router = SkillRouter(skills_source)
                logger.info(f'Loaded skill router ({len(skill_router.skills)} skills)')
            except Exception as e:
                logger.warning(f'Skill router failed to load: {e}')
        index_path = Path(__file__).parent / "skills_index.txt"
        if index_path.exists():
            skills_index = index_path.read_text(encoding="utf-8")
        else:
            logger.warning(f"skills_index.txt not found at {index_path}")

    model = ModelConfig(
        name=args.model_name,
        api_base=api_base.rstrip("/"),
        api_key=api_key,
    )
    studio = StudioConfig(
        exe_path=args.studio_exe,
        mcp_path=args.mcp_bat,
        startup_wait=args.startup_wait,
    )
    # Visual judge setup
    judge = None
    judge_enabled = False
    if args.judge:
        jm = args.judge_model or os.getenv("JUDGE_MODEL")
        jb = args.judge_api_base or os.getenv("JUDGE_API_BASE")
        jk = args.judge_api_key or os.getenv("JUDGE_API_KEY")
        if jm and jb and jk and VisualJudge:
            judge = VisualJudge(jm, jb, jk)
            judge_enabled = True
            logger.info(f"Visual judge enabled: model={jm}")
            # Startup validation ping: send a 1x1 pixel to verify the judge API works
            try:
                import tempfile as _tf
                _tiny_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82'
                _tf_path = Path(_tf.gettempdir()) / "_judge_ping.png"
                _tf_path.write_bytes(_tiny_png)
                await judge.score(
                    task_prompt="test ping",
                    rubric={"correctness": "test"},
                    screenshots=[str(_tf_path)],
                    structure_dump="",
                )
                _tf_path.unlink(missing_ok=True)
                logger.info("Judge validation ping successful")
            except Exception as e:
                logger.error(f"Judge validation ping FAILED: {e}")
                print(f"ERROR: Judge API validation failed: {e}")
                print("Fix judge configuration before running evals. Aborting.")
                sys.exit(1)
        else:
            logger.warning("--judge requested but JUDGE_MODEL/JUDGE_API_BASE/JUDGE_API_KEY not configured")

    run = RunConfig(
        evals_dir=args.evals_dir,
        places_dir=args.places_dir,
        max_tool_rounds=args.max_rounds,
        pass_n=args.pass_n,
        output_dir=args.output_dir,
        screenshots=True,
        verbose=args.verbose,
        eval_timeout=args.eval_timeout,
        skill_loader=skill_loader,
        skill_router=skill_router,
        skills_index=skills_index,
        judge=judge,
        judge_enabled=judge_enabled,
        temperature=args.temperature,
        max_tokens_per_eval=args.max_tokens_per_eval,
        no_gate=args.no_gate,
        fixer=args.fixer,
    )

    # Fixer mode: load StructuralFixer.lua
    if args.fixer:
        fixer_path = Path(__file__).parent / "legacy" / "StructuralFixer.lua"
        if not fixer_path.exists():
            print(f"Error: StructuralFixer.lua not found at {fixer_path}")
            sys.exit(1)
        run.fixer_code = fixer_path.read_text(encoding="utf-8")
        logger.info(f"StructuralFixer enabled: {len(run.fixer_code)} chars")

    # Helpers mode: load SpatialHelpers.lua
    if args.helpers:
        helpers_path = Path(args.helpers_path) if args.helpers_path else (Path(__file__).parent / "legacy" / "SpatialHelpers.lua")
        if not helpers_path.exists():
            print(f"Error: SpatialHelpers.lua not found at {helpers_path}")
            sys.exit(1)
        run.helpers_code = helpers_path.read_text(encoding="utf-8")
        logger.info(f"SpatialHelpers enabled: {len(run.helpers_code)} chars from {helpers_path}")

    # Primitives mode: load PartPrimitives.lua
    if args.primitives:
        primitives_path = Path(args.primitives_path) if args.primitives_path else (Path(__file__).parent / "PartPrimitives.lua")
        if not primitives_path.exists():
            print(f"Error: PartPrimitives.lua not found at {primitives_path}")
            sys.exit(1)
        run.primitives_code = primitives_path.read_text(encoding="utf-8")
        logger.info(f"PartPrimitives enabled: {len(run.primitives_code)} chars from {primitives_path}")

    # Solver mode: load SpatialSolver.lua + build spec vocabulary prompt
    solver_code = None
    solver_enabled = args.solver
    if solver_enabled:
        solver_path = args.solver_path or str(Path(__file__).parent.parent / "spatial-solver" / "SpatialSolver.lua")
        solver_path = Path(solver_path)
        if not solver_path.exists():
            print(f"Error: SpatialSolver.lua not found at {solver_path}")
            sys.exit(1)
        solver_code = solver_path.read_text(encoding="utf-8")
        run.solver_code = solver_code
        logger.info(f"Solver mode enabled: {len(solver_code)} chars from {solver_path}")

    # Generate run directory: {mode}_{date}_{time}
    if skill_loader:
        mode = "skills"
    elif solver_enabled:
        mode = "solver"
    elif args.helpers:
        mode = "helpers"
    elif args.primitives:
        mode = "primitives"
    else:
        mode = "vanilla"
    if args.fixer:
        mode += "_fixer"
    run_id = f"{mode}_{datetime.now().strftime('%m%d_%H%M')}"
    run_dir = f"{args.output_dir}/{run_id}"
    Path(run_dir).mkdir(parents=True, exist_ok=True)
    Path(run_dir, "screenshots").mkdir(parents=True, exist_ok=True)
    run.run_dir = run_dir
    logger.info(f"Run directory: {run_dir}")

    run_config = {
        "pass_n": run.pass_n,
        "max_rounds": run.max_tool_rounds,
        "eval_timeout": run.eval_timeout,
        "screenshots": run.screenshots,
        "temperature": run.temperature,
        "max_tokens_per_eval": run.max_tokens_per_eval,
        "no_gate": run.no_gate,
        "helpers": args.helpers,
        "primitives": args.primitives,
        "solver": solver_enabled,
        "fixer": args.fixer,
        "eval_filter": args.eval_filter,
        "evals_dir": str(Path(args.evals_dir).resolve()),
        "places_dir": str(Path(args.places_dir).resolve()),
    }

    # Parse eval files
    eval_files = sorted(Path(args.evals_dir).rglob("*.lua"))
    if not eval_files:
        print(f"No .lua files found in {args.evals_dir}")
        sys.exit(1)

    evals = [parse_eval(str(f)) for f in eval_files]

    # Apply filter
    if args.eval_filter:
        pattern = re.compile(args.eval_filter)
        evals = [e for e in evals if pattern.search(e.scenario_name)]

    logger.info(f"Loaded {len(evals)} evals")

    # Create output dir
    Path(args.output_dir).mkdir(parents=True, exist_ok=True)

    # Save run manifest
    manifest = {
        "run_id": run_id,
        "model": model.name,
        "config": run_config,
        "start_time": datetime.now().isoformat(),
        "mode": mode,
    }
    if skill_loader:
        manifest["skills_mode"] = "skills"
        manifest["skills_source"] = str(skill_loader.source)
    elif solver_enabled:
        manifest["skills_mode"] = "solver"
    elif args.helpers:
        manifest["skills_mode"] = "helpers"
    elif args.primitives:
        manifest["skills_mode"] = "primitives"
    else:
        manifest["skills_mode"] = "vanilla"
    if judge_enabled:
        manifest["judge_enabled"] = True
        manifest["judge_model"] = args.judge_model or os.getenv("JUDGE_MODEL", "")
    manifest_path = Path(run_dir) / "run_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    # Helper: run a set of evals
    async def run_eval_set(evals_list, label):
        results = []

        for i, ev in enumerate(evals_list):
            logger.info(f"=== [{label}] [{i+1}/{len(evals_list)}] {ev.scenario_name} ===")

            run_results = []
            for attempt in range(run.pass_n):
                logger.info(f"  Attempt {attempt + 1}/{run.pass_n}")
                result = await run_single_eval(ev, model, studio, run)
                run_results.append(result)

                # Retry on transient errors or eval-level timeouts (one retry only).
                # Don't retry check_game timeouts — those are model limitations, not transient.
                # Retry loop for transient errors (connection deaths, etc.)
                max_retries = 2
                for _retry_idx in range(max_retries):
                    should_retry = result.error_category == "transient_error"
                    if result.error_category == "timeout" and not (result.error and "check_game" in result.error):
                        should_retry = True
                    if not should_retry:
                        break
                    result.retried = True
                    logger.info(f"  Transient error, retrying eval (attempt {_retry_idx+1}/{max_retries})...")
                    kill_studio()
                    await asyncio.sleep(3)
                    retry_result = await run_single_eval(ev, model, studio, run)
                    retry_result.retried = True
                    run_results[-1] = retry_result
                    result = retry_result

                status = "PASS" if result.passed else "FAIL"
                skills_tag = f" skills={result.skills_used}" if result.skills_used else ""
                logger.info(
                    f"  {status} | tokens_in={result.total_tokens_in} "
                    f"tokens_out={result.total_tokens_out} "
                    f"latency={fmt_time(result.llm_latency_ms)} "
                    f"total={fmt_time(result.total_time_ms)} "
                    f"tools={result.tool_calls} err={result.tool_errors} "
                    f"edits={result.edit_count} ctx={result.max_context_tokens} "
                    f"cat={result.error_category}{skills_tag}"
                )
                if result.error:
                    logger.info(f"  Error: {result.error}")

            if run.pass_n == 5:
                pass_count = sum(1 for r in run_results if r.passed)
                best = run_results[0]
                best.passed = pass_count >= 1
                best.passed_cons = pass_count >= 3
                best.passed_all = pass_count == 5
                results.append(best)
            else:
                results.append(run_results[0])

            # Incremental save: write results.json after each eval
            try:
                inc_summary = aggregate_results(results, run.pass_n)
                inc_output = {
                    "summary": inc_summary,
                    "model": {"name": model.name, "api_base": model.api_base},
                    "config": run_config,
                    "mode": mode,
                    "evals": [asdict(r) for r in results],
                }
                inc_path = Path(run.run_dir) / "results.json"
                inc_path.write_text(json.dumps(inc_output, indent=2))
            except Exception as e:
                logger.warning(f"Incremental save failed: {e}")

        return results

    # Run expanded evals
    all_results = await run_eval_set(evals, "EXPANDED")

    # Optionally run debug evals
    debug_results = None
    if args.debug_evals_dir:
        debug_dir = Path(args.debug_evals_dir)
        debug_files = sorted(debug_dir.glob("*.lua"))
        if debug_files:
            debug_evals = [parse_eval(str(f)) for f in debug_files]
            if args.eval_filter:
                pattern = re.compile(args.eval_filter)
                debug_evals = [e for e in debug_evals if pattern.search(e.scenario_name)]
            logger.info(f"Loaded {len(debug_evals)} debug evals")
            debug_results = await run_eval_set(debug_evals, "DEBUG")

    # Save results
    results_path = Path(run_dir) / "results.json"
    summary = aggregate_results(all_results, run.pass_n)
    output = {
        "summary": summary,
        "model": {"name": model.name, "api_base": model.api_base},
        "config": run_config,
        "mode": mode,
        "evals": [asdict(r) for r in all_results],
    }

    debug_summary = None
    if debug_results:
        debug_summary = aggregate_results(debug_results, run.pass_n)
        output["debug_summary"] = debug_summary
        output["debug_evals"] = [asdict(r) for r in debug_results]

    results_path.write_text(json.dumps(output, indent=2))
    logger.info(f"Results saved to {results_path}")

    # Print summary
    def print_summary(label, summ, pass_n):
        print(f"\n  [{label}]")
        if pass_n == 5:
            print(f"    Pass@1: {summ['pass_rate']}% ({summ['passed']}/{summ['total_evals']})")
            print(f"    Pass@5: {summ['pass_at_5']}%")
            print(f"    Cons@5: {summ['cons_at_5']}%")
            print(f"    All@5:  {summ['all_at_5']}%")
        else:
            print(f"    PASS RATE: {summ['pass_rate']}% ({summ['passed']}/{summ['total_evals']})")
        print(f"    AVG ROUNDS: {summ['avg_llm_calls']}  AVG TOKENS: in={summ['avg_tokens_in']} out={summ['avg_tokens_out']}")
        print(f"    AVG EDITS: {summ['avg_edit_count']}  AVG PEAK CTX: {summ['avg_max_context_tokens']} tokens")
        print(f"    AVG LATENCY: {fmt_time(summ['avg_latency_ms'])}")
        print(f"    TOOL ERROR RATE: {summ['tool_error_rate']}%")
        if summ.get('tool_errors_by_type'):
            for tname, trate in sorted(summ['tool_errors_by_type'].items(), key=lambda x: -x[1]):
                print(f"      {tname}: {trate}%")
        if summ.get('harness_tool_error_rate') is not None:
            print(f"    HARNESS TOOL ERRORS: {summ['harness_tool_error_rate']}%")
            if summ.get('harness_tool_errors_by_type'):
                for tname, trate in sorted(summ['harness_tool_errors_by_type'].items(), key=lambda x: -x[1]):
                    print(f"      {tname}: {trate}%")
        # Error breakdown
        err_bd = summ.get("error_breakdown", {})
        non_none_errors = {k: v for k, v in err_bd.items() if k != "none"}
        if non_none_errors:
            print(f"    ERRORS: {non_none_errors}")

    print("\n" + "=" * 60)
    print(f"  MODEL: {model.name}")
    print(f"  RUN DIR: {run_dir}")
    print_summary(f"EXPANDED ({summary['total_evals']} evals)", summary, run.pass_n)
    if debug_summary:
        print_summary(f"DEBUG ({debug_summary['total_evals']} evals)", debug_summary, run.pass_n)
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

