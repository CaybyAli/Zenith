from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _status_value(status: Any) -> str | None:
    if status is None:
        return None

    return str(getattr(status, "value", status))


def build_job_state_checkpoint(
    job: Any,
    step_name: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    state_history = list(getattr(job, "state_history", []) or [])
    last_transition = state_history[-1] if state_history else None

    return {
        "job_id": getattr(job, "job_id", None),
        "status": _status_value(getattr(job, "status", None)),
        "current_module": getattr(job, "current_module", None),
        "step_name": step_name,
        "reason": reason,
        "profile_id": getattr(job, "profile_id", None),
        "quality_mode": getattr(job, "quality_mode", None),
        "profile_version": getattr(job, "profile_version", None),
        "profile_snapshot_path": getattr(job, "profile_snapshot_path", None),
        "profile_source": getattr(job, "profile_source", None),
        "state_history_count": len(state_history),
        "last_state_transition": last_transition,
        "timestamp": _utc_now_iso(),
    }


def persist_job_state_checkpoint(
    job: Any,
    job_store: Any | None = None,
    export_dir: str | Path | None = None,
    step_name: str | None = None,
    reason: str | None = None,
) -> dict[str, Any]:
    checkpoint = build_job_state_checkpoint(
        job=job,
        step_name=step_name,
        reason=reason,
    )

    json.dumps(checkpoint)

    if job_store is not None:
        job_store.update_job(job)

    if export_dir is not None:
        export_path = Path(export_dir)
        export_path.mkdir(parents=True, exist_ok=True)

        checkpoint_path = export_path / "job_state_checkpoint.json"
        checkpoint_path.write_text(
            json.dumps(checkpoint, indent=4, ensure_ascii=False),
            encoding="utf-8",
        )

        jsonl_path = export_path / "job_state_checkpoints.jsonl"
        with jsonl_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(checkpoint, ensure_ascii=False) + "\n")

    return checkpoint
