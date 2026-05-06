from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.multi_indicator_score_fusion import MultiIndicatorScoreFusion
from core.channel_cut_profile_provider import ChannelCutProfileProvider
from models.cut_indicator import CutIndicator, CutIndicatorResult


JOB_ID = "job_fusion_smoke"
_FUSION = MultiIndicatorScoreFusion()
_PROFILE = ChannelCutProfileProvider().get_profile("gaming_main")


def _ind(
    indicator_type: str,
    start: float,
    end: float,
    score: float = 0.80,
    confidence: float = 0.70,
    polarity: str = "positive",
) -> CutIndicator:
    return CutIndicator(
        indicator_id=f"ci_{indicator_type}_{int(start*10)}",
        indicator_type=indicator_type,
        start_seconds=start,
        end_seconds=end,
        score=score,
        confidence=confidence,
        source="smoke",
        reason=f"smoke {indicator_type}",
        polarity=polarity,
        channel_scope="gaming_main",
    )


def _result(*indicators: CutIndicator) -> CutIndicatorResult:
    return CutIndicatorResult(indicators=list(indicators), engine="smoke")


# 1 — No indicators / no profile → score unchanged
def test_no_inputs_score_unchanged() -> None:
    result = _FUSION.fuse(10.0, 30.0, 0.60, None, None)
    assert result["fused_score"] == 0.60
    assert result["indicator_delta"] == 0.0
    assert result["positive_delta"] == 0.0
    assert result["negative_delta"] == 0.0


# 2 — Positive overlapping indicators raise score
def test_positive_indicators_raise_score() -> None:
    base = 0.50
    indicators = _result(
        _ind("high_action_burst", 12.0, 18.0, score=0.80, confidence=0.70, polarity="positive"),
        _ind("goal_or_save_like_flash", 15.0, 20.0, score=0.80, confidence=0.65, polarity="positive"),
    )
    result = _FUSION.fuse(10.0, 30.0, base, indicators, _PROFILE)
    assert result["fused_score"] > base
    assert result["positive_delta"] > 0
    assert result["matched_positive_count"] >= 2


# 3 — Negative overlapping indicators lower score
def test_negative_indicators_lower_score() -> None:
    base = 0.60
    indicators = _result(
        _ind("silence_or_dead_air", 12.0, 25.0, score=0.80, confidence=0.70, polarity="negative"),
        _ind("round_end_dead_time", 20.0, 28.0, score=0.80, confidence=0.65, polarity="negative"),
    )
    result = _FUSION.fuse(10.0, 30.0, base, indicators, _PROFILE)
    assert result["fused_score"] < base
    assert result["negative_delta"] < 0
    assert result["matched_negative_count"] >= 2


# 4 — Positive delta is capped at MAX_POSITIVE_DELTA
def test_positive_delta_capped() -> None:
    base = 0.50
    many_positive = _result(
        *[
            _ind("high_action_burst", 10.0 + i * 0.5, 28.0, score=1.0, confidence=1.0, polarity="positive")
            for i in range(8)
        ]
    )
    result = _FUSION.fuse(10.0, 30.0, base, many_positive, _PROFILE)
    assert result["fused_score"] <= base + MultiIndicatorScoreFusion.MAX_POSITIVE_DELTA + 1e-6
    assert result["positive_delta"] <= MultiIndicatorScoreFusion.MAX_POSITIVE_DELTA + 1e-6


# 5 — Negative delta is capped at MAX_NEGATIVE_DELTA
def test_negative_delta_capped() -> None:
    base = 0.60
    many_negative = _result(
        *[
            _ind("silence_or_dead_air", 10.0 + i * 0.5, 28.0, score=1.0, confidence=1.0, polarity="negative")
            for i in range(8)
        ]
    )
    result = _FUSION.fuse(10.0, 30.0, base, many_negative, _PROFILE)
    assert result["fused_score"] >= base + MultiIndicatorScoreFusion.MAX_NEGATIVE_DELTA - 1e-6
    assert result["negative_delta"] >= MultiIndicatorScoreFusion.MAX_NEGATIVE_DELTA - 1e-6


# 6 — Short indicator near segment (proximity ≤ 0.75s) counts
def test_short_indicator_proximity_counts() -> None:
    base = 0.50
    # indicator ends at 9.5, segment starts at 10.0 → distance = 0.5 ≤ 0.75
    indicators = _result(
        _ind("high_action_burst", 9.0, 9.5, score=0.80, confidence=0.70, polarity="positive"),
    )
    result = _FUSION.fuse(10.0, 30.0, base, indicators, _PROFILE)
    assert result["fused_score"] > base, "Nearby short indicator should boost score"
    assert result["matched_positive_count"] >= 1


# 7 — Unknown indicator type has zero weight → score unchanged
def test_unknown_indicator_no_effect() -> None:
    base = 0.55
    indicators = _result(
        _ind("totally_unknown_type_xyz_999", 12.0, 20.0, score=1.0, confidence=1.0, polarity="neutral"),
    )
    result = _FUSION.fuse(10.0, 30.0, base, indicators, _PROFILE)
    assert result["fused_score"] == base
    assert result["indicator_delta"] == 0.0


# 8 — Notes contain indicator_fusion_delta, positive/negative types, engine
def test_notes_contain_expected_entries() -> None:
    indicators = _result(
        _ind("high_action_burst", 12.0, 18.0, score=0.80, confidence=0.70, polarity="positive"),
        _ind("silence_or_dead_air", 20.0, 28.0, score=0.80, confidence=0.70, polarity="negative"),
    )
    result = _FUSION.fuse(10.0, 30.0, 0.55, indicators, _PROFILE)
    notes = result["notes"]
    assert any("indicator_fusion_delta=" in n for n in notes)
    assert any("indicator_positive=" in n for n in notes)
    assert any("indicator_negative=" in n for n in notes)
    assert any("indicator_fusion_engine=" in n for n in notes)


# 9 — Fused score always stays within 0.0..1.0
def test_fused_score_clamped_to_unit_interval() -> None:
    for base in (0.0, 0.01, 0.5, 0.99, 1.0):
        r_pos = _FUSION.fuse(
            10.0, 30.0, base,
            _result(_ind("high_action_burst", 10.0, 30.0, score=1.0, confidence=1.0)),
            _PROFILE,
        )
        r_neg = _FUSION.fuse(
            10.0, 30.0, base,
            _result(_ind("silence_or_dead_air", 10.0, 30.0, score=1.0, confidence=1.0)),
            _PROFILE,
        )
        assert 0.0 <= r_pos["fused_score"] <= 1.0, f"Out of range for base={base} (positive)"
        assert 0.0 <= r_neg["fused_score"] <= 1.0, f"Out of range for base={base} (negative)"

    print("MULTI INDICATOR SCORE FUSION SMOKE TEST PASSED")
    print(f"engine={MultiIndicatorScoreFusion.engine}")
    print(f"MAX_POSITIVE_DELTA={MultiIndicatorScoreFusion.MAX_POSITIVE_DELTA}")
    print(f"MAX_NEGATIVE_DELTA={MultiIndicatorScoreFusion.MAX_NEGATIVE_DELTA}")


if __name__ == "__main__":
    test_no_inputs_score_unchanged()
    test_positive_indicators_raise_score()
    test_negative_indicators_lower_score()
    test_positive_delta_capped()
    test_negative_delta_capped()
    test_short_indicator_proximity_counts()
    test_unknown_indicator_no_effect()
    test_notes_contain_expected_entries()
    test_fused_score_clamped_to_unit_interval()
