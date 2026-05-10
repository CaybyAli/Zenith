from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    PipelineType,
    TargetFormat,
    ValidatorStatus,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class Job:
    job_id: str
    job_type: JobType
    channel_type: ChannelType
    target_format: TargetFormat
    target_platforms: list[str]
    status: JobStatus
    mode: Mode

    autopublish_class: AutopublishClass
    confidence_score: float
    validator_status: ValidatorStatus

    raw_video_path: str | None = None
    shorts: list[dict[str, Any]] = field(default_factory=list)
    topic: str | None = None
    title: str | None = None
    pipeline_type: PipelineType | None = None
    profile_id: str | None = None
    quality_mode: str | None = None
    profile_version: str | None = None
    profile_snapshot_path: str | None = None
    profile_source: str | None = None
    profile_metadata: dict[str, Any] = field(default_factory=dict)
    state_history: list[dict[str, Any]] = field(default_factory=list)
    current_module: str | None = None
    error_message: str | None = None

    file_info: dict[str, Any] = field(default_factory=dict)
    file_acceptance: dict[str, Any] = field(default_factory=dict)
    stream_classification: dict[str, Any] = field(default_factory=dict)
    file_readability: dict[str, Any] = field(default_factory=dict)
    file_handler_report: dict[str, Any] = field(default_factory=dict)
    preprocessing_dir: str | None = None
    preprocessing_manifest_path: str | None = None
    preprocessing_manifest: dict[str, Any] = field(default_factory=dict)
    preprocessing_status: str | None = None
    preprocessing_cache_key: str | None = None
    preprocessing_reused_cache: bool = False
    audio_extraction_plan: dict[str, Any] = field(default_factory=dict)
    audio_targets: list[dict[str, Any]] = field(default_factory=list)

    recovery_status: str | None = None
    resume_safety: str | None = None
    recovery_report: dict[str, Any] = field(default_factory=dict)

    decision_log_path: str | None = None
    decision_jsonl_path: str | None = None
    error_log_path: str | None = None
    error_jsonl_path: str | None = None
    log_index: dict[str, Any] = field(default_factory=dict)

    debug_mode: str = "off"
    debug_context: dict[str, Any] = field(default_factory=dict)

    review_status: str = "pending"
    scheduled_at: Optional[str] = None
    is_scheduled: bool = False

    # 🔥 NEU (für Dashboard)
    is_rerender: bool = False
    source_job_id: str | None = None
    publish_status: str | None = None

    retry_count: int = 0
    max_retry_attempts: int | None = None
    retry_delay_minutes: int | None = None
    next_retry_at: str | None = None
    last_retry_at: str | None = None
    last_retry_reason: str | None = None
    retry_status: str | None = None
    permanently_failed: bool = False

    repost_requested: bool = False
    repost_count: int = 0
    last_repost_at: str | None = None
    next_repost_at: str | None = None
    repost_status: str | None = None 

    thumbnail_path: str | None = None
    video_path: str | None = None    
    render_version: int | None = None

    quality_score: float | None = None
    hook_score: float | None = None
    editing_score: float | None = None
    retention_potential_score: float | None = None
    shorts_potential_score: float | None = None
    final_score: float | None = None

    decision_reason: str | None = None
    improvement_hint: str | None = None

    recommended_action: str | None = None

    performance_tracking: dict[str, Any] = field(default_factory=lambda: {
        "enabled": True,
        "youtube_video_id": None,
        "last_synced_at": None,
        "metrics": {
            "views": 0,
            "likes": 0,
            "comments": 0,
            "ctr": None,
            "average_view_duration": None,
            "average_percentage_viewed": None
        }
    })

    created_at: str = field(default_factory=utc_now_iso)
    updated_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.updated_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Job":
        return cls(
            job_id=data.get("job_id"),
            job_type=JobType(data.get("job_type", "gaming")),
            channel_type=ChannelType(data.get("channel_type", "gaming_main")),
            target_format=TargetFormat(data.get("target_format", "short")),
            target_platforms=list(data.get("target_platforms", [])),
            status=JobStatus(data.get("status", "routed")),
            mode=Mode(data.get("mode", "normal")),
            autopublish_class=AutopublishClass(data.get("autopublish_class", "manual_only")),
            confidence_score=float(data.get("confidence_score", 0.0)),
            validator_status=ValidatorStatus(data.get("validator_status", "not_validated")),
            raw_video_path=data.get("raw_video_path"),
            topic=data.get("topic"),
            title=data.get("title"),            
            pipeline_type=PipelineType(data["pipeline_type"]) if data.get("pipeline_type") else None,
            profile_id=data.get("profile_id"),
            quality_mode=data.get("quality_mode"),
            profile_version=data.get("profile_version"),
            profile_snapshot_path=data.get("profile_snapshot_path"),
            profile_source=data.get("profile_source"),
            profile_metadata=dict(data.get("profile_metadata") or {}),
            state_history=list(data.get("state_history") or []),
            current_module=data.get("current_module"),
            error_message=data.get("error_message"),
            file_info=dict(data.get("file_info") or {}),
            file_acceptance=dict(data.get("file_acceptance") or {}),
            stream_classification=dict(data.get("stream_classification") or {}),
            file_readability=dict(data.get("file_readability") or {}),
            file_handler_report=dict(data.get("file_handler_report") or {}),
            preprocessing_dir=data.get("preprocessing_dir"),
            preprocessing_manifest_path=data.get("preprocessing_manifest_path"),
            preprocessing_manifest=dict(data.get("preprocessing_manifest") or {}),
            preprocessing_status=data.get("preprocessing_status"),
            preprocessing_cache_key=data.get("preprocessing_cache_key"),
            preprocessing_reused_cache=bool(data.get("preprocessing_reused_cache", False)),
            audio_extraction_plan=dict(data.get("audio_extraction_plan") or {}),
            audio_targets=list(data.get("audio_targets") or []),
            recovery_status=data.get("recovery_status"),
            resume_safety=data.get("resume_safety"),
            recovery_report=dict(data.get("recovery_report") or {}),
            decision_log_path=data.get("decision_log_path"),
            decision_jsonl_path=data.get("decision_jsonl_path"),
            error_log_path=data.get("error_log_path"),
            error_jsonl_path=data.get("error_jsonl_path"),
            log_index=dict(data.get("log_index") or {}),
            debug_mode=data.get("debug_mode", "off"),
            debug_context=dict(data.get("debug_context") or {}),
            review_status=data.get("review_status", "pending"),
            scheduled_at=data.get("scheduled_at"),
            is_scheduled=data.get("is_scheduled", False),

            # 🔥 NEU
            is_rerender=bool(
    data.get("is_rerender", False) or data.get("rerender_requested", False)
),
            source_job_id=data.get("source_job_id"),
            publish_status=data.get("publish_status"),

            retry_count=int(data.get("retry_count", 0)),
            max_retry_attempts=(
                int(data["max_retry_attempts"])
                if data.get("max_retry_attempts") is not None
                else None
            ),
            retry_delay_minutes=(
                int(data["retry_delay_minutes"])
                if data.get("retry_delay_minutes") is not None
                else None
            ),
            next_retry_at=data.get("next_retry_at"),
            last_retry_at=data.get("last_retry_at"),
            last_retry_reason=data.get("last_retry_reason"),
            retry_status=data.get("retry_status"),
            permanently_failed=bool(data.get("permanently_failed", False)),
            repost_requested=bool(data.get("repost_requested", False)),
            repost_count=int(data.get("repost_count", 0)),
            last_repost_at=data.get("last_repost_at"),
            next_repost_at=data.get("next_repost_at"),
            repost_status=data.get("repost_status"),

thumbnail_path=data.get("thumbnail_path"),
video_path=data.get("video_path"),
render_version=(
    int(data["render_version"])
    if data.get("render_version") is not None
    else None
),
shorts=[
    {
        "short_id": (
            short.get("short_id")
            if isinstance(short, dict) and short.get("short_id")
            else f"short_{index}"
        ),
        "path": (
            short.get("path")
            if isinstance(short, dict)
            else short
        ),
        "status": (
            short.get("status")
            if isinstance(short, dict) and short.get("status")
            else "generated"
        ),
        "review_status": (
            short.get("review_status")
            if isinstance(short, dict) and short.get("review_status")
            else "pending"
        ),
        "publish_status": (
            short.get("publish_status")
            if isinstance(short, dict) and short.get("publish_status")
            else "not_published"
        ),

        "retry_count": (
            int(short.get("retry_count", 0))
            if isinstance(short, dict)
            else 0
        ),
        "max_retry_attempts": (
            int(short["max_retry_attempts"])
            if isinstance(short, dict) and short.get("max_retry_attempts") is not None
            else None
        ),
        "retry_delay_minutes": (
            int(short["retry_delay_minutes"])
            if isinstance(short, dict) and short.get("retry_delay_minutes") is not None
            else None
        ),
        "next_retry_at": (
            short.get("next_retry_at")
            if isinstance(short, dict)
            else None
        ),
        "last_retry_at": (
            short.get("last_retry_at")
            if isinstance(short, dict)
            else None
        ),
        "last_retry_reason": (
            short.get("last_retry_reason")
            if isinstance(short, dict)
            else None
        ),
        "retry_status": (
            short.get("retry_status")
            if isinstance(short, dict)
            else None
        ),
        "permanently_failed": (
            bool(short.get("permanently_failed", False))
            if isinstance(short, dict)
            else False
        ),
        "platform_targets": (
            list(short.get("platform_targets"))
            if isinstance(short, dict) and short.get("platform_targets")
            else []
        ),
        "segment": (
            {
                "label": short["segment"].get("label"),
                "start_seconds": float(short["segment"].get("start_seconds", 0.0)),
                "end_seconds": float(short["segment"].get("end_seconds", 0.0)),
                "duration_seconds": float(short["segment"].get("duration_seconds", 0.0)),
                "score": float(short["segment"].get("score", 0.0)),
                "selection_reason": str(short["segment"].get("selection_reason", "unknown")),
            }
            if isinstance(short, dict) and isinstance(short.get("segment"), dict)
            else None
        ),
    }
    for index, short in enumerate(data.get("shorts", []), start=1)
    if ((short.get("path") if isinstance(short, dict) else short))
],

            quality_score=float(data["quality_score"]) if data.get("quality_score") is not None else None,
            hook_score=float(data["hook_score"]) if data.get("hook_score") is not None else None,
            editing_score=float(data["editing_score"]) if data.get("editing_score") is not None else None,
            retention_potential_score=float(data["retention_potential_score"]) if data.get("retention_potential_score") is not None else None,
            shorts_potential_score=float(data["shorts_potential_score"]) if data.get("shorts_potential_score") is not None else None,
            final_score=float(data["final_score"]) if data.get("final_score") is not None else None,
            decision_reason=data.get("decision_reason"),
            improvement_hint=data.get("improvement_hint"),

            recommended_action=data.get("recommended_action"),

            performance_tracking=data.get("performance_tracking", {
                "enabled": True,
                "youtube_video_id": None,
                "last_synced_at": None,
                "metrics": {
                    "views": 0,
                    "likes": 0,
                    "comments": 0,
                    "ctr": None,
                    "average_view_duration": None,
                    "average_percentage_viewed": None
                }
            }),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
