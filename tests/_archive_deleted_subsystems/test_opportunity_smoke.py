from core.opportunity_manager import OpportunityManager
from core.opportunity_store import OpportunityStore
from core.trend_qualification_store import TrendQualificationStore
from core.trend_store import TrendStore

trend_store = TrendStore()
qualification_store = TrendQualificationStore()
opportunity_store = OpportunityStore()

manager = OpportunityManager(
    trend_store=trend_store,
    qualification_store=qualification_store,
    opportunity_store=opportunity_store,
)

signals = trend_store.list_signals()
if not signals:
    raise RuntimeError("No trend signals found. Run test_trend_smoke.py first.")

signal = signals[0]
qualification = qualification_store.get_by_signal_id(signal.signal_id)
opportunity = manager.create_opportunity(signal.signal_id)

print("SIGNAL:", signal.to_dict())
print("QUALIFICATION:", qualification.to_dict())
print("OPPORTUNITY:", opportunity.to_dict())