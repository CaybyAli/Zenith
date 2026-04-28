from __future__ import annotations

from app import is_music_intelligence_enabled_for_channel
from shared.enums import ChannelType


def main() -> None:
    assert is_music_intelligence_enabled_for_channel(ChannelType.GAMING_MAIN) is True
    assert is_music_intelligence_enabled_for_channel(ChannelType.GAMING_UNCUT) is False
    assert is_music_intelligence_enabled_for_channel(ChannelType.FACELESS_TREND) is False

    print("MUSIC CHANNEL POLICY SMOKE TEST PASSED")
    print(
        {
            "gaming_main": is_music_intelligence_enabled_for_channel(ChannelType.GAMING_MAIN),
            "gaming_uncut": is_music_intelligence_enabled_for_channel(ChannelType.GAMING_UNCUT),
            "faceless_trend": is_music_intelligence_enabled_for_channel(ChannelType.FACELESS_TREND),
        }
    )


if __name__ == "__main__":
    main()