from __future__ import annotations

from core.render_command_blueprint_builder import build_render_command_blueprint


FORBIDDEN_OUTPUT_KEYS = {
    "command",
    "raw_command",
    "shell_command",
    "command_line",
    "executable_command",
    "ffmpeg_command",
    "argv",
    "args",
    "subprocess",
    "os.system",
}


def _ready_job() -> dict:
    intents = [
        {
            "intent_id": "intent_trim_1",
            "intent_type": "trim_intent",
            "description": "Trim planned segment.",
            "source_segment_id": "src_1",
            "target_segment_id": "seg_1",
            "can_execute_now": False,
            "requires_later_renderer": True,
            "metadata": {"planned_only": True},
        },
        {
            "intent_id": "intent_transition_1",
            "intent_type": "transition_intent",
            "description": "Apply planned transition.",
            "source_segment_id": "src_1",
            "target_segment_id": "seg_1",
            "can_execute_now": False,
            "requires_later_renderer": True,
        },
        {
            "intent_id": "intent_censor_1",
            "intent_type": "censor_sfx_intent",
            "description": "Apply planned censor sound.",
            "source_segment_id": "src_1",
            "target_segment_id": "seg_1",
            "can_execute_now": False,
            "requires_later_renderer": True,
        },
        {
            "intent_id": "intent_audio_1",
            "intent_type": "audio_mix_intent",
            "description": "Apply planned audio mix.",
            "source_segment_id": "src_1",
            "target_segment_id": "seg_1",
            "can_execute_now": False,
            "requires_later_renderer": True,
        },
        {
            "intent_id": "intent_subtitle_1",
            "intent_type": "subtitle_intent",
            "description": "Apply planned subtitles.",
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
        "job_id": "job_blueprint_builder_smoke",
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


def _walk_dicts(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def test_builder_blocks_when_render_plan_missing():
    report = build_render_command_blueprint({"job_id": "missing_plan"})

    assert report["status"] == "render_blueprint_blocked"
    assert "render_blueprint_render_plan_missing" in report["blocking_reasons"]
    assert report["ready_for_renderer_implementation"] is False
    assert report["can_render"] is False


def test_builder_blocks_when_render_plan_not_ready():
    job = _ready_job()
    job["render_plan_status"] = "render_plan_blocked"
    job["render_plan_report"]["status"] = "render_plan_blocked"

    report = build_render_command_blueprint(job)

    assert report["status"] == "render_blueprint_blocked"
    assert "render_blueprint_render_plan_not_ready" in report["blocking_reasons"]


def test_builder_blocks_when_render_plan_has_blocking_reasons():
    job = _ready_job()
    job["render_plan_blocking_reasons"] = ["render_plan_no_timeline_items"]

    report = build_render_command_blueprint(job)

    assert report["status"] == "render_blueprint_blocked"
    assert "render_blueprint_plan_has_blocking_reasons" in report["blocking_reasons"]


def test_builder_blocks_when_render_plan_danger_flags_are_true():
    danger_flags = [
        "render_plan_can_execute_plan",
        "render_plan_can_render",
        "render_plan_can_run_ffmpeg",
        "render_plan_can_write_media",
        "render_plan_can_apply_timeline",
    ]

    for flag in danger_flags:
        job = _ready_job()
        job[flag] = True

        report = build_render_command_blueprint(job)

        assert report["status"] == "render_blueprint_blocked"
        assert f"render_blueprint_dangerous_plan_flag:{flag}" in report["blocking_reasons"]


def test_builder_creates_blueprint_steps_and_counts_from_operation_intents():
    report = build_render_command_blueprint(_ready_job())

    assert report["status"] == "render_blueprint_ready"
    assert report["total_steps"] == 7
    assert report["trim_step_count"] == 1
    assert report["concat_step_count"] == 1
    assert report["transition_step_count"] == 1
    assert report["audio_mix_step_count"] == 1
    assert report["censor_sfx_step_count"] == 1
    assert report["subtitle_step_count"] == 1
    assert report["encode_step_count"] == 1

    step_types = {step["step_type"] for step in report["blueprint_steps"]}
    assert step_types == {
        "trim",
        "concat",
        "transition",
        "audio_mix",
        "censor_sfx",
        "subtitle",
        "encode",
    }

    for step in report["blueprint_steps"]:
        assert step["can_execute_now"] is False
        assert step["requires_renderer_implementation"] is True
        assert step["filter_intents"]
        assert step["planned_inputs"]
        assert step["planned_outputs"]


def test_contract_safety_flags_stay_non_executable():
    report = build_render_command_blueprint(_ready_job())

    assert report["dry_run_only"] is True
    assert report["non_executable"] is True
    assert report["ready_for_renderer_implementation"] is True
    assert report["can_execute_contract"] is False
    assert report["can_render"] is False
    assert report["can_run_ffmpeg"] is False
    assert report["can_spawn_process"] is False
    assert report["can_write_media"] is False


def test_output_contains_no_executable_command_keys():
    report = build_render_command_blueprint(_ready_job())

    for mapping in _walk_dicts(report):
        assert FORBIDDEN_OUTPUT_KEYS.isdisjoint(mapping.keys())

