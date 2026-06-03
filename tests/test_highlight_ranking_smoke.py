from __future__ import annotations

from core.highlight_ranking import (
    HighlightRankingConfig,
    default_highlight_target_seconds,
    rank_highlight_segments,
)


def _flat_windows(start: float, end: float, value: str = "0.20"):
    step = (end - start) / 5.0
    return [
        {"start_seconds": start + step * i, "end_seconds": start + step * (i + 1), "audio_peak_score": value}
        for i in range(5)
    ]


def _prominent_windows(start: float, end: float):
    step = (end - start) / 5.0
    values = ["0.10", "0.10", "1.00", "0.10", "0.10"]
    return [
        {"start_seconds": start + step * i, "end_seconds": start + step * (i + 1), "audio_peak_score": values[i]}
        for i in range(5)
    ]


def test_high_reaction_segment_is_kept_even_when_budget_is_full():
    content_segments = [
        {"segment_id": "low", "start_seconds": 0.0, "end_seconds": 60.0},
        {"segment_id": "high_reaction", "start_seconds": 60.0, "end_seconds": 120.0},
    ]
    raw_windows = _flat_windows(0.0, 60.0, "0.10") + _prominent_windows(60.0, 120.0)
    reactions = [
        {"start_seconds": 70.0, "end_seconds": 72.0, "level": "HIGH"},
    ]

    output_segments, audit = rank_highlight_segments(
        content_segments=content_segments,
        raw_windows=raw_windows,
        reactions=reactions,
        combined_speech_regions=[],
        target_seconds=60.0,
        config=HighlightRankingConfig(min_target_seconds=0.0),
    )

    assert any(seg["start_seconds"] == 60.0 and seg["end_seconds"] == 120.0 for seg in output_segments)
    high_row = next(row for row in audit["ranked_rows"] if row["start_seconds"] == 60.0)
    assert high_row["kept"] is True
    assert high_row["high_reaction_corrobated"] is True
    assert high_row["keep_reason"] == "MANDATORY_HIGH_REACTION"


def test_payoff_tail_marker_segment_is_kept_even_when_budget_is_full():
    content_segments = [
        {"segment_id": "strong", "start_seconds": 0.0, "end_seconds": 60.0},
        {"segment_id": "payoff", "start_seconds": 60.0, "end_seconds": 120.0},
    ]
    raw_windows = _prominent_windows(0.0, 60.0) + _flat_windows(60.0, 120.0, "0.05")
    payoff_tail_segments = [
        {"start_seconds": 70.0, "end_seconds": 90.0, "payoff_tail": True, "source": "payoff_2"},
    ]

    output_segments, audit = rank_highlight_segments(
        content_segments=content_segments,
        raw_windows=raw_windows,
        reactions=[],
        payoff_tail_segments=payoff_tail_segments,
        combined_speech_regions=[],
        target_seconds=60.0,
        config=HighlightRankingConfig(min_target_seconds=0.0),
    )

    assert any(seg["start_seconds"] == 60.0 and seg["end_seconds"] == 120.0 for seg in output_segments)
    payoff_row = next(row for row in audit["ranked_rows"] if row["start_seconds"] == 60.0)
    assert payoff_row["kept"] is True
    assert payoff_row["mandatory_payoff_tail"] is True
    assert payoff_row["keep_reason"] == "MANDATORY_PAYOFF_TAIL"


def test_tight_budget_drops_lowest_score_whole_segment_not_cut():
    content_segments = [
        {"segment_id": "best", "start_seconds": 0.0, "end_seconds": 60.0},
        {"segment_id": "middle", "start_seconds": 60.0, "end_seconds": 120.0},
        {"segment_id": "weak", "start_seconds": 120.0, "end_seconds": 180.0},
    ]
    raw_windows = [
        {"start_seconds": 0.0, "end_seconds": 20.0, "audio_peak_score": "0.10"},
        {"start_seconds": 20.0, "end_seconds": 40.0, "audio_peak_score": "1.00"},
        {"start_seconds": 40.0, "end_seconds": 60.0, "audio_peak_score": "0.10"},
        {"start_seconds": 60.0, "end_seconds": 80.0, "audio_peak_score": "0.10"},
        {"start_seconds": 80.0, "end_seconds": 100.0, "audio_peak_score": "0.70"},
        {"start_seconds": 100.0, "end_seconds": 120.0, "audio_peak_score": "0.10"},
        {"start_seconds": 120.0, "end_seconds": 180.0, "audio_peak_score": "0.10"},
    ]
    speech = [
        {"start_seconds": 0.0, "end_seconds": 50.0},
        {"start_seconds": 60.0, "end_seconds": 90.0},
    ]

    output_segments, audit = rank_highlight_segments(
        content_segments=content_segments,
        raw_windows=raw_windows,
        reactions=[],
        combined_speech_regions=speech,
        target_seconds=120.0,
        config=HighlightRankingConfig(min_target_seconds=0.0),
    )

    assert len(output_segments) == 2
    assert all(seg["duration_seconds"] == 60.0 for seg in output_segments)
    assert audit["hard_checks"]["no_mid_segment_cut"] == "JA"

    dropped = [row for row in audit["ranked_rows"] if row["kept"] is False]
    assert len(dropped) == 1
    assert dropped[0]["start_seconds"] == 120.0
    assert dropped[0]["end_seconds"] == 180.0


def test_adaptive_target_30min_and_8min_floor():
    config = HighlightRankingConfig()

    target_30_min = default_highlight_target_seconds(1800.0, config)
    target_8_min = default_highlight_target_seconds(480.0, config)

    assert 720.0 <= target_30_min <= 780.0
    assert target_8_min == 480.0


def test_reaction_intensity_high_is_read_as_high_reaction_strength():
    content_segments = [
        {"segment_id": "normal", "start_seconds": 0.0, "end_seconds": 60.0},
        {"segment_id": "reaction", "start_seconds": 60.0, "end_seconds": 120.0},
    ]
    raw_windows = _flat_windows(0.0, 60.0, "0.10") + _prominent_windows(60.0, 120.0)
    reactions = [
        {
            "start_seconds": 70.0,
            "end_seconds": 72.0,
            "intensity": "HIGH",
            "fusion_score": "0.42",
            "mic_primary_gate_pass": True,
        },
    ]

    output_segments, audit = rank_highlight_segments(
        content_segments=content_segments,
        raw_windows=raw_windows,
        reactions=reactions,
        combined_speech_regions=[],
        target_seconds=60.0,
        config=HighlightRankingConfig(min_target_seconds=0.0),
    )

    reaction_row = next(row for row in audit["ranked_rows"] if row["start_seconds"] == 60.0)
    assert reaction_row["reaction_max"] == "high"
    assert reaction_row["reaction_strength"] == 1.0
    assert reaction_row["mandatory_high_reaction"] is True
    assert reaction_row["high_reaction_corrobated"] is True
    assert reaction_row["kept"] is True
    assert reaction_row["keep_reason"] == "MANDATORY_HIGH_REACTION"
    assert any(seg["start_seconds"] == 60.0 and seg["end_seconds"] == 120.0 for seg in output_segments)


def test_high_reaction_low_audio_prominence_is_boost_not_mandatory():
    content_segments = [
        {"segment_id": "real_action", "start_seconds": 0.0, "end_seconds": 60.0},
        {"segment_id": "loud_talk", "start_seconds": 60.0, "end_seconds": 120.0},
        {"segment_id": "quiet", "start_seconds": 120.0, "end_seconds": 180.0},
    ]
    raw_windows = (
        _prominent_windows(0.0, 60.0)
        + _flat_windows(60.0, 120.0, "0.20")
        + _flat_windows(120.0, 180.0, "0.10")
    )
    reactions = [
        {"start_seconds": 70.0, "end_seconds": 72.0, "intensity": "HIGH", "fusion_score": "0.50"},
    ]

    _, audit = rank_highlight_segments(
        content_segments=content_segments,
        raw_windows=raw_windows,
        reactions=reactions,
        combined_speech_regions=[],
        target_seconds=60.0,
        config=HighlightRankingConfig(min_target_seconds=0.0),
    )

    loud_talk = next(row for row in audit["ranked_rows"] if row["start_seconds"] == 60.0)

    assert loud_talk["reaction_max"] == "high"
    assert loud_talk["reaction_strength"] == 1.0
    assert loud_talk["mandatory_high_reaction"] is True
    assert loud_talk["high_reaction_corrobated"] is False
    assert loud_talk["mandatory_keep"] is False
    assert loud_talk["keep_reason"] != "MANDATORY_HIGH_REACTION"


def test_hard_checks_use_configured_protected_ranges():
    protected_ranges = {
        "combat": {"start_seconds": 142.0, "end_seconds": 246.0},
        "payoff": {"start_seconds": 1756.0, "end_seconds": 1810.817},
    }
    content_segments = [
        {"segment_id": "combat", "start_seconds": 142.0, "end_seconds": 246.0, "mandatory_keep": True},
        {"segment_id": "payoff", "start_seconds": 1756.0, "end_seconds": 1810.817, "payoff_tail": True},
    ]
    raw_windows = _flat_windows(142.0, 246.0) + _flat_windows(1756.0, 1810.817)

    _, audit = rank_highlight_segments(
        content_segments=content_segments,
        raw_windows=raw_windows,
        reactions=[],
        payoff_tail_segments=[content_segments[1]],
        combined_speech_regions=[],
        target_seconds=240.0,
        config=HighlightRankingConfig(min_target_seconds=0.0, protected_ranges=protected_ranges),
    )

    hard = audit["hard_checks"]
    # alt: round1_fight_142_246_kept -> neu: combat_range_kept.
    # Grund: Die Bounds kommen aus per-video protected_ranges statt aus Fortnite-Codekonstanten.
    assert hard["combat_range_kept"]["target"] == [142.0, 246.0]
    assert hard["combat_range_kept"]["status"] == "JA"
    # alt: death_payoff_*_kept -> neu: payoff_range_kept.
    # Grund: Der Payoff-Bereich wird als Config-Range geprueft, nicht als festes Fortnite-Subfenster.
    assert hard["payoff_range_kept"]["target"] == [1756.0, 1810.817]
    assert hard["payoff_range_kept"]["status"] == "JA"
