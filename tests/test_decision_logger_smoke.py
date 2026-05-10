from __future__ import annotations

import json
from types import SimpleNamespace

from core.decision_logger import (
    build_decision_event,
    log_decision,
    write_decision_event,
)


def _fake_job():
    return SimpleNamespace(
        job_id="job_decision_logger_smoke",
        profile_id="gaming_main",
        quality_mode="pro",
        status="analyzing",
    )


def test_build_decision_event_contains_required_fields():
    job = _fake_job()

    event = build_decision_event(
        job=job,
        phase="profile",
        module="gaming_pipeline",
        event_type="PROFILE_LOADED",
        action="load_json_profile",
        reason="profile_manager_loaded_profile",
        score=0.95,
        details={"profile_snapshot_path": "exports/test/profile_snapshot.json"},
    )

    required_fields = {
        "timestamp",
        "job_id",
        "phase",
        "module",
        "event_type",
        "action",
        "status",
        "reason",
        "score",
        "profile_id",
        "quality_mode",
        "job_status",
        "details",
    }

    assert required_fields.issubset(event.keys())
    assert event["job_id"] == "job_decision_logger_smoke"
    assert event["profile_id"] == "gaming_main"
    assert event["quality_mode"] == "pro"
    assert event["job_status"] == "analyzing"
    assert event["details"]["profile_snapshot_path"] == "exports/test/profile_snapshot.json"


def test_write_decision_event_writes_human_log_and_jsonl(tmp_path):
    job = _fake_job()
    event = build_decision_event(
        job=job,
        phase="analysis",
        module="gaming_pipeline",
        event_type="ANALYSIS_DONE",
        action="analyzer_completed",
        details={"duration_seconds": 300},
    )

    paths = write_decision_event(tmp_path, event)

    human_path = tmp_path / "logs" / "decisions.log"
    jsonl_path = tmp_path / "logs" / "decisions.jsonl"

    assert human_path.exists()
    assert jsonl_path.exists()
    assert paths["decision_log_path"] == str(human_path)
    assert paths["decision_jsonl_path"] == str(jsonl_path)

    human_text = human_path.read_text(encoding="utf-8")
    assert "ANALYSIS_DONE" in human_text
    assert "gaming_pipeline" in human_text

    jsonl_lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    assert len(jsonl_lines) == 1

    loaded_event = json.loads(jsonl_lines[0])
    assert loaded_event["event_type"] == "ANALYSIS_DONE"
    assert loaded_event["details"]["duration_seconds"] == 300


def test_log_decision_returns_event_with_paths(tmp_path):
    job = _fake_job()

    event = log_decision(
        job=job,
        export_dir=tmp_path,
        phase="render",
        module="gaming_pipeline",
        event_type="RENDER_DONE",
        action="renderer_completed",
        reason="rendering_finished",
        details={"final_video_path": "exports/test/final.mp4"},
    )

    assert event["event_type"] == "RENDER_DONE"
    assert "_paths" in event
    assert (tmp_path / "logs" / "decisions.log").exists()
    assert (tmp_path / "logs" / "decisions.jsonl").exists()


def test_missing_optional_fields_do_not_crash(tmp_path):
    job = SimpleNamespace(job_id="job_minimal")

    event = log_decision(
        job=job,
        export_dir=tmp_path,
        phase="minimal",
        module="test_module",
        event_type="MINIMAL_EVENT",
        action="minimal_action",
    )

    assert event["job_id"] == "job_minimal"
    assert event["reason"] is None
    assert event["score"] is None
    assert event["profile_id"] is None
    assert event["quality_mode"] is None
    assert event["job_status"] is None
    assert event["details"] == {}
