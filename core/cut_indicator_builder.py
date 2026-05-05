from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Any

from models.cut_indicator import CutIndicator, CutIndicatorResult


class CutIndicatorBuilder:
    engine = "cut-indicator-builder-v1"

    EDIT_SIGNAL_MAP = {
        "audio_peak": ("audio_peak", "positive"),
        "motion_peak": ("motion_peak", "positive"),
        "audio_activity": ("audio_activity", "positive"),
        "motion_activity": ("motion_activity", "positive"),
        "silence_zone": ("silence", "negative"),
        "low_motion_zone": ("low_motion", "negative"),
        "hook": ("hook_signal", "positive"),
        "highlight": ("highlight_signal", "positive"),
        "duration_context": ("duration_context", "neutral"),
    }

    def _make_indicator_id(self, source: str) -> str:
        return f"ci_{source}_{uuid.uuid4().hex[:12]}"

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

    def _start_end(
        self,
        item: object,
        start_names: tuple[str, ...] = ("start_seconds", "start_time"),
        end_names: tuple[str, ...] = ("end_seconds", "end_time"),
    ) -> tuple[float, float]:
        start = max(0.0, self._safe_float(self._get(item, *start_names, default=0.0), 0.0))
        end = max(start, self._safe_float(self._get(item, *end_names, default=start), start))
        return round(start, 3), round(end, 3)

    def _append(
        self,
        indicators: list[CutIndicator],
        *,
        indicator_type: str,
        start_seconds: float,
        end_seconds: float,
        score: object,
        confidence: object = 0.75,
        source: str,
        reason: str,
        polarity: str,
        channel_scope: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        indicators.append(
            CutIndicator(
                indicator_id=self._make_indicator_id(source),
                indicator_type=indicator_type,
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                score=self._clamp(score),
                confidence=self._clamp(confidence),
                source=source,
                reason=reason,
                polarity=polarity,
                channel_scope=channel_scope,
                metadata=metadata or {},
            )
        )

    def _from_edit_signals(
        self,
        indicators: list[CutIndicator],
        edit_signals: object,
        channel_scope: str,
    ) -> None:
        for signal in self._iter_items(edit_signals):
            signal_type = str(
                self._get(signal, "signal_type", "kind", "type", default="") or ""
            )
            mapped = self.EDIT_SIGNAL_MAP.get(signal_type)
            if not mapped:
                continue
            indicator_type, polarity = mapped
            if indicator_type == "duration_context":
                continue
            start, end = self._start_end(signal)
            notes = self._get(signal, "notes", default=[]) or []
            self._append(
                indicators,
                indicator_type=indicator_type,
                start_seconds=start,
                end_seconds=end,
                score=self._get(signal, "score", "strength", "confidence", default=0.0),
                confidence=self._get(signal, "confidence", default=0.75),
                source="edit_signal",
                reason=f"normalized edit signal: {signal_type}",
                polarity=polarity,
                channel_scope=channel_scope,
                metadata={
                    "signal_type": signal_type,
                    "signal_id": self._get(signal, "signal_id", default=None),
                    "tags": list(self._get(signal, "tags", default=[]) or []),
                    "notes": list(notes)[:3] if isinstance(notes, list) else [str(notes)],
                },
            )

    def _from_transcript(
        self,
        indicators: list[CutIndicator],
        transcript_result: object,
        channel_scope: str,
    ) -> None:
        segments = self._get(transcript_result, "segments", default=[])
        for segment in self._iter_items(segments):
            text = str(self._get(segment, "text", default="") or "").strip()
            if not text:
                continue
            start, end = self._start_end(segment)
            compact_text = " ".join(text.split())
            score = 0.35
            if len(compact_text) <= 8:
                score = 0.20
            elif "?" in compact_text or "!" in compact_text:
                score = 0.55
            self._append(
                indicators,
                indicator_type="speech_segment",
                start_seconds=start,
                end_seconds=end,
                score=score,
                confidence=self._get(segment, "confidence", default=0.75),
                source="transcript",
                reason="transcript speech segment",
                polarity="neutral",
                channel_scope=channel_scope,
                metadata={"text_preview": compact_text[:80]},
            )

    def _from_energy(
        self,
        indicators: list[CutIndicator],
        energy_curve_result: object,
        channel_scope: str,
    ) -> None:
        peak_ids = {
            self._get(point, "point_id", default=None)
            for point in self._iter_items(self._get(energy_curve_result, "peak_points", default=[]))
        }
        points = self._iter_items(self._get(energy_curve_result, "points", default=[]))
        for point in points:
            energy_score = self._clamp(self._get(point, "energy_score", default=0.0))
            if energy_score <= 0.0:
                continue
            point_id = self._get(point, "point_id", default=None)
            is_peak = bool(point_id in peak_ids or energy_score >= 0.65)
            indicator_type = "energy_peak" if is_peak else "energy_activity"
            polarity = "positive" if is_peak else "neutral"
            start, end = self._start_end(point)
            self._append(
                indicators,
                indicator_type=indicator_type,
                start_seconds=start,
                end_seconds=end,
                score=energy_score,
                confidence=0.80 if is_peak else 0.65,
                source="energy",
                reason="energy curve peak" if is_peak else "energy curve activity",
                polarity=polarity,
                channel_scope=channel_scope,
                metadata={
                    "point_id": point_id,
                    "signal_count": self._get(point, "signal_count", default=0),
                    "dominant_signals": list(self._get(point, "dominant_signals", default=[]) or []),
                },
            )

    def _from_vision(
        self,
        indicators: list[CutIndicator],
        gameplay_vision_result: object,
        channel_scope: str,
    ) -> None:
        for window in self._iter_items(self._get(gameplay_vision_result, "action_windows", default=[])):
            start, end = self._start_end(window)
            action_score = self._clamp(self._get(window, "action_score", default=0.0))
            scene_score = self._clamp(self._get(window, "scene_change_score", default=0.0))
            label = str(self._get(window, "label", default="") or "")
            if label == "scene_change" or scene_score > action_score:
                indicator_type = "scene_change"
                score = max(scene_score, action_score)
                polarity = "neutral"
            else:
                indicator_type = "gameplay_action"
                score = action_score
                polarity = "positive"
            self._append(
                indicators,
                indicator_type=indicator_type,
                start_seconds=start,
                end_seconds=end,
                score=score,
                confidence=0.70,
                source="vision",
                reason=str(self._get(window, "reason", default="gameplay vision window") or "gameplay vision window"),
                polarity=polarity,
                channel_scope=channel_scope,
                metadata={
                    "label": label,
                    "motion_score": self._clamp(self._get(window, "motion_score", default=0.0)),
                    "action_score": action_score,
                    "scene_change_score": scene_score,
                },
            )

    def _from_facecam(
        self,
        indicators: list[CutIndicator],
        facecam_reaction_result: object,
        channel_scope: str,
    ) -> None:
        for window in self._iter_items(self._get(facecam_reaction_result, "reaction_windows", default=[])):
            start, end = self._start_end(window)
            self._append(
                indicators,
                indicator_type="facecam_reaction",
                start_seconds=start,
                end_seconds=end,
                score=self._get(window, "reaction_score", default=0.0),
                confidence=0.70,
                source="facecam",
                reason=str(self._get(window, "reason", default="facecam reaction window") or "facecam reaction window"),
                polarity="positive",
                channel_scope=channel_scope,
                metadata={
                    "label": self._get(window, "label", default=""),
                    "motion_score": self._clamp(self._get(window, "motion_score", default=0.0)),
                    "expression_change_score": self._clamp(
                        self._get(window, "expression_change_score", default=0.0)
                    ),
                },
            )

    def _from_timeline(
        self,
        indicators: list[CutIndicator],
        edit_timeline: object,
        channel_scope: str,
    ) -> None:
        for segment in self._iter_items(self._get(edit_timeline, "selected_segments", default=[])):
            start, end = self._start_end(segment)
            self._append(
                indicators,
                indicator_type="selected_segment",
                start_seconds=start,
                end_seconds=end,
                score=self._get(segment, "selection_score", default=0.0),
                confidence=0.80,
                source="timeline",
                reason="selected timeline segment",
                polarity="neutral",
                channel_scope=channel_scope,
                metadata={
                    "segment_id": self._get(segment, "segment_id", default=None),
                    "segment_role": self._get(segment, "segment_role", default=""),
                    "notes": list(self._get(segment, "notes", default=[]) or [])[:5],
                },
            )

    def _from_sentence_timeline(
        self,
        indicators: list[CutIndicator],
        sentence_timeline_result: object,
        channel_scope: str,
    ) -> None:
        mapping = {
            "hook": ("hook_sentence", "positive"),
            "exclamation": ("exclamation_sentence", "positive"),
            "question": ("question_sentence", "positive"),
            "filler": ("filler_sentence", "negative"),
            "incomplete": ("incomplete_sentence", "negative"),
            "normal": ("speech_sentence", "neutral"),
        }
        sentences = self._get(sentence_timeline_result, "sentences", default=[])
        for sentence in self._iter_items(sentences):
            text = str(self._get(sentence, "text", default="") or "").strip()
            if not text:
                continue
            sentence_kind = str(self._get(sentence, "sentence_kind", default="normal") or "normal")
            indicator_type, polarity = mapping.get(sentence_kind, ("speech_sentence", "neutral"))
            start, end = self._start_end(sentence)
            self._append(
                indicators,
                indicator_type=indicator_type,
                start_seconds=start,
                end_seconds=end,
                score=self._get(sentence, "score", default=0.0),
                confidence=self._get(sentence, "confidence", default=0.75),
                source="sentence_timeline",
                reason=f"sentence timeline {sentence_kind}",
                polarity=polarity,
                channel_scope=channel_scope,
                metadata={
                    "sentence_kind": sentence_kind,
                    "text_preview": " ".join(text.split())[:100],
                    "source_segment_ids": list(
                        self._get(sentence, "source_segment_ids", default=[]) or []
                    ),
                },
            )

    def _from_audio_roles(
        self,
        indicators: list[CutIndicator],
        audio_role_result: object,
        channel_scope: str,
    ) -> None:
        negative_roles = {"silence_or_dead_air", "speech_cut_risk_audio"}
        neutral_roles = {"speech_active"}
        for window in self._iter_items(self._get(audio_role_result, "windows", default=[])):
            role_type = str(self._get(window, "role_type", default="") or "")
            if not role_type:
                continue
            start, end = self._start_end(window)
            polarity = "positive"
            if role_type in negative_roles:
                polarity = "negative"
            elif role_type in neutral_roles:
                polarity = "neutral"
            metadata = dict(self._get(window, "metadata", default={}) or {})
            metadata["source_signal_ids"] = list(
                self._get(window, "source_signal_ids", default=[]) or []
            )
            self._append(
                indicators,
                indicator_type=role_type,
                start_seconds=start,
                end_seconds=end,
                score=self._get(window, "score", default=0.0),
                confidence=self._get(window, "confidence", default=0.0),
                source="audio_role",
                reason=str(self._get(window, "reason", default="audio role window") or "audio role window"),
                polarity=polarity,
                channel_scope=channel_scope,
                metadata=metadata,
            )

    def _from_gameplay_events(
        self,
        indicators: list[CutIndicator],
        gameplay_event_result: object,
        channel_scope: str,
    ) -> None:
        positive_events = {"high_action_burst", "sustained_action", "goal_or_save_like_flash"}
        negative_events = {"round_end_dead_time", "menu_or_idle", "low_gameplay_value"}
        for window in self._iter_items(self._get(gameplay_event_result, "windows", default=[])):
            event_type = str(self._get(window, "event_type", default="") or "")
            if not event_type:
                continue
            start, end = self._start_end(window)
            polarity = "neutral"
            if event_type in positive_events:
                polarity = "positive"
            elif event_type in negative_events:
                polarity = "negative"
            metadata = dict(self._get(window, "metadata", default={}) or {})
            metadata["source_window_ids"] = list(
                self._get(window, "source_window_ids", default=[]) or []
            )
            metadata["source_signal_ids"] = list(
                self._get(window, "source_signal_ids", default=[]) or []
            )
            self._append(
                indicators,
                indicator_type=event_type,
                start_seconds=start,
                end_seconds=end,
                score=self._get(window, "score", default=0.0),
                confidence=self._get(window, "confidence", default=0.0),
                source="gameplay_event",
                reason=str(self._get(window, "reason", default="gameplay event window") or "gameplay event window"),
                polarity=polarity,
                channel_scope=channel_scope,
                metadata=metadata,
            )

    def build(
        self,
        *,
        edit_signals: object = None,
        transcript_result: object = None,
        sentence_timeline_result: object = None,
        audio_role_result: object = None,
        gameplay_event_result: object = None,
        energy_curve_result: object = None,
        gameplay_vision_result: object = None,
        facecam_reaction_result: object = None,
        edit_timeline: object = None,
        channel_type: object = "gaming_main",
    ) -> CutIndicatorResult:
        channel_scope = str(getattr(channel_type, "value", channel_type) or "gaming_main")
        indicators: list[CutIndicator] = []

        self._from_edit_signals(indicators, edit_signals, channel_scope)
        self._from_transcript(indicators, transcript_result, channel_scope)
        self._from_sentence_timeline(indicators, sentence_timeline_result, channel_scope)
        self._from_audio_roles(indicators, audio_role_result, channel_scope)
        self._from_gameplay_events(indicators, gameplay_event_result, channel_scope)
        self._from_energy(indicators, energy_curve_result, channel_scope)
        self._from_vision(indicators, gameplay_vision_result, channel_scope)
        self._from_facecam(indicators, facecam_reaction_result, channel_scope)
        self._from_timeline(indicators, edit_timeline, channel_scope)

        indicators.sort(
            key=lambda indicator: (
                indicator.start_seconds,
                indicator.end_seconds,
                indicator.source,
                indicator.indicator_type,
            )
        )
        return CutIndicatorResult(
            indicators=indicators,
            engine=self.engine,
            skipped_reason="no indicators" if not indicators else None,
        )
