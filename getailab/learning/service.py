"""
Adaptive learner service — Gabby user layer integration.

Profiles persist under data/users/<user_id>/learner_profile.json.
Scientists never see this data.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, Optional

from getailab.learning.adaptive_learner import (
    AccessibilityEngine,
    AccessibilityMode,
    AdaptiveLearningEngine,
    InterventionType,
    LearnerContext,
    LearnerProfileStore,
    quick_compliance_score,
)

_DEFAULT_USER = os.getenv("GETAILAB_USER_ID", "default")
_INSTANCES: Dict[str, "AdaptiveLearnerService"] = {}


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _user_dir(user_id: str, data_root: Optional[Path] = None) -> Path:
    root = data_root or (_project_root() / "data")
    return root / "users" / user_id


class AdaptiveLearnerService:
    def __init__(self, user_id: str = _DEFAULT_USER, data_root: Optional[Path] = None):
        self.user_id = user_id
        self.data_root = data_root or (_project_root() / "data")
        self.user_path = _user_dir(user_id, self.data_root)
        self.user_path.mkdir(parents=True, exist_ok=True)
        self.store = LearnerProfileStore(self.user_path / "learner_profile.json")
        self.engine = AdaptiveLearningEngine()
        self.profile = self.store.get_or_create(user_id)

    def record_interaction(
        self,
        *,
        correct: Optional[bool] = None,
        response_quality: float = 0.5,
        subject: Optional[str] = None,
        concept: Optional[str] = None,
        mastered: bool = False,
        struggling: bool = False,
    ) -> LearnerContext:
        if subject:
            self.profile.current_subject = subject
        if concept:
            if mastered and concept not in self.profile.concepts_mastered:
                self.profile.concepts_mastered.append(concept)
                if concept in self.profile.concepts_struggling:
                    self.profile.concepts_struggling.remove(concept)
            elif struggling and concept not in self.profile.concepts_struggling:
                self.profile.concepts_struggling.append(concept)
            elif not mastered and not struggling and concept not in self.profile.concepts_in_progress:
                self.profile.concepts_in_progress.append(concept)

        self.profile = self.engine.update_engagement(
            self.profile, correct=correct, response_quality=response_quality
        )
        if self.engine.should_generate_report(self.profile):
            self.profile.progress_reports.append(self._build_progress_snapshot())
        self.store.update(self.profile)
        return self.profile

    def record_loop_observed(self, loop_id: int, topic: str = "") -> LearnerContext:
        self.profile.loops_observed += 1
        if topic:
            self.profile.current_subject = topic[:200]
        return self.record_interaction(correct=True, response_quality=0.85, subject=topic)

    def record_loop_completed(self, loop_id: int, topic: str = "") -> LearnerContext:
        self.profile.labs_completed += 1
        return self.record_loop_observed(loop_id, topic=topic)

    def estimate_message_quality(self, message: str) -> float:
        """Heuristic quality score from message shape (no LLM)."""
        text = (message or "").strip()
        if not text:
            return 0.2
        quality = min(1.0, len(text) / 180)
        if "?" in text:
            quality = min(1.0, quality + 0.15)
        if any(w in text.lower() for w in ("because", "explain", "how", "why", "hypothesis")):
            quality = min(1.0, quality + 0.1)
        return round(quality, 3)

    def extract_topic_hint(self, message: str) -> Optional[str]:
        text = (message or "").strip()
        if len(text) < 12:
            return None
        return text[:120]

    def get_coaching_message(self) -> str:
        intervention = self.engine.determine_intervention(self.profile)
        if intervention == InterventionType.SUPPORTIVE:
            return self.engine.generate_supportive_message(self.profile)
        if intervention == InterventionType.CHALLENGE:
            subject = self.profile.current_subject or "research"
            return self.engine.generate_challenge_question(self.profile, subject)
        return "You're making steady progress. What would you like to explore next in the lab?"

    def get_adaptive_context(self) -> Dict[str, Any]:
        intervention = self.engine.determine_intervention(self.profile)
        engagement_level = self.engine.calculate_engagement_level(self.profile.engagement_score)
        return {
            "user_id": self.user_id,
            "learner_id": self.profile.learner_id,
            "engagement_score": round(self.profile.engagement_score, 2),
            "engagement_level": engagement_level.value,
            "competency_level": self.profile.competency_level.value,
            "intervention": intervention.value,
            "estimated_aqf_level": self.profile.estimated_aqf_level,
            "total_interactions": self.profile.total_interactions,
            "correct_responses": self.profile.correct_responses,
            "incorrect_responses": self.profile.incorrect_responses,
            "loops_observed": self.profile.loops_observed,
            "labs_completed": self.profile.labs_completed,
            "current_subject": self.profile.current_subject,
            "concepts_mastered": self.profile.concepts_mastered[-5:],
            "concepts_struggling": self.profile.concepts_struggling[-5:],
            "last_interaction": self.profile.last_interaction,
            "coaching_hint": self.get_coaching_message(),
        }

    def format_for_accessibility(self, text: str, mode: str = "standard") -> str:
        try:
            acc_mode = AccessibilityMode(mode)
        except ValueError:
            acc_mode = AccessibilityMode.STANDARD
        return AccessibilityEngine.apply_accessibility(text, acc_mode)

    def check_content_compliance(self, content: str, content_type: str = "general") -> Dict[str, Any]:
        status, note = quick_compliance_score(content, content_type)
        return {"status": status.value, "note": note}

    def _build_progress_snapshot(self) -> Dict[str, Any]:
        ctx = self.get_adaptive_context()
        return {
            "timestamp": self.profile.last_interaction,
            "engagement_score": ctx["engagement_score"],
            "engagement_level": ctx["engagement_level"],
            "competency_level": ctx["competency_level"],
            "estimated_aqf_level": ctx["estimated_aqf_level"],
            "interactions": self.profile.total_interactions,
        }


def get_adaptive_learner(
    user_id: Optional[str] = None,
    data_root: Optional[Path] = None,
) -> AdaptiveLearnerService:
    uid = user_id or _DEFAULT_USER
    if uid not in _INSTANCES or (data_root and _INSTANCES[uid].data_root != data_root):
        _INSTANCES[uid] = AdaptiveLearnerService(uid, data_root=data_root)
    return _INSTANCES[uid]