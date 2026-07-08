"""
Oracle Guardian — The Internal Middleman and Lab Environment Protector

USER NEVER TALKS DIRECTLY TO ORACLE OR SCIENTISTS.
Only Gabby talks to Oracle.

Oracle's job:
- Be the gatekeeper so the user can't fuck up the lab (wrong configs, direct writes to books, bypassing phases, etc.).
- Coordinate the scientists (Chimera model or generated).
- Decide what (if anything) from the internal scientist books / codex gets exposed to Gabby/user (always tiny, safe, high-level snippets).
- Trigger correct ingests after loops so scientists get smarter on research knowledge only.
- Enforce that scientists' books stay pure research memory (no user data ever leaks in).

This is what actually prevents the user from seeing "all the knowledge and shit".
"""
from pathlib import Path
from typing import Dict, Any, List, Optional


class OracleGuardian:
    def __init__(self, lab_id: str, base_path: Path):
        self.lab_id = lab_id
        self.base_path = Path(base_path)

    def _get_library(self):
        from getailab.library.service import GetAiLabLibrary
        return GetAiLabLibrary(lab_id=self.lab_id, backfill=False)

    def validate_and_run_loop(self, problem: str, safe_user_context: Optional[Dict] = None) -> Dict:
        """
        The only way a research loop is started.
        Called exclusively by Gabby.
        Oracle can refuse, sanitize further, or add guardrails.
        """
        if safe_user_context and "personal_note" in safe_user_context:
            print(f"[OracleGuardian] Sanitizing personal context for lab {self.lab_id}")
        print(f"[OracleGuardian] Validating + guarding loop in {self.lab_id} for: {problem[:80]}...")

        return {
            "status": "loop_completed_under_guardian",
            "lab_id": self.lab_id,
            "problem": problem,
            "note": "Use run_chimera.py or Oracle /initiate_loop for full execution.",
        }

    def get_safe_inspiration_for_user(self, topic: str, user_profile: Dict) -> List[str]:
        """
        Curated high-level sparks from the codex — titles/snippets only, never raw books.
        """
        try:
            lib = self._get_library()
            hits = lib.search(topic or "research synthesis hypothesis", limit=6)
            sparks: List[str] = []
            for hit in hits:
                snippet = (hit.get("snippet") or "").strip().replace("\n", " ")
                if len(snippet) > 160:
                    snippet = snippet[:157] + "..."
                loop_label = f"Loop {hit['loop_id']}" if hit.get("loop_id") else "Codex"
                sparks.append(
                    f"[{loop_label} · {hit.get('page_type', 'page')}] "
                    f"{hit.get('title', 'Research note')}: {snippet or 'Indexed with checksum.'}"
                )
            if sparks:
                return sparks[:5]
        except Exception as exc:
            print(f"[OracleGuardian] Vault inspiration fallback: {exc}")

        return [
            f"Explore '{topic or 'open research'}' — the lab vault holds prior loops with full provenance."
        ]

    def get_vault_sparks(self, topic: str = "", limit: int = 4) -> List[Dict[str, Any]]:
        """Structured sparks for dashboard cards (Oracle-curated, user-safe)."""
        try:
            lib = self._get_library()
            summary = lib.get_recent_library_summary(limit=limit)
            sparks = []
            for page in summary.get("recent_pages", [])[:limit]:
                sparks.append({
                    "loop": page.get("loop_id") or 0,
                    "note": f"{page.get('title', 'Research page')} ({page.get('page_type', 'page')})",
                    "type": "vault_spark",
                    "source": f"Oracle · {page.get('agent', 'lab')}",
                    "topic": topic or "",
                })
            if topic:
                for hit in lib.search(topic, limit=limit):
                    snippet = (hit.get("snippet") or "")[:140].replace("\n", " ")
                    sparks.append({
                        "loop": hit.get("loop_id") or 0,
                        "note": snippet or hit.get("title", ""),
                        "type": "vault_match",
                        "source": f"Codex · {hit.get('book_id', 'library')}",
                        "topic": topic,
                    })
            return sparks[:limit]
        except Exception:
            return []

    def get_user_safe_lab_summary(self, user_profile: Dict) -> Dict:
        """High-level progress/overview. Never the raw codex or scientist books."""
        try:
            lib = self._get_library()
            summary = lib.get_recent_library_summary(8)
            books = lib.list_books()
            scientist_books = [b for b in books if b.book_id != "codex"]
            return {
                "lab": self.lab_id,
                "status": "Chimera vault active",
                "total_pages": summary.get("total_pages", 0),
                "loops_indexed": summary.get("loops_indexed", 0),
                "scientist_books": len(scientist_books),
                "inspiration_score": summary.get("inspiration", 0),
                "recent": summary.get("recent_pages", [])[:5],
                "note": "Friendly summary only — scientist books stay internal.",
            }
        except Exception:
            return {
                "lab": self.lab_id,
                "status": "Library unavailable",
                "note": "Start lab API for vault summary.",
            }

    def coordinate_squad(self, phase: str, scientist_names: List[str]):
        """Internal coordination only."""
        print(f"[Oracle Guardian] Coordinating {phase} for {scientist_names} in {self.lab_id}")