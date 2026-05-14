from __future__ import annotations

from core.render_asset_manifest_builder import build_render_asset_manifest


def _ready_job() -> dict:
    return {
        "job_id": "job_render_asset_manifest_smoke",
        "target_platforms": ["youtube"],
        "render_plan_status": "render_plan_ready",
        "render_plan_dry_run_only": True,
        "render_plan_ready_for_renderer_contract": True,
        "render_plan_can_render": False,
        "render_plan_can_run_ffmpeg": False,
        "render_plan_can_write_media": False,
        "render_plan_blocking_reasons": [],
        "render_plan_warnings": [],
        "render_plan_sources": [
            {
                "source_type": "primary_media",
                "path_hint": "inputs/raw/gameplay.mp4",
                "required": True,
            },
            {
                "source_type": "video_track",
                "path_hint": "inputs/raw/facecam.mp4",
                "required": False,
            },
            {
                "source_type": "audio_track",
                "path_hint": "inputs/raw/mic.wav",
                "required": False,
            },
        ],
        "render_plan_output_targets": [
            {
                "output_id": "main_youtube",
                "output_type": "planned_video",
                "filename_hint": "My Unsafe Video & Final.mp4",
                "directory_hint": "exports/gaming_main/job_render_asset_manifest_smoke",
                "output_path_hint": "exports/gaming_main/job_render_asset_manifest_smoke/My Unsafe Video & Final.mp4",
                "container": "mp4",
                "platform": "youtube",
            }
        ],
        "render_plan_report": {
            "status": "render_plan_ready",
            "dry_run_only": True,
            "ready_for_renderer_contract": True,
            "blocking_reasons": [],
            "warnings": [],
            "sources": [
                {
                    "source_type": "primary_media",
                    "path_hint": "inputs/raw/gameplay.mp4",
                    "required": True,
                }
            ],
            "output_targets": [
                {
                    "output_id": "main_youtube",
                    "output_type": "planned_video",
                    "filename_hint": "My Unsafe Video & Final.mp4",
                    "directory_hint": "exports/gaming_main/job_render_asset_manifest_smoke",
                    "output_path_hint": "exports/gaming_main/job_render_asset_manifest_smoke/My Unsafe Video & Final.mp4",
                    "container": "mp4",
                    "platform": "youtube",
                }
            ],
        },
        "render_blueprint_status": "render_blueprint_ready",
        "render_blueprint_dry_run_only": True,
        "render_blueprint_non_executable": True,
        "render_blueprint_ready_for_renderer_implementation": True,
        "render_blueprint_can_render": False,
        "render_blueprint_can_run_ffmpeg": False,
        "render_blueprint_can_write_media": False,
        "render_blueprint_blocking_reasons": [],
        "render_blueprint_warnings": [],
        "render_blueprint_steps": [
            {"step_id": "step_censor", "step_type": "censor_sfx"},
            {"step_id": "step_subtitle", "step_type": "subtitle"},
            {"step_id": "step_audio", "step_type": "audio_mix"},
            {"step_id": "step_encode", "step_type": "encode"},
        ],
        "render_command_blueprint_report": {
            "status": "render_blueprint_ready",
            "dry_run_only": True,
            "non_executable": True,
            "ready_for_renderer_implementation": True,
            "blocking_reasons": [],
            "warnings": [],
            "blueprint_steps": [
                {"step_id": "step_censor", "step_type": "censor_sfx"},
                {"step_id": "step_subtitle", "step_type": "subtitle"},
                {"step_id": "step_audio", "step_type": "audio_mix"},
                {"step_id": "step_encode", "step_type": "encode"},
            ],
        },
    }


def test_builder_blocks_when_render_plan_missing():
    job = _ready_job()
    job["render_plan_report"] = {}
    job["render_plan_status"] = None

    report = build_render_asset_manifest(job)

    assert report["status"] == "render_asset_manifest_blocked"
    assert "render_asset_manifest_render_plan_missing" in report["blocking_reasons"]
    assert report["can_render"] is False


def test_builder_blocks_when_render_blueprint_missing():
    job = _ready_job()
    job["render_command_blueprint_report"] = {}
    job["render_blueprint_status"] = None

    report = build_render_asset_manifest(job)

    assert report["status"] == "render_asset_manifest_blocked"
    assert "render_asset_manifest_blueprint_missing" in report["blocking_reasons"]


def test_builder_blocks_when_blueprint_not_non_executable():
    job = _ready_job()
    job["render_blueprint_non_executable"] = False

    report = build_render_asset_manifest(job)

    assert report["status"] == "render_asset_manifest_blocked"
    assert "render_asset_manifest_blueprint_not_non_executable" in report["blocking_reasons"]


def test_builder_blocks_when_blueprint_not_ready_for_renderer():
    job = _ready_job()
    job["render_blueprint_ready_for_renderer_implementation"] = False

    report = build_render_asset_manifest(job)

    assert report["status"] == "render_asset_manifest_blocked"
    assert "render_asset_manifest_blueprint_not_ready_for_renderer" in report["blocking_reasons"]


def test_builder_blocks_when_danger_flags_are_true():
    danger_flags = [
        "can_render",
        "can_run_ffmpeg",
        "can_write_media",
        "render_plan_can_render",
        "render_plan_can_run_ffmpeg",
        "render_plan_can_write_media",
        "render_blueprint_can_render",
        "render_blueprint_can_run_ffmpeg",
        "render_blueprint_can_write_media",
    ]

    for flag in danger_flags:
        job = _ready_job()
        job[flag] = True

        report = build_render_asset_manifest(job)

        assert report["status"] == "render_asset_manifest_blocked"
        assert f"render_asset_manifest_dangerous_flag:{flag}" in report["blocking_reasons"]


def test_builder_creates_asset_references_from_render_plan_sources():
    report = build_render_asset_manifest(_ready_job())

    asset_types = {asset["asset_type"] for asset in report["asset_references"]}

    assert "primary_media" in asset_types
    assert "video_track" in asset_types
    assert "audio_track" in asset_types
    assert report["total_assets"] >= 3


def test_builder_creates_asset_references_from_blueprint_steps():
    report = build_render_asset_manifest(_ready_job())

    asset_types = {asset["asset_type"] for asset in report["asset_references"]}

    assert "censor_sfx_asset" in asset_types
    assert "subtitle_asset" in asset_types
    assert "audio_mix_asset" in asset_types


def test_censor_sfx_step_creates_required_censor_asset_reference():
    report = build_render_asset_manifest(_ready_job())

    censor_assets = [
        asset
        for asset in report["asset_references"]
        if asset["asset_type"] == "censor_sfx_asset"
    ]

    assert censor_assets
    assert censor_assets[0]["required"] is True
    assert censor_assets[0]["path_hint"] == "assets/sfx/censor/censor_sfx_manifest.json"


def test_output_path_plans_are_created_from_output_targets():
    report = build_render_asset_manifest(_ready_job())

    assert report["output_plan_count"] == 1
    output = report["output_path_plans"][0]
    assert output["output_id"] == "main_youtube"
    assert output["platform"] == "youtube"
    assert output["container"] == "mp4"


def test_safe_filename_removes_dangerous_characters_and_keeps_mp4():
    report = build_render_asset_manifest(_ready_job())

    safe_filename = report["output_path_plans"][0]["safe_filename"]

    assert safe_filename.endswith(".mp4")
    assert "&" not in safe_filename
    assert " " not in safe_filename
    assert "/" not in safe_filename
    assert "\\" not in safe_filename


def test_path_traversal_is_blocked():
    job = _ready_job()
    job["render_plan_sources"][0]["path_hint"] = "../secret/gameplay.mp4"

    report = build_render_asset_manifest(job)

    assert report["status"] == "render_asset_manifest_blocked"
    assert any("path_hint_traversal_not_allowed" in reason for reason in report["blocking_reasons"])


def test_shell_markers_are_blocked():
    job = _ready_job()
    job["render_plan_sources"][0]["path_hint"] = "inputs/raw/gameplay.mp4;bad"

    report = build_render_asset_manifest(job)

    assert report["status"] == "render_asset_manifest_blocked"
    assert any("path_hint_shell_marker_not_allowed" in reason for reason in report["blocking_reasons"])


def test_url_paths_are_blocked():
    job = _ready_job()
    job["render_plan_sources"][0]["path_hint"] = "https://example.com/video.mp4"

    report = build_render_asset_manifest(job)

    assert report["status"] == "render_asset_manifest_blocked"
    assert any("path_hint_url_not_allowed" in reason for reason in report["blocking_reasons"])


def test_required_asset_without_path_hint_blocks():
    job = _ready_job()
    job["render_plan_sources"][0]["path_hint"] = ""

    report = build_render_asset_manifest(job)

    assert report["status"] == "render_asset_manifest_blocked"
    assert report["missing_required_hint_count"] >= 1
    assert "render_asset_missing_required_hint" in report["blocking_reasons"]


def test_manifest_safety_flags_are_locked():
    report = build_render_asset_manifest(_ready_job())

    assert report["dry_run_only"] is True
    assert report["manifest_only"] is True
    assert report["paths_are_hints_only"] is True
    assert report["can_create_directories"] is False
    assert report["can_write_files"] is False
    assert report["can_open_media"] is False
    assert report["can_render"] is False
    assert report["can_run_ffmpeg"] is False
