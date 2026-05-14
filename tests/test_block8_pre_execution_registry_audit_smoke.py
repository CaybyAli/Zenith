from __future__ import annotations

from pathlib import Path

from core.unified_edit_signal_registry import build_unified_edit_signal_result


EXPECTED_SOURCES = {
    "render_readiness_guard",
    "render_plan",
    "render_command_blueprint",
    "render_asset_manifest",
    "render_execution_permission_gate",
    "controlled_render_executor",
}

EXPECTED_SIGNAL_TYPES = {
    "render_readiness_ready",
    "render_readiness_ready_for_next_stage",
    "render_plan_ready",
    "render_plan_segment_planned",
    "render_plan_contract_ready",
    "render_blueprint_ready",
    "render_blueprint_step_planned",
    "render_blueprint_non_executable_confirmed",
    "render_blueprint_contract_ready",
    "render_asset_manifest_ready",
    "render_asset_reference_planned",
    "render_output_path_planned",
    "render_asset_paths_hint_only_confirmed",
    "render_execution_permission_ready",
    "render_execution_ready_for_real_render_stage",
    "render_execution_real_render_still_not_allowed_here",
    "controlled_render_executor_dry_run_ready",
    "controlled_render_execution_step_planned",
    "controlled_render_dry_run_only_confirmed",
    "controlled_render_real_render_not_allowed_here",
}


def _job_with_all_block8_reports() -> dict:
    return {
        "render_readiness_guard_report": {
            "status": "render_readiness_ready",
            "checks": [],
        },
        "render_plan_report": {
            "status": "render_plan_ready",
            "ready_for_renderer_contract": True,
            "segments": [
                {
                    "segment_id": "seg_1",
                    "source_start_seconds": 0.0,
                    "source_end_seconds": 8.0,
                    "output_start_seconds": 0.0,
                    "output_end_seconds": 8.0,
                    "duration_seconds": 8.0,
                    "blocking_reasons": [],
                }
            ],
            "output_targets": [],
            "operation_intents": [],
            "warnings": [],
            "blocking_reasons": [],
        },
        "render_command_blueprint_report": {
            "status": "render_blueprint_ready",
            "ready_for_renderer_implementation": True,
            "non_executable": True,
            "blueprint_steps": [
                {
                    "step_id": "bp_step_1",
                    "step_type": "trim",
                    "order_index": 1,
                    "source_segment_id": "seg_1",
                    "can_execute_now": False,
                    "requires_renderer_implementation": True,
                }
            ],
            "blocking_reasons": [],
        },
        "render_asset_manifest_report": {
            "status": "render_asset_manifest_ready",
            "manifest_only": True,
            "paths_are_hints_only": True,
            "can_render": False,
            "can_run_ffmpeg": False,
            "can_write_files": False,
            "asset_references": [
                {
                    "asset_id": "asset_1",
                    "asset_type": "source_video",
                    "required": True,
                    "path_hint": "hint_only",
                    "safety_status": "safe_hint",
                    "blocking_reasons": [],
                }
            ],
            "output_path_plans": [
                {
                    "output_id": "out_1",
                    "output_type": "video",
                    "platform": "youtube",
                    "safe_filename": "planned_name_only",
                    "path_safety_status": "safe_hint",
                    "blocking_reasons": [],
                }
            ],
            "blocking_reasons": [],
        },
        "render_execution_permission_report": {
            "status": "render_execution_permission_ready",
            "human_approved": True,
            "approved_by": "Hajar",
            "approved_at": "2026-05-14T00:00:00+00:00",
            "ready_for_real_render_stage": True,
            "can_prepare_real_render_execution": True,
            "can_render": False,
            "can_run_ffmpeg": False,
            "can_spawn_process": False,
            "can_write_media": False,
            "can_apply_timeline": False,
            "checks": [],
            "blocking_reasons": [],
        },
        "controlled_render_executor_report": {
            "status": "controlled_render_executor_dry_run_ready",
            "dry_run_only": True,
            "real_render_requested": False,
            "real_render_allowed": False,
            "can_execute_real_render": False,
            "can_render": False,
            "can_run_ffmpeg": False,
            "can_spawn_process": False,
            "can_write_media": False,
            "output_created": False,
            "execution_steps": [
                {
                    "step_id": "controlled_step_1",
                    "source_blueprint_step_id": "bp_step_1",
                    "step_type": "trim",
                    "execution_mode": "dry_run",
                    "executed": False,
                    "skipped_reason": "dry_run_only_in_2b_50",
                    "safety_status": "dry_run_only",
                }
            ],
            "blocking_reasons": [],
        },
    }


def test_registry_file_contains_all_block8_sources_and_collectors() -> None:
    text = Path("core/unified_edit_signal_registry.py").read_text(encoding="utf-8")

    required_tokens = [
        "SOURCE_RENDER_READINESS_GUARD",
        "SOURCE_RENDER_PLAN",
        "SOURCE_RENDER_COMMAND_BLUEPRINT",
        "SOURCE_RENDER_ASSET_MANIFEST",
        "SOURCE_RENDER_EXECUTION_PERMISSION_GATE",
        "SOURCE_CONTROLLED_RENDER_EXECUTOR",
        "build_render_readiness_guard_signals",
        "build_render_plan_signals",
        "build_render_command_blueprint_signals",
        "build_render_asset_manifest_signals",
        "build_render_execution_permission_gate_signals",
        "build_controlled_render_executor_signals",
    ]

    missing = [token for token in required_tokens if token not in text]
    assert missing == []


def test_registry_collects_signals_from_all_block8_modules() -> None:
    result = build_unified_edit_signal_result(
        _job_with_all_block8_reports(),
        dedup_tolerance_seconds=0.0,
        metadata={"audit": "2B-51"},
    )

    source_counts = dict(result.source_counts)
    missing_sources = [source for source in EXPECTED_SOURCES if source not in source_counts]
    assert missing_sources == []

    collected_signal_types = {signal["signal_type"] for signal in result.signals}
    missing_types = EXPECTED_SIGNAL_TYPES - collected_signal_types
    assert missing_types == set()
