#!/usr/bin/env python3
"""
Collaborative Review — squad reads uploaded material and Oracle synthesizes research paths.

Flow:
  1. User supplies files, text, and/or URLs (+ optional working question)
  2. Material is optionally ingested into each scientist's book
  3. Every scientist POSTs /review with structured findings
  4. Oracle POSTs /synthesize_reviews → recommended research paths + refined working question
  5. Markdown report written to docs/reviews/; codex archived via Oracle

Examples:
  python3 scripts/collaborative_review.py --files paper.md notes.txt --question "How does X relate to Y?"
  python3 scripts/collaborative_review.py --url https://example.com/article --ingest
  python3 run_chimera.py --collab-review --file draft.md --question "Is this loop-ready?"
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import requests

from getailab.library import add_scientist_reference
from personas.loader import get_squad_names

try:
    from getailab.lab_config import get_lab_id, get_scientists_dict, get_service_urls
    _ACTIVE_LAB = get_lab_id()
    SCIENTISTS = get_scientists_dict(_ACTIVE_LAB)
    _oracle_default, _lab_default = get_service_urls(_ACTIVE_LAB)
except Exception:
    _ACTIVE_LAB = os.getenv("LAB_ID", "example")
    SCIENTISTS = {
        "albert": 5025, "bohr": 5039, "heisenberg": 5040,
        "alan": 5027, "brian": 5032, "carl": 5028,
        "neil": 5034, "roger": 5038, "emmy": 5029,
        "tesla": 5030, "andrew": 5026,
    }
    _oracle_default, _lab_default = "http://localhost:5024", "http://localhost:5035"

ORACLE_URL = os.getenv("ORACLE_URL", _oracle_default).rstrip("/")
LAB_URL = os.getenv("LAB_URL", _lab_default).rstrip("/")
SCIENTIST_HOST_MODE = os.getenv("SCIENTIST_HOST_MODE", "localhost").strip().lower()
SCIENTIST_HTTP_TIMEOUT = int(os.getenv("SCIENTIST_HTTP_TIMEOUT", "600"))
ORACLE_SYNTH_TIMEOUT = int(os.getenv("ORACLE_SYNTH_TIMEOUT", "300"))

_MAX_MATERIAL_CHARS = 60_000


def _c(text: str, color: str = "") -> str:
    if not color or not sys.stdout.isatty():
        return text
    codes = {"r": "\033[91m", "g": "\033[92m", "y": "\033[93m", "b": "\033[94m", "m": "\033[95m", "c": "\033[96m", "w": "\033[97m", "reset": "\033[0m"}
    return codes.get(color, "") + text + codes["reset"]


def scientist_url(name: str, port: int) -> str:
    override = os.getenv(f"SCIENTIST_{name.upper()}_URL", "").strip()
    if override:
        return override.rstrip("/")
    if SCIENTIST_HOST_MODE == "docker":
        return f"http://{name}:{port}"
    host = os.getenv("SCIENTIST_HOST", "localhost").strip() or "localhost"
    return f"http://{host}:{port}"


def _squad_members(selected: Optional[List[str]] = None) -> List[str]:
    all_names = [n for n in get_squad_names() if n != "oracle"]
    if not selected:
        return all_names
    valid = {n.lower() for n in all_names}
    out = []
    for name in selected:
        n = name.lower().strip()
        if n in valid:
            out.append(n)
    return out or all_names


def _read_file(path: str) -> Tuple[str, str]:
    with open(path, encoding="utf-8", errors="replace") as fh:
        return os.path.basename(path), fh.read()


def _fetch_url(url: str) -> str:
    try:
        res = requests.post(f"{LAB_URL}/web/read", json={"url": url}, timeout=60)
        res.raise_for_status()
        data = res.json()
        if data.get("success"):
            return data.get("text", "")[:15000]
    except Exception:
        pass
    from getailab.library.ingest.reference_ingester import fetch_url_as_text
    return fetch_url_as_text(url)


def load_materials(
    *,
    files: Optional[List[str]] = None,
    text: str = "",
    urls: Optional[List[str]] = None,
) -> Tuple[str, str, List[Dict[str, str]]]:
    """Return (combined_body, title, sources_meta)."""
    parts: List[str] = []
    sources: List[Dict[str, str]] = []
    title = ""

    for fp in files or []:
        fp = fp.strip()
        if not fp:
            continue
        if not os.path.isfile(fp):
            raise FileNotFoundError(f"File not found: {fp}")
        name, body = _read_file(fp)
        sources.append({"type": "file", "path": fp, "title": name})
        parts.append(f"### File: {name}\n\n{body}")
        if not title:
            title = name

    for url in urls or []:
        url = url.strip()
        if not url:
            continue
        body = _fetch_url(url)
        sources.append({"type": "url", "url": url})
        parts.append(f"### URL: {url}\n\n{body}")
        if not title:
            title = url[:80]

    if text.strip():
        sources.append({"type": "text", "title": "inline notes"})
        parts.append(f"### User notes\n\n{text.strip()}")
        if not title:
            title = "Collaborative review material"

    if not parts:
        raise ValueError("No material provided — use --files, --text, or --url")

    combined = "\n\n---\n\n".join(parts)
    if len(combined) > _MAX_MATERIAL_CHARS:
        combined = combined[:_MAX_MATERIAL_CHARS] + "\n\n...[truncated for review session]"

    if not title:
        title = "Collaborative review material"
    return combined, title, sources


def ingest_to_squad(
    scientists: List[str],
    *,
    title: str,
    content: str,
    urls: Optional[List[str]] = None,
    tags: Optional[List[str]] = None,
    lab_id: str,
) -> List[Dict[str, Any]]:
    """Add the same reference to each scientist's book."""
    ingest_tags = ["collaborative-review"] + (tags or [])
    results = []
    url = (urls[0] if urls else "") or ""
    for name in scientists:
        try:
            r = add_scientist_reference(
                name,
                title=title,
                content=content,
                url=url,
                tags=ingest_tags,
                lab_id=lab_id,
                source_label="collaborative_review",
            )
            results.append(r)
            print(_c(f"  📚 Ingested → {name.title()} ({r['page_id']})", "g"))
        except Exception as exc:
            print(_c(f"  ⚠️  Ingest failed for {name}: {exc}", "y"))
    return results


def _is_llm_error(text: str) -> bool:
    if not text:
        return True
    t = str(text).strip()
    return t.startswith("ERROR:") or "HTTPConnectionPool" in t or "Connection refused" in t


def collect_reviews(
    scientists: List[str],
    *,
    materials: str,
    title: str,
    working_question: str,
    review_id: str,
) -> Tuple[Dict[str, str], str]:
    """Call each scientist /review. Returns (reviews dict, raw block for Oracle)."""
    reviews: Dict[str, str] = {}
    raw_blocks: List[str] = []

    print(_c(f"\n🔬 Phase 1 — Scientist reviews ({len(scientists)} squad members)", "b"))
    for name in scientists:
        port = SCIENTISTS.get(name)
        if not port:
            print(_c(f"  ⚠️  No port for {name}, skipping", "y"))
            continue
        print(_c(f"  ⏳ {name.title()} reviewing…", "y"))
        try:
            resp = requests.post(
                scientist_url(name, port) + "/review",
                json={
                    "materials": materials,
                    "title": title,
                    "working_question": working_question,
                    "review_id": review_id,
                },
                timeout=SCIENTIST_HTTP_TIMEOUT,
            )
            if resp.status_code == 503:
                err = resp.json().get("error", "LLM unavailable")
                print(_c(f"  ❌ {name.title()} — {err[:120]}", "r"))
                continue
            data = resp.json()
            review = data.get("review", "")
            if data.get("error") or _is_llm_error(review):
                print(_c(f"  ❌ {name.title()} — review failed", "r"))
                continue
            reviews[name] = review
            raw_blocks.append(f"[{name.upper()} REVIEW]:\n{review}\n")
            print(_c(f"  ✅ {name.title()} — findings recorded", "g"))
        except Exception as exc:
            print(_c(f"  ❌ {name.title()} — {exc}", "r"))

    return reviews, "\n".join(raw_blocks)


def oracle_synthesize(
    *,
    review_id: str,
    working_question: str,
    materials_summary: str,
    raw_reviews: str,
) -> str:
    print(_c("\n🔮 Phase 2 — Oracle synthesis", "b"))
    resp = requests.post(
        f"{ORACLE_URL}/synthesize_reviews",
        json={
            "review_id": review_id,
            "working_question": working_question,
            "materials_summary": materials_summary,
            "raw_reviews": raw_reviews,
        },
        timeout=ORACLE_SYNTH_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("error"):
        raise RuntimeError(data["error"])
    synthesis = data.get("synthesis", "")
    if data.get("library_archived"):
        summary = data.get("library_summary") or {}
        print(_c(
            f"  📖 Codex archived: {summary.get('pages_written', 0)} pages",
            "m",
        ))
    return synthesis


def write_report(
    *,
    output_dir: str,
    review_id: str,
    title: str,
    working_question: str,
    materials: str,
    sources: List[Dict[str, str]],
    reviews: Dict[str, str],
    synthesis: str,
) -> str:
    os.makedirs(output_dir, exist_ok=True)
    date_slug = datetime.now().strftime("%Y%m%d")
    path = os.path.join(output_dir, f"review_{date_slug}_{review_id}.md")

    lines = [
        f"# Collaborative Review — {review_id}",
        f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"**Material:** {title}",
        "",
    ]
    if working_question:
        lines.extend([f"**Working question:** {working_question}", ""])
    if sources:
        lines.append("## Sources")
        for src in sources:
            if src.get("type") == "file":
                lines.append(f"- File: `{src.get('path')}`")
            elif src.get("type") == "url":
                lines.append(f"- URL: {src.get('url')}")
            else:
                lines.append("- Inline user notes")
        lines.append("")

    lines.extend(["## Material (excerpt)", "", materials[:8000], ""])
    lines.append("## Scientist Reviews")
    lines.append("")
    for name, review in sorted(reviews.items()):
        lines.extend([f"### {name.title()}", "", review, ""])
    lines.extend(["## Oracle Synthesis", "", synthesis, ""])

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path


def run_collaborative_review(
    *,
    files: Optional[List[str]] = None,
    text: str = "",
    urls: Optional[List[str]] = None,
    question: str = "",
    title: str = "",
    ingest: bool = True,
    scientists: Optional[List[str]] = None,
    lab_id: Optional[str] = None,
    output_dir: str = "",
    dry_run: bool = False,
    tags: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Main entry — usable from CLI or run_chimera.py Commander."""
    lid = lab_id or _ACTIVE_LAB
    squad = _squad_members(scientists)
    materials, auto_title, sources = load_materials(files=files, text=text, urls=urls)
    mat_title = title.strip() or auto_title
    working_question = (question or "").strip()
    review_id = datetime.now().strftime("%H%M%S")
    out_dir = output_dir or os.path.join(_PROJECT_ROOT, "docs", "reviews")

    print(_c("\n╔══════════════════════════════════════════════════════════════╗", "c"))
    print(_c("║  COLLABORATIVE REVIEW — Squad document analysis               ║", "c"))
    print(_c("╚══════════════════════════════════════════════════════════════╝", "c"))
    print(_c(f"  Session: {review_id}  |  Squad: {len(squad)} scientists", "w"))
    if working_question:
        print(_c(f"  Working question: {working_question[:100]}{'…' if len(working_question) > 100 else ''}", "m"))

    if dry_run:
        print(_c("\n  [dry-run] Material loaded; skipping ingest, reviews, and synthesis.", "y"))
        print(_c(f"  Chars: {len(materials)} | Title: {mat_title}", "w"))
        return {
            "dry_run": True,
            "review_id": review_id,
            "title": mat_title,
            "material_length": len(materials),
            "scientists": squad,
        }

    if ingest:
        print(_c("\n📥 Ingesting material into scientist books…", "b"))
        ingest_to_squad(
            squad,
            title=mat_title,
            content=materials,
            urls=urls,
            tags=tags,
            lab_id=lid,
        )

    reviews, raw_reviews = collect_reviews(
        squad,
        materials=materials,
        title=mat_title,
        working_question=working_question,
        review_id=review_id,
    )
    if not reviews:
        raise RuntimeError(
            "No scientist reviews succeeded — is the squad running? "
            "Try: ./boot_example.sh or python3 run_chimera.py --status"
        )

    materials_summary = (
        f"Title: {mat_title}\n"
        f"Sources: {len(sources)}\n"
        f"Length: {len(materials)} chars\n"
        f"Excerpt:\n{materials[:2500]}"
    )
    synthesis = oracle_synthesize(
        review_id=review_id,
        working_question=working_question,
        materials_summary=materials_summary,
        raw_reviews=raw_reviews,
    )

    report_path = write_report(
        output_dir=out_dir,
        review_id=review_id,
        title=mat_title,
        working_question=working_question,
        materials=materials,
        sources=sources,
        reviews=reviews,
        synthesis=synthesis,
    )

    print(_c(f"\n✅ Review complete — report: {report_path}", "g"))
    print(_c("\n── Oracle recommended paths (excerpt) ──", "c"))
    for line in synthesis.splitlines()[:25]:
        print(_c(f"  {line}", "w"))

    return {
        "review_id": review_id,
        "title": mat_title,
        "working_question": working_question,
        "scientists_reviewed": list(reviews.keys()),
        "report_path": report_path,
        "synthesis": synthesis,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a collaborative squad review of uploaded documents.",
    )
    parser.add_argument("--files", nargs="+", default=[], help="One or more files to review")
    parser.add_argument("--file", dest="files_append", action="append", default=[], help="Single file (repeatable)")
    parser.add_argument("--text", default="", help="Inline notes to include")
    parser.add_argument("--url", action="append", default=[], help="URL to fetch (repeatable)")
    parser.add_argument("--question", "-q", default="", help="Working question to assess against the material")
    parser.add_argument("--title", default="", help="Title for this review session")
    parser.add_argument("--ingest", action="store_true", default=True, help="Ingest material into scientist books (default)")
    parser.add_argument("--no-ingest", action="store_true", help="Skip book ingest; pass material inline only")
    parser.add_argument("--scientists", default="", help="Comma-separated subset (default: full squad)")
    parser.add_argument("--lab-id", default="", help="Lab ID (default: active lab)")
    parser.add_argument("--output-dir", default="", help="Report output directory")
    parser.add_argument("--tags", default="", help="Comma-separated ingest tags")
    parser.add_argument("--dry-run", action="store_true", help="Load material only; no API calls")
    args = parser.parse_args()

    all_files = list(args.files) + list(args.files_append)
    scientists = [s.strip() for s in args.scientists.split(",") if s.strip()] or None
    tags = [t.strip() for t in args.tags.split(",") if t.strip()] or None
    ingest = not args.no_ingest

    try:
        result = run_collaborative_review(
            files=all_files or None,
            text=args.text,
            urls=args.url or None,
            question=args.question,
            title=args.title,
            ingest=ingest,
            scientists=scientists,
            lab_id=args.lab_id or None,
            output_dir=args.output_dir,
            dry_run=args.dry_run,
            tags=tags,
        )
        if not args.dry_run:
            print(json.dumps({k: v for k, v in result.items() if k != "synthesis"}, indent=2))
        return 0
    except Exception as exc:
        print(_c(f"\n❌ Collaborative review failed: {exc}", "r"))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())