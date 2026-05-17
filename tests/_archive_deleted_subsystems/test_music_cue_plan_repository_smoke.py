from __future__ import annotations

import os
import shutil

from core.music_cue_plan_repository import MusicCuePlanRepository
from models.audio_cue import AudioCue
from models.audio_mix_instruction import AudioMixInstruction
from models.music_cue_plan import MusicCuePlan


def main() -> None:
    test_dir = os.path.join("tmp", "music_cue_plan_repository_smoke")
    export_path = os.path.join(test_dir, "export")

    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    cue = AudioCue(
        cue_id="cue_repo_001",
        job_id="job_music_cue_repo_smoke",
        timeline_id="timeline_repo_001",
        segment_id="seg_repo_001",
        cue_kind="intro_bed",
        start_time=10.0,
        end_time=24.0,
        intensity=0.84,
        priority=0.86,
        notes=["repo cue"],
    )

    mix_instruction = AudioMixInstruction(
        instruction_id="mix_repo_001",
        segment_id="seg_repo_001",
        voice_priority=0.90,
        music_level=0.42,
        ducking_required=True,
        notes=["repo mix"],
    )

    plan = MusicCuePlan(
        plan_id="music_repo_001",
        job_id="job_music_cue_repo_smoke",
        timeline_id="timeline_repo_001",
        audio_cues=[cue],
        audio_mix_instructions=[mix_instruction],
        plan_score=0.85,
        notes=["repository smoke test"],
    )

    repo = MusicCuePlanRepository()
    saved_path = repo.save_plan(export_path, plan)
    loaded = repo.load_plan(export_path)

    assert os.path.exists(saved_path)
    assert loaded is not None
    assert loaded.plan_id == plan.plan_id
    assert len(loaded.audio_cues) == 1
    assert len(loaded.audio_mix_instructions) == 1
    assert loaded.plan_score == 0.85

    print("MUSIC CUE PLAN REPOSITORY SMOKE TEST PASSED")
    print(
        {
            "saved_path": saved_path,
            "audio_cues": len(loaded.audio_cues),
            "mix_instructions": len(loaded.audio_mix_instructions),
            "plan_score": loaded.plan_score,
        }
    )


if __name__ == "__main__":
    main()