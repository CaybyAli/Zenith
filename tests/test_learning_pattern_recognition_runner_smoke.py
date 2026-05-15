from core.learning_pattern_recognition_runner import run_learning_pattern_recognition_for_job
from models.job import Job


def test_learning_pattern_runner_writes_job_fields():
    job = Job.from_dict(
        {
            "job_id": "job_runner",
            "feedback_intake_status": "feedback_intake_ready",
            "feedback_submission_count": 3,
            "feedback_tags_summary": {"bad_pacing": 3},
        }
    )

    report = run_learning_pattern_recognition_for_job(job)

    assert job.learning_pattern_recognition_report == report
    assert job.learning_pattern_status == report["status"]
    assert job.learning_pattern_feedback_sample_count == report["feedback_sample_count"]
    assert job.learning_pattern_trend_count == report["trend_count"]
    assert job.learning_pattern_cluster_count == report["cluster_count"]
    assert job.learning_pattern_trends == report["trends"]
    assert job.learning_pattern_clusters == report["clusters"]
    assert job.learning_pattern_confidence == report["confidence"]
    assert job.learning_pattern_overfitting_risk == report["overfitting_risk"]
    assert job.learning_pattern_can_update_style_dna is False
    assert job.learning_pattern_can_write_style_dna is False
    assert job.learning_pattern_can_change_profile is False
    assert job.learning_pattern_can_change_cutting_rules is False
    assert job.learning_pattern_can_modify_timeline is False
    assert job.learning_pattern_can_trigger_render is False
    assert job.learning_pattern_can_publish is False


def test_learning_pattern_runner_supports_dict_jobs():
    job = {
        "job_id": "job_runner_dict",
        "feedback_intake_status": "feedback_intake_ready",
        "feedback_submission_count": 2,
        "feedback_tags_summary": {"wrong_hook": 2},
    }

    report = run_learning_pattern_recognition_for_job(job)

    assert job["learning_pattern_recognition_report"] == report
    assert job["learning_pattern_status"] == report["status"]
    assert job["learning_pattern_cluster_count"] >= 1
    assert job["learning_pattern_can_update_style_dna"] is False
    assert job["learning_pattern_can_write_style_dna"] is False


def test_job_from_dict_loads_learning_pattern_fields_safely():
    job = Job.from_dict(
        {
            "job_id": "job_from_dict_learning",
            "learning_pattern_recognition_report": {
                "status": "learning_pattern_ready",
            },
            "learning_pattern_status": "learning_pattern_ready",
            "learning_pattern_feedback_sample_count": 5,
            "learning_pattern_trends": [{"tag": "bad_pacing"}],
            "learning_pattern_clusters": [{"cluster_type": "pacing_pattern"}],
            "learning_pattern_trend_count": 1,
            "learning_pattern_cluster_count": 1,
            "learning_pattern_top_positive_patterns": ["strong_hook"],
            "learning_pattern_top_negative_patterns": ["bad_pacing"],
            "learning_pattern_repeated_issue_count": 1,
            "learning_pattern_repeated_success_count": 1,
            "learning_pattern_confidence": 0.75,
            "learning_pattern_overfitting_risk": "medium",
            "learning_pattern_ready_for_future_style_dna_proposal": True,
            "learning_pattern_can_update_style_dna": True,
            "learning_pattern_can_write_style_dna": True,
            "learning_pattern_can_change_profile": True,
            "learning_pattern_can_change_cutting_rules": True,
            "learning_pattern_can_modify_timeline": True,
            "learning_pattern_can_trigger_render": True,
            "learning_pattern_can_publish": True,
            "learning_pattern_warnings": ["warning"],
            "learning_pattern_blocking_reasons": ["blocker"],
            "learning_pattern_recommendation": "review_learning_pattern_recognition",
            "feedback_history_snapshot": [{"job_id": "old_job"}],
            "style_dna_learning_history_snapshot": [{"job_id": "old_job"}],
            "learning_pattern_min_occurrences": 3,
            "learning_pattern_min_confidence": 0.6,
            "learning_pattern_requested_by": "tester",
            "learning_pattern_requested_at": "2026-05-15T00:00:00Z",
        }
    )

    assert job.learning_pattern_status == "learning_pattern_ready"
    assert job.learning_pattern_feedback_sample_count == 5
    assert job.learning_pattern_trend_count == 1
    assert job.learning_pattern_cluster_count == 1
    assert job.learning_pattern_ready_for_future_style_dna_proposal is True
    assert job.learning_pattern_can_update_style_dna is False
    assert job.learning_pattern_can_write_style_dna is False
    assert job.learning_pattern_can_change_profile is False
    assert job.learning_pattern_can_change_cutting_rules is False
    assert job.learning_pattern_can_modify_timeline is False
    assert job.learning_pattern_can_trigger_render is False
    assert job.learning_pattern_can_publish is False
    assert isinstance(job.feedback_history_snapshot, list)
    assert isinstance(job.style_dna_learning_history_snapshot, list)
    assert job.learning_pattern_min_occurrences == 3
    assert job.learning_pattern_min_confidence == 0.6
