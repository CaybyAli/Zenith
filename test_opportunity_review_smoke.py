from core.opportunity_review_manager import OpportunityReviewManager
from core.opportunity_review_store import OpportunityReviewStore
from core.opportunity_store import OpportunityStore
from core.trend_qualification_store import TrendQualificationStore
from core.trend_store import TrendStore

trend_store = TrendStore()
qualification_store = TrendQualificationStore()
opportunity_store = OpportunityStore()
review_store = OpportunityReviewStore()

manager = OpportunityReviewManager(
    trend_store=trend_store,
    qualification_store=qualification_store,
    opportunity_store=opportunity_store,
    review_store=review_store,
)

opportunities = opportunity_store.list_opportunities()
if not opportunities:
    raise RuntimeError("No opportunities found. Run test_opportunity_smoke.py first.")

opportunity = opportunities[0]
review_view = manager.create_review_view(opportunity.opportunity_id)
sorted_reviews = manager.list_review_views(sort_by="opportunity_score", descending=True)

print("OPPORTUNITY:", opportunity.to_dict())
print("REVIEW_VIEW:", review_view.to_dict())
print("SORTED_REVIEW_COUNT:", len(sorted_reviews))