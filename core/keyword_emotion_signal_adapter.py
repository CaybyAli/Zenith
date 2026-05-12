from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_SKIPPED_NO_KEYWORD_EMOTION_SEGMENTS = "skipped_no_keyword_emotion_segments"
STATUS_FAILED = "failed"

SOURCE_KEYWORD_EMOTION = "keyword_emotion"


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
    if value is None:
        return default
    try:
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


def _derive_center(start_seconds: float | None, end_seconds: float | None) -> float | None:
    if start_seconds is None or end_seconds is None:
        return None
    return (start_seconds + end_seconds) / 2.0


def _text_preview(text: Any, limit: int = 90) -> str:
    value = " ".join(str(text or "").split())
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def _extract_segment_scores_and_matches(source: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source_dict = _safe_dict(source)
    segment_scores = source_dict.get("segment_scores")
    matches = source_dict.get("matches")

    if not isinstance(segment_scores, list):
        result_dict = _safe_dict(source_dict.get("keyword_emotion_result"))
        segment_scores = result_dict.get("segment_scores")
        matches = matches if isinstance(matches, list) else result_dict.get("matches")

    if not isinstance(segment_scores, list):
        segment_scores = getattr(source, "segment_scores", [])

    if not isinstance(matches, list):
        matches = getattr(source, "matches", [])

    return (
        [dict(item) for item in segment_scores if isinstance(item, dict)]
        if isinstance(segment_scores, list)
        else [],
        [dict(item) for item in matches if isinstance(item, dict)]
        if isinstance(matches, list)
        else [],
    )


def _segment_scores_from_matches(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scores: list[dict[str, Any]] = []
    for index, match in enumerate(matches):
        category = str(match.get("category") or "unknown")
        intensity = _clamp(match.get("intensity"), 0.5)
        confidence = _clamp(match.get("confidence"), 0.6)
        score = _clamp((intensity + confidence) / 2.0)
        scores.append(
            {
                "segment_id": f"keyword_emotion_match_segment_{index}",
                "start_seconds": match.get("start_seconds"),
                "end_seconds": match.get("end_seconds"),
                "duration_seconds": None,
                "text": match.get("text") or match.get("matched_keyword") or "",
                "categories": {category: score},
                "dominant_category": category,
                "emotion_score": score,
                "hype_score": score if category == "hype" else 0.0,
                "frustration_score": score if category == "frustration" else 0.0,
                "shock_score": score if category == "shock" else 0.0,
                "laugh_score": score if category == "laugh" else 0.0,
                "question_score": score if category == "question" else 0.0,
                "overall_keyword_score": score,
                "match_count": 1,
                "recommendation": "review_keyword_match",
                "metadata": {"source_match_id": match.get("match_id")},
                "warnings": match.get("warnings") or [],
                "errors": match.get("errors") or [],
            }
        )
    return scores


def _mapping_for_category(category: str) -> dict[str, str] | None:
    if category == "hype":
        return {
            "signal_type": "keyword_hype_segment",
            "action_hint": "review_hype_keyword_moment",
            "priority": "high",
            "reason": "hype_keyword_detected",
        }
    if category == "shock":
        return {
            "signal_type": "keyword_shock_segment",
            "action_hint": "review_shock_keyword_moment",
            "priority": "high",
            "reason": "shock_keyword_detected",
        }
    if category == "laugh":
        return {
            "signal_type": "keyword_laugh_segment",
            "action_hint": "review_comedy_keyword_moment",
            "priority": "high",
            "reason": "laugh_keyword_detected",
        }
    if category == "frustration":
        return {
            "signal_type": "keyword_frustration_segment",
            "action_hint": "review_frustration_keyword_moment",
            "priority": "medium",
            "reason": "frustration_keyword_detected",
        }
    if category == "question":
        return {
            "signal_type": "keyword_question_segment",
            "action_hint": "review_question_keyword_context",
            "priority": "medium",
            "reason": "question_keyword_detected",
        }
    return None


def _base_signal_metadata(segment_score: dict[str, Any]) -> dict[str, Any]:
    metadata = _safe_dict(segment_score.get("metadata"))
    return {
        "dominant_category": str(segment_score.get("dominant_category") or "neutral"),
        "categories": _safe_dict(segment_score.get("categories")),
        "text_preview": _text_preview(segment_score.get("text")),
        "match_count": int(segment_score.get("match_count", 0) or 0),
        "recommendation": str(segment_score.get("recommendation") or ""),
        "source_segment_id": str(segment_score.get("segment_id") or ""),
        "warnings": [str(item) for item in _safe_list(segment_score.get("warnings"))],
        "errors": [str(item) for item in _safe_list(segment_score.get("errors"))],
        "source_metadata": metadata,
    }


def _signal_for_segment_category(
    segment_score: dict[str, Any],
    category: str,
    source_index: int,
) -> dict[str, Any] | None:
    mapping = _mapping_for_category(category)
    if mapping is None:
        return None

    categories = _safe_dict(segment_score.get("categories"))
    score = _clamp(categories.get(category), _safe_float(segment_score.get(f"{category}_score"), 0.0))
    if score <= 0.0:
        return None

    start_seconds = _safe_optional_float(segment_score.get("start_seconds"))
    end_seconds = _safe_optional_float(segment_score.get("end_seconds"))
    duration_seconds = _derive_duration(
        start_seconds,
        end_seconds,
        _safe_optional_float(segment_score.get("duration_seconds")),
    )
    center_seconds = _derive_center(start_seconds, end_seconds)
    segment_id = str(segment_score.get("segment_id") or f"segment_{source_index}")

    return {
        "signal_id": f"keyword_emotion_{source_index}_{mapping['signal_type']}_{segment_id}",
        "signal_type": mapping["signal_type"],
        "source": SOURCE_KEYWORD_EMOTION,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "center_seconds": center_seconds,
        "duration_seconds": duration_seconds,
        "signal_score": score,
        "priority": mapping["priority"],
        "action_hint": mapping["action_hint"],
        "reason": mapping["reason"],
        "confidence": score,
        "metadata": _base_signal_metadata(segment_score),
    }


def _high_value_signal(
    segment_score: dict[str, Any],
    source_index: int,
    threshold: float = 0.6,
) -> dict[str, Any] | None:
    score = _clamp(segment_score.get("overall_keyword_score"), 0.0)
    if score < threshold:
        return None

    start_seconds = _safe_optional_float(segment_score.get("start_seconds"))
    end_seconds = _safe_optional_float(segment_score.get("end_seconds"))
    duration_seconds = _derive_duration(
        start_seconds,
        end_seconds,
        _safe_optional_float(segment_score.get("duration_seconds")),
    )
    center_seconds = _derive_center(start_seconds, end_seconds)
    segment_id = str(segment_score.get("segment_id") or f"segment_{source_index}")

    return {
        "signal_id": f"keyword_emotion_{source_index}_keyword_high_value_segment_{segment_id}",
        "signal_type": "keyword_high_value_segment",
        "source": SOURCE_KEYWORD_EMOTION,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "center_seconds": center_seconds,
        "duration_seconds": duration_seconds,
        "signal_score": score,
        "priority": "high",
        "action_hint": "review_high_value_keyword_segment",
        "reason": "high_keyword_emotion_score_detected",
        "confidence": score,
        "metadata": _base_signal_metadata(segment_score),
    }


@dataclass
class KeywordEmotionSignalAdapterResult:
    status: str
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0
    hype_signal_count: int = 0
    shock_signal_count: int = 0
    laugh_signal_count: int = 0
    frustration_signal_count: int = 0
    question_signal_count: int = 0
    high_value_signal_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review_keyword_emotion_signals"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "signals": [dict(signal) for signal in self.signals],
            "signal_count": self.signal_count,
            "hype_signal_count": self.hype_signal_count,
            "shock_signal_count": self.shock_signal_count,
            "laugh_signal_count": self.laugh_signal_count,
            "frustration_signal_count": self.frustration_signal_count,
            "question_signal_count": self.question_signal_count,
            "high_value_signal_count": self.high_value_signal_count,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "KeywordEmotionSignalAdapterResult":
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
            hype_signal_count=int(data.get("hype_signal_count", 0) or 0),
            shock_signal_count=int(data.get("shock_signal_count", 0) or 0),
            laugh_signal_count=int(data.get("laugh_signal_count", 0) or 0),
            frustration_signal_count=int(
                data.get("frustration_signal_count", 0) or 0
            ),
            question_signal_count=int(data.get("question_signal_count", 0) or 0),
            high_value_signal_count=int(data.get("high_value_signal_count", 0) or 0),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
            recommendation=str(
                data.get("recommendation") or "review_keyword_emotion_signals"
            ),
        )


def adapt_keyword_emotion_report_to_signals(
    keyword_emotion_report: Any,
) -> KeywordEmotionSignalAdapterResult:
    try:
        segment_scores, matches = _extract_segment_scores_and_matches(keyword_emotion_report)
        if not segment_scores and matches:
            segment_scores = _segment_scores_from_matches(matches)

        warnings: list[str] = []
        errors: list[str] = []

        if not segment_scores:
            return KeywordEmotionSignalAdapterResult(
                status=STATUS_SKIPPED_NO_KEYWORD_EMOTION_SEGMENTS,
                signals=[],
                signal_count=0,
                warnings=["no_keyword_emotion_segments_available"],
                errors=[],
                recommendation="no_keyword_emotion_segments_available",
            )

        signals: list[dict[str, Any]] = []
        for index, segment_score in enumerate(segment_scores):
            if not segment_score:
                warnings.append(f"invalid_keyword_emotion_segment_skipped:{index}")
                continue

            categories = _safe_dict(segment_score.get("categories"))
            for category in ("hype", "shock", "laugh", "frustration", "question"):
                if _clamp(categories.get(category), 0.0) <= 0.0:
                    continue
                signal = _signal_for_segment_category(segment_score, category, index)
                if signal is not None:
                    signals.append(signal)

            high_value = _high_value_signal(segment_score, index)
            if high_value is not None:
                signals.append(high_value)

        if not signals:
            return KeywordEmotionSignalAdapterResult(
                status=STATUS_SKIPPED_NO_KEYWORD_EMOTION_SEGMENTS,
                signals=[],
                signal_count=0,
                warnings=warnings + ["no_keyword_emotion_signals_produced"],
                errors=errors,
                recommendation="no_keyword_emotion_signals_available",
            )

        hype_signal_count = sum(
            1 for signal in signals if signal.get("signal_type") == "keyword_hype_segment"
        )
        shock_signal_count = sum(
            1 for signal in signals if signal.get("signal_type") == "keyword_shock_segment"
        )
        laugh_signal_count = sum(
            1 for signal in signals if signal.get("signal_type") == "keyword_laugh_segment"
        )
        frustration_signal_count = sum(
            1
            for signal in signals
            if signal.get("signal_type") == "keyword_frustration_segment"
        )
        question_signal_count = sum(
            1
            for signal in signals
            if signal.get("signal_type") == "keyword_question_segment"
        )
        high_value_signal_count = sum(
            1
            for signal in signals
            if signal.get("signal_type") == "keyword_high_value_segment"
        )

        status = STATUS_COMPLETED_WITH_WARNINGS if warnings or errors else STATUS_OK

        return KeywordEmotionSignalAdapterResult(
            status=status,
            signals=signals,
            signal_count=len(signals),
            hype_signal_count=hype_signal_count,
            shock_signal_count=shock_signal_count,
            laugh_signal_count=laugh_signal_count,
            frustration_signal_count=frustration_signal_count,
            question_signal_count=question_signal_count,
            high_value_signal_count=high_value_signal_count,
            warnings=warnings,
            errors=errors,
            recommendation="use_keyword_emotion_signals",
        )

    except Exception as exc:
        return KeywordEmotionSignalAdapterResult(
            status=STATUS_FAILED,
            signals=[],
            signal_count=0,
            warnings=[],
            errors=[f"keyword_emotion_signal_adapter_failed:{exc}"],
            recommendation="review_keyword_emotion_signal_adapter_error",
        )
