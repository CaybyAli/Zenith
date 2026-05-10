from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _value_or_none(value: Any) -> str | None:
    if value is None:
        return None
    return str(getattr(value, "value", value))


def build_decision_event(
    job: Any,
    phase: str,
    module: str,
    event_type: str,
    action: str,
    status: str = "ok",
    reason: str | None = None,
    score: float | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "timestamp": _utc_now_iso(),
        "job_id": getattr(job, "job_id", None),
        "phase": phase,
        "module": module,
        "event_type": event_type,
        "action": action,
        "status": status,
        "reason": reason,
        "score": score,
        "profile_id": getattr(job, "profile_id", None),
        "quality_mode": _value_or_none(getattr(job, "quality_mode", None)),
        "job_status": _value_or_none(getattr(job, "status", None)),
        "details": dict(details or {}),
    }


def _format_human_line(event: dict[str, Any]) -> str:
    return (
        f"{event.get('timestamp')} "
        f"[{event.get('event_type')}] "
        f"job={event.get('job_id')} "
        f"phase={event.get('phase')} "
        f"module={event.get('module')} "
        f"action={event.get('action')} "
        f"status={event.get('status')} "
        f"reason={event.get('reason')} "
        f"score={event.get('score')} "
        f"profile_id={event.get('profile_id')} "
        f"quality_mode={event.get('quality_mode')} "
        f"job_status={event.get('job_status')}"
    )


def write_decision_event(export_dir: str | Path, event: dict[str, Any]) -> dict[str, str]:
    log_dir = Path(export_dir) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    human_path = log_dir / "decisions.log"
    jsonl_path = log_dir / "decisions.jsonl"

    with human_path.open("a", encoding="utf-8") as handle:
        handle.write(_format_human_line(event) + "\n")

    with jsonl_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")

    return {
        "decision_log_path": str(human_path),
        "decision_jsonl_path": str(jsonl_path),
    }


def log_decision(
    job: Any,
    export_dir: str | Path,
    phase: str,
    module: str,
    event_type: str,
    action: str,
    status: str = "ok",
    reason: str | None = None,
    score: float | None = None,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    event = build_decision_event(
        job=job,
        phase=phase,
        module=module,
        event_type=event_type,
        action=action,
        status=status,
        reason=reason,
        score=score,
        details=details,
    )

    paths = write_decision_event(export_dir=export_dir, event=event)
    event["_paths"] = paths
    return event
