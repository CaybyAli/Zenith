from __future__ import annotations

from uuid import uuid4

from models.comparison_view_summary import ComparisonViewSummary
from models.insight_summary import InsightSummary
from models.kpi_view_entry import KpiViewEntry


class InsightSurfaceBuilder:
    def build_insights(
        self,
        entries: list[KpiViewEntry],
        comparison_summaries: list[ComparisonViewSummary],
    ) -> list[InsightSummary]:
        insights: list[InsightSummary] = []

        insights.extend(self._build_winner_loser_insights(entries))
        insights.extend(self._build_comparison_insights(comparison_summaries))

        return insights

    def _build_winner_loser_insights(
        self,
        entries: list[KpiViewEntry],
    ) -> list[InsightSummary]:
        if not entries:
            return []

        sorted_entries = sorted(
            entries,
            key=lambda item: item.performance_score or 0.0,
            reverse=True,
        )

        winner = sorted_entries[0]
        loser = sorted_entries[-1]

        insights: list[InsightSummary] = []

        insights.append(
            InsightSummary(
                insight_id=f"ins_{uuid4().hex[:12]}",
                insight_type="winner",
                title="Top performer detected",
                summary_text=(
                    f"Variant {winner.variant_id} on "
                    f"{winner.target_platform.value} currently leads with "
                    f"performance score {winner.performance_score}."
                ),
                severity="info",
                related_variant_ids=[winner.variant_id],
                related_platforms=[winner.target_platform.value],
                related_channels=[winner.channel_type.value],
                metadata={
                    "rank_overall": winner.rank_overall,
                    "performance_score": winner.performance_score,
                },
            )
        )

        if len(sorted_entries) > 1:
            insights.append(
                InsightSummary(
                    insight_id=f"ins_{uuid4().hex[:12]}",
                    insight_type="loser",
                    title="Low performer detected",
                    summary_text=(
                        f"Variant {loser.variant_id} on "
                        f"{loser.target_platform.value} is currently lowest with "
                        f"performance score {loser.performance_score}."
                    ),
                    severity="warning",
                    related_variant_ids=[loser.variant_id],
                    related_platforms=[loser.target_platform.value],
                    related_channels=[loser.channel_type.value],
                    metadata={
                        "rank_overall": loser.rank_overall,
                        "performance_score": loser.performance_score,
                    },
                )
            )

        return insights

    def _build_comparison_insights(
        self,
        comparison_summaries: list[ComparisonViewSummary],
    ) -> list[InsightSummary]:
        insights: list[InsightSummary] = []

        for summary in comparison_summaries:
            insights.append(
                InsightSummary(
                    insight_id=f"ins_{uuid4().hex[:12]}",
                    insight_type=f"{summary.comparison_type}_comparison",
                    title=(
                        f"{summary.comparison_type.title()} comparison: "
                        f"{summary.comparison_key}"
                    ),
                    summary_text=summary.summary_text or "",
                    severity="info",
                    related_variant_ids=[
                        variant_id
                        for variant_id in [
                            summary.winner_variant_id,
                            summary.loser_variant_id,
                        ]
                        if variant_id
                    ],
                    metadata={
                        "comparison_type": summary.comparison_type,
                        "comparison_key": summary.comparison_key,
                        "winner_score": summary.winner_score,
                        "loser_score": summary.loser_score,
                        "average_score": summary.average_score,
                        "item_count": summary.item_count,
                    },
                )
            )

        return insights