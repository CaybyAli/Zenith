from __future__ import annotations

from core.zoom_pacing_engine import ZoomPacingEngine
from models.edit_timeline import EditTimeline
from models.framing_instruction import FramingInstruction
from models.job import Job
from models.reaction_moment import ReactionMoment
from models.reframe_plan import ReframePlan
from models.timeline_segment import TimelineSegment
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
        job_id="job_zoom_pacing_engine_smoke",
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

    segment_1 = TimelineSegment(
        segment_id="seg_001",
        job_id=job.job_id,
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
        job_id=job.job_id,
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
        job_id=job.job_id,
        target_duration=420.0,
        selected_segments=[segment_1, segment_2],
        hook_segment_id=segment_1.segment_id,
        peak_segment_ids=[segment_2.segment_id],
        payoff_segment_id=segment_2.segment_id,
        timeline_score=0.89,
        timeline_notes=[],
    )

    reframe_plan = ReframePlan(
        plan_id="reframe_001",
        job_id=job.job_id,
        timeline_id=timeline.timeline_id,
        source_aspect_ratio="32:9",
        primary_target_aspect_ratio="16:9",
        secondary_target_aspect_ratio="9:16",
        instructions=[
            FramingInstruction(
                instruction_id="frame_001",
                job_id=job.job_id,
                timeline_id=timeline.timeline_id,
                segment_id="seg_001",
                focus_kind="facecam",
                layout_kind="facecam_emphasis",
                source_aspect_ratio="32:9",
                target_aspect_ratio="16:9",
                crop_window={"x": 0.02, "y": 0.08, "width": 0.42, "height": 0.84},
                notes=[],
                metadata={"focus_confidence": 0.88},
            ),
            FramingInstruction(
                instruction_id="frame_002",
                job_id=job.job_id,
                timeline_id=timeline.timeline_id,
                segment_id="seg_002",
                focus_kind="gameplay",
                layout_kind="gameplay_crop",
                source_aspect_ratio="32:9",
                target_aspect_ratio="16:9",
                crop_window={"x": 0.18, "y": 0.06, "width": 0.64, "height": 0.88},
                notes=[],
                metadata={"focus_confidence": 0.91},
            ),
        ],
        plan_notes=[],
        plan_score=0.89,
    )

    moments = [
        ReactionMoment(
            moment_id="moment_001",
            job_id=job.job_id,
            timeline_id=timeline.timeline_id,
            segment_id="seg_001",
            start_time=11.0,
            end_time=13.0,
            reaction_kind="hook_reaction",
            intensity=0.88,
            confidence=0.84,
            notes=[],
        ),
        ReactionMoment(
            moment_id="moment_002",
            job_id=job.job_id,
            timeline_id=timeline.timeline_id,
            segment_id="seg_002",
            start_time=54.0,
            end_time=57.0,
            reaction_kind="peak_reaction",
            intensity=0.92,
            confidence=0.87,
            notes=[],
        ),
    ]

    plan = ZoomPacingEngine().build_plan(
        job=job,
        timeline=timeline,
        reframe_plan=reframe_plan,
        reaction_moments=moments,
    )

    assert len(plan.reaction_moments) == 2
    assert len(plan.zoom_instructions) == 2
    assert len(plan.pacing_hints) == 2
    assert plan.zoom_instructions[0].zoom_kind == "hook_push"
    assert plan.zoom_instructions[1].zoom_kind == "punch_in_gameplay"
    assert plan.plan_score >= 0.60

    print("ZOOM PACING ENGINE SMOKE TEST PASSED")
    print(
        {
            "reaction_moments": len(plan.reaction_moments),
            "zoom_kinds": [zoom.zoom_kind for zoom in plan.zoom_instructions],
            "pacing_hints": len(plan.pacing_hints),
            "plan_score": plan.plan_score,
        }
    )


if __name__ == "__main__":
    main()