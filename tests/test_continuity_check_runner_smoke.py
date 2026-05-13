from pathlib import Path

from core.continuity_check_runner import (
    apply_continuity_check_run_report_to_job,
    run_continuity_check_for_job,
)
from models.continuity_check import ContinuityCheckResult, ContinuityIssue
from models.continuity_check_run import ContinuityCheckRunReport
from models.job import Job


ROOT = Path(__file__).resolve().parents[1]

NEW_FILES = [
    ROOT / "models" / "continuity_check_run.py",
    ROOT / "core" / "continuity_check_runner.py",
    ROOT / "tests" / "test_continuity_check_runner_smoke.py",
]

BASE_JOB_DATA = {
    "job_id": "job_continuity_check_old",
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


def _transition_decision(
    transition_type="hard_cut_review",
    item_id="item_1",
    start=0.0,
    end=4.0,
):
    return {
        "decision_id": f"decision_{item_id}",
        "source_item_id": item_id,
        "segment_id": f"seg_{item_id}",
        "start_seconds": start,
        "end_seconds": end,
        "center_seconds": (start + end) / 2.0,
        "duration_seconds": end - start,
        "transition_type": transition_type,
        "transition_confidence": 0.8,
        "priority": "medium",
        "cut_list_action": "KEEP",
        "duration_status": "duration_ok",
    }


def _cut_list_item(item_id="item_1", start=0.0, end=4.0, action="KEEP"):
    return {
        "item_id": item_id,
        "segment_id": f"seg_{item_id}",
        "start_seconds": start,
        "end_seconds": end,
        "center_seconds": (start + end) / 2.0,
        "duration_seconds": end - start,
        "proposed_action": action,
        "action_confidence": 0.8,
    }


def _clip_duration_recommendation(
    item_id="item_1",
    start=0.0,
    end=4.0,
    status="duration_ok",
    is_protected=False,
    is_censor_keep=False,
):
    return {
        "recommendation_id": f"duration_{item_id}",
        "source_item_id": item_id,
        "segment_id": f"seg_{item_id}",
        "start_seconds": start,
        "end_seconds": end,
        "center_seconds": (start + end) / 2.0,
        "duration_seconds": end - start,
        "duration_status": status,
        "confidence": 0.8,
        "is_protected": is_protected,
        "is_censor_keep": is_censor_keep,
    }


def _signal(signal_type, center=2.0):
    return {
        "signal_id": f"sig_{signal_type}",
        "signal_type": signal_type,
        "center_seconds": center,
        "confidence": 0.9,
        "priority": "high",
    }


def test_continuity_check_run_report_roundtrip():
    issue = ContinuityIssue(
        issue_id="issue_1",
        issue_type="sentence_break_risk",
        severity="high",
        confidence=0.9,
        priority="high",
        is_blocking=True,
        recommendation="review_sentence_boundary_continuity",
    )
    result = ContinuityCheckResult(
        status="completed_with_warnings",
        issues=[issue],
        recommendation="review_sentence_boundary_continuity",
    )
    report = ContinuityCheckRunReport(
        status="completed_with_warnings",
        continuity_check_result=result,
        issues=[issue],
        issue_count=1,
        blocking_issue_count=1,
        sentence_break_risk_count=1,
        recommendation="review_sentence_boundary_continuity",
        metadata={"source": "test"},
    )

    assert ContinuityCheckRunReport.from_dict(report.to_dict()).to_dict() == report.to_dict()


def test_runner_uses_job_transition_decision_decisions():
    job = {
        "transition_decision_decisions": [_transition_decision()],
    }

    report = run_continuity_check_for_job(job)

    assert report.status == "ok"
    assert report.issue_count == 0


def test_runner_uses_fallback_job_cut_list_items():
    job = {
        "cut_list_items": [_cut_list_item()],
    }

    report = run_continuity_check_for_job(job)

    assert report.status == "ok"
    assert report.issue_count == 0


def test_runner_uses_optional_clip_duration_recommendations():
    job = {
        "transition_decision_decisions": [_transition_decision()],
        "clip_duration_recommendations": [
            _clip_duration_recommendation(
                status="too_long_review",
                is_protected=True,
            )
        ],
    }

    report = run_continuity_check_for_job(job)

    assert report.protected_context_count >= 1
    assert any(
        issue.issue_type == "protected_context_violation"
        for issue in report.issues
    )


def test_runner_uses_optional_unified_edit_signals():
    job = {
        "transition_decision_decisions": [_transition_decision()],
        "unified_edit_signals": [_signal("sentence_boundary_protection")],
    }

    report = run_continuity_check_for_job(job)

    assert report.sentence_break_risk_count == 1
    assert report.recommendation == "review_sentence_boundary_continuity"


def test_runner_skips_when_no_transition_decisions_or_cut_list_items_exist():
    report = run_continuity_check_for_job({})

    assert report.status == "skipped_no_transition_decisions"
    assert report.issue_count == 0
    assert report.recommendation == "continuity_check_skipped_no_inputs"


def test_apply_writes_continuity_check_fields_to_dict_job():
    job = {
        "transition_decision_decisions": [_transition_decision()],
        "unified_edit_signals": [_signal("sentence_boundary_protection")],
    }
    report = run_continuity_check_for_job(job)

    apply_continuity_check_run_report_to_job(job, report)

    assert job["continuity_check_report"]["source"] == "continuity_check"
    assert job["continuity_check_status"] == "completed_with_warnings"
    assert len(job["continuity_check_issues"]) == 1
    assert job["continuity_check_issue_count"] == 1
    assert job["continuity_check_sentence_break_risk_count"] == 1
    assert job["continuity_check_recommendation"] == "review_sentence_boundary_continuity"


def test_old_jobs_are_loadable_with_defaults():
    job = Job.from_dict(dict(BASE_JOB_DATA))

    assert job.continuity_check_report == {}
    assert job.continuity_check_status is None
    assert job.continuity_check_issues == []
    assert job.continuity_check_issue_count == 0
    assert job.continuity_check_recommendation is None


def test_job_to_dict_contains_continuity_check_fields():
    job = Job.from_dict(dict(BASE_JOB_DATA))
    data = job.to_dict()

    expected_fields = [
        "continuity_check_report",
        "continuity_check_status",
        "continuity_check_issues",
        "continuity_check_issue_count",
        "continuity_check_blocking_issue_count",
        "continuity_check_sentence_break_risk_count",
        "continuity_check_context_jump_risk_count",
        "continuity_check_censor_context_risk_count",
        "continuity_check_timing_issue_count",
        "continuity_check_transition_conflict_count",
        "continuity_check_technical_issue_count",
        "continuity_check_protected_context_count",
        "continuity_check_recommendation",
    ]

    for field in expected_fields:
        assert field in data


def test_censor_context_risk_is_counted():
    job = {
        "transition_decision_decisions": [_transition_decision()],
        "cut_list_items": [_cut_list_item(action="REVIEW_TRIM")],
        "unified_edit_signals": [_signal("profanity_censor_sfx_required")],
    }

    report = run_continuity_check_for_job(job)

    assert report.censor_context_risk_count == 1
    assert report.blocking_issue_count >= 1


def test_blocking_issues_are_counted():
    job = {
        "transition_decision_decisions": [_transition_decision()],
        "unified_edit_signals": [_signal("transition_no_cut_protect")],
    }

    report = run_continuity_check_for_job(job)

    assert report.transition_conflict_count == 1
    assert report.blocking_issue_count == 1


def test_runner_does_not_crash_with_broken_inputs():
    job = {
        "transition_decision_decisions": [
            None,
            {"decision_id": "broken_no_times"},
            _transition_decision(),
        ],
    }

    report = run_continuity_check_for_job(job)

    assert report.status in {"ok", "completed_with_warnings"}
    assert report.issue_count >= 2


def test_apply_accepts_report_dict():
    job = {}
    report = run_continuity_check_for_job(
        {
            "transition_decision_decisions": [_transition_decision()],
            "unified_edit_signals": [_signal("sentence_boundary_protection")],
        }
    )

    apply_continuity_check_run_report_to_job(job, report.to_dict())

    assert job["continuity_check_status"] == "completed_with_warnings"
    assert job["continuity_check_issue_count"] == 1


def test_new_files_have_no_bom_and_end_with_newline():
    for file_path in NEW_FILES:
        raw = file_path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), file_path
        assert raw.endswith(b"\n"), file_path
