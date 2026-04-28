from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class ChannelPolicy:
    channel_type: str
    channel_group: str
    platform: str = "youtube"
    enabled: bool = True
    requires_manual_approval: bool = True
    publish_days: List[int] = field(default_factory=list)
    publish_hour: int = 17
    publish_minute: int = 0
    upload_every_hours: int = 24
    shorts_enabled: bool = False
    shorts_source_channels: List[str] = field(default_factory=list)
    retry_attempts: int = 3
    retry_delay_minutes: int = 15


CHANNEL_POLICIES: Dict[str, ChannelPolicy] = {
    "gaming_main": ChannelPolicy(
        channel_type="gaming_main",
        channel_group="main",
        platform="youtube",
        enabled=True,
        requires_manual_approval=True,
        publish_days=[0, 1, 2, 3, 4, 5, 6],
        publish_hour=17,
        publish_minute=0,
        upload_every_hours=24,
        shorts_enabled=True,
        shorts_source_channels=["gaming_main"],
        retry_attempts=3,
        retry_delay_minutes=15,
    ),
    "gaming_uncut": ChannelPolicy(
        channel_type="gaming_uncut",
        channel_group="uncut",
        platform="youtube",
        enabled=True,
        requires_manual_approval=True,
        publish_days=[0, 1, 2, 3, 4, 5, 6],
        publish_hour=17,
        publish_minute=0,
        upload_every_hours=24,
        shorts_enabled=False,
        shorts_source_channels=[],
        retry_attempts=3,
        retry_delay_minutes=15,
    ),
    "faceless_trend": ChannelPolicy(
        channel_type="faceless_trend",
        channel_group="faceless",
        platform="youtube",
        enabled=False,
        requires_manual_approval=True,
        publish_days=[0, 1, 2, 3, 4, 5, 6],
        publish_hour=17,
        publish_minute=0,
        upload_every_hours=24,
        shorts_enabled=False,
        shorts_source_channels=[],
        retry_attempts=3,
        retry_delay_minutes=15,
    ),
}


def get_channel_policy(channel_type: str) -> ChannelPolicy:
    policy = CHANNEL_POLICIES.get(channel_type)

    if policy is None:
        raise ValueError(f"Unknown channel_type: {channel_type}")

    return policy


def get_all_channel_policies() -> List[ChannelPolicy]:
    return list(CHANNEL_POLICIES.values())


def get_enabled_channel_policies() -> List[ChannelPolicy]:
    return [
        policy
        for policy in CHANNEL_POLICIES.values()
        if policy.enabled
    ]


def is_channel_enabled(channel_type: str) -> bool:
    return get_channel_policy(channel_type).enabled


def get_shorts_source_channels(channel_type: str) -> List[str]:
    return get_channel_policy(channel_type).shorts_source_channels


def requires_manual_approval(channel_type: str) -> bool:
    return get_channel_policy(channel_type).requires_manual_approval


def get_upload_every_hours(channel_type: str) -> int:
    return get_channel_policy(channel_type).upload_every_hours


def get_publish_days(channel_type: str) -> List[int]:
    return get_channel_policy(channel_type).publish_days

def get_publish_hour(channel_type: str) -> int:
    return get_channel_policy(channel_type).publish_hour


def get_publish_minute(channel_type: str) -> int:
    return get_channel_policy(channel_type).publish_minute


def get_retry_attempts(channel_type: str) -> int:
    return get_channel_policy(channel_type).retry_attempts


def get_retry_delay_minutes(channel_type: str) -> int:
    return get_channel_policy(channel_type).retry_delay_minutes


def get_channel_group(channel_type: str) -> str:
    return get_channel_policy(channel_type).channel_group


def get_platform(channel_type: str) -> str:
    return get_channel_policy(channel_type).platform


def get_enabled_channel_types() -> List[str]:
    return [
        policy.channel_type
        for policy in get_enabled_channel_policies()
    ]