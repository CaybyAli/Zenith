from __future__ import annotations

from core.llm_brain import LLMBrainDecision
from core.shorts_highlight_extractor import LLM_DISABLED, LLM_SHADOW
from core.shorts_reframe_planner import (
    HYBRID_RATIONALE_TAG,
    LAYOUT_FACECAM_CENTERED,
    LAYOUT_GAMEPLAY_CENTERED,
    LAYOUT_HYBRID_SPLIT,
    PLATFORM_YOUTUBE_SHORTS,
    SAFE_ZONE_TOP_PX,
    ShortsReframePlanner,
)
from core.timeline_signal_consumer import (
    SIGNAL_DYNAMIC_PACING,
    SIGNAL_EMOTIONAL_ARC,
    SIGNAL_HOOK_IDENTIFICATION,
    SIGNAL_REACTION_SHOT,
    TimelineSignalConsumer,
)
from models.edit_timeline import EditTimeline
from models.shorts_clip import ShortsClip
from models.timeline_segment import TimelineSegment

JOB_ID = "job_shorts_reframe_planner_test"
TIMELINE_ID = "timeline_shorts_reframe_planner_test"


class DummyLayoutLLMBrain:
    def decide_hook(self, candidates, job_context):
        return LLMBrainDecision(
            decision_type="hook",
            recommended_index=2,
            recommended_order=None,
            reasoning="Mock LLM recommends hybrid_split because both sources matter.",
            confidence=0.8,
            model_used="dummy",
            shadow_mode=True,
            warnings=[],
            raw_response={"dummy": True},
        )


def _clip() -> ShortsClip:
    return ShortsClip(
        source_job_id=JOB_ID,
        source_start_time=10.0,
        source_end_time=40.0,
        planned_duration=30.0,
        hook_score=0.9,
        clip_index=0,
    )


def _timeline() -> EditTimeline:
    return EditTimeline(
        timeline_id=TIMELINE_ID,
        job_id=JOB_ID,
        target_duration=30.0,
        selected_segments=[
            TimelineSegment(
                segment_id="seg_0",
                job_id=JOB_ID,
                candidate_id=None,
                start_time=10.0,
                end_time=40.0,
                segment_role="highlight",
                selection_score=0.9,
            )
        ],
    )


def _signal(signal_type: str, score: float | None) -> dict:
    return {
        "signal_type": signal_type,
        "start_time": 10.0,
        "end_time": 40.0,
        "score": score,
    }


def _planner(
    *,
    hook: float | None = None,
    pacing: float | None = None,
    reaction: float | None = None,
    arc: float | None = None,
    llm_brain=None,
) -> ShortsReframePlanner:
    signals = []
    if hook is not None:
        signals.append(_signal(SIGNAL_HOOK_IDENTIFICATION, hook))
    if pacing is not None:
        signals.append(_signal(SIGNAL_DYNAMIC_PACING, pacing))
    if reaction is not None:
        signals.append(_signal(SIGNAL_REACTION_SHOT, reaction))
    if arc is not None:
        signals.append(_signal(SIGNAL_EMOTIONAL_ARC, arc))

    return ShortsReframePlanner(
        signal_consumer=TimelineSignalConsumer(signals=signals),
        llm_brain=llm_brain,
    )


def _plan_from_scores(
    *,
    hook: float | None = None,
    pacing: float | None = None,
    reaction: float | None = None,
    arc: float | None = None,
    llm_mode: str = LLM_DISABLED,
    llm_brain=None,
):
    return _planner(
        hook=hook,
        pacing=pacing,
        reaction=reaction,
        arc=arc,
        llm_brain=llm_brain,
    ).plan_reframe(_clip(), _timeline(), llm_mode=llm_mode)


def test_gameplay_centered_filter_contains_vertical_crop() -> None:
    plan = _plan_from_scores(hook=0.8, pacing=0.7, reaction=0.1, arc=0.1)

    assert plan.layout_type == LAYOUT_GAMEPLAY_CENTERED
    assert "crop=1080:1920" in plan.ffmpeg_crop_filter


def test_facecam_centered_filter_contains_vstack() -> None:
    plan = _plan_from_scores(hook=0.2, pacing=0.2, reaction=0.8, arc=0.7)

    assert plan.layout_type == LAYOUT_FACECAM_CENTERED
    assert "vstack" in plan.ffmpeg_crop_filter


def test_hybrid_split_filter_contains_vstack() -> None:
    plan = _plan_from_scores(hook=0.5, pacing=0.5, reaction=0.5, arc=0.5)

    assert plan.layout_type == LAYOUT_HYBRID_SPLIT
    assert "vstack" in plan.ffmpeg_crop_filter


def test_hybrid_split_rationale_contains_hybrid() -> None:
    plan = _plan_from_scores(hook=0.5, pacing=0.5, reaction=0.5, arc=0.5)

    assert HYBRID_RATIONALE_TAG in plan.layout_rationale


def test_hook_and_pacing_dominate_selects_gameplay_centered() -> None:
    plan = _plan_from_scores(hook=0.8, pacing=0.7, reaction=0.1, arc=0.1)

    assert plan.layout_type == LAYOUT_GAMEPLAY_CENTERED


def test_reaction_and_arc_dominate_selects_facecam_centered() -> None:
    plan = _plan_from_scores(hook=0.2, pacing=0.2, reaction=0.8, arc=0.7)

    assert plan.layout_type == LAYOUT_FACECAM_CENTERED


def test_equal_signals_select_hybrid_split() -> None:
    plan = _plan_from_scores(hook=0.5, pacing=0.5, reaction=0.5, arc=0.5)

    assert plan.layout_type == LAYOUT_HYBRID_SPLIT


def test_no_signal_data_selects_hybrid_split_safe_default() -> None:
    plan = _plan_from_scores()

    assert plan.layout_type == LAYOUT_HYBRID_SPLIT
    assert "safe default" in plan.layout_rationale


def test_plan_safe_zone_top_is_default() -> None:
    plan = _plan_from_scores(hook=0.8, pacing=0.7, reaction=0.1, arc=0.1)

    assert plan.safe_zone_top_px == SAFE_ZONE_TOP_PX


def test_plan_platform_preset_is_youtube_shorts() -> None:
    plan = _plan_from_scores(hook=0.8, pacing=0.7, reaction=0.1, arc=0.1)

    assert plan.platform_preset == PLATFORM_YOUTUBE_SHORTS


def test_layout_rationale_is_not_empty() -> None:
    plan = _plan_from_scores(hook=0.8, pacing=0.7, reaction=0.1, arc=0.1)

    assert plan.layout_rationale.strip()


def test_llm_shadow_appends_mock_llm_note_to_rationale() -> None:
    plan = _plan_from_scores(
        hook=0.8,
        pacing=0.7,
        reaction=0.1,
        arc=0.1,
        llm_mode=LLM_SHADOW,
        llm_brain=DummyLayoutLLMBrain(),
    )

    assert "LLM_SHADOW:" in plan.layout_rationale
    assert "Mock LLM recommends" in plan.layout_rationale


def test_llm_shadow_does_not_override_heuristic_layout() -> None:
    plan = _plan_from_scores(
        hook=0.8,
        pacing=0.7,
        reaction=0.1,
        arc=0.1,
        llm_mode=LLM_SHADOW,
        llm_brain=DummyLayoutLLMBrain(),
    )

    assert plan.layout_type == LAYOUT_GAMEPLAY_CENTERED
