from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from models.transition_decision import TransitionDecision, TransitionDecisionPlan


@dataclass
class TransitionDecisionRunReport:
    status: str = "skipped_no_clip_duration_recommendations"
    source: str = "transition_decision"
    transition_decision_plan: TransitionDecisionPlan | None = None
    decisions: list[TransitionDecision] = field(default_factory=list)
    decision_count: int = 0
    hard_cut_review_count: int = 0
    j_cut_review_count: int = 0
    l_cut_review_count: int = 0
    quick_fade_review_count: int = 0
    no_cut_protect_count: int = 0
    censor_safe_keep_count: int = 0
    technical_transition_review_count: int = 0
    unknown_review_count: int = 0
    recommendation: str = "transition_decision_skipped_no_inputs"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "source": self.source,
            "transition_decision_plan": (
                self.transition_decision_plan.to_dict()
                if self.transition_decision_plan is not None
                else None
            ),
            "decisions": [decision.to_dict() for decision in self.decisions],
            "decision_count": self.decision_count,
            "hard_cut_review_count": self.hard_cut_review_count,
            "j_cut_review_count": self.j_cut_review_count,
            "l_cut_review_count": self.l_cut_review_count,
            "quick_fade_review_count": self.quick_fade_review_count,
            "no_cut_protect_count": self.no_cut_protect_count,
            "censor_safe_keep_count": self.censor_safe_keep_count,
            "technical_transition_review_count": self.technical_transition_review_count,
            "unknown_review_count": self.unknown_review_count,
            "recommendation": self.recommendation,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "TransitionDecisionRunReport":
        data = data or {}

        plan_data = data.get("transition_decision_plan")
        transition_decision_plan = (
            TransitionDecisionPlan.from_dict(plan_data)
            if isinstance(plan_data, dict)
            else None
        )

        decisions = [
            TransitionDecision.from_dict(item)
            for item in data.get("decisions", []) or []
            if isinstance(item, dict)
        ]

        return cls(
            status=str(
                data.get("status", "skipped_no_clip_duration_recommendations")
            ),
            source=str(data.get("source", "transition_decision")),
            transition_decision_plan=transition_decision_plan,
            decisions=decisions,
            decision_count=int(data.get("decision_count", len(decisions))),
            hard_cut_review_count=int(data.get("hard_cut_review_count", 0)),
            j_cut_review_count=int(data.get("j_cut_review_count", 0)),
            l_cut_review_count=int(data.get("l_cut_review_count", 0)),
            quick_fade_review_count=int(data.get("quick_fade_review_count", 0)),
            no_cut_protect_count=int(data.get("no_cut_protect_count", 0)),
            censor_safe_keep_count=int(data.get("censor_safe_keep_count", 0)),
            technical_transition_review_count=int(
                data.get("technical_transition_review_count", 0)
            ),
            unknown_review_count=int(data.get("unknown_review_count", 0)),
            recommendation=str(
                data.get("recommendation", "transition_decision_skipped_no_inputs")
            ),
            warnings=list(data.get("warnings", []) or []),
            errors=list(data.get("errors", []) or []),
            metadata=dict(data.get("metadata", {}) or {}),
        )
