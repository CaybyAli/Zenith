from __future__ import annotations

from types import SimpleNamespace

from core.feedback_intake_runner import run_feedback_intake_for_job
from models.job import Job


def test_feedback_intake_runner_writes_job_fields():
    job = SimpleNamespace(
        job_id="runner_job",
        feedback_video_score=8,
        feedback_comment="Runner soll Job-Felder schreiben.",
        feedback_tags=["good_cut"],
        feedback_timestamp_items=[
            {
                "timestamp_seconds": 12,
                "category": "cut",
                "tag": "good_cut",
                "sentiment": "positive",
            }
        ],
    )

    report = run_feedback_intake_for_job(job)

    assert report["status"] == "feedback_intake_ready"
    assert job.feedback_intake_status == "feedback_intake_ready"
    assert job.feedback_submission_count == 1
    assert job.feedback_timestamp_feedback_count == 1
    assert job.feedback_positive_feedback_count == 1
    assert job.feedback_average_video_score == 8.0
    assert job.feedback_tags_summary == {"good_cut": 2}
    assert job.feedback_review_required is True
    assert job.feedback_ready_for_style_dna_update is True
    assert job.feedback_can_update_style_dna is False
    assert job.feedback_can_change_profile is False
    assert job.feedback_can_change_cutting_rules is False
    assert job.feedback_can_modify_timeline is False
    assert job.feedback_can_trigger_render is False
    assert job.feedback_can_publish is False


def test_job_from_dict_loads_feedback_intake_fields_and_locks_actions():
    job = Job.from_dict(
        {
            "job_id": "from_dict_job",
            "feedback_intake_report": {"status": "feedback_intake_ready"},
            "feedback_intake_status": "feedback_intake_ready",
            "feedback_submissions": [{"submission_id": "s1"}],
            "feedback_submission_count": 1,
            "feedback_timestamp_feedback_count": 2,
            "feedback_positive_feedback_count": 1,
            "feedback_negative_feedback_count": 1,
            "feedback_neutral_feedback_count": 0,
            "feedback_average_video_score": 7.5,
            "feedback_tags_summary": {"strong_hook": 1},
            "feedback_category_summary": {"hook": 1},
            "feedback_review_required": True,
            "feedback_ready_for_style_dna_update": True,
            "feedback_can_update_style_dna": True,
            "feedback_can_change_profile": True,
            "feedback_can_change_cutting_rules": True,
            "feedback_can_modify_timeline": True,
            "feedback_can_trigger_render": True,
            "feedback_can_publish": True,
            "feedback_warnings": ["warning_one"],
            "feedback_blocking_reasons": [],
            "feedback_recommendation": "review_feedback_intake",
            "feedback_submission": {"video_score": 7},
            "feedback_video_score": 7,
            "feedback_comment": "Direktes Feedback.",
            "feedback_timestamp_items": [{"timestamp_seconds": 1}],
            "feedback_tags": ["strong_hook"],
            "feedback_submitted_by": "manual_review",
            "feedback_submitted_at": "2026-05-15T00:00:00+00:00",
        }
    )

    assert job.feedback_intake_status == "feedback_intake_ready"
    assert job.feedback_submission_count == 1
    assert job.feedback_timestamp_feedback_count == 2
    assert job.feedback_average_video_score == 7.5
    assert job.feedback_tags_summary == {"strong_hook": 1}
    assert job.feedback_category_summary == {"hook": 1}
    assert job.feedback_ready_for_style_dna_update is True

    assert job.feedback_can_update_style_dna is False
    assert job.feedback_can_change_profile is False
    assert job.feedback_can_change_cutting_rules is False
    assert job.feedback_can_modify_timeline is False
    assert job.feedback_can_trigger_render is False
    assert job.feedback_can_publish is False

    assert job.feedback_video_score == 7.0
    assert job.feedback_comment == "Direktes Feedback."
    assert job.feedback_tags == ["strong_hook"]
