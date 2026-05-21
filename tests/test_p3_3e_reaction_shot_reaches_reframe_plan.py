"""
P3-3E Wirkungsbeweis: Reaction Shot Signal landet als Layout-Switch im ReframePlan.
"""

from types import SimpleNamespace

import pytest

from core.timeline_signal_consumer import SIGNAL_REACTION_SHOT
from models.reframe_plan import ReframePlan


def test_reaction_shot_adds_layout_switch_to_reframe_plan_stub():
    """Job mit Reaction-Shot-Signal -> Stub-Plan enthaelt layout_switch-Dict."""
    pytest.importorskip("core.reaction_shot_reframe_applier")
    from core.reaction_shot_reframe_applier import apply_reaction_shots_to_reframe_plan

    job = SimpleNamespace(
        unified_edit_signals=[
            {
                "signal_type": SIGNAL_REACTION_SHOT,
                "can_insert_clip": True,
                "placement_score": 0.8,
                "suggested_position": 42.5,
            }
        ]
    )

    reframe_plan = SimpleNamespace(instructions=[], plan_notes=[])
    result = apply_reaction_shots_to_reframe_plan(reframe_plan, job)

    layout_switches = [
        instruction
        for instruction in result.instructions
        if isinstance(instruction, dict) and instruction.get("type") == "layout_switch"
    ]

    assert len(layout_switches) == 1
    assert layout_switches[0]["layout"] == "facecam_emphasis"
    assert layout_switches[0]["at_seconds"] == 42.5
    assert layout_switches[0]["placement_score"] == 0.8


def test_reaction_shot_adds_framing_instruction_to_real_reframe_plan():
    """Echter ReframePlan bekommt FramingInstruction statt Dict."""
    pytest.importorskip("core.reaction_shot_reframe_applier")
    from core.reaction_shot_reframe_applier import apply_reaction_shots_to_reframe_plan

    job = SimpleNamespace(
        job_id="job_1",
        unified_edit_signals=[
            {
                "signal_type": SIGNAL_REACTION_SHOT,
                "can_insert_clip": True,
                "trigger_segment_id": "seg_1",
                "placement_score": 0.85,
                "suggested_position": 12.25,
            }
        ],
    )
    reframe_plan = ReframePlan(
        plan_id="plan_1",
        job_id="job_1",
        timeline_id="timeline_1",
        source_aspect_ratio="32:9",
        primary_target_aspect_ratio="16:9",
        instructions=[],
        plan_notes=[],
    )

    result = apply_reaction_shots_to_reframe_plan(reframe_plan, job)

    assert len(result.instructions) == 1
    instruction = result.instructions[0]
    assert instruction.segment_id == "seg_1"
    assert instruction.focus_kind == "facecam_emphasis"
    assert instruction.layout_kind == "facecam_emphasis"
    assert instruction.metadata["type"] == "layout_switch"
    assert instruction.metadata["at_seconds"] == 12.25
    assert instruction.metadata["placement_score"] == 0.85


def test_reaction_shot_below_threshold_is_ignored():
    """Signal mit placement_score < 0.3 wird ignoriert."""
    pytest.importorskip("core.reaction_shot_reframe_applier")
    from core.reaction_shot_reframe_applier import apply_reaction_shots_to_reframe_plan

    job = SimpleNamespace(
        unified_edit_signals=[
            {
                "signal_type": SIGNAL_REACTION_SHOT,
                "can_insert_clip": True,
                "placement_score": 0.1,
                "suggested_position": 10.0,
            }
        ]
    )

    reframe_plan = SimpleNamespace(instructions=[])
    result = apply_reaction_shots_to_reframe_plan(reframe_plan, job)

    assert result.instructions == []


def test_reaction_shot_no_signals_plan_unchanged():
    """Kein Signal -> Plan bleibt unveraendert, kein Crash."""
    pytest.importorskip("core.reaction_shot_reframe_applier")
    from core.reaction_shot_reframe_applier import apply_reaction_shots_to_reframe_plan

    job = SimpleNamespace(unified_edit_signals=[])
    reframe_plan = SimpleNamespace(instructions=["existing"])

    result = apply_reaction_shots_to_reframe_plan(reframe_plan, job)

    assert result.instructions == ["existing"]


def test_reaction_shot_none_plan_returns_none():
    """reframe_plan=None -> None zurueck, kein Crash."""
    pytest.importorskip("core.reaction_shot_reframe_applier")
    from core.reaction_shot_reframe_applier import apply_reaction_shots_to_reframe_plan

    result = apply_reaction_shots_to_reframe_plan(
        None,
        SimpleNamespace(unified_edit_signals=[]),
    )

    assert result is None
