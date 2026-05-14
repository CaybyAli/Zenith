from core.render_plan_runner import run_render_plan_for_job
from core.render_plan_signal_adapter import build_render_plan_signals
from core.unified_edit_signal_registry import build_unified_edit_signal_result


def _job():
    return {
        "job_id": "job-render-plan-registry",
        "input_file": "D:/media/source.mp4",
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
                "start_seconds": 0.0,
                "end_seconds": 2.5,
                "duration_seconds": 2.5,
                "transition_intent": "hard_cut",
            }
        ],
    }


def test_render_plan_signal_adapter_emits_contract_and_planned_signals():
    job = _job()
    run_render_plan_for_job(job)

    signals = build_render_plan_signals(job)
    signal_types = {item["signal_type"] for item in signals}

    assert "render_plan_ready_with_warnings" in signal_types
    assert "render_plan_contract_ready" in signal_types
    assert "render_plan_segment_planned" in signal_types
    assert "render_plan_output_target_planned" in signal_types
    assert "render_plan_operation_intent" in signal_types

    for signal in signals:
        assert signal["source"] == "render_plan"
        assert signal["action_hint"] == "review_render_plan"
        assert signal["metadata"]["render_plan_only"] is True
        assert signal["metadata"]["dry_run_only"] is True
        assert signal["metadata"]["renderer_contract_only"] is True
        assert signal["metadata"]["media_unchanged"] is True


def test_unified_registry_collects_render_plan_signals():
    job = _job()
    run_render_plan_for_job(job)

    result = build_unified_edit_signal_result(job)
    data = result.to_dict()

    assert data["source_counts"].get("render_plan", 0) > 0
    assert any(signal["source"] == "render_plan" for signal in data["signals"])
