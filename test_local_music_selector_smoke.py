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
        job_id="job_local_music_selector_smoke",
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

    music_cue_plan = MusicCuePlan(
        plan_id="music_plan_001",
        job_id=job.job_id,
        timeline_id="timeline_001",
        audio_cues=[
            AudioCue(
                cue_id="cue_001",
                job_id=job.job_id,
                timeline_id="timeline_001",
                segment_id="seg_001",
                cue_kind="intro_bed",
                start_time=10.0,
                end_time=24.0,
                intensity=0.82,
                priority=0.84,
                notes=[],
            ),
            AudioCue(
                cue_id="cue_002",
                job_id=job.job_id,
                timeline_id="timeline_001",
                segment_id="seg_002",
                cue_kind="peak_hit",
                start_time=50.0,
                end_time=72.0,
                intensity=0.91,
                priority=0.89,
                notes=[],
            ),
        ],
        audio_mix_instructions=[],
        plan_score=0.85,
        notes=[],
    )

    assets = [
        LocalMusicAsset(
            asset_id="music_001",
            channel_type="gaming_main",
            title="Main Intro Bed",
            file_path="assets/audio/gaming_main/music/main_intro_bed.mp3",
            duration_seconds=94.5,
            energy_level=0.61,
            mood_tags=["focused"],
            cue_kinds=["intro_bed", "transition_bed"],
            notes=[],
        ),
        LocalMusicAsset(
            asset_id="music_002",
            channel_type="gaming_main",
            title="Main Peak Hit",
            file_path="assets/audio/gaming_main/music/main_peak_hit.mp3",
            duration_seconds=71.0,
            energy_level=0.94,
            mood_tags=["impact"],
            cue_kinds=["peak_hit", "build_up"],
            notes=[],
        ),
        LocalMusicAsset(
            asset_id="music_003",
            channel_type="gaming_main",
            title="Main Calm Bed",
            file_path="assets/audio/gaming_main/music/main_calm_bed.mp3",
            duration_seconds=120.0,
            energy_level=0.28,
            mood_tags=["calm"],
            cue_kinds=["calm_bed"],
            notes=[],
        ),
    ]

    selections = LocalMusicSelector().select_for_plan(
        job=job,
        music_cue_plan=music_cue_plan,
        assets=assets,
    )

    assert len(selections) == 2
    assert selections[0].cue_kind == "intro_bed"
    assert selections[1].cue_kind == "peak_hit"
    assert selections[0].asset_id == "music_001"
    assert selections[1].asset_id == "music_002"
    assert all(selection.match_score >= 0.70 for selection in selections)

    print("LOCAL MUSIC SELECTOR SMOKE TEST PASSED")
    print(
        {
            "selections": len(selections),
            "asset_ids": [selection.asset_id for selection in selections],
            "cue_kinds": [selection.cue_kind for selection in selections],
        }
    )


if __name__ == "__main__":
    main()