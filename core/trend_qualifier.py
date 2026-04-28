from __future__ import annotations

from typing import Any

from models.trend_qualification import TrendQualification
from models.trend_signal import TrendSignal
from shared.trend_enums import TrendPlatform
from shared.trend_qualification_enums import ContentShape, DecisionHint, LifespanClass


def _clean_text(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


class TrendQualifier:
    def qualify(self, signal: TrendSignal) -> TrendQualification:
        text_pool = self._build_text_pool(signal)
        content_shape = self._derive_content_shape(text_pool)
        lifespan_class = self._derive_lifespan_class(signal.half_life_hours)
        risk_flags = self._derive_risk_flags(signal)
        fit_main, fit_uncut, fit_faceless = self._derive_channel_fit(
            signal=signal,
            text_pool=text_pool,
            content_shape=content_shape,
            risk_flags=risk_flags,
        )
        decision_hint = self._derive_decision_hint(
            fit_main=fit_main,
            fit_uncut=fit_uncut,
            fit_faceless=fit_faceless,
            risk_flags=risk_flags,
            signal=signal,
        )

        qualification_notes = [
            f"content_shape={content_shape.value}",
            f"lifespan_class={lifespan_class.value}",
            f"decision_hint={decision_hint.value}",
        ]

        if fit_main:
            qualification_notes.append("fit_main_true")
        if fit_uncut:
            qualification_notes.append("fit_uncut_true")
        if fit_faceless:
            qualification_notes.append("fit_faceless_true")
        if risk_flags:
            qualification_notes.append("risk_flags_present")

        transcript_hints: list[str] = []
        multi_track_hints: list[str] = []
        metadata_hints = {
            "platform": signal.platform.value,
            "channel_targets": list(signal.channel_targets),
            "source_type": signal.source_type.value,
        }

        return TrendQualification.from_dict(
            {
                "signal_id": signal.signal_id,
                "fit_main": fit_main,
                "fit_uncut": fit_uncut,
                "fit_faceless": fit_faceless,
                "content_shape": content_shape.value,
                "lifespan_class": lifespan_class.value,
                "risk_flags": risk_flags,
                "decision_hint": decision_hint.value,
                "qualification_notes": qualification_notes,
                "transcript_hints": transcript_hints,
                "multi_track_hints": multi_track_hints,
                "metadata_hints": metadata_hints,
            }
        )

    def _build_text_pool(self, signal: TrendSignal) -> str:
        parts = [
            signal.topic,
            signal.raw_label,
            signal.normalized_label,
            signal.raw_payload.get("title"),
            signal.raw_payload.get("topic"),
            signal.raw_payload.get("label"),
            signal.raw_payload.get("query"),
            signal.raw_payload.get("text"),
        ]

        cleaned = [_clean_text(part).lower() for part in parts if _clean_text(part)]
        return " ".join(cleaned)

    def _derive_content_shape(self, text_pool: str) -> ContentShape:
        reaction_keywords = [
            "reaction",
            "reacts",
            "reacting",
            "first impression",
            "watching",
        ]
        news_keywords = [
            "news",
            "update",
            "breaking",
            "leak",
            "announced",
            "announcement",
            "rumor",
            "rumour",
            "patch notes",
        ]
        clip_keywords = [
            "clip",
            "highlight",
            "moment",
            "compilation",
            "best moment",
        ]
        search_keywords = [
            "how to",
            "guide",
            "tips",
            "tutorial",
            "explained",
            "best",
            "top ",
            "review",
            "vs ",
        ]

        if any(keyword in text_pool for keyword in reaction_keywords):
            return ContentShape.REACTION_DRIVEN
        if any(keyword in text_pool for keyword in news_keywords):
            return ContentShape.NEWS_DRIVEN
        if any(keyword in text_pool for keyword in clip_keywords):
            return ContentShape.CLIP_DRIVEN
        if any(keyword in text_pool for keyword in search_keywords):
            return ContentShape.SEARCH_DRIVEN
        if text_pool.strip():
            return ContentShape.TOPIC_DRIVEN
        return ContentShape.UNKNOWN

    def _derive_lifespan_class(self, half_life_hours: float) -> LifespanClass:
        if half_life_hours <= 12:
            return LifespanClass.FLASH
        if half_life_hours <= 48:
            return LifespanClass.SHORT
        if half_life_hours <= 168:
            return LifespanClass.MEDIUM
        return LifespanClass.LONG

    def _derive_risk_flags(self, signal: TrendSignal) -> list[str]:
        risk_flags: list[str] = []

        if signal.competition_density >= 0.75:
            risk_flags.append("high_competition")
        if signal.confidence < 0.40:
            risk_flags.append("low_confidence")
        if signal.freshness_hours > signal.half_life_hours:
            risk_flags.append("stale_signal")
        if signal.signal_strength < 0.35:
            risk_flags.append("weak_signal")
        if signal.platform == TrendPlatform.UNKNOWN:
            risk_flags.append("platform_unknown")

        return risk_flags

    def _derive_channel_fit(
        self,
        *,
        signal: TrendSignal,
        text_pool: str,
        content_shape: ContentShape,
        risk_flags: list[str],
    ) -> tuple[bool, bool, bool]:
        targets = set(signal.channel_targets)
        creator_bound = self._looks_creator_bound(text_pool)
        hard_block = "platform_unknown" in risk_flags
        too_weak = signal.signal_strength < 0.20

        fit_main = (
            not hard_block
            and not too_weak
            and (
                "main" in targets
                or content_shape in {
                    ContentShape.REACTION_DRIVEN,
                    ContentShape.NEWS_DRIVEN,
                    ContentShape.TOPIC_DRIVEN,
                }
            )
        )

        fit_uncut = (
            not hard_block
            and not too_weak
            and (
                "uncut" in targets
                or content_shape == ContentShape.REACTION_DRIVEN
            )
        )

        fit_faceless = (
            not hard_block
            and not too_weak
            and not creator_bound
            and (
                "faceless" in targets
                or content_shape in {
                    ContentShape.TOPIC_DRIVEN,
                    ContentShape.NEWS_DRIVEN,
                    ContentShape.CLIP_DRIVEN,
                    ContentShape.SEARCH_DRIVEN,
                }
            )
        )

        return fit_main, fit_uncut, fit_faceless

    def _looks_creator_bound(self, text_pool: str) -> bool:
        creator_keywords = [
            "my stream",
            "my chat",
            "facecam",
            "my reaction",
            "creator drama",
            "my gameplay",
            "i reacted",
            "my audience",
        ]
        return any(keyword in text_pool for keyword in creator_keywords)

    def _derive_decision_hint(
        self,
        *,
        fit_main: bool,
        fit_uncut: bool,
        fit_faceless: bool,
        risk_flags: list[str],
        signal: TrendSignal,
    ) -> DecisionHint:
        any_fit = fit_main or fit_uncut or fit_faceless

        if not any_fit:
            return DecisionHint.BLOCK
        if "platform_unknown" in risk_flags:
            return DecisionHint.BLOCK
        if len(risk_flags) >= 3:
            return DecisionHint.BLOCK
        if risk_flags:
            return DecisionHint.WATCH
        if signal.signal_strength >= 0.50 and signal.confidence >= 0.50:
            return DecisionHint.KEEP
        return DecisionHint.WATCH