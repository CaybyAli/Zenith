from __future__ import annotations

from typing import Any

from core.trend_normalizer import TrendNormalizer
from core.trend_store import TrendStore
from models.trend_signal import TrendSignal
from models.trend_source import TrendSource
from shared.errors import ValidationError


class TrendIntakeManager:
    def __init__(
        self,
        trend_store: TrendStore,
        trend_normalizer: TrendNormalizer | None = None,
    ) -> None:
        self.trend_store = trend_store
        self.trend_normalizer = trend_normalizer or TrendNormalizer()

    def register_source(self, raw_source: dict[str, Any] | TrendSource) -> TrendSource:
        source = self.trend_normalizer.normalize_source(raw_source)

        if not source.source_name.strip():
            raise ValidationError("Trend source name is required")

        return self.trend_store.create_source(source)

    def ingest_signal(
        self,
        *,
        source_id: str,
        raw_signal: dict[str, Any],
    ) -> TrendSignal:
        if not source_id or not source_id.strip():
            raise ValidationError("source_id is required")

        if not isinstance(raw_signal, dict) or not raw_signal:
            raise ValidationError("raw_signal must be a non-empty dict")

        source = self.trend_store.get_source(source_id)
        if not source.enabled:
            raise ValidationError(f"Trend source is disabled: {source_id}")

        signal = self.trend_normalizer.normalize_signal(
            source=source,
            raw_signal=raw_signal,
        )
        return self.trend_store.create_signal(signal)