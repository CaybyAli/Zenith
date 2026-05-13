from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_SKIPPED_NO_SEGMENT_CLASSIFICATIONS = "skipped_no_segment_classifications"
STATUS_FAILED = "failed"

SOURCE_SEGMENT_CLASSIFIER = "segment_classifier"


SEGMENT_TYPE_MAPPING = {
    "highlight": {
        "signal_type": "segment_highlight_candidate",
        "action_hint": "review_segment_highlight_candidate",
        "priority": "high",
        "reason": "segment_classifier_highlight_candidate",
    },
    "hook_candidate": {
        "signal_type": "segment_hook_candidate",
        "action_hint": "review_segment_hook_candidate",
        "priority": "high",
        "reason": "segment_classifier_hook_candidate",
    },
    "protected_context": {
        "signal_type": "segment_protected_context",
        "action_hint": "protect_segment_context",
        "priority": "high",
        "reason": "segment_classifier_protected_context",
    },
    "dead_candidate": {
        "signal_type": "segment_dead_candidate",
        "action_hint": "review_segment_dead_candidate",
        "priority": "medium",
        "reason": "segment_classifier_dead_candidate",
    },
    "censor_required_segment": {
        "signal_type": "segment_censor_required",
        "action_hint": "preserve_segment_with_censor_sfx_review",
        "priority": "high",
        "reason": "segment_classifier_censor_required",
    },
    "technical_warning": {
        "signal_type": "segment_technical_warning",
        "action_hint": "review_segment_technical_warning",
        "priority": "high",
        "reason": "segment_classifier_technical_warning",
    },
    "transition": {
        "signal_type": "segment_transition_candidate",
        "action_hint": "review_segment_transition",
        "priority": "medium",
        "reason": "segment_classifier_transition_candidate",
    },
    "filler": {
        "signal_type": "segment_filler_candidate",
        "action_hint": "review_segment_filler_candidate",
        "priority": "medium",
        "reason": "segment_classifier_filler_candidate",
    },
    "normal_content": {
        "signal_type": "segment_normal_content",
        "action_hint": "review_segment_normal_content",
        "priority": "low",
        "reason": "segment_classifier_normal_content",
    },
}


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


def _safe_list(value: Any) -> list[Any]:
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


def _clamp(value: Any, default: float = 0.0) -> float:
    return max(0.0, min(1.0, _safe_float(value, default)))


def _derive_duration(
    start_seconds: float | None,
    end_seconds: float | None,
    duration_seconds: float | None = None,
) -> float | None:
    if duration_seconds is not None:
        return max(0.0, duration_seconds)

    if start_seconds is None or end_seconds is None:
        return None

    return max(0.0, end_seconds - start_seconds)


def _derive_center(
    start_seconds: float | None,
    end_seconds: float | None,
    center_seconds: float | None = None,
) -> float | None:
    if center_seconds is not None:
        return center_seconds

    if start_seconds is None or end_seconds is None:
        return None

    return (start_seconds + end_seconds) / 2.0


def _extract_segments(source: Any) -> list[dict[str, Any]]:
    source_dict = _safe_dict(source)

    segments = source_dict.get("segments")
    if isinstance(segments, list):
        return [dict(item) for item in segments if isinstance(item, dict)]

    report_segments = source_dict.get("segment_classification_segments")
    if isinstance(report_segments, list):
        return [dict(item) for item in report_segments if isinstance(item, dict)]

    nested_result = _safe_dict(source_dict.get("segment_classification_result"))
    nested_segments = nested_result.get("segments")
    if isinstance(nested_segments, list):
        return [dict(item) for item in nested_segments if isinstance(item, dict)]

    nested_report = _safe_dict(source_dict.get("segment_classification_report"))
    nested_report_segments = nested_report.get("segments")
    if isinstance(nested_report_segments, list):
        return [dict(item) for item in nested_report_segments if isinstance(item, dict)]

    return []


def _metadata_for_segment(segment: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_segment_id": str(segment.get("segment_id") or ""),
        "segment_type": str(segment.get("segment_type") or "unknown"),
        "segment_score": _clamp(segment.get("segment_score"), 0.0),
        "content_value_score": _clamp(segment.get("content_value_score"), 0.0),
        "dead_content_score": _clamp(segment.get("dead_content_score"), 0.0),
        "protection_score": _clamp(segment.get("protection_score"), 0.0),
        "technical_risk_score": _clamp(segment.get("technical_risk_score"), 0.0),
        "hook_candidate_score": _clamp(segment.get("hook_candidate_score"), 0.0),
        "censor_required": bool(segment.get("censor_required", False)),
        "is_highlight_candidate": bool(segment.get("is_highlight_candidate", False)),
        "is_hook_candidate": bool(segment.get("is_hook_candidate", False)),
        "is_protected_context": bool(segment.get("is_protected_context", False)),
        "is_dead_candidate": bool(segment.get("is_dead_candidate", False)),
        "is_transition_candidate": bool(segment.get("is_transition_candidate", False)),
        "is_technical_warning": bool(segment.get("is_technical_warning", False)),
        "recommendation": str(segment.get("recommendation") or ""),
        "evidence": _safe_dict(segment.get("evidence")),
        "source_signal_ids": [
            str(item) for item in _safe_list(segment.get("source_signal_ids"))
        ],
        "warnings": [str(item) for item in _safe_list(segment.get("warnings"))],
        "errors": [str(item) for item in _safe_list(segment.get("errors"))],
        "metadata": _safe_dict(segment.get("metadata")),
    }


def _signal_from_segment(
    segment: dict[str, Any],
    mapping: dict[str, str],
    source_index: int,
) -> dict[str, Any]:
    start_seconds = _safe_optional_float(segment.get("start_seconds"))
    end_seconds = _safe_optional_float(segment.get("end_seconds"))
    center_seconds = _derive_center(
        start_seconds,
        end_seconds,
        _safe_optional_float(segment.get("center_seconds")),
    )
    duration_seconds = _derive_duration(
        start_seconds,
        end_seconds,
        _safe_optional_float(segment.get("duration_seconds")),
    )
    segment_score = _clamp(segment.get("segment_score"), 0.0)
    confidence = _clamp(segment.get("confidence"), segment_score)
    segment_id = str(segment.get("segment_id") or f"segment_{source_index}")

    return {
        "signal_id": (
            f"segment_classifier_{source_index}_{mapping['signal_type']}_{segment_id}"
        ),
        "signal_type": mapping["signal_type"],
        "source": SOURCE_SEGMENT_CLASSIFIER,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "center_seconds": center_seconds,
        "duration_seconds": duration_seconds,
        "signal_score": segment_score,
        "priority": mapping["priority"],
        "action_hint": mapping["action_hint"],
        "reason": mapping["reason"],
        "confidence": confidence,
        "metadata": _metadata_for_segment(segment),
    }


@dataclass
class SegmentClassificationSignalAdapterResult:
    status: str
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0
    highlight_signal_count: int = 0
    hook_candidate_signal_count: int = 0
    protected_context_signal_count: int = 0
    dead_candidate_signal_count: int = 0
    censor_required_signal_count: int = 0
    technical_warning_signal_count: int = 0
    transition_signal_count: int = 0
    filler_signal_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review_segment_classification_signals"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "signals": [dict(signal) for signal in self.signals],
            "signal_count": self.signal_count,
            "highlight_signal_count": self.highlight_signal_count,
            "hook_candidate_signal_count": self.hook_candidate_signal_count,
            "protected_context_signal_count": self.protected_context_signal_count,
            "dead_candidate_signal_count": self.dead_candidate_signal_count,
            "censor_required_signal_count": self.censor_required_signal_count,
            "technical_warning_signal_count": self.technical_warning_signal_count,
            "transition_signal_count": self.transition_signal_count,
            "filler_signal_count": self.filler_signal_count,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "SegmentClassificationSignalAdapterResult":
        if not isinstance(data, dict):
            data = {}

        raw_signals = data.get("signals")
        signals = [
            dict(item) for item in raw_signals if isinstance(item, dict)
        ] if isinstance(raw_signals, list) else []

        return cls(
            status=str(data.get("status") or STATUS_FAILED),
            signals=signals,
            signal_count=int(data.get("signal_count", len(signals)) or 0),
            highlight_signal_count=int(data.get("highlight_signal_count", 0) or 0),
            hook_candidate_signal_count=int(
                data.get("hook_candidate_signal_count", 0) or 0
            ),
            protected_context_signal_count=int(
                data.get("protected_context_signal_count", 0) or 0
            ),
            dead_candidate_signal_count=int(
                data.get("dead_candidate_signal_count", 0) or 0
            ),
            censor_required_signal_count=int(
                data.get("censor_required_signal_count", 0) or 0
            ),
            technical_warning_signal_count=int(
                data.get("technical_warning_signal_count", 0) or 0
            ),
            transition_signal_count=int(
                data.get("transition_signal_count", 0) or 0
            ),
            filler_signal_count=int(data.get("filler_signal_count", 0) or 0),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            recommendation=str(
                data.get("recommendation") or "review_segment_classification_signals"
            ),
        )


def adapt_segment_classification_report_to_signals(
    source: Any,
    metadata: dict[str, Any] | None = None,
) -> SegmentClassificationSignalAdapterResult:
    try:
        segments = _extract_segments(source)

        if not segments:
            return SegmentClassificationSignalAdapterResult(
                status=STATUS_SKIPPED_NO_SEGMENT_CLASSIFICATIONS,
                signals=[],
                signal_count=0,
                warnings=["No segment classifications available for signal adapter."],
                recommendation="segment_classification_signals_skipped_no_segments",
            )

        signals: list[dict[str, Any]] = []
        warnings: list[str] = []

        for index, segment in enumerate(segments):
            segment_type = str(segment.get("segment_type") or "unknown")
            mapping = SEGMENT_TYPE_MAPPING.get(segment_type)

            if mapping is None:
                warnings.append(f"Unsupported segment type skipped: {segment_type}")
                continue

            signal = _signal_from_segment(segment, mapping, index)
            signal["metadata"] = {
                **signal["metadata"],
                **dict(metadata or {}),
            }
            signals.append(signal)

        return SegmentClassificationSignalAdapterResult(
            status=STATUS_OK if signals else STATUS_SKIPPED_NO_SEGMENT_CLASSIFICATIONS,
            signals=signals,
            signal_count=len(signals),
            highlight_signal_count=sum(
                1 for signal in signals
                if signal.get("signal_type") == "segment_highlight_candidate"
            ),
            hook_candidate_signal_count=sum(
                1 for signal in signals
                if signal.get("signal_type") == "segment_hook_candidate"
            ),
            protected_context_signal_count=sum(
                1 for signal in signals
                if signal.get("signal_type") == "segment_protected_context"
            ),
            dead_candidate_signal_count=sum(
                1 for signal in signals
                if signal.get("signal_type") == "segment_dead_candidate"
            ),
            censor_required_signal_count=sum(
                1 for signal in signals
                if signal.get("signal_type") == "segment_censor_required"
            ),
            technical_warning_signal_count=sum(
                1 for signal in signals
                if signal.get("signal_type") == "segment_technical_warning"
            ),
            transition_signal_count=sum(
                1 for signal in signals
                if signal.get("signal_type") == "segment_transition_candidate"
            ),
            filler_signal_count=sum(
                1 for signal in signals
                if signal.get("signal_type") == "segment_filler_candidate"
            ),
            warnings=warnings,
            errors=[],
            recommendation=(
                "review_segment_classification_signals"
                if signals
                else "segment_classification_signals_skipped_no_segments"
            ),
        )
    except Exception as exc:
        return SegmentClassificationSignalAdapterResult(
            status=STATUS_FAILED,
            signals=[],
            signal_count=0,
            warnings=[],
            errors=[str(exc)],
            recommendation="segment_classification_signal_adapter_failed",
        )
