from __future__ import annotations

from core.longform_timeline_builder import LongformTimelineBuilder
from models.analysis_result import AnalysisResult
from models.highlight_candidate import HighlightCandidate
from models.job import Job
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
        job_id="job_longform_timeline_builder_smoke",
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

    analysis_result = AnalysisResult(
        job_id=job.job_id,
        duration_seconds=720.0,
        file_size_bytes=123456789,
        usable_for_shorts=True,
        usable_for_longform=True,
        analysis_confidence=0.86,
        notes=["longform timeline builder smoke"],
    )

    highlight_candidates = [
        HighlightCandidate(
            candidate_id="cand_001",
            job_id=job.job_id,
            start_time=12.0,
            end_time=38.0,
            highlight_score=0.82,
            candidate_kind="speech_peak",
            confidence=0.81,
            signal_tags=["intro_zone", "early_section"],
            source="test",
            notes=["good opener"],
        ),
        HighlightCandidate(
            candidate_id="cand_002",
            job_id=job.job_id,
            start_time=60.0,
            end_time=92.0,
            highlight_score=0.91,
            candidate_kind="action_peak",
            confidence=0.87,
            signal_tags=["middle_section"],
            source="test",
            notes=["strong action"],
        ),
        HighlightCandidate(
            candidate_id="cand_003",
            job_id=job.job_id,
            start_time=95.0,
            end_time=120.0,
            highlight_score=0.89,
            candidate_kind="action_peak",
            confidence=0.84,
            signal_tags=["middle_section"],
            source="test",
            notes=["should be penalized by weak zone"],
        ),
        HighlightCandidate(
            candidate_id="cand_004",
            job_id=job.job_id,
            start_time=180.0,
            end_time=220.0,
            highlight_score=0.84,
            candidate_kind="action_peak",
            confidence=0.80,
            signal_tags=["middle_section"],
            source="test",
            notes=["mid video peak"],
        ),
        HighlightCandidate(
            candidate_id="cand_005",
            job_id=job.job_id,
            start_time=320.0,
            end_time=350.0,
            highlight_score=0.80,
            candidate_kind="speech_peak",
            confidence=0.78,
            signal_tags=["late_section"],
            source="test",
            notes=["late payoff candidate"],
        ),
    ]

    weak_zones = [
        HighlightCandidate(
            candidate_id="weak_001",
            job_id=job.job_id,
            start_time=94.0,
            end_time=118.0,
            highlight_score=0.72,
            candidate_kind="drop_zone",
            confidence=0.79,
            signal_tags=["middle_section"],
            source="test",
            notes=["low energy zone"],
        )
    ]

    timeline = LongformTimelineBuilder().build(
        job=job,
        analysis_result=analysis_result,
        highlight_candidates=highlight_candidates,
        weak_zones=weak_zones,
    )

    selected_candidate_ids = [segment.candidate_id for segment in timeline.selected_segments]
    selected_roles = [segment.segment_role for segment in timeline.selected_segments]
    selected_start_times = [segment.start_time for segment in timeline.selected_segments]

    assert len(timeline.selected_segments) >= 3
    assert "cand_003" not in selected_candidate_ids
    assert selected_start_times == sorted(selected_start_times)
    assert selected_roles[0] == "hook"
    assert timeline.payoff_segment_id == timeline.selected_segments[-1].segment_id
    assert timeline.timeline_score >= 0.45

    if len(timeline.selected_segments) >= 3:
        assert len(timeline.peak_segment_ids) >= 1

    print("LONGFORM TIMELINE BUILDER SMOKE TEST PASSED")
    print(
        {
            "selected_segments": len(timeline.selected_segments),
            "candidate_ids": selected_candidate_ids,
            "roles": selected_roles,
            "timeline_score": timeline.timeline_score,
            "target_duration": timeline.target_duration,
        }
    )


if __name__ == "__main__":
    main()