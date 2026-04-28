from __future__ import annotations

from core.final_edit_integration import FinalEditIntegration
from models.audio_cue import AudioCue
from models.audio_mix_instruction import AudioMixInstruction
from models.dynamic_edit_plan import DynamicEditPlan
from models.edit_timeline import EditTimeline
from models.framing_instruction import FramingInstruction
from models.music_cue_plan import MusicCuePlan
from models.reaction_moment import ReactionMoment
from models.reframe_plan import ReframePlan
from models.timeline_segment import TimelineSegment
from models.zoom_instruction import ZoomInstruction


def main() -> None:
    segment = TimelineSegment(
        segment_id="seg_001",
        job_id="job_final_edit_integration_smoke",
        candidate_id="cand_001",
        start_time=10.0,
        end_time=24.0,
        segment_role="hook",
        selection_score=0.90,
        notes=[],
        source="test",
    )

    timeline = EditTimeline(
        timeline_id="timeline_001",
        job_id="job_final_edit_integration_smoke",
        target_duration=420.0,
        selected_segments=[segment],
        hook_segment_id=segment.segment_id,
        peak_segment_ids=[],
        payoff_segment_id=segment.segment_id,
        timeline_score=0.89,
        timeline_notes=[],
    )

    reframe_plan = ReframePlan(
        plan_id="reframe_001",
        job_id="job_final_edit_integration_smoke",
        timeline_id=timeline.timeline_id,
        source_aspect_ratio="32:9",
        primary_target_aspect_ratio="16:9",
        secondary_target_aspect_ratio="9:16",
        instructions=[
            FramingInstruction(
                instruction_id="frame_001",
                job_id="job_final_edit_integration_smoke",
                timeline_id=timeline.timeline_id,
                segment_id=segment.segment_id,
                focus_kind="facecam",
                layout_kind="facecam_emphasis",
                source_aspect_ratio="32:9",
                target_aspect_ratio="16:9",
                crop_window={"x": 0.02, "y": 0.08, "width": 0.42, "height": 0.84},
                notes=[],
                metadata={"focus_confidence": 0.88},
            )
        ],
        plan_notes=[],
        plan_score=0.78,
    )

    dynamic_plan = DynamicEditPlan(
        plan_id="dynamic_001",
        job_id="job_final_edit_integration_smoke",
        timeline_id=timeline.timeline_id,
        reaction_moments=[
            ReactionMoment(
                moment_id="moment_001",
                job_id="job_final_edit_integration_smoke",
                timeline_id=timeline.timeline_id,
                segment_id=segment.segment_id,
                start_time=11.0,
                end_time=13.0,
                reaction_kind="hook_reaction",
                intensity=0.88,
                confidence=0.84,
                notes=[],
            )
        ],
        zoom_instructions=[
            ZoomInstruction(
                instruction_id="zoom_001",
                job_id="job_final_edit_integration_smoke",
                timeline_id=timeline.timeline_id,
                segment_id=segment.segment_id,
                moment_id="moment_001",
                zoom_kind="hook_push",
                focus_kind="facecam",
                intensity=0.86,
                start_time=11.0,
                end_time=13.0,
                notes=[],
            )
        ],
        pacing_hints=[
            {"segment_id": segment.segment_id, "hint_kind": "fast_open", "strength": 0.80, "notes": []}
        ],
        plan_score=0.88,
        plan_notes=[],
    )

    music_cue_plan = MusicCuePlan(
        plan_id="music_001",
        job_id="job_final_edit_integration_smoke",
        timeline_id=timeline.timeline_id,
        audio_cues=[
            AudioCue(
                cue_id="cue_001",
                job_id="job_final_edit_integration_smoke",
                timeline_id=timeline.timeline_id,
                segment_id=segment.segment_id,
                cue_kind="intro_bed",
                start_time=10.0,
                end_time=24.0,
                intensity=0.83,
                priority=0.85,
                notes=[],
            )
        ],
        audio_mix_instructions=[
            AudioMixInstruction(
                instruction_id="mix_001",
                segment_id=segment.segment_id,
                voice_priority=0.90,
                music_level=0.42,
                ducking_required=True,
                notes=[],
            )
        ],
        plan_score=0.84,
        notes=[],
    )

    package = FinalEditIntegration().build(
        timeline=timeline,
        reframe_plan=reframe_plan,
        dynamic_edit_plan=dynamic_plan,
        music_cue_plan=music_cue_plan,
    )

    assert package["selected_segments"] == 1
    assert package["reframe_instructions"] == 1
    assert package["reaction_moments"] == 1
    assert package["zoom_instructions"] == 1
    assert package["audio_cues"] == 1
    assert package["audio_mix_instructions"] == 1
    assert package["integration_score"] >= 0.70

    print("FINAL EDIT INTEGRATION SMOKE TEST PASSED")
    print(package)


if __name__ == "__main__":
    main()