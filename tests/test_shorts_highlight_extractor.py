from __future__ import annotations

import pytest

from core.llm_brain import LLMBrain, LLMBrainDecision
from core.power_profile import PowerProfile
from core.shorts_highlight_extractor import (
    LLM_DISABLED,
    LLM_SHADOW,
    SHORTS_MAX_DURATION_SECONDS,
    SHORTS_MIN_DURATION_SECONDS,
    ShortsHighlightExtractor,
)
from core.timeline_signal_consumer import (
    SIGNAL_BUT_THEREFORE,
    SIGNAL_EMOTIONAL_ARC,
    SIGNAL_HOOK_IDENTIFICATION,
    SIGNAL_REACTION_SHOT,
    TimelineSignalConsumer,
)
from models.edit_timeline import EditTimeline
from models.shorts_clip import ShortsClip
from models.timeline_segment import TimelineSegment

TIMELINE_ID = "timeline_shorts_extractor_test"
JOB_ID = "job_shorts_extractor_test"


class DummyLLMBrain:
    def decide_segment_order(self, segments, arc_hints=None, job=None):
        return LLMBrainDecision(
            decision_type="segment_order",
            recommended_index=None,
            recommended_order=list(range(len(segments))),
            reasoning="Dummy LLM selected the strongest shorts candidates.",
            confidence=0.8,
            model_used="dummy",
            shadow_mode=True,
            warnings=[],
            raw_response={"dummy": True},
        )


def _segment(index: int, start: float, end: float, score: float) -> TimelineSegment:
    return TimelineSegment(
        segment_id=f"seg_{index}",
        job_id=JOB_ID,
        candidate_id=None,
        start_time=start,
        end_time=end,
        segment_role="highlight",
        selection_score=score,
        notes=[f"transcript slice {index}"],
    )


def _timeline(segments: list[TimelineSegment]) -> EditTimeline:
    return EditTimeline(
        timeline_id=TIMELINE_ID,
        job_id=JOB_ID,
        target_duration=sum(segment.duration for segment in segments),
        selected_segments=segments,
        timeline_score=1.0,
    )


def _signal(signal_type: str, start: float, end: float, score: float) -> dict:
    return {
        "signal_type": signal_type,
        "start_time": start,
        "end_time": end,
        "score": score,
    }


def _consumer_for_segments(segments: list[TimelineSegment]) -> TimelineSignalConsumer:
    signals = []
    for index, segment in enumerate(segments):
        base_score = max(0.05, 1.0 - index * 0.07)
        signals.extend(
            [
                _signal(SIGNAL_HOOK_IDENTIFICATION, segment.start_time, segment.end_time, base_score),
                _signal(SIGNAL_REACTION_SHOT, segment.start_time, segment.end_time, base_score - 0.03),
                _signal(SIGNAL_EMOTIONAL_ARC, segment.start_time, segment.end_time, base_score - 0.05),
                _signal(SIGNAL_BUT_THEREFORE, segment.start_time, segment.end_time, base_score - 0.02),
            ]
        )
    return TimelineSignalConsumer(signals=signals)


def _standard_timeline_and_extractor(llm_brain=None):
    segments = [
        _segment(0, 0.0, 20.0, 0.95),
        _segment(1, 25.0, 45.0, 0.88),
        _segment(2, 50.0, 70.0, 0.81),
        _segment(3, 75.0, 95.0, 0.74),
        _segment(4, 100.0, 120.0, 0.67),
        _segment(5, 125.0, 145.0, 0.60),
    ]
    extractor = ShortsHighlightExtractor(
        signal_consumer=_consumer_for_segments(segments),
        llm_brain=llm_brain,
    )
    return _timeline(segments), extractor


def test_eco_returns_one_clip() -> None:
    timeline, extractor = _standard_timeline_and_extractor()

    clips = extractor.extract_highlights(timeline, PowerProfile.ECO, llm_mode=LLM_DISABLED)

    assert len(clips) == 1


def test_balanced_returns_three_clips() -> None:
    timeline, extractor = _standard_timeline_and_extractor()

    clips = extractor.extract_highlights(timeline, PowerProfile.BALANCED, llm_mode=LLM_DISABLED)

    assert len(clips) == 3


def test_performance_returns_five_clips() -> None:
    timeline, extractor = _standard_timeline_and_extractor()

    clips = extractor.extract_highlights(timeline, PowerProfile.PERFORMANCE, llm_mode=LLM_DISABLED)

    assert len(clips) == 5


def test_clips_do_not_overlap() -> None:
    timeline, extractor = _standard_timeline_and_extractor()

    clips = extractor.extract_highlights(timeline, PowerProfile.FULL_POWER, llm_mode=LLM_DISABLED)

    for left_index, left in enumerate(clips):
        for right in clips[left_index + 1:]:
            assert left.source_end_time <= right.source_start_time or right.source_end_time <= left.source_start_time


def test_all_clips_are_between_fifteen_and_sixty_seconds() -> None:
    timeline, extractor = _standard_timeline_and_extractor()

    clips = extractor.extract_highlights(timeline, PowerProfile.FULL_POWER, llm_mode=LLM_DISABLED)

    assert clips
    for clip in clips:
        assert SHORTS_MIN_DURATION_SECONDS <= clip.planned_duration <= SHORTS_MAX_DURATION_SECONDS


def test_unknown_power_profile_defaults_to_three_clips() -> None:
    timeline, extractor = _standard_timeline_and_extractor()

    clips = extractor.extract_highlights(timeline, "unknown_profile", llm_mode=LLM_DISABLED)

    assert len(clips) == 3


def test_short_candidate_is_extended_to_minimum_duration() -> None:
    segments = [
        _segment(0, 0.0, 20.0, 0.20),
        _segment(1, 30.0, 38.0, 0.99),
        _segment(2, 50.0, 70.0, 0.10),
    ]
    extractor = ShortsHighlightExtractor(signal_consumer=_consumer_for_segments(segments))
    timeline = _timeline(segments)

    clips = extractor.extract_highlights(timeline, PowerProfile.ECO, llm_mode=LLM_DISABLED)

    assert len(clips) == 1
    assert clips[0].planned_duration >= SHORTS_MIN_DURATION_SECONDS


def test_long_candidate_is_trimmed_to_maximum_duration() -> None:
    segments = [_segment(0, 0.0, 80.0, 0.99)]
    extractor = ShortsHighlightExtractor(signal_consumer=_consumer_for_segments(segments))
    timeline = _timeline(segments)

    clips = extractor.extract_highlights(timeline, PowerProfile.ECO, llm_mode=LLM_DISABLED)

    assert len(clips) == 1
    assert clips[0].planned_duration <= SHORTS_MAX_DURATION_SECONDS


def test_llm_disabled_keeps_empty_rationale() -> None:
    timeline, extractor = _standard_timeline_and_extractor(llm_brain=DummyLLMBrain())

    clips = extractor.extract_highlights(timeline, PowerProfile.BALANCED, llm_mode=LLM_DISABLED)

    assert clips
    assert all(clip.llm_rationale == "" for clip in clips)


def test_llm_shadow_fills_rationale_with_mock_llm() -> None:
    timeline, extractor = _standard_timeline_and_extractor(llm_brain=DummyLLMBrain())

    clips = extractor.extract_highlights(timeline, PowerProfile.BALANCED, llm_mode=LLM_SHADOW)

    assert clips
    assert all(clip.llm_rationale for clip in clips)


@pytest.mark.local_llm
def test_local_llm_shadow_vs_disabled_ranking_does_not_crash(caplog) -> None:
    timeline, _ = _standard_timeline_and_extractor()

    disabled_extractor = ShortsHighlightExtractor(
        signal_consumer=_consumer_for_segments(timeline.selected_segments),
        llm_brain=LLMBrain(timeout_seconds=0.1),
    )
    shadow_extractor = ShortsHighlightExtractor(
        signal_consumer=_consumer_for_segments(timeline.selected_segments),
        llm_brain=LLMBrain(timeout_seconds=0.1),
    )

    disabled_clips = disabled_extractor.extract_highlights(
        timeline,
        PowerProfile.BALANCED,
        llm_mode=LLM_DISABLED,
    )
    shadow_clips = shadow_extractor.extract_highlights(
        timeline,
        PowerProfile.BALANCED,
        llm_mode=LLM_SHADOW,
    )

    disabled_ranking = [(clip.source_start_time, clip.source_end_time, clip.hook_score) for clip in disabled_clips]
    shadow_ranking = [(clip.source_start_time, clip.source_end_time, clip.hook_score) for clip in shadow_clips]

    print("LLM_DISABLED ranking:", disabled_ranking)
    print("LLM_SHADOW ranking:", shadow_ranking)
    print("ranking_equal:", disabled_ranking == shadow_ranking)

    assert isinstance(shadow_clips, list)
    assert all(isinstance(clip, ShortsClip) for clip in shadow_clips)
    assert len(disabled_clips) == len(shadow_clips)
