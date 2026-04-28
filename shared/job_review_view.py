from __future__ import annotations

from pathlib import Path
from typing import Any

from models.job import Job


def _pretty_channel_name(channel_type: Any) -> str:
    value = str(channel_type)

    if "." in value:
        value = value.split(".")[-1]

    mapping = {
        "gaming_main": "Main",
        "gaming_uncut": "Uncut",
        "faceless_trend": "Faceless Trend",
    }

    return mapping.get(value.lower(), value.replace("_", " ").title())


def _pretty_format_name(target_format: Any) -> str:
    value = str(target_format)

    if "." in value:
        value = value.split(".")[-1]

    return value.replace("_", " ").title()

def _pretty_status_name(status: Any) -> str:
    value = str(status)

    if "." in value:
        value = value.split(".")[-1]

    return value.replace("_", " ").title()

def derive_job_display_title(job: Job) -> str:
    if getattr(job, "title", None) and str(job.title).strip():
        return str(job.title).strip()

    if job.topic and str(job.topic).strip():
        return str(job.topic).strip()

    if job.raw_video_path and str(job.raw_video_path).strip():
        return Path(str(job.raw_video_path)).stem

    return job.job_id


def build_review_card_data(job: Job) -> dict[str, Any]:
    normalized_shorts = []

    for index, short in enumerate(job.shorts or [], start=1):
        if isinstance(short, dict):
            short_path = short.get("path")
            if not short_path:
                continue

            normalized_shorts.append(
                {
                    "short_id": short.get("short_id") or f"short_{index}",
                    "path": short_path,
                    "review_status": short.get("review_status") or "pending",
                    "publish_status": (
                        short.get("publish_status")
                        if short.get("publish_status") is not None
                        else "not_published"
                    ),
                    "retry_count": int(short.get("retry_count", 0)),
                    "max_retry_attempts": (
                        int(short["max_retry_attempts"])
                        if short.get("max_retry_attempts") is not None
                        else None
                    ),
                    "retry_delay_minutes": (
                        int(short["retry_delay_minutes"])
                        if short.get("retry_delay_minutes") is not None
                        else None
                    ),
                    "next_retry_at": short.get("next_retry_at"),
                    "last_retry_at": short.get("last_retry_at"),
                    "last_retry_reason": short.get("last_retry_reason"),
                    "retry_status": short.get("retry_status"),
                    "permanently_failed": bool(short.get("permanently_failed", False)),
                    "platform_targets": list(short.get("platform_targets") or []),
                    "segment": (
    {
        "label": short["segment"].get("label"),
        "start_seconds": float(short["segment"].get("start_seconds", 0.0)),
        "end_seconds": float(short["segment"].get("end_seconds", 0.0)),
        "duration_seconds": float(short["segment"].get("duration_seconds", 0.0)),
        "score": float(short["segment"].get("score", 0.0)),
        "selection_reason": str(short["segment"].get("selection_reason", "unknown")),
    }
    if isinstance(short.get("segment"), dict)
    else None
),
                }
            )
        elif short:
            normalized_shorts.append(
                {
                    "short_id": f"short_{index}",
                    "path": short,
                    "review_status": "pending",
                    "publish_status": "not_published",
                    "retry_count": 0,
                    "max_retry_attempts": None,
                    "retry_delay_minutes": None,
                    "next_retry_at": None,
                    "last_retry_at": None,
                    "last_retry_reason": None,
                    "retry_status": None,
                    "permanently_failed": False,
                    "platform_targets": [],
                    "segment": None,
                }
            )

    return {
        "job_id": job.job_id,
        "title": derive_job_display_title(job),
        "channel": _pretty_channel_name(job.channel_type),
        "format": _pretty_format_name(job.target_format),
        "status": _pretty_status_name(job.status),
        "target_platforms": list(job.target_platforms),
        "thumbnail_path": job.thumbnail_path,
        "video_path": job.video_path,
        "shorts": normalized_shorts,
        "shorts_count": len(normalized_shorts),
               "shorts_preview": [
            f'{short["short_id"]} ({short["review_status"]}, {short["publish_status"]})'
            for short in normalized_shorts
        ],
        "repost_requested": job.repost_requested,
        "repost_count": job.repost_count,
        "last_repost_at": job.last_repost_at,
        "next_repost_at": job.next_repost_at,
        "repost_status": job.repost_status,
        "quality_score": job.quality_score,
        "hook_score": job.hook_score,
        "editing_score": job.editing_score,
        "retention_potential_score": job.retention_potential_score,
        "shorts_potential_score": job.shorts_potential_score,
        "final_score": job.final_score,
        "recommended_action": job.recommended_action,
        "decision_reason": job.decision_reason,
        "improvement_hint": job.improvement_hint,
    }