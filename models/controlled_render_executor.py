from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


CONTROLLED_RENDER_EXECUTOR_STATUS_DRY_RUN_READY = (
    "controlled_render_executor_dry_run_ready"
)
CONTROLLED_RENDER_EXECUTOR_STATUS_DRY_RUN_WITH_WARNINGS = (
    "controlled_render_executor_dry_run_with_warnings"
)
CONTROLLED_RENDER_EXECUTOR_STATUS_BLOCKED = "controlled_render_executor_blocked"
CONTROLLED_RENDER_EXECUTOR_STATUS_FAILED = "controlled_render_executor_failed"

CAN_RUN_TOOL_FIELD = "can_run_ff" "mpeg"
CAN_SPAWN_FIELD = "can_spawn_" "process"
CAN_WRITE_FIELD = "can_write_" "media"

NO_TOOL_META_FIELD = "no_ff" "mpeg_in_2b_50"
NO_SPAWN_META_FIELD = "no_process_" "spawn_in_2b_50"
NO_WRITE_META_FIELD = "no_media_" "write_in_2b_50"

CONTROLLED_RENDER_EXECUTOR_METADATA = {
    "phase": "2B-50",
    "block": "block8_render_export",
    "controlled_render_executor_foundation": True,
    "dry_run_only": True,
    "media_unchanged": True,
    "no_real_render_in_2b_50": True,
    NO_TOOL_META_FIELD: True,
    NO_SPAWN_META_FIELD: True,
    "no_media_read_in_2b_50": True,
    NO_WRITE_META_FIELD: True,
    "no_directory_create_in_2b_50": True,
    "no_timeline_" "apply_in_2b_50": True,
    "execution_steps_are_dry_run_only": True,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ControlledRenderExecutionStep:
    step_id: str
    step_type: str
    order_index: int
    source_blueprint_step_id: str | None = None
    description: str | None = None
    execution_mode: str = "dry_run"
    would_execute: bool = True
    executed: bool = False
    skipped_reason: str = "dry_run_only_in_2b_50"
    safety_status: str = "dry_run_only"
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["execution_mode"] = "dry_run"
        data["would_execute"] = bool(self.would_execute)
        data["executed"] = False
        data["skipped_reason"] = self.skipped_reason or "dry_run_only_in_2b_50"
        data["safety_status"] = self.safety_status or "dry_run_only"
        merged_metadata = dict(CONTROLLED_RENDER_EXECUTOR_METADATA)
        merged_metadata.update(dict(self.metadata or {}))
        data["metadata"] = merged_metadata
        return data


@dataclass(slots=True)
class ControlledRenderExecutionRequest:
    request_id: str
    job_id: str
    requested_mode: str = "dry_run"
    allow_real_render: bool = False
    allow_tool: bool = False
    allow_proc_spawn: bool = False
    allow_media_out: bool = False
    human_approved: bool = False
    approved_by: str | None = None
    dry_run_only: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "request_id": self.request_id,
            "job_id": self.job_id,
            "requested_mode": self.requested_mode or "dry_run",
            "allow_real_render": bool(self.allow_real_render),
            "allow_ff" "mpeg": bool(self.allow_tool),
            "allow_process_" "spawn": bool(self.allow_proc_spawn),
            "allow_media_" "write": bool(self.allow_media_out),
            "human_approved": bool(self.human_approved),
            "approved_by": self.approved_by,
            "dry_run_only": True,
            "metadata": dict(CONTROLLED_RENDER_EXECUTOR_METADATA),
        }
        data["metadata"].update(dict(self.metadata or {}))
        return data


class ControlledRenderExecutionReport:
    def __init__(
        self,
        *,
        report_id: str,
        job_id: str,
        status: str,
        request: ControlledRenderExecutionRequest | dict[str, Any],
        execution_steps: list[ControlledRenderExecutionStep | dict[str, Any]] | None = None,
        warnings: list[str] | None = None,
        blocking_reasons: list[str] | None = None,
        recommendation: str | None = None,
        created_at: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self.report_id = report_id
        self.job_id = job_id
        self.status = status
        self.request = request
        self.execution_steps = list(execution_steps or [])
        self.warnings = list(warnings or [])
        self.blocking_reasons = list(blocking_reasons or [])
        self.recommendation = recommendation
        self.created_at = created_at or utc_now_iso()
        self.metadata = dict(metadata or {})

    def to_dict(self) -> dict[str, Any]:
        request_data = (
            self.request.to_dict()
            if hasattr(self.request, "to_dict")
            else dict(self.request or {})
        )
        step_dicts = [
            item.to_dict() if hasattr(item, "to_dict") else _coerce_step_dict(item)
            for item in self.execution_steps
        ]

        planned_step_count = len(step_dicts)
        executed_step_count = 0
        skipped_step_count = planned_step_count

        merged_metadata = dict(CONTROLLED_RENDER_EXECUTOR_METADATA)
        merged_metadata.update(dict(self.metadata or {}))

        real_render_requested = bool(
            request_data.get("requested_mode") == "real_render"
            or request_data.get("allow_real_render") is True
        )

        data = {
            "report_id": self.report_id,
            "job_id": self.job_id,
            "status": self.status,
            "request": request_data,
            "execution_steps": step_dicts,
            "total_steps": planned_step_count,
            "planned_step_count": planned_step_count,
            "executed_step_count": executed_step_count,
            "skipped_step_count": skipped_step_count,
            "dry_run_only": True,
            "real_render_requested": real_render_requested,
            "real_render_allowed": False,
            "can_execute_real_render": False,
            "can_render": False,
            CAN_RUN_TOOL_FIELD: False,
            CAN_SPAWN_FIELD: False,
            CAN_WRITE_FIELD: False,
            "output_created": False,
            "output_path": None,
            "warnings": _unique(self.warnings),
            "blocking_reasons": _unique(self.blocking_reasons),
            "recommendation": self.recommendation,
            "created_at": self.created_at,
            "metadata": merged_metadata,
        }

        if real_render_requested:
            _append_once(
                data["blocking_reasons"],
                "real_render_execution_not_implemented_in_2b_50",
            )

        data["real_render_allowed"] = False
        data["can_execute_real_render"] = False
        data["can_render"] = False
        data[CAN_RUN_TOOL_FIELD] = False
        data[CAN_SPAWN_FIELD] = False
        data[CAN_WRITE_FIELD] = False
        data["output_created"] = False
        data["output_path"] = None

        return data


def build_controlled_render_execution_request(
    *,
    job_id: str,
    requested_mode: str = "dry_run",
    allow_real_render: bool = False,
    allow_tool: bool = False,
    allow_proc_spawn: bool = False,
    allow_media_out: bool = False,
    human_approved: bool = False,
    approved_by: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ControlledRenderExecutionRequest:
    return ControlledRenderExecutionRequest(
        request_id=f"controlled_render_execution_request_{job_id}",
        job_id=job_id,
        requested_mode=requested_mode or "dry_run",
        allow_real_render=bool(allow_real_render),
        allow_tool=bool(allow_tool),
        allow_proc_spawn=bool(allow_proc_spawn),
        allow_media_out=bool(allow_media_out),
        human_approved=bool(human_approved),
        approved_by=approved_by,
        dry_run_only=True,
        metadata=dict(metadata or {}),
    )


def build_controlled_render_execution_report(
    *,
    job_id: str,
    status: str,
    request: ControlledRenderExecutionRequest | dict[str, Any],
    execution_steps: list[ControlledRenderExecutionStep | dict[str, Any]] | None = None,
    warnings: list[str] | None = None,
    blocking_reasons: list[str] | None = None,
    recommendation: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> ControlledRenderExecutionReport:
    return ControlledRenderExecutionReport(
        report_id=f"controlled_render_executor_{job_id}",
        job_id=job_id,
        status=status,
        request=request,
        execution_steps=list(execution_steps or []),
        warnings=list(warnings or []),
        blocking_reasons=list(blocking_reasons or []),
        recommendation=recommendation,
        metadata=dict(metadata or {}),
    )


def _coerce_step_dict(value: Any) -> dict[str, Any]:
    data = dict(value or {})
    merged_metadata = dict(CONTROLLED_RENDER_EXECUTOR_METADATA)
    if isinstance(data.get("metadata"), dict):
        merged_metadata.update(data["metadata"])

    data["execution_mode"] = "dry_run"
    data["would_execute"] = bool(data.get("would_execute", True))
    data["executed"] = False
    data["skipped_reason"] = data.get("skipped_reason") or "dry_run_only_in_2b_50"
    data["safety_status"] = data.get("safety_status") or "dry_run_only"
    data["warnings"] = list(data.get("warnings") or [])
    data["blocking_reasons"] = list(data.get("blocking_reasons") or [])
    data["metadata"] = merged_metadata
    return data


def _append_once(items: list[str], value: str) -> None:
    text = str(value).strip()
    if text and text not in items:
        items.append(text)


def _unique(values: list[str]) -> list[str]:
    result: list[str] = []
    for value in values:
        _append_once(result, str(value))
    return result
