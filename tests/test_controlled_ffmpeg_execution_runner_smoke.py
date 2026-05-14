from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.controlled_ffmpeg_execution_runner import (
    run_controlled_ffmpeg_execution_dry_run_for_job,
    run_controlled_ffmpeg_execution_for_job,
)
from models.controlled_ffmpeg_execution import (
    STATUS_DRY_RUN_READY,
    STATUS_SMOKE_SUCCEEDED,
)


def _ready_job(**overrides):
    data = {
        "job_id": "job_2b54_runner",
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


def test_runner_writes_default_dry_run_job_fields():
    job = _ready_job()

    report = run_controlled_ffmpeg_execution_for_job(job)

    assert report.status == STATUS_DRY_RUN_READY
    assert job.controlled_ffmpeg_execution_status == STATUS_DRY_RUN_READY
    assert job.controlled_ffmpeg_dry_run_only is True
    assert job.controlled_ffmpeg_real_execution_allowed is False
    assert job.controlled_ffmpeg_real_execution_performed is False
    assert job.controlled_ffmpeg_output_created is False
    assert job.controlled_ffmpeg_can_execute_full_render is False
    assert job.controlled_ffmpeg_can_render_timeline is False
    assert job.controlled_ffmpeg_can_process_user_media is False
    assert job.controlled_ffmpeg_can_write_project_output is False


def test_runner_dry_run_helper_never_executes_smoke(monkeypatch, tmp_path):
    called = {"run": False}

    def fake_run(*args, **kwargs):
        called["run"] = True
        raise AssertionError("subprocess.run must not be called")

    monkeypatch.setattr("core.controlled_ffmpeg_execution.subprocess.run", fake_run)

    job = _ready_job(
        ffmpeg_execution_requested_mode="smoke_test",
        ffmpeg_execution_allow_real_render=True,
        ffmpeg_execution_allow_ffmpeg_execution=True,
        ffmpeg_execution_allow_process_spawn=True,
        ffmpeg_execution_allow_media_write=True,
        ffmpeg_execution_smoke_output_dir_hint=str(tmp_path / "smoke"),
    )

    report = run_controlled_ffmpeg_execution_dry_run_for_job(job)

    assert called["run"] is False
    assert report.real_execution_allowed is True
    assert report.real_execution_performed is False
    assert job.controlled_ffmpeg_real_execution_performed is False


def test_runner_can_execute_mocked_smoke_when_all_flags_are_set(monkeypatch, tmp_path):
    class Completed:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(command, shell, capture_output, text, timeout, check):
        assert shell is False
        assert timeout == 15
        Path(command[-1]).write_bytes(b"fake mp4")
        return Completed()

    monkeypatch.setattr("core.controlled_ffmpeg_execution.subprocess.run", fake_run)

    job = _ready_job(
        ffmpeg_execution_requested_mode="smoke_test",
        ffmpeg_execution_allow_real_render=True,
        ffmpeg_execution_allow_ffmpeg_execution=True,
        ffmpeg_execution_allow_process_spawn=True,
        ffmpeg_execution_allow_media_write=True,
        ffmpeg_execution_smoke_output_dir_hint=str(tmp_path / "smoke"),
    )

    report = run_controlled_ffmpeg_execution_for_job(job)

    assert report.status == STATUS_SMOKE_SUCCEEDED
    assert job.controlled_ffmpeg_execution_status == STATUS_SMOKE_SUCCEEDED
    assert job.controlled_ffmpeg_real_execution_allowed is True
    assert job.controlled_ffmpeg_real_execution_performed is True
    assert job.controlled_ffmpeg_output_created is True
    assert job.controlled_ffmpeg_can_execute_full_render is False
    assert job.controlled_ffmpeg_can_render_timeline is False
    assert job.controlled_ffmpeg_can_process_user_media is False
    assert job.controlled_ffmpeg_can_write_project_output is False
