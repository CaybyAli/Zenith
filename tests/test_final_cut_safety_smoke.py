from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.final_cut_safety_guard import FinalCutSafetyGuard
from models.edit_timeline import EditTimeline
from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult, TranscriptSegment


JOB_ID = "job_final_cut_safety_smoke"


def _segment(segment_id: str, start_time: float, end_time: float) -> TimelineSegment:
    return TimelineSegment(
        segment_id=segment_id,
        job_id=JOB_ID,
        candidate_id=f"cand_{segment_id}",
        start_time=start_time,
        end_time=end_time,
        segment_role="bridge",
        selection_score=0.8,
        notes=[],
        source="final_cut_safety_smoke",
    )


def _transcript(segments: list[TranscriptSegment]) -> TranscriptResult:
    return TranscriptResult(
        source_path="final_cut_safety_smoke.mp4",
        language="de",
        engine="smoke",
        full_text="cut safety smoke",
        segments=segments,
    )


def test_final_cut_safety_smoke() -> None:
    start_before = 11.0
    end_before = 33.0
    skipped_start_before = 46.0

    guarded_start, start_summary = FinalCutSafetyGuard().apply(
        [_segment("seg_start_adjust", start_before, 20.0)],
        _transcript([TranscriptSegment(10.0, 14.0, "start boundary sentence")]),
    )
    by_id = {segment.segment_id: segment for segment in guarded_start}

    assert by_id["seg_start_adjust"].start_time == 10.0
    assert start_summary.adjusted_start >= 1

    guarded_end, end_summary = FinalCutSafetyGuard().apply(
        [_segment("seg_end_adjust", 20.0, end_before)],
        _transcript([TranscriptSegment(30.0, 35.0, "end boundary sentence")]),
    )
    by_id.update({segment.segment_id: segment for segment in guarded_end})

    assert by_id["seg_end_adjust"].end_time == 35.0
    assert end_summary.adjusted_end >= 1

    guarded_skip, skip_summary = FinalCutSafetyGuard().apply(
        [_segment("seg_start_skip_far", skipped_start_before, 60.0)],
        _transcript([TranscriptSegment(40.0, 50.0, "far boundary sentence")]),
    )
    by_id.update({segment.segment_id: segment for segment in guarded_skip})

    assert by_id["seg_start_skip_far"].start_time == skipped_start_before
    assert skip_summary.skipped_start >= 1

    overlap_start_guarded, overlap_start_summary = FinalCutSafetyGuard().apply(
        [
            _segment("seg_previous", 8.0, 10.5),
            _segment("seg_start_overlap_guard", 11.0, 20.0),
        ],
        _transcript([TranscriptSegment(9.0, 12.0, "previous overlap sentence")]),
    )
    by_id.update({segment.segment_id: segment for segment in overlap_start_guarded})

    current = by_id["seg_start_overlap_guard"]
    assert current.start_time >= by_id["seg_previous"].end_time + 0.15
    assert current.start_time == 11.0
    assert overlap_start_summary.skipped_start >= 1

    overlap_end_guarded, overlap_end_summary = FinalCutSafetyGuard().apply(
        [
            _segment("seg_end_overlap_guard", 20.0, 33.0),
            _segment("seg_next", 34.0, 40.0),
        ],
        _transcript([TranscriptSegment(30.0, 36.0, "next overlap sentence")]),
    )
    by_id.update({segment.segment_id: segment for segment in overlap_end_guarded})

    overlap_end = by_id["seg_end_overlap_guard"]
    assert overlap_end.end_time <= by_id["seg_next"].start_time - 0.15
    assert overlap_end_summary.skipped_end >= 1

    combined = sorted(
        [*guarded_start, *guarded_end, *guarded_skip],
        key=lambda segment: (segment.start_time, segment.end_time),
    )
    ids = [segment.segment_id for segment in combined]
    assert len(ids) == len(set(ids))

    no_overlaps = all(
        combined[index].start_time >= combined[index - 1].end_time
        for index in range(1, len(combined))
    )
    no_backjumps = all(
        combined[index].start_time >= combined[index - 1].start_time
        for index in range(1, len(combined))
    )

    assert no_overlaps
    assert no_backjumps
    for segment in [*combined, *overlap_start_guarded, *overlap_end_guarded]:
        assert segment.start_time >= 0.0
        assert segment.end_time > segment.start_time
        assert segment.duration >= 2.0

    timeline = EditTimeline(
        timeline_id="timeline_final_cut_safety_smoke",
        job_id=JOB_ID,
        target_duration=120.0,
        selected_segments=combined,
    )
    assert timeline.total_selected_duration == round(sum(segment.duration for segment in combined), 3)
    assert timeline.total_selected_duration > 0.0

    print(f"start_before={start_before}")
    print(f"start_after={by_id['seg_start_adjust'].start_time}")
    print(f"end_before={end_before}")
    print(f"end_after={by_id['seg_end_adjust'].end_time}")
    print(f"skipped_start={skip_summary.skipped_start + overlap_start_summary.skipped_start}")
    print(f"skipped_end={overlap_end_summary.skipped_end}")
    print(f"no_overlaps={no_overlaps}")
    print(f"no_backjumps={no_backjumps}")
    print(f"total_selected_duration={timeline.total_selected_duration}")
    print("FINAL CUT SAFETY SMOKE TEST PASSED")


if __name__ == "__main__":
    test_final_cut_safety_smoke()
