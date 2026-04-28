from __future__ import annotations

import shutil
from pathlib import Path

from core.feedback_aggregation_service import FeedbackAggregationService
from core.feedback_manager import FeedbackManager
from core.feedback_repository import FeedbackRepository
from shared.enums import ChannelType, PlatformType


def run() -> None:
    test_dir = Path("tmp/feedback_learning_backbone_test")

    if test_dir.exists():
        shutil.rmtree(test_dir)

    test_dir.mkdir(parents=True, exist_ok=True)

    manager = FeedbackManager()
    repository = FeedbackRepository()
    aggregation_service = FeedbackAggregationService()

    manager.create_feedback_record(
        storage_path=str(test_dir),
        job_id="job_feedback_001",
        channel_type=ChannelType.GAMING_MAIN,
        variant_id="variant_feedback_001",
        target_platform=PlatformType.YOUTUBE,
        feedback_category="subtitle_style",
        feedback_direction="negative",
        feedback_text="Subtitle style is too hectic.",
        author_source="user",
        severity="normal",
        metrics_snapshot_id="metrics_feedback_001",
        attribution_id="attrib_feedback_001",
        insight_reference="insight_feedback_001",
        context_snapshot={
            "packaging_profile": "youtube",
            "subtitle_style": "youtube_standard",
        },
        learning_tags=["subtitles", "pacing"],
    )

    manager.create_feedback_record(
        storage_path=str(test_dir),
        job_id="job_feedback_002",
        channel_type=ChannelType.GAMING_UNCUT,
        variant_id="variant_feedback_002",
        target_platform=PlatformType.TIKTOK,
        feedback_category="hook",
        feedback_direction="positive",
        feedback_text="Hook was strong and immediate.",
        author_source="user",
        severity="normal",
        metrics_snapshot_id="metrics_feedback_002",
        attribution_id="attrib_feedback_002",
        insight_reference="insight_feedback_002",
        context_snapshot={
            "packaging_profile": "tiktok",
            "subtitle_style": "short_burned_in",
        },
        learning_tags=["hook", "opening"],
    )

    manager.create_feedback_record(
        storage_path=str(test_dir),
        job_id="job_feedback_003",
        channel_type=ChannelType.GAMING_MAIN,
        variant_id="variant_feedback_003",
        target_platform=PlatformType.YOUTUBE,
        feedback_category="subtitle_style",
        feedback_direction="negative",
        feedback_text="Less subtitle motion please.",
        author_source="user",
        severity="high",
        metrics_snapshot_id="metrics_feedback_003",
        attribution_id="attrib_feedback_003",
        insight_reference="insight_feedback_003",
        context_snapshot={
            "packaging_profile": "youtube",
            "subtitle_style": "youtube_standard",
        },
        learning_tags=["subtitles", "motion"],
    )

    records = repository.load_records(str(test_dir))
    summaries = aggregation_service.build_pattern_summaries(records)

    assert len(records) == 3, "Expected 3 feedback records"
    assert len(summaries) >= 2, "Expected at least 2 feedback pattern summaries"

    subtitle_negative = next(
        summary
        for summary in summaries
        if summary.category == "subtitle_style"
        and summary.direction == "negative"
    )
    assert subtitle_negative.item_count == 2
    assert "gaming_main" in subtitle_negative.channels
    assert "youtube" in subtitle_negative.platforms

    hook_positive = next(
        summary
        for summary in summaries
        if summary.category == "hook"
        and summary.direction == "positive"
    )
    assert hook_positive.item_count == 1
    assert "gaming_uncut" in hook_positive.channels
    assert "tiktok" in hook_positive.platforms

    print("FEEDBACK LEARNING BACKBONE SMOKE TEST PASSED")
    print(
        {
            "records": len(records),
            "summaries": len(summaries),
            "top_summary_category": summaries[0].category,
            "top_summary_direction": summaries[0].direction,
            "test_dir": str(test_dir),
        }
    )


if __name__ == "__main__":
    run()