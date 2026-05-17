from __future__ import annotations

from core.music_application_builder import MusicApplicationBuilder
from models.audio_cue import AudioCue
from models.audio_mix_instruction import AudioMixInstruction
from models.job import Job
from models.local_music_asset import LocalMusicAsset
from models.local_music_selection import LocalMusicSelection
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
        job_id="job_music_application_builder_smoke",
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
        plan_id="music_plan_builder_001",
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
        audio_mix_instructions=[
            AudioMixInstruction(
                instruction_id="mix_001",
                segment_id="seg_001",
                voice_priority=0.90,
                music_level=0.42,
                ducking_required=True,
                notes=[],
            ),
            AudioMixInstruction(
                instruction_id="mix_002",
                segment_id="seg_002",
                voice_priority=0.74,
                music_level=0.78,
                ducking_required=True,
                notes=[],
            ),
        ],
        plan_score=0.85,
        notes=[],
    )

    selections = [
        LocalMusicSelection(
            selection_id="sel_001",
            job_id=job.job_id,
            channel_type="gaming_main",
            asset_id="music_001",
            cue_kind="intro_bed",
            match_score=0.97,
            start_time=10.0,
            end_time=24.0,
            notes=[],
        ),
        LocalMusicSelection(
            selection_id="sel_002",
            job_id=job.job_id,
            channel_type="gaming_main",
            asset_id="music_002",
            cue_kind="peak_hit",
            match_score=0.96,
            start_time=50.0,
            end_time=72.0,
            notes=[],
        ),
    ]

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
    ]

    plan = MusicApplicationBuilder().build(
        job=job,
        music_cue_plan=music_cue_plan,
        local_music_selections=selections,
        assets=assets,
    )

    assert plan is not None
    assert len(plan.instructions) == 2
    assert plan.instructions[0].asset_id == "music_001"
    assert plan.instructions[1].asset_id == "music_002"
    assert plan.instructions[0].fade_in_seconds == 0.35
    assert plan.instructions[1].fade_out_seconds == 0.20
    assert plan.application_score > 0.70

    print("MUSIC APPLICATION BUILDER SMOKE TEST PASSED")
    print(
        {
            "instructions": len(plan.instructions),
            "asset_ids": [instruction.asset_id for instruction in plan.instructions],
            "application_score": plan.application_score,
        }
    )


if __name__ == "__main__":
    main()