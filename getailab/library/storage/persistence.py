"""
Storage/Persistence — Rinsed from backup getailab_library/storage/persistence.py + OpenClaw local hackable + old library_vault manifest+sha pattern.

Each scientist book is self-contained:
- book/ dir with pages/, skills/, manifest.json, knowledge.db (SQLite for fast search within book)
- Checksums on everything for provenance/audit.
- Easy to backup, inspect, or move a single scientist's memory.

For the whole lab: codex/ aggregates.
No shared global state that would leak across labs/users.

This is the "local persistent memory that compounds" we stole from the competition, scoped to research-only per-scientist books.
"""
import json
import sqlite3
import hashlib
from pathlib import Path
from typing import Dict, List, Any

class BookPersistence:
    def __init__(self, book_dir: Path):
        self.book_dir = book_dir
        self.pages_dir = book_dir / "pages"
        self.skills_dir = book_dir / "skills"
        self.manifest_path = book_dir / "manifest.json"
        self.db_path = book_dir / "knowledge.db"
        self._ensure()

    def _ensure(self):
        self.pages_dir.mkdir(parents=True, exist_ok=True)
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        if not self.manifest_path.exists():
            self.manifest_path.write_text(json.dumps({"pages": [], "skills": []}, indent=2))
        conn = sqlite3.connect(self.db_path)
        conn.execute("CREATE TABLE IF NOT EXISTS pages (page_id TEXT PRIMARY KEY, content_checksum TEXT, metadata TEXT)")
        conn.execute("CREATE TABLE IF NOT EXISTS skills (skill_id TEXT PRIMARY KEY, description TEXT)")
        conn.close()

    def write_page(self, page: Dict[str, Any]):
        page_file = self.pages_dir / f"{page['page_id']}.json"
        page_file.write_text(json.dumps(page, indent=2))
        (self.pages_dir / f"{page['page_id']}.sha256").write_text(page["content_checksum"])
        # update manifest
        manifest = json.loads(self.manifest_path.read_text())
        manifest["pages"].append(page["page_id"])
        self.manifest_path.write_text(json.dumps(manifest, indent=2))
        # index in sqlite
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT OR REPLACE INTO pages VALUES (?, ?, ?)", (page["page_id"], page["content_checksum"], json.dumps(page.get("metadata", {}))))
        conn.commit()
        conn.close()

    def add_skill(self, skill: Dict[str, Any]):
        skill_file = self.skills_dir / f"{skill['skill_id']}.json"
        skill_file.write_text(json.dumps(skill, indent=2))
        manifest = json.loads(self.manifest_path.read_text())
        manifest["skills"].append(skill["skill_id"])
        self.manifest_path.write_text(json.dumps(manifest, indent=2))
        conn = sqlite3.connect(self.db_path)
        conn.execute("INSERT OR REPLACE INTO skills VALUES (?, ?)", (skill["skill_id"], skill["description"]))
        conn.commit()
        conn.close()

    def reindex_knowledge_db(self) -> int:
        """Rebuild knowledge.db page index from on-disk page JSON files."""
        self._ensure()
        page_ids: List[str] = []
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("DELETE FROM pages")
        for path in sorted(self.pages_dir.glob("*.json")):
            try:
                data = json.loads(path.read_text())
                page_id = data.get("page_id", path.stem)
                content = data.get("content", "")
                checksum = data.get("content_checksum") or hashlib.sha256(
                    content.encode()
                ).hexdigest()
                metadata = {
                    "title": data.get("title"),
                    "page_type": data.get("page_type"),
                    "loop_id": data.get("loop_id"),
                    "tags": data.get("tags", []),
                    **(data.get("metadata") or {}),
                }
                conn.execute(
                    "INSERT OR REPLACE INTO pages VALUES (?, ?, ?)",
                    (page_id, checksum, json.dumps(metadata)),
                )
                page_ids.append(page_id)
            except Exception:
                continue
        conn.commit()
        conn.close()

        manifest = {"pages": [], "skills": []}
        if self.manifest_path.exists():
            try:
                manifest = json.loads(self.manifest_path.read_text())
            except Exception:
                pass
        manifest["pages"] = page_ids
        self.manifest_path.write_text(json.dumps(manifest, indent=2))
        return len(page_ids)

    def get_relevant(self, query: str) -> List[Dict]:
        # Simple FTS-ish via sqlite for now (rinse LangSmith retrieval)
        conn = sqlite3.connect(self.db_path)
        rows = conn.execute("SELECT page_id, metadata FROM pages").fetchall()
        conn.close()
        # In real: full search_engine.py from backup, scoped to this book
        return [{"page_id": r[0], "metadata": json.loads(r[1])} for r in rows if query.lower() in str(r).lower()][:5]
