"""Strip agentic tool-call artifacts from LLM prose (common with cloud agent models)."""

from __future__ import annotations

import re
from typing import Tuple

_TOOL_MARKERS = (
    r"<\s*tool_call\b",
    r"<\s*/\s*tool_call\s*>",
    r"<\s*tool_response\b",
    r"<\s*/\s*tool_response\s*>",
    r"\]\s*<\s*\]\s*minimax\s*\[\s*>",
    r"<\s*\|\s*tool_calls_begin\s*\|>",
    r"<\s*\|\s*tool_calls_end\s*\|>",
)


def has_tool_artifacts(text: str) -> bool:
    if not text:
        return False
    return any(re.search(p, text, re.IGNORECASE) for p in _TOOL_MARKERS)


def strip_tool_artifacts(text: str) -> str:
    """Remove minimax/Ollama-cloud tool-call blocks from hypothesis/synthesis prose."""
    if not text:
        return ""
    out = text
    for _ in range(8):
        new = re.sub(
            r"<\s*tool_call\b.*?(?:<\s*/\s*tool_call\s*>|$)",
            "",
            out,
            flags=re.DOTALL | re.IGNORECASE,
        )
        new = re.sub(
            r"<\s*tool_response\b.*?(?:<\s*/\s*tool_response\s*>|$)",
            "",
            new,
            flags=re.DOTALL | re.IGNORECASE,
        )
        new = re.sub(r"\]\s*<\s*\]\s*minimax\s*\[\s*>.*", "", new, flags=re.DOTALL | re.IGNORECASE)
        new = re.sub(r"<\s*\|\s*tool_calls_begin\s*\|>.*?<\s*\|\s*tool_calls_end\s*\|>", "", new, flags=re.DOTALL | re.IGNORECASE)
        if new == out:
            break
        out = new
    out = re.sub(r"\n{3,}", "\n\n", out).strip()
    return out


def sanitize_prose(text: str, *, min_chars: int = 200) -> Tuple[str, bool]:
    """
    Clean prose for loop phases. Returns (cleaned_text, ok).
    ok=False if output looks like tool-hallucination sludge after cleaning.
    """
    raw = (text or "").strip()
    if raw.startswith("ERROR:"):
        return raw, False
    cleaned = strip_tool_artifacts(raw)
    if has_tool_artifacts(cleaned):
        cleaned = strip_tool_artifacts(cleaned)
    if len(cleaned) < min_chars and has_tool_artifacts(raw):
        return cleaned, False
    if len(cleaned) < 80 and len(raw) > 80:
        return cleaned, False
    return cleaned, True