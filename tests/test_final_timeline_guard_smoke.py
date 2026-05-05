from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.final_timeline_guard import FinalTimelineGuard
from models.timeline_segment import TimelineSegment


JOB_ID = "job_final_timeline_guard_smoke"


def _segment(
    segment_id: str,
    start_time: float,
    end_time: float,
    score: float,
    *,
    kind: str = "audio_peak",
) -> TimelineSegment:
    return TimelineSegment(
        segment_id=segment_id,
        job_id=JOB_ID,
        candidate_id=f"cand_{segment_id}",
        start_time=start_time,
        end_time=end_time,
        segment_role="bridge",
        selection_score=score,
        notes=[f"candidate_kind={kind}"],
        source="final_timeline_guard_smoke",
    )


def test_final_timeline_guard_smoke() -> None:
    segments = [
        _segment("seg_backjump_a", 10.0, 20.0, 0.80),
        _segment("seg_backjump_b", 18.0, 30.0, 0.78),
        _segment("seg_overlap_low", 40.0, 55.0, 0.60, kind="action_peak"),
        _segment("seg_overlap_high", 45.0, 58.0, 0.90, kind="action_peak"),
        _segment("seg_near_a", 70.0, 80.0, 0.82, kind="audio_peak"),
        _segment("seg_near_b", 80.2, 89.0, 0.70, kind="audio_peak"),
        _segment("seg_good_a", 100.0, 110.0, 0.75, kind="speech_peak"),
        _segment("seg_good_b", 112.0, 120.0, 0.77, kind="action_peak"),
    ]
    duration_before = round(sum(segment.duration for segment in segments), 3)
    backjump_before = ("seg_backjump_a", 10.0, 20.0, "seg_backjump_b", 18.0, 30.0)

    guarded, summary = FinalTimelineGuard().apply(segments)
    by_id = {segment.segment_id: segment for segment in guarded}

    assert "seg_backjump_a" in by_id
    assert "seg_backjump_b" in by_id
    assert by_id["seg_backjump_b"].start_time > by_id["seg_backjump_a"].end_time
    assert summary.backjumps_fixed >= 1
    assert summary.trimmed >= 1

    assert "seg_overlap_high" in by_id
    assert "seg_overlap_low" not in by_id
    assert summary.overlaps_removed >= 1

    assert "seg_near_a" in by_id
    assert "seg_near_b" not in by_id
    assert summary.near_duplicates_removed >= 1

    assert "seg_good_a" in by_id
    assert "seg_good_b" in by_id

    ids = [segment.segment_id for segment in guarded]
    assert len(ids) == len(set(ids))

    previous_end = None
    for segment in guarded:
        assert segment.start_time >= 0.0
        assert segment.end_time > segment.start_time
        if previous_end is not None:
            assert segment.start_time >= previous_end
        previous_end = segment.end_time

    duration_after = round(sum(segment.duration for segment in guarded), 3)
    assert duration_after < duration_before
    assert summary.duration_before == duration_before
    assert summary.duration_after == duration_after

    no_backjumps = all(
        guarded[index].start_time >= guarded[index - 1].end_time
        for index in range(1, len(guarded))
    )
    assert no_backjumps

    print(f"backjump_before={backjump_before}")
    print(
        "backjump_after="
        f"{by_id['seg_backjump_a'].start_time}-{by_id['seg_backjump_a'].end_time} -> "
        f"{by_id['seg_backjump_b'].start_time}-{by_id['seg_backjump_b'].end_time}"
    )
    print(f"backjumps_fixed={summary.backjumps_fixed}")
    print(f"overlaps_removed={summary.overlaps_removed}")
    print(f"near_duplicates_removed={summary.near_duplicates_removed}")
    print(f"final_segments_sorted={True}")
    print(f"no_backjumps={no_backjumps}")
    print("FINAL TIMELINE GUARD SMOKE TEST PASSED")


if __name__ == "__main__":
    test_final_timeline_guard_smoke()
