from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.universal_moment_debug_reporter import UniversalMomentDebugReporter
from models.timeline_segment import TimelineSegment
from models.universal_moment_debug_report import UniversalMomentDebugReport
from models.universal_moment_result import UniversalMomentResult, UniversalMomentWindow


SCORE_FIELDS = (
    "avg_moment_score",
    "max_moment_score",
    "avg_keep_score",
    "avg_remove_score",
    "avg_cut_risk_score",
    "avg_zoom_risk_score",
    "avg_private_talk_score",
    "avg_boring_score",
    "avg_peak_score",
    "avg_tension_score",
    "avg_post_reaction_score",
)


def segment(segment_id: str, start: float, end: float, role: str = "bridge") -> TimelineSegment:
    return TimelineSegment(
        segment_id=segment_id,
        job_id="job_debug",
        candidate_id=None,
        start_time=start,
        end_time=end,
        segment_role=role,
        selection_score=0.7,
        notes=["guard_note", "universal_existing_note"],
        source="test",
    )


def build_report(
    segments: list[TimelineSegment],
    windows: list[UniversalMomentWindow] | None = None,
) -> UniversalMomentDebugReport:
    return UniversalMomentDebugReporter().build(
        job_id="job_debug",
        timeline_segments=segments,
        universal_moment_result=UniversalMomentResult(windows=windows or []),
    )


def by_id(report: UniversalMomentDebugReport, segment_id: str):
    for debug in report.segments:
        if debug.segment_id == segment_id:
            return debug
    raise AssertionError(f"missing segment debug: {segment_id}")


def assert_scores_clamped(report: UniversalMomentDebugReport) -> None:
    assert 0.0 <= report.avg_segment_moment_score <= 1.0
    for debug in report.segments:
        for field in SCORE_FIELDS:
            value = getattr(debug, field)
            assert 0.0 <= value <= 1.0, f"{debug.segment_id}.{field}={value}"


def main() -> None:
    empty_report = build_report([], [])
    assert empty_report.total_segments == 0
    assert empty_report.avg_segment_moment_score == 0.0

    no_window_report = build_report([segment("empty", 0.0, 4.0)], [])
    empty_debug = by_id(no_window_report, "empty")
    assert empty_debug.overlapping_windows == 0
    assert empty_debug.dominant_moment_type == "unknown"
    assert empty_debug.top_moment_types == {}
    assert "NO-SIGNAL: no overlapping universal moment windows" in empty_debug.diagnosis

    windows = [
        UniversalMomentWindow(
            window_id="peak_1",
            start_seconds=11.0,
            end_seconds=12.0,
            moment_type="peak_action",
            should_keep=True,
            peak_score=0.91,
            moment_score=0.86,
            source_notes=["goal flash"],
            source_signals=["goal_or_save_like_flash"],
        ),
        UniversalMomentWindow(
            window_id="peak_2",
            start_seconds=13.0,
            end_seconds=14.0,
            moment_type="peak_action",
            tension_score=0.72,
            moment_score=0.64,
        ),
        UniversalMomentWindow(
            window_id="speech",
            start_seconds=15.0,
            end_seconds=16.0,
            moment_type="speech_context",
            speech_score=0.66,
            moment_score=0.28,
        ),
        UniversalMomentWindow(
            window_id="boring",
            start_seconds=31.0,
            end_seconds=32.0,
            moment_type="boring_wait",
            should_remove=True,
            boring_score=1.2,
            menu_wait_score=0.81,
            dead_time_score=0.74,
            moment_score=-1.0,
        ),
        UniversalMomentWindow(
            window_id="cut",
            start_seconds=41.0,
            end_seconds=42.0,
            moment_type="cut_risk",
            cut_risk_score=0.83,
            speech_boundary_risk=True,
        ),
        UniversalMomentWindow(
            window_id="zoom",
            start_seconds=51.0,
            end_seconds=52.0,
            moment_type="zoom_risk",
            zoom_risk_score=0.79,
            zoom_boundary_risk=True,
        ),
        UniversalMomentWindow(
            window_id="private",
            start_seconds=61.0,
            end_seconds=62.0,
            moment_type="private_menu_talk",
            private_talk_score=0.82,
            menu_private_risk=True,
        ),
        UniversalMomentWindow(
            window_id="context",
            start_seconds=71.0,
            end_seconds=72.0,
            moment_type="pre_action_tension",
            needs_pre_context=True,
            needs_post_context=True,
            pre_action_score=0.72,
            tension_score=0.7,
            post_peak_reaction_score=0.74,
            moment_score=0.76,
        ),
    ]

    report = build_report(
        [
            segment("peak", 10.0, 20.0, "peak"),
            segment("boring", 30.0, 35.0),
            segment("cut", 40.0, 45.0),
            segment("zoom", 50.0, 55.0),
            segment("private", 60.0, 65.0),
            segment("context", 70.0, 75.0),
        ],
        windows,
    )

    peak_debug = by_id(report, "peak")
    assert peak_debug.has_keep_signal
    assert peak_debug.dominant_moment_type == "peak_action"
    assert peak_debug.top_moment_types["peak_action"] == 2
    assert peak_debug.top_moment_types["speech_context"] == 1
    assert "KEEP: peak/tension signal detected" in peak_debug.diagnosis
    assert "universal_existing_note" in peak_debug.universal_notes
    assert any("goal flash" in note for note in peak_debug.universal_notes)

    boring_debug = by_id(report, "boring")
    assert boring_debug.has_remove_signal
    assert "REMOVE-CANDIDATE: boring/menu/dead-time signal" in boring_debug.diagnosis

    cut_debug = by_id(report, "cut")
    assert cut_debug.has_cut_risk
    assert "RISK: cut boundary may hit speech/action" in cut_debug.diagnosis

    zoom_debug = by_id(report, "zoom")
    assert zoom_debug.has_zoom_risk
    assert "RISK: zoom boundary risk" in zoom_debug.diagnosis

    private_debug = by_id(report, "private")
    assert private_debug.has_private_menu_risk
    assert "PRIVATE: menu speech/private talk risk" in private_debug.diagnosis

    context_debug = by_id(report, "context")
    assert context_debug.has_pre_context_need
    assert context_debug.has_post_context_need
    assert "CONTEXT: needs pre-action context" in context_debug.diagnosis
    assert "CONTEXT: needs post-peak reaction" in context_debug.diagnosis

    roundtrip = UniversalMomentDebugReport.from_dict(report.to_dict())
    assert roundtrip.to_dict() == report.to_dict()

    assert report.total_segments == 6
    assert report.segments_with_keep_signal >= 2
    assert report.segments_with_remove_signal == 1
    assert report.segments_with_cut_risk == 1
    assert report.segments_with_zoom_risk == 1
    assert report.segments_with_private_risk == 1
    assert_scores_clamped(report)
    assert_scores_clamped(roundtrip)

    print("UNIVERSAL MOMENT DEBUG REPORTER SMOKE TEST PASSED")


def test_universal_moment_debug_reporter_smoke() -> None:
    main()


if __name__ == "__main__":
    main()
