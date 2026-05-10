from __future__ import annotations

import json
import traceback as traceback_module
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _value_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(getattr(value, "value", value))


def build_error_event(
    job: Any,
    module: str,
    phase: str,
    error: BaseException,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "timestamp": _utc_now_iso(),
        "job_id": getattr(job, "job_id", None),
        "module": module,
        "phase": phase,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "traceback": "".join(
            traceback_module.format_exception(
                type(error),
                error,
                error.__traceback__,
            )
        ),
        "job_status": _value_or_none(getattr(job, "status", None)),
        "current_module": getattr(job, "current_module", None),
        "profile_id": getattr(job, "profile_id", None),
        "quality_mode": _value_or_none(getattr(job, "quality_mode", None)),
        "recovery_status": getattr(job, "recovery_status", None),
        "resume_safety": getattr(job, "resume_safety", None),
        "details": dict(details or {}),
    }


def _format_human_line(event: dict[str, Any]) -> str:
    return (
        f"{event.get('timestamp')} "
        f"[ERROR] "
        f"job={event.get('job_id')} "
        f"module={event.get('module')} "
        f"phase={event.get('phase')} "
        f"error_type={event.get('error_type')} "
        f"message={event.get('error_message')} "
        f"job_status={event.get('job_status')} "
        f"profile_id={event.get('profile_id')} "
        f"quality_mode={event.get('quality_mode')}"
    )


def write_error_event(export_dir: str | Path, event: dict[str, Any]) -> dict[str, str]:
    log_dir = Path(export_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    human_path = log_dir / "errors.log"
    jsonl_path = log_dir / "errors.jsonl"

    with human_path.open("a", encoding="utf-8") as handle:
        handle.write(_format_human_line(event) + "\n")
        if event.get("traceback"):
            handle.write(str(event["traceback"]) + "\n")

    with jsonl_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")

    return {
        "error_log_path": str(human_path),
        "error_jsonl_path": str(jsonl_path),
    }


def log_error(
    job: Any,
    export_dir: str | Path,
    module: str,
    phase: str,
    error: BaseException,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = build_error_event(
        job=job,
        module=module,
        phase=phase,
        error=error,
        details=details,
    )

    paths = write_error_event(export_dir=export_dir, event=event)
    event["_paths"] = paths
    return event
