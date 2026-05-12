from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_SKIPPED_NO_INTERACTION_SEGMENTS = "skipped_no_interaction_segments"
STATUS_FAILED = "failed"

SOURCE_INTERACTION_CLASSIFICATION = "interaction_classification"


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


def _extract_segments(source: Any) -> list[dict[str, Any]]:
    source_dict = _safe_dict(source)
    segments = source_dict.get("segment_classifications")
    if not isinstance(segments, list):
        result_dict = _safe_dict(source_dict.get("interaction_classification_result"))
        segments = result_dict.get("segment_classifications")
    if not isinstance(segments, list):
        segments = source_dict.get("segments")
    if not isinstance(segments, list):
        segments = getattr(source, "segment_classifications", [])

    return [
        dict(item) for item in segments if isinstance(item, dict)
    ] if isinstance(segments, list) else []


def _mapping_for_interaction_type(interaction_type: str) -> dict[str, str] | None:
    if interaction_type == "monologue":
        return {
            "signal_type": "interaction_monologue_segment",
            "action_hint": "review_monologue_context",
            "priority": "medium",
            "reason": "monologue_segment_detected",
        }
    if interaction_type == "interaction":
        return {
            "signal_type": "interaction_dialogue_segment",
            "action_hint": "review_interaction_context",
            "priority": "high",
            "reason": "interaction_segment_detected",
        }
    if interaction_type == "question_answer":
        return {
            "signal_type": "interaction_question_answer_segment",
            "action_hint": "protect_question_answer_context",
            "priority": "high",
            "reason": "question_answer_context_detected",
        }
    if interaction_type == "chat_reaction":
        return {
            "signal_type": "interaction_chat_reaction_segment",
            "action_hint": "review_chat_reaction_context",
            "priority": "medium",
            "reason": "chat_reaction_candidate_detected",
        }
    if interaction_type == "callout":
        return {
            "signal_type": "interaction_callout_segment",
            "action_hint": "review_gameplay_callout",
            "priority": "medium",
            "reason": "gameplay_callout_detected",
        }
    if interaction_type == "private_or_meta_candidate":
        return {
            "signal_type": "interaction_private_or_meta_candidate",
            "action_hint": "review_private_or_meta_candidate",
            "priority": "high",
            "reason": "private_or_meta_candidate_detected",
        }
    return None


def _base_metadata(segment: dict[str, Any]) -> dict[str, Any]:
    metadata = _safe_dict(segment.get("metadata"))
    return {
        "interaction_type": str(segment.get("interaction_type") or "unknown"),
        "text_preview": _text_preview(segment.get("text")),
        "context_needed": bool(segment.get("context_needed")),
        "recommendation": str(segment.get("recommendation") or ""),
        "source_segment_id": str(segment.get("segment_id") or ""),
        "warnings": [str(item) for item in _safe_list(segment.get("warnings"))],
        "errors": [str(item) for item in _safe_list(segment.get("errors"))],
        "source_metadata": metadata,
    }


def _signal_from_segment(
    segment: dict[str, Any],
    mapping: dict[str, str],
    source_index: int,
) -> dict[str, Any]:
    start_seconds = _safe_optional_float(segment.get("start_seconds"))
    end_seconds = _safe_optional_float(segment.get("end_seconds"))
    duration_seconds = _derive_duration(
        start_seconds,
        end_seconds,
        _safe_optional_float(segment.get("duration_seconds")),
    )
    center_seconds = _derive_center(start_seconds, end_seconds)
    segment_id = str(segment.get("segment_id") or f"segment_{source_index}")
    confidence = _clamp(segment.get("confidence"), 0.5)

    return {
        "signal_id": (
            f"interaction_classification_{source_index}_"
            f"{mapping['signal_type']}_{segment_id}"
        ),
        "signal_type": mapping["signal_type"],
        "source": SOURCE_INTERACTION_CLASSIFICATION,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "center_seconds": center_seconds,
        "duration_seconds": duration_seconds,
        "signal_score": confidence,
        "priority": mapping["priority"],
        "action_hint": mapping["action_hint"],
        "reason": mapping["reason"],
        "confidence": confidence,
        "metadata": _base_metadata(segment),
    }


def _context_signal(segment: dict[str, Any], source_index: int) -> dict[str, Any]:
    return _signal_from_segment(
        segment,
        {
            "signal_type": "interaction_context_needed_segment",
            "action_hint": "protect_interaction_context",
            "priority": "high",
            "reason": "interaction_context_needed_detected",
        },
        source_index,
    )


@dataclass
class InteractionClassificationSignalAdapterResult:
    status: str
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0
    monologue_signal_count: int = 0
    interaction_signal_count: int = 0
    question_answer_signal_count: int = 0
    chat_reaction_signal_count: int = 0
    callout_signal_count: int = 0
    private_or_meta_signal_count: int = 0
    context_needed_signal_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review_interaction_classification_signals"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "signals": [dict(signal) for signal in self.signals],
            "signal_count": self.signal_count,
            "monologue_signal_count": self.monologue_signal_count,
            "interaction_signal_count": self.interaction_signal_count,
            "question_answer_signal_count": self.question_answer_signal_count,
            "chat_reaction_signal_count": self.chat_reaction_signal_count,
            "callout_signal_count": self.callout_signal_count,
            "private_or_meta_signal_count": self.private_or_meta_signal_count,
            "context_needed_signal_count": self.context_needed_signal_count,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "InteractionClassificationSignalAdapterResult":
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
            monologue_signal_count=int(data.get("monologue_signal_count", 0) or 0),
            interaction_signal_count=int(
                data.get("interaction_signal_count", 0) or 0
            ),
            question_answer_signal_count=int(
                data.get("question_answer_signal_count", 0) or 0
            ),
            chat_reaction_signal_count=int(
                data.get("chat_reaction_signal_count", 0) or 0
            ),
            callout_signal_count=int(data.get("callout_signal_count", 0) or 0),
            private_or_meta_signal_count=int(
                data.get("private_or_meta_signal_count", 0) or 0
            ),
            context_needed_signal_count=int(
                data.get("context_needed_signal_count", 0) or 0
            ),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
            recommendation=str(
                data.get("recommendation")
                or "review_interaction_classification_signals"
            ),
        )


def adapt_interaction_classification_report_to_signals(
    interaction_classification_report: Any,
) -> InteractionClassificationSignalAdapterResult:
    try:
        segments = _extract_segments(interaction_classification_report)
        warnings: list[str] = []
        errors: list[str] = []

        if not segments:
            return InteractionClassificationSignalAdapterResult(
                status=STATUS_SKIPPED_NO_INTERACTION_SEGMENTS,
                signals=[],
                signal_count=0,
                warnings=["no_interaction_segments_available"],
                errors=[],
                recommendation="no_interaction_segments_available",
            )

        signals: list[dict[str, Any]] = []
        for index, segment in enumerate(segments):
            if not segment:
                warnings.append(f"invalid_interaction_segment_skipped:{index}")
                continue

            interaction_type = str(segment.get("interaction_type") or "unknown")
            mapping = _mapping_for_interaction_type(interaction_type)
            if mapping is None:
                warnings.append(f"unsupported_interaction_type_skipped:{index}")
            else:
                signals.append(_signal_from_segment(segment, mapping, index))

            if bool(segment.get("context_needed")):
                signals.append(_context_signal(segment, index))

        if not signals:
            return InteractionClassificationSignalAdapterResult(
                status=STATUS_SKIPPED_NO_INTERACTION_SEGMENTS,
                signals=[],
                signal_count=0,
                warnings=warnings + ["no_interaction_signals_produced"],
                errors=errors,
                recommendation="no_interaction_signals_available",
            )

        type_counts: dict[str, int] = {}
        for signal in signals:
            signal_type = str(signal.get("signal_type") or "")
            type_counts[signal_type] = type_counts.get(signal_type, 0) + 1

        status = STATUS_COMPLETED_WITH_WARNINGS if warnings or errors else STATUS_OK

        return InteractionClassificationSignalAdapterResult(
            status=status,
            signals=signals,
            signal_count=len(signals),
            monologue_signal_count=type_counts.get(
                "interaction_monologue_segment",
                0,
            ),
            interaction_signal_count=type_counts.get(
                "interaction_dialogue_segment",
                0,
            ),
            question_answer_signal_count=type_counts.get(
                "interaction_question_answer_segment",
                0,
            ),
            chat_reaction_signal_count=type_counts.get(
                "interaction_chat_reaction_segment",
                0,
            ),
            callout_signal_count=type_counts.get("interaction_callout_segment", 0),
            private_or_meta_signal_count=type_counts.get(
                "interaction_private_or_meta_candidate",
                0,
            ),
            context_needed_signal_count=type_counts.get(
                "interaction_context_needed_segment",
                0,
            ),
            warnings=warnings,
            errors=errors,
            recommendation="use_interaction_classification_signals",
        )
    except Exception as exc:
        return InteractionClassificationSignalAdapterResult(
            status=STATUS_FAILED,
            signals=[],
            signal_count=0,
            warnings=[],
            errors=[f"interaction_classification_signal_adapter_failed:{exc}"],
            recommendation="review_interaction_classification_signal_adapter_error",
        )
