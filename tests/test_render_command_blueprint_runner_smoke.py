from __future__ import annotations

from models.job import Job
from core.render_command_blueprint_runner import run_render_command_blueprint_for_job


def _ready_job_dict() -> dict:
    intents = [
        {
            "intent_id": "intent_trim_1",
            "intent_type": "trim_intent",
            "description": "Trim planned segment.",
            "source_segment_id": "src_1",
            "target_segment_id": "seg_1",
            "can_execute_now": False,
            "requires_later_renderer": True,
        },
        {
            "intent_id": "intent_concat_1",
            "intent_type": "concat_intent",
            "description": "Join planned segments.",
            "can_execute_now": False,
            "requires_later_renderer": True,
        },
        {
            "intent_id": "intent_encode_1",
            "intent_type": "output_encode_intent",
            "description": "Encode planned output.",
            "target_segment_id": "output_target_main",
            "can_execute_now": False,
            "requires_later_renderer": True,
        },
    ]
    return {
        "job_id": "job_blueprint_runner_smoke",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "longform",
        "target_platforms": ["youtube"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
        "render_plan_status": "render_plan_ready",
        "render_plan_dry_run_only": True,
        "render_plan_ready_for_renderer_contract": True,
        "render_plan_can_execute_plan": False,
        "render_plan_can_render": False,
        "render_plan_can_run_ffmpeg": False,
        "render_plan_can_write_media": False,
        "render_plan_can_apply_timeline": False,
        "render_plan_blocking_reasons": [],
        "render_plan_warnings": [],
        "render_plan_operation_intents": intents,
        "render_plan_report": {
            "status": "render_plan_ready",
            "dry_run_only": True,
            "ready_for_renderer_contract": True,
            "can_execute_plan": False,
            "can_render": False,
            "can_run_ffmpeg": False,
            "can_write_media": False,
            "can_apply_timeline": False,
            "blocking_reasons": [],
            "warnings": [],
            "operation_intents": intents,
        },
    }


def test_runner_writes_render_blueprint_fields_to_dict_job():
    job = _ready_job_dict()

    report = run_render_command_blueprint_for_job(job)

    assert job["render_command_blueprint_report"] == report
    assert job["render_command_blueprint"] == report
    assert job["render_blueprint_status"] == "render_blueprint_ready"
    assert job["render_blueprint_total_steps"] == 3
    assert job["render_blueprint_trim_step_count"] == 1
    assert job["render_blueprint_concat_step_count"] == 1
    assert job["render_blueprint_encode_step_count"] == 1
    assert job["render_blueprint_dry_run_only"] is True
    assert job["render_blueprint_non_executable"] is True
    assert job["render_blueprint_ready_for_renderer_implementation"] is True
    assert job["render_blueprint_can_execute_contract"] is False
    assert job["render_blueprint_can_render"] is False
    assert job["render_blueprint_can_run_ffmpeg"] is False
    assert job["render_blueprint_can_spawn_process"] is False
    assert job["render_blueprint_can_write_media"] is False


def test_job_from_dict_loads_render_blueprint_fields_and_keeps_danger_flags_false():
    data = _ready_job_dict()
    data.update(
        {
            "render_command_blueprint_report": {"status": "render_blueprint_ready"},
            "render_command_blueprint": {"status": "render_blueprint_ready"},
            "render_blueprint_status": "render_blueprint_ready",
            "render_blueprint_steps": [{"step_id": "s1", "step_type": "trim"}],
            "render_blueprint_total_steps": 1,
            "render_blueprint_trim_step_count": 1,
            "render_blueprint_dry_run_only": True,
            "render_blueprint_non_executable": True,
            "render_blueprint_ready_for_renderer_implementation": True,
            "render_blueprint_can_execute_contract": True,
            "render_blueprint_can_render": True,
            "render_blueprint_can_run_ffmpeg": True,
            "render_blueprint_can_spawn_process": True,
            "render_blueprint_can_write_media": True,
            "render_blueprint_blocking_reasons": [],
            "render_blueprint_warnings": ["warning"],
            "render_blueprint_recommendation": "review_render_command_blueprint",
        }
    )

    job = Job.from_dict(data)

    assert job.render_command_blueprint_report == {"status": "render_blueprint_ready"}
    assert job.render_blueprint_status == "render_blueprint_ready"
    assert job.render_blueprint_total_steps == 1
    assert job.render_blueprint_trim_step_count == 1
    assert job.render_blueprint_dry_run_only is True
    assert job.render_blueprint_non_executable is True
    assert job.render_blueprint_ready_for_renderer_implementation is True
    assert job.render_blueprint_can_execute_contract is False
    assert job.render_blueprint_can_render is False
    assert job.render_blueprint_can_run_ffmpeg is False
    assert job.render_blueprint_can_spawn_process is False
    assert job.render_blueprint_can_write_media is False
    assert job.render_blueprint_warnings == ["warning"]

