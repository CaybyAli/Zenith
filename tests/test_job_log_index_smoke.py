from __future__ import annotations

import json
from types import SimpleNamespace

from core.job_log_index import (
    apply_job_log_index_to_job,
    build_job_log_index,
    update_job_log_index,
    write_job_log_index,
)
from models.job import Job


def _write_jsonl(path, events):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(event, ensure_ascii=False) for event in events) + "\n",
        encoding="utf-8",
    )


def _fake_job():
    return SimpleNamespace(
        job_id="job_log_index_smoke",
        decision_log_path=None,
        decision_jsonl_path=None,
        error_log_path=None,
        error_jsonl_path=None,
        log_index={},
        touched=False,
        touch=lambda: None,
    )


def test_build_job_log_index_reads_decision_logs(tmp_path):
    job = _fake_job()
    logs_dir = tmp_path / "logs"

    (logs_dir / "decisions.log").parent.mkdir(parents=True, exist_ok=True)
    (logs_dir / "decisions.log").write_text("human decision log\n", encoding="utf-8")

    decision_events = [
        {"event_type": "PROFILE_LOADED", "job_id": job.job_id},
        {"event_type": "RENDER_DONE", "job_id": job.job_id},
    ]
    _write_jsonl(logs_dir / "decisions.jsonl", decision_events)

    log_index = build_job_log_index(job, tmp_path)

    assert log_index["job_id"] == "job_log_index_smoke"
    assert log_index["has_decision_log"] is True
    assert log_index["decision_event_count"] == 2
    assert log_index["last_decision_event"]["event_type"] == "RENDER_DONE"
    assert log_index["has_error_log"] is False
    assert log_index["error_event_count"] == 0
    assert log_index["last_error_event"] is None


def test_build_job_log_index_reads_error_logs(tmp_path):
    job = _fake_job()
    logs_dir = tmp_path / "logs"

    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "errors.log").write_text("human error log\n", encoding="utf-8")

    error_events = [
        {"error_type": "RuntimeError", "error_message": "first"},
        {"error_type": "ValueError", "error_message": "last"},
    ]
    _write_jsonl(logs_dir / "errors.jsonl", error_events)

    log_index = build_job_log_index(job, tmp_path)

    assert log_index["has_error_log"] is True
    assert log_index["error_event_count"] == 2
    assert log_index["last_error_event"]["error_type"] == "ValueError"
    assert log_index["decision_event_count"] == 0
    assert log_index["last_decision_event"] is None


def test_apply_job_log_index_to_job_sets_fields(tmp_path):
    job = _fake_job()
    log_index = build_job_log_index(job, tmp_path)

    apply_job_log_index_to_job(job, log_index)

    assert job.decision_log_path == log_index["decision_log_path"]
    assert job.decision_jsonl_path == log_index["decision_jsonl_path"]
    assert job.error_log_path == log_index["error_log_path"]
    assert job.error_jsonl_path == log_index["error_jsonl_path"]
    assert job.log_index["job_id"] == "job_log_index_smoke"


def test_write_job_log_index_writes_json(tmp_path):
    job = _fake_job()
    log_index = build_job_log_index(job, tmp_path)

    path = write_job_log_index(tmp_path, log_index)

    assert path == tmp_path / "job_log_index.json"
    assert path.exists()

    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["job_id"] == "job_log_index_smoke"
    assert "decision_log_path" in loaded
    assert "error_jsonl_path" in loaded


def test_update_job_log_index_does_everything(tmp_path):
    job = _fake_job()
    logs_dir = tmp_path / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    (logs_dir / "decisions.log").write_text("human decision log\n", encoding="utf-8")
    _write_jsonl(
        logs_dir / "decisions.jsonl",
        [{"event_type": "PROFILE_LOADED"}, {"event_type": "RENDER_DONE"}],
    )

    log_index = update_job_log_index(job, tmp_path)

    assert (tmp_path / "job_log_index.json").exists()
    assert job.log_index["decision_event_count"] == 2
    assert log_index["last_decision_event"]["event_type"] == "RENDER_DONE"


def test_job_to_dict_from_dict_preserves_log_fields():
    data = {
        "job_id": "job_model_log_fields",
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
            "last_decision_event": {"event_type": "RENDER_DONE"},
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
