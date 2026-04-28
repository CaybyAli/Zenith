from __future__ import annotations

from models.opportunity import Opportunity
from models.opportunity_review_view import OpportunityReviewView
from models.trend_qualification import TrendQualification
from models.trend_signal import TrendSignal
from shared.opportunity_review_enums import OpportunityReviewStatus
from shared.trend_qualification_enums import DecisionHint


class OpportunityReviewBuilder:
    def build(
        self,
        *,
        signal: TrendSignal,
        qualification: TrendQualification,
        opportunity: Opportunity,
    ) -> OpportunityReviewView:
        topic_label = self._derive_topic_label(signal)
        review_status = self._derive_initial_review_status(qualification.decision_hint)
        upside_preview = list(opportunity.upside_factors[:3])
        downside_preview = list(opportunity.downside_factors[:3])

        review_summary = self._build_review_summary(
            topic_label=topic_label,
            opportunity=opportunity,
            qualification=qualification,
            review_status=review_status,
            upside_preview=upside_preview,
            downside_preview=downside_preview,
        )

        return OpportunityReviewView.from_dict(
            {
                "signal_id": signal.signal_id,
                "qualification_id": qualification.qualification_id,
                "opportunity_id": opportunity.opportunity_id,
                "topic_label": topic_label,
                "platform": signal.platform.value,
                "primary_channel": opportunity.primary_channel,
                "opportunity_score": opportunity.opportunity_score,
                "opportunity_level": opportunity.opportunity_level.value,
                "upside_preview": upside_preview,
                "downside_preview": downside_preview,
                "risk_flags": list(qualification.risk_flags),
                "lifespan_class": qualification.lifespan_class.value,
                "review_status": review_status.value,
                "review_summary": review_summary,
            }
        )

    def _derive_topic_label(self, signal: TrendSignal) -> str:
        candidates = [
            signal.topic,
            signal.raw_label,
            signal.normalized_label,
            signal.raw_payload.get("title"),
            signal.raw_payload.get("topic"),
        ]

        for candidate in candidates:
            text = str(candidate).strip() if candidate is not None else ""
            if text:
                return text

        return signal.signal_id

    def _derive_initial_review_status(
        self,
        decision_hint: DecisionHint,
    ) -> OpportunityReviewStatus:
        if decision_hint == DecisionHint.BLOCK:
            return OpportunityReviewStatus.REJECTED
        if decision_hint == DecisionHint.WATCH:
            return OpportunityReviewStatus.WATCH
        return OpportunityReviewStatus.PENDING

    def _build_review_summary(
        self,
        *,
        topic_label: str,
        opportunity: Opportunity,
        qualification: TrendQualification,
        review_status: OpportunityReviewStatus,
        upside_preview: list[str],
        downside_preview: list[str],
    ) -> str:
        primary_channel = opportunity.primary_channel or "none"
        upside_text = ", ".join(upside_preview) if upside_preview else "none"
        downside_text = ", ".join(downside_preview) if downside_preview else "none"

        return (
            f"{topic_label} | score {opportunity.opportunity_score:.2f} "
            f"({opportunity.opportunity_level.value}) | primary {primary_channel} | "
            f"lifespan {qualification.lifespan_class.value} | status {review_status.value} | "
            f"upside {upside_text} | downside {downside_text}"
        )