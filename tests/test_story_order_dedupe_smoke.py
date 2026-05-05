from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.story_timeline_organizer import StoryTimelineOrganizer
from models.timeline_segment import TimelineSegment


JOB_ID = "job_story_order_dedupe_smoke"


def _segment(
    segment_id: str,
    start_time: float,
    end_time: float,
    score: float,
    *,
    kind: str = "action_peak",
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
        source="story_order_dedupe_smoke",
    )


def test_story_order_dedupe_smoke() -> None:
    segments = [
        _segment("seg_overlap_low", 10.0, 20.0, 0.70),
        _segment("seg_overlap_high", 12.0, 19.0, 0.90),
        _segment("seg_near_low", 30.0, 40.0, 0.66, kind="speech_peak"),
        _segment("seg_near_high", 40.2, 49.0, 0.76, kind="speech_peak"),
        _segment("seg_context_a", 60.0, 70.0, 0.62, kind="action_peak"),
        _segment("seg_context_b", 82.0, 92.0, 0.81, kind="speech_peak"),
        _segment("seg_context_c", 110.0, 122.0, 0.73, kind="action_peak"),
    ]

    candidates_before = len(segments)
    organized, summary = StoryTimelineOrganizer().apply(segments)
    by_id = {segment.segment_id: segment for segment in organized}

    assert candidates_before == 7
    assert len(organized) == 5
    assert summary.duplicates_removed == 1
    assert summary.near_duplicates_removed == 1

    assert "seg_overlap_high" in by_id
    assert "seg_overlap_low" not in by_id
    assert "seg_near_high" in by_id
    assert "seg_near_low" not in by_id

    starts = [segment.start_time for segment in organized]
    assert starts == sorted(starts)

    role_counts = {
        "hook": sum(segment.segment_role == "hook" for segment in organized),
        "build": sum(segment.segment_role == "build" for segment in organized),
        "bridge": sum(segment.segment_role == "bridge" for segment in organized),
        "peak": sum(segment.segment_role == "peak" for segment in organized),
        "payoff": sum(segment.segment_role == "payoff" for segment in organized),
    }
    assert role_counts["hook"] == 1
    assert role_counts["peak"] >= 1
    assert role_counts["payoff"] == 1
    assert role_counts["build"] + role_counts["bridge"] >= 1

    assert organized[0].segment_role == "hook"
    assert organized[-1].segment_role == "payoff"
    assert summary.hook_segment_id == organized[0].segment_id
    assert summary.payoff_segment_id == organized[-1].segment_id
    assert summary.peak_segment_ids

    segment_ids = [segment.segment_id for segment in organized]
    assert len(segment_ids) == len(set(segment_ids))

    duration_after = round(sum(segment.duration for segment in organized), 3)
    assert duration_after > 0.0
    assert duration_after < round(sum(segment.duration for segment in segments), 3)

    for segment in organized:
        assert segment.start_time >= 0.0
        assert segment.end_time > segment.start_time
        assert 0.0 <= segment.selection_score <= 1.0

    print(f"candidates_before={candidates_before}")
    print(f"segments_after={len(organized)}")
    print(f"duplicates_removed={summary.duplicates_removed}")
    print(f"near_duplicates_removed={summary.near_duplicates_removed}")
    print(f"hook_count={role_counts['hook']}")
    print(f"bridge_count={role_counts['bridge']}")
    print(f"build_count={role_counts['build']}")
    print(f"peak_count={role_counts['peak']}")
    print(f"payoff_count={role_counts['payoff']}")
    print(f"roles={[(segment.segment_id, segment.segment_role) for segment in organized]}")
    print("STORY ORDER DEDUPE SMOKE TEST PASSED")


if __name__ == "__main__":
    test_story_order_dedupe_smoke()
