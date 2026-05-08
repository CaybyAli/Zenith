from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


ENGINE = "universal-boundary-evidence-v1"

BOUNDARY_TYPES = {
    "clean",
    "real_speech_cut_risk",
    "possible_speech_cut_risk",
    "action_cut_risk",
    "zoom_cut_risk",
    "menu_jump",
    "boring_gap",
    "likely_false_positive",
    "unknown",
}

BOUNDARY_PRIORITIES = {"real_high", "medium", "low", "false_positive", "unknown"}

EVIDENCE_QUALITIES = {"exact", "likely", "uncertain", "weak", "none"}

SPEECH_BOUNDARY_CLASSIFICATIONS = {
    "real_word_cut",
    "real_sentence_cut",
    "likely_speech_cut",
    "timestamp_uncertain",
    "audio_only_near_edge",
    "weak_speech_evidence",
    "probably_safe",
    "unknown",
}


def _clamp_score(value: object, fallback: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = fallback
    return round(max(0.0, min(1.0, numeric)), 3)


def _safe_seconds(value: object, fallback: float | None = 0.0) -> float | None:
    if value is None and fallback is None:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = 0.0 if fallback is None else fallback
    return round(max(0.0, numeric), 3)


def _clean_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, bytes)):
        text = str(value)
        return [text] if text else []
    try:
        return [str(item) for item in value if str(item)]
    except TypeError:
        text = str(value)
        return [text] if text else []


@dataclass
class UniversalBoundaryEvidence:
    boundary_id: str = ""
    job_id: str = ""
    boundary_index: int = 0

    left_segment_id: str | None = None
    right_segment_id: str | None = None
    left_role: str | None = None
    right_role: str | None = None
    left_end_time: float | None = None
    right_start_time: float | None = None
    gap_seconds: float = 0.0

    evidence_start_time: float = 0.0
    evidence_end_time: float = 0.0
    edge_radius_seconds: float = 0.75

    transcript_left_near_edge: bool = False
    transcript_right_near_edge: bool = False
    sentence_left_near_edge: bool = False
    sentence_right_near_edge: bool = False
    audio_speech_left_near_edge: bool = False
    audio_speech_right_near_edge: bool = False
    speech_crosses_boundary: bool = False
    sentence_crosses_boundary: bool = False
    likely_word_cut: bool = False
    likely_sentence_cut: bool = False

    transcript_edge_distance_left: float | None = None
    transcript_edge_distance_right: float | None = None
    sentence_edge_distance_left: float | None = None
    sentence_edge_distance_right: float | None = None
    audio_edge_distance_left: float | None = None
    audio_edge_distance_right: float | None = None

    word_cut_confidence: float = 0.0
    sentence_cut_confidence: float = 0.0
    transcript_timestamp_uncertainty: float = 0.0
    audio_speech_confidence: float = 0.0
    calibrated_speech_risk_score: float = 0.0

    transcript_evidence_quality: str = "none"
    sentence_evidence_quality: str = "none"
    speech_boundary_classification: str = "unknown"

    transcript_only_risk: bool = False
    audio_only_risk: bool = False
    sentence_span_too_broad: bool = False
    downgrade_candidate: bool = False

    action_left_near_edge: bool = False
    action_right_near_edge: bool = False
    peak_left_near_edge: bool = False
    peak_right_near_edge: bool = False
    tension_left_near_edge: bool = False
    tension_right_near_edge: bool = False
    reaction_left_near_edge: bool = False
    reaction_right_near_edge: bool = False

    cut_risk_left_near_edge: bool = False
    cut_risk_right_near_edge: bool = False
    zoom_risk_left_near_edge: bool = False
    zoom_risk_right_near_edge: bool = False
    menu_wait_left_near_edge: bool = False
    menu_wait_right_near_edge: bool = False
    boring_left_near_edge: bool = False
    boring_right_near_edge: bool = False

    speech_evidence_score: float = 0.0
    action_evidence_score: float = 0.0
    zoom_evidence_score: float = 0.0
    menu_evidence_score: float = 0.0
    boring_evidence_score: float = 0.0
    false_positive_score: float = 0.0
    boundary_risk_score: float = 0.0

    boundary_type: str = "unknown"
    priority: str = "unknown"

    should_protect_boundary: bool = False
    should_review_boundary: bool = False
    can_ignore_warning: bool = False
    needs_transcript_check: bool = False
    needs_visual_check: bool = False

    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    evidence_notes: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.boundary_id = str(self.boundary_id or "")
        self.job_id = str(self.job_id or "")
        try:
            self.boundary_index = max(0, int(self.boundary_index or 0))
        except (TypeError, ValueError):
            self.boundary_index = 0

        self.left_segment_id = self._optional_text(self.left_segment_id)
        self.right_segment_id = self._optional_text(self.right_segment_id)
        self.left_role = self._optional_text(self.left_role)
        self.right_role = self._optional_text(self.right_role)
        self.left_end_time = _safe_seconds(self.left_end_time, None)
        self.right_start_time = _safe_seconds(self.right_start_time, None)
        self.gap_seconds = round(
            float(_safe_seconds(self.gap_seconds, 0.0) or 0.0),
            3,
        )
        self.evidence_start_time = float(_safe_seconds(self.evidence_start_time, 0.0) or 0.0)
        self.evidence_end_time = float(_safe_seconds(self.evidence_end_time, self.evidence_start_time) or 0.0)
        if self.evidence_end_time < self.evidence_start_time:
            self.evidence_end_time = self.evidence_start_time
        self.edge_radius_seconds = float(_safe_seconds(self.edge_radius_seconds, 0.75) or 0.75)

        for name in _DISTANCE_FIELDS:
            setattr(self, name, _safe_seconds(getattr(self, name, None), None))
        for name in _BOOL_FIELDS:
            setattr(self, name, bool(getattr(self, name, False)))
        for name in _SCORE_FIELDS:
            setattr(self, name, _clamp_score(getattr(self, name, 0.0)))

        self.transcript_evidence_quality = str(self.transcript_evidence_quality or "none")
        if self.transcript_evidence_quality not in EVIDENCE_QUALITIES:
            self.transcript_evidence_quality = "none"
        self.sentence_evidence_quality = str(self.sentence_evidence_quality or "none")
        if self.sentence_evidence_quality not in EVIDENCE_QUALITIES:
            self.sentence_evidence_quality = "none"
        self.speech_boundary_classification = str(self.speech_boundary_classification or "unknown")
        if self.speech_boundary_classification not in SPEECH_BOUNDARY_CLASSIFICATIONS:
            self.speech_boundary_classification = "unknown"

        self.boundary_type = str(self.boundary_type or "unknown")
        if self.boundary_type not in BOUNDARY_TYPES:
            self.boundary_type = "unknown"
        self.priority = str(self.priority or "unknown")
        if self.priority not in BOUNDARY_PRIORITIES:
            self.priority = "unknown"

        self.reasons = _clean_string_list(self.reasons)
        self.warnings = _clean_string_list(self.warnings)
        self.evidence_notes = _clean_string_list(self.evidence_notes)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "boundary_id": self.boundary_id,
            "job_id": self.job_id,
            "boundary_index": self.boundary_index,
            "left_segment_id": self.left_segment_id,
            "right_segment_id": self.right_segment_id,
            "left_role": self.left_role,
            "right_role": self.right_role,
            "left_end_time": self.left_end_time,
            "right_start_time": self.right_start_time,
            "gap_seconds": self.gap_seconds,
            "evidence_start_time": self.evidence_start_time,
            "evidence_end_time": self.evidence_end_time,
            "edge_radius_seconds": self.edge_radius_seconds,
            "boundary_type": self.boundary_type,
            "priority": self.priority,
            "transcript_evidence_quality": self.transcript_evidence_quality,
            "sentence_evidence_quality": self.sentence_evidence_quality,
            "speech_boundary_classification": self.speech_boundary_classification,
            "should_protect_boundary": self.should_protect_boundary,
            "should_review_boundary": self.should_review_boundary,
            "can_ignore_warning": self.can_ignore_warning,
            "needs_transcript_check": self.needs_transcript_check,
            "needs_visual_check": self.needs_visual_check,
            "reasons": list(self.reasons),
            "warnings": list(self.warnings),
            "evidence_notes": list(self.evidence_notes),
        }
        for name in _DISTANCE_FIELDS:
            payload[name] = getattr(self, name)
        for name in _BOOL_FIELDS:
            payload[name] = getattr(self, name)
        for name in _SCORE_FIELDS:
            payload[name] = getattr(self, name)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "UniversalBoundaryEvidence":
        data = dict(data or {})
        kwargs = {name: bool(data.get(name, False)) for name in _BOOL_FIELDS}
        kwargs.update({name: data.get(name, 0.0) for name in _SCORE_FIELDS})
        kwargs.update({name: data.get(name) for name in _DISTANCE_FIELDS})
        return cls(
            boundary_id=str(data.get("boundary_id", "")),
            job_id=str(data.get("job_id", "")),
            boundary_index=int(data.get("boundary_index", 0) or 0),
            left_segment_id=data.get("left_segment_id"),
            right_segment_id=data.get("right_segment_id"),
            left_role=data.get("left_role"),
            right_role=data.get("right_role"),
            left_end_time=data.get("left_end_time"),
            right_start_time=data.get("right_start_time"),
            gap_seconds=data.get("gap_seconds", 0.0),
            evidence_start_time=data.get("evidence_start_time", 0.0),
            evidence_end_time=data.get("evidence_end_time", 0.0),
            edge_radius_seconds=data.get("edge_radius_seconds", 0.75),
            boundary_type=str(data.get("boundary_type", "unknown")),
            priority=str(data.get("priority", "unknown")),
            transcript_evidence_quality=str(data.get("transcript_evidence_quality", "none")),
            sentence_evidence_quality=str(data.get("sentence_evidence_quality", "none")),
            speech_boundary_classification=str(data.get("speech_boundary_classification", "unknown")),
            should_protect_boundary=bool(data.get("should_protect_boundary", False)),
            should_review_boundary=bool(data.get("should_review_boundary", False)),
            can_ignore_warning=bool(data.get("can_ignore_warning", False)),
            needs_transcript_check=bool(data.get("needs_transcript_check", False)),
            needs_visual_check=bool(data.get("needs_visual_check", False)),
            reasons=list(data.get("reasons") or []),
            warnings=list(data.get("warnings") or []),
            evidence_notes=list(data.get("evidence_notes") or []),
            **kwargs,
        )

    @staticmethod
    def _optional_text(value: object) -> str | None:
        if value is None:
            return None
        text = str(value)
        return text if text else None


@dataclass
class UniversalBoundaryEvidenceReport:
    job_id: str = ""
    engine: str = ENGINE
    boundaries: list[UniversalBoundaryEvidence] = field(default_factory=list)
    total_boundaries: int = 0
    real_high: int = 0
    medium: int = 0
    low: int = 0
    false_positive: int = 0
    clean: int = 0
    real_speech_cut_risk: int = 0
    possible_speech_cut_risk: int = 0
    action_cut_risk: int = 0
    zoom_cut_risk: int = 0
    menu_jump: int = 0
    boring_gap: int = 0
    avg_boundary_risk_score: float = 0.0
    real_word_cut: int = 0
    real_sentence_cut: int = 0
    likely_speech_cut: int = 0
    timestamp_uncertain: int = 0
    audio_only_near_edge: int = 0
    weak_speech_evidence: int = 0
    probably_safe: int = 0
    downgrade_candidates: int = 0

    def __post_init__(self) -> None:
        self.job_id = str(self.job_id or "")
        self.engine = str(self.engine or ENGINE)
        self.boundaries = sorted(
            [
                boundary
                if isinstance(boundary, UniversalBoundaryEvidence)
                else UniversalBoundaryEvidence.from_dict(boundary)
                for boundary in (self.boundaries or [])
                if isinstance(boundary, (UniversalBoundaryEvidence, dict))
            ],
            key=lambda item: (item.boundary_index, item.left_end_time or 0.0, item.boundary_id),
        )
        self.total_boundaries = len(self.boundaries)
        self.real_high = self._count_priority("real_high")
        self.medium = self._count_priority("medium")
        self.low = self._count_priority("low")
        self.false_positive = self._count_priority("false_positive")
        self.clean = self._count_type("clean")
        self.real_speech_cut_risk = self._count_type("real_speech_cut_risk")
        self.possible_speech_cut_risk = self._count_type("possible_speech_cut_risk")
        self.action_cut_risk = self._count_type("action_cut_risk")
        self.zoom_cut_risk = self._count_type("zoom_cut_risk")
        self.menu_jump = self._count_type("menu_jump")
        self.boring_gap = self._count_type("boring_gap")
        self.real_word_cut = self._count_speech_classification("real_word_cut")
        self.real_sentence_cut = self._count_speech_classification("real_sentence_cut")
        self.likely_speech_cut = self._count_speech_classification("likely_speech_cut")
        self.timestamp_uncertain = self._count_speech_classification("timestamp_uncertain")
        self.audio_only_near_edge = self._count_speech_classification("audio_only_near_edge")
        self.weak_speech_evidence = self._count_speech_classification("weak_speech_evidence")
        self.probably_safe = self._count_speech_classification("probably_safe")
        self.downgrade_candidates = sum(boundary.downgrade_candidate for boundary in self.boundaries)
        self.avg_boundary_risk_score = _clamp_score(
            sum(item.boundary_risk_score for item in self.boundaries) / len(self.boundaries)
            if self.boundaries
            else 0.0
        )

    def _count_priority(self, priority: str) -> int:
        return sum(boundary.priority == priority for boundary in self.boundaries)

    def _count_type(self, boundary_type: str) -> int:
        return sum(boundary.boundary_type == boundary_type for boundary in self.boundaries)

    def _count_speech_classification(self, classification: str) -> int:
        return sum(
            boundary.speech_boundary_classification == classification
            for boundary in self.boundaries
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "engine": self.engine,
            "boundaries": [boundary.to_dict() for boundary in self.boundaries],
            "total_boundaries": self.total_boundaries,
            "real_high": self.real_high,
            "medium": self.medium,
            "low": self.low,
            "false_positive": self.false_positive,
            "clean": self.clean,
            "real_speech_cut_risk": self.real_speech_cut_risk,
            "possible_speech_cut_risk": self.possible_speech_cut_risk,
            "action_cut_risk": self.action_cut_risk,
            "zoom_cut_risk": self.zoom_cut_risk,
            "menu_jump": self.menu_jump,
            "boring_gap": self.boring_gap,
            "avg_boundary_risk_score": self.avg_boundary_risk_score,
            "real_word_cut": self.real_word_cut,
            "real_sentence_cut": self.real_sentence_cut,
            "likely_speech_cut": self.likely_speech_cut,
            "timestamp_uncertain": self.timestamp_uncertain,
            "audio_only_near_edge": self.audio_only_near_edge,
            "weak_speech_evidence": self.weak_speech_evidence,
            "probably_safe": self.probably_safe,
            "downgrade_candidates": self.downgrade_candidates,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "UniversalBoundaryEvidenceReport":
        data = dict(data or {})
        return cls(
            job_id=str(data.get("job_id", "")),
            engine=str(data.get("engine", ENGINE)),
            boundaries=[
                UniversalBoundaryEvidence.from_dict(boundary)
                for boundary in data.get("boundaries", [])
                if isinstance(boundary, dict)
            ],
            total_boundaries=int(data.get("total_boundaries", 0) or 0),
            real_high=int(data.get("real_high", 0) or 0),
            medium=int(data.get("medium", 0) or 0),
            low=int(data.get("low", 0) or 0),
            false_positive=int(data.get("false_positive", 0) or 0),
            clean=int(data.get("clean", 0) or 0),
            real_speech_cut_risk=int(data.get("real_speech_cut_risk", 0) or 0),
            possible_speech_cut_risk=int(data.get("possible_speech_cut_risk", 0) or 0),
            action_cut_risk=int(data.get("action_cut_risk", 0) or 0),
            zoom_cut_risk=int(data.get("zoom_cut_risk", 0) or 0),
            menu_jump=int(data.get("menu_jump", 0) or 0),
            boring_gap=int(data.get("boring_gap", 0) or 0),
            avg_boundary_risk_score=data.get("avg_boundary_risk_score", 0.0),
            real_word_cut=int(data.get("real_word_cut", 0) or 0),
            real_sentence_cut=int(data.get("real_sentence_cut", 0) or 0),
            likely_speech_cut=int(data.get("likely_speech_cut", 0) or 0),
            timestamp_uncertain=int(data.get("timestamp_uncertain", 0) or 0),
            audio_only_near_edge=int(data.get("audio_only_near_edge", 0) or 0),
            weak_speech_evidence=int(data.get("weak_speech_evidence", 0) or 0),
            probably_safe=int(data.get("probably_safe", 0) or 0),
            downgrade_candidates=int(data.get("downgrade_candidates", 0) or 0),
        )


_DISTANCE_FIELDS = (
    "transcript_edge_distance_left",
    "transcript_edge_distance_right",
    "sentence_edge_distance_left",
    "sentence_edge_distance_right",
    "audio_edge_distance_left",
    "audio_edge_distance_right",
)

_BOOL_FIELDS = (
    "transcript_left_near_edge",
    "transcript_right_near_edge",
    "sentence_left_near_edge",
    "sentence_right_near_edge",
    "audio_speech_left_near_edge",
    "audio_speech_right_near_edge",
    "speech_crosses_boundary",
    "sentence_crosses_boundary",
    "likely_word_cut",
    "likely_sentence_cut",
    "transcript_only_risk",
    "audio_only_risk",
    "sentence_span_too_broad",
    "downgrade_candidate",
    "action_left_near_edge",
    "action_right_near_edge",
    "peak_left_near_edge",
    "peak_right_near_edge",
    "tension_left_near_edge",
    "tension_right_near_edge",
    "reaction_left_near_edge",
    "reaction_right_near_edge",
    "cut_risk_left_near_edge",
    "cut_risk_right_near_edge",
    "zoom_risk_left_near_edge",
    "zoom_risk_right_near_edge",
    "menu_wait_left_near_edge",
    "menu_wait_right_near_edge",
    "boring_left_near_edge",
    "boring_right_near_edge",
)

_SCORE_FIELDS = (
    "speech_evidence_score",
    "action_evidence_score",
    "zoom_evidence_score",
    "menu_evidence_score",
    "boring_evidence_score",
    "false_positive_score",
    "boundary_risk_score",
    "word_cut_confidence",
    "sentence_cut_confidence",
    "transcript_timestamp_uncertainty",
    "audio_speech_confidence",
    "calibrated_speech_risk_score",
)
