from __future__ import annotations

import json
from types import SimpleNamespace

from core.error_logger import (
    build_error_event,
    log_error,
    write_error_event,
)


def _fake_job():
    return SimpleNamespace(
        job_id="job_error_logger_smoke",
        profile_id="gaming_main",
        quality_mode="pro",
        status="rendering",
        current_module="gaming_pipeline",
        recovery_status="not_started",
        resume_safety="unknown",
    )


def _make_test_error() -> RuntimeError:
    try:
        raise RuntimeError("ffmpeg failed during smoke test")
    except RuntimeError as exc:
        return exc


def test_build_error_event_contains_required_fields():
    job = _fake_job()
    error = _make_test_error()

    event = build_error_event(
        job=job,
        module="gaming_pipeline",
        phase="render",
        error=error,
        details={"renderer": "FinalRenderDriver"},
    )

    required_fields = {
        "timestamp",
        "job_id",
        "module",
        "phase",
        "error_type",
        "error_message",
        "traceback",
        "job_status",
        "current_module",
        "profile_id",
        "quality_mode",
        "recovery_status",
        "resume_safety",
        "details",
    }

    assert required_fields.issubset(event.keys())
    assert event["job_id"] == "job_error_logger_smoke"
    assert event["module"] == "gaming_pipeline"
    assert event["phase"] == "render"
    assert event["error_type"] == "RuntimeError"
    assert event["error_message"] == "ffmpeg failed during smoke test"
    assert "RuntimeError: ffmpeg failed during smoke test" in event["traceback"]
    assert event["job_status"] == "rendering"
    assert event["current_module"] == "gaming_pipeline"
    assert event["profile_id"] == "gaming_main"
    assert event["quality_mode"] == "pro"
    assert event["recovery_status"] == "not_started"
    assert event["resume_safety"] == "unknown"
    assert event["details"]["renderer"] == "FinalRenderDriver"


def test_write_error_event_writes_human_log_and_jsonl(tmp_path):
    job = _fake_job()
    error = _make_test_error()

    event = build_error_event(
        job=job,
        module="pipeline_runner",
        phase="dispatch",
        error=error,
        details={"channel": "gaming_main"},
    )

    paths = write_error_event(tmp_path, event)

    human_path = tmp_path / "logs" / "errors.log"
    jsonl_path = tmp_path / "logs" / "errors.jsonl"

    assert human_path.exists()
    assert jsonl_path.exists()
    assert paths["error_log_path"] == str(human_path)
    assert paths["error_jsonl_path"] == str(jsonl_path)

    human_text = human_path.read_text(encoding="utf-8")
    assert "[ERROR]" in human_text
    assert "RuntimeError" in human_text
    assert "ffmpeg failed during smoke test" in human_text
    assert "Traceback" in human_text

    jsonl_lines = jsonl_path.read_text(encoding="utf-8").splitlines()
    assert len(jsonl_lines) == 1

    loaded_event = json.loads(jsonl_lines[0])
    assert loaded_event["error_type"] == "RuntimeError"
    assert loaded_event["details"]["channel"] == "gaming_main"
    assert "RuntimeError: ffmpeg failed during smoke test" in loaded_event["traceback"]


def test_log_error_returns_event_with_paths(tmp_path):
    job = _fake_job()
    error = _make_test_error()

    event = log_error(
        job=job,
        export_dir=tmp_path,
        module="gaming_pipeline",
        phase="render",
        error=error,
        details={"final_video_path": "output/test.mp4"},
    )

    assert event["error_type"] == "RuntimeError"
    assert "_paths" in event
    assert (tmp_path / "logs" / "errors.log").exists()
    assert (tmp_path / "logs" / "errors.jsonl").exists()


def test_missing_optional_job_fields_do_not_crash(tmp_path):
    job = SimpleNamespace(job_id="job_minimal")
    error = _make_test_error()

    event = log_error(
        job=job,
        export_dir=tmp_path,
        module="test_module",
        phase="test_phase",
        error=error,
    )

    assert event["job_id"] == "job_minimal"
    assert event["profile_id"] is None
    assert event["quality_mode"] is None
    assert event["job_status"] is None
    assert event["current_module"] is None
    assert event["recovery_status"] is None
    assert event["resume_safety"] is None
    assert event["details"] == {}
