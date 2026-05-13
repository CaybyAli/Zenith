from __future__ import annotations

from dataclasses import fields
from pathlib import Path

from models.job import Job
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)


ROOT = Path(__file__).resolve().parents[1]
JOB_PATH = ROOT / "models" / "job.py"


BLOCK6_JOB_FIELDS = [
    "review_timeline_plan_report",
    "review_timeline_plan",
    "review_timeline_plan_status",
    "review_timeline_plan_items",
    "review_timeline_plan_id",
    "timeline_approval_gate_report",
    "timeline_approval_gate",
    "timeline_approval_gate_status",
    "timeline_approval_status",
    "timeline_can_proceed_to_execution",
    "timeline_can_render",
    "timeline_safety_validator_report",
    "timeline_safety_validator",
    "timeline_safety_validation_status",
    "timeline_is_safe_for_future_execution",
    "timeline_is_safe_for_render",
    "review_timeline_dashboard_package_report",
    "review_timeline_dashboard_package",
    "review_timeline_dashboard_package_status",
    "review_timeline_dashboard_can_render",
    "review_timeline_dashboard_is_safe_for_render",
]


BLOCK6_RENDER_FIELDS_THAT_MUST_DEFAULT_FALSE = [
    "timeline_can_render",
    "timeline_is_safe_for_render",
    "review_timeline_dashboard_can_render",
    "review_timeline_dashboard_is_safe_for_render",
]


def _enum_value(enum_class):
    return list(enum_class)[0].value


def _minimal_job_payload() -> dict:
    return {
        "job_id": "block6_final_audit_job",
        "job_type": _enum_value(JobType),
        "channel_type": _enum_value(ChannelType),
        "target_format": _enum_value(TargetFormat),
        "target_platforms": ["youtube"],
        "status": _enum_value(JobStatus),
        "mode": _enum_value(Mode),
        "autopublish_class": _enum_value(AutopublishClass),
        "confidence_score": 0.0,
        "validator_status": _enum_value(ValidatorStatus),
    }


def test_block6_job_dataclass_contains_all_required_report_fields() -> None:
    job_field_names = {field.name for field in fields(Job)}

    missing_fields = [
        field_name
        for field_name in BLOCK6_JOB_FIELDS
        if field_name not in job_field_names
    ]

    assert missing_fields == []


def test_block6_job_render_safety_fields_default_to_false() -> None:
    payload = _minimal_job_payload()
    job = Job.from_dict(payload)

    for field_name in BLOCK6_RENDER_FIELDS_THAT_MUST_DEFAULT_FALSE:
        assert getattr(job, field_name) is False, field_name


def test_block6_job_from_dict_loads_review_timeline_plan_fields() -> None:
    payload = _minimal_job_payload()
    payload.update(
        {
            "review_timeline_plan_report": {
                "status": "pending_review",
                "metadata": {
                    "review_only": True,
                    "media_unchanged": True,
                },
            },
            "review_timeline_plan": {
                "plan_id": "review_timeline_plan_final_audit",
                "items": [
                    {
                        "timeline_item_id": "item_1",
                        "action": "keep_review",
                    }
                ],
            },
            "review_timeline_plan_status": "pending_review",
            "review_timeline_plan_items": [
                {
                    "timeline_item_id": "item_1",
                    "action": "keep_review",
                }
            ],
            "review_timeline_plan_id": "review_timeline_plan_final_audit",
        }
    )

    job = Job.from_dict(payload)

    assert job.review_timeline_plan_report["status"] == "pending_review"
    assert job.review_timeline_plan["plan_id"] == "review_timeline_plan_final_audit"
    assert job.review_timeline_plan_status == "pending_review"
    assert job.review_timeline_plan_items[0]["action"] == "keep_review"
    assert job.review_timeline_plan_id == "review_timeline_plan_final_audit"


def test_block6_job_from_dict_loads_timeline_approval_gate_fields_and_keeps_render_false() -> None:
    payload = _minimal_job_payload()
    payload.update(
        {
            "timeline_approval_gate_report": {
                "status": "approved",
                "metadata": {
                    "approval_gate_only": True,
                    "media_unchanged": True,
                },
            },
            "timeline_approval_gate": {
                "approval_gate_id": "timeline_approval_gate_final_audit",
                "approval_status": "approved",
                "can_render": False,
            },
            "timeline_approval_gate_status": "approved",
            "timeline_approval_status": "approved",
            "timeline_can_proceed_to_execution": True,
            "timeline_can_render": False,
        }
    )

    job = Job.from_dict(payload)

    assert job.timeline_approval_gate_report["status"] == "approved"
    assert job.timeline_approval_gate["approval_gate_id"] == (
        "timeline_approval_gate_final_audit"
    )
    assert job.timeline_approval_gate_status == "approved"
    assert job.timeline_approval_status == "approved"
    assert job.timeline_can_proceed_to_execution is True
    assert job.timeline_can_render is False


def test_block6_job_from_dict_loads_timeline_safety_fields_and_keeps_render_false() -> None:
    payload = _minimal_job_payload()
    payload.update(
        {
            "timeline_safety_validator_report": {
                "status": "passed",
                "metadata": {
                    "safety_validator_only": True,
                    "media_unchanged": True,
                    "no_execution_in_2b_34": True,
                    "no_render_in_2b_34": True,
                },
            },
            "timeline_safety_validator": {
                "safety_validation_id": "timeline_safety_validation_final_audit",
                "validation_status": "passed",
                "is_safe_for_render": False,
            },
            "timeline_safety_validation_status": "passed",
            "timeline_is_safe_for_future_execution": True,
            "timeline_is_safe_for_render": False,
        }
    )

    job = Job.from_dict(payload)

    assert job.timeline_safety_validator_report["status"] == "passed"
    assert job.timeline_safety_validator["safety_validation_id"] == (
        "timeline_safety_validation_final_audit"
    )
    assert job.timeline_safety_validation_status == "passed"
    assert job.timeline_is_safe_for_future_execution is True
    assert job.timeline_is_safe_for_render is False


def test_block6_job_from_dict_loads_dashboard_package_fields_and_keeps_render_false() -> None:
    payload = _minimal_job_payload()
    payload.update(
        {
            "review_timeline_dashboard_package_report": {
                "status": "ready_for_dashboard",
                "metadata": {
                    "dashboard_only": True,
                    "media_unchanged": True,
                    "no_execution_in_2b_35": True,
                    "no_render_in_2b_35": True,
                },
            },
            "review_timeline_dashboard_package": {
                "dashboard_package_id": "dashboard_package_final_audit",
                "package_status": "ready_for_dashboard",
                "can_render": False,
                "is_safe_for_render": False,
            },
            "review_timeline_dashboard_package_status": "ready_for_dashboard",
            "review_timeline_dashboard_can_render": False,
            "review_timeline_dashboard_is_safe_for_render": False,
        }
    )

    job = Job.from_dict(payload)

    assert job.review_timeline_dashboard_package_report["status"] == (
        "ready_for_dashboard"
    )
    assert job.review_timeline_dashboard_package["dashboard_package_id"] == (
        "dashboard_package_final_audit"
    )
    assert job.review_timeline_dashboard_package_status == "ready_for_dashboard"
    assert job.review_timeline_dashboard_can_render is False
    assert job.review_timeline_dashboard_is_safe_for_render is False


def test_block6_job_from_dict_source_mentions_all_block6_fields() -> None:
    text = JOB_PATH.read_text(encoding="utf-8")

    missing_tokens = [
        field_name
        for field_name in BLOCK6_JOB_FIELDS
        if field_name not in text
    ]

    assert missing_tokens == []


def test_block6_final_audit_static_contract_has_no_forbidden_dashboard_execution_actions() -> None:
    forbidden_dashboard_actions = [
        '"render"',
        "'render'",
        '"execute"',
        "'execute'",
        '"apply"',
        "'apply'",
        '"cut"',
        "'cut'",
        '"trim_now"',
        "'trim_now'",
        '"delete"',
        "'delete'",
        '"mute"',
        "'mute'",
        '"censor_now"',
        "'censor_now'",
        '"apply_timeline"',
        "'apply_timeline'",
        '"execute_timeline"',
        "'execute_timeline'",
    ]

    dashboard_files = [
        ROOT / "models" / "review_timeline_dashboard_package.py",
        ROOT / "core" / "review_timeline_dashboard_package_builder.py",
    ]

    violations: list[str] = []

    for path in dashboard_files:
        text = path.read_text(encoding="utf-8")

        for forbidden_action in forbidden_dashboard_actions:
            if forbidden_action in text:
                violations.append(f"{path.relative_to(ROOT)}: {forbidden_action}")

    assert violations == []