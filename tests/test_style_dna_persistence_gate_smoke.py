from __future__ import annotations

from core.style_dna_persistence_gate import build_style_dna_persistence_gate_report


def _ready_job(**overrides):
    job = {
        "job_id": "job_2b63",
        "style_dna_profile_name": "gaming_main",
        "style_dna_apply_plan_status": "style_dna_apply_plan_ready",
        "style_dna_apply_plan": {
            "plan_id": "job_2b63_style_dna_apply_plan",
            "profile": "gaming_main",
        },
        "style_dna_apply_operation_count": 1,
        "style_dna_apply_approved_operation_count": 1,
        "style_dna_apply_skipped_operation_count": 0,
        "style_dna_apply_before_snapshot": {"zoom_intensity": 1.0},
        "style_dna_apply_after_preview": {"zoom_intensity": 1.2},
        "style_dna_apply_ready_for_future_file_write": True,
        "style_dna_apply_can_write_style_dna": False,
        "style_dna_apply_can_apply_style_dna": False,
        "style_dna_apply_can_update_profile": False,
        "style_dna_apply_can_change_cutting_rules": False,
        "style_dna_apply_can_modify_timeline": False,
        "style_dna_apply_can_trigger_render": False,
        "style_dna_apply_can_publish": False,
        "style_dna_apply_blocking_reasons": [],
        "style_dna_persistence_backup_required": True,
    }
    job.update(overrides)
    return job


def test_without_apply_plan_is_blocked():
    report = build_style_dna_persistence_gate_report({"job_id": "missing"})
    assert report["status"] == "style_dna_persistence_blocked"
    assert "style_dna_apply_plan_status_missing" in report["blocking_reasons"]


def test_blocked_or_failed_apply_plan_is_blocked():
    for status in ["style_dna_apply_plan_blocked", "style_dna_apply_plan_failed"]:
        report = build_style_dna_persistence_gate_report(
            _ready_job(style_dna_apply_plan_status=status)
        )
        assert report["status"] == "style_dna_persistence_blocked"
        assert "style_dna_apply_plan_blocked_or_failed" in report["blocking_reasons"]


def test_waiting_apply_plan_with_pending_request_stays_pending():
    report = build_style_dna_persistence_gate_report(
        _ready_job(
            style_dna_apply_plan_status="style_dna_apply_plan_waiting_for_review",
            style_dna_apply_ready_for_future_file_write=False,
            style_dna_persistence_requested_status="pending_write_review",
        )
    )
    assert report["status"] == "style_dna_persistence_pending_write_review"
    assert report["write_permission_ready_for_future"] is False


def test_ready_apply_plan_without_request_stays_pending():
    report = build_style_dna_persistence_gate_report(_ready_job())
    assert report["status"] == "style_dna_persistence_pending_write_review"
    assert report["write_permission_ready_for_future"] is False


def test_approved_write_without_approved_by_is_blocked():
    report = build_style_dna_persistence_gate_report(
        _ready_job(
            style_dna_persistence_requested_status="approved_write",
            style_dna_persistence_target_path_hint="profiles/style_dna.json",
        )
    )
    assert report["status"] == "style_dna_persistence_blocked"
    assert "style_dna_persistence_approved_by_required" in report["blocking_reasons"]


def test_approved_write_without_target_path_hint_is_blocked():
    report = build_style_dna_persistence_gate_report(
        _ready_job(
            style_dna_persistence_requested_status="approved_write",
            style_dna_persistence_approved_by="Hajar",
        )
    )
    assert report["status"] == "style_dna_persistence_blocked"
    assert "style_dna_persistence_target_path_hint_required" in report["blocking_reasons"]


def test_approved_write_with_url_target_hint_is_blocked():
    report = build_style_dna_persistence_gate_report(
        _ready_job(
            style_dna_persistence_requested_status="approved_write",
            style_dna_persistence_approved_by="Hajar",
            style_dna_persistence_target_path_hint="https://example.com/style_dna.json",
        )
    )
    assert report["status"] == "style_dna_persistence_blocked"
    assert (
        "style_dna_persistence_target_path_hint_url_not_allowed"
        in report["blocking_reasons"]
    )


def test_approved_write_with_path_traversal_is_blocked():
    report = build_style_dna_persistence_gate_report(
        _ready_job(
            style_dna_persistence_requested_status="approved_write",
            style_dna_persistence_approved_by="Hajar",
            style_dna_persistence_target_path_hint="../style_dna.json",
        )
    )
    assert report["status"] == "style_dna_persistence_blocked"
    assert (
        "style_dna_persistence_target_path_hint_traversal_not_allowed"
        in report["blocking_reasons"]
    )


def test_approved_write_without_json_suffix_adds_warning():
    report = build_style_dna_persistence_gate_report(
        _ready_job(
            style_dna_persistence_requested_status="approved_write",
            style_dna_persistence_approved_by="Hajar",
            style_dna_persistence_target_path_hint="profiles/style_dna.txt",
        )
    )
    assert report["status"] == "style_dna_persistence_approved_write"
    assert (
        "style_dna_persistence_target_path_hint_should_end_with_json"
        in report["warnings"]
    )


def test_approved_write_with_valid_target_hint_sets_future_permission_only():
    report = build_style_dna_persistence_gate_report(
        _ready_job(
            style_dna_persistence_requested_status="approved_write",
            style_dna_persistence_approved_by="Hajar",
            style_dna_persistence_target_path_hint="profiles/style_dna.json",
        )
    )
    assert report["status"] == "style_dna_persistence_approved_write"
    assert report["write_permission_ready_for_future"] is True
    assert report["can_write_style_dna"] is False
    assert report["can_apply_style_dna"] is False
    assert report["can_update_profile"] is False
    assert report["can_change_cutting_rules"] is False
    assert report["can_modify_timeline"] is False
    assert report["can_trigger_render"] is False
    assert report["can_publish"] is False


def test_rejected_write_keeps_future_permission_false():
    report = build_style_dna_persistence_gate_report(
        _ready_job(
            style_dna_persistence_requested_status="rejected_write",
            style_dna_persistence_approved_by="Hajar",
        )
    )
    assert report["status"] == "style_dna_persistence_rejected_write"
    assert report["write_permission_ready_for_future"] is False


def test_needs_manual_changes_keeps_future_permission_false():
    report = build_style_dna_persistence_gate_report(
        _ready_job(style_dna_persistence_requested_status="needs_manual_changes")
    )
    assert report["status"] == "style_dna_persistence_needs_manual_changes"
    assert report["write_permission_ready_for_future"] is False


def test_allow_file_write_true_is_blocked_and_performs_no_file_write():
    report = build_style_dna_persistence_gate_report(
        _ready_job(
            style_dna_persistence_requested_status="approved_write",
            style_dna_persistence_approved_by="Hajar",
            style_dna_persistence_target_path_hint="profiles/style_dna.json",
            style_dna_persistence_allow_file_write=True,
        )
    )
    intent = report["gate"]["write_intent"]
    assert report["status"] == "style_dna_persistence_blocked"
    assert "style_dna_file_write_not_allowed_in_2b_63" in report["blocking_reasons"]
    assert intent["no_file_write_performed"] is True


def test_write_intent_contains_snapshots_and_stable_hash():
    job = _ready_job(
        style_dna_persistence_requested_status="approved_write",
        style_dna_persistence_approved_by="Hajar",
        style_dna_persistence_target_path_hint="profiles/style_dna.json",
    )
    report_a = build_style_dna_persistence_gate_report(job)
    report_b = build_style_dna_persistence_gate_report(job)

    intent_a = report_a["gate"]["write_intent"]
    intent_b = report_b["gate"]["write_intent"]

    assert intent_a["before_snapshot"] == {"zoom_intensity": 1.0}
    assert intent_a["after_preview"] == {"zoom_intensity": 1.2}
    assert len(intent_a["write_preview_hash"]) == 64
    assert intent_a["write_preview_hash"] == intent_b["write_preview_hash"]
    assert intent_a["planned_only"] is True
    assert intent_a["no_file_write_performed"] is True
