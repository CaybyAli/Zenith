from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_SKIPPED_NO_MOTION_SEGMENTS = "skipped_no_motion_segments"
STATUS_FAILED = "failed"

CLASSIFICATION_STATIC = "static"
CLASSIFICATION_LOW_MOTION = "low_motion"
CLASSIFICATION_MEDIUM_MOTION = "medium_motion"
CLASSIFICATION_HIGH_MOTION = "high_motion"
CLASSIFICATION_DEAD_VISUAL_CANDIDATE = "dead_visual_candidate"

SIGNAL_TYPE_HIGH_ACTIVITY = "motion_high_activity_segment"
SIGNAL_TYPE_DEAD_VISUAL = "motion_dead_visual_candidate"
SIGNAL_TYPE_LOW_ACTIVITY = "motion_low_activity_segment"
SIGNAL_TYPE_STATIC = "motion_static_segment"
SIGNAL_TYPE_MEDIUM_ACTIVITY = "motion_medium_activity_segment"

SOURCE_MOTION_ANALYSIS = "motion_analysis"


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


def _extract_motion_segments(source: Any) -> list[dict[str, Any]]:
    source_dict = _safe_dict(source)

    for key in ("motion_segments", "motion_analysis_segments", "segments"):
        raw_segments = source_dict.get(key)
        if isinstance(raw_segments, list):
            return [
                dict(item)
                for item in raw_segments
                if isinstance(item, dict)
            ]

    motion_analysis_report = source_dict.get("motion_analysis_report")
    if isinstance(motion_analysis_report, dict):
        report_segments = _extract_motion_segments(motion_analysis_report)
        if report_segments:
            return report_segments

    motion_analysis_result = source_dict.get("motion_analysis_result")
    if isinstance(motion_analysis_result, dict):
        result_segments = _extract_motion_segments(motion_analysis_result)
        if result_segments:
            return result_segments

    for attr_name in (
        "motion_segments",
        "motion_analysis_segments",
        "segments",
        "motion_analysis_report",
        "motion_analysis_result",
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
            nested_segments = _extract_motion_segments(raw_dict)
            if nested_segments:
                return nested_segments

    return []


def _mapping_for_motion_classification(classification: str) -> dict[str, str]:
    if classification == CLASSIFICATION_HIGH_MOTION:
        return {
            "signal_type": SIGNAL_TYPE_HIGH_ACTIVITY,
            "action_hint": "keep_or_review_action_moment",
            "priority": "high",
            "reason": "high_motion_detected",
        }

    if classification == CLASSIFICATION_DEAD_VISUAL_CANDIDATE:
        return {
            "signal_type": SIGNAL_TYPE_DEAD_VISUAL,
            "action_hint": "review_or_trim_dead_visual",
            "priority": "high",
            "reason": "dead_visual_candidate_detected",
        }

    if classification == CLASSIFICATION_LOW_MOTION:
        return {
            "signal_type": SIGNAL_TYPE_LOW_ACTIVITY,
            "action_hint": "review_possible_trim",
            "priority": "medium",
            "reason": "low_motion_detected",
        }

    if classification == CLASSIFICATION_STATIC:
        return {
            "signal_type": SIGNAL_TYPE_STATIC,
            "action_hint": "review_possible_trim",
            "priority": "medium",
            "reason": "static_visual_segment_detected",
        }

    if classification == CLASSIFICATION_MEDIUM_MOTION:
        return {
            "signal_type": SIGNAL_TYPE_MEDIUM_ACTIVITY,
            "action_hint": "context_motion_segment",
            "priority": "low",
            "reason": "medium_motion_detected",
        }

    return {
        "signal_type": "motion_unknown_activity_segment",
        "action_hint": "review_motion_segment",
        "priority": "low",
        "reason": "unknown_motion_classification_detected",
    }


def _signal_score_for_classification(
    classification: str,
    avg_motion_score: float,
    max_motion_score: float,
) -> float:
    if classification == CLASSIFICATION_HIGH_MOTION:
        return _clamp_score(max_motion_score if max_motion_score > 0 else avg_motion_score)

    if classification in {
        CLASSIFICATION_DEAD_VISUAL_CANDIDATE,
        CLASSIFICATION_LOW_MOTION,
        CLASSIFICATION_STATIC,
    }:
        return _clamp_score(1.0 - avg_motion_score)

    return _clamp_score(avg_motion_score)


def build_motion_analysis_signal(
    motion_segment: dict[str, Any],
    source_index: int = 0,
) -> dict[str, Any]:
    classification = _safe_string(
        motion_segment.get("classification"),
        CLASSIFICATION_MEDIUM_MOTION,
    )

    mapping = _mapping_for_motion_classification(classification)

    start_seconds = max(0.0, _safe_float(motion_segment.get("start_seconds"), 0.0))
    end_seconds = max(start_seconds, _safe_float(motion_segment.get("end_seconds"), start_seconds))

    duration_seconds = _safe_float(
        motion_segment.get("duration_seconds"),
        end_seconds - start_seconds,
    )
    duration_seconds = max(0.0, duration_seconds)

    center_seconds = start_seconds + (duration_seconds / 2.0)
    if end_seconds > start_seconds:
        center_seconds = start_seconds + ((end_seconds - start_seconds) / 2.0)

    avg_motion_score = _clamp_score(motion_segment.get("avg_motion_score"), 0.0)
    max_motion_score = _clamp_score(motion_segment.get("max_motion_score"), avg_motion_score)
    signal_score = _signal_score_for_classification(
        classification=classification,
        avg_motion_score=avg_motion_score,
        max_motion_score=max_motion_score,
    )

    confidence = _clamp_score(motion_segment.get("confidence"), signal_score)

    signal_type = mapping["signal_type"]

    return {
        "signal_id": (
            f"motion_analysis_{source_index}_{signal_type}_"
            f"{start_seconds:.3f}_{end_seconds:.3f}"
        ),
        "signal_type": signal_type,
        "source": SOURCE_MOTION_ANALYSIS,
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
            "original_classification": classification,
            "avg_motion_score": avg_motion_score,
            "max_motion_score": max_motion_score,
            "recommendation": _safe_string(
                motion_segment.get("recommendation"),
                "",
            ),
            "source_index": source_index,
            "warnings": _safe_list(motion_segment.get("warnings")),
            "errors": _safe_list(motion_segment.get("errors")),
        },
    }


@dataclass
class MotionAnalysisSignalAdapterResult:
    status: str
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0
    high_motion_signal_count: int = 0
    low_motion_signal_count: int = 0
    static_signal_count: int = 0
    dead_visual_candidate_signal_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "signals": [dict(signal) for signal in self.signals],
            "signal_count": self.signal_count,
            "high_motion_signal_count": self.high_motion_signal_count,
            "low_motion_signal_count": self.low_motion_signal_count,
            "static_signal_count": self.static_signal_count,
            "dead_visual_candidate_signal_count": (
                self.dead_visual_candidate_signal_count
            ),
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "MotionAnalysisSignalAdapterResult":
        if not isinstance(data, dict):
            data = {}

        signals = data.get("signals")
        if not isinstance(signals, list):
            signals = []

        return cls(
            status=_safe_string(data.get("status"), STATUS_FAILED),
            signals=[dict(signal) for signal in signals if isinstance(signal, dict)],
            signal_count=int(data.get("signal_count", 0) or 0),
            high_motion_signal_count=int(
                data.get("high_motion_signal_count", 0) or 0
            ),
            low_motion_signal_count=int(
                data.get("low_motion_signal_count", 0) or 0
            ),
            static_signal_count=int(data.get("static_signal_count", 0) or 0),
            dead_visual_candidate_signal_count=int(
                data.get("dead_visual_candidate_signal_count", 0) or 0
            ),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
            recommendation=_safe_string(data.get("recommendation"), "review"),
        )


def adapt_motion_segments_to_signals(
    motion_segments: list[Any],
) -> MotionAnalysisSignalAdapterResult:
    try:
        valid_segments: list[dict[str, Any]] = []
        warnings: list[str] = []

        for index, segment in enumerate(motion_segments):
            segment_dict = _safe_dict(segment)

            if not segment_dict:
                warnings.append(f"invalid_motion_segment_skipped:{index}")
                continue

            valid_segments.append(segment_dict)

        if not valid_segments:
            return MotionAnalysisSignalAdapterResult(
                status=STATUS_SKIPPED_NO_MOTION_SEGMENTS,
                signals=[],
                signal_count=0,
                high_motion_signal_count=0,
                low_motion_signal_count=0,
                static_signal_count=0,
                dead_visual_candidate_signal_count=0,
                warnings=warnings + ["no_motion_segments_found"],
                errors=[],
                recommendation="provide_motion_segments",
            )

        signals = [
            build_motion_analysis_signal(segment, source_index=index)
            for index, segment in enumerate(valid_segments)
        ]

        high_motion_signal_count = sum(
            1 for signal in signals
            if signal.get("signal_type") == SIGNAL_TYPE_HIGH_ACTIVITY
        )
        low_motion_signal_count = sum(
            1 for signal in signals
            if signal.get("signal_type") == SIGNAL_TYPE_LOW_ACTIVITY
        )
        static_signal_count = sum(
            1 for signal in signals
            if signal.get("signal_type") == SIGNAL_TYPE_STATIC
        )
        dead_visual_candidate_signal_count = sum(
            1 for signal in signals
            if signal.get("signal_type") == SIGNAL_TYPE_DEAD_VISUAL
        )

        status = STATUS_OK
        if warnings:
            status = STATUS_COMPLETED_WITH_WARNINGS

        recommendation = "review_motion_signals"
        if dead_visual_candidate_signal_count > 0:
            recommendation = "review_dead_visual_candidates"
        elif high_motion_signal_count > 0:
            recommendation = "review_high_motion_segments"

        return MotionAnalysisSignalAdapterResult(
            status=status,
            signals=signals,
            signal_count=len(signals),
            high_motion_signal_count=high_motion_signal_count,
            low_motion_signal_count=low_motion_signal_count,
            static_signal_count=static_signal_count,
            dead_visual_candidate_signal_count=dead_visual_candidate_signal_count,
            warnings=warnings,
            errors=[],
            recommendation=recommendation,
        )

    except Exception as exc:
        return MotionAnalysisSignalAdapterResult(
            status=STATUS_FAILED,
            signals=[],
            signal_count=0,
            high_motion_signal_count=0,
            low_motion_signal_count=0,
            static_signal_count=0,
            dead_visual_candidate_signal_count=0,
            warnings=[],
            errors=[f"motion_signal_adapter_failed: {exc}"],
            recommendation="review_motion_signal_adapter_error",
        )


def adapt_motion_analysis_report_to_signals(
    motion_analysis_report: Any,
) -> MotionAnalysisSignalAdapterResult:
    try:
        motion_segments = _extract_motion_segments(motion_analysis_report)

        return adapt_motion_segments_to_signals(motion_segments)

    except Exception as exc:
        return MotionAnalysisSignalAdapterResult(
            status=STATUS_FAILED,
            signals=[],
            signal_count=0,
            high_motion_signal_count=0,
            low_motion_signal_count=0,
            static_signal_count=0,
            dead_visual_candidate_signal_count=0,
            warnings=[],
            errors=[f"motion_report_signal_adapter_failed: {exc}"],
            recommendation="review_motion_signal_adapter_error",
        )
