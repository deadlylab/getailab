"""
User Profile / Engagement Layer (Gabb y territory).

This is SEPARATE from scientist memory.
Scientists do not see this. As far as scientists are concerned, "the user" does not exist.

Gabb y (when built) will live here or in a separate getailab/gabby/ to:
- Remember user preferences, history, engagement.
- Personal context for "no idea" starters (family history etc.).
- But never leak into scientist books or prompts unless explicitly mediated by Oracle.

For scale: per-user isolation.
"""
from pathlib import Path
from typing import Dict, Any

class UserProfile:
    def __init__(self, user_id: str, base_path: Path):
        self.user_id = user_id
        self.profile_path = base_path / user_id / "profile.json"
        self.engagement_path = base_path / user_id / "engagement"

    def ensure_structure(self):
        self.engagement_path.mkdir(parents=True, exist_ok=True)

    def get_profile(self) -> Dict[str, Any]:
        # TODO: load from JSON.
        return {"user_id": self.user_id, "preferences": {}, "labs": []}

    # Gabby will own the "get to know the user" logic here.
    # Oracle can query limited safe parts for lab starters.
