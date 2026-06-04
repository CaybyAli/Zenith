from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_STYLE_DNA_PATH = Path("video_configs/gaming_pairs_style_dna.json")


@dataclass(frozen=True)
class StyleDnaPacingDecision:
    loaded: bool
    source_path: str
    content_type: str | None
    source_count: int | None
    target_clip_seconds: float | None
    cuts_per_minute_median: float | None
    audio_dynamic_range_median: float | None
    pacing_profile: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "loaded": self.loaded,
            "source_path": self.source_path,
            "content_type": self.content_type,
            "source_count": self.source_count,
            "target_clip_seconds": self.target_clip_seconds,
            "cuts_per_minute_median": self.cuts_per_minute_median,
            "audio_dynamic_range_median": self.audio_dynamic_range_median,
            "pacing_profile": self.pacing_profile,
            "confidence": self.confidence,
        }


class StyleDnaPacingAdapter:
    def load_decision(
        self,
        path: str | Path = DEFAULT_STYLE_DNA_PATH,
    ) -> StyleDnaPacingDecision:
        source_path = Path(path)

        try:
            if not source_path.exists():
                return self._fallback(source_path)

            payload = json.loads(source_path.read_text(encoding="utf-8-sig"))
            if not isinstance(payload, dict):
                return self._fallback(source_path)

            cuts_per_minute_median = self._median(payload, "cuts_per_minute")
            target_clip_seconds = self._median(payload, "median_clip_seconds")
            audio_dynamic_range_median = self._median(payload, "audio_dynamic_range")

            return StyleDnaPacingDecision(
                loaded=True,
                source_path=str(source_path),
                content_type=self._string_or_none(payload.get("content_type")),
                source_count=self._int_or_none(payload.get("source_count")),
                target_clip_seconds=target_clip_seconds,
                cuts_per_minute_median=cuts_per_minute_median,
                audio_dynamic_range_median=audio_dynamic_range_median,
                pacing_profile=self._pacing_profile(cuts_per_minute_median),
                confidence=self._confidence(
                    cuts_per_minute_median,
                    target_clip_seconds,
                    audio_dynamic_range_median,
                ),
            )
        except Exception:
            return self._fallback(source_path)

    def _fallback(self, source_path: Path) -> StyleDnaPacingDecision:
        return StyleDnaPacingDecision(
            loaded=False,
            source_path=str(source_path),
            content_type=None,
            source_count=None,
            target_clip_seconds=None,
            cuts_per_minute_median=None,
            audio_dynamic_range_median=None,
            pacing_profile="unknown",
            confidence=0.0,
        )

    def _median(self, payload: dict[str, Any], key: str) -> float | None:
        raw_group = payload.get(key)
        if not isinstance(raw_group, dict):
            return None
        return self._float_or_none(raw_group.get("median"))

    def _pacing_profile(self, cuts_per_minute_median: float | None) -> str:
        if cuts_per_minute_median is None:
            return "unknown"
        if cuts_per_minute_median >= 8.0:
            return "fast"
        if cuts_per_minute_median >= 4.0:
            return "balanced"
        return "slow"

    def _confidence(self, *values: float | None) -> float:
        present_count = sum(value is not None for value in values)
        if present_count == 3:
            return 1.0
        if present_count == 2:
            return 0.66
        if present_count == 1:
            return 0.33
        return 0.0

    def _float_or_none(self, value: Any) -> float | None:
        try:
            if value is None:
                return None
            return float(value)
        except (TypeError, ValueError):
            return None

    def _int_or_none(self, value: Any) -> int | None:
        try:
            if value is None:
                return None
            return int(value)
        except (TypeError, ValueError):
            return None

    def _string_or_none(self, value: Any) -> str | None:
        if value is None:
            return None
        return str(value)