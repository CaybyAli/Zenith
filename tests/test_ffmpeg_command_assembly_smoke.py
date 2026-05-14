from __future__ import annotations

from copy import deepcopy

from core.ffmpeg_command_assembly import build_ffmpeg_command_assembly_report


def _ready_job() -> dict:
    return {
        "job_id": "ffmpeg-command-assembly-smoke",
        "ffmpeg_capability_resolver_report": {"status": "ffmpeg_capability_ready"},
        "ffmpeg_capability_status": "ffmpeg_capability_ready",
        "ffmpeg_path_hint": r"D:\Tools\ffmpeg\bin\ffmpeg.exe",
        "ffmpeg_can_prepare_real_render_tools": True,
        "ffmpeg_can_render": False,
        "ffmpeg_can_process_media": False,
        "ffmpeg_can_write_media": False,
        "ffmpeg_can_probe_media_files": False,
        "render_execution_permission_report": {
            "status": "render_execution_permission_ready"
        },
        "render_execution_permission_status": "render_execution_permission_ready",
        "render_execution_ready_for_real_render_stage": True,
        "render_execution_can_prepare_real_render_execution": True,
        "render_execution_human_approved": True,
        "controlled_render_executor_report": {
            "status": "controlled_render_executor_dry_run_ready"
        },
        "controlled_render_executor_status": "controlled_render_executor_dry_run_ready",
        "controlled_render_dry_run_only": True,
        "controlled_render_output_created": False,
        "render_blueprint_non_executable": True,
        "render_blueprint_steps": [
            {"step_id": "bp_trim_1", "step_type": "trim_concat"},
            {"step_id": "bp_audio_1", "step_type": "audio_mix"},
            {"step_id": "bp_subtitle_1", "step_type": "subtitle"},
            {"step_id": "bp_encode_1", "step_type": "encode"},
        ],
        "render_asset_paths_are_hints_only": True,
        "render_asset_can_write_files": False,
        "render_plan_segments": [{"segment_id": "seg_1"}],
        "render_plan_output_targets": [{"target_id": "target_1"}],
        "render_plan_operation_intents": [{"intent_type": "trim_concat"}],
    }


def test_blocks_when_ffmpeg_capability_report_is_missing() -> None:
    job = _ready_job()
    job["ffmpeg_capability_resolver_report"] = {}

    report = build_ffmpeg_command_assembly_report(job)
    data = report.to_dict()

    assert data["status"] == "ffmpeg_command_assembly_blocked"
    assert "ffmpeg_capability_resolver_report_missing" in data["blocking_reasons"]
    assert data["ready_for_controlled_execution_stage"] is False
    assert data["can_render"] is False


def test_blocks_when_ffmpeg_capability_status_is_blocked_or_failed() -> None:
    for status in ["ffmpeg_capability_blocked", "ffmpeg_capability_failed"]:
        job = _ready_job()
        job["ffmpeg_capability_status"] = status

        report = build_ffmpeg_command_assembly_report(job)
        data = report.to_dict()

        assert data["status"] == "ffmpeg_command_assembly_blocked"
        assert "ffmpeg_capability_status_not_ready" in data["blocking_reasons"]


def test_blocks_when_ffmpeg_can_prepare_real_render_tools_is_false() -> None:
    job = _ready_job()
    job["ffmpeg_can_prepare_real_render_tools"] = False

    report = build_ffmpeg_command_assembly_report(job)
    data = report.to_dict()

    assert data["status"] == "ffmpeg_command_assembly_blocked"
    assert "ffmpeg_can_prepare_real_render_tools_false" in data["blocking_reasons"]


def test_blocks_when_ffmpeg_media_permissions_are_true() -> None:
    cases = [
        ("ffmpeg_can_render", "ffmpeg_can_render_true_blocked"),
        ("ffmpeg_can_process_media", "ffmpeg_can_process_media_true_blocked"),
        ("ffmpeg_can_write_media", "ffmpeg_can_write_media_true_blocked"),
        ("ffmpeg_can_probe_media_files", "ffmpeg_can_probe_media_files_true_blocked"),
    ]

    for field, reason in cases:
        job = _ready_job()
        job[field] = True

        report = build_ffmpeg_command_assembly_report(job)
        data = report.to_dict()

        assert data["status"] == "ffmpeg_command_assembly_blocked"
        assert reason in data["blocking_reasons"]


def test_blocks_when_render_execution_permission_is_missing_or_not_approved() -> None:
    job = _ready_job()
    job["render_execution_permission_report"] = {}

    missing_report = build_ffmpeg_command_assembly_report(job).to_dict()
    assert missing_report["status"] == "ffmpeg_command_assembly_blocked"
    assert "render_execution_permission_report_missing" in missing_report["blocking_reasons"]

    job = _ready_job()
    job["render_execution_human_approved"] = False

    missing_approval = build_ffmpeg_command_assembly_report(job).to_dict()
    assert missing_approval["status"] == "ffmpeg_command_assembly_blocked"
    assert "render_execution_human_approved_false" in missing_approval["blocking_reasons"]


def test_blocks_when_controlled_executor_is_not_dry_run_or_output_was_created() -> None:
    job = _ready_job()
    job["controlled_render_dry_run_only"] = False

    not_dry_run = build_ffmpeg_command_assembly_report(job).to_dict()
    assert not_dry_run["status"] == "ffmpeg_command_assembly_blocked"
    assert "controlled_render_dry_run_only_false" in not_dry_run["blocking_reasons"]

    job = _ready_job()
    job["controlled_render_output_created"] = True

    output_created = build_ffmpeg_command_assembly_report(job).to_dict()
    assert output_created["status"] == "ffmpeg_command_assembly_blocked"
    assert "controlled_render_output_created_true_blocked" in output_created["blocking_reasons"]


def test_ready_report_builds_argv_preview_tokens_and_stays_non_executable() -> None:
    report = build_ffmpeg_command_assembly_report(_ready_job())
    data = report.to_dict()

    assert data["status"] == "ffmpeg_command_assembly_ready_with_warnings"
    assert data["total_assemblies"] >= 1
    assert data["safe_assembly_count"] == data["total_assemblies"]
    assert data["blocked_assembly_count"] == 0
    assert data["ready_for_controlled_execution_stage"] is True

    assert data["dry_run_only"] is True
    assert data["assembly_only"] is True
    assert data["preview_only"] is True
    assert data["can_execute_commands"] is False
    assert data["can_spawn_process"] is False
    assert data["can_render"] is False
    assert data["can_write_media"] is False
    assert data["can_probe_media_files"] is False

    first = data["assemblies"][0]
    assert isinstance(first["argv_preview"], list)
    assert first["argv_preview"][0] == r"D:\Tools\ffmpeg\bin\ffmpeg.exe"
    assert isinstance(first["argument_tokens"], list)
    assert first["argument_tokens"]

    assert first["assembly_only"] is True
    assert first["preview_only"] is True
    assert first["can_execute_command"] is False
    assert first["can_spawn_process"] is False
    assert first["can_render"] is False
    assert first["can_write_media"] is False


def test_blocks_shell_markers_path_traversal_url_and_empty_argv() -> None:
    job = _ready_job()
    job["ffmpeg_path_hint"] = r"D:\Tools\ffmpeg\bin\ffmpeg.exe & calc"

    shell_marker = build_ffmpeg_command_assembly_report(job).to_dict()
    assert shell_marker["status"] == "ffmpeg_command_assembly_blocked"
    assert "argument_shell_marker_blocked" in shell_marker["blocking_reasons"]

    job = _ready_job()
    job["ffmpeg_path_hint"] = r"D:\Tools\..\evil\ffmpeg.exe"

    path_traversal = build_ffmpeg_command_assembly_report(job).to_dict()
    assert path_traversal["status"] == "ffmpeg_command_assembly_blocked"
    assert "argument_path_traversal_blocked" in path_traversal["blocking_reasons"]

    job = _ready_job()
    job["ffmpeg_path_hint"] = "https://example.test/ffmpeg.exe"

    url = build_ffmpeg_command_assembly_report(job).to_dict()
    assert url["status"] == "ffmpeg_command_assembly_blocked"
    assert "argument_url_blocked" in url["blocking_reasons"]

    from core.ffmpeg_command_assembly import _validate_argv

    _, reasons = _validate_argv([], r"D:\Tools\ffmpeg\bin\ffmpeg.exe")
    assert "argv_preview_empty" in reasons


def test_model_from_dict_preserves_safe_false_fields() -> None:
    from models.ffmpeg_command_assembly import FFmpegCommandAssemblyReport

    data = {
        "report_id": "unsafe-input",
        "job_id": "job-1",
        "can_execute_commands": True,
        "can_spawn_process": True,
        "can_render": True,
        "can_write_media": True,
        "can_probe_media_files": True,
        "ready_for_controlled_execution_stage": True,
    }

    report = FFmpegCommandAssemblyReport.from_dict(deepcopy(data))
    loaded = report.to_dict()

    assert loaded["ready_for_controlled_execution_stage"] is True
    assert loaded["can_execute_commands"] is False
    assert loaded["can_spawn_process"] is False
    assert loaded["can_render"] is False
    assert loaded["can_write_media"] is False
    assert loaded["can_probe_media_files"] is False
