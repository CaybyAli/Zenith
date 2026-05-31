
from __future__ import annotations

from core.g8_block_assembly import G8BlockAssemblyPlanner, G8TimelinePlanSegment


def test_g8_builds_block_plan_breaks_540s_cap_and_keeps_chronological_blocks() -> None:
    play_segments = [
        {"start_seconds": 0.0, "end_seconds": 10.0, "state": "intro_menu_lobby", "confidence": 0.9},
        {"start_seconds": 10.0, "end_seconds": 310.0, "state": "active_play", "intensity": "high", "confidence": 0.86},
        {"start_seconds": 310.0, "end_seconds": 315.0, "state": "transition_dead_time", "confidence": 0.8},
        {"start_seconds": 315.0, "end_seconds": 620.0, "state": "active_play", "intensity": "medium", "confidence": 0.82},
        {"start_seconds": 620.0, "end_seconds": 660.0, "state": "intro_menu_lobby", "confidence": 0.8},
        {"start_seconds": 660.0, "end_seconds": 1040.0, "state": "active_play", "intensity": "high", "confidence": 0.84},
    ]
    g7a_spans = [
        {
            "start_seconds": 100.0,
            "end_seconds": 110.0,
            "decision": "trimmable_low_engagement",
            "confidence": 1.0,
        }
    ]
    highlights = [
        {"start_seconds": 10.0, "end_seconds": 620.0, "highlight_score": 0.88},
        {"start_seconds": 660.0, "end_seconds": 1040.0, "highlight_score": 0.80},
    ]

    plan = G8BlockAssemblyPlanner(bridge_seconds=8.0, round_gap_seconds=20.0).build_plan(
        label="synthetic_long",
        play_segments=play_segments,
        g7a_spans=g7a_spans,
        highlights=highlights,
    )
    data = plan.to_dict()

    assert plan.anti_overcut_fail_count == 0
    assert plan.planned_output_duration_seconds >= 720.0
    assert plan.planned_output_duration_seconds > 540.0
    assert data["old_vs_new"]["old_performance_stop_92_seconds"] == 496.8
    assert data["old_vs_new"]["performance_cap_removed_for_longform"] is True

    selected_blocks = data["selected_blocks"]
    assert len(selected_blocks) == 2
    assert selected_blocks[0]["start_seconds"] == 10.0
    assert selected_blocks[0]["end_seconds"] == 620.0
    assert selected_blocks[1]["start_seconds"] == 660.0
    assert selected_blocks[1]["end_seconds"] == 1040.0

    timeline_segments = data["timeline_segments"]
    assert all(item["state"] == "active_play" for item in timeline_segments)
    assert any(item["start_seconds"] == 10.0 and item["end_seconds"] == 100.0 for item in timeline_segments)
    assert any(item["start_seconds"] == 110.0 and item["end_seconds"] == 310.0 for item in timeline_segments)
    assert all(item["start_seconds"] < item["end_seconds"] for item in timeline_segments)


def test_g8_long_non_active_gap_creates_block_boundary() -> None:
    play_segments = [
        {"start_seconds": 0.0, "end_seconds": 100.0, "state": "active_play", "confidence": 0.8},
        {"start_seconds": 100.0, "end_seconds": 106.0, "state": "transition_dead_time", "confidence": 0.8},
        {"start_seconds": 106.0, "end_seconds": 200.0, "state": "active_play", "confidence": 0.8},
        {"start_seconds": 200.0, "end_seconds": 240.0, "state": "intro_menu_lobby", "confidence": 0.8},
        {"start_seconds": 240.0, "end_seconds": 360.0, "state": "active_play", "confidence": 0.8},
    ]

    planner = G8BlockAssemblyPlanner(bridge_seconds=8.0, round_gap_seconds=20.0)
    blocks = planner.build_blocks(planner.normalize_play_segments(play_segments))

    assert len(blocks) == 2
    assert blocks[0].start_seconds == 0.0
    assert blocks[0].end_seconds == 200.0
    assert blocks[1].start_seconds == 240.0
    assert blocks[1].end_seconds == 360.0


def test_g8_audit_fails_on_uncovered_active_play_gap() -> None:
    planner = G8BlockAssemblyPlanner()
    play_segments = [
        {"start_seconds": 0.0, "end_seconds": 300.0, "state": "active_play", "confidence": 0.9},
    ]
    blocks = planner.build_blocks(planner.normalize_play_segments(play_segments))
    block = blocks[0]

    timeline_segments = [
        G8TimelinePlanSegment(
            segment_id="manual_001",
            block_id=block.block_id,
            start_seconds=0.0,
            end_seconds=100.0,
            state="active_play",
            keep_decision="keep_active",
        ),
        G8TimelinePlanSegment(
            segment_id="manual_002",
            block_id=block.block_id,
            start_seconds=130.0,
            end_seconds=300.0,
            state="active_play",
            keep_decision="keep_active",
        ),
    ]
    trim_spans = planner.normalize_g7a_trim_spans(
        [
            {
                "start_seconds": 110.0,
                "end_seconds": 120.0,
                "decision": "trimmable_low_engagement",
            }
        ]
    )

    issues = planner.audit_active_play_gaps(
        selected_blocks=[block],
        timeline_segments=timeline_segments,
        trim_spans=trim_spans,
    )

    assert len(issues) == 1
    assert issues[0].uncovered_active_seconds > 0.5

