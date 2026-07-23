"""
VisualJudge — LLM-as-judge for visual eval scoring.

Scores eval results that pass the structural gate by sending screenshots
+ structural text dump + rubric to a vision model.
"""

import asyncio
import base64
import hashlib
import json
import logging
import os
import struct
from pathlib import Path
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)

JUDGE_PROMPT_VERSION = "ui-rubric-v2"


def validate_score_result(result: dict, rubric: dict) -> dict:
    """Validate a judge response before it becomes benchmark data."""
    if not isinstance(result, dict):
        raise ValueError("judge response must be a JSON object")

    scores = result.get("scores")
    if not isinstance(scores, dict):
        raise ValueError("judge response scores must be an object")
    expected_keys = set(rubric)
    actual_keys = set(scores)
    if actual_keys != expected_keys:
        missing = sorted(expected_keys - actual_keys)
        extra = sorted(actual_keys - expected_keys)
        raise ValueError(f"judge score keys mismatch: missing={missing}, extra={extra}")

    for dimension, score in scores.items():
        if type(score) is not int or not 1 <= score <= 5:
            raise ValueError(f"judge score for {dimension!r} must be an integer from 1 to 5")

    overall = result.get("overall")
    if type(overall) is not int or not 1 <= overall <= 5:
        raise ValueError("judge overall must be an integer from 1 to 5")

    if not isinstance(result.get("reasoning"), str):
        raise ValueError("judge reasoning must be a string")

    issues = result.get("issues")
    if not isinstance(issues, list) or not all(isinstance(issue, str) for issue in issues):
        raise ValueError("judge issues must be an array of strings")

    return result


def _file_provenance(path: str) -> dict:
    data = Path(path).read_bytes()
    metadata = {
        "path": path,
        "sha256": hashlib.sha256(data).hexdigest(),
        "dimensions": None,
    }
    # Roblox screenshot capture currently writes PNG files. Keep this parser
    # dependency-free and leave dimensions unknown for other image formats.
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        metadata["dimensions"] = list(struct.unpack(">II", data[16:24]))
    return metadata


class VisualJudge:
    """LLM-as-judge for visual eval scoring."""

    def __init__(self, model: str, api_base: str, api_key: str):
        self.model = model
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.last_attempt_count = 0

    def _encode_image(self, path: str) -> str:
        """Read an image file and return base64 encoded string."""
        data = Path(path).read_bytes()
        return base64.b64encode(data).decode("utf-8")

    def _build_score_messages(
        self,
        task_prompt: str,
        rubric: dict,
        screenshots: list[str],
        structure_dump: str = "",
    ) -> list:
        """Build OpenAI-format messages with images for scoring."""
        # Build the text instruction
        rubric_text = "\n".join(
            f"- {dim}: {desc}" for dim, desc in rubric.items()
        )
        score_dimensions = ", ".join(
            f"{json.dumps(dim)}: N" for dim in rubric
        )

        instruction = f"""You are judging a Roblox Studio agent's work. The agent was asked to:

{task_prompt}

Scoring rubric (rate each dimension 1-5, where 1=terrible, 3=acceptable, 5=excellent):
{rubric_text}

Screenshots of the result are attached."""
        if structure_dump:
            instruction += f"\n\nStructural description of created elements:\n{structure_dump}"

        instruction += """

Evidence rules:
- Score visible visual properties from the screenshots.
- Use the structural description only to identify elements or disambiguate labels.
- Do not infer optical quality, responsiveness, focus order, input usability, localization behavior, or interaction quality from structure alone.
- If a requested property is not evidenced by the supplied material, mention that limitation in issues instead of assuming it is present.
"""

        instruction += f"""

Respond ONLY with valid JSON in this exact format:
{{"scores": {{{score_dimensions}}}, "overall": N, "reasoning": "brief explanation", "issues": ["specific problem 1", "specific problem 2"]}}

Where N is an integer 1-5. The "overall" should be your holistic assessment."""

        # Build content array with text + images
        content = [{"type": "text", "text": instruction}]
        for ss_path in screenshots:
            if os.path.exists(ss_path):
                b64 = self._encode_image(ss_path)
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{b64}",
                        "detail": "high",
                    },
                })

        return [{"role": "user", "content": content}]

    async def _call_vision_api(self, messages: list) -> dict:
        """Call the vision LLM API and parse JSON response."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "messages": messages,
            "max_tokens": 2000,
            "temperature": 0,
        }

        last_error = None
        self.last_attempt_count = 0
        for attempt in range(3):
            self.last_attempt_count = attempt + 1
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.api_base}/chat/completions",
                        headers=headers,
                        json=body,
                        timeout=aiohttp.ClientTimeout(total=120),
                    ) as resp:
                        if resp.status != 200:
                            text = await resp.text()
                            raise Exception(f"Judge API error {resp.status}: {text[:500]}")
                        data = await resp.json()
                break
            except Exception as e:
                last_error = e
                if attempt < 2:
                    wait = 2 ** (attempt + 1)
                    logger.warning(f"Judge API attempt {attempt+1} failed: {e}, retrying in {wait}s...")
                    await asyncio.sleep(wait)
                else:
                    raise

        content = data["choices"][0]["message"]["content"]

        # Extract JSON from response — try fence extraction first, then regex fallback
        # Strip markdown code fences if present
        cleaned = content.strip()
        if cleaned.startswith("```"):
            # Remove ```json or ``` prefix
            lines = cleaned.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        # Try direct JSON parse first
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # Fallback: find the first balanced JSON object
        # Find first '{' and try to parse from there, expanding until valid
        import re
        start = cleaned.find("{")
        if start == -1:
            raise ValueError(f"Could not parse JSON from judge response: {content[:500]}")
        # Try progressively shorter substrings from first '{' to last '}'
        end = cleaned.rfind("}")
        while end > start:
            try:
                return json.loads(cleaned[start:end+1])
            except json.JSONDecodeError:
                end = cleaned.rfind("}", start, end)
        raise ValueError(f"Could not parse JSON from judge response: {content[:500]}")

    async def score(
        self,
        task_prompt: str,
        rubric: dict,
        screenshots: list[str],
        structure_dump: str = "",
    ) -> dict:
        """Score a single eval attempt. Returns scores + reasoning."""
        messages = self._build_score_messages(
            task_prompt, rubric, screenshots, structure_dump
        )
        result = await self._call_vision_api(messages)
        validate_score_result(result, rubric)

        prompt_text = messages[0]["content"][0]["text"]
        result["_provenance"] = {
            "validation_status": "valid",
            "score_source": "validated_judge_overall",
            "judge_model": self.model,
            "judge_api_base": self.api_base,
            "judge_attempt_count": self.last_attempt_count,
            "prompt_version": JUDGE_PROMPT_VERSION,
            "prompt_sha256": hashlib.sha256(prompt_text.encode("utf-8")).hexdigest(),
            "rubric_sha256": hashlib.sha256(
                json.dumps(rubric, sort_keys=True).encode("utf-8")
            ).hexdigest(),
            "screenshots": [
                _file_provenance(path) for path in screenshots if os.path.exists(path)
            ],
            "structure_dump_sha256": hashlib.sha256(
                structure_dump.encode("utf-8")
            ).hexdigest() if structure_dump else None,
        }
        logger.info(f"Judge scored: overall={result.get('overall', '?')}")
        return result
