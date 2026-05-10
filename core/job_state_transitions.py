from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from shared.enums import JobStatus


class JobStateTransitionError(ValueError):
    pass


ALLOWED_JOB_STATUS_TRANSITIONS = {
    JobStatus.CREATED.value: {
        JobStatus.ANALYZING.value,
        JobStatus.FAILED.value,
    },
    JobStatus.STORED.value: {
        JobStatus.ANALYZING.value,
        JobStatus.FAILED.value,
    },
    JobStatus.ROUTED.value: {
        JobStatus.ANALYZING.value,
        JobStatus.FAILED.value,
    },
    JobStatus.PENDING.value: {
        JobStatus.ANALYZING.value,
        JobStatus.FAILED.value,
    },
    JobStatus.PROCESSING.value: {
        JobStatus.ANALYZING.value,
        JobStatus.FAILED.value,
    },
    JobStatus.ANALYZING.value: {
        JobStatus.ANALYZED.value,
        JobStatus.FAILED.value,
    },
    JobStatus.ANALYZED.value: {
        JobStatus.CUTTING.value,
        JobStatus.FAILED.value,
    },
    JobStatus.CUTTING.value: {
        JobStatus.CUT.value,
        JobStatus.FAILED.value,
    },
    JobStatus.CUT.value: {
        JobStatus.RENDERING.value,
        JobStatus.FAILED.value,
    },
    JobStatus.RENDERING.value: {
        JobStatus.RENDERED.value,
        JobStatus.FAILED.value,
    },
    JobStatus.RENDERED.value: {
        JobStatus.ASSEMBLED.value,
        JobStatus.DONE.value,
        JobStatus.PUBLISHED.value,
        JobStatus.FAILED.value,
    },
    JobStatus.ASSEMBLED.value: {
        JobStatus.DONE.value,
        JobStatus.PUBLISHED.value,
        JobStatus.FAILED.value,
    },
    JobStatus.DONE.value: {
        JobStatus.PUBLISHED.value,
        JobStatus.FAILED.value,
    },
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _status_value(status: Any) -> str:
    return str(getattr(status, "value", status))


def _coerce_status(value: JobStatus | str) -> JobStatus:
    if isinstance(value, JobStatus):
        return value

    return JobStatus(str(value))


def _append_state_history(
    job: Any,
    old_status: JobStatus,
    new_status: JobStatus,
    module: str | None,
    reason: str | None,
) -> None:
    if not hasattr(job, "state_history") or job.state_history is None:
        job.state_history = []

    job.state_history.append(
        {
            "from": old_status.value,
            "to": new_status.value,
            "module": module,
            "reason": reason,
            "timestamp": _utc_now_iso(),
        }
    )


def transition_job_state(
    job: Any,
    new_status: JobStatus | str,
    module: str | None = None,
    reason: str | None = None,
) -> JobStatus:
    old_status = _coerce_status(getattr(job, "status", JobStatus.CREATED))
    next_status = _coerce_status(new_status)

    if old_status == next_status:
        return next_status

    allowed_next = ALLOWED_JOB_STATUS_TRANSITIONS.get(old_status.value, set())

    if next_status.value not in allowed_next:
        raise JobStateTransitionError(
            f"Invalid job status transition: {old_status.value} -> {next_status.value}"
        )

    job.status = next_status

    if module is not None:
        job.current_module = module

    _append_state_history(
        job=job,
        old_status=old_status,
        new_status=next_status,
        module=module,
        reason=reason,
    )

    if hasattr(job, "touch"):
        job.touch()

    return next_status