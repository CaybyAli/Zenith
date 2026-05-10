from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from core.debug_mode import (
    build_debug_context,
    get_debug_mode,
    is_debug_enabled,
    is_trace_enabled,
    is_verbose_enabled,
)
from core.decision_logger import build_decision_event, log_decision
from core.error_logger import build_error_event, log_error
from core.job_log_index import update_job_log_index
from models.job import Job


def _fake_job():
    return SimpleNamespace(
        job_id="job_logging_final_audit",
        profile_id="gaming_main",
        quality_mode="pro",
        status="created",
        current_module="final_audit",
        recovery_status=None,
        resume_safety=None,
        decision_log_path=None,
        decision_jsonl_path=None,
        error_log_path=None,
        error_jsonl_path=None,
        log_index={},
        debug_mode="off",
        debug_context={},
        touched=False,
        touch=lambda: None,
    )


def test_decision_and_error_logs_are_written_and_indexed(tmp_path):
    job = _fake_job()

    decision_event = build_decision_event(
        job=job,
        phase="audit",
        module="logging_final_audit",
        event_type="FINAL_AUDIT_DECISION",
        action="write_decision_log",
        reason="final_audit",
        details={"debug_context": build_debug_context(job=job)},
    )

    assert decision_event["job_id"] == "job_logging_final_audit"
    assert decision_event["profile_id"] == "gaming_main"
    assert decision_event["quality_mode"] == "pro"
    assert decision_event["details"]["debug_context"]["debug_mode"] == "off"

    log_decision(
        job=job,
        export_dir=tmp_path,
        phase="audit",
        module="logging_final_audit",
        event_type="FINAL_AUDIT_DECISION",
        action="write_decision_log",
        reason="final_audit",
        details={"debug_context": build_debug_context(job=job)},
    )

    try:
        raise RuntimeError("controlled final audit error")
    except RuntimeError as exc:
        error_event = build_error_event(
            job=job,
            module="logging_final_audit",
            phase="audit",
            error=exc,
            details={"purpose": "final_audit"},
        )
        log_error(
            job=job,
            export_dir=tmp_path,
            module="logging_final_audit",
            phase="audit",
            error=exc,
            details={"purpose": "final_audit"},
        )

    assert error_event["job_id"] == "job_logging_final_audit"
    assert error_event["error_type"] == "RuntimeError"
    assert "controlled final audit error" in error_event["error_message"]
    assert "RuntimeError" in error_event["traceback"]

    assert (tmp_path / "logs" / "decisions.log").exists()
    assert (tmp_path / "logs" / "decisions.jsonl").exists()
    assert (tmp_path / "logs" / "errors.log").exists()
    assert (tmp_path / "logs" / "errors.jsonl").exists()

    decision_lines = (tmp_path / "logs" / "decisions.jsonl").read_text(encoding="utf-8").splitlines()
    error_lines = (tmp_path / "logs" / "errors.jsonl").read_text(encoding="utf-8").splitlines()

    loaded_decision = json.loads(decision_lines[0])
    loaded_error = json.loads(error_lines[0])

    assert loaded_decision["event_type"] == "FINAL_AUDIT_DECISION"
    assert loaded_decision["profile_id"] == "gaming_main"
    assert loaded_decision["quality_mode"] == "pro"
    assert loaded_error["error_type"] == "RuntimeError"
    assert "RuntimeError" in loaded_error["traceback"]

    log_index = update_job_log_index(job, tmp_path)

    assert (tmp_path / "job_log_index.json").exists()
    assert log_index["decision_event_count"] == 1
    assert log_index["error_event_count"] == 1
    assert log_index["last_decision_event"]["event_type"] == "FINAL_AUDIT_DECISION"
    assert log_index["last_error_event"]["error_type"] == "RuntimeError"

    assert job.decision_log_path == log_index["decision_log_path"]
    assert job.error_log_path == log_index["error_log_path"]
    assert job.log_index["decision_event_count"] == 1
    assert job.log_index["error_event_count"] == 1


def test_debug_context_and_job_model_logging_fields_roundtrip():
    data = {
        "job_id": "job_logging_model_roundtrip",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "longform",
        "target_platforms": ["youtube"],
        "status": "created",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
        "decision_log_path": "exports/gaming_main/job/logs/decisions.log",
        "decision_jsonl_path": "exports/gaming_main/job/logs/decisions.jsonl",
        "error_log_path": "exports/gaming_main/job/logs/errors.log",
        "error_jsonl_path": "exports/gaming_main/job/logs/errors.jsonl",
        "log_index": {
            "decision_event_count": 7,
            "error_event_count": 0,
            "last_decision_event": {"event_type": "RENDER_DONE"},
        },
        "debug_mode": "verbose",
        "debug_context": {
            "debug_mode": "verbose",
            "debug_enabled": True,
            "verbose_enabled": True,
            "trace_enabled": False,
        },
    }

    job = Job.from_dict(data)
    as_dict = job.to_dict()

    assert as_dict["decision_log_path"] == data["decision_log_path"]
    assert as_dict["decision_jsonl_path"] == data["decision_jsonl_path"]
    assert as_dict["error_log_path"] == data["error_log_path"]
    assert as_dict["error_jsonl_path"] == data["error_jsonl_path"]
    assert as_dict["log_index"]["decision_event_count"] == 7
    assert as_dict["log_index"]["last_decision_event"]["event_type"] == "RENDER_DONE"
    assert as_dict["debug_mode"] == "verbose"
    assert as_dict["debug_context"]["debug_mode"] == "verbose"
    assert as_dict["debug_context"]["debug_enabled"] is True
    assert as_dict["debug_context"]["verbose_enabled"] is True
    assert as_dict["debug_context"]["trace_enabled"] is False


def test_debug_mode_levels_are_correct():
    assert get_debug_mode() == "off"
    assert is_debug_enabled() is False
    assert is_verbose_enabled() is False
    assert is_trace_enabled() is False

    assert get_debug_mode(services={"debug_mode": "normal"}) == "normal"
    assert is_debug_enabled(services={"debug_mode": "normal"}) is True
    assert is_verbose_enabled(services={"debug_mode": "normal"}) is False
    assert is_trace_enabled(services={"debug_mode": "normal"}) is False

    assert get_debug_mode(services={"debug_mode": "verbose"}) == "verbose"
    assert is_debug_enabled(services={"debug_mode": "verbose"}) is True
    assert is_verbose_enabled(services={"debug_mode": "verbose"}) is True
    assert is_trace_enabled(services={"debug_mode": "verbose"}) is False

    assert get_debug_mode(services={"debug_mode": "trace"}) == "trace"
    assert is_debug_enabled(services={"debug_mode": "trace"}) is True
    assert is_verbose_enabled(services={"debug_mode": "trace"}) is True
    assert is_trace_enabled(services={"debug_mode": "trace"}) is True

    assert get_debug_mode(services={"debug_mode": "invalid"}) == "off"
    assert get_debug_mode(services={"debug_mode": True}) == "normal"
    assert get_debug_mode(services={"debug_mode": False}) == "off"

    context = build_debug_context(
        job=SimpleNamespace(job_id="job_debug_audit", profile_id="fallback", quality_mode="balanced"),
        profile={"profile_id": "gaming_main", "quality_mode": "pro", "debug_mode": "trace"},
    )

    assert context["debug_mode"] == "trace"
    assert context["debug_enabled"] is True
    assert context["verbose_enabled"] is True
    assert context["trace_enabled"] is True
    assert context["job_id"] == "job_debug_audit"
    assert context["profile_id"] == "gaming_main"
    assert context["quality_mode"] == "pro"


def test_logging_system_files_have_no_bom_and_end_with_newline():
    paths = [
        Path("core/decision_logger.py"),
        Path("core/error_logger.py"),
        Path("core/job_log_index.py"),
        Path("core/debug_mode.py"),
        Path("tests/test_decision_logger_smoke.py"),
        Path("tests/test_error_logger_smoke.py"),
        Path("tests/test_job_log_index_smoke.py"),
        Path("tests/test_debug_mode_smoke.py"),
        Path("tests/test_logging_system_final_audit_smoke.py"),
    ]

    for path in paths:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"{path} has UTF-8 BOM"
        assert raw.endswith(b"\n"), f"{path} does not end with newline"
