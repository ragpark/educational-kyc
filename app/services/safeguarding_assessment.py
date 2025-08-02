from __future__ import annotations

import asyncio
import os
import re
import logging
from datetime import datetime
from typing import Optional, Tuple

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - openai optional
    OpenAI = None  # type: ignore


logger = logging.getLogger(__name__)


def _extract_text(path: str) -> str:
    """Return best-effort text extraction from the uploaded file."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def _heuristic_classification(text: str) -> Tuple[str, str]:
    """Fallback rule-based safeguarding assessment.

    Returns a tuple of (rating, rationale) where rationale is a
    two-sentence explanation of the rating.
    """
    lower = text.lower()
    if "safeguarding" not in lower or "policy" not in lower:
        rationale = (
            "The document does not clearly reference a safeguarding policy. "
            "It therefore appears irrelevant or missing."
        )
        return "red", rationale
    match = re.search(r"20\d{2}", text)
    if match:
        year = int(match.group())
        if year >= datetime.utcnow().year - 2:
            rationale = (
                "The document references safeguarding policy and includes a recent date. "
                "It appears relevant and up to date."
            )
            return "green", rationale
    rationale = (
        "The document mentions safeguarding but may be incomplete or outdated. "
        "Consider reviewing and updating the policy."
    )
    return "amber", rationale


async def assess_safeguarding_policy(path: str) -> Tuple[str, str]:
    """Assess a safeguarding policy document and return rating and rationale."""
    text = _extract_text(path)
    api_key = os.getenv("OPENAI_API_KEY")

    if api_key and OpenAI:
        logger.info("Assessing safeguarding policy using OpenAI LLM")
        client = OpenAI(api_key=api_key)
        system_prompt = (
            "You analyse learning centre safeguarding policy documents. "
            "Given a document, respond with the rating GREEN, AMBER, or RED on the first line "
            "followed by two sentences explaining the rating."
        )
        try:
            response = await asyncio.to_thread(
                lambda: client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": text[:6000]},
                    ],
                    max_tokens=150,
                )
            )
            content = response.choices[0].message.content.strip()
            lines = content.splitlines()
            rating_line = lines[0].strip().lower() if lines else ""
            rationale = " ".join(line.strip() for line in lines[1:]).strip()
            if "green" in rating_line:
                logger.info("Safeguarding assessment generated via OpenAI: green")
                return "green", rationale
            if "amber" in rating_line or "yellow" in rating_line:
                logger.info("Safeguarding assessment generated via OpenAI: amber")
                return "amber", rationale
            if "red" in rating_line:
                logger.info("Safeguarding assessment generated via OpenAI: red")
                return "red", rationale
        except Exception as exc:
            logger.warning("OpenAI safeguarding assessment failed: %s", exc)

    logger.info("Using heuristic safeguarding assessment")
    return _heuristic_classification(text)
