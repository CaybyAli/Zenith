"""
P3-3F Wirkungsbeweis: But/Therefore Story Flow beeinflusst Timeline-Ordering.
"""

from types import SimpleNamespace

from core.but_therefore_story_applier import apply_story_flow_ordering
from core.timeline_signal_consumer import SIGNAL_BUT_THEREFORE


def _item(candidate_id: str, start: float, end: float, score: float = 0.5) -> dict:
    return {
        "candidate": SimpleNamespace(
            candidate_id=candidate_id,
            start_time=start,
            end_time=end,
        ),
        "selection_score": score,
        "notes": [],
    }


def _job(signals: list[dict]) -> SimpleNamespace:
    return SimpleNamespace(unified_edit_signals=signals)


def test_setup_gets_bonus_over_and_segment():
    """setup story_role bekommt Bonus, and bekommt bei Haeufung Penalty."""
    candidates = [
        _item("setup", 0.0, 5.0),
        _item("and_1", 10.0, 15.0),
        _item("and_2", 20.0, 25.0),
        _item("and_3", 30.0, 35.0),
    ]
    job = _job(
        [
            {
                "signal_type": SIGNAL_BUT_THEREFORE,
                "start_seconds": 0.0,
                "end_seconds": 5.0,
                "story_role": "setup",
                "story_score": 0.9,
            },
            {
                "signal_type": SIGNAL_BUT_THEREFORE,
                "start_seconds": 10.0,
                "end_seconds": 15.0,
                "story_role": "and",
                "story_score": 0.9,
            },
            {
                "signal_type": SIGNAL_BUT_THEREFORE,
                "start_seconds": 20.0,
                "end_seconds": 25.0,
                "story_role": "and",
                "story_score": 0.9,
            },
            {
                "signal_type": SIGNAL_BUT_THEREFORE,
                "start_seconds": 30.0,
                "end_seconds": 35.0,
                "story_role": "and",
                "story_score": 0.9,
            },
        ]
    )

    result = apply_story_flow_ordering(candidates, job)

    assert result[0]["selection_score"] > candidates[0]["selection_score"]
    assert result[3]["selection_score"] < candidates[3]["selection_score"]
    assert "story_setup_bonus" in result[0]["notes"]
    assert "story_and_run_penalty" in result[3]["notes"]


def test_payoff_segment_gets_story_bonus():
    """payoff/therefore story_role bekommt Bonus."""
    candidates = [_item("payoff", 40.0, 45.0)]
    job = _job(
        [
            {
                "signal_type": SIGNAL_BUT_THEREFORE,
                "start_seconds": 40.0,
                "end_seconds": 45.0,
                "story_role": "payoff",
                "story_score": 0.9,
            }
        ]
    )

    result = apply_story_flow_ordering(candidates, job)

    assert result[0]["selection_score"] == 0.55
    assert "story_payoff_bonus" in result[0]["notes"]


def test_orphan_reaction_gets_penalty():
    """orphan_reaction=True -> niedrigere Prioritaet, nicht geloescht."""
    candidates = [_item("orphan", 50.0, 55.0)]
    job = _job(
        [
            {
                "signal_type": SIGNAL_BUT_THEREFORE,
                "start_seconds": 50.0,
                "end_seconds": 55.0,
                "story_role": "reaction",
                "story_score": 0.9,
                "orphan_reaction": True,
            }
        ]
    )

    result = apply_story_flow_ordering(candidates, job)

    assert len(result) == 1
    assert result[0]["selection_score"] == 0.45
    assert "story_orphan_reaction_penalty" in result[0]["notes"]


def test_no_signal_returns_candidates_unchanged():
    """Kein Signal -> Liste unveraendert zurueck, kein Crash."""
    candidates = [_item("plain", 0.0, 5.0)]
    job = _job([])

    result = apply_story_flow_ordering(candidates, job)

    assert result is candidates


def test_too_many_and_segments_get_penalty():
    """Mehr als 2 and-Segmente hintereinander bekommen -0.04 Penalty."""
    candidates = [
        _item("and_1", 0.0, 5.0),
        _item("and_2", 10.0, 15.0),
        _item("and_3", 20.0, 25.0),
    ]
    job = _job(
        [
            {
                "signal_type": SIGNAL_BUT_THEREFORE,
                "start_seconds": 0.0,
                "end_seconds": 5.0,
                "story_role": "and",
                "story_score": 0.9,
            },
            {
                "signal_type": SIGNAL_BUT_THEREFORE,
                "start_seconds": 10.0,
                "end_seconds": 15.0,
                "story_role": "and",
                "story_score": 0.9,
            },
            {
                "signal_type": SIGNAL_BUT_THEREFORE,
                "start_seconds": 20.0,
                "end_seconds": 25.0,
                "story_role": "and",
                "story_score": 0.9,
            },
        ]
    )

    result = apply_story_flow_ordering(candidates, job)

    assert result[0]["selection_score"] == 0.5
    assert result[1]["selection_score"] == 0.5
    assert result[2]["selection_score"] == 0.46
    assert "story_and_run_penalty" in result[2]["notes"]
