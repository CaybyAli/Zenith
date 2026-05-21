from __future__ import annotations

from models.job import Job
from models.shorts_clip import ShortsClip
from models.shorts_reframe_plan import ShortsReframePlan
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)


def _make_reframe_plan() -> ShortsReframePlan:
    return ShortsReframePlan(
        layout_type="hybrid_split",
        ffmpeg_crop_filter="crop=608:1080:656:0,scale=1080:1920",
        target_aspect_ratio="9:16",
        safe_zone_top_px=144,
        safe_zone_bottom_px=180,
        face_tracking_enabled=True,
        layout_rationale="Facecam and gameplay both matter for this short.",
        platform_preset="youtube_shorts",
    )


def _make_shorts_clip(reframe_plan: ShortsReframePlan | None = None) -> ShortsClip:
    return ShortsClip(
        source_job_id="job_source_001",
        source_start_time=12.5,
        source_end_time=44.5,
        planned_duration=32.0,
        reframe_plan=reframe_plan,
        hook_score=0.91,
        llm_rationale="Strong opening reaction and clear payoff.",
        status="planned",
        clip_index=0,
        output_path="",
    )


def _make_job(shorts_clips=None) -> Job:
    return Job(
        job_id="job_with_shorts_001",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.BOTH,
        target_platforms=["youtube"],
        status=JobStatus.CREATED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        shorts_clips=list(shorts_clips or []),
    )


def test_shorts_reframe_plan_round_trip() -> None:
    plan = _make_reframe_plan()

    restored = ShortsReframePlan.from_dict(plan.to_dict())

    assert restored == plan


def test_shorts_clip_round_trip_with_reframe_plan() -> None:
    clip = _make_shorts_clip(reframe_plan=_make_reframe_plan())

    restored = ShortsClip.from_dict(clip.to_dict())

    assert restored == clip
    assert restored.reframe_plan == clip.reframe_plan


def test_shorts_clip_round_trip_without_reframe_plan() -> None:
    clip = _make_shorts_clip(reframe_plan=None)

    restored = ShortsClip.from_dict(clip.to_dict())

    assert restored == clip
    assert restored.reframe_plan is None
    assert restored.to_dict()["reframe_plan"] is None


def test_job_round_trip_with_shorts_clips() -> None:
    clip = _make_shorts_clip(reframe_plan=_make_reframe_plan())
    job = _make_job(shorts_clips=[clip])

    restored = Job.from_dict(job.to_dict())

    assert len(restored.shorts_clips) == 1
    assert restored.shorts_clips[0] == clip
    assert restored.shorts_clips[0].reframe_plan == clip.reframe_plan


def test_old_job_without_shorts_clips_key_loads_empty_list() -> None:
    job_dict = _make_job().to_dict()
    job_dict.pop("shorts_clips", None)

    restored = Job.from_dict(job_dict)

    assert restored.shorts_clips == []


def test_shorts_job_status_enum_values_exist() -> None:
    assert JobStatus.SHORTS_GENERATING.value == "shorts_generating"
    assert JobStatus.SHORTS_RENDERED.value == "shorts_rendered"
