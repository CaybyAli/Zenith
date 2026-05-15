from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


STYLE_DNA_STATUS_WAITING = "style_dna_update_waiting_for_feedback"
STYLE_DNA_STATUS_DRAFT_READY = "style_dna_update_draft_ready"
STYLE_DNA_STATUS_DRAFT_READY_WITH_WARNINGS = "style_dna_update_draft_ready_with_warnings"
STYLE_DNA_STATUS_BLOCKED = "style_dna_update_blocked"
STYLE_DNA_STATUS_FAILED = "style_dna_update_failed"

IMPACT_LOW = "low"
IMPACT_MEDIUM = "medium"
IMPACT_HIGH = "high"

OVERFITTING_RISK_LOW = "low"
OVERFITTING_RISK_MEDIUM = "medium"
OVERFITTING_RISK_HIGH = "high"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def normalize_text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    if not isinstance(value, list):
        return []
    items: list[str] = []
    for item in value:
        text = normalize_text(item)
        if text:
            items.append(text)
    return items


def normalize_float(value: Any, default: float = 0.0) -> float:
    try:
        return round(float(value), 3)
    except (TypeError, ValueError):
        return default


def normalize_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return bool(value)


def normalize_impact(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {IMPACT_LOW, IMPACT_MEDIUM, IMPACT_HIGH}:
        return text
    return IMPACT_LOW


def normalize_overfitting_risk(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text in {OVERFITTING_RISK_LOW, OVERFITTING_RISK_MEDIUM, OVERFITTING_RISK_HIGH}:
        return text
    return OVERFITTING_RISK_MEDIUM


@dataclass
class StyleDNAParameterProposal:
    proposal_id: str | None = None
    parameter_name: str | None = None
    current_value: Any = None
    proposed_value: Any = None
    delta: Any = None
    reason: str | None = None
    source_tags: list[str] = field(default_factory=list)
    confidence: float = 0.0
    impact: str = IMPACT_LOW
    safe_to_apply_later: bool = False
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "StyleDNAParameterProposal":
        data = dict(data or {})
        return cls(
            proposal_id=normalize_text(data.get("proposal_id")),
            parameter_name=normalize_text(data.get("parameter_name")),
            current_value=data.get("current_value"),
            proposed_value=data.get("proposed_value"),
            delta=data.get("delta"),
            reason=normalize_text(data.get("reason")),
            source_tags=normalize_text_list(data.get("source_tags")),
            confidence=normalize_float(data.get("confidence"), 0.0),
            impact=normalize_impact(data.get("impact")),
            safe_to_apply_later=normalize_bool(data.get("safe_to_apply_later"), False),
            warnings=list(data.get("warnings") or []),
            blocking_reasons=list(data.get("blocking_reasons") or []),
            metadata=dict(data.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class StyleDNAUpdateDraft:
    draft_id: str | None = None
    profile: str = "gaming_main"
    source_feedback_report_id: str | None = None
    proposals: list[StyleDNAParameterProposal] = field(default_factory=list)
    proposal_count: int = 0
    confidence: float = 0.0
    overfitting_risk: str = OVERFITTING_RISK_MEDIUM
    safe_to_review: bool = False
    warnings: list[str] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "StyleDNAUpdateDraft":
        data = dict(data or {})
        proposals = [
            StyleDNAParameterProposal.from_dict(item)
            for item in list(data.get("proposals") or [])
            if isinstance(item, dict)
        ]
        return cls(
            draft_id=normalize_text(data.get("draft_id")),
            profile=normalize_text(data.get("profile")) or "gaming_main",
            source_feedback_report_id=normalize_text(data.get("source_feedback_report_id")),
            proposals=proposals,
            proposal_count=int(data.get("proposal_count", len(proposals)) or 0),
            confidence=normalize_float(data.get("confidence"), 0.0),
            overfitting_risk=normalize_overfitting_risk(data.get("overfitting_risk")),
            safe_to_review=normalize_bool(data.get("safe_to_review"), False),
            warnings=list(data.get("warnings") or []),
            blocking_reasons=list(data.get("blocking_reasons") or []),
            metadata=dict(data.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["proposals"] = [proposal.to_dict() for proposal in self.proposals]
        payload["proposal_count"] = len(self.proposals)
        return payload


@dataclass
class StyleDNAFeedbackUpdateReport:
    report_id: str | None = None
    job_id: str | None = None
    status: str = STYLE_DNA_STATUS_WAITING
    profile: str = "gaming_main"
    source_feedback_status: str | None = None
    draft: StyleDNAUpdateDraft | None = None
    proposal_count: int = 0
    accepted_feedback_count: int = 0
    rejected_feedback_count: int = 0
    confidence: float = 0.0
    ready_for_human_review: bool = False
    ready_for_later_apply: bool = False
    can_write_style_dna: bool = False
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

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "StyleDNAFeedbackUpdateReport":
        data = dict(data or {})
        draft_data = data.get("draft")
        return cls(
            report_id=normalize_text(data.get("report_id")),
            job_id=normalize_text(data.get("job_id")),
            status=normalize_text(data.get("status")) or STYLE_DNA_STATUS_WAITING,
            profile=normalize_text(data.get("profile")) or "gaming_main",
            source_feedback_status=normalize_text(data.get("source_feedback_status")),
            draft=(
                StyleDNAUpdateDraft.from_dict(draft_data)
                if isinstance(draft_data, dict)
                else None
            ),
            proposal_count=int(data.get("proposal_count", 0) or 0),
            accepted_feedback_count=int(data.get("accepted_feedback_count", 0) or 0),
            rejected_feedback_count=int(data.get("rejected_feedback_count", 0) or 0),
            confidence=normalize_float(data.get("confidence"), 0.0),
            ready_for_human_review=normalize_bool(data.get("ready_for_human_review"), False),
            ready_for_later_apply=normalize_bool(data.get("ready_for_later_apply"), False),
            can_write_style_dna=False,
            can_update_profile=False,
            can_change_cutting_rules=False,
            can_modify_timeline=False,
            can_trigger_render=False,
            can_publish=False,
            warnings=list(data.get("warnings") or []),
            blocking_reasons=list(data.get("blocking_reasons") or []),
            recommendation=normalize_text(data.get("recommendation")),
            created_at=normalize_text(data.get("created_at")) or utc_now_iso(),
            metadata=dict(data.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["draft"] = self.draft.to_dict() if self.draft else None
        payload["can_write_style_dna"] = False
        payload["can_update_profile"] = False
        payload["can_change_cutting_rules"] = False
        payload["can_modify_timeline"] = False
        payload["can_trigger_render"] = False
        payload["can_publish"] = False
        return payload
