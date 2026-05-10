from __future__ import annotations

import json
from pathlib import Path
from typing import Any


CLEAN_COMPLETE_STATUSES = {"assembled", "done", "published", "rendered"}
ACTIVE_INCOMPLETE_STATUSES = {"analyzing", "analyzed", "cutting", "cut", "rendering"}
FAILED_STATUSES = {"failed"}


def _status_value(status: Any) -> str | None:
    if status is None:
        return None

    return str(getattr(status, "value", status))


def _read_json_file(path: Path) -> dict[str, Any] | None:
    try:
        if not path.exists():
            return None

        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data

        return None
    except Exception:
        return None


def _read_jsonl_count(path: Path) -> int:
    try:
        if not path.exists():
            return 0

        return len(
            [
                line
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        )
    except Exception:
        return 0


def build_recovery_report(job: Any, export_dir: str | Path | None = None) -> dict[str, Any]:
    status = _status_value(getattr(job, "status", None))
    state_history = list(getattr(job, "state_history", []) or [])
    last_transition = state_history[-1] if state_history else None

    checkpoint = None
    checkpoint_path = None
    checkpoint_count = 0

    if export_dir is not None:
        export_path = Path(export_dir)
        checkpoint_path_obj = export_path / "job_state_checkpoint.json"
        checkpoint = _read_json_file(checkpoint_path_obj)
        checkpoint_path = str(checkpoint_path_obj) if checkpoint_path_obj.exists() else None
        checkpoint_count = _read_jsonl_count(export_path / "job_state_checkpoints.jsonl")

    has_recovery_evidence = bool(state_history) or checkpoint is not None or checkpoint_count > 0

    recovery_status = "unknown"
    resume_safety = "unknown"
    recommended_action = "manual_review"
    reason = "status_unknown_or_missing"

    if status in CLEAN_COMPLETE_STATUSES:
        recovery_status = "clean_complete"
        resume_safety = "safe"

        if status in {"assembled", "rendered"}:
            recommended_action = "review_or_publish"
            reason = "job_reached_reviewable_complete_state"
        else:
            recommended_action = "none"
            reason = "job_already_complete"

    elif status in FAILED_STATUSES:
        recovery_status = "manual_review_required"
        resume_safety = "unsafe"
        recommended_action = "inspect_error"
        reason = "job_failed"

    elif status in ACTIVE_INCOMPLETE_STATUSES:
        if not has_recovery_evidence:
            recovery_status = "unknown"
            resume_safety = "unknown"
            recommended_action = "manual_review"
            reason = "active_status_without_checkpoint_or_state_history"
        else:
            recovery_status = "needs_recovery"
            recommended_action = "manual_review"

            if status == "rendering":
                resume_safety = "unsafe"
                reason = "job_interrupted_during_rendering"
            else:
                resume_safety = "caution"
                reason = f"job_interrupted_during_{status}"

    elif not has_recovery_evidence:
        recovery_status = "unknown"
        resume_safety = "unknown"
        recommended_action = "manual_review"
        reason = "missing_checkpoint_and_state_history"

    return {
        "job_id": getattr(job, "job_id", None),
        "current_status": status,
        "current_module": getattr(job, "current_module", None),
        "recovery_status": recovery_status,
        "resume_safety": resume_safety,
        "last_checkpoint_path": checkpoint_path,
        "last_checkpoint": checkpoint,
        "checkpoint_count": checkpoint_count,
        "state_history_count": len(state_history),
        "last_state_transition": last_transition,
        "recommended_action": recommended_action,
        "reason": reason,
    }


def apply_recovery_report_to_job(job: Any, report: dict[str, Any]) -> Any:
    job.recovery_status = report.get("recovery_status")
    job.resume_safety = report.get("resume_safety")
    job.recovery_report = dict(report)

    if hasattr(job, "touch"):
        job.touch()

    return job