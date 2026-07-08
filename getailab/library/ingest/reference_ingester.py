"""
Reference Ingester — user-sourced material into a scientist's book.

Research knowledge only (papers, notes, URLs). No user profile data.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from getailab.library.scientist_book.book import ScientistBook, get_scientist_book
from personas.loader import get_squad_names

_MAX_CONTENT_CHARS = 80_000
_MAX_URL_CHARS = 8_000


def valid_scientist_name(name: str) -> bool:
    """Scientists only — Oracle is coordinated separately."""
    n = (name or "").lower().strip()
    return n in get_squad_names() and n != "oracle"


def fetch_url_as_text(url: str, max_chars: int = _MAX_CONTENT_CHARS) -> str:
    """Fetch a URL and return cleaned markdown-ish text for book storage."""
    url = (url or "").strip()
    if not url:
        raise ValueError("url is required")
    if not re.match(r"^https?://", url, re.I):
        raise ValueError("url must start with http:// or https://")

    resp = requests.get(url, headers={"User-Agent": "GetAiLab-ReferenceBot/1.0"}, timeout=45)
    resp.raise_for_status()

    content_type = (resp.headers.get("content-type") or "").lower()
    if "json" in content_type:
        text = resp.text[:max_chars]
    else:
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = md(str(soup), strip=["img"])[:max_chars]

    if not text.strip():
        raise ValueError(f"no extractable text from url: {url}")
    return text.strip()


def ingest_scientist_reference(
    scientist_name: str,
    *,
    title: str = "",
    content: str = "",
    url: str = "",
    tags: Optional[List[str]] = None,
    lab_id: str = "chimera",
    source_label: str = "user",
) -> Dict[str, Any]:
    """
    Add reference material to one scientist's book.
    Provide content directly, or a url to fetch, or both (content appended after fetch).
    """
    scientist = scientist_name.lower().strip()
    if not valid_scientist_name(scientist):
        raise ValueError(f"unknown scientist '{scientist_name}' — must be a Chimera squad member (not oracle)")

    fetched_from_url = False
    url = (url or "").strip()
    body = (content or "").strip()

    if url:
        fetched = fetch_url_as_text(url)
        fetched_from_url = True
        if body:
            body = f"Source: {url}\n\n{fetched}\n\n---\n\nUser notes:\n{body}"
        else:
            body = f"Source: {url}\n\n{fetched}"

    if not body:
        raise ValueError("content or url is required")

    if len(body) > _MAX_CONTENT_CHARS:
        body = body[:_MAX_CONTENT_CHARS] + "\n\n...[truncated for book storage]"

    if not title.strip():
        if url:
            title = url[:120]
        else:
            title = f"Reference note for {scientist.title()}"

    book = get_scientist_book(scientist, lab_id=lab_id)
    page = book.add_reference_page(
        title=title.strip(),
        content=body,
        source=source_label if not fetched_from_url else "url",
        url=url,
        tags=tags,
    )
    book.reindex()

    return {
        "ok": True,
        "scientist": scientist,
        "lab_id": lab_id,
        "page_id": page["page_id"],
        "title": page["title"],
        "page_type": page["page_type"],
        "content_length": len(page["content"]),
        "content_checksum": page["content_checksum"],
        "source": page["metadata"].get("source", source_label),
        "url": url or None,
        "tags": page.get("tags", []),
    }


def list_scientist_references(
    scientist_name: str,
    *,
    lab_id: str = "chimera",
    query: str = "",
    limit: int = 20,
) -> Dict[str, Any]:
    """List reference pages in a scientist's book."""
    scientist = scientist_name.lower().strip()
    if not valid_scientist_name(scientist):
        raise ValueError(f"unknown scientist '{scientist_name}'")

    book: ScientistBook = get_scientist_book(scientist, lab_id=lab_id)
    hits = book.search(query, limit=limit, page_types=["reference"])
    return {
        "scientist": scientist,
        "lab_id": lab_id,
        "count": len(hits),
        "references": hits,
    }