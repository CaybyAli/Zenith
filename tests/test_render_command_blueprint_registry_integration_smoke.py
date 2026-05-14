from __future__ import annotations

from core.render_command_blueprint_signal_adapter import (
    build_render_command_blueprint_signals,
)
from core.unified_edit_signal_registry import (
    SOURCE_RENDER_COMMAND_BLUEPRINT,
    build_unified_edit_signal_result,
)


def _blueprint_report() -> dict:
    return {
        "status": "render_blueprint_ready",
        "ready_for_renderer_implementation": True,
        "dry_run_only": True,
        "non_executable": True,
        "can_execute_contract": False,
        "can_render": False,
        "can_run_ffmpeg": False,
        "can_spawn_process": False,
        "can_write_media": False,
        "blueprint_steps": [
            {
                "step_id": "render_blueprint_step_1",
                "step_type": "trim",
                "order_index": 1,
                "source_segment_id": "src_1",
                "target_segment_id": "seg_1",
                "can_execute_now": False,
                "requires_renderer_implementation": True,
            },
            {
                "step_id": "render_blueprint_step_2",
                "step_type": "encode",
                "order_index": 2,
                "target_segment_id": "output_target_main",
                "can_execute_now": False,
                "requires_renderer_implementation": True,
            },
        ],
        "warnings": [],
        "blocking_reasons": [],
    }


def test_signal_adapter_builds_render_blueprint_signals():
    job = {"render_command_blueprint_report": _blueprint_report()}

    signals = build_render_command_blueprint_signals(job)
    signal_types = {signal["signal_type"] for signal in signals}

    assert "render_blueprint_ready" in signal_types
    assert "render_blueprint_contract_ready" in signal_types
    assert "render_blueprint_non_executable_confirmed" in signal_types
    assert "render_blueprint_step_planned" in signal_types
    assert "render_blueprint_trim_step" in signal_types
    assert "render_blueprint_encode_step" in signal_types

    for signal in signals:
        assert signal["source"] == "render_command_blueprint"
        assert signal["action_hint"] == "review_render_command_blueprint"
        assert signal["metadata"]["non_executable"] is True
        assert signal["metadata"]["dry_run_only"] is True


def test_unified_registry_collects_render_blueprint_signals():
    job = {"render_command_blueprint_report": _blueprint_report()}

    result = build_unified_edit_signal_result(job)

    assert SOURCE_RENDER_COMMAND_BLUEPRINT in result.source_counts
    assert result.source_counts[SOURCE_RENDER_COMMAND_BLUEPRINT] >= 1
    assert any(
        signal["source"] == SOURCE_RENDER_COMMAND_BLUEPRINT
        for signal in result.signals
    )

