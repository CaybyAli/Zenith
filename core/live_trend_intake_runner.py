from __future__ import annotations

from typing import Any

from core.trend_intake_manager import TrendIntakeManager
from core.trend_source_connector import TrendSourceConnector
from models.trend_signal import TrendSignal
from shared.errors import ValidationError


class LiveTrendIntakeRunner:
    def __init__(self, intake_manager: TrendIntakeManager) -> None:
        self.intake_manager = intake_manager

    def import_from_connector(
        self,
        *,
        source_id: str,
        connector: TrendSourceConnector,
    ) -> dict[str, Any]:
        if not source_id or not source_id.strip():
            raise ValidationError("source_id is required")

        raw_items = connector.fetch_items()
        connector_stats = getattr(connector, "last_fetch_stats", {}) or {}

        imported_signals: list[TrendSignal] = []
        failures: list[dict[str, Any]] = []

        for index, raw_signal in enumerate(raw_items, start=1):
            try:
                signal = self.intake_manager.ingest_signal(
                    source_id=source_id,
                    raw_signal=raw_signal,
                )
                imported_signals.append(signal)
            except Exception as exc:
                failures.append(
                    {
                        "index": index,
                        "title": raw_signal.get("title") or raw_signal.get("topic"),
                        "error": str(exc),
                    }
                )

        return {
            "source_id": source_id,
            "connector_name": connector.connector_name,
            "raw_fetched_count": int(connector_stats.get("raw_count", len(raw_items))),
            "accepted_count": int(connector_stats.get("mapped_count", len(raw_items))),
            "filtered_out_count": int(connector_stats.get("skipped_count", 0)),
            "skipped_items": list(connector_stats.get("skipped_items", [])),
            "imported_count": len(imported_signals),
            "failed_count": len(failures),
            "failures": failures,
            "signals": imported_signals,
        }