from __future__ import annotations

from uuid import uuid4

from models.feedback_pattern_summary import FeedbackPatternSummary
from models.feedback_record import FeedbackRecord


class FeedbackAggregationService:
    def build_pattern_summaries(
        self,
        feedback_records: list[FeedbackRecord],
    ) -> list[FeedbackPatternSummary]:
        grouped: dict[tuple[str, str], list[FeedbackRecord]] = {}

        for record in feedback_records:
            key = (record.feedback_category, record.feedback_direction)
            grouped.setdefault(key, []).append(record)

        summaries: list[FeedbackPatternSummary] = []

        for (category, direction), records in grouped.items():
            channels = sorted(
                {
                    record.channel_type.value
                    for record in records
                }
            )
            platforms = sorted(
                {
                    record.target_platform.value
                    for record in records
                    if record.target_platform is not None
                }
            )
            variant_ids = sorted(
                {
                    record.variant_id
                    for record in records
                    if record.variant_id
                }
            )

            summaries.append(
                FeedbackPatternSummary(
                    summary_id=f"fbsum_{uuid4().hex[:12]}",
                    category=category,
                    direction=direction,
                    item_count=len(records),
                    channels=channels,
                    platforms=platforms,
                    variant_ids=variant_ids,
                    summary_text=(
                        f"Feedback pattern {category}/{direction} appears "
                        f"{len(records)} time(s) across {len(channels)} channel(s) "
                        f"and {len(platforms)} platform(s)."
                    ),
                    metadata={
                        "authors": sorted(
                            {
                                record.author_source
                                for record in records
                            }
                        ),
                        "severities": sorted(
                            {
                                record.severity
                                for record in records
                            }
                        ),
                        "feedback_ids": [
                            record.feedback_id for record in records
                        ],
                    },
                )
            )

        summaries.sort(
            key=lambda item: (item.item_count, item.category, item.direction),
            reverse=True,
        )
        return summaries