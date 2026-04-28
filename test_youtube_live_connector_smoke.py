import os

from core.connectors.youtube_most_popular_connector import YouTubeMostPopularConnector
from core.live_trend_intake_runner import LiveTrendIntakeRunner
from core.trend_intake_manager import TrendIntakeManager
from core.trend_store import TrendStore

api_key = os.getenv("YOUTUBE_API_KEY")
if not api_key:
    raise RuntimeError("Missing YOUTUBE_API_KEY environment variable")

trend_store = TrendStore()
intake_manager = TrendIntakeManager(trend_store)
runner = LiveTrendIntakeRunner(intake_manager)

source = intake_manager.register_source(
    {
        "source_type": "api",
        "source_name": "YouTube Most Popular DE Gaming",
        "platform": "youtube",
        "reliability_weight": 0.9,
        "default_half_life_hours": 24,
        "metadata": {
            "connector": "youtube_most_popular",
            "region_code": "DE",
            "video_category_id": "20",
            "strict_category_match": True,
        },
    }
)

connector = YouTubeMostPopularConnector(
    api_key=api_key,
    region_code="DE",
    video_category_id="20",
    max_results=10,
    strict_category_match=True,
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