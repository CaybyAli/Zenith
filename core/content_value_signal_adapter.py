from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_SKIPPED_NO_CONTENT_VALUE_SEGMENTS = "skipped_no_content_value_segments"
STATUS_FAILED = "failed"

SOURCE_CONTENT_VALUE = "content_value"


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


def _extract_segment_scores(source: Any) -> list[dict[str, Any]]:
    source_dict = _safe_dict(source)
    segment_scores = source_dict.get("segment_scores")

    if not isinstance(segment_scores, list):
        result_dict = _safe_dict(source_dict.get("content_value_result"))
        segment_scores = result_dict.get("segment_scores")

    if not isinstance(segment_scores, list):
        segment_scores = source_dict.get("content_value_segment_scores")

    if not isinstance(segment_scores, list):
        segment_scores = getattr(source, "segment_scores", [])

    return [
        dict(item) for item in segment_scores if isinstance(item, dict)
    ] if isinstance(segment_scores, list) else []


def _mapping_for_tier(value_tier: str) -> dict[str, str] | None:
    if value_tier == "high":
        return {
            "signal_type": "content_value_high_segment",
            "action_hint": "review_high_value_segment",
            "priority": "high",
            "reason": "high_content_value_detected",
        }
    if value_tier == "medium":
        return {
            "signal_type": "content_value_mid_segment",
            "action_hint": "review_mid_value_segment",
            "priority": "medium",
            "reason": "mid_content_value_detected",
        }
    if value_tier == "low":
        return {
            "signal_type": "content_value_low_segment",
            "action_hint": "review_low_value_segment",
            "priority": "medium",
            "reason": "low_content_value_detected",
        }
    if value_tier == "protected":
        return {
            "signal_type": "content_value_protected_context",
            "action_hint": "protect_context_from_blind_cut",
            "priority": "high",
            "reason": "protected_context_detected",
        }
    if value_tier == "technical_warning":
        return {
            "signal_type": "content_value_technical_warning",
            "action_hint": "review_technical_warning",
            "priority": "high",
            "reason": "technical_warning_detected",
        }
    return None


def _hook_mapping() -> dict[str, str]:
    return {
        "signal_type": "content_value_hook_candidate",
        "action_hint": "review_hook_candidate",
        "priority": "high",
        "reason": "hook_candidate_detected",
    }


def _metadata_for_score(score: dict[str, Any]) -> dict[str, Any]:
    return {
        "value_tier": str(score.get("value_tier") or "unknown"),
        "review_label": str(score.get("review_label") or ""),
        "content_value_score": _clamp(score.get("content_value_score"), 0.0),
        "final_score": _clamp(score.get("final_score"), 0.0),
        "protection_score": _clamp(score.get("protection_score"), 0.0),
        "dead_content_penalty_score": _clamp(
            score.get("dead_content_penalty_score"),
            0.0,
        ),
        "technical_penalty_score": _clamp(
            score.get("technical_penalty_score"),
            0.0,
        ),
        "is_hook_candidate": bool(score.get("is_hook_candidate")),
        "is_protected_context": bool(score.get("is_protected_context")),
        "evidence": _safe_dict(score.get("evidence")),
        "recommendation": str(score.get("recommendation") or ""),
        "source_segment_id": str(score.get("segment_id") or ""),
        "warnings": [str(item) for item in _safe_list(score.get("warnings"))],
        "errors": [str(item) for item in _safe_list(score.get("errors"))],
    }


def _signal_from_score(
    score: dict[str, Any],
    mapping: dict[str, str],
    source_index: int,
    suffix: str = "",
) -> dict[str, Any]:
    start_seconds = _safe_optional_float(score.get("start_seconds"))
    end_seconds = _safe_optional_float(score.get("end_seconds"))
    center_seconds = _derive_center(
        start_seconds,
        end_seconds,
        _safe_optional_float(score.get("center_seconds")),
    )
    duration_seconds = _derive_duration(
        start_seconds,
        end_seconds,
        _safe_optional_float(score.get("duration_seconds")),
    )
    final_score = _clamp(score.get("final_score"), 0.0)
    segment_id = str(score.get("segment_id") or f"segment_{source_index}")

    return {
        "signal_id": (
            f"content_value_{source_index}_{mapping['signal_type']}_"
            f"{segment_id}{suffix}"
        ),
        "signal_type": mapping["signal_type"],
        "source": SOURCE_CONTENT_VALUE,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "center_seconds": center_seconds,
        "duration_seconds": duration_seconds,
        "signal_score": final_score,
        "priority": mapping["priority"],
        "action_hint": mapping["action_hint"],
        "reason": mapping["reason"],
        "confidence": final_score,
        "metadata": _metadata_for_score(score),
    }


@dataclass
class ContentValueSignalAdapterResult:
    status: str
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0
    high_value_signal_count: int = 0
    mid_value_signal_count: int = 0
    low_value_signal_count: int = 0
    protected_context_signal_count: int = 0
    hook_candidate_signal_count: int = 0
    technical_warning_signal_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review_content_value_signals"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "signals": [dict(signal) for signal in self.signals],
            "signal_count": self.signal_count,
            "high_value_signal_count": self.high_value_signal_count,
            "mid_value_signal_count": self.mid_value_signal_count,
            "low_value_signal_count": self.low_value_signal_count,
            "protected_context_signal_count": self.protected_context_signal_count,
            "hook_candidate_signal_count": self.hook_candidate_signal_count,
            "technical_warning_signal_count": self.technical_warning_signal_count,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "ContentValueSignalAdapterResult":
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
            high_value_signal_count=int(
                data.get("high_value_signal_count", 0) or 0
            ),
            mid_value_signal_count=int(data.get("mid_value_signal_count", 0) or 0),
            low_value_signal_count=int(data.get("low_value_signal_count", 0) or 0),
            protected_context_signal_count=int(
                data.get("protected_context_signal_count", 0) or 0
            ),
            hook_candidate_signal_count=int(
                data.get("hook_candidate_signal_count", 0) or 0
            ),
            technical_warning_signal_count=int(
                data.get("technical_warning_signal_count", 0) or 0
            ),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
            recommendation=str(
                data.get("recommendation") or "review_content_value_signals"
            ),
        )


def adapt_content_value_report_to_signals(
    content_value_report: Any,
) -> ContentValueSignalAdapterResult:
    try:
        warnings: list[str] = []
        errors: list[str] = []
        segment_scores = _extract_segment_scores(content_value_report)
        if not segment_scores:
            return ContentValueSignalAdapterResult(
                status=STATUS_SKIPPED_NO_CONTENT_VALUE_SEGMENTS,
                signals=[],
                signal_count=0,
                warnings=["no_content_value_segments_available"],
                errors=[],
                recommendation="no_content_value_segments_available",
            )

        signals: list[dict[str, Any]] = []
        for index, score in enumerate(segment_scores):
            if not score:
                warnings.append(f"invalid_content_value_segment_skipped:{index}")
                continue

            mapping = _mapping_for_tier(str(score.get("value_tier") or "unknown"))
            if mapping is None:
                warnings.append(f"unsupported_content_value_tier_skipped:{index}")
            else:
                signals.append(_signal_from_score(score, mapping, index))

            if bool(score.get("is_hook_candidate")):
                signals.append(
                    _signal_from_score(
                        score,
                        _hook_mapping(),
                        index,
                        suffix="_hook_candidate",
                    )
                )

        if not signals:
            return ContentValueSignalAdapterResult(
                status=STATUS_SKIPPED_NO_CONTENT_VALUE_SEGMENTS,
                signals=[],
                signal_count=0,
                warnings=warnings + ["no_content_value_signals_produced"],
                errors=errors,
                recommendation="no_content_value_signals_available",
            )

        type_counts: dict[str, int] = {}
        for signal in signals:
            signal_type = str(signal.get("signal_type") or "")
            type_counts[signal_type] = type_counts.get(signal_type, 0) + 1

        status = STATUS_COMPLETED_WITH_WARNINGS if warnings or errors else STATUS_OK
        return ContentValueSignalAdapterResult(
            status=status,
            signals=signals,
            signal_count=len(signals),
            high_value_signal_count=type_counts.get(
                "content_value_high_segment",
                0,
            ),
            mid_value_signal_count=type_counts.get("content_value_mid_segment", 0),
            low_value_signal_count=type_counts.get("content_value_low_segment", 0),
            protected_context_signal_count=type_counts.get(
                "content_value_protected_context",
                0,
            ),
            hook_candidate_signal_count=type_counts.get(
                "content_value_hook_candidate",
                0,
            ),
            technical_warning_signal_count=type_counts.get(
                "content_value_technical_warning",
                0,
            ),
            warnings=warnings,
            errors=errors,
            recommendation="use_content_value_review_signals",
        )
    except Exception as exc:
        return ContentValueSignalAdapterResult(
            status=STATUS_FAILED,
            signals=[],
            signal_count=0,
            warnings=[],
            errors=[f"content_value_signal_adapter_failed:{exc}"],
            recommendation="review_content_value_signal_adapter_error",
        )
