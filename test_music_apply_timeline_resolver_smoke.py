from __future__ import annotations

from core.music_apply_timeline_resolver import MusicApplyTimelineResolver
from models.job import Job
from models.music_application_instruction import MusicApplicationInstruction
from models.music_application_plan import MusicApplicationPlan
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)


def build_job() -> Job:
    return Job(
        job_id="job_music_apply_timeline_resolver_smoke",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.LONGFORM,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="inbox/gaming_main/sample.mp4",
    )


def main() -> None:
    job = build_job()

    plan = MusicApplicationPlan(
        plan_id="music_apply_plan_001",
        job_id=job.job_id,
        channel_type="gaming_main",
        instructions=[
            MusicApplicationInstruction(
                instruction_id="apply_001",
                job_id=job.job_id,
                channel_type="gaming_main",
                asset_id="music_001",
                cue_kind="intro_bed",
                source_file_path="assets/audio/gaming_main/music/main_intro_bed.mp3",
                start_time=10.0,
                end_time=20.0,
                music_level=0.42,
                voice_priority=0.90,
                ducking_required=True,
                fade_in_seconds=0.35,
                fade_out_seconds=0.45,
                notes=[],
            ),
            MusicApplicationInstruction(
                instruction_id="apply_002",
                job_id=job.job_id,
                channel_type="gaming_main",
                asset_id="music_004",
                cue_kind="calm_bed",
                source_file_path="assets/audio/gaming_main/music/main_calm_bed.mp3",
                start_time=18.0,
                end_time=28.0,
                music_level=0.30,
                voice_priority=0.88,
                ducking_required=True,
                fade_in_seconds=0.50,
                fade_out_seconds=0.60,
                notes=[],
            ),
        ],
        application_score=0.85,
        notes=[],
    )

    timeline = MusicApplyTimelineResolver().build(
        job=job,
        music_application_plan=plan,
    )

    assert timeline is not None
    assert len(timeline.segments) == 2
    assert timeline.segments[0].video_start_time == 10.0
    assert timeline.segments[0].video_end_time == 20.0
    assert timeline.segments[1].video_start_time == 20.0
    assert timeline.segments[1].video_end_time == 28.0
    assert timeline.timeline_score > 0.70

    print("MUSIC APPLY TIMELINE RESOLVER SMOKE TEST PASSED")
    print(
        {
            "segments": len(timeline.segments),
            "ranges": [
                [segment.video_start_time, segment.video_end_time]
                for segment in timeline.segments
            ],
            "timeline_score": timeline.timeline_score,
        }
    )


if __name__ == "__main__":
    main()