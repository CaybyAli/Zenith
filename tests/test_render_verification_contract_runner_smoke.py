from __future__ import annotations

from core.render_verification_contract_runner import run_render_verification_contract
from models.job import Job


def _ready_job(**overrides):
    job = {
        "job_id": "job_runner_verify",
        "output_format_contract_report": {"status": "output_format_contract_ready"},
        "output_format_contract_status": "output_format_contract_ready",
        "output_can_prepare_output_format": True,
        "output_can_render": False,
        "output_can_write_project_output": False,
        "output_can_process_user_media": False,
        "output_can_execute_ffmpeg": False,
        "output_video_spec": {
            "codec": "h264",
            "resolution_width": 1920,
            "resolution_height": 1080,
            "fps": 60,
        },
        "output_audio_spec": {"codec": "aac"},
        "output_container_spec": {"container": "mp4", "faststart": True},
        "render_plan_estimated_output_duration_seconds": 12.0,
        "render_verification_duration_tolerance_seconds": 1.0,
        "ffprobe_path_hint": "ffprobe",
    }
    job.update(overrides)
    return job


def test_runner_writes_render_verification_job_fields_to_dict():
    job = _ready_job()
    report = run_render_verification_contract(job)

    assert report["status"] == "render_verification_contract_ready"
    assert job["render_verification_contract_report"]["status"] == report["status"]
    assert job["render_verification_contract_status"] == report["status"]
    assert job["render_verification_expected_spec"]["container"] == "mp4"
    assert len(job["render_verification_checks"]) == 12
    assert job["render_verification_probe_plan"]["tool"] == "ffprobe"
    assert job["render_verification_total_checks"] == 12
    assert job["render_verification_planned_check_count"] == 12
    assert job["render_verification_runnable_smoke_check_count"] == 0
    assert job["render_verification_blocked_check_count"] == 0
    assert job["render_verification_contract_only"] is True
    assert job["render_verification_dry_run_only"] is True
    assert job["render_verification_project_output_probe_allowed"] is False
    assert job["render_verification_can_verify_project_output"] is False
    assert job["render_verification_can_probe_media_files"] is False
    assert job["render_verification_can_render"] is False
    assert job["render_verification_can_write_media"] is False


def test_runner_writes_render_verification_job_fields_to_job_model():
    job = Job.from_dict(_ready_job())
    report = run_render_verification_contract(job)

    assert report["status"] == "render_verification_contract_ready"
    assert job.render_verification_contract_report["status"] == report["status"]
    assert job.render_verification_contract_status == report["status"]
    assert job.render_verification_expected_spec["container"] == "mp4"
    assert len(job.render_verification_checks) == 12
    assert job.render_verification_probe_plan["tool"] == "ffprobe"
    assert job.render_verification_total_checks == 12
    assert job.render_verification_contract_only is True
    assert job.render_verification_dry_run_only is True
    assert job.render_verification_project_output_probe_allowed is False
    assert job.render_verification_can_verify_project_output is False
    assert job.render_verification_can_probe_media_files is False
    assert job.render_verification_can_render is False
    assert job.render_verification_can_write_media is False


def test_job_from_dict_loads_new_render_verification_fields_and_forces_dangerous_flags_false():
    job = Job.from_dict(
        {
            "job_id": "job_from_dict_verify",
            "render_verification_contract_report": {
                "status": "render_verification_contract_ready"
            },
            "render_verification_contract_status": "render_verification_contract_ready",
            "render_verification_expected_spec": {"container": "mp4"},
            "render_verification_checks": [{"check_id": "output_file_exists_check"}],
            "render_verification_probe_plan": {"tool": "ffprobe"},
            "render_verification_total_checks": 12,
            "render_verification_planned_check_count": 12,
            "render_verification_runnable_smoke_check_count": 1,
            "render_verification_blocked_check_count": 0,
            "render_verification_contract_only": True,
            "render_verification_dry_run_only": True,
            "render_verification_smoke_probe_allowed": True,
            "render_verification_project_output_probe_allowed": True,
            "render_verification_can_verify_smoke_output": True,
            "render_verification_can_verify_project_output": True,
            "render_verification_can_probe_media_files": True,
            "render_verification_can_render": True,
            "render_verification_can_write_media": True,
            "render_verification_blocking_reasons": [],
            "render_verification_warnings": ["demo"],
            "render_verification_recommendation": "review_render_verification_contract",
            "render_verification_allow_smoke_probe": True,
            "render_verification_allow_project_output_probe": True,
            "render_verification_expected_duration_seconds": 22.5,
            "render_verification_duration_tolerance_seconds": 1.25,
        }
    )

    assert job.render_verification_contract_status == "render_verification_contract_ready"
    assert job.render_verification_expected_spec == {"container": "mp4"}
    assert len(job.render_verification_checks) == 1
    assert job.render_verification_probe_plan == {"tool": "ffprobe"}
    assert job.render_verification_total_checks == 12
    assert job.render_verification_planned_check_count == 12
    assert job.render_verification_runnable_smoke_check_count == 1
    assert job.render_verification_smoke_probe_allowed is True
    assert job.render_verification_can_verify_smoke_output is True
    assert job.render_verification_allow_smoke_probe is True
    assert job.render_verification_allow_project_output_probe is True
    assert job.render_verification_expected_duration_seconds == 22.5
    assert job.render_verification_duration_tolerance_seconds == 1.25

    assert job.render_verification_project_output_probe_allowed is False
    assert job.render_verification_can_verify_project_output is False
    assert job.render_verification_can_probe_media_files is False
    assert job.render_verification_can_render is False
    assert job.render_verification_can_write_media is False
