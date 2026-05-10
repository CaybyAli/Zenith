from __future__ import annotations

from datetime import datetime

from storage.base_storage_provider import BaseStorageProvider
from storage.local_storage_provider import LocalStorageProvider


class JobRepository:
    def __init__(self, storage_provider: BaseStorageProvider | None = None) -> None:
        self.storage = storage_provider or LocalStorageProvider()

    def save_job(self, job, export_path, publish_package, shorts_paths):
        target_platforms = list(job.target_platforms or [])

        normalized_shorts = [
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
                "platform_targets": (
                    list(short.get("platform_targets"))
                    if isinstance(short, dict) and short.get("platform_targets")
                    else list(target_platforms)
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
            for index, short in enumerate((shorts_paths or []), start=1)
            if ((short.get("path") if isinstance(short, dict) else short))
        ]

        job.shorts = normalized_shorts

        job_data = {
            "job_id": job.job_id,
            "job_type": job.job_type.value,
            "channel_type": job.channel_type.value,
            "target_format": job.target_format.value,
            "target_platforms": job.target_platforms,
            "status": job.status.value,
            "mode": job.mode.value,
            "autopublish_class": job.autopublish_class.value,
            "confidence_score": job.confidence_score,
            "validator_status": job.validator_status.value,
            "raw_video_path": job.raw_video_path,
            "topic": job.topic,
            "pipeline_type": job.pipeline_type.value if job.pipeline_type else None,
            "profile_id": job.profile_id,
            "quality_mode": job.quality_mode,
            "profile_version": job.profile_version,
            "profile_snapshot_path": job.profile_snapshot_path,
            "profile_source": job.profile_source,
            "profile_metadata": job.profile_metadata,
            "state_history": job.state_history,
            "current_module": job.current_module,
            "error_message": job.error_message,
            "review_status": job.review_status,
            "scheduled_at": job.scheduled_at,
            "is_scheduled": job.is_scheduled,
            "is_rerender": job.is_rerender,
            "source_job_id": job.source_job_id,
            "publish_status": job.publish_status,
            "retry_count": job.retry_count,
            "max_retry_attempts": job.max_retry_attempts,
            "retry_delay_minutes": job.retry_delay_minutes,
            "next_retry_at": job.next_retry_at,
            "last_retry_at": job.last_retry_at,
            "last_retry_reason": job.last_retry_reason,
            "retry_status": job.retry_status,
            "permanently_failed": job.permanently_failed,
            "repost_requested": job.repost_requested,
            "repost_count": job.repost_count,
            "last_repost_at": job.last_repost_at,
            "next_repost_at": job.next_repost_at,
            "repost_status": job.repost_status,
            "performance_tracking": job.performance_tracking,
            "quality_score": job.quality_score,
            "hook_score": job.hook_score,
            "editing_score": job.editing_score,
            "retention_potential_score": job.retention_potential_score,
            "shorts_potential_score": job.shorts_potential_score,
            "final_score": job.final_score,
            "recommended_action": job.recommended_action,
            "decision_reason": job.decision_reason,
            "improvement_hint": job.improvement_hint,
            "video_path": self.storage.join(export_path, "video.mp4"),
            "platform_targets": list(target_platforms),
            "thumbnail_path": (
                self.storage.join(export_path, "thumbnail.jpg")
                if publish_package.thumbnail_path
                else None
            ),
            "shorts": normalized_shorts,
            "title": publish_package.title,
            "description": publish_package.description,
            "created_at": job.created_at,
            "updated_at": datetime.utcnow().isoformat(),
        }

        self.storage.ensure_dir(export_path)

        job_file = self.storage.join(export_path, "job.json")
        self.storage.write_json(job_file, job_data, indent=4)

        print(f"[JobRepository] Saved job.json -> {job_file}")