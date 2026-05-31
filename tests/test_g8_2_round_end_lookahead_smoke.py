from __future__ import annotations

from core.g8_block_assembly import G8BlockAssemblyPlanner


def test_g8_2_state_aware_stable_lobby_closes_after_enough_active_round_context():
    planner = G8BlockAssemblyPlanner(
        bridge_seconds=20.0,
        min_standalone_block_seconds=0.0,
        round_gap_seconds=45.0,
        lobby_min_seconds=5.0,
        lobby_boundary_min_active_seconds=80.0,
    )

    play_segments = [
        {"start_seconds": 0.0, "end_seconds": 90.0, "state": "active_play", "confidence": 0.8},
        {"start_seconds": 90.0, "end_seconds": 104.0, "state": "intro_menu_lobby", "confidence": 0.8},
        {"start_seconds": 104.0, "end_seconds": 120.0, "state": "active_play", "confidence": 0.8},
    ]

    blocks = planner.build_blocks(planner.normalize_play_segments(play_segments))

    assert len(blocks) == 2
    assert blocks[0].start_seconds == 0.0
    assert blocks[0].end_seconds == 90.0
    assert blocks[1].start_seconds == 104.0
    assert blocks[1].end_seconds == 120.0


def test_g8_2_stable_lobby_before_enough_active_context_does_not_close_block():
    planner = G8BlockAssemblyPlanner(
        bridge_seconds=20.0,
        min_standalone_block_seconds=0.0,
        round_gap_seconds=45.0,
        lobby_min_seconds=5.0,
        lobby_boundary_min_active_seconds=80.0,
    )

    play_segments = [
        {"start_seconds": 0.0, "end_seconds": 76.0, "state": "active_play", "confidence": 0.8},
        {"start_seconds": 76.0, "end_seconds": 96.0, "state": "intro_menu_lobby", "confidence": 0.8},
        {"start_seconds": 96.0, "end_seconds": 120.0, "state": "active_play", "confidence": 0.8},
    ]

    blocks = planner.build_blocks(planner.normalize_play_segments(play_segments))

    assert len(blocks) == 1
    assert blocks[0].start_seconds == 0.0
    assert blocks[0].end_seconds == 120.0


def test_g8_2_non_lobby_lull_with_next_active_within_round_gap_is_bridged():
    planner = G8BlockAssemblyPlanner(
        bridge_seconds=20.0,
        min_standalone_block_seconds=0.0,
        round_gap_seconds=45.0,
        lobby_min_seconds=5.0,
        lobby_boundary_min_active_seconds=80.0,
    )

    play_segments = [
        {"start_seconds": 80.0, "end_seconds": 142.0, "state": "active_play", "confidence": 0.8},
        {"start_seconds": 142.0, "end_seconds": 166.0, "state": "transition_dead_time", "confidence": 0.8},
        {"start_seconds": 166.0, "end_seconds": 172.0, "state": "active_play", "confidence": 0.8},
    ]

    blocks = planner.build_blocks(planner.normalize_play_segments(play_segments))

    assert len(blocks) == 1
    assert blocks[0].start_seconds == 80.0
    assert blocks[0].end_seconds == 172.0
    assert (80.0, 142.0) in blocks[0].active_ranges
    assert (166.0, 172.0) in blocks[0].active_ranges


def test_g8_2_short_lobby_blip_below_lobby_min_does_not_close_block():
    planner = G8BlockAssemblyPlanner(
        bridge_seconds=20.0,
        min_standalone_block_seconds=0.0,
        round_gap_seconds=45.0,
        lobby_min_seconds=5.0,
        lobby_boundary_min_active_seconds=80.0,
    )

    play_segments = [
        {"start_seconds": 0.0, "end_seconds": 90.0, "state": "active_play", "confidence": 0.8},
        {"start_seconds": 90.0, "end_seconds": 92.0, "state": "intro_menu_lobby", "confidence": 0.8},
        {"start_seconds": 92.0, "end_seconds": 100.0, "state": "transition_dead_time", "confidence": 0.8},
        {"start_seconds": 100.0, "end_seconds": 120.0, "state": "active_play", "confidence": 0.8},
    ]

    blocks = planner.build_blocks(planner.normalize_play_segments(play_segments))

    assert len(blocks) == 1
    assert blocks[0].start_seconds == 0.0
    assert blocks[0].end_seconds == 120.0


def test_g8_2_closes_round_when_next_active_is_beyond_round_gap():
    planner = G8BlockAssemblyPlanner(
        bridge_seconds=20.0,
        min_standalone_block_seconds=0.0,
        round_gap_seconds=45.0,
        lobby_min_seconds=5.0,
        lobby_boundary_min_active_seconds=80.0,
    )

    play_segments = [
        {"start_seconds": 0.0, "end_seconds": 10.0, "state": "active_play", "confidence": 0.8},
        {"start_seconds": 10.0, "end_seconds": 60.0, "state": "transition_dead_time", "confidence": 0.8},
        {"start_seconds": 60.0, "end_seconds": 80.0, "state": "active_play", "confidence": 0.8},
    ]

    blocks = planner.build_blocks(planner.normalize_play_segments(play_segments))

    assert len(blocks) == 2
    assert blocks[0].start_seconds == 0.0
    assert blocks[0].end_seconds == 10.0
    assert blocks[1].start_seconds == 60.0
    assert blocks[1].end_seconds == 80.0


def test_g8_2_build_plan_keeps_tail_active_and_trims_internal_lull():
    planner = G8BlockAssemblyPlanner(
        bridge_seconds=20.0,
        min_standalone_block_seconds=0.0,
        round_gap_seconds=45.0,
        lobby_min_seconds=5.0,
        lobby_boundary_min_active_seconds=80.0,
    )

    plan = planner.build_plan(
        label="g8_2_tail_test",
        play_segments=[
            {"start_seconds": 80.0, "end_seconds": 120.0, "state": "active_play", "confidence": 0.8},
            {"start_seconds": 120.0, "end_seconds": 134.0, "state": "transition_dead_time", "confidence": 0.8},
            {"start_seconds": 134.0, "end_seconds": 142.0, "state": "active_play", "confidence": 0.8},
            {"start_seconds": 142.0, "end_seconds": 166.0, "state": "transition_dead_time", "confidence": 0.8},
            {"start_seconds": 166.0, "end_seconds": 172.0, "state": "active_play", "confidence": 0.8},
        ],
    )

    assert plan.anti_overcut_fail_count == 0
    assert len(plan.selected_blocks) == 1
    assert plan.selected_blocks[0].start_seconds == 80.0
    assert plan.selected_blocks[0].end_seconds == 172.0

    rendered_ranges = [
        (segment.start_seconds, segment.end_seconds)
        for segment in plan.timeline_segments
    ]

    assert (80.0, 120.0) in rendered_ranges
    assert (134.0, 142.0) in rendered_ranges
    assert (166.0, 172.0) in rendered_ranges
    assert (142.0, 166.0) not in rendered_ranges
