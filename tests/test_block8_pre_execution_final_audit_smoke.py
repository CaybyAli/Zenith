from __future__ import annotations

from pathlib import Path


AUDIT_TEST_FILES = [
    "tests/test_block8_pre_execution_static_audit_smoke.py",
    "tests/test_block8_pre_execution_pipeline_order_audit_smoke.py",
    "tests/test_block8_pre_execution_safety_contract_audit_smoke.py",
    "tests/test_block8_pre_execution_registry_audit_smoke.py",
    "tests/test_block8_pre_execution_job_fields_audit_smoke.py",
    "tests/test_block8_pre_execution_final_audit_smoke.py",
]

BLOCK8_CORE_AND_MODEL_FILES = [
    "models/render_readiness_guard.py",
    "core/render_readiness_guard.py",
    "core/render_readiness_guard_runner.py",
    "core/render_readiness_guard_signal_adapter.py",
    "models/render_plan.py",
    "core/render_plan_builder.py",
    "core/render_plan_runner.py",
    "core/render_plan_signal_adapter.py",
    "models/render_command_blueprint.py",
    "core/render_command_blueprint_builder.py",
    "core/render_command_blueprint_runner.py",
    "core/render_command_blueprint_signal_adapter.py",
    "models/render_asset_manifest.py",
    "core/render_asset_manifest_builder.py",
    "core/render_asset_manifest_runner.py",
    "core/render_asset_manifest_signal_adapter.py",
    "models/render_execution_permission_gate.py",
    "core/render_execution_permission_gate.py",
    "core/render_execution_permission_gate_runner.py",
    "core/render_execution_permission_gate_signal_adapter.py",
    "models/controlled_render_executor.py",
    "core/controlled_render_executor.py",
    "core/controlled_render_executor_runner.py",
    "core/controlled_render_executor_signal_adapter.py",
]


def test_2b51_audit_suite_files_exist_with_clean_encoding() -> None:
    problems = []
    for rel in AUDIT_TEST_FILES:
        path = Path(rel)
        if not path.is_file():
            problems.append(f"{rel}:missing")
            continue

        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            problems.append(f"{rel}:bom")
        if not raw.endswith((b"\n", b"\r\n")):
            problems.append(f"{rel}:missing_newline")

    assert problems == []


def test_2b51_final_audit_keeps_scope_to_tests_only() -> None:
    for rel in BLOCK8_CORE_AND_MODEL_FILES:
        assert Path(rel).is_file(), rel

    for rel in AUDIT_TEST_FILES:
        text = Path(rel).read_text(encoding="utf-8")
        assert "pytest" in text or "assert" in text


def test_2b51_audit_documents_all_six_block8_stages() -> None:
    combined = "\n".join(Path(rel).read_text(encoding="utf-8") for rel in AUDIT_TEST_FILES)

    required_stage_tokens = [
        "2B-45",
        "2B-46",
        "2B-47",
        "2B-48",
        "2B-49",
        "2B-50",
        "render_readiness",
        "render_plan",
        "render_blueprint",
        "render_asset",
        "render_execution",
        "controlled_render",
    ]

    missing = [token for token in required_stage_tokens if token not in combined]
    assert missing == []


def test_2b51_final_audit_confirms_no_real_render_contract() -> None:
    combined = "\n".join(Path(rel).read_text(encoding="utf-8") for rel in AUDIT_TEST_FILES)

    required_safety_tokens = [
        "dry_run_only",
        "non_executable",
        "paths_are_hints_only",
        "final_human_approval_gate",
        "executed_step_count",
        "output_created",
        "can_execute_real_render",
        "can_run_ffmpeg",
        "can_spawn_process",
        "can_write_media",
        "can_apply_timeline",
    ]

    missing = [token for token in required_safety_tokens if token not in combined]
    assert missing == []
