from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


REACTION_SHOT_STATUS_READY = "reaction_placement_ready"
REACTION_SHOT_STATUS_READY_WITH_WARNINGS = (
    "reaction_placement_ready_with_warnings"
)
REACTION_SHOT_STATUS_NO_CANDIDATES = "no_reaction_candidates"
REACTION_SHOT_STATUS_NO_TIMELINE_ITEMS = "no_timeline_items"
REACTION_SHOT_STATUS_BLOCKED = "blocked"
REACTION_SHOT_STATUS_FAILED = "failed"

REACTION_SHOT_RECOMMENDATION_READY = "review_reaction_shot_placement"
REACTION_SHOT_RECOMMENDATION_WARNINGS = "review_reaction_shot_warnings"
REACTION_SHOT_RECOMMENDATION_NO_CANDIDATES = (
    "provide_reaction_source_data"
)
REACTION_SHOT_RECOMMENDATION_NO_TIMELINE = "provide_review_timeline_items"
REACTION_SHOT_RECOMMENDATION_BLOCKED = "review_reaction_shot_blockers"
REACTION_SHOT_RECOMMENDATION_FAILED = "review_reaction_shot_failure"

REACTION_TYPE_HYPE = "hype_reaction"
REACTION_TYPE_SHOCK = "shock_reaction"
REACTION_TYPE_LAUGH = "laugh_reaction"
REACTION_TYPE_FRUSTRATION = "frustration_reaction"
REACTION_TYPE_SURPRISE = "surprise_reaction"
REACTION_TYPE_CHAT = "chat_reaction"
REACTION_TYPE_UNKNOWN = "unknown_reaction"

PLACEMENT_TYPE_AFTER_HIGHLIGHT = "after_highlight"
PLACEMENT_TYPE_AFTER_HOOK = "after_hook_candidate"
PLACEMENT_TYPE_AFTER_CLIMAX = "after_climax"
PLACEMENT_TYPE_AFTER_PATTERN_INTERRUPT = "after_pattern_interrupt"
PLACEMENT_TYPE_MANUAL_PLACEHOLDER = "manual_placeholder"
PLACEMENT_TYPE_BLOCKED_BY_CONTINUITY = "blocked_by_continuity"
PLACEMENT_TYPE_CENSOR_REVIEW = "censor_review_required"
PLACEMENT_TYPE_PROTECTED_PRESERVED = "protected_preserved"

SUGGESTED_POSITION_AFTER_TRIGGER = "after_trigger"
SUGGESTED_POSITION_KEEP_ORIGINAL = "keep_original_position"
SUGGESTED_POSITION_MANUAL_REVIEW = "manual_review_only"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_reaction_shot_candidate_id() -> str:
    return f"reaction_shot_candidate_{uuid.uuid4().hex[:12]}"


def new_reaction_shot_placement_id() -> str:
    return f"reaction_shot_placement_{uuid.uuid4().hex[:12]}"


def new_reaction_shot_report_id() -> str:
    return f"reaction_shot_report_{uuid.uuid4().hex[:12]}"


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _safe_list(value: Any) -> list:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return bool(value)


@dataclass
class ReactionShotCandidate:
    candidate_id: str = field(default_factory=new_reaction_shot_candidate_id)
    source_item_id: str | None = None
    source_segment_id: str | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
    duration_seconds: float = 0.0
    reaction_type: str = REACTION_TYPE_UNKNOWN
    reaction_score: float = 0.0
    expressiveness_score: float = 0.0
    audio_reaction_score: float = 0.0
    face_reaction_score: float = 0.0
    keyword_reaction_score: float = 0.0
    confidence: float = 0.0
    review_required: bool = True
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def enforce_review_only(self) -> None:
        self.review_required = True
        self.metadata.update(
            {
                "phase": "2B-41",
                "block": "block7_story_pacing",
                "review_only": True,
                "reaction_shot_placement_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_41": True,
                "no_render_in_2b_41": True,
                "no_timeline_reorder_in_2b_41": True,
                "no_reaction_apply_in_2b_41": True,
                "no_reaction_insert_in_2b_41": True,
                "no_facecam_move_in_2b_41": True,
                "no_zoom_insert_in_2b_41": True,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        self.enforce_review_only()
        return {
            "candidate_id": self.candidate_id,
            "source_item_id": self.source_item_id,
            "source_segment_id": self.source_segment_id,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "reaction_type": self.reaction_type,
            "reaction_score": self.reaction_score,
            "expressiveness_score": self.expressiveness_score,
            "audio_reaction_score": self.audio_reaction_score,
            "face_reaction_score": self.face_reaction_score,
            "keyword_reaction_score": self.keyword_reaction_score,
            "confidence": self.confidence,
            "review_required": self.review_required,
            "warnings": list(self.warnings or []),
            "blocking_reasons": list(self.blocking_reasons or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "ReactionShotCandidate":
        data = data or {}
        candidate = cls(
            candidate_id=str(
                data.get("candidate_id") or new_reaction_shot_candidate_id()
            ),
            source_item_id=data.get("source_item_id"),
            source_segment_id=data.get("source_segment_id"),
            start_seconds=_safe_optional_float(data.get("start_seconds")),
            end_seconds=_safe_optional_float(data.get("end_seconds")),
            duration_seconds=_safe_float(data.get("duration_seconds"), 0.0),
            reaction_type=str(
                data.get("reaction_type") or REACTION_TYPE_UNKNOWN
            ),
            reaction_score=_safe_float(data.get("reaction_score"), 0.0),
            expressiveness_score=_safe_float(
                data.get("expressiveness_score"),
                0.0,
            ),
            audio_reaction_score=_safe_float(
                data.get("audio_reaction_score"),
                0.0,
            ),
            face_reaction_score=_safe_float(
                data.get("face_reaction_score"),
                0.0,
            ),
            keyword_reaction_score=_safe_float(
                data.get("keyword_reaction_score"),
                0.0,
            ),
            confidence=_safe_float(data.get("confidence"), 0.0),
            review_required=True,
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            blocking_reasons=[
                str(item)
                for item in _safe_list(data.get("blocking_reasons"))
            ],
            metadata=_safe_dict(data.get("metadata")),
        )
        candidate.enforce_review_only()
        return candidate


@dataclass
class ReactionShotPlacement:
    placement_id: str = field(default_factory=new_reaction_shot_placement_id)
    trigger_item_id: str | None = None
    trigger_segment_id: str | None = None
    reaction_candidate_id: str | None = None
    placement_type: str = PLACEMENT_TYPE_MANUAL_PLACEHOLDER
    suggested_position: str = SUGGESTED_POSITION_MANUAL_REVIEW
    trigger_start_seconds: float | None = None
    trigger_end_seconds: float | None = None
    reaction_start_seconds: float | None = None
    reaction_end_seconds: float | None = None
    suggested_duration_seconds: float = 0.0
    placement_score: float = 0.0
    review_required: bool = True
    can_auto_place: bool = False
    can_move_clip: bool = False
    can_insert_clip: bool = False
    can_trim: bool = False
    can_extend: bool = False
    can_render: bool = False
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def enforce_review_only(self) -> None:
        self.review_required = True
        self.can_auto_place = False
        self.can_move_clip = False
        self.can_insert_clip = False
        self.can_trim = False
        self.can_extend = False
        self.can_render = False
        self.metadata.update(
            {
                "phase": "2B-41",
                "block": "block7_story_pacing",
                "review_only": True,
                "reaction_shot_placement_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_41": True,
                "no_render_in_2b_41": True,
                "no_timeline_reorder_in_2b_41": True,
                "no_reaction_apply_in_2b_41": True,
                "no_reaction_insert_in_2b_41": True,
                "no_facecam_move_in_2b_41": True,
                "no_zoom_insert_in_2b_41": True,
            }
        )

    def to_dict(self) -> dict[str, Any]:
        self.enforce_review_only()
        return {
            "placement_id": self.placement_id,
            "trigger_item_id": self.trigger_item_id,
            "trigger_segment_id": self.trigger_segment_id,
            "reaction_candidate_id": self.reaction_candidate_id,
            "placement_type": self.placement_type,
            "suggested_position": self.suggested_position,
            "trigger_start_seconds": self.trigger_start_seconds,
            "trigger_end_seconds": self.trigger_end_seconds,
            "reaction_start_seconds": self.reaction_start_seconds,
            "reaction_end_seconds": self.reaction_end_seconds,
            "suggested_duration_seconds": self.suggested_duration_seconds,
            "placement_score": self.placement_score,
            "review_required": self.review_required,
            "can_auto_place": self.can_auto_place,
            "can_move_clip": self.can_move_clip,
            "can_insert_clip": self.can_insert_clip,
            "can_trim": self.can_trim,
            "can_extend": self.can_extend,
            "can_render": self.can_render,
            "warnings": list(self.warnings or []),
            "blocking_reasons": list(self.blocking_reasons or []),
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "ReactionShotPlacement":
        data = data or {}
        placement = cls(
            placement_id=str(
                data.get("placement_id") or new_reaction_shot_placement_id()
            ),
            trigger_item_id=data.get("trigger_item_id"),
            trigger_segment_id=data.get("trigger_segment_id"),
            reaction_candidate_id=data.get("reaction_candidate_id"),
            placement_type=str(
                data.get("placement_type")
                or PLACEMENT_TYPE_MANUAL_PLACEHOLDER
            ),
            suggested_position=str(
                data.get("suggested_position")
                or SUGGESTED_POSITION_MANUAL_REVIEW
            ),
            trigger_start_seconds=_safe_optional_float(
                data.get("trigger_start_seconds")
            ),
            trigger_end_seconds=_safe_optional_float(
                data.get("trigger_end_seconds")
            ),
            reaction_start_seconds=_safe_optional_float(
                data.get("reaction_start_seconds")
            ),
            reaction_end_seconds=_safe_optional_float(
                data.get("reaction_end_seconds")
            ),
            suggested_duration_seconds=_safe_float(
                data.get("suggested_duration_seconds"),
                0.0,
            ),
            placement_score=_safe_float(data.get("placement_score"), 0.0),
            review_required=True,
            can_auto_place=False,
            can_move_clip=False,
            can_insert_clip=False,
            can_trim=False,
            can_extend=False,
            can_render=False,
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            blocking_reasons=[
                str(item)
                for item in _safe_list(data.get("blocking_reasons"))
            ],
            metadata=_safe_dict(data.get("metadata")),
        )
        placement.enforce_review_only()
        return placement


@dataclass
class ReactionShotPlacementReport:
    report_id: str = field(default_factory=new_reaction_shot_report_id)
    job_id: str | None = None
    status: str = REACTION_SHOT_STATUS_NO_CANDIDATES
    candidates: list[ReactionShotCandidate] = field(default_factory=list)
    placements: list[ReactionShotPlacement] = field(default_factory=list)
    total_candidates: int = 0
    total_placements: int = 0
    best_placement_score: float = 0.0
    missing_reaction_placeholder_count: int = 0
    review_required: bool = True
    can_apply_reaction_shots: bool = False
    can_move_clip: bool = False
    can_insert_clip: bool = False
    can_trim: bool = False
    can_extend: bool = False
    can_reorder_timeline: bool = False
    can_render: bool = False
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    recommendation: str = REACTION_SHOT_RECOMMENDATION_NO_CANDIDATES
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def enforce_review_only(self) -> None:
        self.review_required = True
        self.can_apply_reaction_shots = False
        self.can_move_clip = False
        self.can_insert_clip = False
        self.can_trim = False
        self.can_extend = False
        self.can_reorder_timeline = False
        self.can_render = False

        for candidate in self.candidates:
            candidate.enforce_review_only()
        for placement in self.placements:
            placement.enforce_review_only()

        self.metadata.update(
            {
                "phase": "2B-41",
                "block": "block7_story_pacing",
                "review_only": True,
                "reaction_shot_placement_only": True,
                "media_unchanged": True,
                "no_execution_in_2b_41": True,
                "no_render_in_2b_41": True,
                "no_timeline_reorder_in_2b_41": True,
                "no_reaction_apply_in_2b_41": True,
                "no_reaction_insert_in_2b_41": True,
                "no_facecam_move_in_2b_41": True,
                "no_zoom_insert_in_2b_41": True,
            }
        )

    def refresh_metrics(self) -> None:
        self.total_candidates = len(self.candidates)
        self.total_placements = len(self.placements)

        scores = [
            float(placement.placement_score or 0.0)
            for placement in self.placements
        ]
        self.best_placement_score = round(max(scores), 6) if scores else 0.0

        self.missing_reaction_placeholder_count = sum(
            1
            for placement in self.placements
            if placement.placement_type == PLACEMENT_TYPE_MANUAL_PLACEHOLDER
        )

    def to_dict(self) -> dict[str, Any]:
        self.enforce_review_only()
        self.refresh_metrics()
        return {
            "report_id": self.report_id,
            "job_id": self.job_id,
            "status": self.status,
            "candidates": [
                candidate.to_dict() for candidate in self.candidates
            ],
            "placements": [
                placement.to_dict() for placement in self.placements
            ],
            "total_candidates": self.total_candidates,
            "total_placements": self.total_placements,
            "best_placement_score": self.best_placement_score,
            "missing_reaction_placeholder_count": (
                self.missing_reaction_placeholder_count
            ),
            "review_required": self.review_required,
            "can_apply_reaction_shots": self.can_apply_reaction_shots,
            "can_move_clip": self.can_move_clip,
            "can_insert_clip": self.can_insert_clip,
            "can_trim": self.can_trim,
            "can_extend": self.can_extend,
            "can_reorder_timeline": self.can_reorder_timeline,
            "can_render": self.can_render,
            "warnings": list(self.warnings or []),
            "blocking_reasons": list(self.blocking_reasons or []),
            "recommendation": self.recommendation,
            "created_at": self.created_at,
            "metadata": dict(self.metadata or {}),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "ReactionShotPlacementReport":
        data = data or {}

        candidates = [
            ReactionShotCandidate.from_dict(item)
            for item in data.get("candidates", []) or []
            if isinstance(item, dict)
        ]
        placements = [
            ReactionShotPlacement.from_dict(item)
            for item in data.get("placements", []) or []
            if isinstance(item, dict)
        ]

        report = cls(
            report_id=str(
                data.get("report_id") or new_reaction_shot_report_id()
            ),
            job_id=data.get("job_id"),
            status=str(
                data.get("status") or REACTION_SHOT_STATUS_NO_CANDIDATES
            ),
            candidates=candidates,
            placements=placements,
            total_candidates=int(data.get("total_candidates", 0) or 0),
            total_placements=int(data.get("total_placements", 0) or 0),
            best_placement_score=_safe_float(
                data.get("best_placement_score"),
                0.0,
            ),
            missing_reaction_placeholder_count=int(
                data.get("missing_reaction_placeholder_count", 0) or 0
            ),
            review_required=True,
            can_apply_reaction_shots=False,
            can_move_clip=False,
            can_insert_clip=False,
            can_trim=False,
            can_extend=False,
            can_reorder_timeline=False,
            can_render=False,
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            blocking_reasons=[
                str(item)
                for item in _safe_list(data.get("blocking_reasons"))
            ],
            recommendation=str(
                data.get("recommendation")
                or REACTION_SHOT_RECOMMENDATION_NO_CANDIDATES
            ),
            created_at=str(data.get("created_at") or utc_now_iso()),
            metadata=_safe_dict(data.get("metadata")),
        )
        report.enforce_review_only()
        report.refresh_metrics()
        return report
