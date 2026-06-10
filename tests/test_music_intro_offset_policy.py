from __future__ import annotations

import pytest

from core.music_intro_offset_policy import (
    MusicIntroAnalysis,
    MusicIntroOffsetPolicyError,
    build_intro_offset_decision,
    validate_intro_analysis,
    validate_intro_offset_decision,
)


def _analysis(**overrides):
    item = {
        "music_path": "local_assets/music/main_account/funny_gaming_background/demo.mp3",
        "duration_sec": 120.0,
        "first_usable_audio_sec": 30.0,
        "quiet_intro_detected": True,
        "analysis_status": "ok",
        "reason": "test",
    }
    item.update(overrides)
    return MusicIntroAnalysis(**item)


def test_quiet_intro_at_30_seconds_uses_trimmed_start_offset():
    decision = build_intro_offset_decision(_analysis(first_usable_audio_sec=30.0))
    assert decision.use_start_offset is True
    assert decision.start_offset_sec == 30.0
    assert decision.trim_intro is True
    assert decision.boost_intro is False
    assert decision.boost_gain_db == 0.0
    assert "quiet_intro_trimmed" in decision.reason


def test_usable_audio_near_start_does_not_use_offset():
    decision = build_intro_offset_decision(_analysis(first_usable_audio_sec=3.0))
    assert decision.use_start_offset is False
    assert decision.start_offset_sec == 0.0
    assert decision.trim_intro is False


def test_large_first_usable_audio_is_clamped_to_45_seconds():
    decision = build_intro_offset_decision(
        _analysis(duration_sec=120.0, first_usable_audio_sec=80.0)
    )
    assert decision.use_start_offset is True
    assert decision.start_offset_sec == 45.0
    assert "offset_clamped" in decision.reason


def test_negative_first_usable_audio_is_blocked():
    with pytest.raises(MusicIntroOffsetPolicyError):
        validate_intro_analysis(_analysis(first_usable_audio_sec=-1.0))


def test_non_positive_duration_is_blocked():
    with pytest.raises(MusicIntroOffsetPolicyError):
        validate_intro_analysis(_analysis(duration_sec=0.0))


def test_first_usable_audio_at_or_after_duration_is_blocked():
    with pytest.raises(MusicIntroOffsetPolicyError):
        validate_intro_analysis(_analysis(duration_sec=30.0, first_usable_audio_sec=30.0))


def test_intro_boost_stays_disabled():
    decision = build_intro_offset_decision(_analysis(first_usable_audio_sec=30.0))
    assert decision.boost_intro is False
    assert decision.boost_gain_db == 0.0
    with pytest.raises(MusicIntroOffsetPolicyError):
        validate_intro_offset_decision({**decision.__dict__, "boost_intro": True})
