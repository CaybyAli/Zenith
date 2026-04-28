from __future__ import annotations

from models.audio_cue import AudioCue
from models.audio_mix_instruction import AudioMixInstruction
from models.music_cue_plan import MusicCuePlan


def main() -> None:
    cue = AudioCue(
        cue_id="cue_001",
        job_id="job_audio_cue_models_smoke",
        timeline_id="timeline_001",
        segment_id="seg_001",
        cue_kind="intro_bed",
        start_time=12.0,
        end_time=26.5,
        intensity=0.78,
        priority=0.82,
        notes=["hook should get immediate music support"],
    )

    mix_instruction = AudioMixInstruction(
        instruction_id="mix_001",
        segment_id="seg_001",
        voice_priority=0.90,
        music_level=0.42,
        ducking_required=True,
        notes=["voice stays in front during intro"],
    )

    plan = MusicCuePlan(
        plan_id="music_plan_001",
        job_id="job_audio_cue_models_smoke",
        timeline_id="timeline_001",
        audio_cues=[cue],
        audio_mix_instructions=[mix_instruction],
        plan_score=0.84,
        notes=["basic music cue plan smoke"],
    )

    assert cue.duration == 14.5
    assert len(plan.audio_cues) == 1
    assert len(plan.audio_mix_instructions) == 1
    assert plan.audio_cues[0].cue_kind == "intro_bed"
    assert plan.audio_mix_instructions[0].ducking_required is True
    assert plan.plan_score == 0.84

    print("AUDIO CUE MODELS SMOKE TEST PASSED")
    print(
        {
            "audio_cues": len(plan.audio_cues),
            "mix_instructions": len(plan.audio_mix_instructions),
            "plan_score": plan.plan_score,
        }
    )


if __name__ == "__main__":
    main()