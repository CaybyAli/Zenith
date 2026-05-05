from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def _clamp_score(value: object, fallback: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = fallback
    return round(max(0.0, min(1.0, numeric)), 3)


def _safe_seconds(value: object, fallback: float = 0.0) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        numeric = fallback
    return round(max(0.0, numeric), 3)


@dataclass
class SentenceItem:
    sentence_id: str
    text: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    score: float
    confidence: float
    sentence_kind: str
    speaker_role: str = "unknown"
    source_segment_ids: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.sentence_id = str(self.sentence_id or "")
        self.text = str(self.text or "").strip()
        self.start_seconds = _safe_seconds(self.start_seconds)
        self.end_seconds = _safe_seconds(self.end_seconds, self.start_seconds)
        if self.end_seconds < self.start_seconds:
            self.end_seconds = self.start_seconds
        self.duration_seconds = round(max(0.0, self.end_seconds - self.start_seconds), 3)
        self.score = _clamp_score(self.score)
        self.confidence = _clamp_score(self.confidence, 0.75)
        if self.sentence_kind not in {"normal", "question", "exclamation", "hook", "filler", "incomplete"}:
            self.sentence_kind = "normal"
        if self.speaker_role not in {"unknown", "creator", "friend", "group"}:
            self.speaker_role = "unknown"
        self.source_segment_ids = [str(item) for item in (self.source_segment_ids or [])]
        self.metadata = dict(self.metadata or {})

    def to_dict(self) -> dict[str, Any]:
        return {
            "sentence_id": self.sentence_id,
            "text": self.text,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "duration_seconds": self.duration_seconds,
            "score": self.score,
            "confidence": self.confidence,
            "sentence_kind": self.sentence_kind,
            "speaker_role": self.speaker_role,
            "source_segment_ids": self.source_segment_ids,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SentenceItem":
        return cls(
            sentence_id=str(data.get("sentence_id", "")),
            text=str(data.get("text", "")),
            start_seconds=data.get("start_seconds", 0.0),
            end_seconds=data.get("end_seconds", data.get("start_seconds", 0.0)),
            duration_seconds=data.get("duration_seconds", 0.0),
            score=data.get("score", 0.0),
            confidence=data.get("confidence", 0.75),
            sentence_kind=str(data.get("sentence_kind", "normal")),
            speaker_role=str(data.get("speaker_role", "unknown")),
            source_segment_ids=list(data.get("source_segment_ids") or []),
            metadata=dict(data.get("metadata") or {}),
        )


@dataclass
class SentenceTimelineResult:
    sentences: list[SentenceItem] = field(default_factory=list)
    engine: str = "sentence-timeline-builder-v1"
    skipped_reason: str | None = None

    @property
    def total_sentences(self) -> int:
        return len(self.sentences)

    @property
    def hook_sentence_count(self) -> int:
        return sum(sentence.sentence_kind == "hook" for sentence in self.sentences)

    @property
    def filler_sentence_count(self) -> int:
        return sum(sentence.sentence_kind == "filler" for sentence in self.sentences)

    @property
    def incomplete_sentence_count(self) -> int:
        return sum(sentence.sentence_kind == "incomplete" for sentence in self.sentences)

    @property
    def average_score(self) -> float:
        if not self.sentences:
            return 0.0
        return round(sum(sentence.score for sentence in self.sentences) / len(self.sentences), 3)

    @property
    def max_score(self) -> float:
        return max((sentence.score for sentence in self.sentences), default=0.0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sentences": [sentence.to_dict() for sentence in self.sentences],
            "total_sentences": self.total_sentences,
            "hook_sentence_count": self.hook_sentence_count,
            "filler_sentence_count": self.filler_sentence_count,
            "incomplete_sentence_count": self.incomplete_sentence_count,
            "average_score": self.average_score,
            "max_score": self.max_score,
            "engine": self.engine,
            "skipped_reason": self.skipped_reason,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SentenceTimelineResult":
        return cls(
            sentences=[
                SentenceItem.from_dict(sentence)
                for sentence in data.get("sentences", [])
                if isinstance(sentence, dict)
            ],
            engine=str(data.get("engine", "sentence-timeline-builder-v1")),
            skipped_reason=data.get("skipped_reason"),
        )
