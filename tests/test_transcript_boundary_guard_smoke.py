from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.longform_timeline_builder import LongformTimelineBuilder
from models.analysis_result import AnalysisResult
from models.highlight_candidate import HighlightCandidate
from models.job import Job
from models.transcript_result import TranscriptResult, TranscriptSegment
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)


JOB_ID = "job_transcript_boundary_guard_smoke"


def _make_job() -> Job:
    return Job(
        job_id=JOB_ID,
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.LONGFORM,
        target_platforms=[],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.9,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="inbox/gaming_main/transcript_boundary_guard_smoke.mp4",
    )


def _make_analysis() -> AnalysisResult:
    return AnalysisResult(
        job_id=JOB_ID,
        duration_seconds=80.0,
        file_size_bytes=123456,
        usable_for_shorts=True,
        usable_for_longform=True,
        analysis_confidence=0.9,
        notes=[],
    )


def _candidate(
    candidate_id: str,
    start_time: float,
    end_time: float,
) -> HighlightCandidate:
    return HighlightCandidate(
        candidate_id=candidate_id,
        job_id=JOB_ID,
        start_time=start_time,
        end_time=end_time,
        highlight_score=0.75,
        candidate_kind="action_peak",
        confidence=0.9,
        signal_tags=[],
        source="boundary_smoke",
        notes=[],
    )


def _transcript() -> TranscriptResult:
    return TranscriptResult(
        source_path="boundary_smoke.mp4",
        language="de",
        engine="smoke",
        full_text="one two three",
        segments=[
            TranscriptSegment(10.0, 14.0, "start boundary sentence"),
            TranscriptSegment(30.0, 35.0, "end boundary sentence"),
            TranscriptSegment(40.0, 50.0, "far boundary sentence"),
        ],
    )


def test_transcript_boundary_guard_smoke() -> None:
    before_start = 11.0
    before_end = 33.0
    skipped_start = 43.0

    timeline = LongformTimelineBuilder().build(
        job=_make_job(),
        analysis_result=_make_analysis(),
        highlight_candidates=[
            _candidate("start_mid_word", before_start, 20.0),
            _candidate("end_mid_word", 20.0, before_end),
            _candidate("skip_far_boundary", skipped_start, 55.0),
        ],
        weak_zones=[],
        transcript_result=_transcript(),
    )

    by_candidate = {
        segment.candidate_id: segment
        for segment in timeline.selected_segments
    }

    start_segment = by_candidate["start_mid_word"]
    end_segment = by_candidate["end_mid_word"]
    skipped_segment = by_candidate["skip_far_boundary"]

    assert start_segment.start_time == 9.75
    assert any(note.startswith("boundary_adjusted_start=") for note in start_segment.notes)
    assert any(note.startswith("quality_speech_start_adjusted=") for note in start_segment.notes)

    assert end_segment.end_time == 35.35
    assert any(note.startswith("boundary_adjusted_end=") for note in end_segment.notes)
    assert any(note.startswith("quality_speech_end_adjusted=") for note in end_segment.notes)

    assert skipped_segment.start_time == 39.75
    assert "boundary_skipped_start_no_safe_point" in skipped_segment.notes
    assert any(note.startswith("quality_speech_start_adjusted=") for note in skipped_segment.notes)

    for segment in timeline.selected_segments:
        assert segment.start_time >= 0.0
        assert segment.end_time > segment.start_time
        assert 0.0 <= segment.selection_score <= 1.0

    assert 0.0 <= timeline.timeline_score <= 1.0
    assert any("Boundary guard:" in note for note in timeline.timeline_notes)

    print(f"before_start={before_start}")
    print(f"after_start={start_segment.start_time}")
    print(f"before_end={before_end}")
    print(f"after_end={end_segment.end_time}")
    print(f"skipped_case={skipped_segment.start_time}")
    print(f"notes={start_segment.notes + end_segment.notes + skipped_segment.notes}")
    print("TRANSCRIPT BOUNDARY GUARD SMOKE TEST PASSED")


if __name__ == "__main__":
    test_transcript_boundary_guard_smoke()
