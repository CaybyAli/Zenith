from __future__ import annotations

from core.reaction_adaptive_thresholds import (
    build_adaptive_reaction_profile,
    classify_adaptive_reaction,
    is_medium_or_high,
    percentile,
)


def test_percentile_uses_distribution_values():
    assert percentile([0.0, 0.10, 0.20, 0.30, 0.40], 50) == 0.20
    assert percentile([0.0, 0.10, 0.20, 0.30, 0.40], 100) == 0.40


def test_mic_primary_adaptive_distribution_separates_quiet_from_payoff():
    candidates = [
        {"fusion_score": 0.02, "mic_audio_rise_db": -8.0},
        {"fusion_score": 0.05, "mic_audio_rise_db": -6.0},
        {"fusion_score": 0.08, "mic_audio_rise_db": -3.0},
        {"fusion_score": 0.10, "mic_audio_rise_db": 0.0},
        {"fusion_score": 0.12, "mic_audio_rise_db": 2.0},
        {"fusion_score": 0.15, "mic_audio_rise_db": 3.441},
        {"fusion_score": 0.368, "mic_audio_rise_db": 6.516},
        {"fusion_score": 0.62, "mic_audio_rise_db": 10.0},
    ]

    profile = build_adaptive_reaction_profile(
        candidates,
        medium_percentile=80,
        high_percentile=95,
        mic_floor_percentile=75,
    )

    quiet = {"fusion_score": 0.15, "mic_audio_rise_db": 3.441}
    payoff = {"fusion_score": 0.368, "mic_audio_rise_db": 6.516}

    assert classify_adaptive_reaction(quiet, profile) == "none"
    assert classify_adaptive_reaction(payoff, profile) == "medium"
    assert is_medium_or_high(classify_adaptive_reaction(payoff, profile))


def test_high_fusion_low_mic_is_not_reaction():
    candidates = [
        {"fusion_score": 0.05, "mic_audio_rise_db": -5.0},
        {"fusion_score": 0.08, "mic_audio_rise_db": -2.0},
        {"fusion_score": 0.12, "mic_audio_rise_db": 1.0},
        {"fusion_score": 0.20, "mic_audio_rise_db": 3.0},
        {"fusion_score": 0.35, "mic_audio_rise_db": 6.0},
        {"fusion_score": 0.70, "mic_audio_rise_db": 10.0},
    ]

    profile = build_adaptive_reaction_profile(
        candidates,
        medium_percentile=60,
        high_percentile=90,
        mic_floor_percentile=70,
    )

    facecam_only = {"fusion_score": 0.95, "mic_audio_rise_db": -1.0}
    assert classify_adaptive_reaction(facecam_only, profile) == "none"


def test_high_mic_with_matching_fusion_becomes_reaction():
    candidates = [
        {"fusion_score": 0.05, "mic_audio_rise_db": -5.0},
        {"fusion_score": 0.08, "mic_audio_rise_db": -2.0},
        {"fusion_score": 0.12, "mic_audio_rise_db": 1.0},
        {"fusion_score": 0.20, "mic_audio_rise_db": 3.0},
        {"fusion_score": 0.35, "mic_audio_rise_db": 6.0},
        {"fusion_score": 0.70, "mic_audio_rise_db": 10.0},
    ]

    profile = build_adaptive_reaction_profile(
        candidates,
        medium_percentile=60,
        high_percentile=90,
        mic_floor_percentile=70,
    )

    reaction = {"fusion_score": 0.40, "mic_audio_rise_db": 7.0}
    assert classify_adaptive_reaction(reaction, profile) in {"medium", "high"}
