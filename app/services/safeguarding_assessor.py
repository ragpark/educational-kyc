import os
from typing import Literal

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - openai might not be installed during tests
    OpenAI = None

Assessment = Literal['green', 'amber', 'red']

def _read_text(path: str) -> str:
    """Read file content as text. Falls back gracefully."""
    try:
        with open(path, 'rb') as f:
            data = f.read()
        return data.decode('utf-8', errors='ignore')
    except Exception:
        return ""

async def assess_safeguarding_document(path: str) -> Assessment:
    """Use an LLM to assess safeguarding policy documents.

    Returns a simple traffic light rating:
    - green: relevant, complete and in date
    - amber: partially relevant/complete or unclear
    - red: irrelevant, incomplete or out of date

    If no API key is configured the function defaults to 'amber'.
    """
    text = _read_text(path)
    api_key = os.getenv('OPENAI_API_KEY')
    if not api_key or OpenAI is None or not text.strip():
        return 'amber'

    try:
        client = OpenAI(api_key=api_key)
        prompt = (
            "You are verifying a learning centre's safeguarding policy. "
            "Consider if the document is relevant, complete and dated within the last two years. Apply GREEN when theSpecific, current (within 2 years), names a DSL, includes staff training, aligns with UK guidance, assign AMBER	Mostly relevant but missing elements (DSL, update date, references) and assign RED	if the text is Outdated and has expired, generic, non-specific, or missing entirely. "
            "Respond with a single word: Green (good), Amber (partial), or Red (poor).\n\n"
            f"Document text:\n{text[:5000]}"
        )
        resp = client.responses.create(
            model="gpt-4o-mini",
            input=prompt,
            max_output_tokens=10,
        )
        result = resp.output_text.strip().lower()
        if result.startswith('green'):
            return 'green'
        if result.startswith('red'):
            return 'red'
        return 'amber'
    except Exception:
        return 'amber'
