from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from core.job_store import JobStore
from models.job import Job
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)
from shared.channel_policies import get_channel_group, requires_manual_approval
from shared.errors import ValidationError


class IntakeManager:
    def __init__(self, job_store: JobStore) -> None:
        self.job_store = job_store

    def create_gaming_job(
        self,
        *,
        channel_type: ChannelType,
        raw_video_path: str,
        target_format: TargetFormat,
        target_platforms: list[str],
        mode: Mode,
    ) -> Job:
        _VALID_VIDEO_CHANNELS = {
            ChannelType.GAMING_MAIN,
            ChannelType.GAMING_UNCUT,
            ChannelType.VLOG_MAIN,
            ChannelType.FACELESS_TREND,
        }
        if channel_type not in _VALID_VIDEO_CHANNELS:
            raise ValidationError(f"Invalid video channel_type: {channel_type}")
            
        video_path = Path(raw_video_path)
        if not video_path.exists() or not video_path.is_file():
            raise ValidationError(f"Raw video file not found: {raw_video_path}")

        job = Job(
            job_id=self._new_job_id(),
            job_type=JobType.GAMING,
            channel_type=channel_type,
            target_format=target_format,
            target_platforms=self._validate_target_platforms(target_platforms),
            status=JobStatus.CREATED,
            mode=mode,
            autopublish_class=self._default_autopublish_class(
                job_type=JobType.GAMING,
                channel_type=channel_type,
                target_format=target_format,
            ),
            confidence_score=0.0,
            validator_status=ValidatorStatus.NOT_VALIDATED,
            raw_video_path=str(video_path),
            current_module="intake_manager",
            review_status="pending" if requires_manual_approval(channel_type.value) else "approved",
            scheduled_at=None,
            is_scheduled=False,
        )
        return self.job_store.create_job(job)

    def create_faceless_job(
        self,
        *,
        topic: str,
        target_format: TargetFormat,
        target_platforms: list[str],
        mode: Mode,
    ) -> Job:
        if not topic or not topic.strip():
            raise ValidationError("Faceless topic is required")

        job = Job(
            job_id=self._new_job_id(),
            job_type=JobType.FACELESS,
            channel_type=ChannelType.FACELESS_TREND,
            target_format=target_format,
            target_platforms=self._validate_target_platforms(target_platforms),
            status=JobStatus.CREATED,
            mode=mode,
            autopublish_class=self._default_autopublish_class(
                job_type=JobType.FACELESS,
                channel_type=ChannelType.FACELESS_TREND,
                target_format=target_format,
            ),
            confidence_score=0.0,
            validator_status=ValidatorStatus.NOT_VALIDATED,
            topic=topic.strip(),
            current_module="intake_manager",
            review_status="pending" if requires_manual_approval(ChannelType.FACELESS_TREND.value) else "approved",
            scheduled_at=None,
            is_scheduled=False,
        )
        return self.job_store.create_job(job)

    def _new_job_id(self) -> str:
        return f"job_{uuid4().hex[:12]}"

    def _validate_target_platforms(self, target_platforms: list[str]) -> list[str]:
        if not target_platforms:
            raise ValidationError("At least one target platform is required")

        cleaned = [p.strip().lower() for p in target_platforms if p.strip()]
        if not cleaned:
            raise ValidationError("Target platforms are empty after cleaning")

        return cleaned

    def _default_autopublish_class(
        self,
        *,
        job_type: JobType,
        channel_type: ChannelType,
        target_format: TargetFormat,
    ) -> AutopublishClass:
        if job_type == JobType.GAMING and channel_type in {
            ChannelType.GAMING_MAIN, ChannelType.VLOG_MAIN
        }:
            return AutopublishClass.MANUAL_ONLY

        if job_type == JobType.GAMING and channel_type == ChannelType.GAMING_UNCUT:
            return AutopublishClass.CONDITIONAL

        if job_type == JobType.FACELESS and target_format == TargetFormat.SHORT:
            return AutopublishClass.CONDITIONAL

        if job_type == JobType.FACELESS:
            return AutopublishClass.MANUAL_ONLY

        return AutopublishClass.MANUAL_ONLY

    def create_vlog_job(
        self,
        *,
        video_path: str,
        mode: Mode = Mode.NORMAL,
    ) -> Job:
        return self.create_gaming_job(
            channel_type=ChannelType.VLOG_MAIN,
            raw_video_path=video_path,
            target_format=TargetFormat.LONGFORM,
            target_platforms=["youtube"],
            mode=mode,
        )

    def create_uncut_job(
        self,
        *,
        video_path: str,
        mode: Mode = Mode.NORMAL,
    ) -> Job:
        return self.create_gaming_job(
            channel_type=ChannelType.GAMING_UNCUT,
            raw_video_path=video_path,
            target_format=TargetFormat.LONGFORM,
            target_platforms=["youtube"],
            mode=mode,
        )