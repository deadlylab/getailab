"""Shared Sauron extraction logic — provider-agnostic via LLMAdapter."""

import json
import re
from typing import Optional

from llm.adapter import LLMAdapter, create_default_adapter

SAURON_SYSTEM_PROMPT = """You are SAURON, the research extraction layer for Team Chimera.
Extract structured scientific/technical data from the provided page text and/or screenshot.

Return ONLY valid JSON with keys:
{
  "type": "scientific_paper|documentation|code_repo|simulation_result|general",
  "topic": "string",
  "summary": "High-level technical overview",
  "mathematical_formalisms": ["list of formulas or proofs"],
  "architectural_patterns": ["list of logic structures"],
  "key_data": {"key": "value"},
  "code_snippets": [{"language": "str", "code": "str", "purpose": "str"}],
  "confidence": 0.0-1.0,
  "extraction_mode": "vision|text_only"
}
"""


def parse_sauron_json(response_text: str) -> Optional[dict]:
    if not response_text:
        return None
    raw = response_text.strip()
    raw = re.sub(r'^```(?:json)?\s*', '', raw)
    raw = re.sub(r'\s*```$', '', raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                return None
    return None


def extract_with_adapter(
    adapter: LLMAdapter,
    query: str,
    image_bytes: Optional[bytes] = None,
    text_context: Optional[str] = None,
) -> Optional[dict]:
    """Run extraction using whatever the configured provider supports."""
    parts = [SAURON_SYSTEM_PROMPT, f'\nUSER QUERY: "{query}"']
    mode = "text_only"

    if text_context:
        parts.append(f"\nPAGE TEXT (markdown):\n{text_context[:12000]}")

    use_images = None
    if image_bytes and adapter.supports_vision():
        use_images = [image_bytes]
        mode = "vision"
    elif image_bytes:
        parts.append(
            "\nNOTE: A screenshot was captured but the active LLM has no vision model. "
            "Rely on PAGE TEXT. Set LLM_MODEL_VISION (e.g. llava:latest for Ollama) for image analysis."
        )

    if not text_context and not use_images:
        parts.append("\nNOTE: Limited context — return best-effort structured JSON.")

    response_text = adapter.generate("\n".join(parts), images=use_images)
    data = parse_sauron_json(response_text)
    if data:
        data.setdefault("extraction_mode", mode)
    return data