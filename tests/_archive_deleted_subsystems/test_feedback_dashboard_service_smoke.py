from __future__ import annotations

import shutil
from pathlib import Path

from core.feedback_dashboard_service import FeedbackDashboardService
from core.feedback_repository import FeedbackRepository
from models.feedback_record import FeedbackRecord
from shared.enums import ChannelType, PlatformType


def run() -> None:
    test_dir = Path("tmp/feedback_dashboard_service_test")

    if test_dir.exists():
        shutil.rmtree(test_dir)

    (test_dir / "gaming_main" / "job_feedback_dash_001").mkdir(
        parents=True,
        exist_ok=True,
    )
    (test_dir / "gaming_uncut" / "job_feedback_dash_002").mkdir(
        parents=True,
        exist_ok=True,
    )

    repository = FeedbackRepository()
    service = FeedbackDashboardService()

    export_path_1 = str(test_dir / "gaming_main" / "job_feedback_dash_001")
    export_path_2 = str(test_dir / "gaming_uncut" / "job_feedback_dash_002")

    repository.save_records(
        storage_path=export_path_1,
        records=[
            FeedbackRecord(
                feedback_id="fb_dash_001",
                job_id="job_feedback_dash_001",
                channel_type=ChannelType.GAMING_MAIN,
                variant_id="variant_feedback_dash_001",
                target_platform=PlatformType.YOUTUBE,
                feedback_category="subtitle_style",
                feedback_direction="negative",
                feedback_text="Subtitle movement is too hectic.",
                author_source="user",
                severity="high",
                metrics_snapshot_id="metrics_dash_001",
                attribution_id="attrib_dash_001",
                insight_reference="insight_dash_001",
                context_snapshot={
                    "packaging_profile": "youtube",
                    "subtitle_style": "youtube_standard",
                },
                learning_tags=["subtitles", "motion"],
            )
        ],
    )

    repository.save_records(
        storage_path=export_path_2,
        records=[
            FeedbackRecord(
                feedback_id="fb_dash_002",
                job_id="job_feedback_dash_002",
                channel_type=ChannelType.GAMING_UNCUT,
                variant_id="variant_feedback_dash_002",
                target_platform=PlatformType.TIKTOK,
                feedback_category="hook",
                feedback_direction="positive",
                feedback_text="Hook was strong and immediate.",
                author_source="user",
                severity="normal",
                metrics_snapshot_id="metrics_dash_002",
                attribution_id="attrib_dash_002",
                insight_reference="insight_dash_002",
                context_snapshot={
                    "packaging_profile": "tiktok",
                    "subtitle_style": "short_burned_in",
                },
                learning_tags=["hook", "opening"],
            )
        ],
    )

    surface = service.build_surface(base_path=str(test_dir))

    assert surface["total_records"] == 2, "Expected 2 feedback records"
    assert len(surface["recent_feedback"]) == 2, "Expected 2 recent feedback entries"
    assert len(surface["pattern_summaries"]) >= 2, "Expected pattern summaries"
    assert len(surface["category_stats"]) >= 2, "Expected category stats"
    assert len(surface["direction_stats"]) >= 2, "Expected direction stats"

    categories = [item["category"] for item in surface["category_stats"]]
    assert "subtitle_style" in categories
    assert "hook" in categories

    directions = [item["direction"] for item in surface["direction_stats"]]
    assert "negative" in directions
    assert "positive" in directions

    assert surface["recent_feedback"][0]["feedback_id"] in {
        "fb_dash_001",
        "fb_dash_002",
    }

    print("FEEDBACK DASHBOARD SERVICE SMOKE TEST PASSED")
    print(
        {
            "total_records": surface["total_records"],
            "pattern_summaries": len(surface["pattern_summaries"]),
            "category_stats": len(surface["category_stats"]),
            "direction_stats": len(surface["direction_stats"]),
        }
    )


if __name__ == "__main__":
    run()