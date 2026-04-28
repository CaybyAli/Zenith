from __future__ import annotations

import os
import shutil

from core.music_application_plan_repository import MusicApplicationPlanRepository
from models.music_application_instruction import MusicApplicationInstruction
from models.music_application_plan import MusicApplicationPlan


def main() -> None:
    test_dir = os.path.join("tmp", "music_application_plan_repository_smoke")
    export_path = os.path.join(test_dir, "export")

    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    instruction = MusicApplicationInstruction(
        instruction_id="apply_repo_001",
        job_id="job_music_application_repo_smoke",
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
        notes=["repo smoke"],
    )

    plan = MusicApplicationPlan(
        plan_id="music_apply_repo_001",
        job_id="job_music_application_repo_smoke",
        channel_type="gaming_main",
        instructions=[instruction],
        application_score=0.85,
        notes=["repository smoke"],
    )

    repo = MusicApplicationPlanRepository()
    saved_path = repo.save_plan(export_path, plan)
    loaded = repo.load_plan(export_path)

    assert os.path.exists(saved_path)
    assert loaded is not None
    assert loaded.plan_id == plan.plan_id
    assert len(loaded.instructions) == 1
    assert loaded.instructions[0].asset_id == "music_001"
    assert loaded.application_score == 0.85

    print("MUSIC APPLICATION PLAN REPOSITORY SMOKE TEST PASSED")
    print(
        {
            "saved_path": saved_path,
            "instructions": len(loaded.instructions),
            "application_score": loaded.application_score,
        }
    )


if __name__ == "__main__":
    main()