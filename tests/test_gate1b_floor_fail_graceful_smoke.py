from __future__ import annotations
from pathlib import Path

from types import SimpleNamespace

import pipeline_runner
from core.longform_timeline_builder import LongformTimelineBuilder, YOUTUBE_MIN_DURATION
from models.timeline_segment import TimelineSegment
from shared.enums import JobStatus, ValidatorStatus
from shared.errors import ValidationError


def _job() -> SimpleNamespace:
    return SimpleNamespace(
        job_id="job_gate1b_floor_fail",
        status=JobStatus.PROCESSING,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        error_message=None,
        debug_context={},
        raw_video_path="learning_corpus/pairs/pair_001/raw.mp4",
        touch=lambda: None,
    )


def _seg(segment_id: str, start: float, end: float) -> TimelineSegment:
    return TimelineSegment(
        segment_id=segment_id,
        job_id="job_gate1b_floor_fail",
        candidate_id=segment_id,
        start_time=start,
        end_time=end,
        segment_role="peak",
        selection_score=0.9,
        notes=["test_floor_fail_segment"],
    )


def test_longform_floor_fail_diagnostics_are_written_to_debug_context() -> None:
    job = _job()
    builder = LongformTimelineBuilder()
    segments = [
        _seg("seg_a", 0.0, 240.0),
        _seg("seg_b", 300.0, 523.746),
    ]

    builder._write_floor_fail_diagnostics(
        job=job,
        reason="floor_unreachable_after_guards",
        selected_before_guards=484.0,
        selected_after_guards=463.746,
        duration_floor=YOUTUBE_MIN_DURATION,
        target_duration=590.308,
        primary_count=7,
        reserve_count=197,
        selected_segments=segments,
        duration_ledger=[
            {
                "guard": "TIMELINE-ROUND-WAIT-GUARD",
                "before": 659.508,
                "after": 192.889,
                "delta": -466.619,
            }
        ],
    )

    diag = job.debug_context["longform_floor_fail"]

    assert diag["reason"] == "floor_unreachable_after_guards"
    assert diag["selected_before_guards"] == 484.0
    assert diag["selected_after_guards"] == 463.746
    assert diag["floor"] == 480.0
    assert diag["missing_seconds"] == 16.254
    assert diag["render_blocked"] is True
    assert diag["status"] == "controlled_no_go"
    assert diag["duration_ledger"][0]["guard"] == "TIMELINE-ROUND-WAIT-GUARD"
    assert diag["selected_timeline"][0]["segment_id"] == "seg_a"


def test_pipeline_runner_marks_floor_fail_validation_failed_not_crashed() -> None:
    job = _job()
    job.debug_context["longform_floor_fail"] = {
        "reason": "floor_unreachable_after_guards",
        "selected_after_guards": 463.746,
        "floor": 480.0,
        "missing_seconds": 16.254,
        "render_blocked": True,
        "status": "controlled_no_go",
    }

    exc = ValidationError(
        "Longform floor 480s unreachable: only 464s of usable material after guards"
    )

    pipeline_runner._apply_dispatch_exception_to_job(job, exc)

    assert job.status == JobStatus.VALIDATION_FAILED
    assert job.validator_status == ValidatorStatus.FAILED
    assert job.error_message.startswith("floor_unreachable:")
    assert job.debug_context["longform_floor_fail"]["render_blocked"] is True
    assert job.debug_context["longform_floor_fail"]["pipeline_status"] == "validation_failed"
    assert pipeline_runner.classify_job_status_for_runner(job.status) == "error"


def test_non_floor_exception_still_crashes() -> None:
    job = _job()
    exc = RuntimeError("real unexpected crash")

    pipeline_runner._apply_dispatch_exception_to_job(job, exc)

    assert job.status == JobStatus.CRASHED
    assert job.error_message == "real unexpected crash"

def test_floor_fail_diagnostics_include_lock_metric_fields_with_not_available_defaults() -> None:
    job = _job()
    segment = _seg("seg_lock_metric", 0.0, 463.746)

    builder = LongformTimelineBuilder()
    builder._write_floor_fail_diagnostics(
        job=job,
        reason="floor_unreachable_after_guards",
        selected_before_guards=484.0,
        selected_after_guards=463.746,
        duration_floor=YOUTUBE_MIN_DURATION,
        target_duration=590.308,
        primary_count=7,
        reserve_count=197,
        selected_segments=[segment],
        duration_ledger=[],
    )

    diag = job.debug_context["longform_floor_fail"]

    assert diag["status"] == "controlled_no_go"
    assert diag["reason"] == "floor_unreachable_after_guards"
    assert diag["render_blocked"] is True
    assert diag["floor"] == 480.0
    assert diag["selected_before_guards"] == 484.0
    assert diag["selected_after_guards"] == 463.746
    assert diag["missing_seconds"] == 16.254

    assert "removed_speech_seconds" in diag
    assert "removed_speech_source" in diag
    assert "boundary_hits_count" in diag
    assert "boundary_hits_source" in diag
    assert "overlap_count" in diag
    assert "timeline_safety_overlap_count" in diag

    assert diag["removed_speech_seconds"] is None
    assert diag["removed_speech_source"] == "not_available"
    assert diag["boundary_hits_count"] is None
    assert diag["boundary_hits_source"] == "not_available"
    assert diag["overlap_count"] is None
    assert diag["timeline_safety_overlap_count"] is None


def test_floor_fail_diagnostics_persist_explicit_lock_metrics_when_provided() -> None:
    job = _job()
    segment = _seg("seg_lock_metric", 0.0, 463.746)

    builder = LongformTimelineBuilder()
    builder._write_floor_fail_diagnostics(
        job=job,
        reason="floor_unreachable_after_guards",
        selected_before_guards=484.0,
        selected_after_guards=463.746,
        duration_floor=YOUTUBE_MIN_DURATION,
        target_duration=590.308,
        primary_count=7,
        reserve_count=197,
        selected_segments=[segment],
        duration_ledger=[],
        lock_metrics={
            "removed_speech_seconds": 1.234,
            "removed_speech_source": "test_lock_metric",
            "boundary_hits_count": 2,
            "boundary_hits_source": "test_boundary_metric",
            "overlap_count": 0,
            "timeline_safety_overlap_count": 0,
        },
    )

    diag = job.debug_context["longform_floor_fail"]

    assert diag["removed_speech_seconds"] == 1.234
    assert diag["removed_speech_source"] == "test_lock_metric"
    assert diag["boundary_hits_count"] == 2
    assert diag["boundary_hits_source"] == "test_boundary_metric"
    assert diag["overlap_count"] == 0
    assert diag["timeline_safety_overlap_count"] == 0

def test_early_floor_fail_diagnostics_include_lock_metric_defaults() -> None:
    job = _job()
    segment = _seg("seg_early_floor", 0.0, 376.5)

    builder = LongformTimelineBuilder()
    builder._write_floor_fail_diagnostics(
        job=job,
        reason="floor_unreachable_before_guards",
        selected_before_guards=None,
        selected_after_guards=376.5,
        duration_floor=YOUTUBE_MIN_DURATION,
        target_duration=975.233,
        primary_count=2,
        reserve_count=63,
        selected_segments=[segment],
        duration_ledger=[],
    )

    diag = job.debug_context["longform_floor_fail"]

    assert diag["status"] == "controlled_no_go"
    assert diag["reason"] == "floor_unreachable_before_guards"
    assert diag["render_blocked"] is True
    assert diag["selected_before_guards"] is None
    assert diag["selected_after_guards"] == 376.5
    assert diag["floor"] == 480.0
    assert diag["missing_seconds"] == 103.5
    assert diag["primary_count"] == 2
    assert diag["reserve_count"] == 63
    assert diag["removed_speech_seconds"] is None
    assert diag["removed_speech_source"] == "not_available"
    assert diag["boundary_hits_count"] is None
    assert diag["boundary_hits_source"] == "not_available"
    assert diag["overlap_count"] is None
    assert diag["timeline_safety_overlap_count"] is None

def test_early_floor_fail_build_path_writes_diagnostics_before_raise() -> None:
    source = Path("core/longform_timeline_builder.py").read_text(encoding="utf-8")

    start = source.index(
        "        if self._below_duration_floor(selected_items_duration, duration_floor):"
    )
    end = source.index(
        "        peak_index = self._resolve_peak_index(selected_items)",
        start,
    )
    block = source[start:end]

    assert "self._write_floor_fail_diagnostics(" in block
    assert 'reason="floor_unreachable_before_guards"' in block
    assert "selected_before_guards=None" in block
    assert "selected_after_guards=selected_items_duration" in block
