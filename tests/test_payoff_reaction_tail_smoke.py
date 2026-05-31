from __future__ import annotations

from core.payoff_reaction_tail import apply_round_payoff_tails_with_reaction_gate


def _base_plan(end: float = 10.0):
    return {
        "duration_contract": {
            "planned_output_duration_seconds": end,
        },
        "anti_overcut_audit": {
            "fail_count": 0,
        },
        "timeline_segments": [
            {
                "segment_id": "seg_001",
                "block_id": "block_001",
                "start_seconds": 0.0,
                "end_seconds": end,
                "duration_seconds": end,
                "state": "active_play",
                "keep_decision": "keep_active",
                "source": "test",
            },
        ],
    }


def test_tail_is_added_when_reaction_is_medium_and_speech_exists():
    plan = _base_plan(10.0)
    speech = [{"start_seconds": 11.0, "end_seconds": 15.0, "text": "death reaction"}]
    reactions = [{
        "reaction_id": "r1",
        "start_seconds": 12.0,
        "end_seconds": 12.5,
        "peak_time_seconds": 12.0,
        "intensity": "medium",
        "fusion_score": 0.4,
        "mic_audio_rise_db": 6.5,
    }]

    result = apply_round_payoff_tails_with_reaction_gate(
        plan,
        speech,
        reactions,
        media_duration_seconds=40.0,
        tail_max_seconds=20.0,
        reaction_min_intensity="medium",
    )

    assert len(result["payoff_tails"]) == 1
    assert result["payoff_tails"][0]["start_seconds"] == 10.0
    assert result["payoff_tails"][0]["end_seconds"] == 15.0
    assert result["payoff_tail_audit"]["anti_overcut_fail_count"] == 0


def test_no_tail_when_speech_exists_but_reaction_is_none():
    plan = _base_plan(10.0)
    speech = [{"start_seconds": 11.0, "end_seconds": 15.0, "text": "normal talking"}]
    reactions = []

    result = apply_round_payoff_tails_with_reaction_gate(
        plan,
        speech,
        reactions,
        media_duration_seconds=40.0,
        tail_max_seconds=20.0,
        reaction_min_intensity="medium",
    )

    assert result["payoff_tails"] == []
    assert result["payoff_tail_audit"]["added_tail_seconds"] == 0.0
    assert result["payoff_tail_audit"]["evaluations"][0]["reason"] == "reaction_below_min_intensity"


def test_trailing_silence_is_trimmed_after_reaction_tail():
    plan = _base_plan(10.0)
    speech = [{"start_seconds": 12.0, "end_seconds": 13.5, "text": "short reaction"}]
    reactions = [{
        "reaction_id": "r1",
        "start_seconds": 12.0,
        "end_seconds": 12.5,
        "peak_time_seconds": 12.0,
        "intensity": "high",
        "fusion_score": 0.7,
        "mic_audio_rise_db": 9.0,
    }]

    result = apply_round_payoff_tails_with_reaction_gate(
        plan,
        speech,
        reactions,
        media_duration_seconds=40.0,
        tail_max_seconds=20.0,
        reaction_min_intensity="medium",
    )

    tail = result["payoff_tails"][0]
    assert tail["end_seconds"] == 13.5
    assert tail["metadata"]["trailing_silence_trimmed"] is True


def test_low_reaction_does_not_pass_medium_gate():
    plan = _base_plan(10.0)
    speech = [{"start_seconds": 11.0, "end_seconds": 15.0, "text": "weak moment"}]
    reactions = [{
        "reaction_id": "r_low",
        "start_seconds": 12.0,
        "end_seconds": 12.5,
        "peak_time_seconds": 12.0,
        "intensity": "low",
        "fusion_score": 0.2,
        "mic_audio_rise_db": 3.0,
    }]

    result = apply_round_payoff_tails_with_reaction_gate(
        plan,
        speech,
        reactions,
        media_duration_seconds=40.0,
        tail_max_seconds=20.0,
        reaction_min_intensity="medium",
    )

    assert result["payoff_tails"] == []
    assert result["payoff_tail_audit"]["evaluations"][0]["best_reaction_intensity"] == "LOW"
    assert result["payoff_tail_audit"]["evaluations"][0]["reaction_gate_pass"] is False
