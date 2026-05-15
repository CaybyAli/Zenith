from __future__ import annotations

from types import SimpleNamespace

from core.style_dna_feedback_updater import build_style_dna_feedback_update_report


def _job(**overrides):
    data = {
        "job_id": "job_style_dna_1",
        "profile": "gaming_main",
        "feedback_intake_report": {},
        "feedback_intake_status": None,
        "feedback_blocking_reasons": [],
        "feedback_ready_for_style_dna_update": False,
        "feedback_can_update_style_dna": False,
        "feedback_can_change_profile": False,
        "feedback_can_modify_timeline": False,
        "feedback_can_trigger_render": False,
        "feedback_can_publish": False,
        "style_dna_update_allow_file_write": False,
        "existing_style_dna_snapshot": {
            "preferred_avg_clip_duration": 4.0,
            "pacing_sensitivity": 0.5,
            "preferred_hook_energy_min": 0.6,
            "hook_confidence_threshold": 0.7,
            "reaction_shot_priority": 0.4,
            "target_voice_gain_db": 0.0,
            "sentence_boundary_strictness": 0.7,
            "max_cut_shift_ms": 500,
        },
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _feedback_report(tags, submission_count=2, average_video_score=6.5, status="feedback_intake_ready"):
    return {
        "report_id": "feedback_report_1",
        "status": status,
        "submission_count": submission_count,
        "timestamp_feedback_count": submission_count,
        "average_video_score": average_video_score,
        "tags_summary": dict(tags),
        "ready_for_style_dna_update": True,
        "blocking_reasons": [],
        "warnings": [],
    }


def _proposal_names(report):
    draft = report.to_dict()["draft"] or {}
    return {item["parameter_name"] for item in draft.get("proposals", [])}


def test_without_feedback_waits_for_feedback():
    report = build_style_dna_feedback_update_report(_job())

    payload = report.to_dict()
    assert payload["status"] == "style_dna_update_waiting_for_feedback"
    assert payload["proposal_count"] == 0
    assert payload["ready_for_human_review"] is False
    assert payload["ready_for_later_apply"] is False
    assert payload["can_write_style_dna"] is False
    assert payload["can_update_profile"] is False
    assert payload["can_change_cutting_rules"] is False
    assert payload["can_modify_timeline"] is False
    assert payload["can_trigger_render"] is False
    assert payload["can_publish"] is False


def test_blocked_feedback_intake_blocks_style_dna_update():
    report = build_style_dna_feedback_update_report(
        _job(
            feedback_intake_status="feedback_intake_blocked",
            feedback_blocking_reasons=["feedback_has_invalid_timestamp"],
            feedback_intake_report=_feedback_report(
                {"bad_pacing": 1},
                status="feedback_intake_blocked",
            ),
        )
    )

    payload = report.to_dict()
    assert payload["status"] == "style_dna_update_blocked"
    assert "feedback_has_invalid_timestamp" in payload["blocking_reasons"]
    assert payload["ready_for_human_review"] is False
    assert payload["can_write_style_dna"] is False


def test_valid_feedback_creates_draft_and_core_proposals():
    report = build_style_dna_feedback_update_report(
        _job(
            feedback_intake_report=_feedback_report(
                {
                    "bad_pacing": 2,
                    "wrong_hook": 2,
                    "missing_reaction": 2,
                    "audio_too_loud": 1,
                    "audio_too_quiet": 1,
                    "sentence_cut_violation": 2,
                    "render_quality_issue": 1,
                    "output_format_issue": 1,
                },
                submission_count=3,
                average_video_score=4.5,
            )
        )
    )

    payload = report.to_dict()
    names = _proposal_names(report)

    assert payload["status"] in {
        "style_dna_update_draft_ready",
        "style_dna_update_draft_ready_with_warnings",
    }
    assert payload["proposal_count"] >= 10
    assert "preferred_avg_clip_duration" in names
    assert "preferred_hook_energy_min" in names
    assert "reaction_shot_priority" in names
    assert "target_voice_gain_db" in names
    assert "sentence_boundary_strictness" in names
    assert "render_quality_review_required" in names
    assert "output_format_review_required" in names
    assert payload["ready_for_human_review"] is True
    assert payload["ready_for_later_apply"] is True
    assert payload["can_write_style_dna"] is False
    assert payload["can_update_profile"] is False
    assert payload["can_change_cutting_rules"] is False
    assert payload["can_modify_timeline"] is False
    assert payload["can_trigger_render"] is False
    assert payload["can_publish"] is False


def test_positive_tags_create_conservative_stabilization_proposals():
    report = build_style_dna_feedback_update_report(
        _job(
            feedback_intake_report=_feedback_report(
                {
                    "good_pacing": 2,
                    "strong_hook": 2,
                    "good_reaction": 2,
                    "good_censor": 1,
                },
                submission_count=3,
                average_video_score=8.5,
            )
        )
    )

    payload = report.to_dict()
    draft = payload["draft"]
    names = _proposal_names(report)

    assert "preferred_avg_clip_duration" in names
    assert "pacing_sensitivity" in names
    assert "hook_strategy_confidence" in names
    assert "reaction_shot_priority" in names
    assert "censor_sfx_sensitivity" in names
    assert payload["confidence"] <= 0.72
    assert draft["overfitting_risk"] in {"low", "medium"}


def test_single_feedback_caps_confidence_and_marks_overfitting_medium():
    report = build_style_dna_feedback_update_report(
        _job(
            feedback_intake_report=_feedback_report(
                {"bad_pacing": 1},
                submission_count=1,
                average_video_score=6.0,
            )
        )
    )

    payload = report.to_dict()
    assert payload["confidence"] <= 0.60
    assert payload["draft"]["overfitting_risk"] == "medium"
    assert "overfitting_risk_medium" in payload["warnings"]


def test_repeated_tags_raise_confidence():
    one = build_style_dna_feedback_update_report(
        _job(feedback_intake_report=_feedback_report({"bad_pacing": 1}, submission_count=2))
    ).to_dict()
    repeated = build_style_dna_feedback_update_report(
        _job(feedback_intake_report=_feedback_report({"bad_pacing": 3}, submission_count=3))
    ).to_dict()

    assert repeated["confidence"] > one["confidence"]


def test_existing_snapshot_is_read_but_not_written_and_file_write_stays_locked():
    snapshot = {"preferred_avg_clip_duration": 5.0}
    job = _job(
        existing_style_dna_snapshot=snapshot,
        style_dna_update_allow_file_write=True,
        feedback_intake_report=_feedback_report({"bad_pacing": 2}, submission_count=2),
    )

    payload = build_style_dna_feedback_update_report(job).to_dict()
    proposal = payload["draft"]["proposals"][0]

    assert proposal["current_value"] == 5.0
    assert snapshot == {"preferred_avg_clip_duration": 5.0}
    assert payload["can_write_style_dna"] is False
    assert "style_dna_file_write_not_allowed_in_2b_60" in payload["warnings"]


def test_unsafe_feedback_permission_flags_block_update():
    payload = build_style_dna_feedback_update_report(
        _job(
            feedback_can_publish=True,
            feedback_intake_report=_feedback_report({"bad_pacing": 2}, submission_count=2),
        )
    ).to_dict()

    assert payload["status"] == "style_dna_update_blocked"
    assert "unsafe_feedback_permission_flag_true:feedback_can_publish" in payload["blocking_reasons"]
    assert payload["can_publish"] is False
