"""
VisualJudge — LLM-as-judge for visual eval scoring.

Scores eval results that pass the structural gate by sending screenshots
+ structural text dump + rubric to a vision model.
"""

import asyncio
import base64
import json
import logging
import os
from pathlib import Path
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


class VisualJudge:
    """LLM-as-judge for visual eval scoring."""

    def __init__(self, model: str, api_base: str, api_key: str):
        self.model = model
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key

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

        instruction = f"""You are judging a Roblox Studio agent's work. The agent was asked to:

{task_prompt}

Scoring rubric (rate each dimension 1-5, where 1=terrible, 3=acceptable, 5=excellent):
{rubric_text}

Screenshots of the result are attached."""
        if structure_dump:
            instruction += f"\n\nStructural description of created elements:\n{structure_dump}"

        instruction += """

Respond ONLY with valid JSON in this exact format:
{"scores": {"correctness": N, "layout": N, "aesthetics": N, "completeness": N}, "overall": N, "reasoning": "brief explanation", "issues": ["specific problem 1", "specific problem 2"]}

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
        for attempt in range(3):
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
        logger.info(f"Judge scored: overall={result.get('overall', '?')}")
        return result
