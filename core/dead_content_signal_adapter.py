from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_SKIPPED_NO_DEAD_CONTENT_CANDIDATES = "skipped_no_dead_content_candidates"
STATUS_FAILED = "failed"

SOURCE_DEAD_CONTENT = "dead_content"


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


def _extract_candidates(source: Any) -> list[dict[str, Any]]:
    source_dict = _safe_dict(source)
    candidates = source_dict.get("candidates")

    if not isinstance(candidates, list):
        result_dict = _safe_dict(source_dict.get("dead_content_result"))
        candidates = result_dict.get("candidates")

    if not isinstance(candidates, list):
        candidates = source_dict.get("dead_content_candidates")

    if not isinstance(candidates, list):
        candidates = getattr(source, "candidates", [])

    return [
        dict(item) for item in candidates if isinstance(item, dict)
    ] if isinstance(candidates, list) else []


def _extract_segment_scores(source: Any) -> list[dict[str, Any]]:
    source_dict = _safe_dict(source)
    segment_scores = source_dict.get("segment_scores")

    if not isinstance(segment_scores, list):
        result_dict = _safe_dict(source_dict.get("dead_content_result"))
        segment_scores = result_dict.get("segment_scores")

    if not isinstance(segment_scores, list):
        segment_scores = source_dict.get("dead_content_segment_scores")

    if not isinstance(segment_scores, list):
        segment_scores = getattr(source, "segment_scores", [])

    return [
        dict(item) for item in segment_scores if isinstance(item, dict)
    ] if isinstance(segment_scores, list) else []


def _candidate_from_segment_score(score: dict[str, Any], index: int) -> dict[str, Any]:
    start_seconds = _safe_optional_float(score.get("start_seconds"))
    end_seconds = _safe_optional_float(score.get("end_seconds"))
    duration_seconds = _derive_duration(
        start_seconds,
        end_seconds,
        _safe_optional_float(score.get("duration_seconds")),
    )
    return {
        "candidate_id": f"dead_content_segment_score_{index}",
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "center_seconds": _derive_center(start_seconds, end_seconds),
        "duration_seconds": duration_seconds,
        "text": str(score.get("text") or ""),
        "candidate_type": str(score.get("candidate_type") or "unknown"),
        "dead_content_score": _clamp(score.get("dead_content_score"), 0.0),
        "confidence": _clamp(score.get("dead_content_score"), 0.0),
        "protected_by_context": bool(score.get("protected_by_context")),
        "protection_reasons": _safe_list(
            _safe_dict(score.get("evidence")).get("protection_reasons")
        ),
        "evidence": _safe_dict(score.get("evidence")),
        "recommendation": str(score.get("recommendation") or ""),
        "metadata": _safe_dict(score.get("metadata")),
        "warnings": _safe_list(score.get("warnings")),
        "errors": _safe_list(score.get("errors")),
    }


def _mapping_for_candidate_type(candidate_type: str) -> dict[str, str] | None:
    if candidate_type == "dead_air_candidate":
        return {
            "signal_type": "dead_content_dead_air_candidate",
            "action_hint": "review_dead_air_candidate",
            "priority": "high",
            "reason": "dead_air_candidate_detected",
        }
    if candidate_type == "low_value_content_candidate":
        return {
            "signal_type": "dead_content_low_value_candidate",
            "action_hint": "review_low_value_content_candidate",
            "priority": "medium",
            "reason": "low_value_content_candidate_detected",
        }
    if candidate_type == "filler_pause_candidate":
        return {
            "signal_type": "dead_content_filler_pause_candidate",
            "action_hint": "review_filler_pause_candidate",
            "priority": "medium",
            "reason": "filler_pause_candidate_detected",
        }
    if candidate_type == "loading_or_menu_candidate":
        return {
            "signal_type": "dead_content_loading_or_menu_candidate",
            "action_hint": "review_loading_or_menu_candidate",
            "priority": "medium",
            "reason": "loading_or_menu_candidate_detected",
        }
    if candidate_type == "private_or_meta_review_candidate":
        return {
            "signal_type": "dead_content_private_or_meta_review_candidate",
            "action_hint": "review_private_or_meta_candidate",
            "priority": "high",
            "reason": "private_or_meta_candidate_detected",
        }
    if candidate_type == "protected_context_candidate":
        return {
            "signal_type": "dead_content_protected_context_candidate",
            "action_hint": "protect_context_from_dead_content_cut",
            "priority": "high",
            "reason": "protected_context_candidate_detected",
        }
    return None


def _metadata_for_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    evidence = _safe_dict(candidate.get("evidence"))
    metadata = _safe_dict(candidate.get("metadata"))
    return {
        "candidate_type": str(candidate.get("candidate_type") or "unknown"),
        "dead_content_score": _clamp(candidate.get("dead_content_score"), 0.0),
        "content_value_score": _clamp(metadata.get("content_value_score"), 0.0),
        "protected_by_context": bool(candidate.get("protected_by_context")),
        "protection_reasons": [
            str(item) for item in _safe_list(candidate.get("protection_reasons"))
        ],
        "evidence": evidence,
        "recommendation": str(candidate.get("recommendation") or ""),
        "source_candidate_id": str(candidate.get("candidate_id") or ""),
        "warnings": [str(item) for item in _safe_list(candidate.get("warnings"))],
        "errors": [str(item) for item in _safe_list(candidate.get("errors"))],
    }


def _signal_from_candidate(
    candidate: dict[str, Any],
    mapping: dict[str, str],
    source_index: int,
    suffix: str = "",
) -> dict[str, Any]:
    start_seconds = _safe_optional_float(candidate.get("start_seconds"))
    end_seconds = _safe_optional_float(candidate.get("end_seconds"))
    center_seconds = _derive_center(
        start_seconds,
        end_seconds,
        _safe_optional_float(candidate.get("center_seconds")),
    )
    duration_seconds = _derive_duration(
        start_seconds,
        end_seconds,
        _safe_optional_float(candidate.get("duration_seconds")),
    )
    dead_content_score = _clamp(candidate.get("dead_content_score"), 0.0)
    confidence = _clamp(candidate.get("confidence"), dead_content_score)
    candidate_id = str(candidate.get("candidate_id") or f"candidate_{source_index}")

    return {
        "signal_id": (
            f"dead_content_{source_index}_{mapping['signal_type']}_"
            f"{candidate_id}{suffix}"
        ),
        "signal_type": mapping["signal_type"],
        "source": SOURCE_DEAD_CONTENT,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "center_seconds": center_seconds,
        "duration_seconds": duration_seconds,
        "signal_score": dead_content_score,
        "priority": mapping["priority"],
        "action_hint": mapping["action_hint"],
        "reason": mapping["reason"],
        "confidence": confidence,
        "metadata": _metadata_for_candidate(candidate),
    }


@dataclass
class DeadContentSignalAdapterResult:
    status: str
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0
    dead_air_signal_count: int = 0
    low_value_signal_count: int = 0
    filler_pause_signal_count: int = 0
    loading_or_menu_signal_count: int = 0
    private_or_meta_signal_count: int = 0
    protected_context_signal_count: int = 0
    high_score_signal_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review_dead_content_signals"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "signals": [dict(signal) for signal in self.signals],
            "signal_count": self.signal_count,
            "dead_air_signal_count": self.dead_air_signal_count,
            "low_value_signal_count": self.low_value_signal_count,
            "filler_pause_signal_count": self.filler_pause_signal_count,
            "loading_or_menu_signal_count": self.loading_or_menu_signal_count,
            "private_or_meta_signal_count": self.private_or_meta_signal_count,
            "protected_context_signal_count": self.protected_context_signal_count,
            "high_score_signal_count": self.high_score_signal_count,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "DeadContentSignalAdapterResult":
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
            dead_air_signal_count=int(data.get("dead_air_signal_count", 0) or 0),
            low_value_signal_count=int(data.get("low_value_signal_count", 0) or 0),
            filler_pause_signal_count=int(
                data.get("filler_pause_signal_count", 0) or 0
            ),
            loading_or_menu_signal_count=int(
                data.get("loading_or_menu_signal_count", 0) or 0
            ),
            private_or_meta_signal_count=int(
                data.get("private_or_meta_signal_count", 0) or 0
            ),
            protected_context_signal_count=int(
                data.get("protected_context_signal_count", 0) or 0
            ),
            high_score_signal_count=int(
                data.get("high_score_signal_count", 0) or 0
            ),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
            recommendation=str(
                data.get("recommendation") or "review_dead_content_signals"
            ),
        )


def adapt_dead_content_report_to_signals(
    dead_content_report: Any,
) -> DeadContentSignalAdapterResult:
    try:
        warnings: list[str] = []
        errors: list[str] = []
        candidates = _extract_candidates(dead_content_report)
        if not candidates:
            segment_scores = _extract_segment_scores(dead_content_report)
            candidates = [
                _candidate_from_segment_score(score, index)
                for index, score in enumerate(segment_scores)
                if bool(score.get("review_required"))
            ]

        if not candidates:
            return DeadContentSignalAdapterResult(
                status=STATUS_SKIPPED_NO_DEAD_CONTENT_CANDIDATES,
                signals=[],
                signal_count=0,
                warnings=["no_dead_content_candidates_available"],
                errors=[],
                recommendation="no_dead_content_candidates_available",
            )

        signals: list[dict[str, Any]] = []
        for index, candidate in enumerate(candidates):
            if not candidate:
                warnings.append(f"invalid_dead_content_candidate_skipped:{index}")
                continue

            candidate_type = str(candidate.get("candidate_type") or "unknown")
            mapping = _mapping_for_candidate_type(candidate_type)
            if mapping is None:
                warnings.append(f"unsupported_dead_content_candidate_skipped:{index}")
            else:
                signals.append(_signal_from_candidate(candidate, mapping, index))

            if _clamp(candidate.get("dead_content_score"), 0.0) >= 0.85:
                signals.append(
                    _signal_from_candidate(
                        candidate,
                        {
                            "signal_type": "dead_content_high_score_candidate",
                            "action_hint": "review_high_dead_content_score",
                            "priority": "high",
                            "reason": "high_dead_content_score_detected",
                        },
                        index,
                        suffix="_high_score",
                    )
                )

        if not signals:
            return DeadContentSignalAdapterResult(
                status=STATUS_SKIPPED_NO_DEAD_CONTENT_CANDIDATES,
                signals=[],
                signal_count=0,
                warnings=warnings + ["no_dead_content_signals_produced"],
                errors=errors,
                recommendation="no_dead_content_signals_available",
            )

        type_counts: dict[str, int] = {}
        for signal in signals:
            signal_type = str(signal.get("signal_type") or "")
            type_counts[signal_type] = type_counts.get(signal_type, 0) + 1

        status = STATUS_COMPLETED_WITH_WARNINGS if warnings or errors else STATUS_OK
        return DeadContentSignalAdapterResult(
            status=status,
            signals=signals,
            signal_count=len(signals),
            dead_air_signal_count=type_counts.get(
                "dead_content_dead_air_candidate",
                0,
            ),
            low_value_signal_count=type_counts.get(
                "dead_content_low_value_candidate",
                0,
            ),
            filler_pause_signal_count=type_counts.get(
                "dead_content_filler_pause_candidate",
                0,
            ),
            loading_or_menu_signal_count=type_counts.get(
                "dead_content_loading_or_menu_candidate",
                0,
            ),
            private_or_meta_signal_count=type_counts.get(
                "dead_content_private_or_meta_review_candidate",
                0,
            ),
            protected_context_signal_count=type_counts.get(
                "dead_content_protected_context_candidate",
                0,
            ),
            high_score_signal_count=type_counts.get(
                "dead_content_high_score_candidate",
                0,
            ),
            warnings=warnings,
            errors=errors,
            recommendation="use_dead_content_review_signals",
        )
    except Exception as exc:
        return DeadContentSignalAdapterResult(
            status=STATUS_FAILED,
            signals=[],
            signal_count=0,
            warnings=[],
            errors=[f"dead_content_signal_adapter_failed:{exc}"],
            recommendation="review_dead_content_signal_adapter_error",
        )
