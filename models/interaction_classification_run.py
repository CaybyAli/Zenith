from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _safe_list(value: Any) -> list:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


@dataclass
class InteractionClassificationRunReport:
    status: str
    source: str = "interaction_classification_runner"
    transcript_source: str | None = None
    interaction_classification_result: dict[str, Any] = field(default_factory=dict)
    points: list[dict[str, Any]] = field(default_factory=list)
    segment_classifications: list[dict[str, Any]] = field(default_factory=list)
    point_count: int = 0
    segment_classification_count: int = 0
    monologue_count: int = 0
    interaction_count: int = 0
    question_answer_count: int = 0
    chat_reaction_count: int = 0
    callout_count: int = 0
    commentary_count: int = 0
    private_or_meta_count: int = 0
    context_needed_count: int = 0
    recommendation: str | None = None
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "transcript_source": self.transcript_source,
            "interaction_classification_result": dict(
                self.interaction_classification_result
            ),
            "points": [dict(item) for item in self.points],
            "segment_classifications": [
                dict(item) for item in self.segment_classifications
            ],
            "point_count": self.point_count,
            "segment_classification_count": self.segment_classification_count,
            "monologue_count": self.monologue_count,
            "interaction_count": self.interaction_count,
            "question_answer_count": self.question_answer_count,
            "chat_reaction_count": self.chat_reaction_count,
            "callout_count": self.callout_count,
            "commentary_count": self.commentary_count,
            "private_or_meta_count": self.private_or_meta_count,
            "context_needed_count": self.context_needed_count,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "InteractionClassificationRunReport":
        if not isinstance(data, dict):
            data = {}
        raw_points = data.get("points")
        raw_segments = data.get("segment_classifications")
        points = [
            dict(item) for item in raw_points if isinstance(item, dict)
        ] if isinstance(raw_points, list) else []
        segments = [
            dict(item) for item in raw_segments if isinstance(item, dict)
        ] if isinstance(raw_segments, list) else []

        return cls(
            status=str(data.get("status") or "failed"),
            source=str(data.get("source") or "interaction_classification_runner"),
            transcript_source=(
                str(data.get("transcript_source"))
                if data.get("transcript_source") is not None
                else None
            ),
            interaction_classification_result=_safe_dict(
                data.get("interaction_classification_result")
            ),
            points=points,
            segment_classifications=segments,
            point_count=int(data.get("point_count", len(points)) or 0),
            segment_classification_count=int(
                data.get("segment_classification_count", len(segments)) or 0
            ),
            monologue_count=int(data.get("monologue_count", 0) or 0),
            interaction_count=int(data.get("interaction_count", 0) or 0),
            question_answer_count=int(data.get("question_answer_count", 0) or 0),
            chat_reaction_count=int(data.get("chat_reaction_count", 0) or 0),
            callout_count=int(data.get("callout_count", 0) or 0),
            commentary_count=int(data.get("commentary_count", 0) or 0),
            private_or_meta_count=int(data.get("private_or_meta_count", 0) or 0),
            context_needed_count=int(data.get("context_needed_count", 0) or 0),
            recommendation=(
                str(data.get("recommendation"))
                if data.get("recommendation") is not None
                else None
            ),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
            metadata=_safe_dict(data.get("metadata")),
        )
