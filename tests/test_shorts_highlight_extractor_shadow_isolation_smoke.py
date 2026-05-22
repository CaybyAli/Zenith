from __future__ import annotations

from unittest.mock import patch

from core.power_profile import PowerProfile
from core.shorts_highlight_extractor import LLM_SHADOW, ShortsHighlightExtractor
from models.edit_timeline import EditTimeline
from models.timeline_segment import TimelineSegment


class _FakeDecision:
    reasoning = "hook_sec_o(hook_sc startsnw{ schema_field: value }"


def _segment(index: int, start: float, end: float, score: float) -> TimelineSegment:
    return TimelineSegment(
        segment_id=f"shadow_seg_{index}",
        job_id="shadow_smoke_job",
        candidate_id=None,
        start_time=start,
        end_time=end,
        segment_role="highlight",
        selection_score=score,
        notes=[f"shadow transcript slice {index}"],
    )


def _timeline() -> EditTimeline:
    segments = [
        _segment(0, 0.0, 20.0, 0.95),
        _segment(1, 25.0, 45.0, 0.88),
        _segment(2, 50.0, 70.0, 0.81),
    ]
    return EditTimeline(
        timeline_id="timeline_shadow_isolation_smoke",
        job_id="shadow_smoke_job",
        target_duration=sum(segment.duration for segment in segments),
        selected_segments=segments,
        timeline_score=1.0,
    )


def test_shadow_mode_llm_rationale_is_empty_on_all_clips():
    extractor = ShortsHighlightExtractor()

    with patch.object(extractor, "_call_llm", return_value=_FakeDecision()):
        clips = extractor.extract_highlights(
            timeline=_timeline(),
            power_profile=PowerProfile.ECO,
            llm_mode=LLM_SHADOW,
        )

    assert len(clips) >= 1
    for clip in clips:
        assert clip.llm_rationale == "", (
            f"Shadow-Mode Rationale-Leak: clip.llm_rationale={clip.llm_rationale!r}"
        )
