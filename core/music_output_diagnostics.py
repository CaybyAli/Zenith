from __future__ import annotations

import json
import math
import re
import subprocess
from pathlib import Path
from typing import Any

MUSIC_STEM_AUDIBLE_FLOOR_DB = -70.0
VOICE_WINDOW_MUSIC_BELOW_VOICE_DB_MIN = 18.0
OWNER_TAIL_START_SEC = 471.0


class MusicOutputDiagnosticsError(ValueError):
    pass


def _round_sec(value: float) -> float:
    return round(float(value), 3)


def _round_db(value: float | None) -> float | None:
    if value is None or not math.isfinite(float(value)):
        return None
    return round(float(value), 3)


def _window_level_db(window: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        value = window.get(key)
        if value is None:
            continue
        try:
            level = float(value)
        except (TypeError, ValueError):
            continue
        if math.isfinite(level):
            return level
    return None


def _is_audible(window: dict[str, Any], floor_db: float = MUSIC_STEM_AUDIBLE_FLOOR_DB) -> bool:
    level = _window_level_db(window, "mean_volume_db", "rms_db")
    return level is not None and level > floor_db


def build_audio_stem_truth_gate(
    *,
    music_auto_stem_path: str | Path | None = None,
    music_auto_stem_duration_sec: float | None = None,
    expected_duration_sec: float | None = None,
    tail_window_stats: list[dict[str, Any]] | None = None,
    song_start_window_stats: list[dict[str, Any]] | None = None,
    voice_music_relative_stats: list[dict[str, Any]] | None = None,
    final_mix_tail_stats: list[dict[str, Any]] | None = None,
    audible_floor_db: float = MUSIC_STEM_AUDIBLE_FLOOR_DB,
    relative_min_db: float = VOICE_WINDOW_MUSIC_BELOW_VOICE_DB_MIN,
) -> dict[str, Any]:
    tail_windows = list(tail_window_stats or [])
    song_windows = list(song_start_window_stats or [])
    relative_windows = list(voice_music_relative_stats or [])
    final_tail_windows = list(final_mix_tail_stats or [])

    stem_exists = bool(music_auto_stem_path) and Path(music_auto_stem_path).exists()
    duration = None if music_auto_stem_duration_sec is None else float(music_auto_stem_duration_sec)
    expected = None if expected_duration_sec is None else float(expected_duration_sec)
    stem_reaches_expected_end = (
        stem_exists
        and duration is not None
        and expected is not None
        and duration >= expected - 0.75
    )
    missing_tail_duration = bool(
        stem_exists
        and expected is not None
        and expected > OWNER_TAIL_START_SEC
        and not stem_reaches_expected_end
    )

    tail_silent_window_count = sum(1 for window in tail_windows if not _is_audible(window, audible_floor_db))
    if missing_tail_duration:
        tail_silent_window_count = max(1, tail_silent_window_count)
    tail_checked = bool(stem_exists and tail_windows)
    tail_audible = tail_checked and tail_silent_window_count == 0 and not missing_tail_duration

    song_start_silent_window_count = sum(1 for window in song_windows if not _is_audible(window, audible_floor_db))
    song_checked = bool(stem_exists and song_windows)
    song_starts_audible = song_checked and song_start_silent_window_count == 0

    margins: list[float] = []
    for window in relative_windows:
        if "music_below_voice_db" in window:
            try:
                margin = float(window["music_below_voice_db"])
            except (TypeError, ValueError):
                continue
        else:
            voice_level = _window_level_db(window, "voice_proxy_mean_volume_db", "voice_rms_db")
            music_level = _window_level_db(window, "music_auto_mean_volume_db", "music_rms_db")
            if voice_level is None or music_level is None:
                continue
            margin = voice_level - music_level
        if math.isfinite(margin):
            margins.append(margin)

    relative_checked = bool(relative_windows)
    relative_passed = bool(relative_checked and margins and min(margins) >= relative_min_db)
    if relative_checked and not margins:
        relative_passed = False

    final_tail_checked = bool(final_tail_windows)
    final_tail_audible = final_tail_checked and all(_is_audible(window, audible_floor_db) for window in final_tail_windows)
    final_tail_passed = bool(tail_audible and final_tail_audible)

    blocked_reason = None
    if not stem_exists:
        blocked_reason = "audio_stem_probe_missing"
    elif not tail_audible:
        blocked_reason = "music_auto_tail_not_audible"
    elif not song_starts_audible:
        blocked_reason = "song_start_music_not_audible"
    elif not relative_passed:
        blocked_reason = "music_too_close_to_voice"

    return {
        "audio_stem_diagnosis_enabled": True,
        "manifest_truth_requires_audio_stem_probe": True,
        "music_auto_stem_generated_for_gate": stem_exists,
        "music_auto_stem_path": str(music_auto_stem_path) if music_auto_stem_path else None,
        "music_auto_stem_duration_sec": _round_sec(duration) if duration is not None else None,
        "music_auto_expected_duration_sec": _round_sec(expected) if expected is not None else None,
        "music_auto_stem_reaches_expected_end": stem_reaches_expected_end,
        "music_auto_tail_rms_checked": tail_checked,
        "music_auto_tail_audible": tail_audible,
        "music_auto_tail_silent_window_count": int(tail_silent_window_count),
        "song_start_music_stem_checked": song_checked,
        "song_start_silent_window_count": int(song_start_silent_window_count),
        "music_vs_voice_relative_gate_enabled": True,
        "voice_window_music_below_voice_db_min": float(relative_min_db),
        "voice_window_music_below_voice_min_observed_db": _round_db(min(margins)) if margins else None,
        "voice_window_music_below_voice_passed": relative_passed,
        "final_mix_tail_probe_passed": final_tail_passed,
        "status": "blocked" if blocked_reason else "diagnosis_ok",
        "blocked_reason": blocked_reason,
    }


def apply_audio_stem_truth_gate(manifest: dict[str, Any], gate: dict[str, Any]) -> dict[str, Any]:
    previous_status = manifest.get("status")
    previous_blocked_reason = manifest.get("blocked_reason")
    result = dict(manifest)
    result.update(gate)

    if result.get("manifest_truth_requires_audio_stem_probe") is not True:
        return result

    gate_passed = (
        result.get("music_auto_stem_generated_for_gate") is True
        and result.get("music_auto_tail_audible") is True
        and int(result.get("music_auto_tail_silent_window_count", 1) or 0) == 0
        and result.get("song_start_music_stem_checked") is True
        and int(result.get("song_start_silent_window_count", 1) or 0) == 0
        and result.get("voice_window_music_below_voice_passed") is True
        and result.get("final_mix_tail_probe_passed") is True
    )

    result["audio_stem_probe_passed"] = gate_passed
    result["musicbed_no_silent_gaps"] = bool(result.get("musicbed_no_silent_gaps", False) and gate_passed)
    result["musicbed_full_coverage_confirmed"] = bool(
        result.get("musicbed_full_coverage_confirmed", False) and gate_passed
    )
    result["musicbed_no_silent_gaps_verified_by_audio_stem"] = gate_passed

    if not gate_passed:
        result["status"] = "blocked"
        result["blocked_reason"] = str(gate.get("blocked_reason") or "audio_stem_probe_missing")
    elif previous_status == "blocked":
        result["status"] = "blocked"
        result["blocked_reason"] = previous_blocked_reason

    return result


def extract_filter_complex(command: list[str]) -> str:
    try:
        index = command.index("-filter_complex")
    except ValueError as exc:
        raise MusicOutputDiagnosticsError("ffmpeg command is missing filter_complex") from exc
    try:
        return str(command[index + 1])
    except IndexError as exc:
        raise MusicOutputDiagnosticsError("ffmpeg command has no filter_complex value") from exc


def build_audio_stem_command(command: list[str], *, stem_label: str, output_path: str | Path) -> list[str]:
    output = Path(output_path)
    if output.suffix.lower() == ".mp4":
        raise MusicOutputDiagnosticsError("audio stem diagnosis must not write MP4")

    filter_complex = extract_filter_complex(command)
    if stem_label == "musicbed":
        stem_filter = re.sub(r";\[musicbed\]asplit=.*$", "", filter_complex)
        map_label = "[musicbed]"
    elif stem_label == "music_auto":
        stem_filter = re.sub(r";\[music_auto\]anull\[ducked\];\[0:a\]\[ducked\]amix=.*$", "", filter_complex)
        map_label = "[music_auto]"
    elif stem_label == "aout":
        stem_filter = filter_complex
        map_label = "[aout]"
    else:
        raise MusicOutputDiagnosticsError(f"unsupported stem label: {stem_label}")

    filter_index = command.index("-filter_complex")
    prefix = list(command[:filter_index])
    return prefix + [
        "-filter_complex",
        stem_filter,
        "-map",
        map_label,
        "-vn",
        "-c:a",
        "flac",
        str(output),
    ]


def run_checked_command(command: list[str], *, stdout_path: Path | None = None, stderr_path: Path | None = None) -> None:
    completed = subprocess.run(command, capture_output=True, text=True)
    if stdout_path:
        stdout_path.write_text(completed.stdout, encoding="utf-8")
    if stderr_path:
        stderr_path.write_text(completed.stderr, encoding="utf-8")
    if completed.returncode != 0:
        raise MusicOutputDiagnosticsError(f"command failed with exit code {completed.returncode}: {command[0]}")


def probe_audio_duration_sec(path: str | Path) -> float:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise MusicOutputDiagnosticsError(f"ffprobe failed for {path}: {completed.stderr.strip()}")
    data = json.loads(completed.stdout or "{}")
    return float(data.get("format", {}).get("duration", 0.0) or 0.0)


def probe_volume_window(path: str | Path, *, start_sec: float, end_sec: float) -> dict[str, Any]:
    start = max(0.0, float(start_sec))
    end = max(start, float(end_sec))
    duration = max(0.001, end - start)
    command = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-ss",
        f"{start:.3f}",
        "-t",
        f"{duration:.3f}",
        "-i",
        str(path),
        "-af",
        "volumedetect",
        "-f",
        "null",
        "-",
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    text = f"{completed.stdout}\n{completed.stderr}"
    mean_match = re.search(r"mean_volume:\s*(-?(?:inf|\d+(?:\.\d+)?))\s*dB", text)
    max_match = re.search(r"max_volume:\s*(-?(?:inf|\d+(?:\.\d+)?))\s*dB", text)

    def _parse(match: re.Match[str] | None) -> float | None:
        if not match:
            return None
        value = match.group(1)
        if value in {"inf", "-inf"}:
            return None
        return float(value)

    return {
        "path": str(path),
        "start_sec": _round_sec(start),
        "end_sec": _round_sec(end),
        "duration_sec": _round_sec(duration),
        "mean_volume_db": _round_db(_parse(mean_match)),
        "max_volume_db": _round_db(_parse(max_match)),
        "ffmpeg_returncode": completed.returncode,
    }


def default_final_mix_windows(video_duration_sec: float) -> list[dict[str, float]]:
    duration = float(video_duration_sec)
    ranges = [
        (0.0, min(60.0, duration)),
        (100.0, min(120.0, duration)),
        (240.0, min(300.0, duration)),
        (OWNER_TAIL_START_SEC, duration),
        (max(0.0, duration - 30.0), duration),
    ]
    return [
        {"start_sec": _round_sec(start), "end_sec": _round_sec(end)}
        for start, end in ranges
        if end > start
    ]


def tail_probe_windows(video_duration_sec: float, *, window_sec: float = 10.0) -> list[dict[str, float]]:
    duration = float(video_duration_sec)
    windows: list[dict[str, float]] = []
    start = min(OWNER_TAIL_START_SEC, duration)
    while start < duration - 1e-6:
        end = min(start + window_sec, duration)
        windows.append({"start_sec": _round_sec(start), "end_sec": _round_sec(end)})
        start = end
    return windows


def song_start_probe_windows(music_timeline: list[dict[str, Any]], video_duration_sec: float) -> list[dict[str, Any]]:
    duration = float(video_duration_sec)
    windows: list[dict[str, Any]] = []
    for index, segment in enumerate(music_timeline or [], start=1):
        start = max(0.0, float(segment.get("start_sec", 0.0)))
        end = min(duration, start + 10.0)
        if end <= start:
            continue
        windows.append(
            {
                "segment_index": index,
                "track_path": segment.get("track_path") or segment.get("path"),
                "start_sec": _round_sec(start),
                "end_sec": _round_sec(end),
            }
        )
    return windows


def probe_windows(path: str | Path, windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    stats: list[dict[str, Any]] = []
    for window in windows:
        item = probe_volume_window(path, start_sec=float(window["start_sec"]), end_sec=float(window["end_sec"]))
        item.update({key: value for key, value in window.items() if key not in item})
        stats.append(item)
    return stats


def build_relative_voice_music_stats(
    *,
    voice_proxy_stats: list[dict[str, Any]],
    music_auto_stats: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for voice, music in zip(voice_proxy_stats, music_auto_stats):
        voice_level = _window_level_db(voice, "mean_volume_db")
        music_level = _window_level_db(music, "mean_volume_db")
        margin = None if voice_level is None or music_level is None else voice_level - music_level
        result.append(
            {
                "start_sec": voice.get("start_sec"),
                "end_sec": voice.get("end_sec"),
                "voice_proxy_mean_volume_db": _round_db(voice_level),
                "music_auto_mean_volume_db": _round_db(music_level),
                "music_below_voice_db": _round_db(margin),
            }
        )
    return result


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
