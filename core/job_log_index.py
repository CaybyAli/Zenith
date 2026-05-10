from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _read_jsonl_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []

    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue

        try:
            data = json.loads(line)
        except Exception:
            continue

        if isinstance(data, dict):
            events.append(data)

    return events


def build_job_log_index(job: Any, export_dir: str | Path) -> dict[str, Any]:
    export_path = Path(export_dir)
    logs_dir = export_path / "logs"

    decision_log_path = logs_dir / "decisions.log"
    decision_jsonl_path = logs_dir / "decisions.jsonl"
    error_log_path = logs_dir / "errors.log"
    error_jsonl_path = logs_dir / "errors.jsonl"

    decision_events = _read_jsonl_events(decision_jsonl_path)
    error_events = _read_jsonl_events(error_jsonl_path)

    return {
        "job_id": getattr(job, "job_id", None),
        "logs_dir": str(logs_dir),
        "decision_log_path": str(decision_log_path),
        "decision_jsonl_path": str(decision_jsonl_path),
        "error_log_path": str(error_log_path),
        "error_jsonl_path": str(error_jsonl_path),
        "has_decision_log": decision_log_path.exists(),
        "has_error_log": error_log_path.exists(),
        "decision_event_count": len(decision_events),
        "error_event_count": len(error_events),
        "last_decision_event": decision_events[-1] if decision_events else None,
        "last_error_event": error_events[-1] if error_events else None,
    }


def apply_job_log_index_to_job(job: Any, log_index: dict[str, Any]) -> Any:
    job.decision_log_path = log_index.get("decision_log_path")
    job.decision_jsonl_path = log_index.get("decision_jsonl_path")
    job.error_log_path = log_index.get("error_log_path")
    job.error_jsonl_path = log_index.get("error_jsonl_path")
    job.log_index = dict(log_index)

    if hasattr(job, "touch"):
        job.touch()

    return job


def write_job_log_index(export_dir: str | Path, log_index: dict[str, Any]) -> Path:
    export_path = Path(export_dir)
    export_path.mkdir(parents=True, exist_ok=True)

    path = export_path / "job_log_index.json"
    path.write_text(
        json.dumps(log_index, indent=4, ensure_ascii=False, default=str),
        encoding="utf-8",
    )
    return path


def update_job_log_index(job: Any, export_dir: str | Path) -> dict[str, Any]:
    log_index = build_job_log_index(job, export_dir)
    apply_job_log_index_to_job(job, log_index)
    write_job_log_index(export_dir, log_index)
    return log_index
