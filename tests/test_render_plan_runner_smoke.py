from core.render_plan_runner import run_render_plan_for_job
from models.job import Job


def _job_data():
    return {
        "job_id": "job-render-plan-runner",
        "raw_video_path": "D:/media/source.mp4",
        "render_readiness_status": "render_readiness_ready",
        "render_readiness_ready_for_next_render_stage": True,
        "render_readiness_can_start_render_pipeline": True,
        "render_readiness_blocking_count": 0,
        "render_readiness_blocking_reasons": [],
        "render_readiness_warnings": [],
        "render_readiness_guard_report": {
            "status": "render_readiness_ready",
            "ready_for_next_render_stage": True,
            "can_start_render_pipeline": True,
            "blocking_count": 0,
            "blocking_reasons": [],
            "warnings": [],
        },
        "review_timeline_plan_items": [
            {
                "item_id": "item-1",
                "segment_id": "seg-1",
                "start_seconds": 1.0,
                "end_seconds": 4.0,
                "duration_seconds": 3.0,
            }
        ],
    }


def test_runner_writes_render_plan_fields_to_dict_job():
    job = _job_data()

    report = run_render_plan_for_job(job)

    assert job["render_plan_report"] == report
    assert job["render_plan"] == report
    assert job["render_plan_status"] == report["status"]
    assert job["render_plan_sources"] == report["sources"]
    assert job["render_plan_segments"] == report["segments"]
    assert job["render_plan_output_targets"] == report["output_targets"]
    assert job["render_plan_operation_intents"] == report["operation_intents"]
    assert job["render_plan_total_segments"] == 1
    assert job["render_plan_total_duration_seconds"] == 3.0
    assert job["render_plan_estimated_output_duration_seconds"] == 3.0
    assert job["render_plan_dry_run_only"] is True
    assert job["render_plan_ready_for_renderer_contract"] is True
    assert job["render_plan_can_execute_plan"] is False
    assert job["render_plan_can_render"] is False
    assert job["render_plan_can_run_ffmpeg"] is False
    assert job["render_plan_can_write_media"] is False
    assert job["render_plan_can_apply_timeline"] is False


def test_job_from_dict_loads_render_plan_fields_and_forces_safe_false_flags():
    data = _job_data()
    data.update(
        {
            "render_plan_report": {"status": "render_plan_ready"},
            "render_plan": {"status": "render_plan_ready"},
            "render_plan_status": "render_plan_ready",
            "render_plan_sources": [{"source_id": "source_main"}],
            "render_plan_segments": [{"segment_id": "seg-1"}],
            "render_plan_output_targets": [{"target_id": "target"}],
            "render_plan_operation_intents": [{"intent_id": "intent"}],
            "render_plan_total_segments": 1,
            "render_plan_total_duration_seconds": 3.0,
            "render_plan_estimated_output_duration_seconds": 3.0,
            "render_plan_dry_run_only": True,
            "render_plan_ready_for_renderer_contract": True,
            "render_plan_can_execute_plan": True,
            "render_plan_can_render": True,
            "render_plan_can_run_ffmpeg": True,
            "render_plan_can_write_media": True,
            "render_plan_can_apply_timeline": True,
            "render_plan_blocking_reasons": [],
            "render_plan_warnings": ["warning"],
            "render_plan_recommendation": "review_render_plan",
        }
    )

    job = Job.from_dict(data)

    assert job.render_plan_report == {"status": "render_plan_ready"}
    assert job.render_plan == {"status": "render_plan_ready"}
    assert job.render_plan_status == "render_plan_ready"
    assert job.render_plan_sources == [{"source_id": "source_main"}]
    assert job.render_plan_segments == [{"segment_id": "seg-1"}]
    assert job.render_plan_output_targets == [{"target_id": "target"}]
    assert job.render_plan_operation_intents == [{"intent_id": "intent"}]
    assert job.render_plan_total_segments == 1
    assert job.render_plan_total_duration_seconds == 3.0
    assert job.render_plan_estimated_output_duration_seconds == 3.0
    assert job.render_plan_dry_run_only is True
    assert job.render_plan_ready_for_renderer_contract is True
    assert job.render_plan_can_execute_plan is False
    assert job.render_plan_can_render is False
    assert job.render_plan_can_run_ffmpeg is False
    assert job.render_plan_can_write_media is False
    assert job.render_plan_can_apply_timeline is False
    assert job.render_plan_warnings == ["warning"]
    assert job.render_plan_recommendation == "review_render_plan"
