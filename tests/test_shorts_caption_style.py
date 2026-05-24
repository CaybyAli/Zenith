from __future__ import annotations

from pathlib import Path

from core.audio_normalizer import AudioNormalizer
from core.power_profile import PowerProfile
from core.shorts_render_driver import ShortsRenderDriver, VideoCodecChoice
from core.subtitle_ffmpeg_builder import SubtitleFFmpegBuilder
from core.subtitle_generator import SubtitleGenerator, SubtitleSegment, SubtitleStyle
from models.shorts_clip import ShortsClip
from models.shorts_reframe_plan import ShortsReframePlan

JOB_ID = "job_shorts_caption_style_test"
SOURCE_VIDEO_NAME = "source.mp4"
FAKE_FFMPEG_BINARY = "fake_ffmpeg_binary"
TEST_VIDEO_ENCODER = "test_video_encoder"
TEST_PROBE_CODEC = "test_probe_codec"


class FakeFFmpegHelper:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def get_ffmpeg_path(self) -> str:
        return FAKE_FFMPEG_BINARY

    def build_ffmpeg_cmd(self, parts: list[str]) -> list[str]:
        return list(parts)

    def run_ffmpeg(self, cmd: list[str]) -> None:
        self.commands.append(list(cmd))


class FakeCodecResolver:
    def resolve_video_codec(self, prefer_nvenc: bool) -> VideoCodecChoice:
        return VideoCodecChoice(
            encoder=TEST_VIDEO_ENCODER,
            uses_nvenc=False,
            probe_codec_names=(TEST_PROBE_CODEC,),
        )


def _clip(*, hook_score: float, llm_rationale: str, add_plan: bool = True) -> ShortsClip:
    return ShortsClip(
        source_job_id=JOB_ID,
        source_start_time=0.0,
        source_end_time=8.0,
        planned_duration=8.0,
        reframe_plan=(
            ShortsReframePlan(
                layout_type="gameplay_centered",
                ffmpeg_crop_filter="crop=1080:1920:420:0",
            )
            if add_plan
            else None
        ),
        hook_score=hook_score,
        llm_rationale=llm_rationale,
        clip_index=0,
    )


def _driver() -> tuple[ShortsRenderDriver, FakeFFmpegHelper]:
    helper = FakeFFmpegHelper()
    driver = ShortsRenderDriver(
        ffmpeg_helper=helper,
        ffmpeg_capability_resolver=FakeCodecResolver(),
        audio_normalizer=AudioNormalizer(),
        power_profile=PowerProfile.BALANCED,
    )
    return driver, helper


def _command_text(helper: FakeFFmpegHelper) -> str:
    return " ".join(helper.commands[0])


def test_mobile_first_contains_fontsize_86() -> None:
    filter_string = SubtitleFFmpegBuilder.build_filter(["HELLO"], style="mobile_first")

    assert "fontsize=86" in filter_string


def test_mobile_first_contains_mobile_y_position() -> None:
    filter_string = SubtitleFFmpegBuilder.build_filter(["HELLO"], style="mobile_first")

    assert "y=h*0.62" in filter_string


def test_mobile_first_disables_big_background_box() -> None:
    filter_string = SubtitleFFmpegBuilder.build_filter(["HELLO"], style="mobile_first")

    assert "box=0" in filter_string


def test_mobile_first_contains_outline_and_shadow() -> None:
    filter_string = SubtitleFFmpegBuilder.build_filter(["HELLO"], style="mobile_first")

    assert "borderw=10" in filter_string
    assert "bordercolor=black" in filter_string
    assert "shadowcolor=black@0.0" in filter_string
    assert "shadowx=0" in filter_string
    assert "shadowy=0" in filter_string


def test_longform_standard_existing_filter_string_uses_temporal_split() -> None:
    segment = SubtitleSegment(
        text="HELLO WORLD",
        start=0.0,
        end=1.0,
        highlight_words=[],
        style=SubtitleStyle(),
    )

    filter_string = SubtitleFFmpegBuilder.build_filter_string([segment])

    expected = (
        "drawtext=text='HELLO WORLD':fontcolor=white:fontsize=48:box=1:"
        "boxcolor=black@0.4:x=(w-text_w)/2:y=h-100:"
        "enable='between(t,0.000,0.500)'"
    )
    assert filter_string == expected


def test_highlighted_word_adds_second_green_drawtext_pass() -> None:
    filter_string = SubtitleFFmpegBuilder.build_filter(
        ["EPIC"],
        style="mobile_first",
        highlighted_words=["EPIC"],
    )

    assert filter_string.count("drawtext=") == 2
    assert "fontcolor=#00FF38" in filter_string


def test_empty_highlighted_words_adds_only_one_drawtext_pass() -> None:
    filter_string = SubtitleFFmpegBuilder.build_filter(
        ["EPIC"],
        style="mobile_first",
        highlighted_words=[],
    )

    assert filter_string.count("drawtext=") == 1


def test_multiple_highlighted_words_add_only_one_extra_drawtext_pass() -> None:
    filter_string = SubtitleFFmpegBuilder.build_filter(
        ["one", "two", "three"],
        style="mobile_first",
        highlighted_words=["one", "two", "three"],
    )

    assert filter_string.count("drawtext=") == 2


def test_six_words_wrap_after_third_word() -> None:
    filter_string = SubtitleFFmpegBuilder.build_filter(
        ["one", "two", "three", "four", "five", "six"],
        style="mobile_first",
    )

    assert "ONE TWO THREE\\nFOUR FIVE SIX" in filter_string


def test_three_words_do_not_wrap() -> None:
    filter_string = SubtitleFFmpegBuilder.build_filter(
        ["one", "two", "three"],
        style="mobile_first",
    )

    assert "\\n" not in filter_string


def test_comic_style_filter_contains_correct_params() -> None:
    filter_string = SubtitleFFmpegBuilder._build_mobile_first_filter(
        words=["Hallo", "Welt"],
        highlighted_words=["Hallo"],
    )

    assert "borderw=10" in filter_string
    assert "fontsize=86" in filter_string
    assert "HALLO WELT" in filter_string
    assert "Hallo Welt" not in filter_string


def test_highlighted_word_selector_includes_score_above_threshold() -> None:
    highlighted = SubtitleGenerator.highlighted_word_selector(
        ["EPIC"],
        {"EPIC": 0.8},
    )

    assert highlighted == ["EPIC"]


def test_highlighted_word_selector_excludes_score_at_or_below_threshold() -> None:
    highlighted = SubtitleGenerator.highlighted_word_selector(
        ["EPIC"],
        {"EPIC": 0.7},
    )

    assert highlighted == []


def test_highlighted_word_selector_empty_score_map_is_safe() -> None:
    highlighted = SubtitleGenerator.highlighted_word_selector(
        ["EPIC"],
        {},
    )

    assert highlighted == []


def test_shorts_render_driver_adds_captions_for_high_hook_score(tmp_path: Path) -> None:
    driver, helper = _driver()

    driver.render_short(
        clip=_clip(hook_score=0.8, llm_rationale=""),
        source_video_path=SOURCE_VIDEO_NAME,
        output_dir=str(tmp_path),
        job_id=JOB_ID,
        add_captions=True,
    )

    assert "drawtext" in _command_text(helper)


def test_shorts_render_driver_can_disable_captions(tmp_path: Path) -> None:
    driver, helper = _driver()

    driver.render_short(
        clip=_clip(hook_score=0.8, llm_rationale="Strong moment"),
        source_video_path=SOURCE_VIDEO_NAME,
        output_dir=str(tmp_path),
        job_id=JOB_ID,
        add_captions=False,
    )

    assert "drawtext" not in _command_text(helper)


def test_shorts_render_driver_uses_default_captions_without_transcript(tmp_path: Path) -> None:
    driver, helper = _driver()

    driver.render_short(
        clip=_clip(hook_score=0.3, llm_rationale=""),
        source_video_path=SOURCE_VIDEO_NAME,
        output_dir=str(tmp_path),
        job_id=JOB_ID,
        add_captions=True,
        transcript=None,
    )

    command_text = _command_text(helper)
    assert "drawtext" in command_text
    for default_word in ("STRONG", "HIGHLIGHT", "MOMENT"):
        assert default_word in command_text
