from __future__ import annotations

from typing import Any


class MultiIndicatorScoreFusion:
    engine = "multi-indicator-score-fusion-v1"

    MAX_POSITIVE_DELTA = 0.22
    MAX_NEGATIVE_DELTA = -0.28
    MIN_OVERLAP_RATIO = 0.10
    STRONG_OVERLAP_RATIO = 0.35
    MAX_INDICATORS_PER_SEGMENT = 12
    INDICATOR_SCALE = 0.12

    def _overlap_ratio(
        self,
        seg_start: float,
        seg_end: float,
        ind_start: float,
        ind_end: float,
    ) -> float:
        overlap_start = max(seg_start, ind_start)
        overlap_end = min(seg_end, ind_end)
        if overlap_end <= overlap_start:
            return 0.0
        overlap = overlap_end - overlap_start
        shorter = max(0.001, min(seg_end - seg_start, ind_end - ind_start))
        return overlap / shorter

    def _compute_match(
        self,
        seg_start: float,
        seg_end: float,
        ind_start: float,
        ind_end: float,
    ) -> tuple[bool, float]:
        ratio = self._overlap_ratio(seg_start, seg_end, ind_start, ind_end)
        if ratio >= self.MIN_OVERLAP_RATIO:
            factor = 1.0 if ratio >= self.STRONG_OVERLAP_RATIO else 0.5
            return True, factor
        ind_dur = ind_end - ind_start
        if ind_dur <= 2.0:
            if ind_end < seg_start:
                dist = seg_start - ind_end
            elif ind_start > seg_end:
                dist = ind_start - seg_end
            else:
                dist = 0.0
            if dist <= 0.75:
                return True, 0.5
        return False, 0.0

    def fuse(
        self,
        start: float,
        end: float,
        base_score: float,
        cut_indicator_result: Any,
        cut_scoring_profile: Any,
    ) -> dict[str, Any]:
        if cut_indicator_result is None or cut_scoring_profile is None:
            return {
                "fused_score": round(max(0.0, min(1.0, base_score)), 3),
                "indicator_delta": 0.0,
                "positive_delta": 0.0,
                "negative_delta": 0.0,
                "matched_positive_count": 0,
                "matched_negative_count": 0,
                "matched_neutral_count": 0,
                "top_positive_indicators": [],
                "top_negative_indicators": [],
                "notes": [],
            }

        indicators = getattr(cut_indicator_result, "indicators", None) or []

        candidate_effects: list[tuple[str, float]] = []

        for ind in indicators:
            ind_start = float(getattr(ind, "start_seconds", 0.0) or 0.0)
            ind_end = float(getattr(ind, "end_seconds", ind_start) or ind_start)
            ind_type = str(getattr(ind, "indicator_type", "") or "")
            ind_score = float(getattr(ind, "score", 0.0) or 0.0)
            ind_conf = float(getattr(ind, "confidence", 0.0) or 0.0)

            matches, overlap_factor = self._compute_match(start, end, ind_start, ind_end)
            if not matches:
                continue

            weight = cut_scoring_profile.get_weight(ind_type)
            if weight == 0.0:
                continue

            effect = weight * ind_score * ind_conf * overlap_factor * self.INDICATOR_SCALE
            candidate_effects.append((ind_type, effect))

        candidate_effects.sort(key=lambda x: -abs(x[1]))
        candidate_effects = candidate_effects[: self.MAX_INDICATORS_PER_SEGMENT]

        positive_effects: list[tuple[str, float]] = []
        negative_effects: list[tuple[str, float]] = []
        matched_neutral_count = 0
        positive_raw = 0.0
        negative_raw = 0.0

        for ind_type, effect in candidate_effects:
            if effect > 0:
                positive_effects.append((ind_type, effect))
                positive_raw += effect
            elif effect < 0:
                negative_effects.append((ind_type, effect))
                negative_raw += effect
            else:
                matched_neutral_count += 1

        positive_delta = round(min(positive_raw, self.MAX_POSITIVE_DELTA), 4)
        negative_delta = round(max(negative_raw, self.MAX_NEGATIVE_DELTA), 4)
        indicator_delta = round(positive_delta + negative_delta, 4)

        fused_score = round(max(0.0, min(1.0, base_score + indicator_delta)), 3)

        top_positive = [t for t, _ in positive_effects[:3]]
        top_negative = [t for t, _ in negative_effects[:3]]

        notes: list[str] = []
        delta_str = f"+{indicator_delta:.3f}" if indicator_delta >= 0 else f"{indicator_delta:.3f}"
        notes.append(f"indicator_fusion_delta={delta_str}")
        if top_positive:
            notes.append(f"indicator_positive={','.join(top_positive)}")
        if top_negative:
            notes.append(f"indicator_negative={','.join(top_negative)}")
        notes.append(f"indicator_fusion_engine={self.engine}")

        return {
            "fused_score": fused_score,
            "indicator_delta": indicator_delta,
            "positive_delta": positive_delta,
            "negative_delta": negative_delta,
            "matched_positive_count": len(positive_effects),
            "matched_negative_count": len(negative_effects),
            "matched_neutral_count": matched_neutral_count,
            "top_positive_indicators": top_positive,
            "top_negative_indicators": top_negative,
            "notes": notes,
        }
