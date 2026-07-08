"""
ScientistBook: the persistent memory knowledge base for ONE scientist in ONE lab.

CRITICAL ISOLATION:
- This book contains ONLY research knowledge (artifacts, hypotheses, synthesis slices,
  insights from loops that this scientist participated in).
- Scientists use this internally to "get smarter" on their domain.
- THE USER DOES NOT EXIST TO THE SCIENTIST. No user profile, no personal data,
  no engagement history ever goes into a scientist's book.
- Direct/raw access to the full book is INTERNAL ONLY (called by the scientist
  during a loop or by Oracle for coordination).
- User never sees the raw book. Gabby only ever gets sanitized, high-level,
  user-appropriate views (e.g. "inspiration from this lab's research").

This is how we prevent the user from just dumping "all the knowledge and shit".
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from getailab.library.models import LibraryPage
from getailab.library.storage.persistence import BookPersistence

_PAGE_TYPE_BOOST = {
    "reference": 2.0,
    "hypothesis": 1.6,
    "artifact": 1.0,
    "synthesis": 0.6,
    "problem": 0.4,
    "general": 0.8,
}

_SNIPPET_LIMITS = {
    "reference": 2500,
    "hypothesis": 2000,
    "artifact": 1800,
    "synthesis": 1500,
    "problem": 1200,
}


class ScientistBook:
    def __init__(self, lab_id: str, scientist_name: str, base_path: Path):
        self.lab_id = lab_id
        self.scientist_name = scientist_name.lower().strip()
        self.base_path = Path(base_path)
        self.book_path = self.base_path / "labs" / lab_id / "scientists" / self.scientist_name / "book"
        self.pages_path = self.book_path / "pages"
        self.manifest_path = self.book_path / "manifest.json"
        self.db_path = self.book_path / "knowledge.db"
        self._persistence: Optional[BookPersistence] = None

    @property
    def persistence(self) -> BookPersistence:
        if self._persistence is None:
            self._persistence = BookPersistence(self.book_path)
        return self._persistence

    def ensure_structure(self) -> None:
        self.persistence._ensure()

    # ── Page I/O ─────────────────────────────────────────────────────────────

    def _load_page(self, path: Path) -> Optional[LibraryPage]:
        """Load page JSON only if on-disk content passes crush test (checksum match)."""
        try:
            data = json.loads(path.read_text())
            expected = data.get("content_checksum", "")
            if expected:
                actual = hashlib.sha256(data.get("content", "").encode()).hexdigest()
                if actual != expected:
                    print(
                        f"[ScientistBook] Crush test FAIL — skipping tampered page "
                        f"{data.get('page_id', path.stem)} in {self.scientist_name}"
                    )
                    return None
            page = LibraryPage.from_dict(data)
            page.book_id = self.scientist_name
            return page
        except Exception:
            return None

    def _all_pages(self) -> List[LibraryPage]:
        if not self.pages_path.is_dir():
            return []
        pages: List[LibraryPage] = []
        for path in sorted(self.pages_path.glob("*.json")):
            page = self._load_page(path)
            if page:
                pages.append(page)
        return pages

    def get_page(self, page_id: str) -> Optional[LibraryPage]:
        path = self.pages_path / f"{page_id}.json"
        return self._load_page(path) if path.exists() else None

    def page_count(self) -> int:
        return len(list(self.pages_path.glob("*.json"))) if self.pages_path.is_dir() else 0

    def loops_contributed(self) -> List[int]:
        loops = {p.loop_id for p in self._all_pages() if p.loop_id is not None}
        return sorted(loops)

    # ── Search & retrieval ───────────────────────────────────────────────────

    def _tokenize(self, text: str) -> List[str]:
        return [t for t in re.split(r"\W+", (text or "").lower()) if len(t) > 2]

    def _score_page(self, page: LibraryPage, terms: List[str]) -> float:
        if not terms:
            return float(page.loop_id or 0)

        hay_title = page.title.lower()
        hay_tags = " ".join(page.tags).lower()
        hay_content = page.content.lower()
        hay_type = page.page_type.lower()

        score = 0.0
        for term in terms:
            if term in hay_title:
                score += 3.0
            if term in hay_tags:
                score += 2.0
            if term in hay_type:
                score += 1.5
            if term in hay_content:
                score += 1.0
                score += min(hay_content.count(term) * 0.15, 1.5)

        score *= _PAGE_TYPE_BOOST.get(page.page_type, 1.0)
        if page.loop_id:
            score += page.loop_id * 0.001
        return score

    def search(
        self,
        query: str,
        *,
        limit: int = 8,
        page_types: Optional[List[str]] = None,
        exclude_loop_id: Optional[int] = None,
        min_score: float = 0.0,
    ) -> List[Dict[str, Any]]:
        """
        Ranked keyword search within this scientist's book only.
        Returns dicts with page metadata + relevance score + snippet.
        """
        terms = self._tokenize(query)
        allowed = {t.lower() for t in page_types} if page_types else None
        hits: List[Dict[str, Any]] = []

        for page in self._all_pages():
            if exclude_loop_id is not None and page.loop_id == exclude_loop_id:
                continue
            if allowed and page.page_type not in allowed:
                continue

            score = self._score_page(page, terms)
            if terms and score <= min_score:
                continue

            snippet_limit = _SNIPPET_LIMITS.get(page.page_type, 1200)
            hits.append({
                "page_id": page.page_id,
                "title": page.title,
                "loop_id": page.loop_id,
                "page_type": page.page_type,
                "agent": page.agent,
                "tags": page.tags,
                "score": round(score, 3),
                "snippet": page.content[:snippet_limit],
                "content_checksum": page.content_checksum,
                "created_at": page.created_at,
            })

        hits.sort(key=lambda h: h["score"], reverse=True)
        return hits[:limit]

    def get_research_context(
        self,
        query: str,
        *,
        problem_statement: str = "",
        limit: int = 5,
        max_chars: int = 12000,
        exclude_loop_id: Optional[int] = None,
        page_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Build a prompt-ready context block from this scientist's prior research.
        Merges query + problem_statement for retrieval breadth.
        """
        combined_query = " ".join(
            part for part in (query, problem_statement) if part and part.strip()
        ).strip()
        if not page_types:
            page_types = ["reference", "hypothesis", "artifact"]

        hits = self.search(
            combined_query or "research experiment hypothesis",
            limit=limit,
            page_types=page_types,
            exclude_loop_id=exclude_loop_id,
        )
        if not hits and combined_query:
            hits = self.search(
                combined_query,
                limit=limit,
                exclude_loop_id=exclude_loop_id,
            )
        if not hits:
            hits = self.search(
                "",
                limit=min(limit, 3),
                exclude_loop_id=exclude_loop_id,
            )

        sections: List[str] = []
        used = 0
        sources: List[Dict[str, Any]] = []

        header = (
            f"=== RESEARCH MEMORY ({self.scientist_name.title()} / {self.lab_id}) ===\n"
            f"Retrieved for: {combined_query[:200] or 'general prior work'}\n"
        )
        sections.append(header)
        used += len(header)

        sanitize_albert = self.scientist_name.lower() == "albert"
        if sanitize_albert:
            from personas.loader import sanitize_albert_persona_labels

        for hit in hits:
            loop_label = f"Loop {hit['loop_id']}" if hit.get("loop_id") else "Prior"
            snippet = hit["snippet"]
            if sanitize_albert:
                snippet = sanitize_albert_persona_labels(snippet)
            block = (
                f"\n[{loop_label} | {hit['page_type']}] {hit['title']}\n"
                f"{snippet}\n"
            )
            if used + len(block) > max_chars:
                remaining = max_chars - used - 40
                if remaining > 200:
                    block = block[:remaining] + "\n...[truncated]\n"
                else:
                    break
            sections.append(block)
            used += len(block)
            sources.append({
                "page_id": hit["page_id"],
                "title": hit["title"],
                "loop_id": hit.get("loop_id"),
                "page_type": hit["page_type"],
                "score": hit["score"],
            })

        sections.append("=== END RESEARCH MEMORY ===\n")
        context_text = "".join(sections)

        return {
            "scientist": self.scientist_name,
            "lab_id": self.lab_id,
            "query": combined_query,
            "pages_found": len(sources),
            "context_text": context_text,
            "sources": sources,
        }

    def skill_count(self) -> int:
        skills_dir = self.book_path / "skills"
        return len(list(skills_dir.glob("*.json"))) if skills_dir.is_dir() else 0

    def get_skills_context(
        self,
        query: str,
        *,
        limit: int = 5,
        exclude_loop_id: Optional[int] = None,
        max_chars: int = 4000,
    ) -> Dict[str, Any]:
        """
        Retrieve reusable experiment skills/patterns from this scientist's book.
        Written on loop ingest; injected during /implement (and lightly at /hypothesis).
        """
        skills_dir = self.book_path / "skills"
        if not skills_dir.is_dir():
            return {
                "scientist": self.scientist_name,
                "skills_found": 0,
                "context_text": "",
                "sources": [],
            }

        terms = self._tokenize(query)
        hits: List[Dict[str, Any]] = []

        for path in sorted(skills_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text())
            except Exception:
                continue
            source_loop = data.get("source_loop")
            if exclude_loop_id is not None and source_loop == exclude_loop_id:
                continue

            hay = " ".join(
                str(data.get(k, "")) for k in ("skill_id", "description", "usage")
            ).lower()
            score = 0.0
            if not terms:
                score = float(source_loop or 0)
            else:
                for term in terms:
                    if term in hay:
                        score += 2.0 if term in (data.get("skill_id") or "").lower() else 1.0

            if score > 0 or not terms:
                hits.append({
                    "skill_id": data.get("skill_id", path.stem),
                    "description": data.get("description", ""),
                    "usage": data.get("usage", ""),
                    "source_loop": source_loop,
                    "score": score,
                })

        hits.sort(key=lambda h: h["score"], reverse=True)
        hits = hits[:limit]

        lines = [
            f"=== REUSABLE SKILLS ({self.scientist_name.title()} / {self.lab_id}) ===\n",
            f"Matched for: {(query or 'prior experiments')[:120]}\n",
        ]
        used = len("".join(lines))
        sources: List[Dict[str, Any]] = []

        for hit in hits:
            block = (
                f"\n[Loop {hit.get('source_loop') or '?'}] {hit['skill_id']}\n"
                f"  {hit['description']}\n"
                f"  Usage: {hit['usage']}\n"
            )
            if used + len(block) > max_chars:
                break
            lines.append(block)
            used += len(block)
            sources.append({
                "skill_id": hit["skill_id"],
                "source_loop": hit.get("source_loop"),
                "score": hit["score"],
            })

        lines.append("=== END SKILLS ===\n")
        return {
            "scientist": self.scientist_name,
            "lab_id": self.lab_id,
            "query": query,
            "skills_found": len(sources),
            "context_text": "".join(lines),
            "sources": sources,
        }

    # === INTERNAL ONLY (scientists + Oracle during loops) ===

    def _get_relevant_knowledge_internal(
        self, query: str, limit: int = 5, exclude_loop_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Called by the scientist (during their phase) or by Oracle.
        Returns raw research knowledge from THIS scientist's book only.
        """
        return self.search(query, limit=limit, exclude_loop_id=exclude_loop_id)

    # ── Ingest & reference material ────────────────────────────────────────────

    def reindex(self) -> int:
        """Sync knowledge.db index from on-disk page JSON files."""
        self.ensure_structure()
        return self.persistence.reindex_knowledge_db()

    def add_reference_page(
        self,
        title: str,
        content: str,
        *,
        source: str = "user",
        url: str = "",
        tags: Optional[List[str]] = None,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Add user-sourced reference material to this scientist's book.
        Research knowledge only — no user profile fields.
        """
        self.ensure_structure()
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:40] or "note"
        page_id = f"reference-{self.scientist_name}-{slug}-{int(datetime.utcnow().timestamp())}"
        checksum = hashlib.sha256(content.encode()).hexdigest()
        metadata: Dict[str, Any] = {
            "source": source,
            "ingested_at": datetime.utcnow().isoformat(),
        }
        if url:
            metadata["url"] = url
        if extra_metadata:
            metadata.update(extra_metadata)
        page = {
            "page_id": page_id,
            "loop_id": None,
            "page_type": "reference",
            "title": title,
            "content": content,
            "content_checksum": checksum,
            "agent": self.scientist_name,
            "tags": ["reference", self.scientist_name] + (tags or []),
            "metadata": metadata,
            "created_at": datetime.utcnow().isoformat(),
        }
        self.persistence.write_page(page)
        return page

    def ingest_research_from_loop(
        self,
        loop_id: int,
        artifacts: List[Path],
        relevant_synthesis: str,
        metadata: Dict,
    ) -> Dict[str, Any]:
        """
        Post-loop ingest hook for Oracle. Primary archive path is GetAiLabLibrary.archive_loop;
        this method reindexes the book and optionally stores a synthesis slice for this scientist.
        """
        written: List[str] = []
        if relevant_synthesis and relevant_synthesis.strip():
            page_id = f"synthesis-slice-{loop_id}-{self.scientist_name}"
            existing = self.get_page(page_id)
            if not existing:
                content = relevant_synthesis.strip()[:8000]
                checksum = hashlib.sha256(content.encode()).hexdigest()
                page = {
                    "page_id": page_id,
                    "loop_id": loop_id,
                    "page_type": "synthesis",
                    "title": f"Synthesis slice — Loop {loop_id}",
                    "content": content,
                    "content_checksum": checksum,
                    "agent": "oracle",
                    "tags": ["synthesis", self.scientist_name],
                    "metadata": {**metadata, "slice": True},
                    "created_at": datetime.utcnow().isoformat(),
                }
                self.persistence.write_page(page)
                written.append(page_id)

        indexed = self.reindex()
        return {
            "scientist": self.scientist_name,
            "loop_id": loop_id,
            "pages_written": len(written),
            "page_ids": written,
            "artifacts_noted": len(artifacts),
            "indexed_pages": indexed,
        }

    # === USER-FACING (via Gabby only) ===

    def get_high_level_summary_for_gabby(self) -> Dict:
        loops = self.loops_contributed()
        pages = self._all_pages()
        type_counts: Dict[str, int] = {}
        tag_counts: Dict[str, int] = {}
        for p in pages:
            type_counts[p.page_type] = type_counts.get(p.page_type, 0) + 1
            for tag in p.tags:
                if tag in (self.scientist_name, "artifact", "codex"):
                    continue
                tag_counts[tag] = tag_counts.get(tag, 0) + 1

        top_tags = sorted(tag_counts, key=tag_counts.get, reverse=True)[:6]
        themes = top_tags if top_tags else ["research themes from archived loops"]

        return {
            "scientist": self.scientist_name,
            "lab": self.lab_id,
            "loops_contributed": len(loops),
            "loop_ids": loops[-8:],
            "page_count": len(pages),
            "page_types": type_counts,
            "themes": themes,
            "note": "High-level summary only. Raw research knowledge stays internal to the scientist.",
        }

    def get_inspiration_snippet_for_gabby(self, topic: str) -> str:
        hits = self.search(topic, limit=1, page_types=["hypothesis", "reference", "synthesis"])
        if not hits:
            hits = self.search(topic, limit=1)
        if not hits:
            return (
                f"{self.scientist_name.title()} has prior research in {self.lab_id}, "
                f"but nothing closely matched '{topic}' yet."
            )
        hit = hits[0]
        snippet = hit["snippet"][:400].strip()
        if len(hit["snippet"]) > 400:
            snippet += "..."
        loop_part = f" (loop {hit['loop_id']})" if hit.get("loop_id") else ""
        return (
            f"Inspiration from {self.scientist_name.title()}'s past work{loop_part}: "
            f"{snippet}"
        )


def get_scientist_book(
    scientist_name: str,
    lab_id: str = "example",
    base_path: Optional[Path] = None,
) -> ScientistBook:
    """Factory for a scientist's book under data/labs/<lab_id>/scientists/<name>/book/."""
    if base_path is None:
        base_path = Path(__file__).resolve().parents[3] / "data"
    return ScientistBook(lab_id=lab_id, scientist_name=scientist_name, base_path=base_path)