from __future__ import annotations

from uuid import uuid4

from models.comparison_view_summary import ComparisonViewSummary
from models.kpi_view_entry import KpiViewEntry


class ComparisonViewBuilder:
    def build_all_summaries(
        self,
        entries: list[KpiViewEntry],
    ) -> list[ComparisonViewSummary]:
        summaries: list[ComparisonViewSummary] = []
        summaries.extend(self.build_grouped_summaries(entries, "platform"))
        summaries.extend(self.build_grouped_summaries(entries, "channel"))
        summaries.extend(self.build_grouped_summaries(entries, "packaging_profile"))
        summaries.extend(self.build_grouped_summaries(entries, "subtitle_style"))
        return summaries

    def build_grouped_summaries(
        self,
        entries: list[KpiViewEntry],
        comparison_type: str,
    ) -> list[ComparisonViewSummary]:
        groups: dict[str, list[KpiViewEntry]] = {}

        for entry in entries:
            group_key = self._resolve_group_key(entry, comparison_type)
            if not group_key:
                continue
            groups.setdefault(group_key, []).append(entry)

        summaries: list[ComparisonViewSummary] = []

        for group_key, grouped_entries in groups.items():
            grouped_entries.sort(
                key=lambda item: item.performance_score or 0.0,
                reverse=True,
            )

            winner = grouped_entries[0]
            loser = grouped_entries[-1]

            scores = [
                entry.performance_score or 0.0
                for entry in grouped_entries
            ]
            average_score = round(sum(scores) / len(scores), 2) if scores else None

            summary = ComparisonViewSummary(
                comparison_id=f"cmp_{uuid4().hex[:12]}",
                comparison_type=comparison_type,
                comparison_key=group_key,
                item_count=len(grouped_entries),
                winner_variant_id=winner.variant_id,
                loser_variant_id=loser.variant_id,
                winner_label=f"{group_key}:{winner.variant_id}",
                loser_label=f"{group_key}:{loser.variant_id}",
                winner_score=winner.performance_score,
                loser_score=loser.performance_score,
                average_score=average_score,
                summary_text=(
                    f"{comparison_type}={group_key} has {len(grouped_entries)} "
                    f"entries. Winner {winner.variant_id} scored "
                    f"{winner.performance_score}, loser {loser.variant_id} "
                    f"scored {loser.performance_score}."
                ),
                metadata={
                    "comparison_type": comparison_type,
                    "comparison_key": group_key,
                    "variant_ids": [entry.variant_id for entry in grouped_entries],
                },
            )
            summaries.append(summary)

        return summaries

    def _resolve_group_key(
        self,
        entry: KpiViewEntry,
        comparison_type: str,
    ) -> str | None:
        if comparison_type == "platform":
            return entry.target_platform.value

        if comparison_type == "channel":
            return entry.channel_type.value

        if comparison_type == "packaging_profile":
            return entry.packaging_profile

        if comparison_type == "subtitle_style":
            return entry.subtitle_style

        raise ValueError(f"Unsupported comparison type: {comparison_type}")