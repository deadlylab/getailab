"""
Per-lab section management.

Each lab gets its own isolated section with books for its scientists.
Chimera is the model lab (id='chimera' or similar).
Generated labs get their own.

This ensures no cross-lab pollution.
"""
from pathlib import Path
from typing import Dict, Optional

class LabSection:
    def __init__(self, lab_id: str, base_path: Path):
        self.lab_id = lab_id
        self.base_path = base_path / lab_id
        self.books_path = self.base_path / "scientists"
        self.codex_path = self.base_path / "codex"
        self.artifacts_path = self.base_path / "artifacts"
        self.config_path = self.base_path / "config"

    def ensure_structure(self):
        for p in [self.books_path, self.codex_path, self.artifacts_path, self.config_path]:
            p.mkdir(parents=True, exist_ok=True)
        # Each scientist gets a book dir
        # (populated when scientists are loaded for this lab)

    def get_scientist_book_path(self, scientist_name: str) -> Path:
        return self.books_path / scientist_name / "book"

    # TODO: hand-pick and adapt storage/ingest from backup here.
    # Scientists only see their book + lab codex. No user data.
