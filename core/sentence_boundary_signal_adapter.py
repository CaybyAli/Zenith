from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


STATUS_OK = "ok"
STATUS_COMPLETED_WITH_WARNINGS = "completed_with_warnings"
STATUS_SKIPPED_NO_SENTENCE_BOUNDARIES = "skipped_no_sentence_boundaries"
STATUS_FAILED = "failed"

SOURCE_SENTENCE_BOUNDARY = "sentence_boundary"


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


def _extract_boundaries_and_zones(source: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source_dict = _safe_dict(source)

    boundaries = source_dict.get("boundaries")
    zones = source_dict.get("protection_zones")

    if not isinstance(boundaries, list):
        result_dict = _safe_dict(source_dict.get("sentence_boundary_result"))
        boundaries = result_dict.get("boundaries")
        zones = zones if isinstance(zones, list) else result_dict.get("protection_zones")

    if not isinstance(boundaries, list):
        boundaries = getattr(source, "boundaries", [])

    if not isinstance(zones, list):
        zones = getattr(source, "protection_zones", [])

    return (
        [dict(item) for item in boundaries if isinstance(item, dict)]
        if isinstance(boundaries, list)
        else [],
        [dict(item) for item in zones if isinstance(item, dict)]
        if isinstance(zones, list)
        else [],
    )


def _mapping_for_boundary_type(boundary_type: str) -> dict[str, str] | None:
    if boundary_type == "safe_sentence_boundary":
        return {
            "signal_type": "sentence_safe_boundary",
            "action_hint": "boundary_safe_for_review",
            "priority": "medium",
            "reason": "safe_sentence_boundary_detected",
        }

    if boundary_type in {"unsafe_sentence_boundary", "open_sentence_fragment"}:
        return {
            "signal_type": "sentence_boundary_protection",
            "action_hint": "protect_sentence_from_cut",
            "priority": "high",
            "reason": "open_sentence_or_unsafe_boundary_detected",
        }

    if boundary_type in {"question_boundary", "open_question"}:
        return {
            "signal_type": "sentence_question_context_protection",
            "action_hint": "protect_question_answer_context",
            "priority": "high",
            "reason": "question_context_should_be_preserved",
        }

    if boundary_type == "answer_candidate":
        return {
            "signal_type": "sentence_answer_candidate",
            "action_hint": "review_answer_context",
            "priority": "medium",
            "reason": "answer_candidate_detected",
        }

    return None


def _make_text_preview(text: Any, limit: int = 80) -> str:
    value = " ".join(str(text or "").split())
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


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


def sentence_boundary_to_signal(
    boundary: dict[str, Any],
    source_index: int = 0,
) -> dict[str, Any] | None:
    boundary_type = str(boundary.get("boundary_type") or "unknown")
    mapping = _mapping_for_boundary_type(boundary_type)
    if mapping is None:
        return None

    start_seconds = _safe_optional_float(boundary.get("start_seconds"))
    end_seconds = _safe_optional_float(boundary.get("end_seconds"))
    center_seconds = _derive_center(
        start_seconds,
        end_seconds,
        _safe_optional_float(boundary.get("center_seconds")),
    )
    duration_seconds = _derive_duration(start_seconds, end_seconds)
    confidence = _clamp(boundary.get("confidence"), 0.65)

    boundary_id = str(boundary.get("boundary_id") or f"boundary_{source_index}")

    return {
        "signal_id": f"sentence_boundary_{source_index}_{mapping['signal_type']}_{boundary_id}",
        "signal_type": mapping["signal_type"],
        "source": SOURCE_SENTENCE_BOUNDARY,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "center_seconds": center_seconds,
        "duration_seconds": duration_seconds,
        "signal_score": confidence,
        "priority": mapping["priority"],
        "action_hint": mapping["action_hint"],
        "reason": mapping["reason"],
        "confidence": confidence,
        "metadata": {
            "original_boundary_type": boundary_type,
            "protection_level": str(boundary.get("protection_level") or ""),
            "text_preview": _make_text_preview(
                boundary.get("text") or boundary.get("normalized_text")
            ),
            "source_boundary_id": boundary_id,
            "recommendation": str(boundary.get("recommendation") or ""),
            "warnings": [str(item) for item in _safe_list(boundary.get("warnings"))],
            "errors": [str(item) for item in _safe_list(boundary.get("errors"))],
        },
    }


def protection_zone_to_signal(
    zone: dict[str, Any],
    source_index: int = 0,
) -> dict[str, Any] | None:
    zone_id = str(zone.get("zone_id") or f"zone_{source_index}")
    start_seconds = _safe_optional_float(zone.get("start_seconds"))
    end_seconds = _safe_optional_float(zone.get("end_seconds"))
    duration_seconds = _derive_duration(
        start_seconds,
        end_seconds,
        _safe_optional_float(zone.get("duration_seconds")),
    )
    center_seconds = _derive_center(start_seconds, end_seconds)
    confidence = _clamp(zone.get("confidence"), 0.7)
    metadata = _safe_dict(zone.get("metadata"))

    return {
        "signal_id": f"sentence_boundary_zone_{source_index}_{zone_id}",
        "signal_type": "sentence_protection_zone",
        "source": SOURCE_SENTENCE_BOUNDARY,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "center_seconds": center_seconds,
        "duration_seconds": duration_seconds,
        "signal_score": confidence,
        "priority": "high",
        "action_hint": "protect_transcript_zone",
        "reason": "sentence_protection_zone_detected",
        "confidence": confidence,
        "metadata": {
            "original_boundary_type": str(metadata.get("source_boundary_type") or ""),
            "protection_level": str(zone.get("protection_level") or ""),
            "text_preview": "",
            "source_boundary_id": ",".join(
                str(item) for item in _safe_list(zone.get("source_boundary_ids"))
            ),
            "source_zone_id": zone_id,
            "recommendation": str(zone.get("reason") or ""),
            "warnings": [str(item) for item in _safe_list(zone.get("warnings"))],
            "errors": [str(item) for item in _safe_list(zone.get("errors"))],
            "zone_type": str(zone.get("zone_type") or ""),
        },
    }


@dataclass
class SentenceBoundarySignalAdapterResult:
    status: str
    signals: list[dict[str, Any]] = field(default_factory=list)
    signal_count: int = 0
    safe_boundary_signal_count: int = 0
    protection_signal_count: int = 0
    question_context_signal_count: int = 0
    answer_candidate_signal_count: int = 0
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str = "review_sentence_boundary_signals"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "signals": [dict(signal) for signal in self.signals],
            "signal_count": self.signal_count,
            "safe_boundary_signal_count": self.safe_boundary_signal_count,
            "protection_signal_count": self.protection_signal_count,
            "question_context_signal_count": self.question_context_signal_count,
            "answer_candidate_signal_count": self.answer_candidate_signal_count,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
        }

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any] | None,
    ) -> "SentenceBoundarySignalAdapterResult":
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
            safe_boundary_signal_count=int(
                data.get("safe_boundary_signal_count", 0) or 0
            ),
            protection_signal_count=int(data.get("protection_signal_count", 0) or 0),
            question_context_signal_count=int(
                data.get("question_context_signal_count", 0) or 0
            ),
            answer_candidate_signal_count=int(
                data.get("answer_candidate_signal_count", 0) or 0
            ),
            warnings=[str(item) for item in _safe_list(data.get("warnings"))],
            errors=[str(item) for item in _safe_list(data.get("errors"))],
            recommendation=str(
                data.get("recommendation") or "review_sentence_boundary_signals"
            ),
        )


def adapt_sentence_boundary_report_to_signals(
    sentence_boundary_report: Any,
) -> SentenceBoundarySignalAdapterResult:
    try:
        boundaries, zones = _extract_boundaries_and_zones(sentence_boundary_report)
        warnings: list[str] = []
        errors: list[str] = []

        if not boundaries and not zones:
            return SentenceBoundarySignalAdapterResult(
                status=STATUS_SKIPPED_NO_SENTENCE_BOUNDARIES,
                signals=[],
                signal_count=0,
                warnings=["no_sentence_boundaries_available"],
                errors=[],
                recommendation="no_sentence_boundaries_available",
            )

        signals: list[dict[str, Any]] = []
        for index, boundary in enumerate(boundaries):
            signal = sentence_boundary_to_signal(boundary, source_index=index)
            if signal is None:
                warnings.append(f"unsupported_sentence_boundary_skipped:{index}")
                continue
            signals.append(signal)

        for index, zone in enumerate(zones):
            signal = protection_zone_to_signal(zone, source_index=index)
            if signal is None:
                warnings.append(f"invalid_sentence_protection_zone_skipped:{index}")
                continue
            signals.append(signal)

        if not signals:
            return SentenceBoundarySignalAdapterResult(
                status=STATUS_SKIPPED_NO_SENTENCE_BOUNDARIES,
                signals=[],
                signal_count=0,
                warnings=warnings + ["no_sentence_boundary_signals_produced"],
                errors=errors,
                recommendation="no_sentence_boundary_signals_available",
            )

        safe_boundary_signal_count = sum(
            1 for signal in signals if signal.get("signal_type") == "sentence_safe_boundary"
        )
        protection_signal_count = sum(
            1
            for signal in signals
            if signal.get("signal_type")
            in {"sentence_boundary_protection", "sentence_protection_zone"}
        )
        question_context_signal_count = sum(
            1
            for signal in signals
            if signal.get("signal_type") == "sentence_question_context_protection"
        )
        answer_candidate_signal_count = sum(
            1
            for signal in signals
            if signal.get("signal_type") == "sentence_answer_candidate"
        )

        status = STATUS_COMPLETED_WITH_WARNINGS if warnings or errors else STATUS_OK

        return SentenceBoundarySignalAdapterResult(
            status=status,
            signals=signals,
            signal_count=len(signals),
            safe_boundary_signal_count=safe_boundary_signal_count,
            protection_signal_count=protection_signal_count,
            question_context_signal_count=question_context_signal_count,
            answer_candidate_signal_count=answer_candidate_signal_count,
            warnings=warnings,
            errors=errors,
            recommendation="use_sentence_boundary_signals",
        )

    except Exception as exc:
        return SentenceBoundarySignalAdapterResult(
            status=STATUS_FAILED,
            signals=[],
            signal_count=0,
            warnings=[],
            errors=[f"sentence_boundary_signal_adapter_failed:{exc}"],
            recommendation="review_sentence_boundary_signal_adapter_error",
        )
