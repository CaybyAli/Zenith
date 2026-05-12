from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_SKIPPED_NO_VISUAL_ENERGY_SEGMENTS = "skipped_no_visual_energy_segments"
STATUS_FAILED = "failed"

CLASSIFICATION_PEAK_VISUAL_ENERGY = "peak_visual_energy"
CLASSIFICATION_HIGH_VISUAL_ENERGY = "high_visual_energy"
CLASSIFICATION_LOW_VISUAL_ENERGY = "low_visual_energy"
CLASSIFICATION_TECHNICAL_WARNING = "technical_warning"

SIGNAL_TYPE_PEAK_VISUAL_ENERGY = "visual_peak_energy_segment"
SIGNAL_TYPE_HIGH_VISUAL_ENERGY = "visual_high_energy_segment"
SIGNAL_TYPE_LOW_VISUAL_ENERGY = "visual_low_energy_segment"
SIGNAL_TYPE_TECHNICAL_WARNING = "visual_technical_warning_segment"

SOURCE_VISUAL_ENERGY = "visual_energy"

FORBIDDEN_ACTION_HINTS = {
    "remove_now",
    "hard_remove",
    "auto_remove",
    "auto_highlight",
    "force_cut",
}


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


def _safe_dict_list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []

    result: list[dict[str, Any]] = []
    for item in value:
        item_dict = _safe_dict(item)
        if item_dict:
            result.append(item_dict)

    return result


def _clamp_score(value: Any, default: float = 0.0) -> float:
    return max(0.0, min(1.0, _safe_float(value, default)))


def _extract_visual_energy_segments(source: Any) -> list[dict[str, Any]]:
    source_dict = _safe_dict(source)

    for key in ("visual_energy_segments", "segments"):
        raw_segments = source_dict.get(key)
        if isinstance(raw_segments, list):
            return [dict(item) for item in raw_segments if isinstance(item, dict)]

    visual_energy_report = source_dict.get("visual_energy_report")
    if isinstance(visual_energy_report, dict):
        report_segments = _extract_visual_energy_segments(visual_energy_report)
        if report_segments:
            return report_segments

    visual_energy_result = source_dict.get("visual_energy_result")
    if isinstance(visual_energy_result, dict):
        result_segments = _extract_visual_energy_segments(visual_energy_result)
        if result_segments:
            return result_segments

    for attr_name in (
        "visual_energy_segments",
        "segments",
        "visual_energy_report",
        "visual_energy_result",
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
            nested_segments = _extract_visual_energy_segments(raw_dict)
            if nested_segments:
                return nested_segments

    return []


def _mapping_for_classification(classification: str) -> dict[str, str] | None:
    if classification == CLASSIFICATION_PEAK_VISUAL_ENERGY:
        return {
            "signal_type": SIGNAL_TYPE_PEAK_VISUAL_ENERGY,
            "action_hint": "review_visual_highlight_candidate",
            "priority": "high",
            "reason": "peak_visual_energy_detected",
        }

    if classification == CLASSIFICATION_HIGH_VISUAL_ENERGY:
        return {
            "signal_type": SIGNAL_TYPE_HIGH_VISUAL_ENERGY,
            "action_hint": "review_visual_engagement_candidate",
            "priority": "high",
            "reason": "high_visual_energy_detected",
        }

    if classification == CLASSIFICATION_LOW_VISUAL_ENERGY:
        return {
            "signal_type": SIGNAL_TYPE_LOW_VISUAL_ENERGY,
            "action_hint": "review_possible_trim_low_visual_energy",
            "priority": "medium",
            "reason": "low_visual_energy_detected",
        }

    if classification == CLASSIFICATION_TECHNICAL_WARNING:
        return {
            "signal_type": SIGNAL_TYPE_TECHNICAL_WARNING,
            "action_hint": "review_visual_technical_warning",
            "priority": "high",
            "reason": "visual_technical_warning_detected",
        }

    return None


def _validate_action_hint(action_hint: str) -> str:
    if action_hint in FORBIDDEN_ACTION_HINTS:
        return "review_visual_energy_segment"
    return action_hint


def build_visual_energy_signal(
    visual_energy_segment: dict[str, Any],
    source_index: int = 0,
) -> dict[str, Any] | None:
    classification = _safe_string(
        visual_energy_segment.get("classification"),
        "",
    )
    mapping = _mapping_for_classification(classification)
    if mapping is None:
        return None

    start_seconds = max(
        0.0,
        _safe_float(visual_energy_segment.get("start_seconds"), 0.0),
    )
    end_seconds = max(
        start_seconds,
        _safe_float(visual_energy_segment.get("end_seconds"), start_seconds),
    )
    duration_seconds = _safe_float(
        visual_energy_segment.get("duration_seconds"),
        end_seconds - start_seconds,
    )
    duration_seconds = max(0.0, duration_seconds)

    center_seconds = start_seconds + (duration_seconds / 2.0)
    if end_seconds > start_seconds:
        center_seconds = start_seconds + ((end_seconds - start_seconds) / 2.0)

    avg_score = _clamp_score(
        visual_energy_segment.get("avg_visual_energy_score"),
        0.0,
    )
    max_score = _clamp_score(
        visual_energy_segment.get("max_visual_energy_score"),
        avg_score,
    )
    min_score = _clamp_score(
        visual_energy_segment.get("min_visual_energy_score"),
        avg_score,
    )

    signal_score = max_score
    if classification == CLASSIFICATION_LOW_VISUAL_ENERGY:
        signal_score = 1.0 - avg_score

    action_hint = _validate_action_hint(mapping["action_hint"])

    return {
        "signal_id": (
            f"visual_energy_{source_index}_{mapping['signal_type']}_"
            f"{start_seconds:.3f}_{end_seconds:.3f}"
        ),
        "signal_type": mapping["signal_type"],
        "source": SOURCE_VISUAL_ENERGY,
        "start_seconds": round(start_seconds, 6),
        "end_seconds": round(end_seconds, 6),
        "center_seconds": round(center_seconds, 6),
        "duration_seconds": round(duration_seconds, 6),
        "signal_score": signal_score,
        "priority": mapping["priority"],
        "action_hint": action_hint,
        "reason": mapping["reason"],
        "confidence": None,
        "metadata": {
            "classification": classification,
            "avg_visual_energy_score": avg_score,
            "max_visual_energy_score": max_score,
            "min_visual_energy_score": min_score,
            "recommendation": _safe_string(
                visual_energy_segment.get("recommendation"),
                "",
            ),
            "source_index": source_index,
            "warnings": _safe_list(visual_energy_segment.get("warnings")),
            "errors": _safe_list(visual_energy_segment.get("errors")),
            "no_cut_decision": True,
            "no_auto_remove": True,
            "no_auto_highlight": True,
        },
    }


@dataclass
class VisualEnergySignalAdapterResult:
    status: str
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0
    peak_signal_count: int = 0
    high_signal_count: int = 0
    low_signal_count: int = 0
    technical_warning_signal_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "signals": [dict(signal) for signal in self.signals],
            "signal_count": self.signal_count,
            "peak_signal_count": self.peak_signal_count,
            "high_signal_count": self.high_signal_count,
            "low_signal_count": self.low_signal_count,
            "technical_warning_signal_count": self.technical_warning_signal_count,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "VisualEnergySignalAdapterResult":
        if not isinstance(data, dict):
            data = {}

        signals = data.get("signals")
        if not isinstance(signals, list):
            signals = []

        return cls(
            status=_safe_string(data.get("status"), STATUS_FAILED),
            signals=[dict(signal) for signal in signals if isinstance(signal, dict)],
            signal_count=int(data.get("signal_count", 0) or 0),
            peak_signal_count=int(data.get("peak_signal_count", 0) or 0),
            high_signal_count=int(data.get("high_signal_count", 0) or 0),
            low_signal_count=int(data.get("low_signal_count", 0) or 0),
            technical_warning_signal_count=int(
                data.get("technical_warning_signal_count", 0) or 0
            ),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
            recommendation=_safe_string(data.get("recommendation"), "review"),
        )


def adapt_visual_energy_segments_to_signals(
    visual_energy_segments: list[Any],
) -> VisualEnergySignalAdapterResult:
    try:
        valid_segments: list[dict[str, Any]] = []
        warnings: list[str] = []

        for index, segment in enumerate(visual_energy_segments):
            segment_dict = _safe_dict(segment)
            if not segment_dict:
                warnings.append(f"invalid_visual_energy_segment_skipped:{index}")
                continue
            valid_segments.append(segment_dict)

        if not valid_segments:
            return VisualEnergySignalAdapterResult(
                status=STATUS_SKIPPED_NO_VISUAL_ENERGY_SEGMENTS,
                signals=[],
                signal_count=0,
                peak_signal_count=0,
                high_signal_count=0,
                low_signal_count=0,
                technical_warning_signal_count=0,
                warnings=warnings + ["no_visual_energy_segments_found"],
                errors=[],
                recommendation="provide_visual_energy_segments",
            )

        signals: list[dict[str, Any]] = []
        for index, segment in enumerate(valid_segments):
            signal = build_visual_energy_signal(segment, source_index=index)
            if signal is None:
                warnings.append(f"unsupported_visual_energy_classification_skipped:{index}")
                continue
            signals.append(signal)

        if not signals:
            return VisualEnergySignalAdapterResult(
                status=STATUS_SKIPPED_NO_VISUAL_ENERGY_SEGMENTS,
                signals=[],
                signal_count=0,
                peak_signal_count=0,
                high_signal_count=0,
                low_signal_count=0,
                technical_warning_signal_count=0,
                warnings=warnings + ["no_supported_visual_energy_segments_found"],
                errors=[],
                recommendation="provide_visual_energy_segments",
            )

        peak_signal_count = sum(
            1
            for signal in signals
            if signal.get("signal_type") == SIGNAL_TYPE_PEAK_VISUAL_ENERGY
        )
        high_signal_count = sum(
            1
            for signal in signals
            if signal.get("signal_type") == SIGNAL_TYPE_HIGH_VISUAL_ENERGY
        )
        low_signal_count = sum(
            1
            for signal in signals
            if signal.get("signal_type") == SIGNAL_TYPE_LOW_VISUAL_ENERGY
        )
        technical_warning_signal_count = sum(
            1
            for signal in signals
            if signal.get("signal_type") == SIGNAL_TYPE_TECHNICAL_WARNING
        )

        status = STATUS_OK
        if warnings:
            status = STATUS_COMPLETED_WITH_WARNINGS

        recommendation = "review_visual_energy_signals"
        if peak_signal_count > 0:
            recommendation = "review_visual_highlight_candidates"
        elif technical_warning_signal_count > 0:
            recommendation = "review_visual_technical_warnings"
        elif low_signal_count > 0:
            recommendation = "review_low_visual_energy_segments"

        return VisualEnergySignalAdapterResult(
            status=status,
            signals=signals,
            signal_count=len(signals),
            peak_signal_count=peak_signal_count,
            high_signal_count=high_signal_count,
            low_signal_count=low_signal_count,
            technical_warning_signal_count=technical_warning_signal_count,
            warnings=warnings,
            errors=[],
            recommendation=recommendation,
        )

    except Exception as exc:
        return VisualEnergySignalAdapterResult(
            status=STATUS_FAILED,
            signals=[],
            signal_count=0,
            peak_signal_count=0,
            high_signal_count=0,
            low_signal_count=0,
            technical_warning_signal_count=0,
            warnings=[],
            errors=[f"visual_energy_signal_adapter_failed: {exc}"],
            recommendation="review_visual_energy_signal_adapter_error",
        )


def adapt_visual_energy_report_to_signals(
    visual_energy_report: Any,
) -> VisualEnergySignalAdapterResult:
    try:
        visual_energy_segments = _extract_visual_energy_segments(visual_energy_report)

        return adapt_visual_energy_segments_to_signals(visual_energy_segments)

    except Exception as exc:
        return VisualEnergySignalAdapterResult(
            status=STATUS_FAILED,
            signals=[],
            signal_count=0,
            peak_signal_count=0,
            high_signal_count=0,
            low_signal_count=0,
            technical_warning_signal_count=0,
            warnings=[],
            errors=[f"visual_energy_report_signal_adapter_failed: {exc}"],
            recommendation="review_visual_energy_signal_adapter_error",
        )
