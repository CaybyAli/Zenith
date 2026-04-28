from __future__ import annotations

import shutil
from pathlib import Path

from core.feedback_context_bridge import FeedbackContextBridge
from core.feedback_repository import FeedbackRepository
from models.insight_summary import InsightSummary
from models.performance_attribution_snapshot import (
    PerformanceAttributionSnapshot,
)
from shared.enums import ChannelType, PlatformType


def run() -> None:
    test_dir = Path("tmp/feedback_context_bridge_test")

    if test_dir.exists():
        shutil.rmtree(test_dir)

    test_dir.mkdir(parents=True, exist_ok=True)

    bridge = FeedbackContextBridge()
    repository = FeedbackRepository()

    attribution_snapshot = PerformanceAttributionSnapshot(
        attribution_id="attrib_feedback_bridge_001",
        metrics_snapshot_id="metrics_feedback_bridge_001",
        job_id="job_feedback_bridge_001",
        variant_id="variant_feedback_bridge_001",
        target_platform=PlatformType.YOUTUBE,
        channel_type=ChannelType.GAMING_MAIN,
        platform_video_id="yt_feedback_bridge_001",
        publish_reference={
            "platform": "youtube",
            "publish_status": "published",
            "backend_name": "youtube",
        },
        variant_kind="platform_variant",
        packaging_profile="youtube",
        subtitle_style="youtube_standard",
        metadata_context_snapshot={
            "title": "Bridge Test Title",
            "description": "Bridge test description",
            "hashtags": ["#bridge", "#feedback"],
        },
        policy_snapshot={
            "title_mode": "youtube_title",
            "subtitle_style": "youtube_standard",
        },
        publish_status="published",
        guard_status="allow",
        published_at="2026-04-15T17:00:00+00:00",
        synced_at="2026-04-15T18:00:00+00:00",
    )

    insight_summary = InsightSummary(
        insight_id="insight_feedback_bridge_001",
        insight_type="winner",
        title="Top performer detected",
        summary_text="Variant is currently above average.",
        severity="info",
    )

    record = bridge.create_feedback_from_attribution(
        storage_path=str(test_dir),
        attribution_snapshot=attribution_snapshot,
        feedback_category="subtitle_style",
        feedback_direction="improvement_request",
        feedback_text="Use less subtitle movement next time.",
        insight_summary=insight_summary,
        author_source="user",
        severity="high",
        learning_tags=["subtitle_style", "motion"],
        extra_context={"manual_label": "important"},
    )

    records = repository.load_records(str(test_dir))
    assert len(records) == 1, "Expected 1 feedback record"

    stored = records[0]
    assert stored.feedback_id == record.feedback_id
    assert stored.job_id == "job_feedback_bridge_001"
    assert stored.variant_id == "variant_feedback_bridge_001"
    assert stored.target_platform == PlatformType.YOUTUBE
    assert stored.channel_type == ChannelType.GAMING_MAIN
    assert stored.feedback_category == "subtitle_style"
    assert stored.feedback_direction == "improvement_request"
    assert stored.metrics_snapshot_id == "metrics_feedback_bridge_001"
    assert stored.attribution_id == "attrib_feedback_bridge_001"
    assert stored.insight_reference == "insight_feedback_bridge_001"
    assert stored.severity == "high"

    assert stored.context_snapshot["packaging_profile"] == "youtube"
    assert stored.context_snapshot["subtitle_style"] == "youtube_standard"
    assert stored.context_snapshot["publish_status"] == "published"
    assert stored.context_snapshot["guard_status"] == "allow"
    assert stored.context_snapshot["manual_label"] == "important"
    assert stored.context_snapshot["insight_summary"]["title"] == "Top performer detected"

    print("FEEDBACK CONTEXT BRIDGE SMOKE TEST PASSED")
    print(
        {
            "records": len(records),
            "feedback_id": stored.feedback_id,
            "variant_id": stored.variant_id,
            "test_dir": str(test_dir),
        }
    )


if __name__ == "__main__":
    run()