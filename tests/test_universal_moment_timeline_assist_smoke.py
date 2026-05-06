from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.universal_moment_timeline_assist import UniversalMomentTimelineAssist
from models.timeline_segment import TimelineSegment
from models.universal_moment_result import UniversalMomentResult, UniversalMomentWindow


def segment(segment_id: str, start: float, end: float, role: str = "bridge") -> TimelineSegment:
    return TimelineSegment(
        segment_id=segment_id,
        job_id="job_test",
        candidate_id=None,
        start_time=start,
        end_time=end,
        segment_role=role,
        selection_score=0.7,
        source="test",
    )


def apply_assist(
    segments: list[TimelineSegment],
    windows: list[UniversalMomentWindow] | None = None,
):
    return UniversalMomentTimelineAssist().apply(
        segments,
        universal_moment_result=UniversalMomentResult(windows=windows or []),
    )


def assert_invariants(segments: list[TimelineSegment]) -> None:
    previous_end = -1.0
    for current in segments:
        assert current.end_time > current.start_time
        assert current.duration >= 2.5
        assert current.start_time >= previous_end
        previous_end = current.end_time


def main() -> None:
    empty_segments = [segment("empty", 10.0, 15.0)]
    empty_result, empty_summary = apply_assist(empty_segments, [])
    assert len(empty_result) == 1
    assert empty_summary.keep_protected == 0
    assert empty_result[0].start_time == 10.0
    assert empty_result[0].end_time == 15.0

    keep_segments, keep_summary = apply_assist(
        [segment("keep", 10.0, 15.0)],
        [
            UniversalMomentWindow(
                window_id="peak",
                start_seconds=11.0,
                end_seconds=12.0,
                should_keep=True,
                peak_score=0.82,
                moment_score=0.82,
            )
        ],
    )
    assert keep_summary.keep_protected == 1
    assert "universal_keep_protected" in keep_segments[0].notes

    pre_segments, pre_summary = apply_assist(
        [segment("pre", 10.0, 15.0)],
        [
            UniversalMomentWindow(
                window_id="pre_action",
                start_seconds=7.0,
                end_seconds=10.2,
                needs_pre_context=True,
                pre_action_score=0.72,
                tension_score=0.66,
            )
        ],
    )
    assert pre_summary.pre_context_protected == 1
    assert pre_segments[0].start_time == 9.0
    assert pre_segments[0].end_time == 15.0
    assert any(note.startswith("universal_pre_context=") for note in pre_segments[0].notes)

    post_segments, post_summary = apply_assist(
        [segment("post", 20.0, 25.0)],
        [
            UniversalMomentWindow(
                window_id="post_peak",
                start_seconds=24.6,
                end_seconds=28.0,
                needs_post_context=True,
                post_peak_reaction_score=0.74,
                reaction_score=0.72,
            )
        ],
    )
    assert post_summary.post_context_protected == 1
    assert post_segments[0].start_time == 20.0
    assert post_segments[0].end_time == 26.0
    assert any(note.startswith("universal_post_context=") for note in post_segments[0].notes)

    cut_segments, cut_summary = apply_assist(
        [segment("cut", 30.0, 35.0)],
        [
            UniversalMomentWindow(
                window_id="cut_risk",
                start_seconds=31.0,
                end_seconds=32.0,
                cut_risk_score=0.82,
                speech_boundary_risk=True,
            )
        ],
    )
    assert cut_summary.cut_risk_protected == 1
    assert "universal_cut_risk_protected" in cut_segments[0].notes

    zoom_segments, zoom_summary = apply_assist(
        [segment("zoom", 40.0, 45.0)],
        [
            UniversalMomentWindow(
                window_id="zoom_risk",
                start_seconds=41.0,
                end_seconds=42.0,
                zoom_risk_score=0.76,
                zoom_boundary_risk=True,
            )
        ],
    )
    assert zoom_summary.zoom_risk_marked == 1
    assert "universal_zoom_risk" in zoom_segments[0].notes

    remove_segments, remove_summary = apply_assist(
        [segment("remove", 50.0, 55.0)],
        [
            UniversalMomentWindow(
                window_id="boring",
                start_seconds=51.0,
                end_seconds=52.0,
                should_remove=True,
                boring_score=0.88,
                menu_wait_score=0.74,
                peak_score=0.1,
                speech_score=0.1,
            )
        ],
    )
    assert len(remove_segments) == 1
    assert remove_summary.remove_supported == 1
    assert remove_summary.boring_trim_suggested == 1
    assert "universal_remove_supported" in remove_segments[0].notes

    private_segments, private_summary = apply_assist(
        [segment("private", 60.0, 65.0)],
        [
            UniversalMomentWindow(
                window_id="private_menu",
                start_seconds=61.0,
                end_seconds=62.0,
                moment_type="private_menu_talk",
                private_talk_score=0.8,
                menu_private_risk=True,
            )
        ],
    )
    assert len(private_segments) == 1
    assert private_summary.private_menu_supported == 1
    assert "universal_private_menu_supported" in private_segments[0].notes

    overlap_guard_segments, overlap_guard_summary = apply_assist(
        [segment("prev", 0.0, 9.6), segment("blocked_pre", 10.0, 15.0)],
        [
            UniversalMomentWindow(
                window_id="blocked_pre",
                start_seconds=8.0,
                end_seconds=10.2,
                needs_pre_context=True,
                pre_action_score=0.8,
            )
        ],
    )
    assert overlap_guard_summary.pre_context_protected == 1
    assert overlap_guard_segments[1].start_time == 9.6
    assert_invariants(overlap_guard_segments)

    first_context_segments, first_context_summary = apply_assist(
        [segment("first30", 2.0, 8.0, "hook")],
        [
            UniversalMomentWindow(
                window_id="first30_pre",
                start_seconds=0.0,
                end_seconds=2.2,
                needs_pre_context=True,
                pre_action_score=0.72,
                tension_score=0.62,
            )
        ],
    )
    assert first_context_summary.pre_context_protected == 1
    assert first_context_segments[0].start_time == 1.0
    assert first_context_segments[0].end_time == 8.0
    assert "universal_first_30s_protected" in first_context_segments[0].notes
    assert_invariants(first_context_segments)

    for checked in [
        empty_result,
        keep_segments,
        pre_segments,
        post_segments,
        cut_segments,
        zoom_segments,
        remove_segments,
        private_segments,
        overlap_guard_segments,
        first_context_segments,
    ]:
        assert_invariants(checked)

    print("UNIVERSAL MOMENT TIMELINE ASSIST SMOKE TEST PASSED")


def test_universal_moment_timeline_assist_smoke() -> None:
    main()


if __name__ == "__main__":
    main()
