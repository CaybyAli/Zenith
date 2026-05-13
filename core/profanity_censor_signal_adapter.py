from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_SKIPPED_NO_CENSOR_REQUIRED_MATCHES = "skipped_no_censor_required_matches"
STATUS_FAILED = "failed"

SOURCE_PROFANITY_CENSOR = "profanity_censor"

SIGNAL_TYPE_SFX_REQUIRED = "profanity_censor_sfx_required"
SIGNAL_TYPE_WORD_TIMED = "profanity_censor_word_timed_overlay"
SIGNAL_TYPE_SEGMENT_FALLBACK = "profanity_censor_segment_fallback_overlay"

ACTION_REVIEW_CENSOR_SFX = "review_censor_sfx_overlay"
ACTION_REVIEW_WORD_TIMED = "review_word_timed_censor_sfx_overlay"
ACTION_REVIEW_SEGMENT_FALLBACK = "review_segment_fallback_censor_sfx_overlay"


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


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(value)
    except (TypeError, ValueError):
        return default


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


def _extract_matches(source: Any) -> list[dict[str, Any]]:
    source_dict = _safe_dict(source)
    matches = source_dict.get("matches")

    if not isinstance(matches, list):
        result_dict = _safe_dict(source_dict.get("profanity_censor_result"))
        matches = result_dict.get("matches")

    if not isinstance(matches, list):
        matches = getattr(source, "matches", [])

    return [
        dict(item) for item in matches if isinstance(item, dict)
    ] if isinstance(matches, list) else []


def _metadata_for_match(match: dict[str, Any]) -> dict[str, Any]:
    return {
        "severity": str(match.get("severity") or "unknown"),
        "category": str(match.get("category") or "unknown"),
        "matched_text": str(match.get("matched_text") or ""),
        "normalized_match": str(match.get("normalized_match") or ""),
        "replacement_sfx": match.get("replacement_sfx"),
        "censor_required": bool(match.get("censor_required")),
        "censor_action": str(match.get("censor_action") or "none"),
        "timing_source": str(match.get("timing_source") or "unknown"),
        "source_match_id": str(match.get("match_id") or ""),
        "warnings": [str(item) for item in _safe_list(match.get("warnings"))],
        "errors": [str(item) for item in _safe_list(match.get("errors"))],
    }


def _signal_from_match(
    match: dict[str, Any],
    mapping: dict[str, str],
    source_index: int,
    suffix: str = "",
) -> dict[str, Any]:
    start_seconds = _safe_optional_float(match.get("start_seconds"))
    end_seconds = _safe_optional_float(match.get("end_seconds"))
    center_seconds = _derive_center(
        start_seconds,
        end_seconds,
        _safe_optional_float(match.get("center_seconds")),
    )
    duration_seconds = _derive_duration(
        start_seconds,
        end_seconds,
        _safe_optional_float(match.get("duration_seconds")),
    )
    confidence = _clamp(match.get("confidence"), 0.85)
    match_id = str(match.get("match_id") or f"match_{source_index}")

    return {
        "signal_id": (
            f"profanity_censor_{source_index}_{mapping['signal_type']}_"
            f"{match_id}{suffix}"
        ),
        "signal_type": mapping["signal_type"],
        "source": SOURCE_PROFANITY_CENSOR,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "center_seconds": center_seconds,
        "duration_seconds": duration_seconds,
        "signal_score": confidence,
        "priority": mapping["priority"],
        "action_hint": mapping["action_hint"],
        "reason": mapping["reason"],
        "confidence": confidence,
        "metadata": _metadata_for_match(match),
    }


def _required_mapping() -> dict[str, str]:
    return {
        "signal_type": SIGNAL_TYPE_SFX_REQUIRED,
        "action_hint": ACTION_REVIEW_CENSOR_SFX,
        "priority": "high",
        "reason": "severe_profanity_censor_sfx_required",
    }


def _word_timed_mapping() -> dict[str, str]:
    return {
        "signal_type": SIGNAL_TYPE_WORD_TIMED,
        "action_hint": ACTION_REVIEW_WORD_TIMED,
        "priority": "high",
        "reason": "word_level_profanity_timing_available",
    }


def _segment_fallback_mapping() -> dict[str, str]:
    return {
        "signal_type": SIGNAL_TYPE_SEGMENT_FALLBACK,
        "action_hint": ACTION_REVIEW_SEGMENT_FALLBACK,
        "priority": "medium",
        "reason": "segment_fallback_profanity_timing_used",
    }


@dataclass
class ProfanityCensorSignalAdapterResult:
    status: str
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0
    censor_required_signal_count: int = 0
    word_timed_signal_count: int = 0
    segment_fallback_signal_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review_profanity_censor_signals"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "signals": [dict(signal) for signal in self.signals],
            "signal_count": self.signal_count,
            "censor_required_signal_count": self.censor_required_signal_count,
            "word_timed_signal_count": self.word_timed_signal_count,
            "segment_fallback_signal_count": self.segment_fallback_signal_count,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "ProfanityCensorSignalAdapterResult":
        if not isinstance(data, dict):
            data = {}
        raw_signals = data.get("signals")
        signals = [
            dict(item) for item in raw_signals if isinstance(item, dict)
        ] if isinstance(raw_signals, list) else []
        return cls(
            status=str(data.get("status") or STATUS_FAILED),
            signals=signals,
            signal_count=_safe_int(data.get("signal_count"), len(signals)),
            censor_required_signal_count=_safe_int(
                data.get("censor_required_signal_count"),
                0,
            ),
            word_timed_signal_count=_safe_int(
                data.get("word_timed_signal_count"),
                0,
            ),
            segment_fallback_signal_count=_safe_int(
                data.get("segment_fallback_signal_count"),
                0,
            ),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
            recommendation=str(
                data.get("recommendation")
                or "review_profanity_censor_signals"
            ),
        )


def adapt_profanity_censor_report_to_signals(
    profanity_censor_report: Any,
) -> ProfanityCensorSignalAdapterResult:
    try:
        warnings: list[str] = []
        errors: list[str] = []
        matches = _extract_matches(profanity_censor_report)
        if not matches:
            return ProfanityCensorSignalAdapterResult(
                status=STATUS_SKIPPED_NO_CENSOR_REQUIRED_MATCHES,
                signals=[],
                signal_count=0,
                warnings=["no_profanity_censor_matches_available"],
                errors=[],
                recommendation="no_censor_sfx_signals_available",
            )

        signals: list[dict[str, Any]] = []
        for index, match in enumerate(matches):
            if not match:
                warnings.append(f"invalid_profanity_censor_match_skipped:{index}")
                continue

            if not bool(match.get("censor_required")):
                continue

            if str(match.get("severity") or "").lower() != "severe":
                continue

            signals.append(_signal_from_match(match, _required_mapping(), index))

            timing_source = str(match.get("timing_source") or "").lower()
            if timing_source == "word_timestamp":
                signals.append(
                    _signal_from_match(
                        match,
                        _word_timed_mapping(),
                        index,
                        suffix="_word_timed",
                    )
                )
            elif timing_source == "segment_fallback":
                signals.append(
                    _signal_from_match(
                        match,
                        _segment_fallback_mapping(),
                        index,
                        suffix="_segment_fallback",
                    )
                )
            else:
                warnings.append(
                    f"unknown_profanity_censor_timing_source:{index}"
                )

        if not signals:
            return ProfanityCensorSignalAdapterResult(
                status=STATUS_SKIPPED_NO_CENSOR_REQUIRED_MATCHES,
                signals=[],
                signal_count=0,
                warnings=warnings + ["no_censor_required_matches_available"],
                errors=errors,
                recommendation="no_censor_sfx_signals_available",
            )

        type_counts: dict[str, int] = {}
        for signal in signals:
            signal_type = str(signal.get("signal_type") or "")
            type_counts[signal_type] = type_counts.get(signal_type, 0) + 1

        status = STATUS_COMPLETED_WITH_WARNINGS if warnings or errors else STATUS_OK
        return ProfanityCensorSignalAdapterResult(
            status=status,
            signals=signals,
            signal_count=len(signals),
            censor_required_signal_count=type_counts.get(
                SIGNAL_TYPE_SFX_REQUIRED,
                0,
            ),
            word_timed_signal_count=type_counts.get(SIGNAL_TYPE_WORD_TIMED, 0),
            segment_fallback_signal_count=type_counts.get(
                SIGNAL_TYPE_SEGMENT_FALLBACK,
                0,
            ),
            warnings=warnings,
            errors=errors,
            recommendation="use_profanity_censor_review_signals",
        )
    except Exception as exc:
        return ProfanityCensorSignalAdapterResult(
            status=STATUS_FAILED,
            signals=[],
            signal_count=0,
            warnings=[],
            errors=[f"profanity_censor_signal_adapter_failed:{exc}"],
            recommendation="review_profanity_censor_signal_adapter_error",
        )
