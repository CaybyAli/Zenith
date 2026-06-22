from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


CONTEXT_WINDOW_SECONDS = 6.0


def build_a2_reaction_candidates(a2_segments: list[Any]) -> list[dict[str, Any]]:
    segments = [_segment_payload(segment) for segment in a2_segments]
    candidates: list[dict[str, Any]] = []

    for source_index, segment in enumerate(segments):
        text = _text(segment)
        if not text:
            continue

        start = _number(segment, "start", "start_seconds")
        end = _number(segment, "end", "end_seconds")
        candidates.append(
            {
                "source_index": source_index,
                "start": round(start, 3),
                "end": round(end, 3),
                "friend_text": text,
                "beat_type": "a2_segment",
                "transcript_context": _transcript_context(
                    segments,
                    start=start,
                    end=end,
                    window_seconds=CONTEXT_WINDOW_SECONDS,
                ),
                "ali_context_text": "",
            }
        )

    return candidates


def build_shadow_report(
    accepted: list[dict[str, Any]],
    rejected_silence: list[dict[str, Any]],
    presence_policy: dict[str, Any],
    selections: list[Any],
    *,
    meta: dict[str, Any],
) -> dict[str, Any]:
    selections_by_index = {
        _selection_index(selection): _selection_payload(selection)
        for selection in selections
        if _selection_index(selection) is not None
    }

    rows: list[dict[str, Any]] = []
    for candidate_index, candidate in enumerate(accepted):
        selection = selections_by_index.get(candidate_index, {})
        is_real = bool(selection.get("is_real_reaction", False))
        rows.append(
            {
                "candidate_index": candidate_index,
                "source_index": candidate.get("source_index"),
                "friend_text": str(candidate.get("friend_text") or ""),
                "start": _rounded_optional(candidate.get("start")),
                "end": _rounded_optional(candidate.get("end")),
                "zoom_start": _rounded_optional(candidate.get("zoom_start")),
                "zoom_end": _rounded_optional(candidate.get("zoom_end")),
                "zoom_mode": str(candidate.get("zoom_mode") or ""),
                "is_real_reaction": is_real,
                "confidence": _clamped_confidence(selection.get("confidence")),
                "reason": str(selection.get("reason") or "Missing LLM verdict."),
            }
        )

    return {
        "report_type": "llm_friend_reaction_shadow_report",
        "meta": dict(meta),
        "presence_policy": dict(presence_policy),
        "candidates": rows,
        "rejected_by_presence": list(rejected_silence),
        "summary": {
            "candidate_count": len(accepted) + len(rejected_silence),
            "accepted_count": len(accepted),
            "selected_count": sum(1 for row in rows if row["is_real_reaction"] is True),
        },
    }


def _segment_payload(segment: Any) -> dict[str, Any]:
    if isinstance(segment, dict):
        return segment
    if is_dataclass(segment):
        return asdict(segment)
    if callable(getattr(segment, "to_dict", None)):
        payload = segment.to_dict()
        if isinstance(payload, dict):
            return payload
    return {
        "start_seconds": getattr(segment, "start_seconds", None),
        "end_seconds": getattr(segment, "end_seconds", None),
        "text": getattr(segment, "text", ""),
        "speaker": getattr(segment, "speaker", "unknown"),
    }


def _transcript_context(
    segments: list[dict[str, Any]],
    *,
    start: float,
    end: float,
    window_seconds: float,
) -> list[dict[str, Any]]:
    window_start = start - window_seconds
    window_end = end + window_seconds
    context: list[dict[str, Any]] = []
    for source_index, segment in enumerate(segments):
        text = _text(segment)
        if not text:
            continue
        segment_start = _number(segment, "start", "start_seconds")
        segment_end = _number(segment, "end", "end_seconds")
        if segment_start < window_end and segment_end > window_start:
            context.append(
                {
                    "source_index": source_index,
                    "start": round(segment_start, 3),
                    "end": round(segment_end, 3),
                    "speaker": str(segment.get("speaker") or "unknown"),
                    "text": text,
                }
            )
    return context


def _selection_payload(selection: Any) -> dict[str, Any]:
    if isinstance(selection, dict):
        return selection
    if is_dataclass(selection):
        return asdict(selection)
    return {
        "candidate_index": getattr(selection, "candidate_index", None),
        "is_real_reaction": getattr(selection, "is_real_reaction", False),
        "confidence": getattr(selection, "confidence", 0.0),
        "reason": getattr(selection, "reason", ""),
    }


def _selection_index(selection: Any) -> int | None:
    payload = _selection_payload(selection)
    value = payload.get("candidate_index")
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    return None


def _number(segment: dict[str, Any], *names: str) -> float:
    for name in names:
        value = segment.get(name)
        if value is not None:
            return float(value)
    raise ValueError(f"Segment without time field {names}: {segment!r}")


def _text(segment: dict[str, Any]) -> str:
    return str(segment.get("text") or "").strip()


def _rounded_optional(value: Any) -> float | None:
    if value is None:
        return None
    return round(float(value), 3)


def _clamped_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        confidence = 0.0
    return round(max(0.0, min(1.0, confidence)), 3)
