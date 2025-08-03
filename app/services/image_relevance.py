import base64
import logging
import os
from typing import Literal

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - openai might not be installed during tests
    OpenAI = None

ImageAssessment = Literal["green", "amber", "red"]

logger = logging.getLogger(__name__)

async def assess_image_relevance(path: str) -> ImageAssessment:
    """Assess whether an image is relevant to a teaching environment.

    Uses a vision-capable model and returns GREEN, AMBER or RED. Defaults to RED
    if the model or API is unavailable.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key or OpenAI is None:
        logger.warning("OpenAI not configured; defaulting image assessment to RED")
        return "red"
    try:
        with open(path, "rb") as f:
            img_bytes = f.read()
        b64_img = base64.b64encode(img_bytes).decode("ascii")
        prompt = (
            "Is this image relevant to a college teaching or learning environment? "
            "Respond with one word: GREEN if relevant, RED if not."
        )
        client = OpenAI(api_key=api_key)
        resp = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image": b64_img},
                    ],
                }
            ],
            max_output_tokens=1,
        )
        result = resp.output_text.strip().lower()
        if result.startswith("green"):
            return "green"
        if result.startswith("amber"):
            return "amber"
        return "red"
    except Exception as exc:  # pragma: no cover - external API may fail
        logger.warning("Image assessment failed: %s", exc)
        return "red"
