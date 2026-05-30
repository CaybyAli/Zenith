from __future__ import annotations

from core.g8_block_assembly import G8BlockAssemblyPlanner


def test_g8_1_discards_isolated_micro_block_before_selection() -> None:
    play_segments = [
        {"start_seconds": 0.0, "end_seconds": 700.0, "state": "active_play", "confidence": 0.8},
        {"start_seconds": 700.0, "end_seconds": 750.0, "state": "intro_menu_lobby", "confidence": 0.8},
        {"start_seconds": 750.0, "end_seconds": 754.0, "state": "active_play", "confidence": 1.0},
        {"start_seconds": 754.0, "end_seconds": 800.0, "state": "intro_menu_lobby", "confidence": 0.8},
        {"start_seconds": 800.0, "end_seconds": 840.0, "state": "active_play", "confidence": 0.8},
    ]

    plan = G8BlockAssemblyPlanner(
        bridge_seconds=20.0,
        min_standalone_block_seconds=12.0,
    ).build_plan(label="g8_1_micro_discard", play_segments=play_segments)

    data = plan.to_dict()
    filter_report = data["minimum_standalone_block_filter"]

    assert plan.anti_overcut_fail_count == 0
    assert filter_report["before_block_count"] == 3
    assert filter_report["after_block_count"] == 2
    assert filter_report["discarded_count"] == 1
    assert filter_report["expanded_count"] == 0
    assert plan.planned_output_duration_seconds == 740.0
    assert plan.planned_output_duration_seconds >= 720.0

    assert any(
        action["action"] == "discarded_isolated_micro_block"
        and action["block_id"] == "g8_block_002"
        for action in filter_report["actions"]
    )
    assert all(
        block["keep_active_budget_seconds"] >= 12.0
        for block in filter_report["after_blocks"]
    )
    assert not any(
        block["start_seconds"] == 750.0 and block["end_seconds"] == 754.0
        for block in filter_report["after_blocks"]
    )


def test_g8_1_high_quality_does_not_rescue_isolated_micro_block() -> None:
    play_segments = [
        {"start_seconds": 0.0, "end_seconds": 720.0, "state": "active_play", "confidence": 0.7},
        {"start_seconds": 720.0, "end_seconds": 800.0, "state": "intro_menu_lobby", "confidence": 0.8},
        {"start_seconds": 800.0, "end_seconds": 804.0, "state": "active_play", "confidence": 1.0},
    ]
    highlights = [
        {"start_seconds": 800.0, "end_seconds": 804.0, "highlight_score": 1.0},
    ]

    plan = G8BlockAssemblyPlanner(
        bridge_seconds=20.0,
        min_standalone_block_seconds=12.0,
    ).build_plan(
        label="g8_1_high_quality_micro",
        play_segments=play_segments,
        highlights=highlights,
    )

    filter_report = plan.to_dict()["minimum_standalone_block_filter"]

    assert plan.anti_overcut_fail_count == 0
    assert filter_report["discarded_count"] == 1
    assert filter_report["actions"][0]["quality_does_not_override_minimum_standalone_duration"] is True
    assert not any(
        block["start_seconds"] == 800.0 and block["end_seconds"] == 804.0
        for block in filter_report["after_blocks"]
    )
