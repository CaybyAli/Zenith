from __future__ import annotations

from models.music_application_instruction import MusicApplicationInstruction
from models.music_application_plan import MusicApplicationPlan


def main() -> None:
    instruction = MusicApplicationInstruction(
        instruction_id="apply_001",
        job_id="job_music_application_models_smoke",
        channel_type="gaming_main",
        asset_id="music_001",
        cue_kind="intro_bed",
        source_file_path="assets/audio/gaming_main/music/main_intro_bed.mp3",
        start_time=10.0,
        end_time=24.0,
        music_level=0.42,
        voice_priority=0.90,
        ducking_required=True,
        fade_in_seconds=0.35,
        fade_out_seconds=0.45,
        notes=["main channel music application"],
    )

    plan = MusicApplicationPlan(
        plan_id="music_apply_plan_001",
        job_id="job_music_application_models_smoke",
        channel_type="gaming_main",
        instructions=[instruction],
        application_score=0.84,
        notes=["basic music application plan smoke"],
    )

    assert len(plan.instructions) == 1
    assert plan.instructions[0].asset_id == "music_001"
    assert plan.instructions[0].ducking_required is True
    assert plan.instructions[0].fade_in_seconds == 0.35
    assert plan.application_score == 0.84

    print("MUSIC APPLICATION MODELS SMOKE TEST PASSED")
    print(
        {
            "instructions": len(plan.instructions),
            "asset_id": plan.instructions[0].asset_id,
            "application_score": plan.application_score,
        }
    )


if __name__ == "__main__":
    main()