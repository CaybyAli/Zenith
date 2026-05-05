from __future__ import annotations

import re
import uuid
from collections.abc import Iterable
from typing import Any

from models.audio_role_result import AudioRoleResult, AudioRoleWindow


class AudioRoleIndicatorBuilder:
    engine = "audio-role-indicator-builder-v1"

    LAUGH_TERMS = {"haha", "hahaha", "lol", "lach", "lache", "lachen"}
    SHOUT_TERMS = {"alter", "junge", "oh mein gott", "wtf", "no way", "was war das"}

    def _make_window_id(self, role_type: str) -> str:
        return f"audio_role_{role_type}_{uuid.uuid4().hex[:12]}"

    def _safe_float(self, value: object, fallback: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    def _clamp(self, value: object, fallback: float = 0.0) -> float:
        return round(max(0.0, min(1.0, self._safe_float(value, fallback))), 3)

    def _iter_items(self, value: object) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, dict):
            return list(value.values())
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            return list(value)
        return []

    def _get(self, item: object, *names: str, default: object = None) -> object:
        if isinstance(item, dict):
            for name in names:
                if name in item:
                    return item[name]
            return default
        for name in names:
            value = getattr(item, name, None)
            if value is not None:
                return value
        return default

    def _start_end(self, item: object) -> tuple[float, float]:
        start = max(0.0, self._safe_float(self._get(item, "start_seconds", "start_time", default=0.0)))
        end = max(start, self._safe_float(self._get(item, "end_seconds", "end_time", default=start), start))
        return round(start, 3), round(end, 3)

    def _overlaps(self, left: dict[str, Any], right: dict[str, Any]) -> bool:
        return left["start_seconds"] < right["end_seconds"] and left["end_seconds"] > right["start_seconds"]

    def _append(
        self,
        windows: list[AudioRoleWindow],
        *,
        role_type: str,
        start_seconds: float,
        end_seconds: float,
        score: object,
        confidence: object,
        reason: str,
        source_signal_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        windows.append(
            AudioRoleWindow(
                window_id=self._make_window_id(role_type),
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                role_type=role_type,
                score=self._clamp(score),
                confidence=self._clamp(confidence),
                reason=reason,
                source_signal_ids=source_signal_ids or [],
                metadata=metadata or {},
            )
        )

    def _signals(self, edit_signals: object) -> list[dict[str, Any]]:
        signals: list[dict[str, Any]] = []
        for signal in self._iter_items(edit_signals):
            signal_type = str(self._get(signal, "signal_type", "kind", "type", default="") or "")
            start, end = self._start_end(signal)
            if end <= start:
                continue
            signals.append(
                {
                    "signal_id": str(self._get(signal, "signal_id", default="")),
                    "signal_type": signal_type,
                    "start_seconds": start,
                    "end_seconds": end,
                    "strength": self._clamp(self._get(signal, "strength", "score", default=0.0)),
                    "confidence": self._clamp(self._get(signal, "confidence", default=0.75)),
                }
            )
        return sorted(signals, key=lambda item: (item["start_seconds"], item["end_seconds"], item["signal_type"]))

    def _speech_units(
        self,
        transcript_result: object,
        sentence_timeline_result: object,
    ) -> list[dict[str, Any]]:
        units: list[dict[str, Any]] = []
        for sentence in self._iter_items(self._get(sentence_timeline_result, "sentences", default=[])):
            text = str(self._get(sentence, "text", default="") or "").strip()
            if not text:
                continue
            start, end = self._start_end(sentence)
            kind = str(self._get(sentence, "sentence_kind", default="normal") or "normal")
            score = self._clamp(self._get(sentence, "score", default=0.45), 0.45)
            units.append(
                {
                    "unit_id": str(self._get(sentence, "sentence_id", default="")),
                    "source": "sentence",
                    "text": text,
                    "start_seconds": start,
                    "end_seconds": end,
                    "score": max(0.45, score),
                    "confidence": self._clamp(self._get(sentence, "confidence", default=0.75), 0.75),
                    "sentence_kind": kind,
                    "source_segment_ids": list(self._get(sentence, "source_segment_ids", default=[]) or []),
                }
            )

        if units:
            return sorted(units, key=lambda item: (item["start_seconds"], item["end_seconds"]))

        for index, segment in enumerate(self._iter_items(self._get(transcript_result, "segments", default=[]))):
            text = str(self._get(segment, "text", default="") or "").strip()
            if not text:
                continue
            start, end = self._start_end(segment)
            units.append(
                {
                    "unit_id": f"transcript_{index:06d}",
                    "source": "transcript",
                    "text": text,
                    "start_seconds": start,
                    "end_seconds": end,
                    "score": 0.45,
                    "confidence": self._clamp(self._get(segment, "confidence", default=0.75), 0.75),
                    "sentence_kind": "unknown",
                    "source_segment_ids": [f"transcript_{index:06d}"],
                }
            )
        return sorted(units, key=lambda item: (item["start_seconds"], item["end_seconds"]))

    def _word_count(self, text: str) -> int:
        return len(re.findall(r"[A-Za-zÄÖÜäöüß0-9]+", text.lower()))

    def _contains_term(self, text: str, terms: set[str]) -> bool:
        lowered = text.lower()
        return any(term in lowered for term in terms)

    def _overlapping_signal_ids(
        self,
        unit: dict[str, Any],
        signals: list[dict[str, Any]],
        signal_types: set[str],
    ) -> list[str]:
        return [
            signal["signal_id"]
            for signal in signals
            if signal["signal_type"] in signal_types and self._overlaps(unit, signal)
        ]

    def _has_speech_overlap(self, signal: dict[str, Any], speech_units: list[dict[str, Any]]) -> bool:
        return any(self._overlaps(signal, unit) for unit in speech_units)

    def _add_speech_roles(
        self,
        windows: list[AudioRoleWindow],
        speech_units: list[dict[str, Any]],
        audio_signals: list[dict[str, Any]],
    ) -> None:
        for unit in speech_units:
            kind = unit["sentence_kind"]
            score = 0.45
            if kind == "hook":
                score = 0.82
            elif kind == "exclamation":
                score = 0.72
            elif kind == "question":
                score = 0.58
            elif kind == "filler":
                score = 0.35
            elif unit["source"] == "sentence":
                score = max(0.50, unit["score"])
            signal_ids = self._overlapping_signal_ids(unit, audio_signals, {"audio_peak", "audio_activity"})
            self._append(
                windows,
                role_type="speech_active",
                start_seconds=unit["start_seconds"],
                end_seconds=unit["end_seconds"],
                score=score,
                confidence=max(0.70, unit["confidence"]),
                reason=f"{unit['source']} speech activity",
                source_signal_ids=signal_ids,
                metadata={
                    "text_preview": " ".join(unit["text"].split())[:100],
                    "sentence_kind": kind,
                    "source": unit["source"],
                    "source_segment_ids": unit["source_segment_ids"],
                },
            )

            for start, end, edge in (
                (unit["start_seconds"] - 0.15, unit["start_seconds"] + 0.15, "speech_start"),
                (unit["end_seconds"] - 0.15, unit["end_seconds"] + 0.25, "speech_end"),
            ):
                self._append(
                    windows,
                    role_type="speech_cut_risk_audio",
                    start_seconds=max(0.0, round(start, 3)),
                    end_seconds=max(0.0, round(end, 3)),
                    score=0.55,
                    confidence=0.65,
                    reason=f"audio speech boundary risk around {edge}",
                    source_signal_ids=signal_ids,
                    metadata={"edge": edge, "source_unit_id": unit["unit_id"]},
                )

            if self._contains_term(unit["text"], self.LAUGH_TERMS):
                self._append(
                    windows,
                    role_type="laugh_like_audio",
                    start_seconds=unit["start_seconds"],
                    end_seconds=unit["end_seconds"],
                    score=0.76,
                    confidence=0.70,
                    reason="laugh-like transcript text",
                    source_signal_ids=signal_ids,
                    metadata={"text_preview": unit["text"][:100]},
                )

            if kind == "exclamation" or self._contains_term(unit["text"], self.SHOUT_TERMS):
                self._append(
                    windows,
                    role_type="shout_like_audio",
                    start_seconds=unit["start_seconds"],
                    end_seconds=unit["end_seconds"],
                    score=0.78 if kind == "exclamation" else 0.70,
                    confidence=0.70,
                    reason="shout-like speech or exclamation",
                    source_signal_ids=signal_ids,
                    metadata={"text_preview": unit["text"][:100], "sentence_kind": kind},
                )

            if signal_ids and unit["sentence_kind"] not in {"hook", "filler"} and self._word_count(unit["text"]) <= 6:
                self._append(
                    windows,
                    role_type="secondary_speech_like",
                    start_seconds=unit["start_seconds"],
                    end_seconds=unit["end_seconds"],
                    score=0.55,
                    confidence=0.45,
                    reason="audio activity overlaps short speech; possible secondary speaker",
                    source_signal_ids=signal_ids,
                    metadata={"text_preview": unit["text"][:100], "sentence_kind": kind},
                )

    def _add_signal_roles(
        self,
        windows: list[AudioRoleWindow],
        signals: list[dict[str, Any]],
        speech_units: list[dict[str, Any]],
    ) -> None:
        for signal in signals:
            if signal["signal_type"] == "silence_zone":
                duration = signal["end_seconds"] - signal["start_seconds"]
                score = min(1.0, 0.60 + (duration / 10.0))
                self._append(
                    windows,
                    role_type="silence_or_dead_air",
                    start_seconds=signal["start_seconds"],
                    end_seconds=signal["end_seconds"],
                    score=score,
                    confidence=0.85,
                    reason="silence zone from edit signals",
                    source_signal_ids=[signal["signal_id"]],
                    metadata={"duration_seconds": round(duration, 3), "signal_type": signal["signal_type"]},
                )
            elif signal["signal_type"] == "audio_peak" and not self._has_speech_overlap(signal, speech_units):
                self._append(
                    windows,
                    role_type="game_audio_peak",
                    start_seconds=signal["start_seconds"],
                    end_seconds=signal["end_seconds"],
                    score=max(0.50, signal["strength"]),
                    confidence=max(0.50, min(0.70, signal["confidence"])),
                    reason="audio peak without speech overlap",
                    source_signal_ids=[signal["signal_id"]],
                    metadata={"signal_type": signal["signal_type"], "strength": signal["strength"]},
                )
            elif signal["signal_type"] == "audio_peak" and signal["strength"] >= 0.85:
                self._append(
                    windows,
                    role_type="shout_like_audio",
                    start_seconds=signal["start_seconds"],
                    end_seconds=signal["end_seconds"],
                    score=min(0.90, signal["strength"]),
                    confidence=0.55,
                    reason="strong audio peak; possible shout-like moment",
                    source_signal_ids=[signal["signal_id"]],
                    metadata={"signal_type": signal["signal_type"], "strength": signal["strength"]},
                )

        peakish = [signal for signal in signals if signal["signal_type"] in {"audio_peak", "audio_activity"}]
        for unit in speech_units:
            cluster = [
                signal for signal in peakish
                if signal["start_seconds"] < unit["end_seconds"] + 1.0
                and signal["end_seconds"] > unit["start_seconds"] - 1.0
            ]
            peak_count = sum(signal["signal_type"] == "audio_peak" for signal in cluster)
            if len(cluster) >= 3 and peak_count >= 1 and unit["sentence_kind"] in {"hook", "exclamation", "unknown", "normal"}:
                self._append(
                    windows,
                    role_type="group_reaction_like",
                    start_seconds=max(0.0, min(unit["start_seconds"], min(signal["start_seconds"] for signal in cluster))),
                    end_seconds=max(unit["end_seconds"], max(signal["end_seconds"] for signal in cluster)),
                    score=0.72 if unit["sentence_kind"] in {"hook", "exclamation"} else 0.65,
                    confidence=0.62,
                    reason="clustered audio peaks with speech/reaction",
                    source_signal_ids=[signal["signal_id"] for signal in cluster],
                    metadata={
                        "cluster_size": len(cluster),
                        "peak_count": peak_count,
                        "sentence_kind": unit["sentence_kind"],
                    },
                )

    def build(
        self,
        *,
        edit_signals: object = None,
        transcript_result: object = None,
        sentence_timeline_result: object = None,
        energy_curve_result: object = None,
        channel_type: object = "gaming_main",
    ) -> AudioRoleResult:
        del energy_curve_result, channel_type
        signals = self._signals(edit_signals)
        speech_units = self._speech_units(transcript_result, sentence_timeline_result)
        windows: list[AudioRoleWindow] = []

        self._add_speech_roles(windows, speech_units, signals)
        self._add_signal_roles(windows, signals, speech_units)

        windows.sort(key=lambda window: (window.start_seconds, window.end_seconds, window.role_type))
        return AudioRoleResult(
            windows=windows,
            engine=self.engine,
            skipped_reason="no audio role windows" if not windows else None,
        )
