from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.channel_cut_profile_provider import ChannelCutProfileProvider


def test_gaming_main_profile_exists() -> None:
    profile = ChannelCutProfileProvider().get_profile("gaming_main")
    assert profile is not None
    assert profile.profile_name == "gaming_main"


def test_gaming_main_weights() -> None:
    profile = ChannelCutProfileProvider().get_profile("gaming_main")
    assert profile.get_weight("high_action_burst") > 0
    assert profile.get_weight("silence_or_dead_air") < 0


def test_gaming_main_pacing() -> None:
    profile = ChannelCutProfileProvider().get_profile("gaming_main")
    assert profile.target_pacing == "aggressive"
    assert profile.min_segment_duration_seconds == 2.5
    assert profile.max_segment_duration_seconds == 18.0


def test_gaming_uncut_min_seg_greater_than_gaming_main() -> None:
    gaming_main = ChannelCutProfileProvider().get_profile("gaming_main")
    gaming_uncut = ChannelCutProfileProvider().get_profile("gaming_uncut")
    assert gaming_uncut.min_segment_duration_seconds > gaming_main.min_segment_duration_seconds


def test_vlog_main_speech_weight_greater_than_gameplay() -> None:
    profile = ChannelCutProfileProvider().get_profile("vlog_main")
    assert profile.speech_safety_weight > profile.gameplay_weight


def test_reaction_uncut_weights() -> None:
    profile = ChannelCutProfileProvider().get_profile("reaction_uncut")
    assert profile.get_weight("group_reaction_like") > 0
    assert profile.get_weight("shock_like") > 0


def test_shorts_weights() -> None:
    profile = ChannelCutProfileProvider().get_profile("shorts")
    assert profile.get_weight("hook_sentence") >= 1.0
    assert profile.get_weight("silence_or_dead_air") <= -1.0


def test_unknown_channel_returns_default() -> None:
    profile = ChannelCutProfileProvider().get_profile("totally_unknown_channel_xyz_99")
    assert profile is not None
    assert profile.profile_name == "default"


def test_get_weight_unknown_key_returns_zero() -> None:
    profile = ChannelCutProfileProvider().get_profile("gaming_main")
    assert profile.get_weight("nonexistent_indicator_key_xyz") == 0.0


def test_to_dict_contains_expected_top_level_keys() -> None:
    profile = ChannelCutProfileProvider().get_profile("gaming_main")
    d = profile.to_dict()
    expected_keys = [
        "profile_name",
        "channel_type",
        "description",
        "indicator_weights",
        "positive_indicator_types",
        "negative_indicator_types",
        "neutral_indicator_types",
        "min_segment_duration_seconds",
        "max_segment_duration_seconds",
        "target_pacing",
        "speech_safety_weight",
        "gameplay_weight",
        "facecam_weight",
        "audio_reaction_weight",
        "story_weight",
        "dead_air_penalty_weight",
        "micro_cut_penalty_weight",
        "duplicate_penalty_weight",
        "metadata",
    ]
    for key in expected_keys:
        assert key in d, f"Missing key in to_dict(): {key}"

    print("CHANNEL CUT PROFILE SMOKE TEST PASSED")
    print(f"profile_name={d['profile_name']}")
    print(f"target_pacing={d['target_pacing']}")
    print(f"min_seg={d['min_segment_duration_seconds']}")
    print(f"max_seg={d['max_segment_duration_seconds']}")
    print(f"indicator_weights_count={len(d['indicator_weights'])}")


if __name__ == "__main__":
    test_gaming_main_profile_exists()
    test_gaming_main_weights()
    test_gaming_main_pacing()
    test_gaming_uncut_min_seg_greater_than_gaming_main()
    test_vlog_main_speech_weight_greater_than_gameplay()
    test_reaction_uncut_weights()
    test_shorts_weights()
    test_unknown_channel_returns_default()
    test_get_weight_unknown_key_returns_zero()
    test_to_dict_contains_expected_top_level_keys()
