from __future__ import annotations

import math
from typing import Any

from models.beat_detection_signal import BeatDetectionSignalAdapterResult


REQUIRED_SIGNAL_FIELDS = [
    "signal_type",
    "source",
    "start_seconds",
    "end_seconds",
    "center_seconds",
    "signal_score",
    "priority",
    "reason",
    "beat_time_seconds",
    "beat_strength",
    "beat_confidence",
    "estimated_bpm",
    "beat_index",
    "beat_count",
    "source_beat",
    "metadata",
]


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


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        converted = float(value)
    except (TypeError, ValueError):
        return default

    if not math.isfinite(converted):
        return default

    return converted


def _safe_optional_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        converted = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(converted):
        return None

    return converted


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value

    if value is None:
        return default

    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}

    return bool(value)


def _clamp(value: float, minimum: float = 0.0, maximum: float = 1.0) -> float:
    safe_value = _safe_float(value, minimum)
    return max(minimum, min(maximum, safe_value))


def _get_value(source: Any, key: str) -> Any:
    if source is None:
        return None

    if isinstance(source, dict):
        return source.get(key)

    return getattr(source, key, None)


def _as_beat_dict(value: Any) -> dict[str, Any] | None:
    beat = _safe_dict(value)

    if not beat:
        return None

    if "time_seconds" not in beat and "beat_time_seconds" not in beat:
        return None

    return beat


def _extract_from_list(source: Any) -> list[dict[str, Any]]:
    if not isinstance(source, list):
        return []

    beats: list[dict[str, Any]] = []

    for item in source:
        beat = _as_beat_dict(item)
        if beat is not None:
            beats.append(beat)

    return beats


def extract_beat_dicts(source: Any) -> list[dict[str, Any]]:
    if source is None:
        return []

    if isinstance(source, list):
        return _extract_from_list(source)

    source_dict = _safe_dict(source)

    if source_dict:
        direct_beats = source_dict.get("beats")
        beats = _extract_from_list(direct_beats)
        if beats:
            return beats

        beat_detection_result = source_dict.get("beat_detection_result")
        result_dict = _safe_dict(beat_detection_result)
        beats = _extract_from_list(result_dict.get("beats"))
        if beats:
            return beats

    for attribute_name in [
        "beat_detection_report",
        "beat_detection_result",
        "beat_detection_beats",
    ]:
        attribute_value = _get_value(source, attribute_name)

        if attribute_name == "beat_detection_beats":
            beats = _extract_from_list(attribute_value)
            if beats:
                return beats
            continue

        attribute_dict = _safe_dict(attribute_value)
        beats = _extract_from_list(attribute_dict.get("beats"))
        if beats:
            return beats

        nested_result = attribute_dict.get("beat_detection_result")
        nested_dict = _safe_dict(nested_result)
        beats = _extract_from_list(nested_dict.get("beats"))
        if beats:
            return beats

    return []


def beat_to_signal(
    beat: Any,
    source_index: int = 0,
    beat_count: int | None = None,
    estimated_bpm: float | None = None,
    window_before_seconds: float = 0.12,
    window_after_seconds: float = 0.12,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    source_beat = _safe_dict(beat)

    if not source_beat:
        return None

    time_value = source_beat.get("time_seconds")
    if time_value is None:
        time_value = source_beat.get("beat_time_seconds")

    center_seconds = _safe_optional_float(time_value)
    if center_seconds is None:
        return None

    if center_seconds < 0:
        return None

    strength = _clamp(_safe_float(source_beat.get("strength"), 0.0))
    confidence = _clamp(_safe_float(source_beat.get("confidence"), 0.0))
    is_downbeat_candidate = _safe_bool(source_beat.get("is_downbeat_candidate"), False)

    base_score = max(strength, confidence)

    if is_downbeat_candidate:
        signal_type = "beat_downbeat_candidate"
        signal_score = max(base_score, 0.9)
    elif strength >= 0.80 or confidence >= 0.80:
        signal_type = "beat_strong_sync_point"
        signal_score = base_score
    elif strength >= 0.50 or confidence >= 0.50:
        signal_type = "beat_sync_point"
        signal_score = base_score
    else:
        signal_type = "beat_soft_sync_point"
        signal_score = base_score

    signal_score = _clamp(signal_score)

    if signal_score >= 0.8:
        priority = "high"
    elif signal_score >= 0.5:
        priority = "medium"
    else:
        priority = "low"

    before = max(0.0, _safe_float(window_before_seconds, 0.12))
    after = max(0.0, _safe_float(window_after_seconds, 0.12))

    signal_metadata = dict(metadata) if isinstance(metadata, dict) else {}

    safe_beat_count = beat_count
    if safe_beat_count is None:
        safe_beat_count = _safe_int(source_beat.get("beat_count"), 0)

    safe_estimated_bpm = estimated_bpm
    if safe_estimated_bpm is None:
        safe_estimated_bpm = _safe_optional_float(source_beat.get("bpm_context"))

    return {
        "signal_type": signal_type,
        "source": "beat_detection_signal_adapter",
        "start_seconds": max(0.0, center_seconds - before),
        "end_seconds": center_seconds + after,
        "center_seconds": center_seconds,
        "signal_score": signal_score,
        "priority": priority,
        "reason": f"{signal_type}_from_detected_beat",
        "beat_time_seconds": center_seconds,
        "beat_strength": strength,
        "beat_confidence": confidence,
        "estimated_bpm": safe_estimated_bpm,
        "beat_index": source_index,
        "beat_count": safe_beat_count,
        "source_beat": dict(source_beat),
        "metadata": signal_metadata,
    }


def _count_signal_types(signals: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}

    for signal in signals:
        signal_type = str(signal.get("signal_type", "unknown"))
        counts[signal_type] = counts.get(signal_type, 0) + 1

    return counts


def _score_stats(signals: list[dict[str, Any]]) -> tuple[float, float]:
    if not signals:
        return 0.0, 0.0

    scores = [_safe_float(signal.get("signal_score"), 0.0) for signal in signals]

    return max(scores), sum(scores) / len(scores)


def adapt_beats_to_signals(
    beats: Any,
    estimated_bpm: float | None = None,
    max_signals: int | None = None,
    window_before_seconds: float = 0.12,
    window_after_seconds: float = 0.12,
    metadata: dict[str, Any] | None = None,
) -> BeatDetectionSignalAdapterResult:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}

    try:
        beat_dicts = extract_beat_dicts(beats)

        if not beat_dicts:
            return BeatDetectionSignalAdapterResult(
                status="skipped_no_beats",
                signals=[],
                signal_count=0,
                beat_count=0,
                estimated_bpm=estimated_bpm,
                recommendation="no_beats_available",
                warnings=["no_beats_available"],
                errors=[],
                metadata=safe_metadata,
            )

        signals: list[dict[str, Any]] = []
        bad_beat_count = 0

        for index, beat in enumerate(beat_dicts):
            signal = beat_to_signal(
                beat=beat,
                source_index=index,
                beat_count=len(beat_dicts),
                estimated_bpm=estimated_bpm,
                window_before_seconds=window_before_seconds,
                window_after_seconds=window_after_seconds,
                metadata=safe_metadata,
            )

            if signal is None:
                bad_beat_count += 1
                continue

            signals.append(signal)

        if max_signals is not None:
            safe_max_signals = max(0, _safe_int(max_signals, 0))
            if safe_max_signals > 0:
                signals = sorted(
                    signals,
                    key=lambda signal: _safe_float(signal.get("signal_score"), 0.0),
                    reverse=True,
                )[:safe_max_signals]
                signals = sorted(
                    signals,
                    key=lambda signal: _safe_float(signal.get("center_seconds"), 0.0),
                )

        if not signals:
            return BeatDetectionSignalAdapterResult(
                status="completed_with_warnings",
                signals=[],
                signal_count=0,
                beat_count=len(beat_dicts),
                estimated_bpm=estimated_bpm,
                recommendation="review_warnings",
                warnings=["no_valid_beat_signals_created"],
                errors=[],
                metadata=safe_metadata,
            )

        max_score, avg_score = _score_stats(signals)
        signal_types = _count_signal_types(signals)
        high_priority_count = len(
            [signal for signal in signals if signal.get("priority") == "high"]
        )

        warnings: list[str] = []
        if bad_beat_count > 0:
            warnings.append("some_beats_could_not_be_converted")

        status = "ok" if not warnings else "completed_with_warnings"
        recommendation = "use_beat_edit_signals" if not warnings else "review_warnings"

        return BeatDetectionSignalAdapterResult(
            status=status,
            signals=signals,
            signal_count=len(signals),
            high_priority_signal_count=high_priority_count,
            signal_types=signal_types,
            max_signal_score=max_score,
            avg_signal_score=avg_score,
            beat_count=len(beat_dicts),
            estimated_bpm=estimated_bpm,
            warnings=warnings,
            errors=[],
            recommendation=recommendation,
            metadata=safe_metadata,
        )

    except Exception as exc:
        return BeatDetectionSignalAdapterResult(
            status="failed",
            signals=[],
            signal_count=0,
            beat_count=0,
            estimated_bpm=estimated_bpm,
            recommendation="retry_or_fix_beat_report",
            warnings=[],
            errors=["beat_detection_signal_adapter_failed"],
            metadata={
                **safe_metadata,
                "error_detail": str(exc),
            },
        )


def adapt_beat_detection_run_report_to_signals(
    beat_report: Any,
    max_signals: int | None = None,
    window_before_seconds: float = 0.12,
    window_after_seconds: float = 0.12,
    metadata: dict[str, Any] | None = None,
) -> BeatDetectionSignalAdapterResult:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}

    try:
        report_dict = _safe_dict(beat_report)

        if not report_dict:
            return BeatDetectionSignalAdapterResult(
                status="skipped_no_beat_report",
                signals=[],
                signal_count=0,
                beat_count=0,
                estimated_bpm=None,
                recommendation="no_beat_report_available",
                warnings=["no_beat_report_available"],
                errors=[],
                metadata=safe_metadata,
            )

        estimated_bpm = _safe_optional_float(report_dict.get("estimated_bpm"))
        beat_count = _safe_int(report_dict.get("beat_count"), 0)

        report_metadata = {
            **safe_metadata,
            "beat_detection_status": report_dict.get("status"),
            "selected_type": report_dict.get("selected_type"),
            "selected_path": report_dict.get("selected_path"),
            "estimated_bpm": estimated_bpm,
            "beat_count": beat_count,
        }

        result = adapt_beats_to_signals(
            beats=report_dict,
            estimated_bpm=estimated_bpm,
            max_signals=max_signals,
            window_before_seconds=window_before_seconds,
            window_after_seconds=window_after_seconds,
            metadata=report_metadata,
        )

        result.beat_count = beat_count if beat_count > 0 else result.beat_count
        result.estimated_bpm = estimated_bpm
        result.metadata = report_metadata

        return result

    except Exception as exc:
        return BeatDetectionSignalAdapterResult(
            status="failed",
            signals=[],
            signal_count=0,
            beat_count=0,
            estimated_bpm=None,
            recommendation="retry_or_fix_beat_report",
            warnings=[],
            errors=["beat_detection_signal_adapter_failed"],
            metadata={
                **safe_metadata,
                "error_detail": str(exc),
            },
        )
