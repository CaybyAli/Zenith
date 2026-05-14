from __future__ import annotations

import re
from pathlib import Path


def _normalized_pipeline_text() -> str:
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")
    return re.sub(r'["\']\s+["\']', "", text)


def test_block8_pipeline_runner_order_is_final_and_safe() -> None:
    text = _normalized_pipeline_text()

    ordered_call_tokens = [
        "run_render_readiness_guard(",
        "run_render_plan_for_job(",
        "run_render_command_blueprint_for_job(",
        "run_render_asset_manifest_for_job(",
        "run_render_execution_permission_gate_for_job(",
        "run_controlled_render_executor_for_job(",
        "run_ff_tool_capability_resolver(",
        "run_ff_command_assembly_for_job(",
        "run_controlled_ff_exec_for_job(",
        "run_output_format_handler(",
        "run_render_verification_contract(",
        "run_render_dashboard_delivery_package(",
    ]

    positions = []
    for token in ordered_call_tokens:
        assert token in text, f"missing pipeline call: {token}"
        positions.append(text.index(token))

    assert positions == sorted(positions)


def test_block8_pipeline_imports_all_render_export_runners() -> None:
    text = _normalized_pipeline_text()

    required_import_concepts = [
        "core.render_readiness_guard_runner",
        "core.render_plan_runner",
        "core.render_command_blueprint_runner",
        "core.render_asset_manifest_runner",
        "core.render_execution_permission_gate_runner",
        "core.controlled_render_executor_runner",
        "core.ffmpeg_capability_resolver_runner",
        "core.ffmpeg_command_assembly_runner",
        "core.controlled_ffmpeg_execution_runner",
        "core.output_format_handler_runner",
        "core.render_verification_contract_runner",
        "core.render_dashboard_delivery_package_runner",
    ]

    for token in required_import_concepts:
        assert token in text, f"missing runner import concept: {token}"


def test_block8_pipeline_metadata_contains_all_safety_concepts() -> None:
    text = _normalized_pipeline_text()

    required_concepts = {
        "block8_render_export": ["block8_render_export"],
        "dry_run_only": ["dry_run_only"],
        "non_executable": ["non_executable"],
        "paths_are_hints_only": ["paths_are_hints_only", "path_hints_only", "hints_only"],
        "final_human_approval_gate": [
            "final_human_approval_gate",
            "render_execution_human_approved",
            "human_approval",
        ],
        "execution_steps_are_dry_run_only": [
            "execution_steps_are_dry_run_only",
            "controlled_render_executor",
            "dry_run_only",
        ],
        "controlled_tool_probe_only": ["controlled_tool_probe_only"],
        "ffmpeg_command_assembly_only": ["ffmpeg_command_assembly_only"],
        "controlled_ffmpeg_execution_gate": ["controlled_ffmpeg_execution_gate"],
        "output_format_contract_only": ["output_format_contract_only"],
        "render_verification_contract_only": ["render_verification_contract_only"],
        "render_dashboard_delivery_package_only": [
            "render_dashboard_delivery_package_only"
        ],
        "no_full_render": ["no_full_render", "no_full_render_in_2b"],
        "no_timeline_apply": ["no_timeline_apply"],
    }

    for concept, alternatives in required_concepts.items():
        assert any(token in text for token in alternatives), (
            f"missing pipeline metadata concept: {concept}"
        )


def test_2b51_has_no_pipeline_runner_between_block8_runtime_stages() -> None:
    text = _normalized_pipeline_text()

    assert "run_block8_pre_execution" not in text
    assert "block8_pre_execution_runner" not in text
