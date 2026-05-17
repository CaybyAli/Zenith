from shared.enums import ACTIVE_CHANNEL_TYPES, ChannelType
from models.channel_editing_profile import ChannelProfile, CHANNEL_EDITING_PROFILES


def test_channel_profile_uses_shared_channel_type():
    assert ChannelProfile is ChannelType


def test_active_channel_types_are_exactly_five():
    assert list(ACTIVE_CHANNEL_TYPES) == [
        ChannelType.GAMING_MAIN,
        ChannelType.VLOG_MAIN,
        ChannelType.GAMING_UNCUT,
        ChannelType.REACTION_UNCUT,
        ChannelType.VLOG_UNCUT,
    ]


def test_every_active_channel_has_editing_profile():
    for channel in ACTIVE_CHANNEL_TYPES:
        assert channel in CHANNEL_EDITING_PROFILES


def test_faceless_trend_is_kept_but_inactive_for_phase_15():
    assert ChannelType.FACELESS_TREND not in ACTIVE_CHANNEL_TYPES
    assert ChannelType.FACELESS_TREND not in CHANNEL_EDITING_PROFILES
