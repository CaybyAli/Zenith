from types import SimpleNamespace

from core.render_gate import RenderGateDecision, evaluate_render_gate


def _base_render_ready_job(**overrides):
    values = {
        "render_readiness_status": "ready",
        "render_readiness_ready_for_next_render_stage": True,
        "render_readiness_blocking_count": 0,
        "render_readiness_blocking_reasons": [],
        "render_plan_status": "ready",
        "render_plan_ready_for_renderer_contract": True,
        "render_plan_blocking_reasons": [],
        "render_asset_manifest_status": "ready",
        "render_asset_unsafe_path_count": 0,
        "render_asset_blocking_reasons": [],
        "render_execution_permission_status": "ready",
        "render_execution_ready_for_real_render_stage": True,
        "render_execution_blocking_reasons": [],
        "render_execution_human_approved": True,
        "render_verification_contract_status": "ready",
        "render_verification_blocked_check_count": 0,
        "render_verification_blocking_reasons": [],
        "render_verification_can_verify_smoke_output": True,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_final_quality_allows_render_when_render_and_execute_are_true(monkeypatch):
    monkeypatch.setenv("ZENITH_RENDER_GATE_AUTO_APPROVE", "0")
    monkeypatch.setattr("core.render_gate.read_job_approval", lambda job: None)

    job = _base_render_ready_job(
        final_quality_status="final_quality_ready",
        final_quality_can_render=True,
        final_quality_can_execute_timeline=True,
        final_quality_blocking_count=0,
        final_quality_blocking_reasons=[],
        final_quality_overall_score=0.92,
    )

    result = evaluate_render_gate(job)

    assert result.decision == RenderGateDecision.PASS
    assert result.reason == "all_gates_passed"
    assert result.detail["final_quality_can_render"] is True
    assert result.detail["final_quality_can_execute_timeline"] is True


def test_final_quality_blocks_when_can_render_false(monkeypatch):
    monkeypatch.setenv("ZENITH_RENDER_GATE_AUTO_APPROVE", "0")
    monkeypatch.setattr("core.render_gate.read_job_approval", lambda job: None)

    job = _base_render_ready_job(
        final_quality_status="final_quality_ready",
        final_quality_can_render=False,
        final_quality_can_execute_timeline=True,
        final_quality_blocking_count=0,
        final_quality_blocking_reasons=[],
    )

    result = evaluate_render_gate(job)

    assert result.decision == RenderGateDecision.BLOCKED
    assert result.reason == "final_quality_not_renderable"
    assert result.detail["would_block_stage"] == "final_quality"


def test_final_quality_blocks_when_can_execute_timeline_false(monkeypatch):
    monkeypatch.setenv("ZENITH_RENDER_GATE_AUTO_APPROVE", "0")
    monkeypatch.setattr("core.render_gate.read_job_approval", lambda job: None)

    job = _base_render_ready_job(
        final_quality_status="final_quality_ready",
        final_quality_can_render=True,
        final_quality_can_execute_timeline=False,
        final_quality_blocking_count=0,
        final_quality_blocking_reasons=[],
    )

    result = evaluate_render_gate(job)

    assert result.decision == RenderGateDecision.BLOCKED
    assert result.reason == "final_quality_not_renderable"
    assert result.detail["would_block_detail"]["final_quality_can_execute_timeline"] is False


def test_final_quality_blocks_when_blocking_count_positive(monkeypatch):
    monkeypatch.setenv("ZENITH_RENDER_GATE_AUTO_APPROVE", "0")
    monkeypatch.setattr("core.render_gate.read_job_approval", lambda job: None)

    job = _base_render_ready_job(
        final_quality_status="final_quality_blocked",
        final_quality_can_render=True,
        final_quality_can_execute_timeline=True,
        final_quality_blocking_count=1,
        final_quality_blocking_reasons=["story_quality_blocked"],
    )

    result = evaluate_render_gate(job)

    assert result.decision == RenderGateDecision.BLOCKED
    assert result.reason == "final_quality_not_renderable"
    assert result.detail["final_quality_blocking_count"] == 1


def test_render_gate_without_final_quality_data_keeps_existing_pass_behavior(monkeypatch):
    monkeypatch.setenv("ZENITH_RENDER_GATE_AUTO_APPROVE", "0")
    monkeypatch.setattr("core.render_gate.read_job_approval", lambda job: None)

    job = _base_render_ready_job()

    result = evaluate_render_gate(job)

    assert result.decision == RenderGateDecision.PASS
    assert result.reason == "all_gates_passed"
    assert "final_quality_can_render" not in result.detail
