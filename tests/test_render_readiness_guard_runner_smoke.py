from types import SimpleNamespace

from core.render_readiness_guard_runner import run_render_readiness_guard
from models.job import Job


def _job(**overrides):
    data = {
        "job_id": "runner-render-readiness-job",
        "status": "routed",
        "review_timeline_plan": {"status": "ready"},
        "review_timeline_plan_report": {"status": "ready"},
        "review_timeline_plan_status": "ready",
        "review_timeline_plan_items": [
            {
                "item_id": "clip-1",
                "start_seconds": 0.0,
                "end_seconds": 5.0,
                "duration_seconds": 5.0,
            }
        ],
        "timeline_approval_gate": {
            "status": "approved",
            "approval_status": "approved",
            "approved_by": "human_reviewer",
        },
        "timeline_approval_gate_report": {
            "status": "approved",
            "approval_status": "approved",
            "approved_by": "human_reviewer",
        },
        "timeline_approval_status": "approved",
        "timeline_approved_by": "human_reviewer",
        "timeline_can_render": False,
        "timeline_safety_validator": {"status": "safe"},
        "timeline_safety_validator_report": {"status": "safe"},
        "timeline_safety_validation_status": "safe",
        "timeline_is_safe_for_future_execution": True,
        "timeline_is_safe_for_render": False,
        "timeline_safety_blocking_errors": [],
        "review_timeline_dashboard_package": {"status": "ready"},
        "review_timeline_dashboard_package_report": {"status": "ready"},
        "review_timeline_dashboard_package_status": "ready",
        "review_timeline_dashboard_can_render": False,
        "review_timeline_dashboard_blocking_errors": [],
        "final_quality_validation_report": {
            "status": "final_quality_ready",
            "blocking_count": 0,
            "blocking_reasons": [],
            "overall_quality_score": 0.90,
        },
        "final_quality_validation_status": "final_quality_ready",
        "final_quality_overall_score": 0.90,
        "final_quality_blocking_count": 0,
        "final_quality_can_render": False,
        "final_quality_can_execute_timeline": False,
        "final_quality_blocking_reasons": [],
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_render_readiness_runner_writes_job_fields():
    job = _job()

    report = run_render_readiness_guard(job)

    assert report["status"] == "render_readiness_ready"
    assert job.render_readiness_status == "render_readiness_ready"
    assert job.render_readiness_guard_report["status"] == "render_readiness_ready"
    assert job.render_readiness_guard["status"] == "render_readiness_ready"
    assert isinstance(job.render_readiness_checks, list)
    assert job.render_readiness_total_checks >= 13
    assert job.render_readiness_passed_count >= 10
    assert job.render_readiness_warning_count == 0
    assert job.render_readiness_blocking_count == 0
    assert job.render_readiness_review_required is False
    assert job.render_readiness_ready_for_next_render_stage is True
    assert job.render_readiness_can_start_render_pipeline is True
    assert job.render_readiness_recommendation == "Ready for the next render stage. 2B-45 still does not render."


def test_render_readiness_runner_forces_all_media_execution_flags_false():
    job = _job(
        timeline_can_render=True,
        story_can_trim=True,
        final_quality_can_execute_timeline=True,
    )

    report = run_render_readiness_guard(job)

    assert report["status"] == "render_readiness_blocked"
    assert job.render_readiness_can_render is False
    assert job.render_readiness_can_run_ffmpeg is False
    assert job.render_readiness_can_execute_media_operations is False
    assert job.render_readiness_can_apply_timeline is False
    assert job.render_readiness_can_modify_media is False
    assert report["can_render"] is False
    assert report["can_run_ffmpeg"] is False
    assert report["can_execute_media_operations"] is False
    assert report["can_apply_timeline"] is False
    assert report["can_modify_media"] is False


def test_job_from_dict_loads_render_readiness_fields_and_keeps_media_execution_false():
    loaded = Job.from_dict(
        {
            "job_id": "job-from-dict-render-readiness",
            "job_type": "gaming",
            "channel_type": "gaming_main",
            "target_format": "short",
            "target_platforms": ["youtube"],
            "status": "routed",
            "mode": "normal",
            "autopublish_class": "manual_only",
            "confidence_score": 0.0,
            "validator_status": "not_validated",
            "render_readiness_guard_report": {
                "status": "render_readiness_ready_with_warnings",
                "checks": [{"check_id": "human_approval_chain_present"}],
            },
            "render_readiness_guard": {
                "status": "render_readiness_ready_with_warnings",
            },
            "render_readiness_status": "render_readiness_ready_with_warnings",
            "render_readiness_checks": [{"check_id": "human_approval_chain_present"}],
            "render_readiness_total_checks": 13,
            "render_readiness_passed_count": 12,
            "render_readiness_warning_count": 1,
            "render_readiness_blocking_count": 0,
            "render_readiness_review_required": True,
            "render_readiness_ready_for_next_render_stage": True,
            "render_readiness_can_start_render_pipeline": True,
            "render_readiness_can_render": True,
            "render_readiness_can_run_ffmpeg": True,
            "render_readiness_can_execute_media_operations": True,
            "render_readiness_can_apply_timeline": True,
            "render_readiness_can_modify_media": True,
            "render_readiness_blocking_reasons": [],
            "render_readiness_warnings": ["approval unclear"],
            "render_readiness_recommendation": "review_render_readiness",
        }
    )

    assert loaded.render_readiness_status == "render_readiness_ready_with_warnings"
    assert loaded.render_readiness_guard_report["status"] == "render_readiness_ready_with_warnings"
    assert loaded.render_readiness_guard["status"] == "render_readiness_ready_with_warnings"
    assert loaded.render_readiness_checks == [{"check_id": "human_approval_chain_present"}]
    assert loaded.render_readiness_total_checks == 13
    assert loaded.render_readiness_passed_count == 12
    assert loaded.render_readiness_warning_count == 1
    assert loaded.render_readiness_blocking_count == 0
    assert loaded.render_readiness_review_required is True
    assert loaded.render_readiness_ready_for_next_render_stage is True
    assert loaded.render_readiness_can_start_render_pipeline is True
    assert loaded.render_readiness_can_render is False
    assert loaded.render_readiness_can_run_ffmpeg is False
    assert loaded.render_readiness_can_execute_media_operations is False
    assert loaded.render_readiness_can_apply_timeline is False
    assert loaded.render_readiness_can_modify_media is False
    assert loaded.render_readiness_warnings == ["approval unclear"]
    assert loaded.render_readiness_recommendation == "review_render_readiness"
