from __future__ import annotations

import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.universal_moment_debug_reporter import UniversalMomentDebugReporter
from core.universal_moment_review_exporter import UniversalMomentReviewExporter
from models.timeline_segment import TimelineSegment
from models.universal_moment_debug_report import UniversalMomentDebugReport
from models.universal_moment_result import UniversalMomentResult, UniversalMomentWindow


def segment(segment_id: str, start: float, end: float, role: str = "bridge") -> TimelineSegment:
    return TimelineSegment(
        segment_id=segment_id,
        job_id="job_professional",
        candidate_id=None,
        start_time=start,
        end_time=end,
        segment_role=role,
        selection_score=0.7,
        notes=["universal_test_note"],
        source="test",
    )


def by_id(report: UniversalMomentDebugReport, segment_id: str):
    for debug in report.segments:
        if debug.segment_id == segment_id:
            return debug
    raise AssertionError(f"missing segment debug: {segment_id}")


def build_report() -> UniversalMomentDebugReport:
    segments = [
        segment("speech_mid", 0.0, 10.0),
        segment("speech_edge", 20.0, 30.0),
        segment("action_edge", 40.0, 50.0),
        segment("private_menu", 60.0, 70.0),
        segment("keep_peak", 80.0, 90.0, "peak"),
        segment("boring_wait", 100.0, 110.0),
        segment("mixed", 120.0, 130.0),
    ]
    windows = [
        UniversalMomentWindow(
            window_id="speech_mid_window",
            start_seconds=4.0,
            end_seconds=5.0,
            moment_type="speech_context",
            speech_score=0.68,
            cut_risk_score=0.64,
            speech_boundary_risk=True,
        ),
        UniversalMomentWindow(
            window_id="speech_edge_window",
            start_seconds=19.9,
            end_seconds=20.4,
            moment_type="speech_context",
            speech_score=0.66,
            cut_risk_score=0.72,
            speech_boundary_risk=True,
        ),
        UniversalMomentWindow(
            window_id="action_edge_window",
            start_seconds=48.8,
            end_seconds=49.4,
            moment_type="peak_action",
            peak_score=0.72,
            visual_action_score=0.70,
            action_context_risk=True,
            should_keep=True,
        ),
        UniversalMomentWindow(
            window_id="private_menu_window",
            start_seconds=64.0,
            end_seconds=65.0,
            moment_type="private_menu_talk",
            speech_score=0.64,
            private_talk_score=0.78,
            menu_wait_score=0.74,
            peak_score=0.12,
            menu_private_risk=True,
        ),
        UniversalMomentWindow(
            window_id="keep_peak_window",
            start_seconds=84.0,
            end_seconds=85.0,
            moment_type="peak_action",
            should_keep=True,
            peak_score=0.78,
            tension_score=0.70,
            moment_score=0.80,
        ),
        UniversalMomentWindow(
            window_id="boring_wait_window",
            start_seconds=104.0,
            end_seconds=105.0,
            moment_type="boring_wait",
            should_remove=True,
            boring_score=0.84,
            speech_score=0.20,
            peak_score=0.12,
        ),
        UniversalMomentWindow(
            window_id="mixed_window",
            start_seconds=124.0,
            end_seconds=125.0,
            moment_type="private_menu_talk",
            should_keep=True,
            peak_score=0.72,
            tension_score=0.62,
            private_talk_score=0.80,
            menu_wait_score=0.72,
            menu_private_risk=True,
            moment_score=0.75,
        ),
    ]
    return UniversalMomentDebugReporter().build(
        job_id="job_professional",
        timeline_segments=segments,
        universal_moment_result=UniversalMomentResult(windows=windows),
    )


def main() -> None:
    report = build_report()

    speech_mid = by_id(report, "speech_mid")
    assert speech_mid.raw_cut_risk_windows == 1
    assert not speech_mid.has_cut_risk
    assert not speech_mid.confirmed_cut_risk

    speech_edge = by_id(report, "speech_edge")
    assert speech_edge.has_cut_risk
    assert speech_edge.confirmed_cut_risk_windows == 1
    assert speech_edge.professional_verdict == "review_cut_risk"

    action_edge = by_id(report, "action_edge")
    assert action_edge.has_cut_risk
    assert action_edge.confirmed_cut_risk_windows == 1
    assert any("action context near segment edge" in reason for reason in action_edge.cut_risk_reason)

    private_menu = by_id(report, "private_menu")
    assert private_menu.professional_verdict == "review_private_menu"
    assert "REVIEW_PRIVATE_MENU: likely private menu/wait speech" in private_menu.diagnosis

    keep_peak = by_id(report, "keep_peak")
    assert keep_peak.professional_verdict in {"keep_strong", "keep_context"}
    assert "KEEP_STRONG: peak/tension/reaction content" in keep_peak.diagnosis

    boring_wait = by_id(report, "boring_wait")
    assert boring_wait.professional_verdict == "review_boring"
    assert "REVIEW_BORING: low speech and low action" in boring_wait.diagnosis

    mixed = by_id(report, "mixed")
    assert mixed.professional_verdict == "mixed_conflict"
    assert "MIXED_CONFLICT: keep and remove signals disagree" in mixed.diagnosis

    with tempfile.TemporaryDirectory() as temp_dir:
        review_path = UniversalMomentReviewExporter().write_report(
            report=report,
            output_dir=temp_dir,
        )
        assert review_path.exists()
        markdown = review_path.read_text(encoding="utf-8")
        assert "Segment 01 -- 00:00.00-00:10.00" in markdown
        assert "- Verdict:" in markdown
        assert "- Reason:" in markdown
        assert "- Scores:" in markdown

    roundtrip = UniversalMomentDebugReport.from_dict(report.to_dict())
    assert roundtrip.to_dict() == report.to_dict()

    legacy_payload = report.to_dict()
    for segment_payload in legacy_payload["segments"]:
        segment_payload.pop("professional_verdict", None)
        segment_payload.pop("professional_reason", None)
        segment_payload.pop("confirmed_cut_risk", None)
        segment_payload.pop("raw_cut_risk_windows", None)
        segment_payload.pop("confirmed_cut_risk_windows", None)
        segment_payload.pop("cut_risk_reason", None)
    legacy_roundtrip = UniversalMomentDebugReport.from_dict(legacy_payload)
    assert legacy_roundtrip.total_segments == report.total_segments

    print("UNIVERSAL MOMENT PROFESSIONAL CALIBRATION SMOKE TEST PASSED")


def test_universal_moment_professional_calibration_smoke() -> None:
    main()


if __name__ == "__main__":
    main()
