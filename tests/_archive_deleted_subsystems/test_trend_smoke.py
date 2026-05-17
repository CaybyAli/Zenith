from core.trend_intake_manager import TrendIntakeManager
from core.trend_store import TrendStore

store = TrendStore()
manager = TrendIntakeManager(store)

source = manager.register_source(
    {
        "source_type": "manual",
        "source_name": "Manual Trend Notes",
        "platform": "youtube",
        "reliability_weight": 0.8,
        "default_half_life_hours": 48,
        "metadata": {
            "owner": "zenith",
        },
    }
)

signal = manager.ingest_signal(
    source_id=source.source_id,
    raw_signal={
        "title": "GTA 6 trailer reactions",
        "topic": "GTA 6 trailer reactions",
        "observed_at": "2026-04-10T12:00:00+00:00",
        "captured_at": "2026-04-10T12:30:00+00:00",
        "platform": "YT",
        "signal_strength": 0.92,
        "competition_density": 0.73,
        "confidence": 0.88,
        "half_life_hours": 48,
        "language": "de",
        "channel_targets": [" gaming_main ", "FACELESS_TREND"],
    },
)

print("SOURCE:", source.to_dict())
print("SIGNAL:", signal.to_dict())