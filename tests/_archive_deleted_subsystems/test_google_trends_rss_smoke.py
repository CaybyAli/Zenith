import os

from core.connectors.google_trends_rss_connector import GoogleTrendsRssConnector
from core.live_trend_intake_runner import LiveTrendIntakeRunner
from core.trend_intake_manager import TrendIntakeManager
from core.trend_store import TrendStore

rss_url = os.getenv("GOOGLE_TRENDS_RSS_URL")
if not rss_url:
    raise RuntimeError("Missing GOOGLE_TRENDS_RSS_URL environment variable")

trend_store = TrendStore()
intake_manager = TrendIntakeManager(trend_store)
runner = LiveTrendIntakeRunner(intake_manager)

source = intake_manager.register_source(
    {
        "source_type": "rss",
        "source_name": "Google Trends Trending Now RSS DE Hardening",
        "platform": "web",
        "reliability_weight": 0.85,
        "default_half_life_hours": 12,
        "metadata": {
            "connector": "google_trends_rss",
            "country_code": "DE",
            "rss_mode": "official_export_url",
        },
    }
)

connector = GoogleTrendsRssConnector(
    rss_url=rss_url,
    country_code="DE",
)

result = runner.import_from_connector(
    source_id=source.source_id,
    connector=connector,
)

print("SOURCE:", source.to_dict())
print(
    "RESULT:",
    {
        "source_id": result["source_id"],
        "connector_name": result["connector_name"],
        "raw_fetched_count": result["raw_fetched_count"],
        "accepted_count": result["accepted_count"],
        "filtered_out_count": result["filtered_out_count"],
        "imported_count": result["imported_count"],
        "failed_count": result["failed_count"],
    },
)

for skipped in result["skipped_items"][:5]:
    print("SKIPPED:", skipped)

for signal in result["signals"][:3]:
    print("SIGNAL:", signal.to_dict())