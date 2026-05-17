from __future__ import annotations

from core.reframing_core import ReframingCore
from models.edit_timeline import EditTimeline
from models.highlight_candidate import HighlightCandidate
from models.job import Job
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
        job_id="job_reframing_core_smoke",
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
        end_time=28.0,
        segment_role="hook",
        selection_score=0.90,
        notes=[],
        source="test",
    )
    segment_2 = TimelineSegment(
        segment_id="seg_002",
        job_id=job.job_id,
        candidate_id="cand_002",
        start_time=60.0,
        end_time=88.0,
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
        timeline_notes=["reframing core smoke"],
    )

    candidates = [
        HighlightCandidate(
            candidate_id="cand_001",
            job_id=job.job_id,
            start_time=10.0,
            end_time=28.0,
            highlight_score=0.86,
            candidate_kind="speech_peak",
            confidence=0.80,
            signal_tags=["intro_zone"],
            source="test",
            notes=[],
        ),
        HighlightCandidate(
            candidate_id="cand_002",
            job_id=job.job_id,
            start_time=60.0,
            end_time=88.0,
            highlight_score=0.92,
            candidate_kind="action_peak",
            confidence=0.87,
            signal_tags=["middle_section"],
            source="test",
            notes=[],
        ),
    ]

    plan = ReframingCore().build_plan(
        job=job,
        timeline=timeline,
        highlight_candidates=candidates,
        source_aspect_ratio="32:9",
        primary_target_aspect_ratio="16:9",
        secondary_target_aspect_ratio="9:16",
    )

    assert len(plan.instructions) == 2
    assert plan.instructions[0].focus_kind == "facecam"
    assert plan.instructions[1].focus_kind == "gameplay"
    assert plan.instructions[0].layout_kind in {"facecam_emphasis", "balanced_split"}
    assert plan.instructions[1].layout_kind in {"gameplay_crop", "balanced_split"}
    assert plan.instructions[0].metadata["secondary_target_aspect_ratio"] == "9:16"
    assert "secondary_crop_window" in plan.instructions[0].metadata
    assert plan.plan_score >= 0.60

    print("REFRAMING CORE SMOKE TEST PASSED")
    print(
        {
            "instructions": len(plan.instructions),
            "focus_kinds": [instruction.focus_kind for instruction in plan.instructions],
            "layout_kinds": [instruction.layout_kind for instruction in plan.instructions],
            "plan_score": plan.plan_score,
        }
    )


if __name__ == "__main__":
    main()