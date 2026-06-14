from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from core.ffmpeg_helper import apply_ffmpeg_thread_cap, get_ffmpeg_path
from models.music_apply_timeline import MusicApplyTimeline
from models.music_apply_segment import MusicApplySegment


DYNAUDNORM_FILTER = "dynaudnorm=f=250:g=31:m=8:p=0.9"
MUSIC_CONST_COMPRESSOR_FILTER = "acompressor=threshold=0.05:ratio=6:attack=20:release=250:makeup=8"
MUSIC_BED_GAIN_DB = -34.0
SIDECHAIN_FILTER = "sidechaincompress=threshold=0.03:ratio=3:attack=150:release=700"
MUSIC_PEAK_LIMITER_FILTER = "volume=13.0dB,alimiter=limit=0.06309573:attack=5:release=80:level=0,volume=-13.0dB"


class MusicApplyProcessorError(RuntimeError):
    pass


def _format_seconds(value: float) -> str:
    return f"{float(value):.3f}".rstrip("0").rstrip(".") or "0"


def _format_db(value: float) -> str:
    return f"{float(value):.3f}".rstrip("0").rstrip(".") or "0"


def _segment_duration(segment: MusicApplySegment) -> float:
    return float(segment.music_offset_end) - float(segment.music_offset_start)


def _output_video_path(rendered_video_path: Path) -> Path:
    return rendered_video_path.with_name(
        f"{rendered_video_path.stem}_music_applied{rendered_video_path.suffix}"
    )


def _music_ducked_stem_path(rendered_video_path: Path) -> Path:
    return rendered_video_path.with_name(
        f"{rendered_video_path.stem}_music_ducked_stem.flac"
    )


def _context_path(rendered_video_path: Path) -> Path:
    return rendered_video_path.with_name(
        f"{rendered_video_path.stem}_music_apply_context.json"
    )


def _validate_apply_inputs(
    rendered_video_path: Path,
    segments: list[MusicApplySegment],
) -> None:
    if not rendered_video_path.exists():
        raise FileNotFoundError(f"rendered video does not exist: {rendered_video_path}")

    for segment in segments:
        source_path = Path(segment.source_file_path)
        if not source_path.exists():
            raise FileNotFoundError(
                f"music source does not exist for segment {segment.segment_id}: {source_path}"
            )
        if float(segment.video_start_time) < 0.0:
            raise ValueError(f"segment {segment.segment_id} has negative video_start_time")
        if float(segment.music_offset_start) < 0.0:
            raise ValueError(f"segment {segment.segment_id} has negative music_offset_start")
        if _segment_duration(segment) <= 0.0:
            raise ValueError(f"segment {segment.segment_id} has non-positive music trim duration")


def build_music_apply_filter_complex(segments: list[MusicApplySegment]) -> str:
    if not segments:
        raise ValueError("music apply filter requires at least one segment")

    filter_parts: list[str] = []
    segment_labels: list[str] = []

    for index, segment in enumerate(segments, start=1):
        duration = _segment_duration(segment)
        fade_in = max(0.0, min(float(segment.fade_in_seconds), duration))
        fade_out = max(0.0, min(float(segment.fade_out_seconds), duration))
        fade_out_start = max(0.0, duration - fade_out)
        delay_ms = max(0, int(round(float(segment.video_start_time) * 1000.0)))
        label = f"musicSegment{index}"
        segment_labels.append(f"[{label}]")

        filter_parts.append(
            f"[{index}:a]"
            f"atrim=start={_format_seconds(segment.music_offset_start)}:"
            f"end={_format_seconds(segment.music_offset_end)},"
            "asetpts=PTS-STARTPTS,"
            f"volume={_format_db(segment.music_level)}dB,"
            f"afade=t=in:st=0:d={_format_seconds(fade_in)},"
            f"afade=t=out:st={_format_seconds(fade_out_start)}:"
            f"d={_format_seconds(fade_out)},"
            f"adelay={delay_ms}:all=1"
            f"[{label}]"
        )

    filter_parts.append(
        "".join(segment_labels)
        + f"amix=inputs={len(segment_labels)}:duration=longest:"
        "dropout_transition=0:normalize=0[musicbed]"
    )
    filter_parts.append(
        f"[musicbed]{DYNAUDNORM_FILTER},{MUSIC_CONST_COMPRESSOR_FILTER}[music_const]"
    )
    filter_parts.append(f"[music_const]volume={MUSIC_BED_GAIN_DB:.1f}dB[music_bed]")
    filter_parts.append(f"[music_bed][0:a]{SIDECHAIN_FILTER}[music_ducked_prelimit]")
    filter_parts.append(
        f"[music_ducked_prelimit]{MUSIC_PEAK_LIMITER_FILTER}[music_ducked]"
    )
    filter_parts.append("[music_ducked]asplit=2[music_ducked_stem][music_ducked_mix]")
    filter_parts.append(
        "[0:a][music_ducked_mix]amix=inputs=2:duration=first:"
        "dropout_transition=0,volume=1.0[aout]"
    )

    return ";".join(filter_parts)


def build_music_apply_ffmpeg_command(
    *,
    rendered_video_path: str | Path,
    segments: list[MusicApplySegment],
    output_video_path: str | Path,
    music_ducked_stem_path: str | Path,
) -> list[str]:
    filter_complex = build_music_apply_filter_complex(segments)
    command = [
        get_ffmpeg_path(),
        "-y",
        "-hide_banner",
        "-nostats",
        "-i",
        str(rendered_video_path),
    ]
    for segment in segments:
        command.extend(["-i", segment.source_file_path])
    command.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            "0:v:0",
            "-map",
            "[aout]",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-movflags",
            "+faststart",
            str(output_video_path),
            "-map",
            "[music_ducked_stem]",
            "-vn",
            "-c:a",
            "flac",
            str(music_ducked_stem_path),
        ]
    )
    return apply_ffmpeg_thread_cap(command)


def _run_ffmpeg(command: list[str]) -> None:
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        stderr_tail = "\n".join((completed.stderr or completed.stdout or "").splitlines()[-25:])
        raise MusicApplyProcessorError(
            f"music apply ffmpeg failed with exit code {completed.returncode}:\n{stderr_tail}"
        )


class MusicApplyProcessor:
    def apply(
        self,
        rendered_video_path: str | Path,
        music_application_plan: Any,
        channel_type: str,
        music_apply_timeline: MusicApplyTimeline | None,
    ) -> dict[str, Any]:
        rendered_path = Path(rendered_video_path)
        output_video_path = str(rendered_path)

        if music_apply_timeline is None or not music_apply_timeline.segments:
            return {
                "music_applied": False,
                "output_video_path": output_video_path,
            }

        segments = list(music_apply_timeline.segments)
        _validate_apply_inputs(rendered_path, segments)

        applied_video_path = _output_video_path(rendered_path)
        music_ducked_path = _music_ducked_stem_path(rendered_path)
        command = build_music_apply_ffmpeg_command(
            rendered_video_path=rendered_path,
            segments=segments,
            output_video_path=applied_video_path,
            music_ducked_stem_path=music_ducked_path,
        )

        _run_ffmpeg(command)

        result = {
            "music_applied": True,
            "output_video_path": str(applied_video_path),
            "music_apply_timeline_id": music_apply_timeline.timeline_id,
            "music_apply_segment_count": len(segments),
            "applied_music_segment_count": len(segments),
            "music_application_asset_ids": [segment.asset_id for segment in segments],
            "music_ducked_stem_path": str(music_ducked_path),
            "music_apply_filter_complex": build_music_apply_filter_complex(segments),
            "music_apply_timeline_source": "pipeline",
        }
        _context_path(rendered_path).write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return result
