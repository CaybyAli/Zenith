from __future__ import annotations

from core.render_gate import RenderGateDecision, evaluate_render_gate


def _ready_job() -> dict:
    return {
        "render_readiness_status": "render_readiness_ready",
        "render_readiness_ready_for_next_render_stage": True,
        "render_readiness_blocking_count": 0,
        "render_readiness_blocking_reasons": [],
        "render_plan_status": "render_plan_ready",
        "render_plan_ready_for_renderer_contract": True,
        "render_plan_blocking_reasons": [],
        "render_asset_manifest_status": "render_asset_manifest_ready",
        "render_asset_unsafe_path_count": 0,
        "render_asset_blocking_reasons": [],
        "render_execution_permission_status": "render_execution_permission_ready",
        "render_execution_human_approved": True,
        "render_execution_ready_for_real_render_stage": True,
        "render_execution_blocking_reasons": [],
        "render_verification_contract_status": "render_verification_contract_ready",
        "render_verification_blocked_check_count": 0,
        "render_verification_can_verify_smoke_output": True,
        "render_verification_blocking_reasons": [],
    }


def test_render_gate_overrides_readiness_block_when_auto_approve_active(monkeypatch) -> None:
    monkeypatch.setenv("ZENITH_RENDER_GATE_AUTO_APPROVE", "1")
    job = _ready_job()
    job["render_readiness_status"] = "render_readiness_blocked"
    job["render_readiness_blocking_reasons"] = ["timeline not approved"]

    result = evaluate_render_gate(job)

    assert result.decision == RenderGateDecision.PASS
    assert result.reason == "auto_approve_override"
    assert result.detail["would_block_reason"] == "readiness_not_ready"
    assert result.detail["would_block_detail"]["render_readiness_blocking_reasons"] == [
        "timeline not approved"
    ]


def test_render_gate_blocks_readiness_when_auto_approve_disabled(monkeypatch) -> None:
    monkeypatch.setenv("ZENITH_RENDER_GATE_AUTO_APPROVE", "0")
    job = _ready_job()
    job["render_readiness_status"] = "render_readiness_blocked"

    result = evaluate_render_gate(job)

    assert result.decision == RenderGateDecision.BLOCKED
    assert result.reason == "readiness_not_ready"


def test_render_gate_passes_all_ready_with_or_without_auto_approve(monkeypatch) -> None:
    for value in ("0", "1"):
        monkeypatch.setenv("ZENITH_RENDER_GATE_AUTO_APPROVE", value)

        result = evaluate_render_gate(_ready_job())

        assert result.decision == RenderGateDecision.PASS
        assert result.reason == "all_gates_passed"
        assert "would_block_reason" not in result.detail


def test_render_gate_overrides_verification_block_when_auto_approve_active(monkeypatch) -> None:
    monkeypatch.setenv("ZENITH_RENDER_GATE_AUTO_APPROVE", "1")
    job = _ready_job()
    job["render_verification_contract_status"] = "render_verification_failed"

    result = evaluate_render_gate(job)

    assert result.decision == RenderGateDecision.PASS
    assert result.reason == "auto_approve_override"
    assert result.detail["would_block_reason"] == "verification_not_ready"
