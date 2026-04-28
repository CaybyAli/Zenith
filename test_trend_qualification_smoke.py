from core.trend_qualification_manager import TrendQualificationManager
from core.trend_qualification_store import TrendQualificationStore
from core.trend_store import TrendStore

trend_store = TrendStore()
qualification_store = TrendQualificationStore()
manager = TrendQualificationManager(
    trend_store=trend_store,
    qualification_store=qualification_store,
)

signals = trend_store.list_signals()
if not signals:
    raise RuntimeError("No trend signals found. Run test_trend_smoke.py first.")

signal = signals[0]
qualification = manager.qualify_signal(signal.signal_id)

print("SIGNAL:", signal.to_dict())
print("QUALIFICATION:", qualification.to_dict())