from __future__ import annotations

from core.opportunity_scorer import OpportunityScorer
from core.opportunity_store import OpportunityStore
from core.trend_qualification_store import TrendQualificationStore
from core.trend_store import TrendStore
from models.opportunity import Opportunity
from shared.errors import ValidationError


class OpportunityManager:
    def __init__(
        self,
        trend_store: TrendStore,
        qualification_store: TrendQualificationStore,
        opportunity_store: OpportunityStore,
        opportunity_scorer: OpportunityScorer | None = None,
    ) -> None:
        self.trend_store = trend_store
        self.qualification_store = qualification_store
        self.opportunity_store = opportunity_store
        self.opportunity_scorer = opportunity_scorer or OpportunityScorer()

    def create_opportunity(self, signal_id: str) -> Opportunity:
        if not signal_id or not signal_id.strip():
            raise ValidationError("signal_id is required")

        signal = self.trend_store.get_signal(signal_id)
        qualification = self.qualification_store.get_by_signal_id(signal_id)

        opportunity = self.opportunity_scorer.score(
            signal=signal,
            qualification=qualification,
        )
        return self.opportunity_store.create_opportunity(opportunity)