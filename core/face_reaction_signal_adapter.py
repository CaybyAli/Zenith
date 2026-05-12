from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_SKIPPED_NO_FACE_REACTION_SEGMENTS = "skipped_no_face_reaction_segments"
STATUS_FAILED = "failed"

REACTION_NEUTRAL_FACE = "neutral_face"
REACTION_MOUTH_OPEN_CANDIDATE = "mouth_open_candidate"
REACTION_LAUGH_CANDIDATE = "laugh_candidate"
REACTION_SHOCK_CANDIDATE = "shock_candidate"
REACTION_HYPE_CANDIDATE = "hype_candidate"
REACTION_EXPRESSIVE_CANDIDATE = "expressive_reaction_candidate"

SIGNAL_TYPE_HIGH_REACTION = "face_high_reaction_segment"
SIGNAL_TYPE_SHOCK = "face_shock_reaction_candidate"
SIGNAL_TYPE_LAUGH = "face_laugh_reaction_candidate"
SIGNAL_TYPE_MOUTH_OPEN = "face_mouth_open_candidate"
SIGNAL_TYPE_NEUTRAL = "face_neutral_presence_segment"

SOURCE_FACE_REACTION = "face_reaction"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_string(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value)


def _safe_list(value: Any) -> list:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)

    to_dict = getattr(value, "to_dict", None)
    if callable(to_dict):
        try:
            converted = to_dict()
            if isinstance(converted, dict):
                return dict(converted)
        except Exception:
            return {}

    return {}


def _clamp_score(value: Any, default: float = 0.0) -> float:
    return max(0.0, min(1.0, _safe_float(value, default)))


def _extract_face_reaction_segments(source: Any) -> list[dict[str, Any]]:
    source_dict = _safe_dict(source)

    for key in ("face_reaction_segments", "segments"):
        raw_segments = source_dict.get(key)
        if isinstance(raw_segments, list):
            return [dict(item) for item in raw_segments if isinstance(item, dict)]

    face_reaction_report = source_dict.get("face_reaction_report")
    if isinstance(face_reaction_report, dict):
        report_segments = _extract_face_reaction_segments(face_reaction_report)
        if report_segments:
            return report_segments

    face_reaction_result = source_dict.get("face_reaction_result")
    if isinstance(face_reaction_result, dict):
        result_segments = _extract_face_reaction_segments(face_reaction_result)
        if result_segments:
            return result_segments

    for attr_name in (
        "face_reaction_segments",
        "segments",
        "face_reaction_report",
        "face_reaction_result",
    ):
        raw_value = getattr(source, attr_name, None)

        if isinstance(raw_value, list):
            result: list[dict[str, Any]] = []
            for item in raw_value:
                item_dict = _safe_dict(item)
                if item_dict:
                    result.append(item_dict)
            if result:
                return result

        raw_dict = _safe_dict(raw_value)
        if raw_dict:
            nested_segments = _extract_face_reaction_segments(raw_dict)
            if nested_segments:
                return nested_segments

    return []


def _mapping_for_reaction_type(reaction_type: str) -> dict[str, str]:
    if reaction_type in {
        REACTION_HYPE_CANDIDATE,
        REACTION_EXPRESSIVE_CANDIDATE,
    }:
        return {
            "signal_type": SIGNAL_TYPE_HIGH_REACTION,
            "action_hint": "keep_or_emphasize_reaction",
            "priority": "high",
            "reason": "high_face_reaction_detected",
        }

    if reaction_type == REACTION_SHOCK_CANDIDATE:
        return {
            "signal_type": SIGNAL_TYPE_SHOCK,
            "action_hint": "review_reaction_zoom_candidate",
            "priority": "high",
            "reason": "shock_reaction_candidate_detected",
        }

    if reaction_type == REACTION_LAUGH_CANDIDATE:
        return {
            "signal_type": SIGNAL_TYPE_LAUGH,
            "action_hint": "review_reaction_moment",
            "priority": "high",
            "reason": "laugh_reaction_candidate_detected",
        }

    if reaction_type == REACTION_MOUTH_OPEN_CANDIDATE:
        return {
            "signal_type": SIGNAL_TYPE_MOUTH_OPEN,
            "action_hint": "review_reaction_moment",
            "priority": "medium",
            "reason": "mouth_open_candidate_detected",
        }

    if reaction_type == REACTION_NEUTRAL_FACE:
        return {
            "signal_type": SIGNAL_TYPE_NEUTRAL,
            "action_hint": "context_face_presence",
            "priority": "low",
            "reason": "neutral_face_presence_detected",
        }

    return {
        "signal_type": SIGNAL_TYPE_HIGH_REACTION,
        "action_hint": "review_reaction_moment",
        "priority": "low",
        "reason": "unknown_face_reaction_candidate_detected",
    }


def _signal_score_for_reaction_type(
    reaction_type: str,
    avg_reaction_score: float,
    max_reaction_score: float,
) -> float:
    if reaction_type == REACTION_NEUTRAL_FACE:
        return _clamp_score(avg_reaction_score)

    return _clamp_score(max_reaction_score if max_reaction_score > 0 else avg_reaction_score)


def build_face_reaction_signal(
    face_reaction_segment: dict[str, Any],
    source_index: int = 0,
) -> dict[str, Any]:
    reaction_type = _safe_string(
        face_reaction_segment.get("reaction_type"),
        REACTION_EXPRESSIVE_CANDIDATE,
    )
    mapping = _mapping_for_reaction_type(reaction_type)

    start_seconds = max(0.0, _safe_float(face_reaction_segment.get("start_seconds"), 0.0))
    end_seconds = max(
        start_seconds,
        _safe_float(face_reaction_segment.get("end_seconds"), start_seconds),
    )

    duration_seconds = _safe_float(
        face_reaction_segment.get("duration_seconds"),
        end_seconds - start_seconds,
    )
    duration_seconds = max(0.0, duration_seconds)

    center_seconds = start_seconds + (duration_seconds / 2.0)
    if end_seconds > start_seconds:
        center_seconds = start_seconds + ((end_seconds - start_seconds) / 2.0)

    avg_reaction_score = _clamp_score(
        face_reaction_segment.get("avg_reaction_score"),
        0.0,
    )
    max_reaction_score = _clamp_score(
        face_reaction_segment.get("max_reaction_score"),
        avg_reaction_score,
    )
    avg_face_area_ratio = max(
        0.0,
        _safe_float(face_reaction_segment.get("avg_face_area_ratio"), 0.0),
    )

    signal_score = _signal_score_for_reaction_type(
        reaction_type=reaction_type,
        avg_reaction_score=avg_reaction_score,
        max_reaction_score=max_reaction_score,
    )
    confidence = _clamp_score(face_reaction_segment.get("confidence"), signal_score)
    signal_type = mapping["signal_type"]

    return {
        "signal_id": (
            f"face_reaction_{source_index}_{signal_type}_"
            f"{start_seconds:.3f}_{end_seconds:.3f}"
        ),
        "signal_type": signal_type,
        "source": SOURCE_FACE_REACTION,
        "start_seconds": round(start_seconds, 6),
        "end_seconds": round(end_seconds, 6),
        "center_seconds": round(center_seconds, 6),
        "duration_seconds": round(duration_seconds, 6),
        "signal_score": signal_score,
        "priority": mapping["priority"],
        "action_hint": mapping["action_hint"],
        "reason": mapping["reason"],
        "confidence": confidence,
        "metadata": {
            "original_reaction_type": reaction_type,
            "avg_reaction_score": avg_reaction_score,
            "max_reaction_score": max_reaction_score,
            "avg_face_area_ratio": avg_face_area_ratio,
            "recommendation": _safe_string(
                face_reaction_segment.get("recommendation"),
                "",
            ),
            "source_index": source_index,
            "warnings": _safe_list(face_reaction_segment.get("warnings")),
            "errors": _safe_list(face_reaction_segment.get("errors")),
        },
    }


@dataclass
class FaceReactionSignalAdapterResult:
    status: str
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0
    high_reaction_signal_count: int = 0
    shock_signal_count: int = 0
    laugh_signal_count: int = 0
    mouth_open_signal_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "signals": [dict(signal) for signal in self.signals],
            "signal_count": self.signal_count,
            "high_reaction_signal_count": self.high_reaction_signal_count,
            "shock_signal_count": self.shock_signal_count,
            "laugh_signal_count": self.laugh_signal_count,
            "mouth_open_signal_count": self.mouth_open_signal_count,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "FaceReactionSignalAdapterResult":
        if not isinstance(data, dict):
            data = {}

        signals = data.get("signals")
        if not isinstance(signals, list):
            signals = []

        return cls(
            status=_safe_string(data.get("status"), STATUS_FAILED),
            signals=[dict(signal) for signal in signals if isinstance(signal, dict)],
            signal_count=int(data.get("signal_count", 0) or 0),
            high_reaction_signal_count=int(
                data.get("high_reaction_signal_count", 0) or 0
            ),
            shock_signal_count=int(data.get("shock_signal_count", 0) or 0),
            laugh_signal_count=int(data.get("laugh_signal_count", 0) or 0),
            mouth_open_signal_count=int(
                data.get("mouth_open_signal_count", 0) or 0
            ),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
            recommendation=_safe_string(data.get("recommendation"), "review"),
        )


def adapt_face_reaction_segments_to_signals(
    face_reaction_segments: list[Any],
) -> FaceReactionSignalAdapterResult:
    try:
        valid_segments: list[dict[str, Any]] = []
        warnings: list[str] = []

        for index, segment in enumerate(face_reaction_segments):
            segment_dict = _safe_dict(segment)
            if not segment_dict:
                warnings.append(f"invalid_face_reaction_segment_skipped:{index}")
                continue
            valid_segments.append(segment_dict)

        if not valid_segments:
            return FaceReactionSignalAdapterResult(
                status=STATUS_SKIPPED_NO_FACE_REACTION_SEGMENTS,
                signals=[],
                signal_count=0,
                high_reaction_signal_count=0,
                shock_signal_count=0,
                laugh_signal_count=0,
                mouth_open_signal_count=0,
                warnings=warnings + ["no_face_reaction_segments_found"],
                errors=[],
                recommendation="provide_face_reaction_segments",
            )

        signals = [
            build_face_reaction_signal(segment, source_index=index)
            for index, segment in enumerate(valid_segments)
        ]

        high_reaction_signal_count = sum(
            1
            for signal in signals
            if signal.get("signal_type") == SIGNAL_TYPE_HIGH_REACTION
        )
        shock_signal_count = sum(
            1 for signal in signals if signal.get("signal_type") == SIGNAL_TYPE_SHOCK
        )
        laugh_signal_count = sum(
            1 for signal in signals if signal.get("signal_type") == SIGNAL_TYPE_LAUGH
        )
        mouth_open_signal_count = sum(
            1
            for signal in signals
            if signal.get("signal_type") == SIGNAL_TYPE_MOUTH_OPEN
        )

        status = STATUS_OK
        if warnings:
            status = STATUS_COMPLETED_WITH_WARNINGS

        recommendation = "review_face_reaction_signals"
        if shock_signal_count > 0:
            recommendation = "review_shock_reaction_candidates"
        elif laugh_signal_count > 0:
            recommendation = "review_laugh_reaction_candidates"
        elif high_reaction_signal_count > 0:
            recommendation = "review_high_face_reaction_segments"

        return FaceReactionSignalAdapterResult(
            status=status,
            signals=signals,
            signal_count=len(signals),
            high_reaction_signal_count=high_reaction_signal_count,
            shock_signal_count=shock_signal_count,
            laugh_signal_count=laugh_signal_count,
            mouth_open_signal_count=mouth_open_signal_count,
            warnings=warnings,
            errors=[],
            recommendation=recommendation,
        )

    except Exception as exc:
        return FaceReactionSignalAdapterResult(
            status=STATUS_FAILED,
            signals=[],
            signal_count=0,
            high_reaction_signal_count=0,
            shock_signal_count=0,
            laugh_signal_count=0,
            mouth_open_signal_count=0,
            warnings=[],
            errors=[f"face_reaction_signal_adapter_failed: {exc}"],
            recommendation="review_face_reaction_signal_adapter_error",
        )


def adapt_face_reaction_report_to_signals(
    face_reaction_report: Any,
) -> FaceReactionSignalAdapterResult:
    try:
        face_reaction_segments = _extract_face_reaction_segments(face_reaction_report)

        return adapt_face_reaction_segments_to_signals(face_reaction_segments)

    except Exception as exc:
        return FaceReactionSignalAdapterResult(
            status=STATUS_FAILED,
            signals=[],
            signal_count=0,
            high_reaction_signal_count=0,
            shock_signal_count=0,
            laugh_signal_count=0,
            mouth_open_signal_count=0,
            warnings=[],
            errors=[f"face_reaction_report_signal_adapter_failed: {exc}"],
            recommendation="review_face_reaction_signal_adapter_error",
        )
