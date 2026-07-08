"""
GetAiLab Library — live service wired into Oracle + lab dashboard.

File-based provenance: per-scientist books + lab codex under data/labs/<lab_id>/.
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from getailab.library.ingest.loop_ingester import LoopIngester, parse_scientists_from_raw
from getailab.library.models import LibraryBook, LibraryPage
from getailab.library.ingest.reference_ingester import (
    ingest_scientist_reference,
    list_scientist_references,
    valid_scientist_name,
)
from getailab.library.scientist_book.book import ScientistBook
from getailab.library.storage.persistence import BookPersistence
from personas.loader import get_squad_names

_INSTANCE: Optional["GetAiLabLibrary"] = None
_INSTANCE_LAB_ID: Optional[str] = None


def _active_lab_id(lab_id: Optional[str] = None) -> str:
    if lab_id:
        return lab_id.strip() or "chimera"
    from getailab.lab_config import get_lab_id
    return get_lab_id()


def reset_library_cache() -> None:
    """Drop singleton so next get_library() binds to the current LAB_ID."""
    global _INSTANCE, _INSTANCE_LAB_ID
    _INSTANCE = None
    _INSTANCE_LAB_ID = None


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


class LibraryPersistence:
    """Thin wrapper so dashboard code can read vault_path."""

    def __init__(self, root: Path):
        self.root = root


class GetAiLabLibrary:
    def __init__(
        self,
        lab_id: Optional[str] = None,
        data_root: Optional[Path] = None,
        project_root: Optional[Path] = None,
    ):
        from getailab.lab_config import agora_db_path, lab_artifacts_dir, lab_results_db_path, lab_vault_path

        self.lab_id = _active_lab_id(lab_id)
        self.project_root = project_root or _project_root()
        self.data_root = data_root or (self.project_root / "data")
        self.labs_root = self.data_root / "labs"
        self.lab_path = lab_vault_path(self.lab_id)
        self.artifacts_dir = lab_artifacts_dir(self.lab_id)
        self.lab_db = lab_results_db_path(self.lab_id)
        self._agora_db_resolver = agora_db_path
        self.persistence = LibraryPersistence(self.lab_path)
        self.ingester = LoopIngester(lab_id, self.labs_root)
        self._ensure_structure()

    def _ensure_structure(self):
        for sub in ("scientists", "codex", "artifacts"):
            (self.lab_path / sub).mkdir(parents=True, exist_ok=True)
        (self.lab_path / "codex" / "book").mkdir(parents=True, exist_ok=True)

    # ── Archive (called by Oracle after synthesis) ───────────────────────────

    def _agora_db_path(self) -> Path:
        """Loop record DB for this lab only — never cross-contaminate forged labs."""
        return self._agora_db_resolver(self.lab_id)

    def backfill_historical_loops(self, limit: int = 50) -> Dict[str, Any]:
        """Index past agora_loops from *this lab's* DB into its vault."""
        db_path = self._agora_db_path()
        if not db_path.is_file():
            return {"backfilled": 0, "reason": "no_agora_db"}
        manifest_path = self.lab_path / "manifest.json"
        already = set()
        if manifest_path.exists():
            try:
                already = set(json.loads(manifest_path.read_text()).get("loops", []))
            except Exception:
                pass
        conn = sqlite3.connect(db_path, timeout=10)
        rows = conn.execute(
            """
            SELECT loop_id, problem_statement, consensus_artefact
            FROM agora_loops
            WHERE consensus_artefact IS NOT NULL
            ORDER BY loop_id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
        conn.close()
        count = 0
        for loop_id, problem, synthesis in rows:
            if loop_id in already:
                continue
            self.archive_loop(int(loop_id), problem or "", synthesis or "", raw_data="")
            count += 1
        return {"backfilled": count, "already_indexed": len(already)}

    def archive_loop(
        self,
        loop_id: int,
        problem: str,
        synthesis: str,
        raw_data: str = "",
        participants: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        participants = participants or parse_scientists_from_raw(raw_data)
        if not participants:
            participants = [n for n in get_squad_names() if n != "oracle"]

        artifacts = self._collect_loop_artifacts(loop_id)
        result = self.ingester.ingest_loop(
            loop_id=loop_id,
            problem=problem,
            synthesis=synthesis,
            scientist_participants=participants,
            artifacts=artifacts,
            raw_data=raw_data,
            metadata={
                "problem": problem[:500],
                "archived_at": datetime.utcnow().isoformat(),
                "lab_id": self.lab_id,
            },
        )
        reindex = self.reindex_books(["codex", *participants])
        result["reindex"] = reindex
        try:
            from getailab.integrity.signing import attest_vault

            result["attestation"] = attest_vault(
                self.lab_id,
                loop_id=loop_id,
                project_root=self.project_root,
            )
        except Exception as exc:
            result["attestation"] = {"signed": False, "error": str(exc)}
        return result

    def _collect_loop_artifacts(self, loop_id: int) -> List[Path]:
        paths: List[Path] = []
        loop_dir = self.artifacts_dir / str(loop_id)
        if loop_dir.is_dir():
            for f in loop_dir.rglob("*"):
                if f.is_file() and f.name not in (".gitkeep",):
                    paths.append(f)

        if self.lab_db.exists():
            try:
                conn = sqlite3.connect(self.lab_db, timeout=5)
                rows = conn.execute(
                    "SELECT artifacts_json FROM lab_experiments WHERE loop_id = ?",
                    (str(loop_id),),
                ).fetchall()
                conn.close()
                for (aj,) in rows:
                    if not aj:
                        continue
                    try:
                        for name in json.loads(aj) or []:
                            p = loop_dir / name if loop_dir.exists() else self.artifacts_dir / str(loop_id) / name
                            if p.exists() and p not in paths:
                                paths.append(p)
                    except Exception:
                        pass
            except Exception:
                pass
        return paths

    # ── Read API (dashboard + export) ────────────────────────────────────────

    def _iter_page_files(self) -> List[tuple]:
        """Yield (book_id, path) for every page JSON."""
        found: List[tuple] = []
        codex_pages = self.lab_path / "codex" / "book" / "pages"
        if codex_pages.is_dir():
            for p in codex_pages.glob("*.json"):
                found.append(("codex", p))
        scientists_dir = self.lab_path / "scientists"
        if scientists_dir.is_dir():
            for sci_dir in scientists_dir.iterdir():
                if not sci_dir.is_dir():
                    continue
                pages_dir = sci_dir / "book" / "pages"
                if pages_dir.is_dir():
                    for p in pages_dir.glob("*.json"):
                        found.append((sci_dir.name, p))
        return found

    def _load_page_file(self, book_id: str, path: Path) -> Optional[LibraryPage]:
        try:
            data = json.loads(path.read_text())
            page = LibraryPage.from_dict(data)
            page.book_id = book_id
            return page
        except Exception:
            return None

    def _all_pages(self) -> List[LibraryPage]:
        pages = []
        for book_id, path in self._iter_page_files():
            p = self._load_page_file(book_id, path)
            if p:
                pages.append(p)
        return pages

    def get_page(self, page_id: str) -> Optional[LibraryPage]:
        for book_id, path in self._iter_page_files():
            if path.stem == page_id:
                return self._load_page_file(book_id, path)
        return None

    def get_loop_as_pages(self, loop_id: int) -> List[LibraryPage]:
        return [p for p in self._all_pages() if p.loop_id == loop_id]

    def search(
        self, query: str, filters: Optional[Dict] = None, limit: int = 12
    ) -> List[Dict[str, Any]]:
        filters = filters or {}
        q = (query or "").lower().strip()
        hits: List[Dict[str, Any]] = []
        for page in self._all_pages():
            if filters.get("loop_id") is not None and page.loop_id != filters["loop_id"]:
                continue
            hay = f"{page.title} {page.content} {page.agent} {' '.join(page.tags)}".lower()
            if not q or q in hay:
                hits.append({
                    "page_id": page.page_id,
                    "title": page.title,
                    "loop_id": page.loop_id,
                    "page_type": page.page_type,
                    "agent": page.agent,
                    "book_id": page.book_id,
                    "snippet": page.content[:200],
                    "content_checksum": page.content_checksum,
                })
        return hits[:limit]

    def list_books(self) -> List[LibraryBook]:
        books: List[LibraryBook] = []
        codex_pages = [p.page_id for p in self._all_pages() if p.book_id == "codex"]
        books.append(LibraryBook(
            book_id="codex",
            title=f"{self.lab_id.title()} Codex",
            slug="codex",
            page_ids=codex_pages,
            metadata={"type": "codex", "lab_id": self.lab_id},
        ))
        scientists_dir = self.lab_path / "scientists"
        if scientists_dir.is_dir():
            for sci_dir in sorted(scientists_dir.iterdir()):
                if not sci_dir.is_dir():
                    continue
                name = sci_dir.name
                ids = [p.page_id for p in self._all_pages() if p.book_id == name]
                books.append(LibraryBook(
                    book_id=name,
                    title=f"{name.title()} — Research Book",
                    slug=name,
                    page_ids=ids,
                    metadata={"scientist": name, "lab_id": self.lab_id},
                ))
        return books

    def get_or_create_default_book(self) -> LibraryBook:
        books = self.list_books()
        return books[0] if books else LibraryBook(
            book_id="codex",
            title=f"{self.lab_id.title()} Codex",
            slug="codex",
        )

    def get_recent_library_summary(self, limit: int = 6) -> Dict[str, Any]:
        pages = sorted(self._all_pages(), key=lambda p: p.created_at, reverse=True)
        recent = pages[:limit]
        loop_ids = {p.loop_id for p in pages if p.loop_id}
        return {
            "total_pages": len(pages),
            "loops_indexed": len(loop_ids),
            "inspiration": min(99, 60 + len(pages) // 2),
            "recent_pages": [
                {
                    "page_id": p.page_id,
                    "title": p.title,
                    "loop_id": p.loop_id,
                    "page_type": p.page_type,
                    "agent": p.agent,
                }
                for p in recent
            ],
        }

    def prepare_loop_export_data(self, loop_id: int) -> Dict[str, Any]:
        pages = self.get_loop_as_pages(loop_id)
        problem = ""
        synthesis = ""
        for p in pages:
            if p.page_type == "problem":
                problem = p.content
            elif p.page_type == "synthesis":
                synthesis = p.content
        if not problem or not synthesis:
            db_path = self._agora_db_path()
            if db_path.is_file():
                try:
                    conn = sqlite3.connect(db_path, timeout=5)
                    row = conn.execute(
                        "SELECT problem_statement, consensus_artefact FROM agora_loops WHERE loop_id = ?",
                        (loop_id,),
                    ).fetchone()
                    conn.close()
                    if row:
                        problem = problem or (row[0] or "")
                        synthesis = synthesis or (row[1] or "")
                except Exception:
                    pass
        artifacts_list = [
            p.metadata.get("source_file", p.title)
            for p in pages if p.page_type == "artifact"
        ]
        return {
            "id": loop_id,
            "problem": problem,
            "synthesis": synthesis,
            "full_report": synthesis,
            "artifacts": len(artifacts_list),
            "artifacts_list": artifacts_list,
            "page_count": len(pages),
        }

    def _book_dir(self, book_id: str) -> Path:
        if book_id == "codex":
            return self.lab_path / "codex" / "book"
        return self.lab_path / "scientists" / book_id / "book"

    def reindex_book(self, book_id: str) -> int:
        """Rebuild SQLite index for one book (codex or scientist name)."""
        book_dir = self._book_dir(book_id)
        if not book_dir.is_dir():
            return 0
        return BookPersistence(book_dir).reindex_knowledge_db()

    def reindex_books(self, book_ids: List[str]) -> Dict[str, Any]:
        """Reindex a specific set of books."""
        books: Dict[str, int] = {}
        for book_id in dict.fromkeys(book_ids):
            book_dir = self._book_dir(book_id)
            if not book_dir.is_dir():
                continue
            books[book_id] = self.reindex_book(book_id)
        return {
            "lab_id": self.lab_id,
            "books": books,
            "total_pages_indexed": sum(books.values()),
        }

    def reindex_all_books(self) -> Dict[str, Any]:
        """Rebuild SQLite indexes for codex and every scientist book."""
        book_ids = ["codex"]
        scientists_dir = self.lab_path / "scientists"
        if scientists_dir.is_dir():
            book_ids.extend(
                sorted(
                    d.name for d in scientists_dir.iterdir()
                    if d.is_dir() and (d / "book").is_dir()
                )
            )
        return self.reindex_books(book_ids)

    def repair_checksums(self) -> int:
        """Recompute checksums from stored content (fixes legacy truncate mismatches)."""
        import hashlib
        fixed = 0
        for _book_id, path in self._iter_page_files():
            try:
                data = json.loads(path.read_text())
                content = data.get("content", "")
                actual = hashlib.sha256(content.encode()).hexdigest()
                if data.get("content_checksum") != actual:
                    data["content_checksum"] = actual
                    path.write_text(json.dumps(data, indent=2))
                    fixed += 1
                sidecar = path.parent / f"{path.stem}.sha256"
                sidecar.write_text(actual)
            except Exception:
                pass
        if fixed:
            self.reindex_all_books()
        return fixed

    def verify_library_integrity(
        self,
        book: Optional[LibraryBook] = None,
        *,
        include_indexes: bool = True,
    ) -> Dict[str, Any]:
        """
        Crush-test every library page: on-disk content hash must match stored checksum.

        Returns Old Mate-style integrity PASS/FAIL plus structured mismatch objects.
        Legacy fields (ok, checked, valid, failures) are preserved for existing API clients.
        """
        from getailab.integrity.verify import crush_test_indexes, crush_test_vault

        book_filter: Optional[str] = None
        if book and book.book_id != "codex":
            book_filter = book.book_id

        pages = crush_test_vault(
            self.lab_id,
            book_id=book_filter,
            project_root=self.project_root,
        )

        failures: List[str] = []
        for item in pages.get("mismatches", []):
            failures.append(
                f"{item['page_id']}: checksum mismatch "
                f"(expected {item['expected'][:12]}… actual {item['actual'][:12]}…)"
            )
        for item in pages.get("missing", []):
            failures.append(f"{item['page_id']}: missing ({item['file_path']})")
        for item in pages.get("sidecar_issues", []):
            if "expected" in item and "actual" in item:
                failures.append(
                    f"{item['page_id']}: sidecar mismatch "
                    f"(expected {item['expected'][:12]}… actual {item['actual'][:12]}…)"
                )
            else:
                failures.append(f"{item['page_id']}: {item.get('detail', 'sidecar issue')}")
        for item in pages.get("read_errors", []):
            failures.append(f"{item.get('page_id', '?')}: {item.get('detail', 'read error')}")

        integrity = pages.get("integrity", "FAIL")
        report: Dict[str, Any] = {
            "integrity": integrity,
            "ok": integrity == "PASS",
            "checked": pages.get("total", 0),
            "valid": pages.get("verified", 0),
            "failures": failures[:20],
            "mismatches": pages.get("mismatches", []),
            "missing": pages.get("missing", []),
            "sidecar_issues": pages.get("sidecar_issues", []),
            "read_errors": pages.get("read_errors", []),
            "lab_id": self.lab_id,
            "vault": pages.get("vault", str(self.lab_path)),
            "book_filter": book_filter,
            "timestamp": pages.get("timestamp"),
        }

        if include_indexes and book_filter is None:
            indexes = crush_test_indexes(self.lab_id, project_root=self.project_root)
            report["indexes"] = indexes
            if indexes.get("integrity") != "PASS":
                report["integrity"] = "FAIL"
                report["ok"] = False
                for item in indexes.get("stale_index", []):
                    failures.append(
                        f"{item['book_id']}/{item['page_id']}: index stale "
                        f"(expected {item['expected'][:12]}… actual {item['actual'][:12]}…)"
                    )
                for item in indexes.get("missing_index", []):
                    failures.append(
                        f"{item['book_id']}/{item['page_id']}: missing from index"
                    )
                for item in indexes.get("orphan_index", []):
                    failures.append(
                        f"{item['book_id']}/{item['page_id']}: orphan index entry"
                    )
                report["failures"] = failures[:20]

        return report


def get_library(lab_id: Optional[str] = None, backfill: bool = True) -> GetAiLabLibrary:
    """Singleton library instance for the active lab (never shares vault across departments)."""
    global _INSTANCE, _INSTANCE_LAB_ID
    lid = _active_lab_id(lab_id)
    if _INSTANCE is None or _INSTANCE_LAB_ID != lid:
        _INSTANCE = GetAiLabLibrary(lab_id=lid)
        _INSTANCE_LAB_ID = lid
        if backfill:
            try:
                result = _INSTANCE.backfill_historical_loops()
                if result.get("backfilled"):
                    print(f"[GetAiLabLibrary] Backfilled {result['backfilled']} historical loops")
                repaired = _INSTANCE.repair_checksums()
                if repaired:
                    print(f"[GetAiLabLibrary] Repaired {repaired} page checksums")
                reindexed = _INSTANCE.reindex_all_books()
                if reindexed.get("total_pages_indexed"):
                    print(
                        f"[GetAiLabLibrary] Reindexed {reindexed['total_pages_indexed']} pages "
                        f"across {len(reindexed.get('books', {}))} books"
                    )
            except Exception as e:
                print(f"[GetAiLabLibrary] Backfill skipped: {e}")
    return _INSTANCE


def archive_completed_loop(
    loop_id: int,
    problem: str,
    synthesis: str,
    raw_data: str = "",
    **kwargs,
) -> Dict[str, Any]:
    """Convenience hook for Oracle synthesize route."""
    lid = _active_lab_id(kwargs.pop("lab_id", None))
    return get_library(lab_id=lid, backfill=False).archive_loop(
        loop_id=loop_id,
        problem=problem,
        synthesis=synthesis,
        raw_data=raw_data,
        participants=kwargs.get("participants"),
    )


def get_scientist_book(
    scientist_name: str,
    lab_id: Optional[str] = None,
) -> ScientistBook:
    """Return the live ScientistBook for one squad member in the active lab."""
    lib = get_library(lab_id=lab_id, backfill=False)
    return ScientistBook(
        lab_id=lib.lab_id,
        scientist_name=scientist_name,
        base_path=lib.data_root,
    )


def add_scientist_reference(
    scientist_name: str,
    *,
    title: str = "",
    content: str = "",
    url: str = "",
    tags: Optional[List[str]] = None,
    lab_id: Optional[str] = None,
    source_label: str = "user",
) -> Dict[str, Any]:
    """Add user reference material to a scientist's book."""
    lid = _active_lab_id(lab_id)
    return ingest_scientist_reference(
        scientist_name,
        title=title,
        content=content,
        url=url,
        tags=tags,
        lab_id=lid,
        source_label=source_label,
    )


def reindex_library(lab_id: Optional[str] = None) -> Dict[str, Any]:
    """Rebuild all scientist book + codex SQLite indexes for a lab."""
    return get_library(lab_id=lab_id, backfill=False).reindex_all_books()


def get_scientist_references(
    scientist_name: str,
    *,
    query: str = "",
    limit: int = 20,
    lab_id: Optional[str] = None,
) -> Dict[str, Any]:
    """List reference pages for one scientist."""
    lid = _active_lab_id(lab_id)
    return list_scientist_references(
        scientist_name,
        lab_id=lid,
        query=query,
        limit=limit,
    )


def archive_collaborative_review(
    *,
    review_id: str,
    working_question: str = "",
    materials_summary: str = "",
    raw_reviews: str = "",
    synthesis: str = "",
    scientist_participants: Optional[List[str]] = None,
    lab_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist a collaborative review session to codex + per-scientist review pages."""
    lid = _active_lab_id(lab_id)
    lib = get_library(lab_id=lid, backfill=False)
    ingester = lib.ingester
    codex_persist = BookPersistence(lib.lab_path / "codex" / "book")
    codex_persist._ensure()

    slug = re.sub(r"[^a-z0-9]+", "-", review_id.lower()).strip("-")[:60] or "review"
    written: List[str] = []

    if working_question:
        q_page = ingester._make_text_page(
            page_id=f"review-question-{slug}"[:120],
            loop_id=0,
            page_type="problem",
            title=f"Working question — {review_id}",
            content=working_question,
            agent="oracle",
            tags=["review", "codex", "working-question"],
            metadata={"review_id": review_id, "source": "collaborative_review"},
        )
        codex_persist.write_page(q_page)
        written.append(q_page["page_id"])

    if materials_summary:
        m_page = ingester._make_text_page(
            page_id=f"review-materials-{slug}"[:120],
            loop_id=0,
            page_type="reference",
            title=f"Review materials — {review_id}",
            content=materials_summary[:80000],
            agent="oracle",
            tags=["review", "codex", "materials"],
            metadata={"review_id": review_id, "source": "collaborative_review"},
        )
        codex_persist.write_page(m_page)
        written.append(m_page["page_id"])

    participants = scientist_participants or []
    if not participants and raw_reviews:
        participants = sorted({
            m.group(1).lower()
            for m in re.finditer(r"\[([A-Z][A-Z]+) REVIEW\]", raw_reviews, re.I)
            if m.group(1).lower() != "oracle"
        })

    for scientist in participants:
        pattern = rf"\[{scientist.upper()} REVIEW\]:\s*(.*?)(?=\[[A-Z]|\Z)"
        match = re.search(pattern, raw_reviews, re.I | re.S)
        if not match:
            continue
        body = match.group(1).strip()
        if not body:
            continue
        book_persist = ingester._book_persistence(scientist)
        page = ingester._make_text_page(
            page_id=f"review-{slug}-{scientist}"[:120],
            loop_id=0,
            page_type="reference",
            title=f"{scientist.title()} review — {review_id}",
            content=body[:80000],
            agent=scientist,
            tags=["review", scientist],
            metadata={"review_id": review_id, "source": "collaborative_review"},
        )
        book_persist.write_page(page)
        written.append(page["page_id"])

    if synthesis:
        synth_page = ingester._make_text_page(
            page_id=f"review-synthesis-{slug}"[:120],
            loop_id=0,
            page_type="synthesis",
            title=f"Oracle review synthesis — {review_id}",
            content=synthesis,
            agent="oracle",
            tags=["review", "synthesis", "codex"],
            metadata={"review_id": review_id, "source": "collaborative_review"},
        )
        codex_persist.write_page(synth_page)
        written.append(synth_page["page_id"])

    lib.reindex_all_books()

    return {
        "review_id": review_id,
        "lab_id": lid,
        "pages_written": len(written),
        "page_ids": written,
        "scientists": participants,
    }