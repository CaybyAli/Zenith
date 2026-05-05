from __future__ import annotations

import re
import uuid
from collections.abc import Iterable
from typing import Any

from models.facecam_emotion_result import FacecamEmotionResult, FacecamEmotionWindow


class FacecamEmotionIndicatorBuilder:
    engine = "facecam-emotion-indicator-builder-v1"

    LAUGH_TERMS = {"haha", "hahaha", "lol", "lach", "lache", "lachen"}

    def _make_emotion_id(self, emotion_type: str) -> str:
        return f"facecam_emotion_{emotion_type}_{uuid.uuid4().hex[:12]}"

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

    def _is_near(self, left: dict[str, Any], right: dict[str, Any], tolerance: float = 1.5) -> bool:
        return left["start_seconds"] <= right["end_seconds"] + tolerance and left["end_seconds"] >= right["start_seconds"] - tolerance

    def _facecam_windows(self, facecam_reaction_result: object) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for index, window in enumerate(self._iter_items(self._get(facecam_reaction_result, "windows", default=[]))):
            start, end = self._start_end(window)
            rows.append(
                {
                    "window_id": f"facecam_window_{index:06d}",
                    "start_seconds": start,
                    "end_seconds": end,
                    "reaction_score": self._clamp(self._get(window, "reaction_score", default=0.0)),
                    "motion_score": self._clamp(self._get(window, "motion_score", default=0.0)),
                    "expression_change_score": self._clamp(self._get(window, "expression_change_score", default=0.0)),
                    "label": str(self._get(window, "label", default="") or ""),
                    "reason": str(self._get(window, "reason", default="") or ""),
                }
            )
        return sorted(rows, key=lambda item: (item["start_seconds"], item["end_seconds"]))

    def _audio_roles(self, audio_role_result: object) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for window in self._iter_items(self._get(audio_role_result, "windows", default=[])):
            start, end = self._start_end(window)
            rows.append(
                {
                    "window_id": str(self._get(window, "window_id", default="")),
                    "start_seconds": start,
                    "end_seconds": end,
                    "role_type": str(self._get(window, "role_type", default="") or ""),
                    "score": self._clamp(self._get(window, "score", default=0.0)),
                    "source_signal_ids": list(self._get(window, "source_signal_ids", default=[]) or []),
                }
            )
        return rows

    def _sentences(self, sentence_timeline_result: object) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for sentence in self._iter_items(self._get(sentence_timeline_result, "sentences", default=[])):
            start, end = self._start_end(sentence)
            text = str(self._get(sentence, "text", default="") or "")
            rows.append(
                {
                    "sentence_id": str(self._get(sentence, "sentence_id", default="")),
                    "start_seconds": start,
                    "end_seconds": end,
                    "sentence_kind": str(self._get(sentence, "sentence_kind", default="normal") or "normal"),
                    "text": text,
                    "source_segment_ids": list(self._get(sentence, "source_segment_ids", default=[]) or []),
                }
            )
        return rows

    def _gameplay_events(self, gameplay_event_result: object) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for window in self._iter_items(self._get(gameplay_event_result, "windows", default=[])):
            start, end = self._start_end(window)
            rows.append(
                {
                    "event_id": str(self._get(window, "event_id", default="")),
                    "start_seconds": start,
                    "end_seconds": end,
                    "event_type": str(self._get(window, "event_type", default="") or ""),
                    "score": self._clamp(self._get(window, "score", default=0.0)),
                    "source_window_ids": list(self._get(window, "source_window_ids", default=[]) or []),
                    "source_signal_ids": list(self._get(window, "source_signal_ids", default=[]) or []),
                }
            )
        return rows

    def _near_audio_roles(
        self,
        facecam_window: dict[str, Any],
        audio_roles: list[dict[str, Any]],
        role_types: set[str],
    ) -> list[dict[str, Any]]:
        return [
            role for role in audio_roles
            if role["role_type"] in role_types and self._is_near(facecam_window, role, tolerance=1.5)
        ]

    def _near_sentences(
        self,
        facecam_window: dict[str, Any],
        sentences: list[dict[str, Any]],
        kinds: set[str] | None = None,
        laugh_text: bool = False,
    ) -> list[dict[str, Any]]:
        matches: list[dict[str, Any]] = []
        for sentence in sentences:
            if not self._is_near(facecam_window, sentence, tolerance=1.5):
                continue
            text_matches = laugh_text and self._contains_laugh_text(sentence["text"])
            kind_matches = kinds is not None and sentence["sentence_kind"] in kinds
            if kinds is None and not laugh_text:
                matches.append(sentence)
            elif text_matches or kind_matches:
                matches.append(sentence)
        return matches

    def _near_gameplay_events(
        self,
        facecam_window: dict[str, Any],
        gameplay_events: list[dict[str, Any]],
        event_types: set[str],
    ) -> list[dict[str, Any]]:
        return [
            event for event in gameplay_events
            if event["event_type"] in event_types and self._is_near(facecam_window, event, tolerance=1.5)
        ]

    def _contains_laugh_text(self, text: str) -> bool:
        lowered = text.lower()
        return any(term in lowered for term in self.LAUGH_TERMS) or bool(re.search(r"\bha+\b", lowered))

    def _append(
        self,
        windows: list[FacecamEmotionWindow],
        *,
        emotion_type: str,
        facecam_window: dict[str, Any],
        score: object,
        confidence: object,
        reason: str,
        related_windows: list[dict[str, Any]] | None = None,
        source_signal_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> FacecamEmotionWindow:
        related_windows = related_windows or []
        source_window_ids = [facecam_window["window_id"]]
        for related in related_windows:
            for key in ("window_id", "event_id", "sentence_id"):
                related_id = related.get(key)
                if related_id:
                    source_window_ids.append(str(related_id))
                    break
            source_window_ids.extend(str(item) for item in related.get("source_window_ids", []) if item)

        signal_ids = list(source_signal_ids or [])
        for related in related_windows:
            signal_ids.extend(str(item) for item in related.get("source_signal_ids", []) if item)
            signal_ids.extend(str(item) for item in related.get("source_segment_ids", []) if item)

        payload = {
            "facecam_label": facecam_window["label"],
            "reaction_score": facecam_window["reaction_score"],
            "motion_score": facecam_window["motion_score"],
            "expression_change_score": facecam_window["expression_change_score"],
        }
        payload.update(metadata or {})

        window = FacecamEmotionWindow(
            emotion_id=self._make_emotion_id(emotion_type),
            start_seconds=facecam_window["start_seconds"],
            end_seconds=facecam_window["end_seconds"],
            emotion_type=emotion_type,
            score=self._clamp(score),
            confidence=self._clamp(confidence),
            reason=reason,
            source_window_ids=list(dict.fromkeys(source_window_ids)),
            source_signal_ids=list(dict.fromkeys(signal_ids)),
            metadata=payload,
        )
        windows.append(window)
        return window

    def build(
        self,
        *,
        facecam_reaction_result: object = None,
        audio_role_result: object = None,
        sentence_timeline_result: object = None,
        gameplay_event_result: object = None,
        channel_type: object = "gaming_main",
    ) -> FacecamEmotionResult:
        del channel_type
        facecam_windows = self._facecam_windows(facecam_reaction_result)
        if not facecam_windows:
            return FacecamEmotionResult(
                engine=self.engine,
                skipped_reason="no facecam reaction windows",
            )

        audio_roles = self._audio_roles(audio_role_result)
        sentences = self._sentences(sentence_timeline_result)
        gameplay_events = self._gameplay_events(gameplay_event_result)

        emotion_windows: list[FacecamEmotionWindow] = []
        low_count = 0
        strong_by_facecam_id: dict[str, list[FacecamEmotionWindow]] = {}

        for facecam_window in facecam_windows:
            reaction_score = facecam_window["reaction_score"]
            motion_score = facecam_window["motion_score"]
            expression_score = facecam_window["expression_change_score"]
            label = facecam_window["label"]
            is_reaction = reaction_score >= 0.20 or label in {"facecam_reaction", "strong_facecam_reaction"}

            if is_reaction:
                created = self._append(
                    emotion_windows,
                    emotion_type="facecam_reaction_spike",
                    facecam_window=facecam_window,
                    score=max(0.50, min(0.88, reaction_score * 1.45)),
                    confidence=0.75 if reaction_score >= 0.42 else 0.58,
                    reason="high facecam reaction score",
                )
                strong_by_facecam_id.setdefault(facecam_window["window_id"], []).append(created)

            if motion_score >= 0.18:
                created = self._append(
                    emotion_windows,
                    emotion_type="facecam_motion_spike",
                    facecam_window=facecam_window,
                    score=max(0.45, min(0.75, motion_score * 1.2)),
                    confidence=0.68 if motion_score >= 0.30 else 0.52,
                    reason="facecam motion spike",
                )
                if created.score >= 0.60:
                    strong_by_facecam_id.setdefault(facecam_window["window_id"], []).append(created)

            if expression_score >= 0.15:
                created = self._append(
                    emotion_windows,
                    emotion_type="expression_change_like",
                    facecam_window=facecam_window,
                    score=max(0.45, min(0.75, expression_score * 1.5)),
                    confidence=0.66 if expression_score >= 0.28 else 0.50,
                    reason="facecam expression-change-like signal",
                )
                if created.score >= 0.60:
                    strong_by_facecam_id.setdefault(facecam_window["window_id"], []).append(created)

            shout_roles = self._near_audio_roles(facecam_window, audio_roles, {"shout_like_audio", "group_reaction_like"})
            laugh_roles = self._near_audio_roles(facecam_window, audio_roles, {"laugh_like_audio"})
            laugh_sentences = self._near_sentences(facecam_window, sentences, laugh_text=True)
            shock_sentences = self._near_sentences(facecam_window, sentences, kinds={"exclamation", "hook"})
            gameplay_flash = self._near_gameplay_events(facecam_window, gameplay_events, {"goal_or_save_like_flash"})

            if expression_score >= 0.15 and shout_roles:
                self._append(
                    emotion_windows,
                    emotion_type="mouth_open_like",
                    facecam_window=facecam_window,
                    score=max(0.55, min(0.85, expression_score * 1.8 + 0.18)),
                    confidence=0.58 if expression_score >= 0.30 else 0.42,
                    reason="expression change near shout/group reaction",
                    related_windows=shout_roles,
                    metadata={"nearby_audio_roles": [role["role_type"] for role in shout_roles]},
                )

            if (expression_score >= 0.12 or reaction_score >= 0.18) and (laugh_roles or laugh_sentences):
                related = [*laugh_roles, *laugh_sentences]
                self._append(
                    emotion_windows,
                    emotion_type="smile_like",
                    facecam_window=facecam_window,
                    score=max(0.50, min(0.75, max(expression_score, reaction_score) * 1.25 + 0.20)),
                    confidence=0.58 if laugh_roles else 0.44,
                    reason="facecam change near laugh-like audio/text",
                    related_windows=related,
                    metadata={"nearby_laugh_sources": len(related)},
                )

            if is_reaction and (shout_roles or shock_sentences or gameplay_flash):
                related = [*shout_roles, *shock_sentences, *gameplay_flash]
                created = self._append(
                    emotion_windows,
                    emotion_type="shock_like",
                    facecam_window=facecam_window,
                    score=max(0.60, min(0.90, reaction_score * 1.25 + 0.20)),
                    confidence=0.68 if shout_roles or gameplay_flash else 0.50,
                    reason="facecam reaction near shout/exclamation/gameplay flash",
                    related_windows=related,
                    metadata={
                        "nearby_shout_or_group": len(shout_roles),
                        "nearby_exclamation_or_hook": len(shock_sentences),
                        "nearby_gameplay_flash": len(gameplay_flash),
                    },
                )
                strong_by_facecam_id.setdefault(facecam_window["window_id"], []).append(created)

            if is_reaction and laugh_roles:
                created = self._append(
                    emotion_windows,
                    emotion_type="laugh_like_face",
                    facecam_window=facecam_window,
                    score=max(0.60, min(0.85, reaction_score * 1.15 + 0.20)),
                    confidence=0.66 if reaction_score >= 0.35 else 0.48,
                    reason="facecam reaction overlaps laugh-like audio",
                    related_windows=laugh_roles,
                    metadata={"nearby_laugh_audio": len(laugh_roles)},
                )
                strong_by_facecam_id.setdefault(facecam_window["window_id"], []).append(created)

            if motion_score >= 0.18 and expression_score <= max(0.14, motion_score * 0.65):
                self._append(
                    emotion_windows,
                    emotion_type="head_movement_like",
                    facecam_window=facecam_window,
                    score=max(0.45, min(0.70, motion_score * 1.1)),
                    confidence=0.58 if motion_score >= 0.30 else 0.42,
                    reason="facecam motion exceeds expression change",
                )

            if reaction_score < 0.05 and motion_score < 0.05 and low_count < 3:
                low_count += 1
                self._append(
                    emotion_windows,
                    emotion_type="low_facecam_value",
                    facecam_window=facecam_window,
                    score=0.55,
                    confidence=0.50,
                    reason="low facecam reaction value",
                )

        for facecam_id, related in strong_by_facecam_id.items():
            eligible = [
                window for window in related
                if window.emotion_type in {"facecam_reaction_spike", "shock_like", "laugh_like_face"}
                and window.score >= 0.60
            ]
            if not eligible:
                continue
            source = max(eligible, key=lambda window: window.score)
            facecam_window = next((item for item in facecam_windows if item["window_id"] == facecam_id), None)
            if facecam_window is None:
                continue
            self._append(
                emotion_windows,
                emotion_type="thumbnail_face_candidate",
                facecam_window=facecam_window,
                score=source.score,
                confidence=max(0.45, min(0.70, source.confidence)),
                reason="strong facecam moment suitable for thumbnail candidate",
                related_windows=[{"window_id": source.emotion_id}],
                metadata={"source_emotion_type": source.emotion_type},
            )

        emotion_windows.sort(key=lambda window: (window.start_seconds, window.end_seconds, window.emotion_type))
        return FacecamEmotionResult(
            windows=emotion_windows,
            engine=self.engine,
            skipped_reason="no facecam emotion windows" if not emotion_windows else None,
        )
