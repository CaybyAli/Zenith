from core.learning_pattern_recognition import build_learning_pattern_recognition_report


def test_learning_pattern_waits_without_feedback():
    report = build_learning_pattern_recognition_report(
        {
            "job_id": "job_waiting",
            "feedback_intake_status": "feedback_intake_waiting_for_feedback",
            "feedback_submission_count": 0,
        }
    )

    assert report["status"] == "learning_pattern_waiting_for_feedback"
    assert report["trend_count"] == 0
    assert report["cluster_count"] == 0
    assert report["ready_for_future_style_dna_proposal"] is False
    assert report["can_update_style_dna"] is False
    assert report["can_write_style_dna"] is False
    assert report["can_change_profile"] is False
    assert report["can_change_cutting_rules"] is False
    assert report["can_modify_timeline"] is False
    assert report["can_trigger_render"] is False
    assert report["can_publish"] is False


def test_learning_pattern_blocks_when_feedback_intake_failed():
    report = build_learning_pattern_recognition_report(
        {
            "job_id": "job_blocked",
            "feedback_intake_status": "feedback_intake_failed",
            "feedback_submission_count": 2,
            "feedback_tags_summary": {"bad_pacing": 2},
        }
    )

    assert report["status"] == "learning_pattern_blocked"
    assert "source_feedback_status_feedback_intake_failed" in report["blocking_reasons"]


def test_learning_pattern_carries_blocking_reasons():
    report = build_learning_pattern_recognition_report(
        {
            "job_id": "job_blocking_reason",
            "feedback_intake_status": "feedback_intake_ready",
            "feedback_blocking_reasons": ["feedback_source_blocked"],
            "style_dna_update_blocking_reasons": ["style_dna_update_blocked"],
        }
    )

    assert report["status"] == "learning_pattern_blocked"
    assert "feedback_source_blocked" in report["blocking_reasons"]
    assert "style_dna_update_blocked" in report["blocking_reasons"]


def test_learning_pattern_single_job_warning_and_confidence_cap():
    report = build_learning_pattern_recognition_report(
        {
            "job_id": "job_single",
            "feedback_intake_status": "feedback_intake_ready",
            "feedback_submission_count": 3,
            "feedback_tags_summary": {"bad_pacing": 3},
        }
    )

    assert report["status"] == "learning_pattern_ready_with_warnings"
    assert "learning_pattern_history_missing_single_job_only" in report["warnings"]
    assert report["trend_count"] >= 1
    assert report["cluster_count"] >= 1
    assert report["confidence"] <= 0.60


def test_learning_pattern_tags_summary_creates_trends_and_clusters():
    report = build_learning_pattern_recognition_report(
        {
            "job_id": "job_tags",
            "feedback_intake_status": "feedback_intake_ready",
            "feedback_submission_count": 8,
            "feedback_tags_summary": {
                "bad_pacing": 2,
                "wrong_hook": 2,
                "missing_reaction": 2,
                "audio_too_loud": 2,
                "segment_too_long": 2,
                "sentence_cut_violation": 2,
                "render_quality_issue": 2,
                "output_format_issue": 2,
            },
        }
    )

    trend_tags = {trend["tag"] for trend in report["trends"]}
    cluster_types = {cluster["cluster_type"] for cluster in report["clusters"]}

    assert "bad_pacing" in trend_tags
    assert "wrong_hook" in trend_tags
    assert "missing_reaction" in trend_tags
    assert "audio_too_loud" in trend_tags
    assert "segment_too_long" in trend_tags
    assert "sentence_cut_violation" in trend_tags
    assert "render_quality_issue" in trend_tags
    assert "output_format_issue" in trend_tags

    assert "pacing_pattern" in cluster_types
    assert "hook_pattern" in cluster_types
    assert "reaction_pattern" in cluster_types
    assert "audio_pattern" in cluster_types
    assert "segment_length_pattern" in cluster_types
    assert "sentence_boundary_pattern" in cluster_types
    assert "render_quality_pattern" in cluster_types
    assert "output_format_pattern" in cluster_types


def test_learning_pattern_audio_quiet_and_segment_short_clusters():
    report = build_learning_pattern_recognition_report(
        {
            "job_id": "job_audio_segment",
            "feedback_intake_status": "feedback_intake_ready",
            "feedback_submission_count": 4,
            "feedback_tags_summary": {
                "audio_too_quiet": 2,
                "segment_too_short": 2,
            },
        }
    )

    cluster_types = {cluster["cluster_type"] for cluster in report["clusters"]}
    assert "audio_pattern" in cluster_types
    assert "segment_length_pattern" in cluster_types


def test_learning_pattern_repeated_issue_repeated_success_and_mixed_signal():
    repeated_issue = build_learning_pattern_recognition_report(
        {
            "job_id": "job_issue",
            "feedback_intake_status": "feedback_intake_ready",
            "feedback_submission_count": 2,
            "feedback_tags_summary": {"bad_pacing": 2},
        }
    )
    assert repeated_issue["trends"][0]["trend_type"] == "repeated_issue"
    assert repeated_issue["repeated_issue_count"] >= 1

    repeated_success = build_learning_pattern_recognition_report(
        {
            "job_id": "job_success",
            "feedback_intake_status": "feedback_intake_ready",
            "feedback_submission_count": 2,
            "feedback_tags_summary": {"strong_hook": 2},
        }
    )
    assert repeated_success["trends"][0]["trend_type"] == "repeated_success"
    assert repeated_success["repeated_success_count"] >= 1

    mixed_signal = build_learning_pattern_recognition_report(
        {
            "job_id": "job_mixed",
            "feedback_intake_status": "feedback_intake_ready",
            "feedback_submission_count": 2,
            "feedback_submissions": [
                {"tags": ["bad_pacing"], "sentiment": "negative"},
                {"tags": ["bad_pacing"], "sentiment": "positive"},
            ],
        }
    )
    assert mixed_signal["trends"][0]["trend_type"] == "mixed_signal"
    assert mixed_signal["confidence"] <= 0.55
    assert mixed_signal["overfitting_risk"] == "high"


def test_learning_pattern_ready_for_future_proposal_can_be_true_with_history():
    report = build_learning_pattern_recognition_report(
        {
            "job_id": "job_ready",
            "feedback_intake_status": "feedback_intake_ready",
            "feedback_submission_count": 4,
            "feedback_tags_summary": {"bad_pacing": 2},
            "feedback_history_snapshot": [
                {
                    "job_id": "old_job_1",
                    "feedback_tags_summary": {"bad_pacing": 1},
                },
                {
                    "job_id": "old_job_2",
                    "feedback_tags_summary": {"bad_pacing": 1},
                },
            ],
            "learning_pattern_min_occurrences": 2,
            "learning_pattern_min_confidence": 0.50,
        }
    )

    assert report["cluster_count"] >= 1
    assert report["confidence"] >= 0.50
    assert report["overfitting_risk"] != "high"
    assert report["ready_for_future_style_dna_proposal"] is True
    assert report["can_update_style_dna"] is False
    assert report["can_write_style_dna"] is False
    assert report["can_change_profile"] is False
    assert report["can_change_cutting_rules"] is False
    assert report["can_modify_timeline"] is False
    assert report["can_trigger_render"] is False
    assert report["can_publish"] is False
