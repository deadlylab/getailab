#!/usr/bin/env python3
"""
Ingest the example lab research loops and synthesis docs into scientist books (beef-up at scale).

Supports:
  - 2025 legacy archive: # Dialectic Loop #N, **Research Question:**
  - R&D division exports: # Research Loop #N, ## Problem Statement
  - Standalone synthesis markdown (white papers, reports)

Usage:
    python3 scripts/ingest_legacy_research.py /path/to/research_output
    python3 scripts/ingest_legacy_research.py /path/to/exports/research --tag rd_division --year 2026
    python3 scripts/ingest_legacy_research.py /path/to/exports/research --dry-run
    python3 scripts/ingest_legacy_research.py /path --docs CHIMERA_WHITE_PAPER_V1.md CHIMERA_RESEARCH_REPORT.md
"""

from __future__ import annotations

import argparse
import hashlib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from getailab.library import add_scientist_reference
from getailab.library.storage.persistence import BookPersistence
from personas.loader import get_squad_names, sanitize_albert_persona_labels

_SCIENTIST_RE = re.compile(
    r"\b(Albert|Andrew|Alan|Carl|Bohr|Brian|Neil|Roger|Emmy|Heisenberg)\b",
    re.IGNORECASE,
)
_DIALECTIC_LOOP_RE = re.compile(r"# Dialectic Loop #(\d+)", re.IGNORECASE)
_RESEARCH_LOOP_RE = re.compile(r"# Research Loop #(\d+)", re.IGNORECASE)
_QUESTION_INLINE_RE = re.compile(r"\*\*Research Question:\*\*\s*(.+)", re.IGNORECASE)
_PROBLEM_STATEMENT_RE = re.compile(
    r"(?ms)^## Problem Statement\s*\n+(.+?)(?:\n---|\n## )",
)


def _slug_scientist(header: str) -> Optional[str]:
    m = _SCIENTIST_RE.search(header)
    return m.group(1).lower() if m else None


def _is_oracle(header: str) -> bool:
    return "oracle" in header.lower()


def _extract_question(text: str, fallback: str) -> str:
    q_m = _QUESTION_INLINE_RE.search(text)
    if q_m:
        return q_m.group(1).strip()
    ps_m = _PROBLEM_STATEMENT_RE.search(text)
    if ps_m:
        q = ps_m.group(1).strip()
        q = re.sub(r"\n{3,}", "\n\n", q)
        return q
    return fallback


def _extract_loop_num(text: str) -> Optional[int]:
    for pat in (_DIALECTIC_LOOP_RE, _RESEARCH_LOOP_RE):
        m = pat.search(text)
        if m:
            return int(m.group(1))
    return None


def parse_loop_file(path: Path) -> Tuple[Optional[int], str, Dict[str, str]]:
    """Return (loop_num, question, {scientist: content})."""
    text = path.read_text(encoding="utf-8", errors="replace")
    loop_num = _extract_loop_num(text)
    question = _extract_question(text, path.stem)

    sections: Dict[str, str] = {}
    oracle_body = ""
    parts = re.split(r"(?m)^(### .+)$", text)
    i = 1
    while i < len(parts):
        header = parts[i].strip()
        body = parts[i + 1].strip() if i + 1 < len(parts) else ""
        i += 2
        if _is_oracle(header):
            oracle_body = body
            continue
        scientist = _slug_scientist(header)
        if scientist and scientist in get_squad_names() and scientist != "oracle":
            preamble = f"**Loop {loop_num or '?'}** — {question}\n\n"
            sections[scientist] = preamble + body

    if oracle_body:
        sections["_oracle_synthesis"] = (
            f"**Oracle synthesis — loop {loop_num or '?'}**\n"
            f"**Question:** {question}\n\n{oracle_body}"
        )
    return loop_num, question, sections


def _write_codex_page(
    lab_id: str,
    title: str,
    content: str,
    page_id: str,
    loop_num: Optional[int],
    page_type: str,
    tags: List[str],
    source_label: str,
):
    codex_dir = ROOT / "data" / "labs" / lab_id / "codex" / "book"
    codex_dir.mkdir(parents=True, exist_ok=True)
    persist = BookPersistence(codex_dir)
    persist._ensure()
    persist.write_page({
        "page_id": page_id,
        "loop_id": loop_num,
        "page_type": page_type,
        "title": title,
        "content": content,
        "content_checksum": hashlib.sha256(content.encode()).hexdigest(),
        "agent": "oracle",
        "tags": tags,
        "metadata": {
            "source": source_label,
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        },
        "created_at": datetime.now(timezone.utc).isoformat(),
    })


def ingest_archive(
    archive_dir: Path,
    *,
    lab_id: str = "example",
    dry_run: bool = False,
    loop_filter: Optional[set] = None,
    tag: str = "legacy",
    year: str = "2025",
    source_label: str = "legacy_archive",
    label_prefix: str = "Legacy",
    codex_id_prefix: str = "legacy",
    ingest_index: bool = True,
) -> Dict[str, int]:
    stats = {"files": 0, "pages": 0, "codex": 0, "skipped": 0, "by_scientist": {}}
    base_tags = [tag, year]

    if ingest_index:
        index_path = archive_dir / "index.md"
        if index_path.is_file():
            index_body = index_path.read_text(encoding="utf-8", errors="replace")
            targets = [n for n in get_squad_names() if n != "oracle"]
            if dry_run:
                print(f"[dry-run] index.md → {len(targets)} scientists")
            else:
                for scientist in targets:
                    add_scientist_reference(
                        scientist,
                        title=f"{label_prefix} Research Index",
                        content=index_body,
                        tags=base_tags + ["index"],
                        lab_id=lab_id,
                        source_label=source_label,
                    )
                    stats["by_scientist"][scientist] = stats["by_scientist"].get(scientist, 0) + 1
                    stats["pages"] += 1
            stats["files"] += 1

    loop_files = sorted(archive_dir.glob("loop_*.md"))
    for path in loop_files:
        loop_num, question, sections = parse_loop_file(path)
        if loop_filter and loop_num not in loop_filter:
            stats["skipped"] += 1
            continue
        stats["files"] += 1
        label = f"loop {loop_num}" if loop_num else path.name
        print(f"  📄 {path.name} → {len(sections)} section(s)")

        oracle_key = "_oracle_synthesis"
        if oracle_key in sections:
            if dry_run:
                print(f"     [dry-run] codex ← Oracle synthesis ({label})")
            else:
                _write_codex_page(
                    lab_id,
                    f"{label_prefix} Oracle synthesis — {label}",
                    sections[oracle_key],
                    f"{codex_id_prefix}-synthesis-{loop_num or 0}",
                    loop_num,
                    "synthesis",
                    base_tags + ["codex", "synthesis"],
                    source_label,
                )
                stats["codex"] += 1
            del sections[oracle_key]

        for scientist, content in sections.items():
            if not content.strip():
                continue
            if scientist == "albert":
                content = sanitize_albert_persona_labels(content)
            title = f"{label_prefix} {label}: {question[:72]}{'…' if len(question) > 72 else ''}"
            if dry_run:
                print(f"     [dry-run] {scientist} ← {len(content)} chars")
            else:
                add_scientist_reference(
                    scientist,
                    title=title,
                    content=content,
                    tags=base_tags + [f"loop_{loop_num or 0}"],
                    lab_id=lab_id,
                    source_label=source_label,
                )
            stats["by_scientist"][scientist] = stats["by_scientist"].get(scientist, 0) + 1
            stats["pages"] += 1

    return stats


def ingest_documents(
    doc_paths: List[Path],
    *,
    lab_id: str = "example",
    dry_run: bool = False,
    tag: str = "synthesis",
    year: str = "2026",
    source_label: str = "rd_division",
    label_prefix: str = "R&D",
    codex_id_prefix: str = "rd-doc",
) -> Dict[str, int]:
    """Ingest standalone markdown docs to all scientists + codex."""
    stats = {"files": 0, "pages": 0, "codex": 0, "by_scientist": {}}
    base_tags = [tag, year, "synthesis_doc"]
    targets = [n for n in get_squad_names() if n != "oracle"]

    for path in doc_paths:
        if not path.is_file():
            print(f"  ⚠️  skip (missing): {path}")
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        title = path.stem.replace("_", " ")
        stats["files"] += 1
        print(f"  📘 {path.name} → scientists + codex")

        if dry_run:
            print(f"     [dry-run] {len(targets)} scientists + codex ← {len(content)} chars")
            stats["pages"] += len(targets)
            stats["codex"] += 1
            continue

        for scientist in targets:
            sci_content = sanitize_albert_persona_labels(content) if scientist == "albert" else content
            add_scientist_reference(
                scientist,
                title=f"{label_prefix}: {title}",
                content=sci_content,
                tags=base_tags,
                lab_id=lab_id,
                source_label=source_label,
            )
            stats["by_scientist"][scientist] = stats["by_scientist"].get(scientist, 0) + 1
            stats["pages"] += 1

        slug = re.sub(r"[^a-z0-9]+", "-", path.stem.lower()).strip("-")
        _write_codex_page(
            lab_id,
            f"{label_prefix}: {title}",
            content,
            f"{codex_id_prefix}-{slug}",
            None,
            "reference",
            base_tags + ["codex"],
            source_label,
        )
        stats["codex"] += 1

    return stats


def main():
    parser = argparse.ArgumentParser(description="Ingest the example lab research into scientist books")
    parser.add_argument("archive_dir", nargs="?", help="Path to folder with loop_*.md files")
    parser.add_argument("--lab-id", default="example")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--loop", type=int, nargs="*", help="Only ingest these loop numbers")
    parser.add_argument("--tag", default="legacy", help="Primary tag for ingested pages")
    parser.add_argument("--year", default="2025", help="Year tag (e.g. 2025, 2026)")
    parser.add_argument(
        "--source-label",
        default="legacy_archive",
        help="source_label stored on reference pages",
    )
    parser.add_argument(
        "--label-prefix",
        default="Legacy",
        help="Title prefix for ingested loop pages",
    )
    parser.add_argument(
        "--codex-prefix",
        default="legacy",
        help="Codex page_id prefix (avoid collisions across ingests)",
    )
    parser.add_argument(
        "--no-index",
        action="store_true",
        help="Skip index.md if present",
    )
    parser.add_argument(
        "--docs",
        nargs="*",
        metavar="FILE",
        help="Standalone markdown files to ingest to all scientists + codex",
    )
    args = parser.parse_args()

    if not args.archive_dir and not args.docs:
        parser.error("Provide archive_dir and/or --docs")

    loop_filter = set(args.loop) if args.loop else None
    total = {"files": 0, "pages": 0, "codex": 0, "skipped": 0, "by_scientist": {}}

    if args.archive_dir:
        archive = Path(args.archive_dir).expanduser().resolve()
        if not archive.is_dir():
            print(f"❌ Not a directory: {archive}")
            sys.exit(1)
        print(f"🔥 Loop ingest: {archive}")
        print(f"   Lab: {args.lab_id}  |  tag: {args.tag}  |  dry_run: {args.dry_run}")
        if loop_filter:
            print(f"   Filter: loops {sorted(loop_filter)}")

        stats = ingest_archive(
            archive,
            lab_id=args.lab_id,
            dry_run=args.dry_run,
            loop_filter=loop_filter,
            tag=args.tag,
            year=args.year,
            source_label=args.source_label,
            label_prefix=args.label_prefix,
            codex_id_prefix=args.codex_prefix,
            ingest_index=not args.no_index,
        )
        for k in ("files", "pages", "codex", "skipped"):
            total[k] += stats[k]
        for name, count in stats.get("by_scientist", {}).items():
            total["by_scientist"][name] = total["by_scientist"].get(name, 0) + count

    if args.docs:
        doc_paths = [Path(p).expanduser().resolve() for p in args.docs]
        print(f"\n🔥 Document ingest: {len(doc_paths)} file(s)")
        doc_stats = ingest_documents(
            doc_paths,
            lab_id=args.lab_id,
            dry_run=args.dry_run,
            tag=args.tag,
            year=args.year,
            source_label=args.source_label,
            label_prefix=args.label_prefix.replace("Legacy", "R&D") if args.label_prefix == "Legacy" else args.label_prefix,
            codex_id_prefix=f"{args.codex_prefix}-doc",
        )
        total["files"] += doc_stats["files"]
        total["pages"] += doc_stats["pages"]
        total["codex"] += doc_stats["codex"]
        for name, count in doc_stats.get("by_scientist", {}).items():
            total["by_scientist"][name] = total["by_scientist"].get(name, 0) + count

    print("\n" + "=" * 50)
    print(f"✅ Done — {total['pages']} reference pages, {total['codex']} codex pages")
    print(f"   Files processed: {total['files']}  |  skipped: {total['skipped']}")
    if total["by_scientist"]:
        print("   By scientist:")
        for name, count in sorted(total["by_scientist"].items()):
            print(f"     {name:12} {count}")
    if not args.dry_run:
        print("\n   Verify: python3 run_chimera.py --beef-up brian --list-refs")


if __name__ == "__main__":
    main()