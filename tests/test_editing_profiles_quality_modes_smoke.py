import pytest

from models.quality_mode import QualityMode, get_quality_mode_config
from models.channel_editing_profile import (
    ChannelProfile,
    ChannelEditingProfile,
    CHANNEL_EDITING_PROFILES,
)
from core.editing_profile_registry import (
    resolve_quality_mode,
    resolve_channel_profile,
    resolve,
)


def test_all_quality_modes_exist():
    for mode in [QualityMode.FAST, QualityMode.BALANCED, QualityMode.PRO, QualityMode.CINEMATIC]:
        cfg = get_quality_mode_config(mode)
        assert cfg.mode == mode
        assert cfg.analysis_depth in ("surface", "standard", "deep", "maximum")
        assert 0.0 <= cfg.min_confidence_threshold <= 1.0


def test_cinematic_allows_overnight():
    cfg = get_quality_mode_config(QualityMode.CINEMATIC)
    assert cfg.allow_overnight_render is True


def test_fast_no_overnight():
    cfg = get_quality_mode_config(QualityMode.FAST)
    assert cfg.allow_overnight_render is False


def test_unknown_quality_mode_falls_back_to_pro():
    mode = resolve_quality_mode("unknown_xyz")
    assert mode == QualityMode.PRO


def test_quality_mode_string_parsing():
    assert resolve_quality_mode("fast") == QualityMode.FAST
    assert resolve_quality_mode("balanced") == QualityMode.BALANCED
    assert resolve_quality_mode("pro") == QualityMode.PRO
    assert resolve_quality_mode("cinematic") == QualityMode.CINEMATIC


def test_all_channel_profiles_exist():
    for profile in ChannelProfile:
        assert profile in CHANNEL_EDITING_PROFILES
        p = CHANNEL_EDITING_PROFILES[profile]
        assert isinstance(p, ChannelEditingProfile)


def test_unknown_channel_falls_back_to_gaming_main():
    channel = resolve_channel_profile("unknown_channel_xyz")
    assert channel == ChannelProfile.GAMING_MAIN


def test_gaming_uncut_no_music_fixed_facecam():
    p = CHANNEL_EDITING_PROFILES[ChannelProfile.GAMING_UNCUT]
    assert p.music_allowed is False
    assert p.fixed_facecam_mode is True
    assert p.cut_aggressiveness < 0.5


def test_reaction_uncut_minimal_cut():
    p = CHANNEL_EDITING_PROFILES[ChannelProfile.REACTION_UNCUT]
    assert p.cut_aggressiveness <= 0.15
    assert p.requires_human_approval is False


def test_gaming_main_aggressive_cut():
    p = CHANNEL_EDITING_PROFILES[ChannelProfile.GAMING_MAIN]
    assert p.cut_aggressiveness >= 0.80
    assert p.music_allowed is True
    assert p.requires_human_approval is True


def test_to_dict_from_dict_roundtrip():
    for profile in ChannelProfile:
        p = CHANNEL_EDITING_PROFILES[profile]
        d = p.to_dict()
        restored = ChannelEditingProfile.from_dict(d)
        assert restored.channel == p.channel
        assert restored.cut_aggressiveness == p.cut_aggressiveness
        assert restored.music_allowed == p.music_allowed
        assert restored.fixed_facecam_mode == p.fixed_facecam_mode


def test_registry_resolve_returns_tuple():
    profile, mode_config = resolve("gaming_main", "pro")
    assert profile.channel == ChannelProfile.GAMING_MAIN
    assert mode_config.mode == QualityMode.PRO


def test_registry_resolve_unknown_values_use_defaults():
    profile, mode_config = resolve("garbage_channel", "garbage_mode")
    assert profile.channel == ChannelProfile.GAMING_MAIN
    assert mode_config.mode == QualityMode.PRO


def test_registry_all_channel_quality_combinations():
    for channel in ChannelProfile:
        for mode in QualityMode:
            profile, mode_cfg = resolve(channel.value, mode.value)
            assert profile is not None
            assert mode_cfg is not None
