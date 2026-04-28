from __future__ import annotations

from core.local_music_selector import LocalMusicSelector
from models.audio_cue import AudioCue
from models.job import Job
from models.local_music_asset import LocalMusicAsset
from models.music_cue_plan import MusicCuePlan
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
        job_id="job_local_music_selector_channel_guard_smoke",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_UNCUT,
        target_format=TargetFormat.LONGFORM,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="inbox/gaming_uncut/sample.mp4",
    )


def main() -> None:
    job = build_job()

    music_cue_plan = MusicCuePlan(
        plan_id="music_plan_guard_001",
        job_id=job.job_id,
        timeline_id="timeline_guard_001",
        audio_cues=[
            AudioCue(
                cue_id="cue_guard_001",
                job_id=job.job_id,
                timeline_id="timeline_guard_001",
                segment_id="seg_guard_001",
                cue_kind="intro_bed",
                start_time=10.0,
                end_time=24.0,
                intensity=0.80,
                priority=0.82,
                notes=[],
            )
        ],
        audio_mix_instructions=[],
        plan_score=0.80,
        notes=[],
    )

    assets = [
        LocalMusicAsset(
            asset_id="music_guard_001",
            channel_type="gaming_main",
            title="Main Intro Bed",
            file_path="assets/audio/gaming_main/music/main_intro_bed.mp3",
            duration_seconds=94.5,
            energy_level=0.61,
            mood_tags=["focused"],
            cue_kinds=["intro_bed"],
            notes=[],
        )
    ]

    selections = LocalMusicSelector().select_for_plan(
        job=job,
        music_cue_plan=music_cue_plan,
        assets=assets,
    )

    assert selections == []

    print("LOCAL MUSIC SELECTOR CHANNEL GUARD SMOKE TEST PASSED")
    print({"selections": len(selections), "channel_type": job.channel_type.value})


if __name__ == "__main__":
    main()