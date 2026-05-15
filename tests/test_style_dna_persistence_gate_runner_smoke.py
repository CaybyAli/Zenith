from __future__ import annotations

from core.style_dna_persistence_gate_runner import run_style_dna_persistence_gate_for_job
from models.job import Job


def _job():
    return Job.from_dict(
        {
            "job_id": "runner_2b63",
            "style_dna_profile_name": "gaming_main",
            "style_dna_apply_plan_status": "style_dna_apply_plan_ready",
            "style_dna_apply_plan": {
                "plan_id": "runner_2b63_style_dna_apply_plan",
                "profile": "gaming_main",
            },
            "style_dna_apply_operation_count": 1,
            "style_dna_apply_approved_operation_count": 1,
            "style_dna_apply_before_snapshot": {"zoom_intensity": 1.0},
            "style_dna_apply_after_preview": {"zoom_intensity": 1.2},
            "style_dna_apply_ready_for_future_file_write": True,
            "style_dna_persistence_requested_status": "approved_write",
            "style_dna_persistence_approved_by": "Hajar",
            "style_dna_persistence_target_path_hint": "profiles/style_dna.json",
            "style_dna_persistence_backup_required": True,
        }
    )


def test_runner_writes_job_fields_correctly():
    job = _job()
    report = run_style_dna_persistence_gate_for_job(job)

    assert report["status"] == "style_dna_persistence_approved_write"
    assert job.style_dna_persistence_gate_report == report
    assert job.style_dna_persistence_gate["status"] == report["status"]
    assert job.style_dna_persistence_status == "style_dna_persistence_approved_write"
    assert job.style_dna_persistence_write_permission_ready_for_future is True
    assert job.style_dna_persistence_write_intent["before_snapshot"] == {
        "zoom_intensity": 1.0
    }
    assert job.style_dna_persistence_write_intent["after_preview"] == {
        "zoom_intensity": 1.2
    }
    assert isinstance(job.style_dna_persistence_write_preview_hash, str)
    assert len(job.style_dna_persistence_write_preview_hash) == 64
    assert job.style_dna_persistence_can_write_style_dna is False
    assert job.style_dna_persistence_can_apply_style_dna is False
    assert job.style_dna_persistence_can_update_profile is False
    assert job.style_dna_persistence_can_change_cutting_rules is False
    assert job.style_dna_persistence_can_modify_timeline is False
    assert job.style_dna_persistence_can_trigger_render is False
    assert job.style_dna_persistence_can_publish is False


def test_job_from_dict_loads_new_persistence_fields():
    job = Job.from_dict(
        {
            "job_id": "from_dict_2b63",
            "style_dna_persistence_gate_report": {"status": "x"},
            "style_dna_persistence_gate": {"gate_id": "gate"},
            "style_dna_persistence_status": "style_dna_persistence_approved_write",
            "style_dna_persistence_requested_status": "approved_write",
            "style_dna_persistence_approved_by": "Hajar",
            "style_dna_persistence_comment": "ok",
            "style_dna_persistence_requested_at": "2026-05-15T00:00:00+00:00",
            "style_dna_persistence_write_intent": {"intent_id": "intent"},
            "style_dna_persistence_write_preview_hash": "abc",
            "style_dna_persistence_target_path_hint": "profiles/style_dna.json",
            "style_dna_persistence_backup_required": True,
            "style_dna_persistence_write_permission_ready_for_future": True,
            "style_dna_persistence_can_write_style_dna": True,
            "style_dna_persistence_can_apply_style_dna": True,
            "style_dna_persistence_can_update_profile": True,
            "style_dna_persistence_can_change_cutting_rules": True,
            "style_dna_persistence_can_modify_timeline": True,
            "style_dna_persistence_can_trigger_render": True,
            "style_dna_persistence_can_publish": True,
            "style_dna_persistence_warnings": ["warn"],
            "style_dna_persistence_blocking_reasons": ["block"],
            "style_dna_persistence_recommendation": "review_style_dna_persistence_gate",
        }
    )

    assert job.style_dna_persistence_gate_report == {"status": "x"}
    assert job.style_dna_persistence_gate == {"gate_id": "gate"}
    assert job.style_dna_persistence_status == "style_dna_persistence_approved_write"
    assert job.style_dna_persistence_requested_status == "approved_write"
    assert job.style_dna_persistence_approved_by == "Hajar"
    assert job.style_dna_persistence_comment == "ok"
    assert job.style_dna_persistence_requested_at == "2026-05-15T00:00:00+00:00"
    assert job.style_dna_persistence_write_intent == {"intent_id": "intent"}
    assert job.style_dna_persistence_write_preview_hash == "abc"
    assert job.style_dna_persistence_target_path_hint == "profiles/style_dna.json"
    assert job.style_dna_persistence_backup_required is True
    assert job.style_dna_persistence_write_permission_ready_for_future is True

    assert job.style_dna_persistence_can_write_style_dna is False
    assert job.style_dna_persistence_can_apply_style_dna is False
    assert job.style_dna_persistence_can_update_profile is False
    assert job.style_dna_persistence_can_change_cutting_rules is False
    assert job.style_dna_persistence_can_modify_timeline is False
    assert job.style_dna_persistence_can_trigger_render is False
    assert job.style_dna_persistence_can_publish is False

    assert job.style_dna_persistence_warnings == ["warn"]
    assert job.style_dna_persistence_blocking_reasons == ["block"]
    assert (
        job.style_dna_persistence_recommendation
        == "review_style_dna_persistence_gate"
    )
