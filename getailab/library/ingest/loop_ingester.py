"""
Loop Ingester — post-loop archive into per-scientist books + lab codex.
Research knowledge only. Checksums on every page.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from getailab.library.storage.persistence import BookPersistence


def parse_scientists_from_raw(raw_data: str) -> List[str]:
    """Extract scientist names from oracle raw_data blocks like [ALBERT HYPOTHESIS]."""
    names = re.findall(r"\[([A-Z][A-Z]+) HYPOTHESIS\]", raw_data or "", re.I)
    return sorted({n.lower() for n in names if n.lower() != "oracle"})


class LoopIngester:
    def __init__(self, lab_id: str, labs_root: Path):
        self.lab_id = lab_id
        self.lab_path = labs_root / lab_id

    def ingest_loop(
        self,
        loop_id: int,
        problem: str,
        synthesis: str,
        scientist_participants: List[str],
        artifacts: List[Path],
        raw_data: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Archive one completed loop. Returns summary of pages written."""
        metadata = metadata or {}
        written: List[str] = []

        codex_dir = self.lab_path / "codex"
        codex_dir.mkdir(parents=True, exist_ok=True)
        codex_persist = BookPersistence(codex_dir / "book")
        codex_persist._ensure()

        problem_page = self._make_text_page(
            page_id=f"problem-{loop_id}",
            loop_id=loop_id,
            page_type="problem",
            title=f"Problem — Loop {loop_id}",
            content=problem,
            agent="oracle",
            tags=["problem", "codex"],
            metadata={"source": "agora_loops"},
        )
        codex_persist.write_page(problem_page)
        written.append(problem_page["page_id"])

        for scientist in scientist_participants:
            hyp = self._extract_hypothesis(raw_data, scientist)
            if hyp:
                book_persist = self._book_persistence(scientist)
                page = self._make_text_page(
                    page_id=f"hypothesis-{loop_id}-{scientist}",
                    loop_id=loop_id,
                    page_type="hypothesis",
                    title=f"{scientist.title()} hypothesis — Loop {loop_id}",
                    content=hyp,
                    agent=scientist,
                    tags=["hypothesis", scientist],
                )
                book_persist.write_page(page)
                written.append(page["page_id"])

        for scientist in scientist_participants:
            book_persist = self._book_persistence(scientist)
            for art in artifacts:
                if not art.exists():
                    continue
                page = self._make_page_from_artifact(loop_id, scientist, art, metadata)
                book_persist.write_page(page)
                written.append(page["page_id"])
                skills = self._extract_skills_from_artifact(art, loop_id)
                for skill in skills:
                    book_persist.add_skill(skill)

        synth_page = self._make_text_page(
            page_id=f"synthesis-{loop_id}",
            loop_id=loop_id,
            page_type="synthesis",
            title=f"Oracle synthesis — Loop {loop_id}",
            content=synthesis,
            agent="oracle",
            tags=["synthesis", "codex"],
            metadata=metadata,
        )
        codex_persist.write_page(synth_page)
        written.append(synth_page["page_id"])

        manifest_path = self.lab_path / "manifest.json"
        manifest = {"loops": [], "last_ingest": datetime.utcnow().isoformat()}
        if manifest_path.exists():
            try:
                manifest = json.loads(manifest_path.read_text())
            except Exception:
                pass
        if loop_id not in manifest.get("loops", []):
            manifest.setdefault("loops", []).append(loop_id)
        manifest["last_ingest"] = datetime.utcnow().isoformat()
        manifest_path.write_text(json.dumps(manifest, indent=2))

        return {
            "loop_id": loop_id,
            "pages_written": len(written),
            "page_ids": written,
            "scientists": scientist_participants,
            "artifacts": len(artifacts),
        }

    def _book_persistence(self, scientist: str) -> BookPersistence:
        book_dir = self.lab_path / "scientists" / scientist / "book"
        persist = BookPersistence(book_dir)
        persist._ensure()
        return persist

    def _extract_hypothesis(self, raw_data: str, scientist: str) -> str:
        pattern = rf"\[{scientist.upper()} HYPOTHESIS\]:\s*(.*?)(?=\[|\Z)"
        match = re.search(pattern, raw_data, re.I | re.S)
        return match.group(1).strip()[:8000] if match else ""

    def _make_text_page(
        self,
        page_id: str,
        loop_id: int,
        page_type: str,
        title: str,
        content: str,
        agent: str,
        tags: List[str],
        metadata: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        checksum = hashlib.sha256(content.encode()).hexdigest()
        return {
            "page_id": page_id,
            "loop_id": loop_id,
            "page_type": page_type,
            "title": title,
            "content": content,
            "content_checksum": checksum,
            "agent": agent,
            "tags": tags,
            "metadata": metadata or {},
            "created_at": datetime.utcnow().isoformat(),
        }

    def _make_page_from_artifact(
        self, loop_id: int, scientist: str, artifact: Path, metadata: Dict
    ) -> Dict[str, Any]:
        if artifact.suffix.lower() in (".json", ".txt", ".csv", ".py", ".md"):
            content = artifact.read_text(errors="replace")[:50000]
        else:
            content = f"[binary artifact: {artifact.name}]"
        checksum = hashlib.sha256(content.encode()).hexdigest()
        return {
            "page_id": f"artifact-{loop_id}-{scientist}-{artifact.stem}"[:120],
            "loop_id": loop_id,
            "page_type": "artifact",
            "title": f"Artifact: {artifact.name}",
            "content": content,
            "content_checksum": checksum,
            "agent": scientist,
            "tags": ["artifact", scientist],
            "metadata": {
                "source_file": str(artifact),
                "experiment": metadata.get("experiment_name", ""),
            },
            "created_at": datetime.utcnow().isoformat(),
        }

    def _extract_skills_from_artifact(self, artifact: Path, loop_id: int) -> List[Dict]:
        if artifact.suffix.lower() not in (".csv", ".json", ".py"):
            return []
        return [{
            "skill_id": f"skill-{loop_id}-{artifact.stem}"[:80],
            "description": f"Reusable pattern from {artifact.name} (loop {loop_id})",
            "usage": "Reference this artifact structure in future experiments.",
            "source_loop": loop_id,
        }]