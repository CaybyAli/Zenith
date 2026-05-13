from pathlib import Path

from core.transition_decision_runner import (
    apply_transition_decision_run_report_to_job,
    run_transition_decision_for_job,
)
from models.job import Job
from models.transition_decision import TransitionDecision, TransitionDecisionPlan
from models.transition_decision_run import TransitionDecisionRunReport


ROOT = Path(__file__).resolve().parents[1]

NEW_FILES = [
    ROOT / "models" / "transition_decision_run.py",
    ROOT / "core" / "transition_decision_runner.py",
    ROOT / "tests" / "test_transition_decision_runner_smoke.py",
]

BASE_JOB_DATA = {
    "job_id": "job_transition_decision_old",
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


def _clip_duration_recommendation(
    recommendation_id: str,
    source_item_id: str,
    start_seconds: float,
    end_seconds: float,
    duration_status: str = "duration_ok",
):
    return {
        "recommendation_id": recommendation_id,
        "source_item_id": source_item_id,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "duration_status": duration_status,
        "confidence": 0.8,
    }


def _cut_list_item(
    item_id: str,
    start_seconds: float,
    end_seconds: float,
    proposed_action: str = "KEEP",
):
    return {
        "item_id": item_id,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "proposed_action": proposed_action,
        "action_confidence": 0.8,
    }


def _signal(signal_id: str, signal_type: str, center_seconds: float):
    return {
        "signal_id": signal_id,
        "signal_type": signal_type,
        "center_seconds": center_seconds,
        "confidence": 0.9,
    }


def test_transition_decision_run_report_roundtrip():
    decision = TransitionDecision(
        decision_id="decision_1",
        source_item_id="item_1",
        transition_type="hard_cut_review",
        transition_confidence=0.8,
    )
    plan = TransitionDecisionPlan(
        status="ok",
        decisions=[decision],
        decision_count=1,
        hard_cut_review_count=1,
        recommendation="transition_decision_review_plan_ready",
    )
    report = TransitionDecisionRunReport(
        status="ok",
        transition_decision_plan=plan,
        decisions=[decision],
        decision_count=1,
        hard_cut_review_count=1,
        recommendation="transition_decision_review_plan_ready",
        metadata={"source": "test"},
    )

    loaded = TransitionDecisionRunReport.from_dict(report.to_dict())

    assert loaded.to_dict() == report.to_dict()


def test_runner_uses_job_clip_duration_recommendations():
    job = {
        "clip_duration_recommendations": [
            _clip_duration_recommendation("rec_1", "item_1", 0.0, 4.0),
        ],
        "unified_edit_signals": [
            _signal("scene_1", "scene_hard_cut_point", 2.0),
        ],
    }

    report = run_transition_decision_for_job(job)

    assert report.status == "ok"
    assert report.decision_count == 1
    assert report.hard_cut_review_count == 1
    assert report.decisions[0].transition_type == "hard_cut_review"


def test_runner_uses_fallback_job_cut_list_items():
    job = {
        "cut_list_items": [
            _cut_list_item("item_1", 0.0, 4.0, "KEEP"),
        ],
        "unified_edit_signals": [
            _signal("scene_1", "scene_hard_cut_point", 2.0),
        ],
    }

    report = run_transition_decision_for_job(job)

    assert report.status == "ok"
    assert report.decision_count == 1
    assert report.hard_cut_review_count == 1


def test_runner_uses_optional_unified_edit_signals():
    job = {
        "clip_duration_recommendations": [
            _clip_duration_recommendation("rec_1", "item_1", 10.0, 14.0),
        ],
        "unified_edit_signals": [
            _signal("sentence_1", "sentence_boundary_protection", 12.0),
        ],
    }

    report = run_transition_decision_for_job(job)

    assert report.no_cut_protect_count == 1
    assert report.decisions[0].transition_type == "no_cut_protect"


def test_runner_skips_when_no_clip_duration_recommendations_or_cut_list_items_exist():
    report = run_transition_decision_for_job({})

    assert report.status == "skipped_no_clip_duration_recommendations"
    assert report.decision_count == 0
    assert report.recommendation == "transition_decision_skipped_no_inputs"


def test_apply_writes_transition_decision_fields_to_dict_job():
    job = {
        "clip_duration_recommendations": [
            _clip_duration_recommendation("rec_1", "item_1", 0.0, 4.0),
        ],
        "unified_edit_signals": [
            _signal("scene_1", "scene_hard_cut_point", 2.0),
        ],
    }
    report = run_transition_decision_for_job(job)

    apply_transition_decision_run_report_to_job(job, report)

    assert job["transition_decision_report"]["source"] == "transition_decision"
    assert job["transition_decision_status"] == "ok"
    assert len(job["transition_decision_decisions"]) == 1
    assert job["transition_decision_count"] == 1
    assert job["transition_decision_hard_cut_review_count"] == 1
    assert job["transition_decision_recommendation"] == "transition_decision_review_plan_ready"


def test_old_jobs_are_loadable_with_defaults():
    job = Job.from_dict(dict(BASE_JOB_DATA))

    assert job.transition_decision_report == {}
    assert job.transition_decision_status is None
    assert job.transition_decision_decisions == []
    assert job.transition_decision_count == 0
    assert job.transition_decision_recommendation is None


def test_job_to_dict_contains_transition_decision_fields():
    job = Job.from_dict(dict(BASE_JOB_DATA))
    data = job.to_dict()

    expected_fields = [
        "transition_decision_report",
        "transition_decision_status",
        "transition_decision_decisions",
        "transition_decision_count",
        "transition_decision_hard_cut_review_count",
        "transition_decision_j_cut_review_count",
        "transition_decision_l_cut_review_count",
        "transition_decision_quick_fade_review_count",
        "transition_decision_no_cut_protect_count",
        "transition_decision_censor_safe_keep_count",
        "transition_decision_technical_review_count",
        "transition_decision_unknown_review_count",
        "transition_decision_recommendation",
    ]

    for field in expected_fields:
        assert field in data


def test_censor_safe_keep_is_counted():
    job = {
        "clip_duration_recommendations": [
            _clip_duration_recommendation(
                "rec_1",
                "item_1",
                20.0,
                24.0,
                "censor_keep_duration",
            ),
        ],
    }

    report = run_transition_decision_for_job(job)

    assert report.censor_safe_keep_count == 1
    assert report.decisions[0].transition_type == "censor_safe_keep"


def test_no_cut_protect_is_counted():
    job = {
        "clip_duration_recommendations": [
            _clip_duration_recommendation(
                "rec_1",
                "item_1",
                30.0,
                34.0,
                "protect_duration",
            ),
        ],
    }

    report = run_transition_decision_for_job(job)

    assert report.no_cut_protect_count == 1
    assert report.decisions[0].transition_type == "no_cut_protect"


def test_runner_does_not_crash_with_broken_inputs():
    job = {
        "clip_duration_recommendations": [
            None,
            {"recommendation_id": "broken_no_times"},
            _clip_duration_recommendation("rec_1", "item_1", 0.0, 4.0),
        ],
    }

    report = run_transition_decision_for_job(job)

    assert report.decision_count == 3
    assert report.status in {"ok", "completed_with_warnings"}


def test_apply_accepts_report_dict():
    job = {}
    report = run_transition_decision_for_job(
        {
            "clip_duration_recommendations": [
                _clip_duration_recommendation("rec_1", "item_1", 0.0, 4.0),
            ],
            "unified_edit_signals": [
                _signal("scene_1", "scene_hard_cut_point", 2.0),
            ],
        }
    )

    apply_transition_decision_run_report_to_job(job, report.to_dict())

    assert job["transition_decision_status"] == "ok"
    assert job["transition_decision_count"] == 1


def test_new_files_have_no_bom_and_end_with_newline():
    for file_path in NEW_FILES:
        raw = file_path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), file_path
        assert raw.endswith(b"\n"), file_path
