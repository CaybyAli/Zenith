from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


STYLE_DNA_PERSISTENCE_STATUS_PENDING_WRITE_REVIEW = (
    "style_dna_persistence_pending_write_review"
)
STYLE_DNA_PERSISTENCE_STATUS_APPROVED_WRITE = (
    "style_dna_persistence_approved_write"
)
STYLE_DNA_PERSISTENCE_STATUS_REJECTED_WRITE = (
    "style_dna_persistence_rejected_write"
)
STYLE_DNA_PERSISTENCE_STATUS_NEEDS_MANUAL_CHANGES = (
    "style_dna_persistence_needs_manual_changes"
)
STYLE_DNA_PERSISTENCE_STATUS_BLOCKED = "style_dna_persistence_blocked"
STYLE_DNA_PERSISTENCE_STATUS_FAILED = "style_dna_persistence_failed"

REQUEST_STATUS_PENDING_WRITE_REVIEW = "pending_write_review"
REQUEST_STATUS_APPROVED_WRITE = "approved_write"
REQUEST_STATUS_REJECTED_WRITE = "rejected_write"
REQUEST_STATUS_NEEDS_MANUAL_CHANGES = "needs_manual_changes"

ALLOWED_REQUEST_STATUSES = {
    REQUEST_STATUS_PENDING_WRITE_REVIEW,
    REQUEST_STATUS_APPROVED_WRITE,
    REQUEST_STATUS_REJECTED_WRITE,
    REQUEST_STATUS_NEEDS_MANUAL_CHANGES,
}

PHASE_METADATA: dict[str, Any] = {
    "phase": "2B-63",
    "block": "block9_learning_feedback",
    "style_dna_persistence_gate_only": True,
    "final_human_write_permission_gate": True,
    "write_intent_only": True,
    "no_style_dna_file_write_in_2b_63": True,
    "no_backup_write_in_2b_63": True,
    "no_profile_change_in_2b_63": True,
    "no_cutting_rule_activation_in_2b_63": True,
    "no_timeline_modify_in_2b_63": True,
    "no_render_trigger_in_2b_63": True,
    "no_publish_in_2b_63": True,
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
class StyleDNAPersistenceWriteIntent:
    intent_id: str
    profile: str | None = None
    target_path_hint: str | None = None
    operation_count: int = 0
    approved_operation_count: int = 0
    backup_required: bool = True
    before_snapshot: dict[str, Any] = field(default_factory=dict)
    after_preview: dict[str, Any] = field(default_factory=dict)
    write_preview_hash: str | None = None
    planned_only: bool = True
    no_file_write_performed: bool = True
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "intent_id": self.intent_id,
            "profile": self.profile,
            "target_path_hint": self.target_path_hint,
            "operation_count": int(self.operation_count),
            "approved_operation_count": int(self.approved_operation_count),
            "backup_required": bool(self.backup_required),
            "before_snapshot": dict(self.before_snapshot),
            "after_preview": dict(self.after_preview),
            "write_preview_hash": self.write_preview_hash,
            "planned_only": True,
            "no_file_write_performed": True,
            "warnings": list(self.warnings),
            "blocking_reasons": list(self.blocking_reasons),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "StyleDNAPersistenceWriteIntent":
        source = normalize_dict(data)
        return cls(
            intent_id=normalize_text(source.get("intent_id")),
            profile=source.get("profile"),
            target_path_hint=source.get("target_path_hint"),
            operation_count=normalize_int(source.get("operation_count"), 0),
            approved_operation_count=normalize_int(
                source.get("approved_operation_count"),
                0,
            ),
            backup_required=normalize_bool(source.get("backup_required"), True),
            before_snapshot=normalize_dict(source.get("before_snapshot")),
            after_preview=normalize_dict(source.get("after_preview")),
            write_preview_hash=source.get("write_preview_hash"),
            planned_only=True,
            no_file_write_performed=True,
            warnings=normalize_text_list(source.get("warnings")),
            blocking_reasons=normalize_text_list(source.get("blocking_reasons")),
            metadata=normalize_dict(source.get("metadata")),
        )


@dataclass
class StyleDNAPersistenceGate:
    gate_id: str
    job_id: str
    source_apply_plan_id: str | None = None
    requested_status: str = REQUEST_STATUS_PENDING_WRITE_REVIEW
    status: str = STYLE_DNA_PERSISTENCE_STATUS_PENDING_WRITE_REVIEW
    approved_by: str | None = None
    comment: str | None = None
    write_intent: StyleDNAPersistenceWriteIntent | None = None
    write_permission_ready_for_future: bool = False
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
        intent_data = self.write_intent.to_dict() if self.write_intent else {}
        return {
            "gate_id": self.gate_id,
            "job_id": self.job_id,
            "source_apply_plan_id": self.source_apply_plan_id,
            "requested_status": self.requested_status,
            "status": self.status,
            "approved_by": self.approved_by,
            "comment": self.comment,
            "write_intent": intent_data,
            "write_permission_ready_for_future": bool(
                self.write_permission_ready_for_future
            ),
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
    def from_dict(cls, data: dict[str, Any]) -> "StyleDNAPersistenceGate":
        source = normalize_dict(data)
        intent_data = normalize_dict(source.get("write_intent"))
        intent = (
            StyleDNAPersistenceWriteIntent.from_dict(intent_data)
            if intent_data
            else None
        )
        return cls(
            gate_id=normalize_text(source.get("gate_id")),
            job_id=normalize_text(source.get("job_id")),
            source_apply_plan_id=source.get("source_apply_plan_id"),
            requested_status=normalize_text(
                source.get("requested_status"),
                REQUEST_STATUS_PENDING_WRITE_REVIEW,
            ),
            status=normalize_text(
                source.get("status"),
                STYLE_DNA_PERSISTENCE_STATUS_PENDING_WRITE_REVIEW,
            ),
            approved_by=source.get("approved_by"),
            comment=source.get("comment"),
            write_intent=intent,
            write_permission_ready_for_future=normalize_bool(
                source.get("write_permission_ready_for_future"),
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


@dataclass
class StyleDNAPersistenceGateReport:
    report_id: str
    job_id: str
    status: str
    gate: StyleDNAPersistenceGate | None = None
    source_apply_plan_status: str | None = None
    source_operation_count: int = 0
    write_permission_ready_for_future: bool = False
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
        gate_data = self.gate.to_dict() if self.gate else {}
        return {
            "report_id": self.report_id,
            "job_id": self.job_id,
            "status": self.status,
            "gate": gate_data,
            "source_apply_plan_status": self.source_apply_plan_status,
            "source_operation_count": int(self.source_operation_count),
            "write_permission_ready_for_future": bool(
                self.write_permission_ready_for_future
            ),
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
    def from_dict(cls, data: dict[str, Any]) -> "StyleDNAPersistenceGateReport":
        source = normalize_dict(data)
        gate_data = normalize_dict(source.get("gate"))
        gate = StyleDNAPersistenceGate.from_dict(gate_data) if gate_data else None
        return cls(
            report_id=normalize_text(source.get("report_id")),
            job_id=normalize_text(source.get("job_id")),
            status=normalize_text(
                source.get("status"),
                STYLE_DNA_PERSISTENCE_STATUS_PENDING_WRITE_REVIEW,
            ),
            gate=gate,
            source_apply_plan_status=source.get("source_apply_plan_status"),
            source_operation_count=normalize_int(
                source.get("source_operation_count"),
                0,
            ),
            write_permission_ready_for_future=normalize_bool(
                source.get("write_permission_ready_for_future"),
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
