from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core import ffmpeg_helper as default_ffmpeg_helper
from core.audio_normalizer import (
    DEFAULT_LRA,
    DEFAULT_TARGET_I,
    DEFAULT_TARGET_TP,
    AudioNormalizer,
)
from core.ffmpeg_capability_resolver import resolve_ffmpeg_capabilities
from core.power_profile import PowerProfile
from core.subtitle_ffmpeg_builder import SubtitleFFmpegBuilder
from core.subtitle_generator import SubtitleGenerator
from core.shorts_transcript_caption_builder import build_caption_words_from_transcript
from models.shorts_clip import ShortsClip
from models.transcript_result import TranscriptResult

LOGGER = logging.getLogger(__name__)

SHORTS_OUTPUT_WIDTH = 1080
SHORTS_OUTPUT_HEIGHT = 1920
SHORTS_OUTPUT_FPS = 60
SHORTS_AUDIO_BITRATE = "320k"
SHORTS_MOVFLAGS = "+faststart"
SHORTS_OUTPUT_EXTENSION = ".mp4"
DEFAULT_SHORTS_CAPTION_WORDS = ("Strong", "highlight", "moment")
RAW_MIXED_AUDIO_FILENAME = "raw_mixed_audio.mp4"

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
        except Exception as exc:
            clip.status = "failed"
            raise RuntimeError(
                f"Shorts render failed for job={job_id} clip_index={clip.clip_index}: {exc}"
            ) from exc

        clip.output_path = output_path
        clip.status = "rendered"
        return output_path

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
        caption_filter = self._caption_filter(
            clip=clip,
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

        words: list[str] = []
        hook_score_by_word: dict[str, float] = {}

        if transcript is not None:
            words, hook_score_by_word = build_caption_words_from_transcript(
                transcript=transcript,
                clip_start_seconds=float(clip.source_start_time),
                clip_end_seconds=float(clip.source_end_time),
                max_words=4,
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
