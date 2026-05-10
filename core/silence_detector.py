from __future__ import annotations

import re
import subprocess
from typing import Any

from models.silence_detection import SilenceDetectionResult, SilenceSegment

DEFAULT_SILENCE_THRESHOLD_DB: float = -40.0
DEFAULT_MIN_SILENCE_DURATION_SECONDS: float = 0.4
TAIL_LIMIT: int = 4000


def build_silencedetect_command(
    source_path: str,
    threshold_db: float = DEFAULT_SILENCE_THRESHOLD_DB,
    min_duration_seconds: float = DEFAULT_MIN_SILENCE_DURATION_SECONDS,
    ffmpeg_path: str | None = None,
) -> list[str]:
    if ffmpeg_path is None:
        try:
            from core.ffmpeg_helper import get_ffmpeg_path
            ffmpeg_path = get_ffmpeg_path()
        except Exception:
            ffmpeg_path = "ffmpeg"

    af_filter = f"silencedetect=noise={threshold_db}dB:d={min_duration_seconds}"
    return [
        ffmpeg_path,
        "-hide_banner",
        "-i", source_path,
        "-af", af_filter,
        "-f", "null",
        "-",
    ]


def parse_silencedetect_output(
    source_path: str,
    output: str,
    threshold_db: float,
    min_duration_seconds: float,
    command_preview: list[str],
) -> SilenceDetectionResult:
    warnings: list[str] = []
    errors: list[str] = []
    segments: list[SilenceSegment] = []

    raw_tail = output[-TAIL_LIMIT:] if len(output) > TAIL_LIMIT else output

    start_re = re.compile(r"\[silencedetect[^\]]*\]\s+silence_start:\s*([\d.,]+)")
    end_re = re.compile(
        r"\[silencedetect[^\]]*\]\s+silence_end:\s*([\d.,]+)"
        r"\s*\|\s*silence_duration:\s*([\d.,]+)"
    )

    pending_start: float | None = None

    for line in output.splitlines():
        start_match = start_re.search(line)
        end_match = end_re.search(line)

        if start_match:
            pending_start = float(start_match.group(1).replace(",", "."))
        elif end_match:
            end_seconds = float(end_match.group(1).replace(",", "."))
            duration_seconds = float(end_match.group(2).replace(",", "."))

            if pending_start is None:
                warnings.append("orphan_silence_end: end without preceding start")
                pending_start = max(0.0, end_seconds - duration_seconds)

            segments.append(
                SilenceSegment(
                    start_seconds=pending_start,
                    end_seconds=end_seconds,
                    duration_seconds=duration_seconds,
                    threshold_db=threshold_db,
                )
            )
            pending_start = None

    if pending_start is not None:
        warnings.append("orphan_silence_start: start without matching end")

    total_silence = sum(s.duration_seconds for s in segments)

    return SilenceDetectionResult(
        source_path=source_path,
        status="ok",
        threshold_db=threshold_db,
        min_duration_seconds=min_duration_seconds,
        segments=segments,
        segment_count=len(segments),
        total_silence_seconds=round(total_silence, 6),
        warnings=warnings,
        errors=errors,
        raw_output_tail=raw_tail if raw_tail else None,
        command_preview=command_preview,
    )


def detect_silence(
    source_path: str,
    threshold_db: float = DEFAULT_SILENCE_THRESHOLD_DB,
    min_duration_seconds: float = DEFAULT_MIN_SILENCE_DURATION_SECONDS,
    ffmpeg_path: str | None = None,
) -> SilenceDetectionResult:
    command: list[str] = []
    try:
        command = build_silencedetect_command(
            source_path=source_path,
            threshold_db=threshold_db,
            min_duration_seconds=min_duration_seconds,
            ffmpeg_path=ffmpeg_path,
        )

        proc = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        combined_output = proc.stdout or ""
        raw_tail = combined_output[-TAIL_LIMIT:] if len(combined_output) > TAIL_LIMIT else combined_output

        if proc.returncode != 0:
            return SilenceDetectionResult(
                source_path=source_path,
                status="failed",
                threshold_db=threshold_db,
                min_duration_seconds=min_duration_seconds,
                errors=["ffmpeg_silencedetect_failed"],
                raw_output_tail=raw_tail if raw_tail else None,
                command_preview=command,
            )

        return parse_silencedetect_output(
            source_path=source_path,
            output=combined_output,
            threshold_db=threshold_db,
            min_duration_seconds=min_duration_seconds,
            command_preview=command,
        )

    except Exception:
        return SilenceDetectionResult(
            source_path=source_path,
            status="failed",
            threshold_db=threshold_db,
            min_duration_seconds=min_duration_seconds,
            errors=["silence_detection_failed"],
            command_preview=command,
        )
