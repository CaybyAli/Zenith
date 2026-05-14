from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.controlled_ffmpeg_execution import (
    _build_internal_smoke_command,
    build_controlled_ffmpeg_execution_report,
    execute_controlled_ffmpeg_smoke_test,
)
from models.controlled_ffmpeg_execution import (
    MODE_SMOKE_TEST,
    STATUS_BLOCKED,
    STATUS_DRY_RUN_READY,
    STATUS_SMOKE_FAILED,
    STATUS_SMOKE_READY,
    STATUS_SMOKE_SUCCEEDED,
)


def _ready_job(**overrides):
    data = {
        "job_id": "job_2b54",
        "render_execution_permission_status": "render_execution_permission_ready",
        "render_execution_human_approved": True,
        "render_execution_ready_for_real_render_stage": True,
        "render_execution_can_prepare_real_render_execution": True,
        "render_execution_blocking_reasons": [],
        "ffmpeg_capability_status": "ffmpeg_capability_ready",
        "ffmpeg_path_hint": "C:/Tools/ffmpeg/bin/ffmpeg.exe",
        "ffmpeg_can_prepare_real_render_tools": True,
        "ffmpeg_can_render": False,
        "ffmpeg_can_process_media": False,
        "ffmpeg_can_write_media": False,
        "ffmpeg_blocking_reasons": [],
        "ffmpeg_command_assembly_status": "ffmpeg_command_assembly_ready",
        "ffmpeg_command_ready_for_controlled_execution_stage": True,
        "ffmpeg_command_can_execute_commands": False,
        "ffmpeg_command_can_spawn_process": False,
        "ffmpeg_command_can_render": False,
        "ffmpeg_command_can_write_media": False,
        "ffmpeg_command_blocking_reasons": [],
        "ffmpeg_execution_requested_mode": "dry_run",
        "ffmpeg_execution_allow_real_render": False,
        "ffmpeg_execution_allow_ffmpeg_execution": False,
        "ffmpeg_execution_allow_process_spawn": False,
        "ffmpeg_execution_allow_media_write": False,
        "ffmpeg_execution_smoke_duration_seconds": 1.0,
        "ffmpeg_execution_smoke_output_dir_hint": None,
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_default_stays_dry_run_and_never_creates_output():
    report = build_controlled_ffmpeg_execution_report(_ready_job())

    assert report.status == STATUS_DRY_RUN_READY
    assert report.dry_run_only is True
    assert report.real_execution_allowed is False
    assert report.real_execution_performed is False
    assert report.output_created is False
    assert report.can_execute_full_render is False
    assert report.can_render_timeline is False
    assert report.can_process_user_media is False
    assert report.can_write_project_output is False
    assert report.can_spawn_process is False


def test_missing_permission_gate_blocks():
    report = build_controlled_ffmpeg_execution_report(
        _ready_job(render_execution_permission_status=None)
    )

    assert report.status == STATUS_BLOCKED
    assert "render_execution_permission_not_ready" in report.blocking_reasons
    assert report.real_execution_performed is False


def test_missing_human_approval_blocks():
    report = build_controlled_ffmpeg_execution_report(
        _ready_job(render_execution_human_approved=False)
    )

    assert report.status == STATUS_BLOCKED
    assert "render_execution_human_approval_missing" in report.blocking_reasons


def test_missing_capability_gate_blocks():
    report = build_controlled_ffmpeg_execution_report(
        _ready_job(ffmpeg_capability_status=None)
    )

    assert report.status == STATUS_BLOCKED
    assert "ffmpeg_capability_not_ready" in report.blocking_reasons


def test_missing_command_assembly_gate_blocks():
    report = build_controlled_ffmpeg_execution_report(
        _ready_job(ffmpeg_command_assembly_status=None)
    )

    assert report.status == STATUS_BLOCKED
    assert "ffmpeg_command_assembly_not_ready" in report.blocking_reasons


def test_ffmpeg_can_prepare_real_render_tools_false_blocks():
    report = build_controlled_ffmpeg_execution_report(
        _ready_job(ffmpeg_can_prepare_real_render_tools=False)
    )

    assert report.status == STATUS_BLOCKED
    assert "ffmpeg_cannot_prepare_real_render_tools" in report.blocking_reasons


def test_command_ready_for_controlled_execution_false_blocks():
    report = build_controlled_ffmpeg_execution_report(
        _ready_job(ffmpeg_command_ready_for_controlled_execution_stage=False)
    )

    assert report.status == STATUS_BLOCKED
    assert (
        "ffmpeg_command_not_ready_for_controlled_execution_stage"
        in report.blocking_reasons
    )


def test_upstream_forbidden_media_permissions_block():
    report = build_controlled_ffmpeg_execution_report(
        _ready_job(ffmpeg_can_write_media=True)
    )

    assert report.status == STATUS_BLOCKED
    assert (
        "ffmpeg_write_media_permission_must_remain_false_before_2b54"
        in report.blocking_reasons
    )


def test_upstream_forbidden_command_permissions_block():
    report = build_controlled_ffmpeg_execution_report(
        _ready_job(ffmpeg_command_can_spawn_process=True)
    )

    assert report.status == STATUS_BLOCKED
    assert (
        "ffmpeg_command_spawn_permission_must_remain_false_before_2b54"
        in report.blocking_reasons
    )


def test_smoke_request_without_all_flags_blocks():
    report = build_controlled_ffmpeg_execution_report(
        _ready_job(
            ffmpeg_execution_requested_mode=MODE_SMOKE_TEST,
            ffmpeg_execution_allow_real_render=True,
            ffmpeg_execution_allow_ffmpeg_execution=True,
            ffmpeg_execution_allow_process_spawn=False,
            ffmpeg_execution_allow_media_write=True,
        )
    )

    assert report.status == STATUS_BLOCKED
    assert "allow_process_spawn_missing" in report.blocking_reasons
    assert report.real_execution_performed is False


def test_smoke_request_with_all_flags_becomes_smoke_ready():
    report = build_controlled_ffmpeg_execution_report(
        _ready_job(
            ffmpeg_execution_requested_mode=MODE_SMOKE_TEST,
            ffmpeg_execution_allow_real_render=True,
            ffmpeg_execution_allow_ffmpeg_execution=True,
            ffmpeg_execution_allow_process_spawn=True,
            ffmpeg_execution_allow_media_write=True,
        )
    )

    assert report.status == STATUS_SMOKE_READY
    assert report.dry_run_only is False
    assert report.smoke_test_only is True
    assert report.real_execution_requested is True
    assert report.real_execution_allowed is True
    assert report.real_execution_performed is False
    assert report.can_execute_full_render is False
    assert report.can_render_timeline is False
    assert report.can_process_user_media is False
    assert report.can_write_project_output is False


def test_internal_smoke_command_uses_lavfi_testsrc_sine_and_no_user_media(tmp_path):
    output_path = tmp_path / "smoke.mp4"
    command = _build_internal_smoke_command(
        ffmpeg_path="C:/Tools/ffmpeg/bin/ffmpeg.exe",
        output_path=output_path,
        duration_seconds=1.0,
    )

    joined = " ".join(command)
    assert command[0].endswith("ffmpeg.exe")
    assert "-f" in command
    assert "lavfi" in command
    assert "testsrc=size=320x180:rate=10:duration=1" in command
    assert "sine=frequency=1000:duration=1" in command
    assert str(output_path) == command[-1]
    assert "raw_video_path" not in joined
    assert "user_media" not in joined


def test_execute_smoke_uses_subprocess_safely_and_marks_output(monkeypatch, tmp_path):
    captured = {}

    class Completed:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(command, shell, capture_output, text, timeout, check):
        captured["command"] = command
        captured["shell"] = shell
        captured["capture_output"] = capture_output
        captured["text"] = text
        captured["timeout"] = timeout
        captured["check"] = check
        Path(command[-1]).write_bytes(b"fake mp4")
        return Completed()

    monkeypatch.setattr("core.controlled_ffmpeg_execution.subprocess.run", fake_run)

    report = execute_controlled_ffmpeg_smoke_test(
        _ready_job(
            ffmpeg_execution_requested_mode=MODE_SMOKE_TEST,
            ffmpeg_execution_allow_real_render=True,
            ffmpeg_execution_allow_ffmpeg_execution=True,
            ffmpeg_execution_allow_process_spawn=True,
            ffmpeg_execution_allow_media_write=True,
            ffmpeg_execution_smoke_output_dir_hint=str(tmp_path / "smoke"),
        )
    )

    assert report.status == STATUS_SMOKE_SUCCEEDED
    assert captured["shell"] is False
    assert captured["capture_output"] is True
    assert captured["timeout"] == 15
    assert captured["check"] is False
    assert "lavfi" in captured["command"]
    assert any("testsrc" in item for item in captured["command"])
    assert any("sine=frequency=1000" in item for item in captured["command"])
    assert report.real_execution_performed is True
    assert report.output_created is True
    assert report.can_execute_full_render is False
    assert report.can_render_timeline is False
    assert report.can_process_user_media is False
    assert report.can_write_project_output is False


def test_execute_smoke_failed_is_reported(monkeypatch, tmp_path):
    class Completed:
        returncode = 9
        stdout = ""
        stderr = "boom"

    def fake_run(command, shell, capture_output, text, timeout, check):
        return Completed()

    monkeypatch.setattr("core.controlled_ffmpeg_execution.subprocess.run", fake_run)

    report = execute_controlled_ffmpeg_smoke_test(
        _ready_job(
            ffmpeg_execution_requested_mode=MODE_SMOKE_TEST,
            ffmpeg_execution_allow_real_render=True,
            ffmpeg_execution_allow_ffmpeg_execution=True,
            ffmpeg_execution_allow_process_spawn=True,
            ffmpeg_execution_allow_media_write=True,
            ffmpeg_execution_smoke_output_dir_hint=str(tmp_path / "smoke"),
        )
    )

    assert report.status == STATUS_SMOKE_FAILED
    assert report.real_execution_performed is True
    assert report.output_created is False
    assert "controlled_ffmpeg_smoke_test_failed" in report.blocking_reasons
