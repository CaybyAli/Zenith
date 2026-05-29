
from core.longform_timeline_builder import LongformTimelineBuilder
from models.gameplay_vision_result import GameplayVisionResult, GameplayVisionWindow
from models.highlight_candidate import HighlightCandidate


def _candidate(start: float, end: float, kind: str = "speech_peak") -> HighlightCandidate:
    return HighlightCandidate(
        candidate_id=f"cand_{start}",
        job_id="job_p5_g5_owner_no_go",
        start_time=start,
        end_time=end,
        highlight_score=0.86,
        candidate_kind=kind,
        confidence=0.90,
        signal_tags=[],
        source="test",
    )


def test_p5_g5_intro_speech_without_gameplay_action_is_capped_below_primary_floor():
    vision = GameplayVisionResult(
        windows=[
            GameplayVisionWindow(
                start_seconds=0.0,
                end_seconds=80.0,
                motion_score=0.05,
                action_score=0.04,
                scene_change_score=0.0,
                label="menu_wait",
                reason="synthetic intro waiting",
            )
        ],
        action_windows=[],
        average_action_score=0.04,
        max_action_score=0.04,
    )

    score, notes = LongformTimelineBuilder()._score_candidate_for_longform(
        _candidate(20.0, 63.0),
        weak_zones=[],
        gameplay_vision_result=vision,
    )

    assert score <= 0.34
    assert "owner_no_go_intro_no_gameplay_action_cap" in notes


def test_p5_g5_later_speech_without_gameplay_action_is_capped_as_menu_wait():
    vision = GameplayVisionResult(
        windows=[
            GameplayVisionWindow(
                start_seconds=600.0,
                end_seconds=630.0,
                motion_score=0.08,
                action_score=0.05,
                scene_change_score=0.0,
                label="menu_wait",
                reason="synthetic waiting",
            )
        ],
        action_windows=[],
        average_action_score=0.05,
        max_action_score=0.05,
    )

    score, notes = LongformTimelineBuilder()._score_candidate_for_longform(
        _candidate(602.7, 629.35),
        weak_zones=[],
        gameplay_vision_result=vision,
    )

    assert score <= 0.44
    assert "owner_no_go_menu_wait_no_gameplay_action_cap" in notes


def test_p5_g5_gameplay_action_overlap_is_not_owner_no_go_capped():
    action_window = GameplayVisionWindow(
        start_seconds=30.0,
        end_seconds=45.0,
        motion_score=0.80,
        action_score=0.85,
        scene_change_score=0.20,
        label="action",
        reason="synthetic real gameplay action",
    )
    vision = GameplayVisionResult(
        windows=[action_window],
        action_windows=[action_window],
        average_action_score=0.85,
        max_action_score=0.85,
    )

    score, notes = LongformTimelineBuilder()._score_candidate_for_longform(
        _candidate(20.0, 63.0),
        weak_zones=[],
        gameplay_vision_result=vision,
    )

    assert score > 0.45
    assert "vision_boost" in notes
    assert "owner_no_go_intro_no_gameplay_action_cap" not in notes
    assert "owner_no_go_menu_wait_no_gameplay_action_cap" not in notes
