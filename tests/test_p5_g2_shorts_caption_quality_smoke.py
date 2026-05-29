from __future__ import annotations

import json
from pathlib import Path

from core.audio_normalizer import AudioNormalizer
from core.caption_ass_builder import CaptionASSBuilder, CaptionGroup
from core.power_profile import PowerProfile
from core.shorts_render_driver import ShortsRenderDriver, VideoCodecChoice
from core.shorts_transcript_caption_builder import build_sane_caption_words_from_transcript
from models.shorts_clip import ShortsClip
from models.shorts_reframe_plan import ShortsReframePlan
from models.transcript_result import TranscriptResult, TranscriptSegment, TranscriptWord


class FakeFFmpegHelper:
    def __init__(self) -> None:
        self.commands: list[list[str]] = []

    def get_ffmpeg_path(self) -> str:
        return "fake_ffmpeg"

    def build_ffmpeg_cmd(self, parts: list[str]) -> list[str]:
        return list(parts)

    def run_ffmpeg(self, cmd: list[str]) -> None:
        self.commands.append(list(cmd))


class FakeCodecResolver:
    def resolve_video_codec(self, prefer_nvenc: bool) -> VideoCodecChoice:
        return VideoCodecChoice(
            encoder="libx264",
            uses_nvenc=False,
            probe_codec_names=("h264",),
        )


def _word(text: str, start: float, end: float) -> TranscriptWord:
    return TranscriptWord(
        text=text,
        start_seconds=start,
        end_seconds=end,
        probability=0.95,
    )


def _transcript_with_injected_outlier() -> TranscriptResult:
    return TranscriptResult(
        source_path="synthetic_whisperx.json",
        language="de",
        engine="whisperx",
        full_text="ein zwei drei vier funf sechs sieb acht",
        segments=[
            TranscriptSegment(
                start_seconds=0.0,
                end_seconds=3.0,
                text="ein zwei drei vier funf sechs sieb acht",
                words=[
                    _word("ein", 0.00, 0.28),
                    _word("zwei", 0.35, 0.62),
                    _word("drei", 0.70, 0.95),
                    _word("vier", 1.02, 1.28),
                    _word("funf", 1.37, 1.65),
                    _word("sechs", 1.74, 2.05),
                    _word("sieb", 2.14, 2.45),
                    _word("acht", 2.54, 7.70),
                ],
            )
        ],
    )


def _clip() -> ShortsClip:
    return ShortsClip(
        source_job_id="job_p5_g2_caption_test",
        source_start_time=0.0,
        source_end_time=3.0,
        planned_duration=3.0,
        hook_score=0.91,
        clip_index=0,
        reframe_plan=ShortsReframePlan(
            layout_type="gameplay_centered",
            ffmpeg_crop_filter="crop=1080:1920:420:0",
        ),
    )


def test_injected_outlier_word_timestamp_is_clamped_to_segment_boundary() -> None:
    transcript = _transcript_with_injected_outlier()

    result = build_sane_caption_words_from_transcript(
        transcript=transcript,
        clip_start_seconds=0.0,
        clip_end_seconds=3.0,
    )

    assert len(result.clamp_events) == 1
    event = result.clamp_events[0]

    assert event.word == "acht"
    assert event.raw_end_seconds == 7.7
    assert event.segment_end_seconds == 3.0
    assert event.clamped_end_seconds == 3.0
    assert event.reason == "end_after_segment"

    assert all(0.0 <= word.start_seconds < word.end_seconds <= 3.0 for word in result.words)

    print(
        "P5_G2_SANITY_AUDIT "
        f"word={event.word} "
        f"raw_end={event.raw_end_seconds} "
        f"segment_end={event.segment_end_seconds} "
        f"clamped_end={event.clamped_end_seconds} "
        f"reason={event.reason}"
    )


def test_caption_grouping_uses_two_to_four_word_bursts() -> None:
    transcript = _transcript_with_injected_outlier()
    result = build_sane_caption_words_from_transcript(transcript, 0.0, 3.0)

    groups = CaptionASSBuilder().build_groups([CaptionGroup(words=result.words)])
    group_texts = [[word.text for word in group] for group in groups]

    assert group_texts
    assert all(2 <= len(group) <= 4 for group in group_texts)
    assert max(len(" ".join(group)) for group in group_texts) <= 22

    print(f"P5_G2_GROUPING_AUDIT groups={group_texts}")


def test_libass_caption_audit_is_written_with_word_timestamp_source(tmp_path: Path) -> None:
    transcript = _transcript_with_injected_outlier()
    output_path = tmp_path / "short.mp4"

    driver = ShortsRenderDriver(
        ffmpeg_helper=FakeFFmpegHelper(),
        ffmpeg_capability_resolver=FakeCodecResolver(),
        audio_normalizer=AudioNormalizer(),
        power_profile=PowerProfile.BALANCED,
    )

    caption_filter = driver._caption_filter_for_render(
        clip=_clip(),
        output_path=str(output_path),
        add_captions=True,
        transcript=transcript,
    )

    audit_path = output_path.with_suffix(".caption_audit.json")
    audit = json.loads(audit_path.read_text(encoding="utf-8"))

    assert "subtitles=" in caption_filter
    assert audit["source"] == "whisperx_word_timestamps"
    assert audit["renderer"] == "libass"
    assert audit["active_word_highlighting"] is True
    assert audit["clamped_word_timestamp_count"] == 1
    assert audit["max_group_words"] <= 4
    assert audit["max_group_chars"] <= 22

    print(
        "P5_G2_LIBASS_AUDIT "
        f"source={audit['source']} "
        f"renderer={audit['renderer']} "
        f"clamps={audit['clamped_word_timestamp_count']} "
        f"groups={audit['groups']}"
    )
