import logging

from shared.enums import ACTIVE_CHANNEL_TYPES

from models.quality_mode import QualityMode, QualityModeConfig, get_quality_mode_config
from models.channel_editing_profile import (
    ChannelProfile,
    ChannelEditingProfile,
    CHANNEL_EDITING_PROFILES,
)


logger = logging.getLogger(__name__)

DEFAULT_QUALITY_MODE = QualityMode.PRO
DEFAULT_CHANNEL_PROFILE = ChannelProfile.GAMING_MAIN


def resolve_quality_mode(mode_str: str) -> QualityMode:
    """
    Parst einen String zu QualityMode.
    Unbekannte Werte fallen auf PRO zurück.
    """
    try:
        return QualityMode(str(mode_str or "").lower())
    except ValueError:
        logger.warning(
            f"[EditingProfileRegistry] Unbekannter QualityMode '{mode_str}' "
            f"— Fallback auf '{DEFAULT_QUALITY_MODE.value}'"
        )
        return DEFAULT_QUALITY_MODE


def resolve_channel_profile(channel_str: str) -> ChannelProfile:
    """
    Parst einen String zu ChannelProfile.
    Nur aktive 5 Kanäle bekommen ein Editing-Profil.
    Unbekannte oder inaktive Werte fallen auf GAMING_MAIN zurück.
    """
    try:
        channel = ChannelProfile(str(channel_str or "").lower())
        if channel in ACTIVE_CHANNEL_TYPES:
            return channel
        raise ValueError
    except ValueError:
        logger.warning(
            f"[EditingProfileRegistry] Unbekannter oder inaktiver ChannelProfile '{channel_str}' "
            f"— Fallback auf '{DEFAULT_CHANNEL_PROFILE.value}'"
        )
        return DEFAULT_CHANNEL_PROFILE


def resolve(
    channel_str: str,
    quality_mode_str: str,
) -> tuple[ChannelEditingProfile, QualityModeConfig]:
    """
    Gibt (ChannelEditingProfile, QualityModeConfig) zurück.
    Immer sicher — kein Crash bei unbekannten Werten.
    """
    channel = resolve_channel_profile(channel_str)
    mode = resolve_quality_mode(quality_mode_str)
    profile = CHANNEL_EDITING_PROFILES[channel]
    mode_config = get_quality_mode_config(mode)
    return profile, mode_config

