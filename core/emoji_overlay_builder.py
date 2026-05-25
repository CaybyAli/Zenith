from __future__ import annotations

import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.caption_ass_builder import ASS_TEXT_DELAY_SECONDS
from core.ffmpeg_capability_resolver import resolve_ffmpeg_capabilities


LOGGER = logging.getLogger(__name__)

SHORTS_EMOJI_OVERLAY_ENV_VAR = "ZENITH_SHORTS_EMOJI_OVERLAY"

DEFAULT_EMOJI_ASSET_DIR = Path(__file__).resolve().parents[1] / "assets" / "emoji" / "noto_512"
EMOJI_SIZE = 700
EMOJI_X = 190
EMOJI_Y = 1220
EMOJI_OUTLINE_BLUR = 3
EMOJI_OUTLINE_ALPHA = 0.78
MAX_EMOJIS_PER_SHORT = 3
MIN_SECONDS_BETWEEN_EMOJIS = 9.0
DEFAULT_EMOJI_DURATION_SECONDS = 1.70

EMOJI_ASSET_FILENAMES = {
    "heart": "heart_512.png",
    "laugh": "laugh_512.png",
    "fire": "fire_512.png",
    "eyes": "eyes_512.png",
    "shock": "shock_512.png",
    "skull": "skull_512.png",
    "trophy": "trophy_512.png",
}

_ENCODER_CACHE: dict[tuple[str, str], str] = {}


def _resolve_encoder(ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe") -> str:
    cache_key = (str(ffmpeg_path), str(ffprobe_path))
    if cache_key in _ENCODER_CACHE:
        return _ENCODER_CACHE[cache_key]

    try:
        report = resolve_ffmpeg_capabilities(
            {
                "job_id": "emoji_overlay_builder",
                "ffmpeg_path_hint": str(ffmpeg_path),
                "ffprobe_path_hint": str(ffprobe_path),
                "ffmpeg_resolver_allow_tool_probe": True,
            }
        )
        encoder = "h264_nvenc" if bool(getattr(report, "has_nvenc", False)) else "libx264"
    except Exception:
        encoder = "libx264"

    _ENCODER_CACHE[cache_key] = encoder
    return encoder


@dataclass(frozen=True)
class EmojiOverlayEvent:
    emoji: str
    start_seconds: float
    end_seconds: float
    source_text: str = ""


def emoji_overlay_enabled() -> bool:
    value = os.getenv(SHORTS_EMOJI_OVERLAY_ENV_VAR, "1")
    return str(value or "").strip().casefold() not in {"0", "false", "no", "off"}


class EmojiOverlaySelector:
    def select(
        self,
        groups: list[list[Any]],
        duration_seconds: float | None = None,
    ) -> list[EmojiOverlayEvent]:
        selected: list[EmojiOverlayEvent] = []
        last_time = -999.0
        limit = float(duration_seconds) if duration_seconds is not None else None

        for group in groups:
            if not group:
                continue

            group_text = " ".join(_word_text(word) for word in group)
            emoji = self.choose_emoji(group_text)

            if not emoji:
                continue

            start = max(0.20, _word_start(group[0]) + ASS_TEXT_DELAY_SECONDS)
            end = start + DEFAULT_EMOJI_DURATION_SECONDS

            if limit is not None:
                end = min(limit, end)

            if start - last_time < MIN_SECONDS_BETWEEN_EMOJIS:
                continue

            selected.append(
                EmojiOverlayEvent(
                    emoji=emoji,
                    start_seconds=start,
                    end_seconds=end,
                    source_text=group_text,
                )
            )
            last_time = start

            if len(selected) >= MAX_EMOJIS_PER_SHORT:
                break

        return selected

    @staticmethod
    def choose_emoji(group_text: str) -> str | None:
        text = " " + str(group_text or "").upper() + " "

        if any(keyword in text for keyword in [" LIEBE ", " LIEB ", " HERZ ", " KUSS ", " HAB DICH "]):
            return "heart"

        if any(keyword in text for keyword in [" HAHA ", " HAH ", " LACHE ", " LACHEN ", " LUSTIG ", " WITZIG "]):
            return "laugh"

        if any(keyword in text for keyword in [" TOT ", " STERBE ", " GESTORBEN ", " DEAD ", " KILL ", " GEKILLT ", " FAIL "]):
            return "skull"

        if any(keyword in text for keyword in [" SIEG ", " GEWONNEN ", " GESCHAFFT ", " WIN ", " GEWINNEN "]):
            return "trophy"

        if any(keyword in text for keyword in [" OHA ", " WAS ", " NEIN ", " OMG ", " SCHOCK ", " ALTER "]):
            return "shock"

        if any(keyword in text for keyword in [" KRASS ", " HEFTIG ", " INSANE ", " WILD ", " STARK ", " GEIL ", " EZ "]):
            return "fire"

        if any(keyword in text for keyword in [" WARTE ", " GUCK ", " SCHAU ", " SIEH ", " H? ", " HMM "]):
            return "eyes"

        return None


class EmojiOverlayRenderer:
    def __init__(
        self,
        ffmpeg_path: str = "ffmpeg",
        asset_dir: str | Path = DEFAULT_EMOJI_ASSET_DIR,
    ) -> None:
        self.ffmpeg_path = str(ffmpeg_path)
        self.asset_dir = Path(asset_dir)

    def overlay(
        self,
        input_video_path: str | Path,
        output_video_path: str | Path,
        events: list[EmojiOverlayEvent],
    ) -> bool:
        input_path = Path(input_video_path)
        output_path = Path(output_video_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        available_events = [
            event for event in events if self._asset_path(event.emoji).exists()
        ]

        missing_events = [
            event for event in events if not self._asset_path(event.emoji).exists()
        ]
        for event in missing_events:
            LOGGER.warning(
                "Emoji asset missing for %s at %s",
                event.emoji,
                self._asset_path(event.emoji),
            )

        if not available_events:
            shutil.copy2(input_path, output_path)
            return False

        cmd = [
            self.ffmpeg_path,
            "-y",
            "-hwaccel",
            "cuda",
            "-hwaccel_output_format",
            "cuda",
            "-i",
            str(input_path),
        ]

        for event in available_events:
            cmd.extend(["-loop", "1", "-i", str(self._asset_path(event.emoji))])

        filter_complex = self._filter_complex(available_events)
        video_encoder = _resolve_encoder(self.ffmpeg_path)
        if video_encoder == "h264_nvenc":
            video_encoder_args = ["-c:v", video_encoder, "-pix_fmt", "yuv420p", "-cq", "23", "-preset", "fast"]
        else:
            video_encoder_args = ["-c:v", video_encoder, "-crf", "23", "-preset", "fast"]

        cmd.extend(
            [
                "-filter_complex",
                filter_complex,
                "-map",
                f"[v{len(available_events)}]",
                "-map",
                "0:a?",
                *video_encoder_args,
                "-c:a",
                "copy",
                "-shortest",
                str(output_path),
            ]
        )

        completed = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
        )

        if completed.returncode != 0:
            stderr = (completed.stderr or "").strip()
            stdout = (completed.stdout or "").strip()
            raise RuntimeError(stderr or stdout or "emoji_overlay_ffmpeg_failed")

        return True

    def _filter_complex(self, events: list[EmojiOverlayEvent]) -> str:
        parts: list[str] = ["[0:v]hwdownload,format=yuv420p[base0]"]
        last_video = "base0"

        for index, event in enumerate(events, start=1):
            tag = f"e{index}"
            out = f"v{index}"

            parts.extend(
                [
                    f"[{index}:v]scale={EMOJI_SIZE}:{EMOJI_SIZE}:flags=lanczos,format=rgba[{tag}]",
                    f"[{tag}]split=2[{tag}_real][{tag}_mask]",
                    f"[{tag}_mask]alphaextract,boxblur={EMOJI_OUTLINE_BLUR}:1[{tag}_alpha]",
                    f"color=white@{EMOJI_OUTLINE_ALPHA}:s={EMOJI_SIZE}x{EMOJI_SIZE},format=rgba[{tag}_white]",
                    f"[{tag}_white][{tag}_alpha]alphamerge[{tag}_outline]",
                    f"[{tag}_outline][{tag}_real]overlay=0:0[{tag}_final]",
                    (
                        f"[{last_video}][{tag}_final]"
                        f"overlay=x={EMOJI_X}:y={EMOJI_Y}:"
                        f"enable='between(t,{event.start_seconds:.2f},{event.end_seconds:.2f})'"
                        f"[{out}]"
                    ),
                ]
            )
            last_video = out

        return ";".join(parts)

    def _asset_path(self, emoji: str) -> Path:
        filename = EMOJI_ASSET_FILENAMES.get(emoji, f"{emoji}_512.png")
        return self.asset_dir / filename


def _word_text(word: Any) -> str:
    if isinstance(word, dict):
        value = word.get("text", word.get("word", ""))
    else:
        value = getattr(word, "text", None)
        if value is None:
            value = getattr(word, "word", "")
    return " ".join(str(value or "").split())


def _word_start(word: Any) -> float:
    if isinstance(word, dict):
        value = word.get("start_seconds", word.get("start", 0.0))
    else:
        value = getattr(word, "start_seconds", getattr(word, "start", 0.0))

    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0
