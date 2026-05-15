from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


STYLE_DNA_APPLY_PLAN_STATUS_WAITING_FOR_REVIEW = (
    "style_dna_apply_plan_waiting_for_review"
)
STYLE_DNA_APPLY_PLAN_STATUS_READY = "style_dna_apply_plan_ready"
STYLE_DNA_APPLY_PLAN_STATUS_READY_WITH_WARNINGS = (
    "style_dna_apply_plan_ready_with_warnings"
)
STYLE_DNA_APPLY_PLAN_STATUS_BLOCKED = "style_dna_apply_plan_blocked"
STYLE_DNA_APPLY_PLAN_STATUS_FAILED = "style_dna_apply_plan_failed"

OPERATION_TYPE_SET_VALUE = "set_value"
OPERATION_TYPE_INCREMENT_VALUE = "increment_value"
OPERATION_TYPE_STABILIZE_VALUE = "stabilize_value"
OPERATION_TYPE_MANUAL_REVIEW_REQUIRED = "manual_review_required"
OPERATION_TYPE_MARK_REVIEW_REQUIRED = "mark_review_required"

PHASE_METADATA: dict[str, Any] = {
    "phase": "2B-62",
    "block": "block9_learning_feedback",
    "style_dna_apply_plan_only": True,
    "non_writing_apply_contract": True,
    "style_dna_preview_only": True,
    "no_style_dna_file_write_in_2b_62": True,
    "no_profile_change_in_2b_62": True,
    "no_cutting_rule_activation_in_2b_62": True,
    "no_timeline_modify_in_2b_62": True,
    "no_render_trigger_in_2b_62": True,
    "no_publish_in_2b_62": True,
}


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def normalize_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return bool(value)


def normalize_int(value: Any, default: int = 0) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return default


def normalize_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def normalize_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    return []


def normalize_text_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = normalize_text(item)
        if text and text not in result:
            result.append(text)
    return result


@dataclass
class StyleDNAApplyOperation:
    operation_id: str
    proposal_id: str
    parameter_name: str
    current_value: Any = None
    proposed_value: Any = None
    delta: Any = None
    operation_type: str = OPERATION_TYPE_SET_VALUE
    approved: bool = False
    planned_only: bool = True
    safe_to_apply_later: bool = False
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "operation_id": self.operation_id,
            "proposal_id": self.proposal_id,
            "parameter_name": self.parameter_name,
            "current_value": self.current_value,
            "proposed_value": self.proposed_value,
            "delta": self.delta,
            "operation_type": self.operation_type,
            "approved": bool(self.approved),
            "planned_only": True,
            "safe_to_apply_later": bool(self.safe_to_apply_later),
            "warnings": list(self.warnings),
            "blocking_reasons": list(self.blocking_reasons),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StyleDNAApplyOperation":
        source = normalize_dict(data)
        return cls(
            operation_id=normalize_text(source.get("operation_id")),
            proposal_id=normalize_text(source.get("proposal_id")),
            parameter_name=normalize_text(source.get("parameter_name")),
            current_value=source.get("current_value"),
            proposed_value=source.get("proposed_value"),
            delta=source.get("delta"),
            operation_type=normalize_text(
                source.get("operation_type"),
                OPERATION_TYPE_SET_VALUE,
            ),
            approved=normalize_bool(source.get("approved"), False),
            planned_only=True,
            safe_to_apply_later=normalize_bool(
                source.get("safe_to_apply_later"),
                False,
            ),
            warnings=normalize_text_list(source.get("warnings")),
            blocking_reasons=normalize_text_list(source.get("blocking_reasons")),
            metadata=normalize_dict(source.get("metadata")),
        )


@dataclass
class StyleDNAApplyPlan:
    plan_id: str
    job_id: str
    profile: str | None = None
    source_review_gate_id: str | None = None
    source_draft_id: str | None = None
    operations: list[StyleDNAApplyOperation] = field(default_factory=list)
    operation_count: int = 0
    approved_operation_count: int = 0
    skipped_operation_count: int = 0
    before_snapshot: dict[str, Any] = field(default_factory=dict)
    after_preview: dict[str, Any] = field(default_factory=dict)
    planned_only: bool = True
    non_writing: bool = True
    safe_to_review: bool = True
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        operations = [operation.to_dict() for operation in self.operations]
        return {
            "plan_id": self.plan_id,
            "job_id": self.job_id,
            "profile": self.profile,
            "source_review_gate_id": self.source_review_gate_id,
            "source_draft_id": self.source_draft_id,
            "operations": operations,
            "operation_count": int(self.operation_count),
            "approved_operation_count": int(self.approved_operation_count),
            "skipped_operation_count": int(self.skipped_operation_count),
            "before_snapshot": dict(self.before_snapshot),
            "after_preview": dict(self.after_preview),
            "planned_only": True,
            "non_writing": True,
            "safe_to_review": bool(self.safe_to_review),
            "warnings": list(self.warnings),
            "blocking_reasons": list(self.blocking_reasons),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StyleDNAApplyPlan":
        source = normalize_dict(data)
        operations = [
            StyleDNAApplyOperation.from_dict(item)
            for item in normalize_list(source.get("operations"))
            if isinstance(item, dict)
        ]
        return cls(
            plan_id=normalize_text(source.get("plan_id")),
            job_id=normalize_text(source.get("job_id")),
            profile=source.get("profile"),
            source_review_gate_id=source.get("source_review_gate_id"),
            source_draft_id=source.get("source_draft_id"),
            operations=operations,
            operation_count=normalize_int(
                source.get("operation_count"),
                len(operations),
            ),
            approved_operation_count=normalize_int(
                source.get("approved_operation_count"),
                len([operation for operation in operations if operation.approved]),
            ),
            skipped_operation_count=normalize_int(
                source.get("skipped_operation_count"),
                0,
            ),
            before_snapshot=normalize_dict(source.get("before_snapshot")),
            after_preview=normalize_dict(source.get("after_preview")),
            planned_only=True,
            non_writing=True,
            safe_to_review=normalize_bool(source.get("safe_to_review"), True),
            warnings=normalize_text_list(source.get("warnings")),
            blocking_reasons=normalize_text_list(source.get("blocking_reasons")),
            metadata=normalize_dict(source.get("metadata")),
        )


@dataclass
class StyleDNAApplyPlanReport:
    report_id: str
    job_id: str
    status: str
    profile: str | None = None
    source_review_status: str | None = None
    plan: StyleDNAApplyPlan | None = None
    operation_count: int = 0
    approved_operation_count: int = 0
    skipped_operation_count: int = 0
    ready_for_future_file_write: bool = False
    can_write_style_dna: bool = False
    can_apply_style_dna: bool = False
    can_update_profile: bool = False
    can_change_cutting_rules: bool = False
    can_modify_timeline: bool = False
    can_trigger_render: bool = False
    can_publish: bool = False
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    recommendation: str | None = None
    created_at: str = field(default_factory=utc_now_iso)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        plan_data = self.plan.to_dict() if self.plan else {}
        return {
            "report_id": self.report_id,
            "job_id": self.job_id,
            "status": self.status,
            "profile": self.profile,
            "source_review_status": self.source_review_status,
            "plan": plan_data,
            "operation_count": int(self.operation_count),
            "approved_operation_count": int(self.approved_operation_count),
            "skipped_operation_count": int(self.skipped_operation_count),
            "ready_for_future_file_write": bool(self.ready_for_future_file_write),
            "can_write_style_dna": False,
            "can_apply_style_dna": False,
            "can_update_profile": False,
            "can_change_cutting_rules": False,
            "can_modify_timeline": False,
            "can_trigger_render": False,
            "can_publish": False,
            "warnings": list(self.warnings),
            "blocking_reasons": list(self.blocking_reasons),
            "recommendation": self.recommendation,
            "created_at": self.created_at,
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StyleDNAApplyPlanReport":
        source = normalize_dict(data)
        plan_data = normalize_dict(source.get("plan"))
        plan = StyleDNAApplyPlan.from_dict(plan_data) if plan_data else None
        return cls(
            report_id=normalize_text(source.get("report_id")),
            job_id=normalize_text(source.get("job_id")),
            status=normalize_text(
                source.get("status"),
                STYLE_DNA_APPLY_PLAN_STATUS_WAITING_FOR_REVIEW,
            ),
            profile=source.get("profile"),
            source_review_status=source.get("source_review_status"),
            plan=plan,
            operation_count=normalize_int(source.get("operation_count"), 0),
            approved_operation_count=normalize_int(
                source.get("approved_operation_count"),
                0,
            ),
            skipped_operation_count=normalize_int(
                source.get("skipped_operation_count"),
                0,
            ),
            ready_for_future_file_write=normalize_bool(
                source.get("ready_for_future_file_write"),
                False,
            ),
            can_write_style_dna=False,
            can_apply_style_dna=False,
            can_update_profile=False,
            can_change_cutting_rules=False,
            can_modify_timeline=False,
            can_trigger_render=False,
            can_publish=False,
            warnings=normalize_text_list(source.get("warnings")),
            blocking_reasons=normalize_text_list(source.get("blocking_reasons")),
            recommendation=source.get("recommendation"),
            created_at=normalize_text(source.get("created_at"), utc_now_iso()),
            metadata=normalize_dict(source.get("metadata")),
        )
