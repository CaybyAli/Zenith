from __future__ import annotations

from core.audio_mix_planner import AudioMixPlanner
from models.audio_cue import AudioCue
from models.dynamic_edit_plan import DynamicEditPlan
from models.edit_timeline import EditTimeline
from models.timeline_segment import TimelineSegment


def main() -> None:
    segment_1 = TimelineSegment(
        segment_id="seg_001",
        job_id="job_audio_mix_planner_smoke",
        candidate_id="cand_001",
        start_time=10.0,
        end_time=24.0,
        segment_role="hook",
        selection_score=0.90,
        notes=[],
        source="test",
    )
    segment_2 = TimelineSegment(
        segment_id="seg_002",
        job_id="job_audio_mix_planner_smoke",
        candidate_id="cand_002",
        start_time=50.0,
        end_time=72.0,
        segment_role="peak",
        selection_score=0.93,
        notes=[],
        source="test",
    )

    timeline = EditTimeline(
        timeline_id="timeline_001",
        job_id="job_audio_mix_planner_smoke",
        target_duration=420.0,
        selected_segments=[segment_1, segment_2],
        hook_segment_id=segment_1.segment_id,
        peak_segment_ids=[segment_2.segment_id],
        payoff_segment_id=segment_2.segment_id,
        timeline_score=0.89,
        timeline_notes=[],
    )

    dynamic_plan = DynamicEditPlan(
        plan_id="dynamic_001",
        job_id="job_audio_mix_planner_smoke",
        timeline_id="timeline_001",
        reaction_moments=[],
        zoom_instructions=[],
        pacing_hints=[
            {"segment_id": "seg_001", "hint_kind": "fast_open", "strength": 0.80, "notes": []},
            {"segment_id": "seg_002", "hint_kind": "impact_emphasis", "strength": 0.86, "notes": []},
        ],
        plan_score=0.89,
        plan_notes=[],
    )

    audio_cues = [
        AudioCue(
            cue_id="cue_001",
            job_id="job_audio_mix_planner_smoke",
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
            job_id="job_audio_mix_planner_smoke",
            timeline_id="timeline_001",
            segment_id="seg_002",
            cue_kind="peak_hit",
            start_time=50.0,
            end_time=72.0,
            intensity=0.90,
            priority=0.88,
            notes=[],
        ),
    ]

    instructions = AudioMixPlanner().build_mix_instructions(
        timeline=timeline,
        dynamic_edit_plan=dynamic_plan,
        audio_cues=audio_cues,
    )

    assert len(instructions) == 2
    assert instructions[0].ducking_required is True
    assert instructions[1].music_level >= 0.70
    assert all(instruction.voice_priority >= 0.70 for instruction in instructions)

    print("AUDIO MIX PLANNER SMOKE TEST PASSED")
    print(
        {
            "mix_instructions": len(instructions),
            "music_levels": [instruction.music_level for instruction in instructions],
            "voice_priorities": [instruction.voice_priority for instruction in instructions],
        }
    )


if __name__ == "__main__":
    main()