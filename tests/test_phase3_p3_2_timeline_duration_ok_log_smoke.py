from __future__ import annotations

from types import SimpleNamespace

from models.analysis_result import AnalysisResult
from models.highlight_candidate import HighlightCandidate
from models.job import Job
from core.longform_timeline_builder import LongformTimelineBuilder
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)


def _job() -> Job:
    return Job(
        job_id="job_p3_2_timeline_duration_ok",
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


def _analysis() -> AnalysisResult:
    return AnalysisResult(
        job_id="job_p3_2_timeline_duration_ok",
        duration_seconds=900.0,
        file_size_bytes=123456789,
        usable_for_shorts=True,
        usable_for_longform=True,
        analysis_confidence=0.9,
        notes=["p3-2 duration ok log smoke"],
    )


def _candidate(candidate_id: str, start: float, end: float) -> HighlightCandidate:
    return HighlightCandidate(
        candidate_id=candidate_id,
        job_id="job_p3_2_timeline_duration_ok",
        start_time=start,
        end_time=end,
        highlight_score=0.86,
        candidate_kind="action_peak",
        confidence=0.86,
        signal_tags=["p3_2_duration_ok_log"],
        source="test",
        notes=["synthetic p3-2 duration ok candidate"],
    )


def test_successful_floor_path_logs_selected_after_guards(capsys, monkeypatch) -> None:
    def _keep_round_lifecycle_segments(self, segments, **kwargs):
        duration = round(sum(segment.duration for segment in segments), 3)
        return segments, SimpleNamespace(
            menu_removed=0,
            round_start_shifted=0,
            pre_goal_expanded=0,
            post_goal_extended=0,
            boring_removed=0,
            boring_trimmed=0,
            duration_before=duration,
            duration_after=duration,
            examples=[],
        )

    monkeypatch.setattr(
        "core.longform_timeline_builder.RoundLifecycleGuard.apply",
        _keep_round_lifecycle_segments,
    )

    builder = LongformTimelineBuilder()
    candidates = [
        _candidate(f"p3_2_ok_{index}", index * 11.0, index * 11.0 + 10.0)
        for index in range(50)
    ]

    builder.build(
        job=_job(),
        analysis_result=_analysis(),
        highlight_candidates=candidates,
        weak_zones=[],
    )

    output = capsys.readouterr().out

    assert "[TIMELINE-DURATION-OK]" in output
    assert "[TIMELINE-DURATION-FLOOR-BLOCKED]" not in output
    assert "selected_after_guards=" in output
    assert "floor=480.000s" in output
    assert "primary=" in output
    assert "reserve=" in output
    assert "target=" in output
