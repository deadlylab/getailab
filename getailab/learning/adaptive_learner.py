"""
Adaptive / recursive learner profile engine.

Adapted from CryptO'Brien education division (academy_engine extraction).
Tracks engagement, competency, AQF level, and intervention style per user.
Stdlib only — no LLM calls.
"""

from __future__ import annotations

import json
import random
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class QualificationLevel(str, Enum):
    CERT_I = "cert_i"
    CERT_II = "cert_ii"
    CERT_III = "cert_iii"
    CERT_IV = "cert_iv"
    DIPLOMA = "diploma"
    ADV_DIPLOMA = "adv_diploma"
    BACHELOR = "bachelor"


class AssessmentType(str, Enum):
    KNOWLEDGE = "knowledge"
    PRACTICAL = "practical"
    PORTFOLIO = "portfolio"
    OBSERVATION = "observation"
    THIRD_PARTY = "third_party"
    PROJECT = "project"


class AccessibilityMode(str, Enum):
    STANDARD = "standard"
    SCREEN_READER = "screen_reader"
    PLAIN_LANGUAGE = "plain_language"
    DYSLEXIA_FRIENDLY = "dyslexia_friendly"


class ComplianceStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    NEEDS_WORK = "needs_work"


class CompetencyLevel(str, Enum):
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"


class EngagementLevel(str, Enum):
    STRUGGLING = "struggling"
    DEVELOPING = "developing"
    THRIVING = "thriving"
    MASTERY = "mastery"


class InterventionType(str, Enum):
    SUPPORTIVE = "supportive"
    STANDARD = "standard"
    CHALLENGE = "challenge"


@dataclass
class LearnerContext:
    """Recursive learner profile — tracks state across sessions."""

    learner_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    competency_level: CompetencyLevel = CompetencyLevel.BEGINNER
    engagement_score: float = 50.0
    detected_language: str = "en-AU"
    language_confidence: float = 1.0
    total_interactions: int = 0
    correct_responses: int = 0
    incorrect_responses: int = 0
    concepts_mastered: List[str] = field(default_factory=list)
    concepts_struggling: List[str] = field(default_factory=list)
    concepts_in_progress: List[str] = field(default_factory=list)
    current_subject: Optional[str] = None
    current_unit: Optional[str] = None
    session_start: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_interaction: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    progress_reports: List[Dict[str, Any]] = field(default_factory=list)
    estimated_aqf_level: int = 1
    aqf_progression_notes: List[str] = field(default_factory=list)
    labs_completed: int = 0
    loops_observed: int = 0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["competency_level"] = self.competency_level.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> LearnerContext:
        data = data.copy()
        if "competency_level" in data and isinstance(data["competency_level"], str):
            data["competency_level"] = CompetencyLevel(data["competency_level"])
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


class AccessibilityEngine:
    @staticmethod
    def format_for_screen_reader(text: str) -> str:
        clean = text
        clean = re.sub(r"\*\*([^*]+)\*\*", r"\1", clean)
        clean = re.sub(r"\*([^*]+)\*", r"\1", clean)
        clean = re.sub(r"#{1,6}\s*", "", clean)
        clean = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", clean)
        clean = re.sub(r"`([^`]+)`", r"\1", clean)
        clean = re.sub(r"\n{3,}", "\n\n", clean)
        clean = re.sub(r"^- ", "Item: ", clean, flags=re.MULTILINE)
        clean = re.sub(r"^\d+\. ", "Step ", clean, flags=re.MULTILINE)
        return clean

    @staticmethod
    def format_plain_language(text: str) -> str:
        header = (
            "[PLAIN LANGUAGE VERSION]\n"
            "Reading Level: Grade 6-8\nShort sentences. Common words. Clear structure.\n\n"
        )
        return header + text

    @staticmethod
    def format_dyslexia_friendly(text: str) -> str:
        header = (
            "[DYSLEXIA-FRIENDLY FORMAT]\n"
            "Recommended: OpenDyslexic or Arial, 14pt min, 1.5 line spacing, "
            "left-aligned, no italics.\n\n"
        )
        return header + text

    @staticmethod
    def apply_accessibility(text: str, mode: AccessibilityMode) -> str:
        if mode == AccessibilityMode.SCREEN_READER:
            return AccessibilityEngine.format_for_screen_reader(text)
        if mode == AccessibilityMode.PLAIN_LANGUAGE:
            return AccessibilityEngine.format_plain_language(text)
        if mode == AccessibilityMode.DYSLEXIA_FRIENDLY:
            return AccessibilityEngine.format_dyslexia_friendly(text)
        return text


class AdaptiveLearningEngine:
    """Engagement, competency, AQF, and intervention calculations."""

    STRUGGLING_THRESHOLD = 40.0
    DEVELOPING_THRESHOLD = 70.0
    THRIVING_THRESHOLD = 90.0
    INTERMEDIATE_THRESHOLD = 60.0
    ADVANCED_THRESHOLD = 85.0
    AQF_THRESHOLDS = {1: 0, 2: 30, 3: 50, 4: 65, 5: 75, 6: 85, 7: 95}

    def calculate_engagement_level(self, score: float) -> EngagementLevel:
        if score < self.STRUGGLING_THRESHOLD:
            return EngagementLevel.STRUGGLING
        if score < self.DEVELOPING_THRESHOLD:
            return EngagementLevel.DEVELOPING
        if score < self.THRIVING_THRESHOLD:
            return EngagementLevel.THRIVING
        return EngagementLevel.MASTERY

    def calculate_competency_level(self, profile: LearnerContext) -> CompetencyLevel:
        if profile.total_interactions < 5:
            return CompetencyLevel.BEGINNER
        success_rate = (
            profile.correct_responses / profile.total_interactions * 100
            if profile.total_interactions > 0
            else 0
        )
        combined = (profile.engagement_score + success_rate) / 2
        if combined >= self.ADVANCED_THRESHOLD:
            return CompetencyLevel.ADVANCED
        if combined >= self.INTERMEDIATE_THRESHOLD:
            return CompetencyLevel.INTERMEDIATE
        return CompetencyLevel.BEGINNER

    def calculate_aqf_level(self, profile: LearnerContext) -> int:
        combined = profile.engagement_score
        if profile.total_interactions > 0:
            success = profile.correct_responses / profile.total_interactions * 100
            combined = (profile.engagement_score + success) / 2
        for level in range(7, 0, -1):
            if combined >= self.AQF_THRESHOLDS[level]:
                return level
        return 1

    def determine_intervention(self, profile: LearnerContext) -> InterventionType:
        level = self.calculate_engagement_level(profile.engagement_score)
        if level == EngagementLevel.STRUGGLING:
            return InterventionType.SUPPORTIVE
        if level == EngagementLevel.MASTERY:
            return InterventionType.CHALLENGE
        return InterventionType.STANDARD

    def update_engagement(
        self,
        profile: LearnerContext,
        correct: Optional[bool] = None,
        response_quality: float = 0.5,
    ) -> LearnerContext:
        profile.total_interactions += 1
        profile.last_interaction = datetime.now(timezone.utc).isoformat()

        if correct is not None:
            if correct:
                profile.correct_responses += 1
                adjustment = 3.0 + (response_quality * 5.0)
            else:
                profile.incorrect_responses += 1
                adjustment = -2.0 + (response_quality * 2.0)
        else:
            adjustment = 1.0 + (response_quality * 2.0)

        profile.engagement_score = max(0.0, min(100.0, profile.engagement_score + adjustment))
        profile.competency_level = self.calculate_competency_level(profile)
        profile.estimated_aqf_level = self.calculate_aqf_level(profile)
        return profile

    def generate_supportive_message(self, profile: LearnerContext) -> str:
        struggling = profile.concepts_struggling[:3] if profile.concepts_struggling else []
        messages = [
            "Let's take this step by step — there's no rush.",
            "Great question! Let me break this down in a simpler way.",
            "I can see you're working hard. Let's approach it differently.",
            "No worries if this feels tricky — many learners find this challenging at first.",
            "You've got this! Let me explain it with a real-world example.",
        ]
        base = random.choice(messages)
        if struggling:
            base += f" It might help to revisit: {', '.join(struggling)}."
        return base

    def generate_challenge_question(self, profile: LearnerContext, subject: str) -> str:
        mastered = profile.concepts_mastered[:3] if profile.concepts_mastered else [subject]
        return (
            f"Explain how you would apply advanced principles of {subject} "
            f"(especially {', '.join(mastered)}) to solve a complex, novel industry problem "
            "you have actually encountered. Be specific about your reasoning and outcome."
        )

    def should_generate_report(self, profile: LearnerContext) -> bool:
        return profile.total_interactions > 0 and profile.total_interactions % 5 == 0


class LearnerProfileStore:
    """In-memory + JSON file store for LearnerContext."""

    def __init__(self, persist_path: Optional[Path] = None):
        self._profiles: Dict[str, LearnerContext] = {}
        self._persist_path = persist_path
        if persist_path and persist_path.exists():
            self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self._persist_path.read_text())
            self._profiles = {k: LearnerContext.from_dict(v) for k, v in data.items()}
        except Exception:
            self._profiles = {}

    def _save(self) -> None:
        if not self._persist_path:
            return
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            data = {k: v.to_dict() for k, v in self._profiles.items()}
            self._persist_path.write_text(json.dumps(data, indent=2, default=str))
        except Exception:
            pass

    def get_or_create(self, learner_id: Optional[str] = None) -> LearnerContext:
        if learner_id and learner_id in self._profiles:
            return self._profiles[learner_id]
        new_id = learner_id or str(uuid.uuid4())
        profile = LearnerContext(learner_id=new_id)
        self._profiles[new_id] = profile
        self._save()
        return profile

    def update(self, profile: LearnerContext) -> None:
        profile.last_interaction = datetime.now(timezone.utc).isoformat()
        self._profiles[profile.learner_id] = profile
        self._save()

    def get(self, learner_id: str) -> Optional[LearnerContext]:
        return self._profiles.get(learner_id)

    def list_all(self) -> List[str]:
        return list(self._profiles.keys())


COMPLIANCE_CHECKLIST = [
    "Is this mapped to a recognizable competency or unit?",
    "Would it stand up in a basic quality audit?",
    "Is the risk / difficulty level appropriate for the audience?",
    "Is the language simple and clear?",
    "Is it accessible (multiple formats, plain language option)?",
    "Does it genuinely help the learner progress?",
]


def quick_compliance_score(content: str, content_type: str = "general") -> Tuple[ComplianceStatus, str]:
    score = 3
    notes: List[str] = []
    if len(content) > 800:
        score += 1
    else:
        notes.append("Content is quite short.")
    if any(x in content.lower() for x in ["objective", "outcome", "assess", "practical", "example"]):
        score += 1
    else:
        notes.append("Missing clear objectives or practical elements.")
    status = (
        ComplianceStatus.PASS
        if score >= 5
        else (ComplianceStatus.NEEDS_WORK if score >= 3 else ComplianceStatus.FAIL)
    )
    return status, f"Quick score: {score}/6. " + ("; ".join(notes) if notes else "Looks reasonable on surface.")