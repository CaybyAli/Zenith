from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from models.trend_signal import TrendSignal
from models.trend_source import TrendSource
from shared.errors import NotFoundError, StorageError


class TrendStore:
    def __init__(
        self,
        sources_path: str = "data/trend_sources.json",
        signals_path: str = "data/trend_signals.json",
    ) -> None:
        self.sources_path = Path(sources_path)
        self.signals_path = Path(signals_path)

        self.sources_path.parent.mkdir(parents=True, exist_ok=True)
        self.signals_path.parent.mkdir(parents=True, exist_ok=True)

        if not self.sources_path.exists():
            self._write_raw(self.sources_path, {"sources": {}})

        if not self.signals_path.exists():
            self._write_raw(self.signals_path, {"signals": {}})

    def create_source(self, source: TrendSource) -> TrendSource:
        data = self._read_raw(self.sources_path)
        sources = data["sources"]

        for source_id, existing in sources.items():
            existing_source = TrendSource.from_dict(existing)

            same_name = existing_source.source_name.strip().lower() == source.source_name.strip().lower()
            same_platform = existing_source.platform.value == source.platform.value
            same_type = existing_source.source_type.value == source.source_type.value

            if same_name and same_platform and same_type:
                merged_source = TrendSource.from_dict(existing)
                merged_source.reliability_weight = source.reliability_weight
                merged_source.default_half_life_hours = source.default_half_life_hours
                merged_source.enabled = source.enabled
                merged_source.workspace_id = source.workspace_id
                merged_source.metadata = dict(source.metadata)
                merged_source.touch()

                sources[source_id] = merged_source.to_dict()
                self._write_raw(self.sources_path, data)
                return merged_source

        if source.source_id in sources:
            raise StorageError(f"Trend source already exists: {source.source_id}")

        sources[source.source_id] = source.to_dict()
        self._write_raw(self.sources_path, data)
        return source

    def update_source(self, source: TrendSource) -> TrendSource:
        data = self._read_raw(self.sources_path)
        sources = data["sources"]

        if source.source_id not in sources:
            raise NotFoundError(f"Trend source not found: {source.source_id}")

        source.touch()
        sources[source.source_id] = source.to_dict()
        self._write_raw(self.sources_path, data)
        return source

    def get_source(self, source_id: str) -> TrendSource:
        data = self._read_raw(self.sources_path)
        sources = data["sources"]

        if source_id not in sources:
            raise NotFoundError(f"Trend source not found: {source_id}")

        return TrendSource.from_dict(sources[source_id])

    def list_sources(self) -> list[TrendSource]:
        data = self._read_raw(self.sources_path)
        return [TrendSource.from_dict(item) for item in data["sources"].values()]

    def create_signal(self, signal: TrendSignal) -> TrendSignal:
        data = self._read_raw(self.signals_path)
        signals = data["signals"]

        for existing in signals.values():
            existing_signal = TrendSignal.from_dict(existing)

            same_source = existing_signal.source_id == signal.source_id
            same_label = existing_signal.normalized_label == signal.normalized_label
            same_observed_at = existing_signal.observed_at == signal.observed_at

            if same_source and same_label and same_observed_at:
                return existing_signal

        if signal.signal_id in signals:
            raise StorageError(f"Trend signal already exists: {signal.signal_id}")

        signals[signal.signal_id] = signal.to_dict()
        self._write_raw(self.signals_path, data)
        return signal

    def update_signal(self, signal: TrendSignal) -> TrendSignal:
        data = self._read_raw(self.signals_path)
        signals = data["signals"]

        if signal.signal_id not in signals:
            raise NotFoundError(f"Trend signal not found: {signal.signal_id}")

        signal.touch()
        signals[signal.signal_id] = signal.to_dict()
        self._write_raw(self.signals_path, data)
        return signal

    def get_signal(self, signal_id: str) -> TrendSignal:
        data = self._read_raw(self.signals_path)
        signals = data["signals"]

        if signal_id not in signals:
            raise NotFoundError(f"Trend signal not found: {signal_id}")

        return TrendSignal.from_dict(signals[signal_id])

    def list_signals(self) -> list[TrendSignal]:
        data = self._read_raw(self.signals_path)
        return [TrendSignal.from_dict(item) for item in data["signals"].values()]

    def _read_raw(self, path: Path) -> dict[str, Any]:
        try:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            raise StorageError(f"Could not read trend store: {exc}") from exc

    def _write_raw(self, path: Path, data: dict[str, Any]) -> None:
        try:
            with path.open("w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as exc:
            raise StorageError(f"Could not write trend store: {exc}") from exc