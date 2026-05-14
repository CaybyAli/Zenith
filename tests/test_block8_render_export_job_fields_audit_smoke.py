from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from models.job import Job


REQUIRED_FIELD_GROUP_PREFIXES = [
    "render_readiness_",
    "render_plan_",
    "render_blueprint_",
    "render_asset_",
    "render_execution_",
    "controlled_render_",
    "ffmpeg_",
    "ffmpeg_command_",
    "controlled_ffmpeg_",
    "output_format_",
    "output_",
    "render_verification_",
    "render_dashboard_delivery_",
]

HARD_FALSE_FIELDS = [
    "render_readiness_can_render",
    "render_plan_can_render",
    "render_blueprint_can_render",
    "render_asset_can_render",
    "render_execution_can_render",
    "controlled_render_can_render",
    "ffmpeg_can_render",
    "ffmpeg_command_can_render",
    "controlled_ffmpeg_can_execute_full_render",
    "controlled_ffmpeg_can_render_timeline",
    "output_can_render",
    "render_verification_can_render",
    "render_dashboard_delivery_can_render",
    "render_dashboard_delivery_can_write_dashboard_file",
    "render_dashboard_delivery_can_move_video",
    "render_dashboard_delivery_can_copy_output",
    "render_dashboard_delivery_can_extract_thumbnail",
]


def _job_field_names() -> set[str]:
    return {field.name for field in fields(Job)}


def test_job_dataclass_contains_all_block8_field_groups() -> None:
    names = _job_field_names()

    for prefix in REQUIRED_FIELD_GROUP_PREFIXES:
        matches = [name for name in names if name.startswith(prefix)]
        assert matches, f"missing Job field group: {prefix}"


def test_job_dataclass_contains_all_hard_false_safety_fields() -> None:
    names = _job_field_names()

    missing = [field for field in HARD_FALSE_FIELDS if field not in names]
    assert missing == []


def test_job_from_dict_forces_block8_dangerous_fields_false() -> None:
    payload = {
        "job_id": "job_2b58_fields",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "short",
        "target_platforms": ["youtube"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
    }

    for field in HARD_FALSE_FIELDS:
        payload[field] = True

    job = Job.from_dict(payload)

    for field in HARD_FALSE_FIELDS:
        assert getattr(job, field) is False, f"from_dict must force False: {field}"


def test_job_from_dict_source_keeps_each_block8_dangerous_field_hard_false() -> None:
    text = Path("models/job.py").read_text(encoding="utf-8")

    for field in HARD_FALSE_FIELDS:
        assert f"{field}=False," in text, f"from_dict must hard-force False for {field}"


def test_job_defaults_keep_render_export_dangerous_permissions_false() -> None:
    job = Job.from_dict(
        {
            "job_id": "job_2b58_default_false",
            "job_type": "gaming",
            "channel_type": "gaming_main",
            "target_format": "short",
            "target_platforms": ["youtube"],
            "status": "routed",
            "mode": "normal",
            "autopublish_class": "manual_only",
            "confidence_score": 0.0,
            "validator_status": "not_validated",
        }
    )

    for field in HARD_FALSE_FIELDS:
        assert getattr(job, field) is False, f"default should stay False: {field}"
