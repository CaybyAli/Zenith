from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_SKIPPED_NO_MURCH_SCORES = "skipped_no_murch_scores"
STATUS_FAILED = "failed"

SOURCE_MURCH_SCORING = "murch_scoring"

TIER_MAPPING = {
    "high": {
        "signal_type": "murch_high_score_segment",
        "action_hint": "review_high_murch_score_segment",
        "priority": "high",
        "reason": "murch_scoring_high_score",
    },
    "medium": {
        "signal_type": "murch_medium_score_segment",
        "action_hint": "review_medium_murch_score_segment",
        "priority": "medium",
        "reason": "murch_scoring_medium_score",
    },
    "low": {
        "signal_type": "murch_low_score_segment",
        "action_hint": "review_low_murch_score_segment",
        "priority": "medium",
        "reason": "murch_scoring_low_score",
    },
    "protected": {
        "signal_type": "murch_protected_context",
        "action_hint": "protect_murch_context",
        "priority": "high",
        "reason": "murch_scoring_protected_context",
    },
    "technical_warning": {
        "signal_type": "murch_technical_warning",
        "action_hint": "review_murch_technical_warning",
        "priority": "high",
        "reason": "murch_scoring_technical_warning",
    },
}

CENSOR_MAPPING = {
    "signal_type": "murch_censor_required_context",
    "action_hint": "preserve_murch_segment_with_censor_sfx_review",
    "priority": "high",
    "reason": "murch_scoring_censor_required",
}

EMOTION_HIGH_MAPPING = {
    "signal_type": "murch_emotion_high",
    "action_hint": "review_high_emotion_segment",
    "priority": "high",
    "reason": "murch_scoring_emotion_high",
}

STORY_HIGH_MAPPING = {
    "signal_type": "murch_story_high",
    "action_hint": "review_high_story_segment",
    "priority": "high",
    "reason": "murch_scoring_story_high",
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


def _extract_segment_scores(source: Any) -> list[dict[str, Any]]:
    source_dict = _safe_dict(source)

    direct_scores = source_dict.get("segment_scores")
    if isinstance(direct_scores, list):
        return [dict(item) for item in direct_scores if isinstance(item, dict)]

    job_scores = source_dict.get("murch_scoring_segment_scores")
    if isinstance(job_scores, list):
        return [dict(item) for item in job_scores if isinstance(item, dict)]

    nested_result = _safe_dict(source_dict.get("murch_scoring_result"))
    nested_scores = nested_result.get("segment_scores")
    if isinstance(nested_scores, list):
        return [dict(item) for item in nested_scores if isinstance(item, dict)]

    nested_report = _safe_dict(source_dict.get("murch_scoring_report"))
    nested_report_scores = nested_report.get("segment_scores")
    if isinstance(nested_report_scores, list):
        return [dict(item) for item in nested_report_scores if isinstance(item, dict)]

    nested_report_result = _safe_dict(nested_report.get("murch_scoring_result"))
    nested_report_result_scores = nested_report_result.get("segment_scores")
    if isinstance(nested_report_result_scores, list):
        return [
            dict(item)
            for item in nested_report_result_scores
            if isinstance(item, dict)
        ]

    return []


def _metadata_for_score(segment_score: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_segment_id": str(
            segment_score.get("source_segment_id")
            or segment_score.get("segment_id")
            or ""
        ),
        "segment_type": str(segment_score.get("segment_type") or "unknown"),
        "murch_score": _clamp(segment_score.get("murch_score"), 0.0),
        "murch_tier": str(segment_score.get("murch_tier") or "unknown"),
        "emotion_score": _clamp(segment_score.get("emotion_score"), 0.0),
        "story_score": _clamp(segment_score.get("story_score"), 0.0),
        "rhythm_score": _clamp(segment_score.get("rhythm_score"), 0.0),
        "eye_trace_score": _clamp(segment_score.get("eye_trace_score"), 0.0),
        "screen_direction_score": _clamp(
            segment_score.get("screen_direction_score"),
            0.0,
        ),
        "spatial_continuity_score": _clamp(
            segment_score.get("spatial_continuity_score"),
            0.0,
        ),
        "protection_score": _clamp(segment_score.get("protection_score"), 0.0),
        "risk_score": _clamp(segment_score.get("risk_score"), 0.0),
        "dead_content_risk_score": _clamp(
            segment_score.get("dead_content_risk_score"),
            0.0,
        ),
        "technical_risk_score": _clamp(
            segment_score.get("technical_risk_score"),
            0.0,
        ),
        "censor_required": bool(segment_score.get("censor_required", False)),
        "is_protected_context": bool(
            segment_score.get("is_protected_context", False)
        ),
        "is_censor_required": bool(
            segment_score.get("is_censor_required", False)
        ),
        "recommendation": str(segment_score.get("recommendation") or ""),
        "evidence": _safe_dict(segment_score.get("evidence")),
        "source_signal_ids": [
            str(item) for item in _safe_list(segment_score.get("source_signal_ids"))
        ],
        "warnings": [str(item) for item in _safe_list(segment_score.get("warnings"))],
        "errors": [str(item) for item in _safe_list(segment_score.get("errors"))],
        "metadata": _safe_dict(segment_score.get("metadata")),
    }


def _signal_from_score(
    segment_score: dict[str, Any],
    mapping: dict[str, str],
    source_index: int,
    suffix: str,
) -> dict[str, Any]:
    action_hint = mapping["action_hint"]

    start_seconds = _safe_optional_float(segment_score.get("start_seconds"))
    end_seconds = _safe_optional_float(segment_score.get("end_seconds"))
    center_seconds = _derive_center(
        start_seconds,
        end_seconds,
        _safe_optional_float(segment_score.get("center_seconds")),
    )
    duration_seconds = _derive_duration(
        start_seconds,
        end_seconds,
        _safe_optional_float(segment_score.get("duration_seconds")),
    )

    segment_id = str(segment_score.get("segment_id") or f"murch_segment_{source_index}")
    murch_score = _clamp(segment_score.get("murch_score"), 0.0)

    return {
        "signal_id": (
            f"murch_scoring_{source_index}_{mapping['signal_type']}_{suffix}_{segment_id}"
        ),
        "signal_type": mapping["signal_type"],
        "source": SOURCE_MURCH_SCORING,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "center_seconds": center_seconds,
        "duration_seconds": duration_seconds,
        "signal_score": murch_score,
        "priority": mapping["priority"],
        "action_hint": action_hint,
        "reason": mapping["reason"],
        "confidence": murch_score,
        "metadata": _metadata_for_score(segment_score),
    }


@dataclass
class MurchScoringSignalAdapterResult:
    status: str
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0
    high_score_signal_count: int = 0
    medium_score_signal_count: int = 0
    low_score_signal_count: int = 0
    protected_context_signal_count: int = 0
    technical_warning_signal_count: int = 0
    censor_required_signal_count: int = 0
    emotion_high_signal_count: int = 0
    story_high_signal_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review_murch_scoring_signals"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "signals": [dict(signal) for signal in self.signals],
            "signal_count": self.signal_count,
            "high_score_signal_count": self.high_score_signal_count,
            "medium_score_signal_count": self.medium_score_signal_count,
            "low_score_signal_count": self.low_score_signal_count,
            "protected_context_signal_count": self.protected_context_signal_count,
            "technical_warning_signal_count": self.technical_warning_signal_count,
            "censor_required_signal_count": self.censor_required_signal_count,
            "emotion_high_signal_count": self.emotion_high_signal_count,
            "story_high_signal_count": self.story_high_signal_count,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "MurchScoringSignalAdapterResult":
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
            high_score_signal_count=int(
                data.get("high_score_signal_count", 0) or 0
            ),
            medium_score_signal_count=int(
                data.get("medium_score_signal_count", 0) or 0
            ),
            low_score_signal_count=int(
                data.get("low_score_signal_count", 0) or 0
            ),
            protected_context_signal_count=int(
                data.get("protected_context_signal_count", 0) or 0
            ),
            technical_warning_signal_count=int(
                data.get("technical_warning_signal_count", 0) or 0
            ),
            censor_required_signal_count=int(
                data.get("censor_required_signal_count", 0) or 0
            ),
            emotion_high_signal_count=int(
                data.get("emotion_high_signal_count", 0) or 0
            ),
            story_high_signal_count=int(
                data.get("story_high_signal_count", 0) or 0
            ),
            warnings=list(data.get("warnings") or []),
            errors=list(data.get("errors") or []),
            recommendation=str(
                data.get("recommendation") or "review_murch_scoring_signals"
            ),
        )


def adapt_murch_scoring_report_to_signals(
    source: Any,
    metadata: dict[str, Any] | None = None,
) -> MurchScoringSignalAdapterResult:
    try:
        segment_scores = _extract_segment_scores(source)

        if not segment_scores:
            return MurchScoringSignalAdapterResult(
                status=STATUS_SKIPPED_NO_MURCH_SCORES,
                signals=[],
                signal_count=0,
                warnings=["No Murch segment scores available for signal adapter."],
                recommendation="murch_scoring_signals_skipped_no_scores",
            )

        signals: list[dict[str, Any]] = []
        warnings: list[str] = []

        for index, segment_score in enumerate(segment_scores):
            tier = str(segment_score.get("murch_tier") or "unknown")
            mapping = TIER_MAPPING.get(tier)

            if mapping is None:
                warnings.append(f"Unsupported Murch tier skipped: {tier}")
            else:
                signals.append(
                    _signal_from_score(
                        segment_score,
                        mapping,
                        index,
                        "tier",
                    )
                )

            if bool(segment_score.get("censor_required", False)) or bool(
                segment_score.get("is_censor_required", False)
            ):
                signals.append(
                    _signal_from_score(
                        segment_score,
                        CENSOR_MAPPING,
                        index,
                        "censor",
                    )
                )

            if _clamp(segment_score.get("emotion_score"), 0.0) >= 0.75:
                signals.append(
                    _signal_from_score(
                        segment_score,
                        EMOTION_HIGH_MAPPING,
                        index,
                        "emotion",
                    )
                )

            if _clamp(segment_score.get("story_score"), 0.0) >= 0.75:
                signals.append(
                    _signal_from_score(
                        segment_score,
                        STORY_HIGH_MAPPING,
                        index,
                        "story",
                    )
                )

        for signal in signals:
            signal["metadata"] = {
                **dict(signal.get("metadata") or {}),
                **dict(metadata or {}),
            }

        return MurchScoringSignalAdapterResult(
            status=STATUS_OK if signals else STATUS_SKIPPED_NO_MURCH_SCORES,
            signals=signals,
            signal_count=len(signals),
            high_score_signal_count=sum(
                1 for signal in signals
                if signal.get("signal_type") == "murch_high_score_segment"
            ),
            medium_score_signal_count=sum(
                1 for signal in signals
                if signal.get("signal_type") == "murch_medium_score_segment"
            ),
            low_score_signal_count=sum(
                1 for signal in signals
                if signal.get("signal_type") == "murch_low_score_segment"
            ),
            protected_context_signal_count=sum(
                1 for signal in signals
                if signal.get("signal_type") == "murch_protected_context"
            ),
            technical_warning_signal_count=sum(
                1 for signal in signals
                if signal.get("signal_type") == "murch_technical_warning"
            ),
            censor_required_signal_count=sum(
                1 for signal in signals
                if signal.get("signal_type") == "murch_censor_required_context"
            ),
            emotion_high_signal_count=sum(
                1 for signal in signals
                if signal.get("signal_type") == "murch_emotion_high"
            ),
            story_high_signal_count=sum(
                1 for signal in signals
                if signal.get("signal_type") == "murch_story_high"
            ),
            warnings=warnings,
            errors=[],
            recommendation=(
                "review_murch_scoring_signals"
                if signals
                else "murch_scoring_signals_skipped_no_scores"
            ),
        )
    except Exception as exc:
        return MurchScoringSignalAdapterResult(
            status=STATUS_FAILED,
            signals=[],
            signal_count=0,
            warnings=[],
            errors=[str(exc)],
            recommendation="murch_scoring_signal_adapter_failed",
        )
