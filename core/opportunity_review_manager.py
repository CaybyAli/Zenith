from __future__ import annotations

from core.opportunity_review_builder import OpportunityReviewBuilder
from core.opportunity_review_store import OpportunityReviewStore
from core.opportunity_store import OpportunityStore
from core.trend_qualification_store import TrendQualificationStore
from core.trend_store import TrendStore
from models.opportunity_review_view import OpportunityReviewView
from shared.errors import ValidationError
from shared.opportunity_review_enums import OpportunityReviewStatus


class OpportunityReviewManager:
    def __init__(
        self,
        trend_store: TrendStore,
        qualification_store: TrendQualificationStore,
        opportunity_store: OpportunityStore,
        review_store: OpportunityReviewStore,
        review_builder: OpportunityReviewBuilder | None = None,
    ) -> None:
        self.trend_store = trend_store
        self.qualification_store = qualification_store
        self.opportunity_store = opportunity_store
        self.review_store = review_store
        self.review_builder = review_builder or OpportunityReviewBuilder()

    def create_review_view(self, opportunity_id: str) -> OpportunityReviewView:
        if not opportunity_id or not opportunity_id.strip():
            raise ValidationError("opportunity_id is required")

        opportunity = self.opportunity_store.get_opportunity(opportunity_id)
        signal = self.trend_store.get_signal(opportunity.signal_id)
        qualification = self.qualification_store.get_qualification(opportunity.qualification_id)

        review_view = self.review_builder.build(
            signal=signal,
            qualification=qualification,
            opportunity=opportunity,
        )
        return self.review_store.create_review_view(review_view)

    def set_review_status(
        self,
        review_view_id: str,
        review_status: str,
    ) -> OpportunityReviewView:
        if not review_view_id or not review_view_id.strip():
            raise ValidationError("review_view_id is required")

        status = self._normalize_review_status(review_status)
        review_view = self.review_store.get_review_view(review_view_id)
        review_view.review_status = status
        return self.review_store.update_review_view(review_view)

    def list_review_views(
        self,
        *,
        sort_by: str = "opportunity_score",
        descending: bool = True,
        review_status: str | None = None,
        platform: str | None = None,
        primary_channel: str | None = None,
        opportunity_level: str | None = None,
    ) -> list[OpportunityReviewView]:
        views = self.review_store.list_review_views()

        if review_status:
            wanted_status = self._normalize_review_status(review_status)
            views = [view for view in views if view.review_status == wanted_status]

        if platform:
            wanted_platform = platform.strip().lower()
            views = [view for view in views if view.platform.strip().lower() == wanted_platform]

        if primary_channel:
            wanted_channel = primary_channel.strip().lower()
            views = [
                view
                for view in views
                if (view.primary_channel or "").strip().lower() == wanted_channel
            ]

        if opportunity_level:
            wanted_level = opportunity_level.strip().lower()
            views = [view for view in views if view.opportunity_level.value == wanted_level]

        views.sort(
            key=lambda view: self._sort_value(view, sort_by),
            reverse=descending,
        )
        return views

    def _normalize_review_status(self, value: str) -> OpportunityReviewStatus:
        cleaned = value.strip().lower()

        for item in OpportunityReviewStatus:
            if item.value == cleaned:
                return item

        raise ValidationError(f"Invalid review_status: {value}")

    def _sort_value(self, view: OpportunityReviewView, sort_by: str):
        if sort_by == "opportunity_score":
            return view.opportunity_score
        if sort_by == "platform":
            return view.platform.lower()
        if sort_by == "primary_channel":
            return (view.primary_channel or "").lower()
        if sort_by == "review_status":
            order = {
                "pending": 4,
                "watch": 3,
                "approved": 2,
                "rejected": 1,
            }
            return order.get(view.review_status.value, 0)
        if sort_by == "opportunity_level":
            order = {
                "very_high": 4,
                "high": 3,
                "medium": 2,
                "low": 1,
            }
            return order.get(view.opportunity_level.value, 0)
        if sort_by == "lifespan_class":
            order = {
                "long": 4,
                "medium": 3,
                "short": 2,
                "flash": 1,
            }
            return order.get(view.lifespan_class.value, 0)

        return view.opportunity_score