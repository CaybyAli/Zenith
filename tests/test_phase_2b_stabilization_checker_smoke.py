from __future__ import annotations

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.phase_2b_stabilization_checker import Phase2BStabilizationChecker
from models.phase_2b_final_review import Phase2BFinalReviewReport, Phase2BSegmentReview
from models.phase_2b_stabilization_result import Phase2BStabilizationResult
from models.timeline_segment import TimelineSegment
from models.universal_boundary_evidence import (
    UniversalBoundaryEvidence,
    UniversalBoundaryEvidenceReport,
)


JOB_ID = "job_phase_2b_stabilization"


def _segment(segment_id: str, start: float, end: float) -> TimelineSegment:
    return TimelineSegment(
        segment_id=segment_id,
        job_id=JOB_ID,
        candidate_id=None,
        start_time=start,
        end_time=end,
        segment_role="build",
        selection_score=0.7,
    )


def _timeline(*, overlap: bool = False) -> list[TimelineSegment]:
    second_start = 9.5 if overlap else 10.0
    return [
        _segment("s1", 0.0, 10.0),
        _segment("s2", second_start, 20.0),
    ]


def _final_review(priority: str = "none") -> Phase2BFinalReviewReport:
    return Phase2BFinalReviewReport(
        job_id=JOB_ID,
        segments=[
            Phase2BSegmentReview(
                segment_id="s1",
                index=0,
                start_time=0.0,
                end_time=10.0,
                segment_role="build",
                final_review_status="strong_keep",
                human_review_priority=priority,
            ),
            Phase2BSegmentReview(
                segment_id="s2",
                index=1,
                start_time=10.0,
                end_time=20.0,
                segment_role="build",
                final_review_status="strong_keep",
                human_review_priority=priority,
            ),
        ],
    )


def _boundary_report() -> UniversalBoundaryEvidenceReport:
    return UniversalBoundaryEvidenceReport(
        job_id=JOB_ID,
        boundaries=[
            UniversalBoundaryEvidence(
                boundary_id="b1",
                job_id=JOB_ID,
                boundary_index=1,
                left_segment_id="s1",
                right_segment_id="s2",
                left_end_time=10.0,
                right_start_time=10.0,
                boundary_type="likely_false_positive",
                priority="false_positive",
                speech_boundary_classification="probably_safe",
            )
        ],
    )


def _write_complete_artifacts(directory: Path) -> Path:
    for filename in (
        "universal_moment_debug.json",
        "universal_moment_soft_decision.json",
        "universal_role_decision_audit.json",
        "universal_context_audit.json",
        "universal_boundary_evidence.json",
        "phase_2b_final_review.json",
    ):
        (directory / filename).write_text("{}", encoding="utf-8")
    (directory / "universal_moment_review.md").write_text("# Review\n", encoding="utf-8")
    render_path = directory / f"{JOB_ID}_v1_final.mp4"
    render_path.write_bytes(b"fake mp4")
    return render_path


def _check(
    directory: Path,
    *,
    timeline=None,
    final_review=None,
    boundary_report=None,
    validator_result=None,
    render_path: Path | None = None,
) -> Phase2BStabilizationResult:
    return Phase2BStabilizationChecker().check(
        job_id=JOB_ID,
        job_dir=directory,
        export_dir=directory,
        timeline_segments=_timeline() if timeline is None else timeline,
        final_review_report=_final_review() if final_review is None else final_review,
        boundary_evidence_report=_boundary_report() if boundary_report is None else boundary_report,
        validator_result=(
            {"validator_status": "passed", "blocking_issues": [], "reason": ""}
            if validator_result is None
            else validator_result
        ),
        render_path=render_path,
    )


def test_empty_missing_artifacts_fail() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        result = Phase2BStabilizationChecker().check(
            job_id=JOB_ID,
            export_dir=tmp,
            timeline_segments=[],
        )
    assert result.status == "failed"
    assert not result.phase_2b_ready_to_close


def test_complete_artifacts_render_export_pass() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        render_path = _write_complete_artifacts(directory)
        result = _check(directory, render_path=render_path)
    assert result.status in {"passed", "passed_with_known_warnings"}
    assert result.phase_2b_ready_to_close
    assert result.render_exists
    assert result.export_exists


def test_missing_thumbnail_validator_is_known_warning() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        render_path = _write_complete_artifacts(directory)
        result = _check(
            directory,
            validator_result={
                "validator_status": "failed",
                "blocking_issues": ["Missing thumbnail"],
                "reason": "Missing thumbnail",
            },
            render_path=render_path,
        )
    assert result.status == "passed_with_known_warnings"
    assert result.validator_failed_only_thumbnail
    assert result.missing_thumbnail_known_warning


def test_validator_other_failure_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        render_path = _write_complete_artifacts(directory)
        result = _check(
            directory,
            validator_result={
                "validator_status": "failed",
                "blocking_issues": ["Missing title"],
                "reason": "Missing title",
            },
            render_path=render_path,
        )
    assert result.status == "failed"
    assert not result.phase_2b_ready_to_close


def test_timeline_overlap_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        render_path = _write_complete_artifacts(directory)
        result = _check(directory, timeline=_timeline(overlap=True), render_path=render_path)
    assert result.status == "failed"
    assert not result.timeline_exists


def test_high_priority_final_review_is_known_warning_not_failure() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        render_path = _write_complete_artifacts(directory)
        result = _check(directory, final_review=_final_review("high"), render_path=render_path)
    assert result.status == "passed_with_known_warnings"
    assert result.phase_2b_ready_to_close
    assert result.high_boundary_review_warning


def test_to_dict_from_dict_roundtrip() -> None:
    result = Phase2BStabilizationResult(
        job_id=JOB_ID,
        status="passed_with_known_warnings",
        phase_2b_ready_to_close=True,
        known_open_items=["Missing thumbnail"],
        notes=["ok"],
    )
    assert Phase2BStabilizationResult.from_dict(result.to_dict()).to_dict() == result.to_dict()


def test_markdown_contains_stabilization_status() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        render_path = _write_complete_artifacts(directory)
        result = _check(directory, render_path=render_path)
        path = Phase2BStabilizationChecker().write_markdown(
            result=result,
            output_dir=directory,
        )
        text = path.read_text(encoding="utf-8")
    assert "# Phase 2.B Stabilization" in text
    assert "Ready to Close" in text


def main() -> None:
    test_empty_missing_artifacts_fail()
    test_complete_artifacts_render_export_pass()
    test_missing_thumbnail_validator_is_known_warning()
    test_validator_other_failure_fails()
    test_timeline_overlap_fails()
    test_high_priority_final_review_is_known_warning_not_failure()
    test_to_dict_from_dict_roundtrip()
    test_markdown_contains_stabilization_status()
    print("PHASE 2B STABILIZATION CHECKER SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
