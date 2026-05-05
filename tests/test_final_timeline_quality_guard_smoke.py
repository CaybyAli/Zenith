from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.final_timeline_quality_guard import FinalTimelineQualityGuard
from models.highlight_candidate import HighlightCandidate
from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult, TranscriptSegment


JOB_ID = "job_final_timeline_quality_guard_smoke"


def _segment(
    segment_id: str,
    start_time: float,
    end_time: float,
    *,
    role: str = "bridge",
    score: float = 0.75,
    notes: list[str] | None = None,
) -> TimelineSegment:
    return TimelineSegment(
        segment_id=segment_id,
        job_id=JOB_ID,
        candidate_id=f"cand_{segment_id}",
        start_time=start_time,
        end_time=end_time,
        segment_role=role,
        selection_score=score,
        notes=notes or [],
        source="quality_guard_smoke",
    )


def _weak_zone(
    zone_id: str,
    start_time: float,
    end_time: float,
    *,
    kind: str = "silence",
) -> HighlightCandidate:
    return HighlightCandidate(
        candidate_id=zone_id,
        job_id=JOB_ID,
        start_time=start_time,
        end_time=end_time,
        highlight_score=0.1,
        candidate_kind="drop_zone",
        confidence=0.9,
        signal_tags=[f"{kind}_zone"],
        source="quality_guard_smoke",
        notes=[f"{kind}_zone_detected"],
    )


def _transcript() -> TranscriptResult:
    return TranscriptResult(
        source_path="quality_guard_smoke.mp4",
        language="de",
        engine="smoke",
        full_text="speech guard smoke",
        segments=[
            TranscriptSegment(30.0, 34.0, "start speech"),
            TranscriptSegment(50.0, 55.0, "end speech"),
            TranscriptSegment(80.5, 83.0, "speech wins against silence"),
        ],
    )


def test_final_timeline_quality_guard_smoke() -> None:
    segments = [
        _segment("seg_micro_remove", 10.0, 10.2),
        _segment("seg_peak_micro_allowed", 20.0, 22.2, role="peak", score=0.95, notes=["energy_peak"]),
        _segment("seg_speech_start", 31.0, 40.0),
        _segment("seg_speech_end", 45.0, 53.0),
        _segment("seg_silence_start", 60.0, 70.0),
        _segment("seg_speech_wins", 80.0, 90.0),
    ]
    weak_zones = [
        _weak_zone("weak_silence_start", 60.0, 62.0),
        _weak_zone("weak_speech_overlap", 80.0, 82.0),
    ]

    guarded, summary = FinalTimelineQualityGuard().apply(
        segments,
        transcript_result=_transcript(),
        weak_zones=weak_zones,
    )
    by_id = {segment.segment_id: segment for segment in guarded}

    assert "seg_micro_remove" not in by_id
    assert summary.micro_removed >= 1

    assert "seg_peak_micro_allowed" in by_id
    assert by_id["seg_peak_micro_allowed"].duration < 2.5
    assert summary.peak_micro_allowed >= 1

    assert by_id["seg_speech_start"].start_time == 29.75
    assert summary.speech_start_adjusted >= 1

    assert by_id["seg_speech_end"].end_time == 55.35
    assert summary.speech_end_adjusted >= 1

    assert by_id["seg_silence_start"].start_time == 62.0
    assert summary.silence_edge_trimmed >= 1

    assert by_id["seg_speech_wins"].start_time == 80.0
    assert not any(
        note.startswith("quality_silence_edge_trim_start=")
        for note in by_id["seg_speech_wins"].notes
    )

    ids = [segment.segment_id for segment in guarded]
    assert len(ids) == len(set(ids))

    no_backjumps = all(
        guarded[index].start_time >= guarded[index - 1].start_time
        for index in range(1, len(guarded))
    )
    no_overlaps = all(
        guarded[index].start_time >= guarded[index - 1].end_time
        for index in range(1, len(guarded))
    )
    no_micro_cuts = all(
        segment.duration >= 2.5
        or (
            segment.segment_role == "peak"
            and segment.selection_score >= 0.90
            and "quality_peak_micro_allowed" in segment.notes
        )
        for segment in guarded
    )

    assert no_backjumps
    assert no_overlaps
    assert no_micro_cuts
    for segment in guarded:
        assert segment.start_time >= 0.0
        assert segment.end_time > segment.start_time

    print(f"micro_removed={summary.micro_removed}")
    print(f"peak_micro_allowed={summary.peak_micro_allowed}")
    print(f"speech_start_adjusted={summary.speech_start_adjusted}")
    print(f"speech_end_adjusted={summary.speech_end_adjusted}")
    print(f"silence_edge_trimmed={summary.silence_edge_trimmed}")
    print(f"duration_before={summary.duration_before}")
    print(f"duration_after={summary.duration_after}")
    print(f"no_micro_cuts={no_micro_cuts}")
    print(f"no_backjumps={no_backjumps}")
    print(f"no_overlaps={no_overlaps}")
    print("FINAL TIMELINE QUALITY GUARD SMOKE TEST PASSED")


if __name__ == "__main__":
    test_final_timeline_quality_guard_smoke()
