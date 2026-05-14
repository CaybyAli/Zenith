from __future__ import annotations

from core.render_verification_contract import build_render_verification_contract


def _ready_job(**overrides):
    job = {
        "job_id": "job_render_verify",
        "output_format_contract_report": {"status": "output_format_contract_ready"},
        "output_format_contract_status": "output_format_contract_ready",
        "output_can_prepare_output_format": True,
        "output_can_render": False,
        "output_can_write_project_output": False,
        "output_can_process_user_media": False,
        "output_can_execute_ffmpeg": False,
        "output_video_spec": {
            "codec": "h264",
            "encoder_intent": "h264_nvenc",
            "resolution_width": 1920,
            "resolution_height": 1080,
            "fps": 60,
        },
        "output_audio_spec": {
            "codec": "aac",
            "target_lufs": -14.0,
            "true_peak_db": -1.0,
        },
        "output_container_spec": {
            "container": "mp4",
            "extension": ".mp4",
            "faststart": True,
        },
        "render_plan_estimated_output_duration_seconds": 12.0,
        "render_verification_duration_tolerance_seconds": 1.0,
        "ffprobe_path_hint": "ffprobe",
        "controlled_ffmpeg_output_created": False,
        "controlled_ffmpeg_output_path": None,
        "controlled_ffmpeg_smoke_test_only": True,
        "render_verification_allow_smoke_probe": False,
    }
    job.update(overrides)
    return job


def test_contract_blocks_when_output_format_contract_missing():
    report = build_render_verification_contract(
        {
            "job_id": "missing_output_format",
            "output_can_prepare_output_format": True,
        }
    ).to_dict()

    assert report["status"] == "render_verification_contract_blocked"
    assert "output_format_contract_report_missing" in report["blocking_reasons"]


def test_contract_blocks_when_output_format_status_blocked_or_failed():
    for status in ["output_format_contract_blocked", "output_format_contract_failed"]:
        report = build_render_verification_contract(
            _ready_job(output_format_contract_status=status)
        ).to_dict()

        assert report["status"] == "render_verification_contract_blocked"
        assert "output_format_contract_not_ready" in report["blocking_reasons"]


def test_contract_blocks_when_output_can_prepare_output_format_false():
    report = build_render_verification_contract(
        _ready_job(output_can_prepare_output_format=False)
    ).to_dict()

    assert report["status"] == "render_verification_contract_blocked"
    assert "output_can_prepare_output_format_false" in report["blocking_reasons"]


def test_contract_blocks_permission_leaks_from_output_format_stage():
    leak_cases = [
        ("output_can_render", "output_can_render_must_remain_false"),
        ("output_can_write_project_output", "output_can_write_project_output_must_remain_false"),
        ("output_can_process_user_media", "output_can_process_user_media_must_remain_false"),
        ("output_can_execute_ffmpeg", "output_can_execute_ffmpeg_must_remain_false"),
    ]

    for field, reason in leak_cases:
        report = build_render_verification_contract(_ready_job(**{field: True})).to_dict()

        assert report["status"] == "render_verification_contract_blocked"
        assert reason in report["blocking_reasons"]


def test_expected_spec_is_built_from_output_specs():
    report = build_render_verification_contract(_ready_job()).to_dict()
    spec = report["expected_spec"]

    assert spec["container"] == "mp4"
    assert spec["video_codec"] == "h264"
    assert spec["audio_codec"] == "aac"
    assert spec["width"] == 1920
    assert spec["height"] == 1080
    assert spec["fps"] == 60.0
    assert spec["expected_duration_seconds"] == 12.0
    assert spec["duration_tolerance_seconds"] == 1.0
    assert spec["require_video_stream"] is True
    assert spec["require_audio_stream"] is True
    assert spec["require_faststart"] is True
    assert spec["require_nonzero_size"] is True


def test_checks_are_planned_and_cover_required_contract_items():
    report = build_render_verification_contract(_ready_job()).to_dict()
    checks = report["checks"]
    check_ids = {check["check_id"] for check in checks}

    assert report["total_checks"] == 12
    assert report["planned_check_count"] == 12
    assert "output_file_exists_check" in check_ids
    assert "output_file_nonzero_size_check" in check_ids
    assert "duration_within_tolerance_check" in check_ids
    assert "video_stream_present_check" in check_ids
    assert "audio_stream_present_check" in check_ids
    assert "container_matches_check" in check_ids
    assert "video_codec_matches_check" in check_ids
    assert "audio_codec_matches_check" in check_ids
    assert "resolution_matches_check" in check_ids
    assert "fps_matches_check" in check_ids
    assert "faststart_planned_check" in check_ids
    assert "corruption_probe_planned_check" in check_ids

    assert all(check["planned_only"] is True for check in checks)
    assert all(check["can_run_now"] is False for check in checks)
    assert all(check["status"] == "planned" for check in checks)


def test_probe_plan_is_argv_preview_only_and_not_executable():
    report = build_render_verification_contract(_ready_job()).to_dict()
    probe_plan = report["probe_plan"]

    assert probe_plan["tool"] == "ffprobe"
    assert probe_plan["argv_preview"] == [
        "ffprobe",
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-of",
        "json",
        "<OUTPUT_PATH_PLACEHOLDER>",
    ]
    assert probe_plan["can_execute_probe"] is False
    assert probe_plan["can_probe_project_output"] is False
    assert probe_plan["project_output_probe_allowed"] is False


def test_project_output_and_media_permissions_remain_false():
    report = build_render_verification_contract(_ready_job()).to_dict()

    assert report["project_output_probe_allowed"] is False
    assert report["can_verify_project_output"] is False
    assert report["can_probe_media_files"] is False
    assert report["can_render"] is False
    assert report["can_write_media"] is False
    assert report["contract_only"] is True
    assert report["dry_run_only"] is True


def test_ready_with_warnings_when_duration_missing():
    report = build_render_verification_contract(
        _ready_job(render_plan_estimated_output_duration_seconds=0.0)
    ).to_dict()

    assert report["status"] == "render_verification_contract_ready_with_warnings"
    assert "expected_duration_seconds_missing" in report["warnings"]


def test_smoke_probe_ready_only_when_smoke_output_exists_and_allowed():
    no_allow = build_render_verification_contract(
        _ready_job(
            controlled_ffmpeg_output_created=True,
            controlled_ffmpeg_output_path="smoke.mp4",
            controlled_ffmpeg_smoke_test_only=True,
            render_verification_allow_smoke_probe=False,
        )
    ).to_dict()

    assert no_allow["status"] == "render_verification_contract_ready"
    assert no_allow["can_verify_smoke_output"] is False

    allowed = build_render_verification_contract(
        _ready_job(
            controlled_ffmpeg_output_created=True,
            controlled_ffmpeg_output_path="smoke.mp4",
            controlled_ffmpeg_smoke_test_only=True,
            render_verification_allow_smoke_probe=True,
        )
    ).to_dict()

    assert allowed["status"] == "render_verification_contract_smoke_probe_ready"
    assert allowed["smoke_probe_allowed"] is True
    assert allowed["can_verify_smoke_output"] is True
    assert allowed["probe_plan"]["target_path_hint"] == "smoke.mp4"
    assert allowed["runnable_smoke_check_count"] == 12
    assert all(check["can_run_now"] is True for check in allowed["checks"])
    assert all(check["status"] == "smoke_runnable" for check in allowed["checks"])
