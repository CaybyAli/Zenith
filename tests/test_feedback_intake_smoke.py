from __future__ import annotations

from types import SimpleNamespace

from core.feedback_intake import build_feedback_intake_report


def _report(job):
    return build_feedback_intake_report(job).to_dict()


def test_feedback_intake_without_feedback_waits_for_feedback():
    report = _report(SimpleNamespace(job_id="job_without_feedback"))

    assert report["status"] == "feedback_intake_waiting_for_feedback"
    assert report["review_required"] is True
    assert report["submission_count"] == 0
    assert report["ready_for_style_dna_update"] is False
    assert report["can_update_style_dna"] is False
    assert report["can_modify_timeline"] is False
    assert report["can_trigger_render"] is False
    assert report["can_publish"] is False


def test_feedback_intake_accepts_valid_video_score_1_to_10():
    for score in [1, 5.55, 10]:
        report = _report(
            SimpleNamespace(
                job_id=f"job_score_{score}",
                feedback_video_score=score,
                feedback_comment="Review feedback vorhanden.",
            )
        )

        assert report["status"] == "feedback_intake_ready"
        assert report["submission_count"] == 1
        assert report["average_video_score"] == round(float(score), 1)
        assert report["ready_for_style_dna_update"] is True


def test_feedback_intake_blocks_score_outside_1_to_10():
    report = _report(
        SimpleNamespace(
            job_id="job_bad_score",
            feedback_video_score=11,
            feedback_comment="Score ist zu hoch.",
        )
    )

    assert report["status"] == "feedback_intake_blocked"
    assert "video_score_outside_1_to_10" in report["blocking_reasons"]
    assert report["ready_for_style_dna_update"] is False


def test_feedback_intake_comment_without_score_warns_but_does_not_crash():
    report = _report(
        SimpleNamespace(
            job_id="job_comment_only",
            feedback_comment="Nur Kommentar ohne Score.",
        )
    )

    assert report["status"] == "feedback_intake_ready_with_warnings"
    assert "feedback_comment_without_video_score" in report["warnings"]
    assert report["submission_count"] == 1
    assert report["ready_for_style_dna_update"] is False


def test_feedback_intake_stores_timestamp_feedback_and_counts_sentiment():
    report = _report(
        SimpleNamespace(
            job_id="job_timestamp_feedback",
            feedback_video_score=8,
            feedback_timestamp_items=[
                {
                    "timestamp_seconds": 5,
                    "start_seconds": 4,
                    "end_seconds": 6,
                    "category": "hook",
                    "tag": "strong_hook",
                    "sentiment": "positive",
                    "severity": "high",
                    "comment": "Starker Hook.",
                },
                {
                    "timestamp_seconds": 20,
                    "category": "pacing",
                    "tag": "bad_pacing",
                    "sentiment": "negative",
                    "severity": "medium",
                    "comment": "Hier verliert es Tempo.",
                },
                {
                    "timestamp_seconds": 30,
                    "category": "visual",
                    "tag": "good_cut",
                    "sentiment": "neutral",
                    "severity": "info",
                },
            ],
        )
    )

    assert report["status"] == "feedback_intake_ready"
    assert report["timestamp_feedback_count"] == 3
    assert report["positive_feedback_count"] == 1
    assert report["negative_feedback_count"] == 1
    assert report["neutral_feedback_count"] == 1
    assert report["tags_summary"]["strong_hook"] == 1
    assert report["tags_summary"]["bad_pacing"] == 1
    assert report["tags_summary"]["good_cut"] == 1
    assert report["category_summary"]["hook"] == 1
    assert report["category_summary"]["pacing"] == 1
    assert report["category_summary"]["visual"] == 1


def test_feedback_intake_blocks_invalid_timestamp_ranges():
    negative_report = _report(
        SimpleNamespace(
            job_id="job_negative_timestamp",
            feedback_video_score=7,
            feedback_timestamp_items=[
                {
                    "timestamp_seconds": -1,
                    "category": "cut",
                    "tag": "cut_too_early",
                    "sentiment": "negative",
                    "comment": "Negativer Timestamp.",
                }
            ],
        )
    )

    assert negative_report["status"] == "feedback_intake_blocked"
    assert "timestamp_seconds_negative" in negative_report["blocking_reasons"]

    bad_range_report = _report(
        SimpleNamespace(
            job_id="job_bad_range",
            feedback_video_score=7,
            feedback_timestamp_items=[
                {
                    "timestamp_seconds": 10,
                    "start_seconds": 12,
                    "end_seconds": 11,
                    "category": "cut",
                    "tag": "cut_too_late",
                    "sentiment": "negative",
                    "comment": "Ende liegt vor Start.",
                }
            ],
        )
    )

    assert bad_range_report["status"] == "feedback_intake_blocked"
    assert "end_seconds_before_start_seconds" in bad_range_report["blocking_reasons"]


def test_feedback_intake_unknown_tag_is_custom_warning_and_saved():
    report = _report(
        SimpleNamespace(
            job_id="job_custom_tag",
            feedback_video_score=6,
            feedback_tags=["my_custom_tag"],
            feedback_timestamp_items=[
                {
                    "timestamp_seconds": 3,
                    "category": "my_custom_category",
                    "tag": "another_custom_tag",
                    "sentiment": "neutral",
                }
            ],
        )
    )

    assert report["status"] == "feedback_intake_ready_with_warnings"
    assert "unknown_feedback_tag:my_custom_tag" in report["warnings"]
    assert "unknown_feedback_tag:another_custom_tag" in report["warnings"]
    assert "unknown_feedback_category:my_custom_category" in report["warnings"]
    assert report["tags_summary"]["my_custom_tag"] == 1
    assert report["tags_summary"]["another_custom_tag"] == 1
    assert report["category_summary"]["my_custom_category"] == 1


def test_feedback_intake_safety_flags_never_enable_actions():
    report = _report(
        SimpleNamespace(
            job_id="job_safety",
            feedback_video_score=9,
            feedback_timestamp_items=[
                {
                    "timestamp_seconds": 1,
                    "category": "hook",
                    "tag": "strong_hook",
                    "sentiment": "positive",
                }
            ],
        )
    )

    assert report["ready_for_style_dna_update"] is True
    assert report["can_update_style_dna"] is False
    assert report["can_change_profile"] is False
    assert report["can_change_cutting_rules"] is False
    assert report["can_modify_timeline"] is False
    assert report["can_trigger_render"] is False
    assert report["can_publish"] is False
