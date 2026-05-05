from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.silence_timeline_trimmer import SilenceTimelineTrimmer
from models.highlight_candidate import HighlightCandidate
from models.timeline_segment import TimelineSegment


JOB_ID = "job_silence_timeline_trim_smoke"


def _segment(
    segment_id: str,
    start_time: float,
    end_time: float,
    *,
    score: float = 0.7,
) -> TimelineSegment:
    return TimelineSegment(
        segment_id=segment_id,
        job_id=JOB_ID,
        candidate_id=f"cand_{segment_id}",
        start_time=start_time,
        end_time=end_time,
        segment_role="bridge",
        selection_score=score,
        notes=[],
        source="silence_trim_smoke",
    )


def _weak_zone(
    zone_id: str,
    start_time: float,
    end_time: float,
    *,
    kind: str = "silence",
) -> HighlightCandidate:
    note = "silence_zone_detected" if kind == "silence" else "low_motion_zone_detected"
    tag = "silence_zone" if kind == "silence" else "low_motion_zone"
    return HighlightCandidate(
        candidate_id=zone_id,
        job_id=JOB_ID,
        start_time=start_time,
        end_time=end_time,
        highlight_score=0.9,
        candidate_kind="drop_zone",
        confidence=0.9,
        signal_tags=[tag],
        source="highlight_selector.weak_zones",
        notes=[note],
    )


def test_silence_timeline_trim_smoke() -> None:
    segments = [
        _segment("seg_start_trim", 10.0, 20.0),
        _segment("seg_end_trim", 30.0, 40.0),
        _segment("seg_removed", 50.0, 60.0),
        _segment("seg_middle_skip", 70.0, 85.0),
        _segment("seg_min_duration", 90.0, 92.5),
        _segment("seg_low_motion", 100.0, 110.0),
    ]
    weak_zones = [
        _weak_zone("weak_start", 10.0, 12.0),
        _weak_zone("weak_end", 37.0, 40.0),
        _weak_zone("weak_removed", 50.5, 59.5),
        _weak_zone("weak_middle", 76.0, 78.0),
        _weak_zone("weak_min_duration", 90.0, 91.5),
        _weak_zone("weak_low_motion", 100.0, 102.0, kind="low_motion"),
    ]

    duration_before = round(sum(segment.duration for segment in segments), 3)
    kept_segments, summary = SilenceTimelineTrimmer().apply(segments, weak_zones)
    by_id = {segment.segment_id: segment for segment in kept_segments}

    assert by_id["seg_start_trim"].start_time == 12.0
    assert any(note.startswith("silence_trim_start=") for note in by_id["seg_start_trim"].notes)

    assert by_id["seg_end_trim"].end_time == 37.0
    assert any(note.startswith("silence_trim_end=") for note in by_id["seg_end_trim"].notes)

    assert "seg_removed" not in by_id
    assert summary.removed == 1

    assert by_id["seg_middle_skip"].start_time == 70.0
    assert by_id["seg_middle_skip"].end_time == 85.0
    assert "silence_middle_skipped" in by_id["seg_middle_skip"].notes

    assert by_id["seg_low_motion"].start_time == 102.0
    assert any(note.startswith("low_motion_trim_start=") for note in by_id["seg_low_motion"].notes)

    assert by_id["seg_min_duration"].start_time == 90.0
    assert by_id["seg_min_duration"].end_time == 92.5
    assert "silence_skipped_min_duration" in by_id["seg_min_duration"].notes

    duration_after = round(sum(segment.duration for segment in kept_segments), 3)
    assert duration_after < duration_before
    assert summary.duration_before == duration_before
    assert summary.duration_after == duration_after
    assert summary.trimmed_start >= 2
    assert summary.trimmed_end == 1
    assert summary.skipped_middle == 1

    for segment in kept_segments:
        assert segment.start_time >= 0.0
        assert segment.end_time > segment.start_time
        assert segment.duration >= 2.0
        assert 0.0 <= segment.selection_score <= 1.0

    print(f"start_before=10.0 start_after={by_id['seg_start_trim'].start_time}")
    print(f"end_before=40.0 end_after={by_id['seg_end_trim'].end_time}")
    print(f"removed_count={summary.removed}")
    print(f"duration_before={summary.duration_before}")
    print(f"duration_after={summary.duration_after}")
    print(f"skipped_middle={summary.skipped_middle}")
    print(f"notes={[(segment.segment_id, segment.notes) for segment in kept_segments]}")
    print("SILENCE TIMELINE TRIM SMOKE TEST PASSED")


if __name__ == "__main__":
    test_silence_timeline_trim_smoke()
