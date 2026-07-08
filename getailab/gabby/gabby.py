"""
Gabby - User Profile and Engagement Layer

THE ONLY THING THE USER TALKS TO.

Gabby:
- Knows the user (profile, history, preferences, engagement).
- Handles personal context ("family history", "no idea" starters with user flavor).
- Can ask high-level, safe questions of the library (via Oracle).
- NEVER gives the user raw access to scientist books, full codex, or internal research knowledge.

What prevents the user from "seeing all the knowledge and shit":
- Gabby only exposes curated, user-safe views (summaries, inspiration snippets, progress overviews).
- Any request for actual research knowledge goes through OracleGuardian first.
- Scientists' books are internal-only (see scientist_book/book.py).
- The codex has a "public/auditable" layer (registered pages) vs internal research memory.

Gabby is the friendly face. The research machine stays protected behind Oracle.
"""
from pathlib import Path
from typing import Dict, Any, Optional, List

from getailab.learning.service import get_adaptive_learner


class Gabby:
    def __init__(self, user_id: str, base_path: Path):
        self.user_id = user_id
        self.base_path = Path(base_path)
        self.profile_path = self.base_path / "users" / user_id / "profile.json"
        self.engagement_path = self.base_path / "users" / user_id / "engagement"
        self._learner = get_adaptive_learner(user_id, data_root=self.base_path)

    def ensure_structure(self):
        self.engagement_path.mkdir(parents=True, exist_ok=True)

    def get_user_profile(self) -> Dict[str, Any]:
        """Full user context. Gabby-only. Never passed raw to scientists."""
        profile = {
            "user_id": self.user_id,
            "preferences": {},
            "labs": ["example"],
            "personal_note": "",
        }
        if self.profile_path.exists():
            try:
                import json
                stored = json.loads(self.profile_path.read_text())
                profile.update(stored)
            except Exception:
                pass
        profile["adaptive"] = self._learner.get_adaptive_context()
        return profile

    def record_interaction(self, message: str, *, correct: Optional[bool] = None) -> Dict[str, Any]:
        """Update adaptive learner state from a user message."""
        quality = self._learner.estimate_message_quality(message)
        topic = self._learner.extract_topic_hint(message)
        self._learner.record_interaction(
            correct=correct,
            response_quality=quality,
            subject=topic,
            concept=topic,
        )
        return self._learner.get_adaptive_context()

    def get_adaptive_coaching(self) -> str:
        return self._learner.get_coaching_message()

    def chat(self, message: str, lab_id: str = "example") -> str:
        """Normal user conversation. Gabby can be helpful, remember context, etc."""
        ctx = self.record_interaction(message)
        intervention = ctx.get("intervention", "standard")
        print(f"[Gabby] User {self.user_id} to {lab_id}: {message} [{intervention}]")
        if intervention == "supportive":
            return self._learner.get_coaching_message()
        if intervention == "challenge":
            return self._learner.get_coaching_message()
        return "Got it. I've noted that. Want me to kick off something in the lab?"

    def get_safe_research_inspiration(self, lab_id: str = "example", topic: str = "") -> List[str]:
        """
        User-friendly inspiration (for 'no idea' flow or to make the lab feel alive).
        This is the ONLY way a user gets to see *any* of the scientists' accumulated knowledge.
        It is heavily sanitized through Oracle.
        """
        from ..oracle.guardian import OracleGuardian
        guardian = OracleGuardian(lab_id, self.base_path)
        return guardian.get_safe_inspiration_for_user(topic, self.get_user_profile())

    def request_research_loop(self, problem: str, lab_id: str = "example") -> Dict:
        """
        User asks Gabby to run research.
        Gabby adds any personal flavor (sanitized), then asks Oracle to handle it.
        User never touches scientists or their books directly.
        """
        self.record_interaction(problem)
        profile = self.get_user_profile()
        safe_context = {"personal_note": profile.get("personal_note", "")}
        from ..oracle.guardian import OracleGuardian
        guardian = OracleGuardian(lab_id, self.base_path)
        return guardian.validate_and_run_loop(problem, safe_context)

    def get_my_lab_overview(self, lab_id: str = "example") -> Dict:
        """High-level, user-safe view of a lab. 'Your research progress', not the raw books."""
        from ..oracle.guardian import OracleGuardian
        guardian = OracleGuardian(lab_id, self.base_path)
        overview = guardian.get_user_safe_lab_summary(self.get_user_profile())
        overview["adaptive"] = self._learner.get_adaptive_context()
        return overview

    def on_loop_completed(self, loop_id: int, topic: str = "") -> Dict[str, Any]:
        """Called when user observes or completes a research loop."""
        self._learner.record_loop_completed(loop_id, topic=topic)
        return self._learner.get_adaptive_context()