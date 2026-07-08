"""
Codex: the searchable collection of research "books" for a lab.

Aggregates scientist books + shared pages.
Used by Oracle for synthesis, by scientists for relevant knowledge, by user for overview.

For Chimera model: one codex per lab, with books for each fixed scientist.
"""
from pathlib import Path
from typing import List, Dict

class Codex:
    def __init__(self, lab_id: str, base_path: Path):
        self.lab_id = lab_id
        self.codex_path = base_path / lab_id / "codex"

    def ensure_structure(self):
        self.codex_path.mkdir(parents=True, exist_ok=True)

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search across the lab's scientist books and shared codex."""
        # TODO: hand-pick/adapt from backup search/search_engine.py
        # Scope to this lab only.
        print(f"[Codex] Lab {self.lab_id}: search '{query}' (stub)")
        return []

    def add_shared_page(self, title: str, content: str, metadata: Dict):
        """For Oracle synthesis or lab-level pages."""
        # TODO: create immutable page with checksum, add to manifest.
        pass
