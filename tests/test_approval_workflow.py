from __future__ import annotations

import json
from pathlib import Path

from core.approval_store import read_job_approval, write_job_approval
from core.render_gate import RenderGateDecision, evaluate_render_gate


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _blocked_job(job_id: str = "job_explicit_approval") -> dict:
    return {
        "job_id": job_id,
        "channel_type": "gaming_main",
        "render_readiness_status": "render_readiness_blocked",
        "render_readiness_ready_for_next_render_stage": False,
        "render_readiness_blocking_count": 1,
        "render_readiness_blocking_reasons": ["timeline not approved"],
    }


def test_explicit_job_approval_overrides_blocked_gate(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ZENITH_RENDER_GATE_AUTO_APPROVE", "0")

    job = _blocked_job()
    approval_path = write_job_approval(
        job_id=job["job_id"],
        channel=job["channel_type"],
        approved_by="test",
    )

    result = evaluate_render_gate(job)

    assert approval_path.is_file()
    assert result.decision == RenderGateDecision.PASS
    assert result.reason == "explicitly_approved"
    assert result.detail["explicit_job_approval"] is True
    assert result.detail["explicit_approval"]["approved_by"] == "test"


def test_non_approved_job_still_blocks_when_auto_approve_disabled(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("ZENITH_RENDER_GATE_AUTO_APPROVE", "0")

    result = evaluate_render_gate(_blocked_job())

    assert result.decision == RenderGateDecision.BLOCKED
    assert result.reason == "readiness_not_ready"
    assert result.detail["explicit_job_approval"] is False


def test_approval_file_is_job_and_channel_scoped(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    write_job_approval(
        job_id="job_a",
        channel="gaming_main",
        approved_by="test",
    )

    approved = read_job_approval(
        {
            "job_id": "job_a",
            "channel_type": "gaming_main",
        }
    )
    wrong_job = read_job_approval(
        {
            "job_id": "job_b",
            "channel_type": "gaming_main",
        }
    )
    wrong_channel = read_job_approval(
        {
            "job_id": "job_a",
            "channel_type": "gaming_uncut",
        }
    )

    assert approved is not None
    assert approved["approved"] is True
    assert wrong_job is None
    assert wrong_channel is None


def test_approval_file_payload_shape(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    path = write_job_approval(
        job_id="job_shape",
        channel="gaming_main",
        approved_by="test",
    )
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["approved"] is True
    assert payload["job_id"] == "job_shape"
    assert payload["channel"] == "gaming_main"
    assert payload["approved_by"] == "test"
    assert payload["approved_at"].endswith("Z")


def test_pipeline_runner_source_contains_approval_cli_hooks() -> None:
    source = (PROJECT_ROOT / "pipeline_runner.py").read_text(encoding="utf-8")

    assert "argparse" in source
    assert "--approve" in source
    assert "--list-blocked" in source
    assert "approved_job_id" in source
    assert "write_job_approval" in source
    assert "APPROVE" in source
