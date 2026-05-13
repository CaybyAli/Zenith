from __future__ import annotations

from typing import Any

from models.final_cut_list import (
    FINAL_ACTION_BLOCKED_BY_CONTINUITY,
    FINAL_ACTION_CENSOR_KEEP,
    FINAL_ACTION_KEEP_HIGH_VALUE,
    FINAL_ACTION_KEEP_REVIEW,
    FINAL_ACTION_PROTECT,
    FINAL_ACTION_REMOVE_REVIEW,
    FINAL_ACTION_TECHNICAL_REVIEW,
    FINAL_ACTION_TRIM_REVIEW,
    FINAL_ACTION_UNKNOWN_REVIEW,
)
from models.review_timeline_plan import (
    REVIEW_TIMELINE_ACTION_BLOCKED_BY_CONTINUITY,
    REVIEW_TIMELINE_ACTION_CENSOR_KEEP,
    REVIEW_TIMELINE_ACTION_KEEP_REVIEW,
    REVIEW_TIMELINE_ACTION_PROTECT,
    REVIEW_TIMELINE_ACTION_REMOVE_REVIEW,
    REVIEW_TIMELINE_ACTION_TECHNICAL_REVIEW,
    REVIEW_TIMELINE_ACTION_TRIM_REVIEW,
    REVIEW_TIMELINE_ACTION_UNKNOWN_REVIEW,
    REVIEW_TIMELINE_PLAN_STATUS_PENDING_REVIEW,
    REVIEW_TIMELINE_PROTECTION_CENSOR_PROTECTED,
    REVIEW_TIMELINE_PROTECTION_CONTINUITY_BLOCKED,
    REVIEW_TIMELINE_PROTECTION_NORMAL,
    REVIEW_TIMELINE_PROTECTION_PROTECTED,
    ReviewTimelineItem,
    ReviewTimelinePlan,
)


def _object_to_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)

    if hasattr(value, "to_dict"):
        try:
            converted = value.to_dict()
            if isinstance(converted, dict):
                return dict(converted)
        except Exception:
            return {}

    return {}


def _read_value(source: Any, key: str, default: Any = None) -> Any:
    if isinstance(source, dict):
        return source.get(key, default)

    return getattr(source, key, default)


def _safe_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default

    if isinstance(value, bool):
        return value

    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "ja"}

    return bool(value)


def _safe_optional_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_duration(item_data: dict[str, Any]) -> float:
    duration = _safe_optional_float(item_data.get("duration_seconds"))
    if duration is not None and duration >= 0.0:
        return duration

    start = _safe_optional_float(item_data.get("start_seconds"))
    end = _safe_optional_float(item_data.get("end_seconds"))

    if start is not None and end is not None and end >= start:
        return end - start

    return 0.0


def _source_window(item_data: dict[str, Any]) -> tuple[float | None, float | None]:
    start = _safe_optional_float(item_data.get("start_seconds"))
    end = _safe_optional_float(item_data.get("end_seconds"))
    return start, end


def _normal_final_action(item_data: dict[str, Any]) -> str:
    return str(item_data.get("final_action") or FINAL_ACTION_UNKNOWN_REVIEW).strip().upper()


def _base_flags() -> list[str]:
    return [
        "review_only_plan",
        "media_unchanged",
        "approval_required_before_changes",
    ]


def _mapped_action_data(
    final_action: str,
    item_data: dict[str, Any],
) -> dict[str, Any]:
    item_review_required = _safe_bool(
        item_data.get("is_review_required"),
        default=final_action != FINAL_ACTION_KEEP_HIGH_VALUE,
    )
    continuity_blocked = _safe_bool(item_data.get("continuity_blocked"), False)
    is_invalid_timing = _safe_bool(item_data.get("is_invalid_timing"), False)

    flags = _base_flags()

    if is_invalid_timing:
        flags.append("invalid_timing_review_required")

    if final_action == FINAL_ACTION_KEEP_HIGH_VALUE:
        review_required = item_review_required or continuity_blocked or is_invalid_timing
        return {
            "action": REVIEW_TIMELINE_ACTION_KEEP_REVIEW,
            "protection_status": REVIEW_TIMELINE_PROTECTION_NORMAL,
            "censor_sfx_required": False,
            "continuity_blocked": continuity_blocked,
            "review_required": review_required,
            "safety_flags": flags + ["high_value_keep_candidate"],
            "review_reason": "High value item prepared for human review timeline.",
        }

    if final_action == FINAL_ACTION_KEEP_REVIEW:
        return {
            "action": REVIEW_TIMELINE_ACTION_KEEP_REVIEW,
            "protection_status": REVIEW_TIMELINE_PROTECTION_NORMAL,
            "censor_sfx_required": False,
            "continuity_blocked": continuity_blocked,
            "review_required": True,
            "safety_flags": flags + ["keep_requires_review"],
            "review_reason": "Keep decision requires human review.",
        }

    if final_action == FINAL_ACTION_TRIM_REVIEW:
        return {
            "action": REVIEW_TIMELINE_ACTION_TRIM_REVIEW,
            "protection_status": REVIEW_TIMELINE_PROTECTION_NORMAL,
            "censor_sfx_required": False,
            "continuity_blocked": continuity_blocked,
            "review_required": True,
            "safety_flags": flags + ["trim_requires_review"],
            "review_reason": "Trim decision is review-only.",
        }

    if final_action == FINAL_ACTION_REMOVE_REVIEW:
        return {
            "action": REVIEW_TIMELINE_ACTION_REMOVE_REVIEW,
            "protection_status": REVIEW_TIMELINE_PROTECTION_NORMAL,
            "censor_sfx_required": False,
            "continuity_blocked": continuity_blocked,
            "review_required": True,
            "safety_flags": flags + ["human_review_remove_candidate"],
            "review_reason": "Remove decision is only a human review candidate.",
        }

    if final_action == FINAL_ACTION_PROTECT:
        return {
            "action": REVIEW_TIMELINE_ACTION_PROTECT,
            "protection_status": REVIEW_TIMELINE_PROTECTION_PROTECTED,
            "censor_sfx_required": False,
            "continuity_blocked": continuity_blocked,
            "review_required": True,
            "safety_flags": flags + ["protected_context_preserved"],
            "review_reason": "Protected item must stay preserved for review.",
        }

    if final_action == FINAL_ACTION_CENSOR_KEEP:
        return {
            "action": REVIEW_TIMELINE_ACTION_CENSOR_KEEP,
            "protection_status": REVIEW_TIMELINE_PROTECTION_CENSOR_PROTECTED,
            "censor_sfx_required": True,
            "continuity_blocked": continuity_blocked,
            "review_required": True,
            "safety_flags": flags + ["censor_sfx_required", "censor_segment_preserved"],
            "review_reason": "Censor item is preserved and marked for later approval.",
        }

    if final_action == FINAL_ACTION_TECHNICAL_REVIEW:
        return {
            "action": REVIEW_TIMELINE_ACTION_TECHNICAL_REVIEW,
            "protection_status": REVIEW_TIMELINE_PROTECTION_NORMAL,
            "censor_sfx_required": False,
            "continuity_blocked": continuity_blocked,
            "review_required": True,
            "safety_flags": flags + ["technical_review_required"],
            "review_reason": "Technical item requires human review.",
        }

    if final_action == FINAL_ACTION_BLOCKED_BY_CONTINUITY:
        return {
            "action": REVIEW_TIMELINE_ACTION_BLOCKED_BY_CONTINUITY,
            "protection_status": REVIEW_TIMELINE_PROTECTION_CONTINUITY_BLOCKED,
            "censor_sfx_required": False,
            "continuity_blocked": True,
            "review_required": True,
            "safety_flags": flags + ["blocked_by_continuity"],
            "review_reason": "Continuity block prevents automatic changes.",
        }

    return {
        "action": REVIEW_TIMELINE_ACTION_UNKNOWN_REVIEW,
        "protection_status": REVIEW_TIMELINE_PROTECTION_NORMAL,
        "censor_sfx_required": False,
        "continuity_blocked": continuity_blocked,
        "review_required": True,
        "safety_flags": flags + ["unknown_final_decision"],
        "review_reason": "Unknown final decision requires human review.",
    }


def build_review_timeline_item(
    final_item: Any,
    index: int,
    timeline_start_seconds: float,
) -> ReviewTimelineItem:
    item_data = _object_to_dict(final_item)

    final_action = _normal_final_action(item_data)
    mapped = _mapped_action_data(final_action, item_data)

    source_start, source_end = _source_window(item_data)
    duration = _safe_duration(item_data)

    timeline_end_seconds = timeline_start_seconds + duration

    source_segment_id = (
        item_data.get("segment_id")
        or item_data.get("source_segment_id")
        or item_data.get("source_item_id")
    )

    source_final_item_id = item_data.get("final_item_id") or f"final_item_{index}"

    source_reason = str(item_data.get("reason") or "").strip()
    review_reason = source_reason or str(mapped["review_reason"])

    notes = [
        "safe_review_timeline_item",
        "source_window_preserved",
    ]

    if item_data.get("recommended_start_seconds") is not None:
        notes.append("recommended_start_kept_as_metadata_only")

    if item_data.get("recommended_end_seconds") is not None:
        notes.append("recommended_end_kept_as_metadata_only")

    return ReviewTimelineItem(
        timeline_item_id=f"review_timeline_item_{index}_{source_final_item_id}",
        source_segment_id=str(source_segment_id) if source_segment_id is not None else None,
        start_seconds=round(timeline_start_seconds, 3),
        end_seconds=round(timeline_end_seconds, 3),
        source_start_seconds=source_start,
        source_end_seconds=source_end,
        duration_seconds=round(duration, 3),
        action=str(mapped["action"]),
        final_decision=final_action,
        protection_status=str(mapped["protection_status"]),
        censor_sfx_required=bool(mapped["censor_sfx_required"]),
        continuity_blocked=bool(mapped["continuity_blocked"]),
        review_required=bool(mapped["review_required"]),
        review_reason=review_reason,
        safety_flags=list(mapped["safety_flags"]),
        notes=notes,
        metadata={
            "source_final_item_id": source_final_item_id,
            "source_item_id": item_data.get("source_item_id"),
            "final_confidence": item_data.get("final_confidence"),
            "priority": item_data.get("priority"),
            "segment_type": item_data.get("segment_type"),
            "cut_list_action": item_data.get("cut_list_action"),
            "duration_status": item_data.get("duration_status"),
            "transition_type": item_data.get("transition_type"),
            "murch_score": item_data.get("murch_score"),
            "is_keep_candidate": bool(item_data.get("is_keep_candidate", False)),
            "is_trim_candidate": bool(item_data.get("is_trim_candidate", False)),
            "is_remove_candidate": bool(item_data.get("is_remove_candidate", False)),
            "is_invalid_timing": bool(item_data.get("is_invalid_timing", False)),
            "recommended_start_seconds": item_data.get("recommended_start_seconds"),
            "recommended_end_seconds": item_data.get("recommended_end_seconds"),
            "recommended_duration_seconds": item_data.get(
                "recommended_duration_seconds"
            ),
            "decision_basis": dict(item_data.get("decision_basis") or {}),
            "source_signal_ids": list(item_data.get("source_signal_ids") or []),
        },
    )


def _chronological_items(items: list[Any]) -> list[Any]:
    indexed = list(enumerate(items))

    def sort_key(pair: tuple[int, Any]) -> tuple[float, int]:
        index, item = pair
        item_data = _object_to_dict(item)
        start = _safe_optional_float(_read_value(item_data, "start_seconds"))
        if start is None:
            start = float(index)
        return (start, index)

    return [item for _, item in sorted(indexed, key=sort_key)]


def build_review_timeline_plan(
    final_cut_list_items: list[Any] | None = None,
    job_id: str | None = None,
    source_cut_list_id: str | None = None,
    source_finalizer_run_id: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ReviewTimelinePlan:
    safe_metadata = dict(metadata or {})
    final_items = _chronological_items(list(final_cut_list_items or []))

    plan = ReviewTimelinePlan(
        job_id=job_id,
        source_cut_list_id=source_cut_list_id,
        source_finalizer_run_id=source_finalizer_run_id,
        status=REVIEW_TIMELINE_PLAN_STATUS_PENDING_REVIEW,
        recommendation="review_timeline_plan_pending_review",
        metadata={
            **safe_metadata,
            "review_only": True,
            "approval_required": True,
            "source": "cut_list_finalizer",
        },
    )

    if not final_items:
        plan.warnings.append("no_final_cut_list_items_available")
        plan.recommendation = "review_timeline_plan_empty_pending_review"
        plan.refresh_counts()
        return plan

    timeline_cursor = 0.0
    review_items: list[ReviewTimelineItem] = []

    for index, final_item in enumerate(final_items):
        item = build_review_timeline_item(
            final_item=final_item,
            index=index,
            timeline_start_seconds=timeline_cursor,
        )
        review_items.append(item)
        timeline_cursor += float(item.duration_seconds or 0.0)

    plan.items = review_items
    plan.refresh_counts()
    return plan
