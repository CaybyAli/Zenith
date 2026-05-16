from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


APPROVAL_FILE_NAME = "approval.json"


def _job_attr(job: Any, name: str, default: Any = None) -> Any:
    if isinstance(job, dict):
        return job.get(name, default)
    return getattr(job, name, default)


def _value_text(value: Any) -> str:
    return str(getattr(value, "value", value) or "").strip()


def _job_id(job: Any) -> str:
    return _value_text(_job_attr(job, "job_id"))


def _channel(job: Any) -> str:
    return _value_text(_job_attr(job, "channel_type"))


def approval_file_path(
    *,
    job_id: str,
    channel: str,
    exports_base: str | Path = "exports",
) -> Path:
    return Path(exports_base) / channel / job_id / APPROVAL_FILE_NAME


def approval_file_path_for_job(
    job: Any,
    exports_base: str | Path = "exports",
) -> Path | None:
    job_id = _job_id(job)
    channel = _channel(job)
    if not job_id or not channel:
        return None
    return approval_file_path(
        job_id=job_id,
        channel=channel,
        exports_base=exports_base,
    )


def write_job_approval(
    *,
    job_id: str,
    channel: str,
    approved_by: str = "cli",
    exports_base: str | Path = "exports",
) -> Path:
    path = approval_file_path(
        job_id=job_id,
        channel=channel,
        exports_base=exports_base,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "approved": True,
        "job_id": str(job_id),
        "channel": str(channel),
        "approved_at": datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z"),
        "approved_by": str(approved_by),
    }
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path


def read_job_approval(
    job: Any,
    exports_base: str | Path = "exports",
) -> dict[str, Any] | None:
    path = approval_file_path_for_job(job, exports_base=exports_base)
    if path is None or not path.is_file():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None
    if payload.get("approved") is not True:
        return None

    expected_job_id = _job_id(job)
    expected_channel = _channel(job)
    if str(payload.get("job_id") or "") != expected_job_id:
        return None
    if str(payload.get("channel") or "") != expected_channel:
        return None

    payload = dict(payload)
    payload["approval_file"] = str(path)
    return payload


def is_job_explicitly_approved(
    job: Any,
    exports_base: str | Path = "exports",
) -> bool:
    return read_job_approval(job, exports_base=exports_base) is not None
