from __future__ import annotations

from models.opportunity import Opportunity
from models.trend_qualification import TrendQualification
from models.trend_signal import TrendSignal
from shared.opportunity_enums import OpportunityLevel
from shared.trend_qualification_enums import ContentShape, DecisionHint, LifespanClass


class OpportunityScorer:
    def score(
        self,
        *,
        signal: TrendSignal,
        qualification: TrendQualification,
    ) -> Opportunity:
        freshness_factor = self._derive_freshness_factor(
            freshness_hours=signal.freshness_hours,
            half_life_hours=signal.half_life_hours,
        )
        competition_factor = round(max(0.0, 1.0 - signal.competition_density), 4)
        decision_factor = self._derive_decision_factor(qualification.decision_hint)
        lifespan_factor = self._derive_lifespan_factor(qualification.lifespan_class)

        base_score = (
            100.0
            * (
                0.30 * signal.signal_strength
                + 0.22 * signal.confidence
                + 0.16 * freshness_factor
                + 0.12 * competition_factor
                + 0.10 * decision_factor
                + 0.10 * lifespan_factor
            )
        )

        penalty_points = self._derive_penalty_points(qualification.risk_flags)
        adjusted_base_score = round(max(0.0, min(100.0, base_score - penalty_points)), 2)

        channel_scores = self._derive_channel_scores(
            base_score=adjusted_base_score,
            signal=signal,
            qualification=qualification,
        )
        primary_channel = self._derive_primary_channel(channel_scores)

        opportunity_score = adjusted_base_score
        if primary_channel:
            opportunity_score = channel_scores[primary_channel]
        else:
            opportunity_score = min(opportunity_score, 20.0)

        opportunity_score = round(max(0.0, min(100.0, opportunity_score)), 2)
        opportunity_level = self._derive_opportunity_level(opportunity_score)

        upside_factors = self._derive_upside_factors(
            signal=signal,
            qualification=qualification,
            primary_channel=primary_channel,
        )
        downside_factors = self._derive_downside_factors(
            signal=signal,
            qualification=qualification,
            primary_channel=primary_channel,
        )
        opportunity_reason = self._build_reason(
            opportunity_score=opportunity_score,
            opportunity_level=opportunity_level,
            primary_channel=primary_channel,
            upside_factors=upside_factors,
            downside_factors=downside_factors,
        )

        return Opportunity.from_dict(
            {
                "signal_id": signal.signal_id,
                "qualification_id": qualification.qualification_id,
                "opportunity_score": opportunity_score,
                "opportunity_level": opportunity_level.value,
                "primary_channel": primary_channel,
                "channel_scores": channel_scores,
                "upside_factors": upside_factors,
                "downside_factors": downside_factors,
                "opportunity_reason": opportunity_reason,
            }
        )

    def _derive_freshness_factor(
        self,
        *,
        freshness_hours: float,
        half_life_hours: float,
    ) -> float:
        if half_life_hours <= 0:
            return 0.2

        ratio = freshness_hours / half_life_hours

        if ratio <= 0.50:
            return 1.0
        if ratio <= 1.00:
            return 0.75
        if ratio <= 1.50:
            return 0.45
        return 0.20

    def _derive_decision_factor(self, decision_hint: DecisionHint) -> float:
        if decision_hint == DecisionHint.KEEP:
            return 1.0
        if decision_hint == DecisionHint.WATCH:
            return 0.65
        return 0.20

    def _derive_lifespan_factor(self, lifespan_class: LifespanClass) -> float:
        if lifespan_class == LifespanClass.FLASH:
            return 0.45
        if lifespan_class == LifespanClass.SHORT:
            return 0.65
        if lifespan_class == LifespanClass.MEDIUM:
            return 0.80
        return 0.90

    def _derive_penalty_points(self, risk_flags: list[str]) -> float:
        penalties = {
            "platform_unknown": 25.0,
            "weak_signal": 15.0,
            "low_confidence": 12.0,
            "stale_signal": 10.0,
            "high_competition": 8.0,
        }

        total = 0.0
        for flag in risk_flags:
            total += penalties.get(flag, 0.0)

        return total

    def _derive_channel_scores(
        self,
        *,
        base_score: float,
        signal: TrendSignal,
        qualification: TrendQualification,
    ) -> dict[str, float]:
        content_shape = qualification.content_shape
        targets = self._normalize_channel_targets(signal.channel_targets)

        scores = {
            "gaming_main": 0.0,
            "gaming_uncut": 0.0,
            "faceless_trend": 0.0,
        }

        if qualification.fit_main:
            scores["gaming_main"] = round(
                max(
                    0.0,
                    min(
                        100.0,
                        base_score
                        * self._main_shape_multiplier(content_shape)
                        * self._target_bias("gaming_main", targets),
                    ),
                ),
                2,
            )

        if qualification.fit_uncut:
            scores["gaming_uncut"] = round(
                max(
                    0.0,
                    min(
                        100.0,
                        base_score
                        * self._uncut_shape_multiplier(content_shape)
                        * self._target_bias("gaming_uncut", targets),
                    ),
                ),
                2,
            )

        if qualification.fit_faceless:
            scores["faceless_trend"] = round(
                max(
                    0.0,
                    min(
                        100.0,
                        base_score
                        * self._faceless_shape_multiplier(content_shape)
                        * self._target_bias("faceless_trend", targets),
                    ),
                ),
                2,
            )

        return scores

    def _normalize_channel_targets(self, channel_targets: list[str]) -> set[str]:
        mapping = {
            "main": "gaming_main",
            "gaming_main": "gaming_main",
            "uncut": "gaming_uncut",
            "gaming_uncut": "gaming_uncut",
            "faceless": "faceless_trend",
            "faceless_trend": "faceless_trend",
        }

        normalized: set[str] = set()

        for item in channel_targets:
            cleaned = str(item).strip().lower()
            if not cleaned:
                continue
            normalized.add(mapping.get(cleaned, cleaned))

        return normalized

    def _target_bias(self, channel: str, targets: set[str]) -> float:
        if channel in targets:
            return 1.0
        return 0.90

    def _main_shape_multiplier(self, content_shape: ContentShape) -> float:
        mapping = {
            ContentShape.REACTION_DRIVEN: 1.00,
            ContentShape.NEWS_DRIVEN: 0.95,
            ContentShape.TOPIC_DRIVEN: 0.90,
            ContentShape.CLIP_DRIVEN: 0.70,
            ContentShape.SEARCH_DRIVEN: 0.75,
            ContentShape.UNKNOWN: 0.60,
        }
        return mapping.get(content_shape, 0.60)

    def _uncut_shape_multiplier(self, content_shape: ContentShape) -> float:
        mapping = {
            ContentShape.REACTION_DRIVEN: 1.00,
            ContentShape.NEWS_DRIVEN: 0.70,
            ContentShape.TOPIC_DRIVEN: 0.75,
            ContentShape.CLIP_DRIVEN: 0.65,
            ContentShape.SEARCH_DRIVEN: 0.45,
            ContentShape.UNKNOWN: 0.55,
        }
        return mapping.get(content_shape, 0.55)

    def _faceless_shape_multiplier(self, content_shape: ContentShape) -> float:
        mapping = {
            ContentShape.REACTION_DRIVEN: 0.65,
            ContentShape.NEWS_DRIVEN: 0.95,
            ContentShape.TOPIC_DRIVEN: 1.00,
            ContentShape.CLIP_DRIVEN: 0.85,
            ContentShape.SEARCH_DRIVEN: 0.95,
            ContentShape.UNKNOWN: 0.60,
        }
        return mapping.get(content_shape, 0.60)

    def _derive_primary_channel(self, channel_scores: dict[str, float]) -> str | None:
        if not channel_scores:
            return None

        best_channel = None
        best_score = 0.0

        for channel, score in channel_scores.items():
            if score > best_score:
                best_channel = channel
                best_score = score

        if best_score <= 0.0:
            return None

        return best_channel

    def _derive_opportunity_level(self, score: float) -> OpportunityLevel:
        if score >= 85.0:
            return OpportunityLevel.VERY_HIGH
        if score >= 70.0:
            return OpportunityLevel.HIGH
        if score >= 45.0:
            return OpportunityLevel.MEDIUM
        return OpportunityLevel.LOW

    def _derive_upside_factors(
        self,
        *,
        signal: TrendSignal,
        qualification: TrendQualification,
        primary_channel: str | None,
    ) -> list[str]:
        factors: list[str] = []

        if signal.signal_strength >= 0.75:
            factors.append("strong_signal_strength")
        if signal.confidence >= 0.75:
            factors.append("high_confidence")
        if signal.competition_density <= 0.40:
            factors.append("manageable_competition")
        if signal.freshness_hours <= signal.half_life_hours:
            factors.append("still_fresh")
        if qualification.lifespan_class in {LifespanClass.MEDIUM, LifespanClass.LONG}:
            factors.append("durable_lifespan")
        if qualification.decision_hint == DecisionHint.KEEP:
            factors.append("qualification_keep")
        if qualification.content_shape != ContentShape.UNKNOWN:
            factors.append("clear_content_shape")
        if primary_channel:
            factors.append(f"primary_channel_{primary_channel}")

        return factors

    def _derive_downside_factors(
        self,
        *,
        signal: TrendSignal,
        qualification: TrendQualification,
        primary_channel: str | None,
    ) -> list[str]:
        factors: list[str] = list(qualification.risk_flags)

        if qualification.decision_hint == DecisionHint.WATCH:
            factors.append("qualification_watch")
        if qualification.decision_hint == DecisionHint.BLOCK:
            factors.append("qualification_block")
        if not primary_channel:
            factors.append("no_clear_primary_channel")
        if signal.competition_density >= 0.75 and "high_competition" not in factors:
            factors.append("high_competition")
        if signal.confidence < 0.40 and "low_confidence" not in factors:
            factors.append("low_confidence")

        return factors

    def _build_reason(
        self,
        *,
        opportunity_score: float,
        opportunity_level: OpportunityLevel,
        primary_channel: str | None,
        upside_factors: list[str],
        downside_factors: list[str],
    ) -> str:
        primary_text = primary_channel if primary_channel else "none"
        upside_text = ", ".join(upside_factors[:3]) if upside_factors else "none"
        downside_text = ", ".join(downside_factors[:3]) if downside_factors else "none"

        return (
            f"Opportunity scored {opportunity_score:.2f} ({opportunity_level.value}). "
            f"Primary channel: {primary_text}. "
            f"Upside: {upside_text}. "
            f"Downside: {downside_text}."
        )