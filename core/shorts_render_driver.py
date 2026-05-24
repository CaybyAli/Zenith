from __future__ import annotations

import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core import ffmpeg_helper as default_ffmpeg_helper
from core.caption_ass_builder import (
    CaptionASSBuilder,
    CaptionGroup,
    DEFAULT_FONTS_DIR,
    escape_ffmpeg_filter_path,
)
from core.emoji_overlay_builder import (
    EmojiOverlayRenderer,
    EmojiOverlaySelector,
    emoji_overlay_enabled,
)
from core.audio_normalizer import (
    DEFAULT_LRA,
    DEFAULT_TARGET_I,
    DEFAULT_TARGET_TP,
    AudioNormalizer,
)
from core.ffmpeg_capability_resolver import resolve_ffmpeg_capabilities
from core.power_profile import PowerProfile
from core.subtitle_ffmpeg_builder import SubtitleFFmpegBuilder
from core.subtitle_generator import SubtitleGenerator, SubtitleSegment, SubtitleStyle
from core.shorts_transcript_caption_builder import build_caption_words_from_transcript
from models.shorts_clip import ShortsClip
from models.transcript_result import TranscriptResult, TranscriptWord

LOGGER = logging.getLogger(__name__)

SHORTS_OUTPUT_WIDTH = 1080
SHORTS_OUTPUT_HEIGHT = 1920
SHORTS_OUTPUT_FPS = 60
SHORTS_AUDIO_BITRATE = "320k"
SHORTS_MOVFLAGS = "+faststart"
SHORTS_OUTPUT_EXTENSION = ".mp4"
DEFAULT_SHORTS_CAPTION_WORDS = ("Strong", "highlight", "moment")
RAW_MIXED_AUDIO_FILENAME = "raw_mixed_audio.mp4"
CAPTION_RENDERER_ENV_VAR = "ZENITH_CAPTION_RENDERER"
CAPTION_RENDERER_LIBASS = "libass"
CAPTION_RENDERER_DRAWTEXT = "drawtext"
MAX_WORDS_PER_CAPTION_SEGMENT = 3
MAX_CHARS_PER_CAPTION_SEGMENT = 14

CPU_H264_ENCODER = "libx264"
NVENC_H264_ENCODER = "h264_nvenc"
AAC_AUDIO_ENCODER = "aac"
H264_PROBE_CODEC = "h264"
HEVC_PROBE_CODEC = "hevc"

POWER_PROFILE_CRF = {
    PowerProfile.ECO: 23,
    PowerProfile.BALANCED: 18,
    PowerProfile.PERFORMANCE: 15,
    PowerProfile.FULL_POWER: 15,
}


@dataclass(frozen=True)
class VideoCodecChoice:
    encoder: str
    uses_nvenc: bool
    probe_codec_names: tuple[str, ...]


class _DefaultFFmpegHelper:
    def get_ffmpeg_path(self) -> str:
        return default_ffmpeg_helper.get_ffmpeg_path()

    def build_ffmpeg_cmd(self, parts: list[str]) -> list[str]:
        return list(parts)

    def run_ffmpeg(self, cmd: list[str]) -> None:
        completed = subprocess.run(
            list(cmd),
            shell=False,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            stdout = (completed.stdout or "").strip()
            detail = stderr or stdout or f"ffmpeg_returncode_{completed.returncode}"
            raise RuntimeError(detail)


class _ResolverJob:
    job_id = "shorts_render_driver"
    ffmpeg_resolver_allow_tool_probe = True


class _DefaultCodecResolver:
    def resolve_video_codec(self, prefer_nvenc: bool) -> VideoCodecChoice:
        report = resolve_ffmpeg_capabilities(_ResolverJob())

        has_nvenc = bool(getattr(report, "has_nvenc", False))
        if prefer_nvenc and has_nvenc:
            return VideoCodecChoice(
                encoder=NVENC_H264_ENCODER,
                uses_nvenc=True,
                probe_codec_names=(H264_PROBE_CODEC,),
            )

        return VideoCodecChoice(
            encoder=CPU_H264_ENCODER,
            uses_nvenc=False,
            probe_codec_names=(H264_PROBE_CODEC,),
        )


def build_caption_segments(
    clip: ShortsClip,
    transcript: TranscriptResult | None,
) -> list[SubtitleSegment]:
    if transcript is None:
        return []

    clip_start = _safe_optional_float(getattr(clip, "source_start_time", None))
    clip_end = _safe_optional_float(getattr(clip, "source_end_time", None))
    if clip_start is None or clip_end is None:
        return []

    clip_words: list[Any] = []
    for word in _transcript_words(transcript):
        start = _word_seconds(word, ("start_seconds", "start", "start_time"))
        end = _word_seconds(word, ("end_seconds", "end", "end_time"))
        if start is None or end is None:
            continue
        if start >= clip_start and end <= clip_end:
            clip_words.append(word)

    has_word_times = (
        len(clip_words) > 0
        and hasattr(clip_words[0], "start_seconds")
        and getattr(clip_words[0], "start_seconds", None) is not None
    )
    if not has_word_times:
        return []

    relative_words: list[TranscriptWord] = []
    for word in clip_words:
        start = _word_seconds(word, ("start_seconds", "start", "start_time"))
        end = _word_seconds(word, ("end_seconds", "end", "end_time"))
        text = " ".join(str(getattr(word, "text", "") or "").split())
        if start is None or end is None or not text:
            continue

        relative_start = max(0.0, round(start - clip_start, 3))
        relative_end = max(0.0, round(end - clip_start, 3))
        if relative_end <= relative_start:
            continue

        relative_words.append(
            TranscriptWord(
                text=text,
                start_seconds=relative_start,
                end_seconds=relative_end,
                probability=getattr(word, "probability", None),
            )
        )

    return _group_words_into_segments(relative_words)


def _group_words_into_segments(
    relative_words: list[TranscriptWord],
) -> list[SubtitleSegment]:
    segments: list[SubtitleSegment] = []
    current_group: list[TranscriptWord] = []

    for word in relative_words:
        candidate_group = [*current_group, word]
        candidate_chars = len(" ".join(str(item.text or "") for item in candidate_group))

        if current_group and (
            _should_break_after_sentence_punctuation(current_group, word)
            or len(current_group) >= MAX_WORDS_PER_CAPTION_SEGMENT
            or candidate_chars > MAX_CHARS_PER_CAPTION_SEGMENT
        ):
            segments.append(_make_segment(current_group))
            current_group = []

        current_group.append(word)

    if current_group:
        segments.append(_make_segment(current_group))

    return segments


def _should_break_after_sentence_punctuation(
    current_group: list[TranscriptWord],
    next_word: TranscriptWord,
) -> bool:
    previous_text = str(current_group[-1].text or "").strip()
    next_text = str(next_word.text or "").strip()
    if not previous_text or not next_text:
        return False
    if previous_text[-1] not in ".!?":
        return False

    return not (
        previous_text[-1] == "?"
        and len(current_group) == 1
        and next_text.upper().rstrip(".!?") in {"JA", "NEIN", "YES", "NO"}
    )


def _make_segment(group: list[TranscriptWord]) -> SubtitleSegment:
    segment = SubtitleSegment(
        text=" ".join(word.text for word in group),
        start=group[0].start_seconds,
        end=group[-1].end_seconds,
        highlight_words=[],
        style=SubtitleStyle(),
    )
    segment.words = group
    return segment


def _caption_renderer() -> str:
    value = os.getenv(CAPTION_RENDERER_ENV_VAR, CAPTION_RENDERER_LIBASS)
    value = str(value or "").strip().casefold()
    if value in {CAPTION_RENDERER_LIBASS, CAPTION_RENDERER_DRAWTEXT}:
        return value
    return CAPTION_RENDERER_LIBASS


def _caption_groups_from_segments(
    segments: list[SubtitleSegment],
) -> list[CaptionGroup]:
    groups: list[CaptionGroup] = []
    for segment in segments:
        words = list(getattr(segment, "words", []) or [])
        if words:
            groups.append(CaptionGroup(words=words))
    return groups




def _caption_groups_for_clip(
    clip: ShortsClip,
    transcript: TranscriptResult,
) -> list[CaptionGroup]:
    clip_start = _safe_optional_float(getattr(clip, "source_start_time", None))
    clip_end = _safe_optional_float(getattr(clip, "source_end_time", None))
    if clip_start is None or clip_end is None:
        return []

    relative_words: list[TranscriptWord] = []

    for word in _transcript_words(transcript):
        start = _word_seconds(word, ("start_seconds", "start", "start_time"))
        end = _word_seconds(word, ("end_seconds", "end", "end_time"))
        text_value = getattr(word, "text", "")
        text = " ".join(str(text_value or "").split())

        if start is None or end is None or not text:
            continue

        if start < clip_start or end > clip_end:
            continue

        relative_start = max(0.0, round(start - clip_start, 3))
        relative_end = max(0.0, round(end - clip_start, 3))

        if relative_end <= relative_start:
            continue

        relative_words.append(
            TranscriptWord(
                text=text,
                start_seconds=relative_start,
                end_seconds=relative_end,
                probability=getattr(word, "probability", None),
            )
        )

    return [CaptionGroup(words=relative_words)] if relative_words else []


def _transcript_words(transcript: TranscriptResult) -> list[Any]:
    all_words = getattr(transcript, "all_words", None)
    if callable(all_words):
        try:
            return list(all_words() or [])
        except Exception:
            pass

    words: list[Any] = []
    for segment in getattr(transcript, "segments", []) or []:
        words.extend(list(getattr(segment, "words", []) or []))
    return words


def _word_seconds(word: Any, keys: tuple[str, ...]) -> float | None:
    for key in keys:
        value = getattr(word, key, None)
        seconds = _safe_optional_float(value)
        if seconds is not None:
            return seconds
    return None


def _safe_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _fallback_caption_words_from_transcript(
    transcript: TranscriptResult,
    clip_start_seconds: float,
    clip_end_seconds: float,
    max_words: int,
) -> tuple[list[str], dict[str, float]]:
    try:
        return build_caption_words_from_transcript(
            transcript=transcript,
            clip_start_seconds=clip_start_seconds,
            clip_end_seconds=clip_end_seconds,
            max_words=max_words,
        )
    except (AttributeError, TypeError, ValueError):
        pass

    words: list[str] = []
    hook_score_by_word: dict[str, float] = {}

    for segment in getattr(transcript, "segments", []) or []:
        if not _segment_overlaps_clip(segment, clip_start_seconds, clip_end_seconds):
            continue

        for raw_word in str(getattr(segment, "text", "") or "").split():
            clean = " ".join(raw_word.split())
            if not clean:
                continue

            words.append(clean)
            hook_score_by_word[clean.casefold()] = 0.5
            if len(words) >= max_words:
                return words, hook_score_by_word

    return words, hook_score_by_word


def _segment_overlaps_clip(
    segment: Any,
    clip_start_seconds: float,
    clip_end_seconds: float,
) -> bool:
    start = _word_seconds(segment, ("start_seconds", "start", "start_time"))
    end = _word_seconds(segment, ("end_seconds", "end", "end_time"))
    if start is None or end is None:
        return False

    return end > clip_start_seconds and start < clip_end_seconds


class ShortsRenderDriver:
    def __init__(
        self,
        ffmpeg_helper: Any | None = None,
        ffmpeg_capability_resolver: Any | None = None,
        audio_normalizer: AudioNormalizer | None = None,
        power_profile: str = PowerProfile.DEFAULT,
    ) -> None:
        self.ffmpeg_helper = ffmpeg_helper or _DefaultFFmpegHelper()
        self.ffmpeg_capability_resolver = (
            ffmpeg_capability_resolver or _DefaultCodecResolver()
        )
        self.audio_normalizer = audio_normalizer or AudioNormalizer(
            target_i=DEFAULT_TARGET_I,
            target_tp=DEFAULT_TARGET_TP,
        )
        self.power_profile = PowerProfile.normalize(power_profile)

    def render_short(
        self,
        clip: ShortsClip,
        source_video_path: str,
        output_dir: str,
        job_id: str,
        add_captions: bool = True,
        transcript: TranscriptResult | None = None,
    ) -> str:
        output_path = self._output_path(
            output_dir=output_dir,
            job_id=job_id,
            clip_index=int(getattr(clip, "clip_index", 0) or 0),
        )

        try:
            cmd = self.build_render_command(
                clip=clip,
                source_video_path=source_video_path,
                output_path=output_path,
                add_captions=add_captions,
                transcript=transcript,
            )
            self.ffmpeg_helper.run_ffmpeg(cmd)
            self._overlay_emojis_for_render(
                clip=clip,
                output_path=output_path,
                add_captions=add_captions,
                transcript=transcript,
            )
        except Exception as exc:
            clip.status = "failed"
            raise RuntimeError(
                f"Shorts render failed for job={job_id} clip_index={clip.clip_index}: {exc}"
            ) from exc

        clip.output_path = output_path
        clip.status = "rendered"
        return output_path

    def _overlay_emojis_for_render(
        self,
        clip: ShortsClip,
        output_path: str,
        add_captions: bool,
        transcript: TranscriptResult | None,
    ) -> None:
        if not add_captions:
            return

        if transcript is None:
            return

        if _caption_renderer() != CAPTION_RENDERER_LIBASS:
            return

        if not emoji_overlay_enabled():
            return

        caption_groups = _caption_groups_for_clip(clip=clip, transcript=transcript)
        if not caption_groups:
            return

        groups = CaptionASSBuilder().build_groups(caption_groups)
        if not groups:
            return

        duration = max(0.0, float(clip.source_end_time) - float(clip.source_start_time))
        emoji_events = EmojiOverlaySelector().select(
            groups=groups,
            duration_seconds=duration,
        )

        if not emoji_events:
            return

        output = Path(output_path)
        temp_output = output.with_name(output.stem + "_emoji_tmp" + output.suffix)
        event_log = output.with_suffix(".emoji_events.txt")

        event_log.write_text(
            "\n".join(
                f"{event.start_seconds:.2f}-{event.end_seconds:.2f} | {event.emoji} | {event.source_text}"
                for event in emoji_events
            ),
            encoding="utf-8",
        )

        EmojiOverlayRenderer(ffmpeg_path=self._ffmpeg_path()).overlay(
            input_video_path=output,
            output_video_path=temp_output,
            events=emoji_events,
        )

        os.replace(temp_output, output)


    def build_render_command(
        self,
        clip: ShortsClip,
        source_video_path: str,
        output_path: str,
        add_captions: bool = True,
        transcript: TranscriptResult | None = None,
    ) -> list[str]:
        reframe_plan = getattr(clip, "reframe_plan", None)
        if reframe_plan is None:
            raise ValueError("ShortsClip.reframe_plan is required before render")

        codec_choice = self._resolve_video_codec()
        caption_filter = self._caption_filter_for_render(
            clip=clip,
            output_path=output_path,
            add_captions=add_captions,
            transcript=transcript,
        )
        video_filter = self._video_filter(
            str(reframe_plan.ffmpeg_crop_filter or ""),
            caption_filter=caption_filter,
        )
        audio_filter = self._audio_filter()
        crf = self._crf_for_power_profile()
        audio_input_index = 0

        cmd: list[str] = [
            self._ffmpeg_path(),
            "-y",
            "-ss",
            self._format_seconds(clip.source_start_time),
            "-to",
            self._format_seconds(clip.source_end_time),
            "-i",
            str(source_video_path),
        ]

        raw_mixed_audio_path = Path(source_video_path).parent / RAW_MIXED_AUDIO_FILENAME
        if raw_mixed_audio_path.exists():
            audio_input_index = 1
            cmd.extend(
                [
                    "-ss",
                    self._format_seconds(clip.source_start_time),
                    "-to",
                    self._format_seconds(clip.source_end_time),
                    "-i",
                    str(raw_mixed_audio_path),
                ]
            )
        else:
            LOGGER.warning(
                "raw_mixed_audio.mp4 not found, falling back to raw.mp4 audio"
            )

        if self._is_complex_filter(video_filter):
            cmd.extend(
                [
                    "-filter_complex",
                    video_filter,
                    "-map",
                    "[out]",
                    "-map",
                    f"{audio_input_index}:a?",
                ]
            )
        else:
            cmd.extend(["-vf", video_filter])
            if audio_input_index == 1:
                cmd.extend(["-map", "0:v", "-map", "1:a"])

        cmd.extend(
            [
                "-r",
                str(SHORTS_OUTPUT_FPS),
                "-c:v",
                codec_choice.encoder,
            ]
        )

        if codec_choice.uses_nvenc:
            cmd.extend(["-cq", str(crf)])
        else:
            cmd.extend(["-crf", str(crf), "-preset", "fast"])

        cmd.extend(
            [
                "-pix_fmt",
                "yuv420p",
                "-af",
                audio_filter,
                "-c:a",
                AAC_AUDIO_ENCODER,
                "-b:a",
                SHORTS_AUDIO_BITRATE,
                "-movflags",
                SHORTS_MOVFLAGS,
                str(output_path),
            ]
        )

        builder = getattr(self.ffmpeg_helper, "build_ffmpeg_cmd", None)
        if callable(builder):
            return builder(cmd)

        return cmd

    def _output_path(self, output_dir: str, job_id: str, clip_index: int) -> str:
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        return str(out_dir / f"{job_id}_short_{clip_index}{SHORTS_OUTPUT_EXTENSION}")

    def _ffmpeg_path(self) -> str:
        getter = getattr(self.ffmpeg_helper, "get_ffmpeg_path", None)
        if callable(getter):
            return str(getter())
        return default_ffmpeg_helper.get_ffmpeg_path()

    def _resolve_video_codec(self) -> VideoCodecChoice:
        prefer_nvenc = self.power_profile in {
            PowerProfile.PERFORMANCE,
            PowerProfile.FULL_POWER,
        }

        resolver = self.ffmpeg_capability_resolver
        method = getattr(resolver, "resolve_video_codec", None)
        if callable(method):
            choice = method(prefer_nvenc=prefer_nvenc)
            if isinstance(choice, VideoCodecChoice):
                return choice
            if isinstance(choice, str):
                return VideoCodecChoice(
                    encoder=choice,
                    uses_nvenc="nvenc" in choice.lower(),
                    probe_codec_names=(H264_PROBE_CODEC,),
                )

        if callable(resolver):
            report = resolver(_ResolverJob())
            if prefer_nvenc and bool(getattr(report, "has_nvenc", False)):
                return VideoCodecChoice(
                    encoder=NVENC_H264_ENCODER,
                    uses_nvenc=True,
                    probe_codec_names=(H264_PROBE_CODEC,),
                )

        return VideoCodecChoice(
            encoder=CPU_H264_ENCODER,
            uses_nvenc=False,
            probe_codec_names=(H264_PROBE_CODEC,),
        )

    def _crf_for_power_profile(self) -> int:
        return POWER_PROFILE_CRF.get(self.power_profile, POWER_PROFILE_CRF[PowerProfile.BALANCED])

    def _audio_filter(self) -> str:
        target_i = float(getattr(self.audio_normalizer, "target_i", DEFAULT_TARGET_I))
        target_tp = float(getattr(self.audio_normalizer, "target_tp", DEFAULT_TARGET_TP))
        return f"loudnorm=I={target_i}:TP={target_tp}:LRA={DEFAULT_LRA}"

    def _video_filter(self, reframe_filter: str, caption_filter: str = "") -> str:
        clean_filter = str(reframe_filter or "").strip()
        if not clean_filter:
            raise ValueError("Shorts reframe ffmpeg_crop_filter must not be empty")

        if self._is_complex_filter(clean_filter):
            normalized = clean_filter.replace(
                "[0:v]crop=",
                "[0:v]scale=1920:1920:force_original_aspect_ratio=increase,crop=",
            )
            if "[out]" not in normalized:
                normalized = normalized.replace(
                    "vstack",
                    f"vstack,scale={SHORTS_OUTPUT_WIDTH}:{SHORTS_OUTPUT_HEIGHT}[out]",
                )
            return self._append_caption_to_complex_filter(normalized, caption_filter)

        simple_filter = clean_filter
        if "crop=1080:1920" in simple_filter and "scale=1920:1920" not in simple_filter:
            simple_filter = (
                "scale=1920:1920:force_original_aspect_ratio=increase,"
                f"{simple_filter}"
            )

        output_exact = "crop=1080:1920" in simple_filter or "s=1080x1920" in simple_filter
        if not output_exact and "scale=1080:1920" not in simple_filter:
            simple_filter = f"{simple_filter},scale={SHORTS_OUTPUT_WIDTH}:{SHORTS_OUTPUT_HEIGHT}"

        return self._append_caption_to_simple_filter(simple_filter, caption_filter)

    def _caption_filter_for_render(
        self,
        clip: ShortsClip,
        output_path: str,
        add_captions: bool = True,
        transcript: TranscriptResult | None = None,
    ) -> str:
        if not add_captions:
            return ""

        if _caption_renderer() == CAPTION_RENDERER_LIBASS and transcript is not None:
            caption_groups = _caption_groups_for_clip(clip=clip, transcript=transcript)
            if caption_groups:
                ass_path = Path(output_path).with_suffix(".ass")
                CaptionASSBuilder().generate_ass_file(
                    caption_groups=caption_groups,
                    output_path=str(ass_path),
                )
                return self._ass_caption_filter(ass_path)

            LOGGER.warning(
                "No word-level timestamps available for libass, falling back to drawtext captions"
            )

        return self._caption_filter(
            clip=clip,
            add_captions=add_captions,
            transcript=transcript,
        )

    def _ass_caption_filter(self, ass_path: Path) -> str:
        escaped_ass_path = escape_ffmpeg_filter_path(ass_path)
        escaped_fonts_dir = escape_ffmpeg_filter_path(DEFAULT_FONTS_DIR)
        return f"subtitles={escaped_ass_path}:fontsdir={escaped_fonts_dir}"

    def _caption_filter(
        self,
        clip: ShortsClip,
        add_captions: bool = True,
        transcript: TranscriptResult | None = None,
    ) -> str:
        if not add_captions:
            return ""

        try:
            hook_score = float(getattr(clip, "hook_score", 0.0) or 0.0)
        except Exception:
            hook_score = 0.0

        if transcript is not None:
            segments = build_caption_segments(clip=clip, transcript=transcript)
            if segments:
                return SubtitleFFmpegBuilder.build_filter_string(segments)

            LOGGER.warning(
                "No word-level timestamps available, falling back to segment-level captions"
            )

        words: list[str] = []
        hook_score_by_word: dict[str, float] = {}

        if transcript is not None:
            words, hook_score_by_word = _fallback_caption_words_from_transcript(
                transcript=transcript,
                clip_start_seconds=float(clip.source_start_time),
                clip_end_seconds=float(clip.source_end_time),
                max_words=MAX_WORDS_PER_CAPTION_SEGMENT,
            )

        if not words:
            words = list(DEFAULT_SHORTS_CAPTION_WORDS)
            hook_score_by_word = {}

        hook_scores: dict[str, float] = {}
        for word in words:
            score = hook_score_by_word.get(word.casefold(), hook_score)
            hook_scores[word] = score
            hook_scores[word.casefold()] = score

        highlighted_words = SubtitleGenerator.highlighted_word_selector(words, hook_scores)[:1]

        return SubtitleFFmpegBuilder.build_filter(
            words=words,
            style="mobile_first",
            highlighted_words=highlighted_words,
        )

    def _append_caption_to_simple_filter(self, video_filter: str, caption_filter: str) -> str:
        if not caption_filter:
            return video_filter
        return f"{video_filter},{caption_filter}"

    def _append_caption_to_complex_filter(self, video_filter: str, caption_filter: str) -> str:
        if not caption_filter:
            return video_filter
        if "[out]" not in video_filter:
            return f"{video_filter},{caption_filter}"
        return video_filter.replace("[out]", "[caption_in]", 1) + f";[caption_in]{caption_filter}[out]"

    def _is_complex_filter(self, filter_string: str) -> bool:
        return "[" in filter_string and "]" in filter_string

    def expected_probe_codec_names(self) -> tuple[str, ...]:
        return self._resolve_video_codec().probe_codec_names

    @staticmethod
    def _format_seconds(value: float) -> str:
        return f"{float(value):.3f}"
