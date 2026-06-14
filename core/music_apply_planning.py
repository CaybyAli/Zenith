from __future__ import annotations

import hashlib
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.music_timeline_planner import (
    MUSIC_CATEGORY_FUNNY_GAMING_BACKGROUND,
    classify_music_track_category,
    get_media_duration_sec,
    plan_music_timeline,
)
from core.profile_manager import ProfileManager
from models.music_apply_segment import MusicApplySegment
from models.music_apply_timeline import MusicApplyTimeline


DEFAULT_MUSIC_ASSETS_DIR = Path("local_assets/music/main_account/funny_gaming_background")
SUPPORTED_MUSIC_EXTENSIONS = {".aac", ".flac", ".m4a", ".mp3", ".ogg", ".wav"}
TARGET_MUSIC_ST_P95_LUFS = -17.0

_EBUR128_SHORTTERM_RE = re.compile(
    r"t:\s*[-+]?\d+(?:\.\d+)?\s+"
    r"TARGET:\s*[-+]?\d+(?:\.\d+)?\s+LUFS\s+"
    r"M:\s*[-+]?\d+(?:\.\d+)?\s+"
    r"S:\s*(?P<shortterm>[-+]?\d+(?:\.\d+)?)"
)
_MEAN_VOLUME_RE = re.compile(r"mean_volume:\s*(?P<mean>[-+]?\d+(?:\.\d+)?)\s*dB")


class MusicApplyPlanningError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MusicApplyPlanningResult:
    status: str
    reason: str | None
    timeline_path: str | None
    segment_count: int


def _null_output_path() -> str:
    return "NUL" if os.name == "nt" else "/dev/null"


def _string_value(value: Any) -> str:
    if hasattr(value, "value"):
        value = value.value
    return str(value or "").strip().lower()


def _round_db(value: float) -> float:
    return round(float(value), 3)


def _round_sec(value: float) -> float:
    return round(float(value), 3)


def _run_ffmpeg_probe(command: list[str], error_label: str) -> str:
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise MusicApplyPlanningError(
            f"{error_label} failed: {(completed.stderr or completed.stdout).strip()}"
        )
    return f"{completed.stdout or ''}\n{completed.stderr or ''}"


def calculate_short_term_p95_from_samples(shortterm_lufs_samples: list[float]) -> float:
    filtered = [
        float(sample)
        for sample in shortterm_lufs_samples
        if float(sample) > -100.0
    ]
    if not filtered:
        raise MusicApplyPlanningError("short-term p95 requires non-silent ebur128 samples")

    ordered = sorted(filtered)
    index = int(round(0.95 * (len(ordered) - 1)))
    return _round_db(ordered[index])


def calculate_music_level_gain_db(
    short_term_p95_lufs: float,
    *,
    target_lufs: float = TARGET_MUSIC_ST_P95_LUFS,
) -> float:
    return _round_db(float(target_lufs) - float(short_term_p95_lufs))


def measure_short_term_p95_lufs(music_file: str | Path) -> float:
    path = Path(music_file)
    if not path.exists():
        raise MusicApplyPlanningError(f"music file does not exist: {path}")

    output = _run_ffmpeg_probe(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "verbose",
            "-nostats",
            "-i",
            str(path),
            "-filter:a",
            "ebur128=framelog=verbose",
            "-f",
            "null",
            _null_output_path(),
        ],
        f"ffmpeg ebur128 short-term p95 probe for {path}",
    )
    samples = [
        float(match.group("shortterm"))
        for match in _EBUR128_SHORTTERM_RE.finditer(output)
    ]
    return calculate_short_term_p95_from_samples(samples)


def measure_mean_volume_db(music_file: str | Path) -> float:
    path = Path(music_file)
    if not path.exists():
        raise MusicApplyPlanningError(f"music file does not exist: {path}")

    output = _run_ffmpeg_probe(
        [
            "ffmpeg",
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-filter:a",
            "volumedetect",
            "-f",
            "null",
            _null_output_path(),
        ],
        f"ffmpeg volumedetect probe for {path}",
    )
    match = _MEAN_VOLUME_RE.search(output)
    if match is None:
        raise MusicApplyPlanningError(f"mean_volume missing in ffmpeg output for {path}")
    return _round_db(float(match.group("mean")))


def collect_available_music_tracks(
    music_assets_dir: str | Path = DEFAULT_MUSIC_ASSETS_DIR,
) -> list[dict[str, Any]]:
    assets_dir = Path(music_assets_dir)
    if not assets_dir.exists():
        raise MusicApplyPlanningError(f"music assets directory does not exist: {assets_dir}")

    tracks: list[dict[str, Any]] = []
    for music_file in sorted(assets_dir.iterdir(), key=lambda item: item.name.lower()):
        if not music_file.is_file():
            continue
        if music_file.suffix.lower() not in SUPPORTED_MUSIC_EXTENSIONS:
            continue

        tracks.append(
            {
                "path": music_file.as_posix(),
                "duration_sec": _round_sec(get_media_duration_sec(music_file)),
                "mean_volume_db": measure_mean_volume_db(music_file),
                "category": classify_music_track_category(music_file)
                or MUSIC_CATEGORY_FUNNY_GAMING_BACKGROUND,
            }
        )

    if not tracks:
        raise MusicApplyPlanningError(f"no supported music tracks found in {assets_dir}")
    return tracks


def _asset_id_for_track(track_path: str) -> str:
    digest = hashlib.sha1(track_path.encode("utf-8")).hexdigest()[:12]
    return f"music_{digest}"


def _timeline_to_apply_segments(
    *,
    job_id: str,
    music_timeline: list[dict[str, Any]],
    per_song_gain_db: dict[str, float],
    per_song_st_p95_lufs: dict[str, float],
) -> list[MusicApplySegment]:
    segments: list[MusicApplySegment] = []
    for index, planned_segment in enumerate(music_timeline, start=1):
        track_path = str(planned_segment["track_path"])
        st_p95 = per_song_st_p95_lufs[track_path]
        gain_db = per_song_gain_db[track_path]
        segments.append(
            MusicApplySegment(
                segment_id=f"music_apply_segment_{index:03d}",
                job_id=job_id,
                asset_id=_asset_id_for_track(track_path),
                cue_kind=str(planned_segment.get("music_category") or "background_bed"),
                source_file_path=track_path,
                video_start_time=_round_sec(float(planned_segment["start_sec"])),
                video_end_time=_round_sec(float(planned_segment["end_sec"])),
                music_offset_start=_round_sec(float(planned_segment["track_source_start_sec"])),
                music_offset_end=_round_sec(float(planned_segment["track_source_end_sec"])),
                music_level=gain_db,
                voice_priority=True,
                ducking_required=True,
                fade_in_seconds=_round_sec(float(planned_segment.get("crossfade_in_sec", 0.0) or 0.0)),
                fade_out_seconds=_round_sec(float(planned_segment.get("crossfade_out_sec", 0.0) or 0.0)),
                notes=[
                    "source=music_apply_planning",
                    f"short_term_p95_lufs={st_p95:.3f}",
                    f"target_music_st_p95_lufs={TARGET_MUSIC_ST_P95_LUFS:.3f}",
                    f"per_song_gain_db={gain_db:.3f}",
                ],
            )
        )
    return segments


def build_and_save_music_apply_timeline(
    *,
    export_path: str | Path,
    video_duration_sec: float,
    job_id: str,
    channel_type: str,
    music_enabled: bool,
    content_type: str | None = None,
    music_assets_dir: str | Path = DEFAULT_MUSIC_ASSETS_DIR,
    mood_timeline: list[dict[str, Any]] | None = None,
) -> MusicApplyPlanningResult:
    normalized_channel = _string_value(channel_type)
    normalized_content = _string_value(content_type or normalized_channel)
    timeline_path = Path(export_path) / "music_apply_timeline.json"

    if normalized_channel != "gaming_main":
        return MusicApplyPlanningResult(
            status="skipped",
            reason="channel_not_gaming_main",
            timeline_path=None,
            segment_count=0,
        )
    if not bool(music_enabled):
        return MusicApplyPlanningResult(
            status="skipped",
            reason="music_disabled",
            timeline_path=None,
            segment_count=0,
        )
    if "uncut" in normalized_content:
        return MusicApplyPlanningResult(
            status="skipped",
            reason="content_type_uncut",
            timeline_path=None,
            segment_count=0,
        )

    available_tracks = collect_available_music_tracks(music_assets_dir)
    plan = plan_music_timeline(
        video_duration_sec=float(video_duration_sec),
        available_tracks=available_tracks,
        content_type=normalized_content,
        mood_timeline=mood_timeline,
    )
    if plan.get("status") != "ok":
        return MusicApplyPlanningResult(
            status="skipped",
            reason=str(plan.get("status") or "planner_not_ok"),
            timeline_path=None,
            segment_count=0,
        )

    planned_timeline = list(plan.get("music_timeline") or [])
    selected_track_paths = sorted({str(segment["track_path"]) for segment in planned_timeline})
    per_song_st_p95_lufs = {
        track_path: measure_short_term_p95_lufs(track_path)
        for track_path in selected_track_paths
    }
    per_song_gain_db = {
        track_path: calculate_music_level_gain_db(st_p95)
        for track_path, st_p95 in per_song_st_p95_lufs.items()
    }

    timeline = MusicApplyTimeline(
        timeline_id=f"music_apply_timeline_{job_id}",
        job_id=job_id,
        channel_type=normalized_channel,
        segments=_timeline_to_apply_segments(
            job_id=job_id,
            music_timeline=planned_timeline,
            per_song_gain_db=per_song_gain_db,
            per_song_st_p95_lufs=per_song_st_p95_lufs,
        ),
        timeline_score=1.0,
        notes=[
            "source=music_apply_planning",
            f"assets_dir={Path(music_assets_dir).as_posix()}",
            "short_term_p95_method=ffmpeg_ebur128_framelog_verbose_percentile_95",
            f"target_music_st_p95_lufs={TARGET_MUSIC_ST_P95_LUFS:.3f}",
            f"planner_status={plan.get('status')}",
        ],
    )

    from core.music_apply_timeline_repository import MusicApplyTimelineRepository

    saved_path = MusicApplyTimelineRepository().save_timeline(export_path, timeline)
    return MusicApplyPlanningResult(
        status="created",
        reason=None,
        timeline_path=saved_path,
        segment_count=len(timeline.segments),
    )


def _resolve_job_music_enabled(job: Any, channel_type: str) -> bool:
    profile_metadata = getattr(job, "profile_metadata", None)
    if isinstance(profile_metadata, dict) and isinstance(profile_metadata.get("music_enabled"), bool):
        return bool(profile_metadata["music_enabled"])

    profile_id = _string_value(getattr(job, "profile_id", None)) or channel_type
    try:
        profile = ProfileManager().load_profile(profile_id)
    except Exception as exc:
        raise MusicApplyPlanningError(
            f"music_enabled could not be resolved for profile {profile_id}"
        ) from exc

    value = profile.get("music_enabled")
    if not isinstance(value, bool):
        raise MusicApplyPlanningError(
            f"profile {profile_id} has non-boolean music_enabled"
        )
    return value


def ensure_music_apply_timeline_for_render_export(
    *,
    job: Any,
    export_path: str | Path,
    video_duration_sec: float,
) -> MusicApplyPlanningResult:
    channel_type = _string_value(getattr(job, "channel_type", ""))
    if channel_type != "gaming_main":
        return MusicApplyPlanningResult(
            status="skipped",
            reason="channel_not_gaming_main",
            timeline_path=None,
            segment_count=0,
        )

    music_enabled = _resolve_job_music_enabled(job, channel_type)
    return build_and_save_music_apply_timeline(
        export_path=export_path,
        video_duration_sec=video_duration_sec,
        job_id=str(getattr(job, "job_id", "")),
        channel_type=channel_type,
        music_enabled=music_enabled,
        content_type=channel_type,
    )
