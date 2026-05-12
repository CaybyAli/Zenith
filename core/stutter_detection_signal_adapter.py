from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_SKIPPED_NO_STUTTER_SEGMENTS = "skipped_no_stutter_segments"
STATUS_FAILED = "failed"

CLASSIFICATION_STUTTER_SEGMENT = "stutter_segment"
CLASSIFICATION_FREEZE_SEGMENT = "freeze_segment"
CLASSIFICATION_ENCODING_DROP_CANDIDATE = "encoding_drop_candidate"

SIGNAL_TYPE_STUTTER = "stutter_segment_candidate"
SIGNAL_TYPE_FREEZE = "freeze_segment_candidate"
SIGNAL_TYPE_ENCODING_DROP = "encoding_drop_candidate"

SOURCE_STUTTER_DETECTION = "stutter_detection"


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


def _safe_optional_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _clamp_score(value: Any, default: float = 0.0) -> float:
    return max(0.0, min(1.0, _safe_float(value, default)))


def _extract_stutter_segments(source: Any) -> list[dict[str, Any]]:
    source_dict = _safe_dict(source)

    for key in ("stutter_segments", "stutter_detection_segments", "segments"):
        raw_segments = source_dict.get(key)
        if isinstance(raw_segments, list):
            return [dict(item) for item in raw_segments if isinstance(item, dict)]

    stutter_detection_report = source_dict.get("stutter_detection_report")
    if isinstance(stutter_detection_report, dict):
        report_segments = _extract_stutter_segments(stutter_detection_report)
        if report_segments:
            return report_segments

    stutter_detection_result = source_dict.get("stutter_detection_result")
    if isinstance(stutter_detection_result, dict):
        result_segments = _extract_stutter_segments(stutter_detection_result)
        if result_segments:
            return result_segments

    for attr_name in (
        "stutter_segments",
        "stutter_detection_segments",
        "segments",
        "stutter_detection_report",
        "stutter_detection_result",
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
            nested_segments = _extract_stutter_segments(raw_dict)
            if nested_segments:
                return nested_segments

    return []


def _mapping_for_classification(classification: str) -> dict[str, str] | None:
    if classification == CLASSIFICATION_STUTTER_SEGMENT:
        return {
            "signal_type": SIGNAL_TYPE_STUTTER,
            "action_hint": "review_stutter_segment",
            "priority": "high",
            "reason": "stutter_segment_detected",
        }

    if classification == CLASSIFICATION_FREEZE_SEGMENT:
        return {
            "signal_type": SIGNAL_TYPE_FREEZE,
            "action_hint": "review_freeze_segment",
            "priority": "high",
            "reason": "freeze_segment_detected",
        }

    if classification == CLASSIFICATION_ENCODING_DROP_CANDIDATE:
        return {
            "signal_type": SIGNAL_TYPE_ENCODING_DROP,
            "action_hint": "review_encoding_drop_candidate",
            "priority": "medium",
            "reason": "encoding_drop_candidate_detected",
        }

    return None


def build_stutter_detection_signal(
    stutter_segment: dict[str, Any],
    source_index: int = 0,
) -> dict[str, Any] | None:
    classification = _safe_string(stutter_segment.get("classification"), "")
    mapping = _mapping_for_classification(classification)
    if mapping is None:
        return None

    start_seconds = max(0.0, _safe_float(stutter_segment.get("start_seconds"), 0.0))
    end_seconds = max(
        start_seconds,
        _safe_float(stutter_segment.get("end_seconds"), start_seconds),
    )

    duration_seconds = _safe_float(
        stutter_segment.get("duration_seconds"),
        end_seconds - start_seconds,
    )
    duration_seconds = max(0.0, duration_seconds)

    center_seconds = start_seconds + (duration_seconds / 2.0)
    if end_seconds > start_seconds:
        center_seconds = start_seconds + ((end_seconds - start_seconds) / 2.0)

    avg_duplicate_score = _clamp_score(stutter_segment.get("avg_duplicate_score"), 0.0)
    max_duplicate_score = _clamp_score(
        stutter_segment.get("max_duplicate_score"),
        avg_duplicate_score,
    )
    signal_score = max_duplicate_score
    confidence = _clamp_score(stutter_segment.get("confidence"), signal_score)
    signal_type = mapping["signal_type"]

    return {
        "signal_id": (
            f"stutter_detection_{source_index}_{signal_type}_"
            f"{start_seconds:.3f}_{end_seconds:.3f}"
        ),
        "signal_type": signal_type,
        "source": SOURCE_STUTTER_DETECTION,
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
            "duplicate_frame_count": _safe_int(
                stutter_segment.get("duplicate_frame_count"),
                0,
            ),
            "avg_duplicate_score": avg_duplicate_score,
            "max_duplicate_score": max_duplicate_score,
            "recommendation": _safe_string(
                stutter_segment.get("recommendation"),
                "",
            ),
            "source_index": source_index,
            "start_frame_index": _safe_optional_int(
                stutter_segment.get("start_frame_index")
            ),
            "end_frame_index": _safe_optional_int(
                stutter_segment.get("end_frame_index")
            ),
            "warnings": _safe_list(stutter_segment.get("warnings")),
            "errors": _safe_list(stutter_segment.get("errors")),
        },
    }


@dataclass
class StutterDetectionSignalAdapterResult:
    status: str
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0
    stutter_signal_count: int = 0
    freeze_signal_count: int = 0
    encoding_drop_signal_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "signals": [dict(signal) for signal in self.signals],
            "signal_count": self.signal_count,
            "stutter_signal_count": self.stutter_signal_count,
            "freeze_signal_count": self.freeze_signal_count,
            "encoding_drop_signal_count": self.encoding_drop_signal_count,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "StutterDetectionSignalAdapterResult":
        if not isinstance(data, dict):
            data = {}

        signals = data.get("signals")
        if not isinstance(signals, list):
            signals = []

        return cls(
            status=_safe_string(data.get("status"), STATUS_FAILED),
            signals=[dict(signal) for signal in signals if isinstance(signal, dict)],
            signal_count=int(data.get("signal_count", 0) or 0),
            stutter_signal_count=int(data.get("stutter_signal_count", 0) or 0),
            freeze_signal_count=int(data.get("freeze_signal_count", 0) or 0),
            encoding_drop_signal_count=int(
                data.get("encoding_drop_signal_count", 0) or 0
            ),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
            recommendation=_safe_string(data.get("recommendation"), "review"),
        )


def adapt_stutter_segments_to_signals(
    stutter_segments: list[Any],
) -> StutterDetectionSignalAdapterResult:
    try:
        valid_segments: list[dict[str, Any]] = []
        warnings: list[str] = []

        for index, segment in enumerate(stutter_segments):
            segment_dict = _safe_dict(segment)
            if not segment_dict:
                warnings.append(f"invalid_stutter_segment_skipped:{index}")
                continue
            valid_segments.append(segment_dict)

        if not valid_segments:
            return StutterDetectionSignalAdapterResult(
                status=STATUS_SKIPPED_NO_STUTTER_SEGMENTS,
                signals=[],
                signal_count=0,
                stutter_signal_count=0,
                freeze_signal_count=0,
                encoding_drop_signal_count=0,
                warnings=warnings + ["no_stutter_segments_found"],
                errors=[],
                recommendation="provide_stutter_segments",
            )

        signals: list[dict[str, Any]] = []
        for index, segment in enumerate(valid_segments):
            signal = build_stutter_detection_signal(segment, source_index=index)
            if signal is None:
                warnings.append(f"unsupported_stutter_classification_skipped:{index}")
                continue
            signals.append(signal)

        if not signals:
            return StutterDetectionSignalAdapterResult(
                status=STATUS_SKIPPED_NO_STUTTER_SEGMENTS,
                signals=[],
                signal_count=0,
                stutter_signal_count=0,
                freeze_signal_count=0,
                encoding_drop_signal_count=0,
                warnings=warnings + ["no_supported_stutter_segments_found"],
                errors=[],
                recommendation="provide_stutter_segments",
            )

        stutter_signal_count = sum(
            1 for signal in signals if signal.get("signal_type") == SIGNAL_TYPE_STUTTER
        )
        freeze_signal_count = sum(
            1 for signal in signals if signal.get("signal_type") == SIGNAL_TYPE_FREEZE
        )
        encoding_drop_signal_count = sum(
            1
            for signal in signals
            if signal.get("signal_type") == SIGNAL_TYPE_ENCODING_DROP
        )

        status = STATUS_OK
        if warnings:
            status = STATUS_COMPLETED_WITH_WARNINGS

        recommendation = "review_stutter_detection_signals"
        if freeze_signal_count > 0:
            recommendation = "review_freeze_segments"
        elif stutter_signal_count > 0:
            recommendation = "review_stutter_segments"
        elif encoding_drop_signal_count > 0:
            recommendation = "review_encoding_drop_candidates"

        return StutterDetectionSignalAdapterResult(
            status=status,
            signals=signals,
            signal_count=len(signals),
            stutter_signal_count=stutter_signal_count,
            freeze_signal_count=freeze_signal_count,
            encoding_drop_signal_count=encoding_drop_signal_count,
            warnings=warnings,
            errors=[],
            recommendation=recommendation,
        )

    except Exception as exc:
        return StutterDetectionSignalAdapterResult(
            status=STATUS_FAILED,
            signals=[],
            signal_count=0,
            stutter_signal_count=0,
            freeze_signal_count=0,
            encoding_drop_signal_count=0,
            warnings=[],
            errors=[f"stutter_detection_signal_adapter_failed: {exc}"],
            recommendation="review_stutter_detection_signal_adapter_error",
        )


def adapt_stutter_detection_report_to_signals(
    stutter_detection_report: Any,
) -> StutterDetectionSignalAdapterResult:
    try:
        stutter_segments = _extract_stutter_segments(stutter_detection_report)

        return adapt_stutter_segments_to_signals(stutter_segments)

    except Exception as exc:
        return StutterDetectionSignalAdapterResult(
            status=STATUS_FAILED,
            signals=[],
            signal_count=0,
            stutter_signal_count=0,
            freeze_signal_count=0,
            encoding_drop_signal_count=0,
            warnings=[],
            errors=[f"stutter_detection_report_signal_adapter_failed: {exc}"],
            recommendation="review_stutter_detection_signal_adapter_error",
        )
