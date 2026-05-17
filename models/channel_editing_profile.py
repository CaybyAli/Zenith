from enum import Enum
from dataclasses import dataclass, field

from shared.enums import ChannelType


ChannelProfile = ChannelType


class ContentFamily(str, Enum):
    GAMING = "gaming"
    VLOG = "vlog"
    REACTION = "reaction"


class OutputStyle(str, Enum):
    MAIN = "main"
    UNCUT = "uncut"


@dataclass
class ChannelEditingProfile:
    channel: ChannelProfile
    content_family: ContentFamily
    output_style: OutputStyle

    cut_aggressiveness: float
    dead_time_removal_strength: float
    speech_protection_strength: float
    story_context_weight: float
    gameplay_context_weight: float
    reaction_context_weight: float
    minimum_segment_duration_seconds: float
    max_edge_trim_seconds: float

    music_allowed: bool
    dynamic_zoom_allowed: bool
    facecam_emphasis_allowed: bool
    gameplay_focus_allowed: bool
    fixed_facecam_mode: bool
    subtitles_default: bool

    review_strictness: str
    requires_human_approval: bool

    def to_dict(self) -> dict:
        return {
            "channel": self.channel.value,
            "content_family": self.content_family.value,
            "output_style": self.output_style.value,
            "cut_aggressiveness": self.cut_aggressiveness,
            "dead_time_removal_strength": self.dead_time_removal_strength,
            "speech_protection_strength": self.speech_protection_strength,
            "story_context_weight": self.story_context_weight,
            "gameplay_context_weight": self.gameplay_context_weight,
            "reaction_context_weight": self.reaction_context_weight,
            "minimum_segment_duration_seconds": self.minimum_segment_duration_seconds,
            "max_edge_trim_seconds": self.max_edge_trim_seconds,
            "music_allowed": self.music_allowed,
            "dynamic_zoom_allowed": self.dynamic_zoom_allowed,
            "facecam_emphasis_allowed": self.facecam_emphasis_allowed,
            "gameplay_focus_allowed": self.gameplay_focus_allowed,
            "fixed_facecam_mode": self.fixed_facecam_mode,
            "subtitles_default": self.subtitles_default,
            "review_strictness": self.review_strictness,
            "requires_human_approval": self.requires_human_approval,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChannelEditingProfile":
        return cls(
            channel=ChannelProfile(data["channel"]),
            content_family=ContentFamily(data["content_family"]),
            output_style=OutputStyle(data["output_style"]),
            cut_aggressiveness=data["cut_aggressiveness"],
            dead_time_removal_strength=data["dead_time_removal_strength"],
            speech_protection_strength=data["speech_protection_strength"],
            story_context_weight=data["story_context_weight"],
            gameplay_context_weight=data["gameplay_context_weight"],
            reaction_context_weight=data["reaction_context_weight"],
            minimum_segment_duration_seconds=data["minimum_segment_duration_seconds"],
            max_edge_trim_seconds=data["max_edge_trim_seconds"],
            music_allowed=data["music_allowed"],
            dynamic_zoom_allowed=data["dynamic_zoom_allowed"],
            facecam_emphasis_allowed=data["facecam_emphasis_allowed"],
            gameplay_focus_allowed=data["gameplay_focus_allowed"],
            fixed_facecam_mode=data["fixed_facecam_mode"],
            subtitles_default=data["subtitles_default"],
            review_strictness=data["review_strictness"],
            requires_human_approval=data["requires_human_approval"],
        )


CHANNEL_EDITING_PROFILES: dict[ChannelProfile, ChannelEditingProfile] = {
    ChannelProfile.GAMING_MAIN: ChannelEditingProfile(
        channel=ChannelProfile.GAMING_MAIN,
        content_family=ContentFamily.GAMING,
        output_style=OutputStyle.MAIN,
        cut_aggressiveness=0.85,
        dead_time_removal_strength=0.90,
        speech_protection_strength=0.85,
        story_context_weight=0.70,
        gameplay_context_weight=0.90,
        reaction_context_weight=0.80,
        minimum_segment_duration_seconds=2.0,
        max_edge_trim_seconds=1.5,
        music_allowed=True,
        dynamic_zoom_allowed=True,
        facecam_emphasis_allowed=True,
        gameplay_focus_allowed=True,
        fixed_facecam_mode=False,
        subtitles_default=False,
        review_strictness="strict",
        requires_human_approval=True,
    ),
    ChannelProfile.VLOG_MAIN: ChannelEditingProfile(
        channel=ChannelProfile.VLOG_MAIN,
        content_family=ContentFamily.VLOG,
        output_style=OutputStyle.MAIN,
        cut_aggressiveness=0.60,
        dead_time_removal_strength=0.75,
        speech_protection_strength=0.95,
        story_context_weight=0.95,
        gameplay_context_weight=0.0,
        reaction_context_weight=0.50,
        minimum_segment_duration_seconds=3.0,
        max_edge_trim_seconds=1.0,
        music_allowed=True,
        dynamic_zoom_allowed=True,
        facecam_emphasis_allowed=True,
        gameplay_focus_allowed=False,
        fixed_facecam_mode=False,
        subtitles_default=False,
        review_strictness="strict",
        requires_human_approval=True,
    ),
    ChannelProfile.GAMING_UNCUT: ChannelEditingProfile(
        channel=ChannelProfile.GAMING_UNCUT,
        content_family=ContentFamily.GAMING,
        output_style=OutputStyle.UNCUT,
        cut_aggressiveness=0.20,
        dead_time_removal_strength=0.70,
        speech_protection_strength=0.99,
        story_context_weight=0.50,
        gameplay_context_weight=0.75,
        reaction_context_weight=0.70,
        minimum_segment_duration_seconds=5.0,
        max_edge_trim_seconds=0.5,
        music_allowed=False,
        dynamic_zoom_allowed=False,
        facecam_emphasis_allowed=True,
        gameplay_focus_allowed=True,
        fixed_facecam_mode=True,
        subtitles_default=False,
        review_strictness="light",
        requires_human_approval=False,
    ),
    ChannelProfile.REACTION_UNCUT: ChannelEditingProfile(
        channel=ChannelProfile.REACTION_UNCUT,
        content_family=ContentFamily.REACTION,
        output_style=OutputStyle.UNCUT,
        cut_aggressiveness=0.10,
        dead_time_removal_strength=0.65,
        speech_protection_strength=0.99,
        story_context_weight=0.60,
        gameplay_context_weight=0.30,
        reaction_context_weight=0.99,
        minimum_segment_duration_seconds=8.0,
        max_edge_trim_seconds=0.3,
        music_allowed=False,
        dynamic_zoom_allowed=False,
        facecam_emphasis_allowed=True,
        gameplay_focus_allowed=False,
        fixed_facecam_mode=True,
        subtitles_default=False,
        review_strictness="light",
        requires_human_approval=False,
    ),
    ChannelProfile.VLOG_UNCUT: ChannelEditingProfile(
        channel=ChannelProfile.VLOG_UNCUT,
        content_family=ContentFamily.VLOG,
        output_style=OutputStyle.UNCUT,
        cut_aggressiveness=0.35,
        dead_time_removal_strength=0.80,
        speech_protection_strength=0.95,
        story_context_weight=0.85,
        gameplay_context_weight=0.0,
        reaction_context_weight=0.50,
        minimum_segment_duration_seconds=4.0,
        max_edge_trim_seconds=0.8,
        music_allowed=True,
        dynamic_zoom_allowed=False,
        facecam_emphasis_allowed=True,
        gameplay_focus_allowed=False,
        fixed_facecam_mode=True,
        subtitles_default=False,
        review_strictness="standard",
        requires_human_approval=False,
    ),
}

