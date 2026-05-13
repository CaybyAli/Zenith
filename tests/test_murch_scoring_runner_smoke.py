from __future__ import annotations

from pathlib import Path

from core.murch_scoring_runner import (
    apply_murch_scoring_run_report_to_job,
    run_murch_scoring_for_job,
)
from models.job import Job
from models.murch_scoring import MURCH_TIER_HIGH, STATUS_SKIPPED_NO_SEGMENTS
from models.murch_scoring_run import MurchScoringRunReport


PROJECT_ROOT = Path(__file__).resolve().parents[1]

NEW_FILES = [
    PROJECT_ROOT / "models" / "murch_scoring_run.py",
    PROJECT_ROOT / "core" / "murch_scoring_runner.py",
    PROJECT_ROOT / "tests" / "test_murch_scoring_runner_smoke.py",
]

FORBIDDEN_ACTION_PARTS = [
    "force_cut",
    "auto_remove",
    "hard_remove",
    "remove_now",
    "auto_cut",
    "auto_trim",
    "auto_highlight",
    "highlight_now",
    "auto_hook",
    "auto_mute",
    "censor_now",
    "delete_segment",
    "drop_segment",
    "timeline_apply_now",
    "apply_cut",
    "render_now",
]


def _minimal_job_data() -> dict:
    return {
        "job_id": "job_murch_smoke",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "longform",
        "target_platforms": ["youtube"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
    }


def _high_segment() -> dict:
    return {
        "segment_id": "segment_high",
        "start_seconds": 10.0,
        "end_seconds": 20.0,
        "center_seconds": 15.0,
        "duration_seconds": 10.0,
        "segment_type": "highlight",
        "confidence": 0.9,
        "segment_score": 0.9,
        "content_value_score": 0.9,
        "dead_content_score": 0.0,
        "protection_score": 0.0,
        "technical_risk_score": 0.0,
        "hook_candidate_score": 0.4,
        "censor_required": False,
        "is_highlight_candidate": True,
        "is_hook_candidate": False,
        "is_protected_context": False,
        "is_dead_candidate": False,
        "is_transition_candidate": False,
        "is_technical_warning": False,
        "recommendation": "review_segment_highlight_candidate",
        "evidence": {
            "signal_types": [
                "content_value_high_segment",
                "keyword_hype_segment",
            ]
        },
        "source_signal_ids": ["signal_high"],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


def test_murch_scoring_run_report_roundtrip() -> None:
    job = {
        "segment_classification_segments": [_high_segment()],
        "unified_edit_signals": [],
    }
    report = run_murch_scoring_for_job(job)
    loaded = MurchScoringRunReport.from_dict(report.to_dict())

    assert loaded.to_dict() == report.to_dict()
    assert loaded.source == "murch_scoring"


def test_runner_uses_job_segment_classification_segments() -> None:
    job = {
        "segment_classification_segments": [_high_segment()],
    }

    report = run_murch_scoring_for_job(job)

    assert report.status in {"ok", "completed_with_warnings"}
    assert report.segment_score_count == 1
    assert report.high_score_count == 1
    assert report.segment_scores[0].segment_id == "segment_high"
    assert report.segment_scores[0].murch_tier == MURCH_TIER_HIGH


def test_runner_uses_optional_unified_edit_signals() -> None:
    segment = _high_segment()
    segment["source_signal_ids"] = ["signal_story"]

    job = {
        "segment_classification_segments": [segment],
        "unified_edit_signals": [
            {
                "signal_id": "signal_story",
                "signal_type": "interaction_question_answer_segment",
                "source": "interaction_classification",
                "score": 0.95,
                "confidence": 0.95,
                "start_seconds": 10.0,
                "end_seconds": 20.0,
            }
        ],
    }

    report = run_murch_scoring_for_job(job)

    assert report.segment_score_count == 1
    assert report.segment_scores[0].story_score >= 0.7


def test_runner_skipped_no_segments() -> None:
    report = run_murch_scoring_for_job({"segment_classification_segments": []})

    assert report.status == STATUS_SKIPPED_NO_SEGMENTS
    assert report.segment_score_count == 0
    assert report.recommendation == "murch_scoring_skipped_no_segments"


def test_apply_report_writes_job_fields() -> None:
    job = Job.from_dict(_minimal_job_data())
    report = run_murch_scoring_for_job(
        {"segment_classification_segments": [_high_segment()]}
    )

    apply_murch_scoring_run_report_to_job(job, report)

    assert job.murch_scoring_status == report.status
    assert job.murch_scoring_segment_score_count == 1
    assert job.murch_scoring_high_score_count == 1
    assert job.murch_scoring_recommendation == report.recommendation
    assert len(job.murch_scoring_segment_scores) == 1
    assert job.murch_scoring_report["source"] == "murch_scoring"


def test_old_jobs_load_without_murch_fields() -> None:
    job = Job.from_dict(_minimal_job_data())

    assert job.murch_scoring_report == {}
    assert job.murch_scoring_status is None
    assert job.murch_scoring_segment_scores == []
    assert job.murch_scoring_segment_score_count == 0
    assert job.murch_scoring_recommendation is None


def test_job_to_dict_contains_murch_scoring_fields() -> None:
    job = Job.from_dict(_minimal_job_data())
    data = job.to_dict()

    assert "murch_scoring_report" in data
    assert "murch_scoring_status" in data
    assert "murch_scoring_segment_scores" in data
    assert "murch_scoring_segment_score_count" in data
    assert "murch_scoring_high_score_count" in data
    assert "murch_scoring_medium_score_count" in data
    assert "murch_scoring_low_score_count" in data
    assert "murch_scoring_protected_context_count" in data
    assert "murch_scoring_censor_required_count" in data
    assert "murch_scoring_technical_warning_count" in data
    assert "murch_scoring_avg_score" in data
    assert "murch_scoring_max_score" in data
    assert "murch_scoring_min_score" in data
    assert "murch_scoring_recommendation" in data


def test_censor_required_is_counted() -> None:
    segment = _high_segment()
    segment["segment_id"] = "segment_censor"
    segment["censor_required"] = True
    segment["segment_type"] = "censor_required_segment"
    segment["evidence"] = {"signal_types": ["profanity_censor_sfx_required"]}

    report = run_murch_scoring_for_job(
        {"segment_classification_segments": [segment]}
    )

    assert report.censor_required_count == 1
    assert report.segment_scores[0].censor_required is True
    assert report.segment_scores[0].recommendation == "review_murch_score_with_censor_sfx"


def test_protected_context_is_counted() -> None:
    segment = _high_segment()
    segment["segment_id"] = "segment_protected"
    segment["segment_type"] = "protected_context"
    segment["protection_score"] = 0.9
    segment["is_protected_context"] = True
    segment["evidence"] = {"signal_types": ["interaction_question_answer_segment"]}

    report = run_murch_scoring_for_job(
        {"segment_classification_segments": [segment]}
    )

    assert report.protected_context_count == 1
    assert report.segment_scores[0].is_protected_context is True
    assert report.segment_scores[0].recommendation == "review_protected_murch_context"


def test_no_crash_with_broken_segments() -> None:
    job = {
        "segment_classification_segments": [
            None,
            {"segment_id": "broken_but_safe"},
        ]
    }

    report = run_murch_scoring_for_job(job)

    assert report.segment_score_count >= 1
    assert isinstance(report.errors, list)


def test_runner_does_not_create_forbidden_actions() -> None:
    report = run_murch_scoring_for_job(
        {"segment_classification_segments": [_high_segment()]}
    )

    serialized = str(report.to_dict())

    for forbidden in FORBIDDEN_ACTION_PARTS:
        assert forbidden not in serialized


def test_new_files_have_no_bom_and_end_with_newline() -> None:
    for path in NEW_FILES:
        data = path.read_bytes()

        assert data.startswith(b"\xef\xbb\xbf") is False
        assert data.endswith(b"\n")
