from __future__ import annotations

import subprocess
from pathlib import Path
from statistics import median
from typing import Any


MUSIC_CATEGORY_FUNNY_GAMING_BACKGROUND = "funny_gaming_background"
MUSIC_CATEGORY_FAIL = "fail"
MUSIC_CATEGORY_HYPE = "hype"
MUSIC_CATEGORY_SAD = "sad"
MUSIC_CATEGORY_VLOG_BACKGROUND = "vlog_background"
MUSIC_CATEGORY_INTRO = "intro"
MUSIC_CATEGORY_OUTRO = "outro"

MOOD_FUNNY = "funny"
MOOD_FAIL = "fail"
MOOD_HYPE = "hype"
MOOD_EPIC = "epic"
MOOD_SAD = "sad"
MOOD_NEUTRAL_BACKGROUND = "neutral_background"

MOOD_ANALYSIS_SOURCE_FALLBACK_NEUTRAL_GAMING = "fallback_neutral_gaming"
MOOD_ANALYSIS_SOURCE_FALLBACK_ENERGY_TIMELINE = "fallback_energy_timeline"

DEFAULT_OWNER_GAIN_RANGE_DB = [-40.0, -35.0]
DEFAULT_OWNER_BASE_GAIN_DB = -38.0


class MusicTimelinePlannerError(RuntimeError):
    pass


def _round_sec(value: float) -> float:
    return int(float(value) * 1000.0) / 1000.0


def get_media_duration_sec(path: Path) -> float:
    media_path = Path(path)
    if not media_path.exists():
        raise MusicTimelinePlannerError(f"media file does not exist: {media_path}")

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=nw=1:nk=1",
        str(media_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    if completed.returncode != 0:
        raise MusicTimelinePlannerError(
            f"ffprobe duration failed for {media_path}: {completed.stderr.strip()}"
        )

    try:
        duration = float((completed.stdout or "").strip())
    except ValueError as exc:
        raise MusicTimelinePlannerError(f"ffprobe returned invalid duration for {media_path}") from exc

    if duration <= 0.0:
        raise MusicTimelinePlannerError(f"media duration must be positive for {media_path}")
    return duration


def classify_music_track_category(path: Path) -> str:
    categories = {
        MUSIC_CATEGORY_FUNNY_GAMING_BACKGROUND,
        MUSIC_CATEGORY_FAIL,
        MUSIC_CATEGORY_HYPE,
        MUSIC_CATEGORY_SAD,
        MUSIC_CATEGORY_VLOG_BACKGROUND,
        MUSIC_CATEGORY_INTRO,
        MUSIC_CATEGORY_OUTRO,
    }
    for part in reversed(Path(path).parts):
        normalized = part.strip().lower()
        if normalized in categories:
            return normalized
    return MUSIC_CATEGORY_FUNNY_GAMING_BACKGROUND


def mood_to_music_category(mood: str, content_type: str) -> str | None:
    normalized_content = (content_type or "").strip().lower()
    normalized_mood = (mood or MOOD_NEUTRAL_BACKGROUND).strip().lower()

    if "uncut" in normalized_content:
        return None

    if normalized_content == "vlog_main":
        if normalized_mood == MOOD_SAD:
            return MUSIC_CATEGORY_SAD
        if normalized_mood in {MOOD_NEUTRAL_BACKGROUND, MOOD_FUNNY}:
            return MUSIC_CATEGORY_VLOG_BACKGROUND
        if normalized_mood in {MOOD_HYPE, MOOD_EPIC}:
            return MUSIC_CATEGORY_VLOG_BACKGROUND
        return MUSIC_CATEGORY_VLOG_BACKGROUND

    if normalized_mood == MOOD_FUNNY:
        return MUSIC_CATEGORY_FUNNY_GAMING_BACKGROUND
    if normalized_mood == MOOD_FAIL:
        return MUSIC_CATEGORY_FAIL
    if normalized_mood in {MOOD_HYPE, MOOD_EPIC}:
        return MUSIC_CATEGORY_HYPE
    if normalized_mood == MOOD_SAD:
        return MUSIC_CATEGORY_SAD
    return MUSIC_CATEGORY_FUNNY_GAMING_BACKGROUND


def build_fallback_video_mood_timeline(video_duration_sec: float, content_type: str) -> dict[str, Any]:
    duration = float(video_duration_sec)
    if duration <= 0.0:
        raise MusicTimelinePlannerError("video_duration_sec must be positive")

    normalized_content = (content_type or "").strip().lower()
    if "uncut" in normalized_content:
        return {
            "mood_analysis_source": "blocked_uncut_no_music",
            "true_ai_mood_detection_used": False,
            "mood_category_mapping_enabled": False,
            "mood_timeline": [],
        }

    segment_target_sec = 120.0 if duration <= 900.0 else 150.0
    segments = []
    cursor = 0.0

    while cursor < duration - 0.001:
        end = min(duration, cursor + segment_target_sec)
        mood = MOOD_FUNNY if normalized_content == "gaming_main" else MOOD_NEUTRAL_BACKGROUND
        segments.append(
            {
                "start_sec": _round_sec(cursor),
                "end_sec": _round_sec(end),
                "mood": mood,
                "source": MOOD_ANALYSIS_SOURCE_FALLBACK_NEUTRAL_GAMING,
            }
        )
        cursor = end

    return {
        "mood_analysis_source": MOOD_ANALYSIS_SOURCE_FALLBACK_NEUTRAL_GAMING,
        "true_ai_mood_detection_used": False,
        "mood_category_mapping_enabled": True,
        "mood_timeline": segments,
    }


def compute_adaptive_track_gain(
    track_mean_volume_db: float,
    reference_track_mean_volume_db: float,
    owner_gain_range_db: list[float] | tuple[float, float] = DEFAULT_OWNER_GAIN_RANGE_DB,
    owner_base_gain_db: float = DEFAULT_OWNER_BASE_GAIN_DB,
) -> dict[str, Any]:
    raw_gain_db = float(owner_base_gain_db) + (
        float(reference_track_mean_volume_db) - float(track_mean_volume_db)
    )
    lower = float(min(owner_gain_range_db))
    upper = float(max(owner_gain_range_db))
    final_gain_db = min(max(raw_gain_db, lower), upper)
    return {
        "raw_gain_db": round(raw_gain_db, 3),
        "final_gain_db": round(final_gain_db, 3),
        "clamped": abs(raw_gain_db - final_gain_db) > 0.0001,
    }


def _tracks_by_category(available_tracks: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for track in available_tracks:
        category = str(track.get("category") or MUSIC_CATEGORY_FUNNY_GAMING_BACKGROUND)
        grouped.setdefault(category, []).append(track)
    return grouped


def _pick_track(
    candidates: list[dict[str, Any]],
    category_usage: dict[str, int],
    last_track_path: str | None,
) -> dict[str, Any]:
    if not candidates:
        raise MusicTimelinePlannerError("no music candidates available")

    ordered = sorted(
        candidates,
        key=lambda track: (
            category_usage.get(str(track["path"]), 0),
            str(track["path"]),
        ),
    )

    if len(ordered) > 1:
        for track in ordered:
            if str(track["path"]) != last_track_path:
                return track

    return ordered[0]


def _allowed_fallback_category(content_type: str, grouped: dict[str, list[dict[str, Any]]]) -> str | None:
    normalized_content = (content_type or "").strip().lower()
    if "uncut" in normalized_content:
        return None
    if normalized_content == "vlog_main":
        if MUSIC_CATEGORY_VLOG_BACKGROUND in grouped:
            return MUSIC_CATEGORY_VLOG_BACKGROUND
        if MUSIC_CATEGORY_SAD in grouped:
            return MUSIC_CATEGORY_SAD
        return None
    if MUSIC_CATEGORY_FUNNY_GAMING_BACKGROUND in grouped:
        return MUSIC_CATEGORY_FUNNY_GAMING_BACKGROUND
    for category in (MUSIC_CATEGORY_HYPE, MUSIC_CATEGORY_FAIL, MUSIC_CATEGORY_SAD):
        if category in grouped:
            return category
    return None



DEFAULT_TRACK_START_TRIM_SEC = 30.0
DEFAULT_TRACK_END_TRIM_SEC = 15.0
MINIMUM_MUSIC_SEGMENT_DURATION_SEC = 45.0
MINIMUM_REUSE_SEGMENT_DURATION_SEC = 60.0


def _usable_track_window(duration_sec: float) -> dict[str, float]:
    duration = max(0.0, float(duration_sec))
    source_start = min(DEFAULT_TRACK_START_TRIM_SEC, duration)
    source_end = max(source_start, duration - DEFAULT_TRACK_END_TRIM_SEC)
    usable_duration = max(0.0, source_end - source_start)
    if usable_duration <= 0.001:
        source_start = 0.0
        source_end = duration
        usable_duration = duration
    return {
        "track_source_start_sec": source_start,
        "track_source_end_sec": source_end,
        "track_usable_duration_sec": usable_duration,
    }


def plan_music_timeline(
    *,
    video_duration_sec: float,
    available_tracks: list[dict[str, Any]],
    content_type: str,
    mood_timeline: list[dict[str, Any]] | None = None,
    owner_gain_range_db: list[float] | tuple[float, float] = DEFAULT_OWNER_GAIN_RANGE_DB,
    owner_base_gain_db: float = DEFAULT_OWNER_BASE_GAIN_DB,
) -> dict[str, Any]:
    duration = float(video_duration_sec)
    normalized_content = (content_type or "").strip().lower()

    if duration <= 0.0:
        raise MusicTimelinePlannerError("video_duration_sec must be positive")

    if "uncut" in normalized_content:
        return {
            "status": "blocked_uncut_no_music",
            "music_timeline_planner_enabled": True,
            "video_duration_sec": _round_sec(duration),
            "music_timeline": [],
            "music_timeline_segment_count": 0,
            "selected_music_track_count": 0,
            "used_music_categories": [],
            "single_song_loop": False,
            "direct_repeat_allowed": False,
            "track_duration_aware_selection": True,
            "duration_based_song_count": True,
            "mood_category_mapping_enabled": True,
            "true_ai_mood_detection_used": False,
            "mood_analysis_source": "blocked_uncut_no_music",
            "adaptive_track_gain_enabled": True,
            "gain_range_db": list(owner_gain_range_db),
        }

    if not available_tracks:
        raise MusicTimelinePlannerError("available_tracks must not be empty")

    normalized_tracks: list[dict[str, Any]] = []
    for track in available_tracks:
        path = str(track.get("path") or "").strip()
        duration_sec = float(track.get("duration_sec") or 0.0)
        mean_volume_db = float(track.get("mean_volume_db"))
        if not path:
            raise MusicTimelinePlannerError("track path is required")
        if duration_sec <= 0.0:
            raise MusicTimelinePlannerError(f"track duration must be positive for {path}")
        category = str(track.get("category") or classify_music_track_category(Path(path)))
        if normalized_content == "gaming_main" and category == MUSIC_CATEGORY_VLOG_BACKGROUND:
            continue
        normalized_tracks.append(
            {
                **track,
                "path": path,
                "category": category,
                "duration_sec": duration_sec,
                "mean_volume_db": mean_volume_db,
            }
        )

    if not normalized_tracks:
        raise MusicTimelinePlannerError("no allowed music tracks available")

    reference_mean_volume_db = float(median([track["mean_volume_db"] for track in normalized_tracks]))
    grouped = _tracks_by_category(normalized_tracks)

    if mood_timeline is None:
        fallback = build_fallback_video_mood_timeline(duration, normalized_content)
        mood_timeline = fallback["mood_timeline"]
        mood_analysis_source = fallback["mood_analysis_source"]
        true_ai_mood_detection_used = False
        mood_category_mapping_enabled = fallback["mood_category_mapping_enabled"]
    else:
        mood_analysis_source = "provided_mood_timeline"
        true_ai_mood_detection_used = False
        mood_category_mapping_enabled = True

    if not mood_timeline:
        mood_timeline = [
            {
                "start_sec": 0.0,
                "end_sec": duration,
                "mood": MOOD_NEUTRAL_BACKGROUND,
            }
        ]

    timeline = []
    category_usage: dict[str, int] = {}
    last_track_path: str | None = None

    for mood_segment in mood_timeline:
        segment_start = max(0.0, float(mood_segment.get("start_sec", 0.0)))
        segment_end = min(duration, float(mood_segment.get("end_sec", duration)))
        if segment_end <= segment_start:
            continue

        mood = str(mood_segment.get("mood") or MOOD_NEUTRAL_BACKGROUND)
        requested_category = mood_to_music_category(mood, normalized_content)
        if requested_category is None:
            continue

        category = requested_category if requested_category in grouped else _allowed_fallback_category(
            normalized_content, grouped
        )
        if category is None:
            continue

        cursor = segment_start
        while cursor < segment_end - 0.001:
            track = _pick_track(grouped[category], category_usage, last_track_path)
            track_path = str(track["path"])
            available_track_duration = float(track["duration_sec"])
            usable_window = _usable_track_window(available_track_duration)
            track_usable_duration = float(usable_window["track_usable_duration_sec"])
            remaining_segment = segment_end - cursor
            used_duration = min(track_usable_duration, remaining_segment)

            remaining_after_use = max(0.0, remaining_segment - used_duration)
            if (
                0.001 < remaining_after_use < MINIMUM_MUSIC_SEGMENT_DURATION_SEC
                and used_duration + remaining_after_use <= track_usable_duration
            ):
                used_duration = remaining_segment

            gain = compute_adaptive_track_gain(
                track["mean_volume_db"],
                reference_mean_volume_db,
                owner_gain_range_db,
                owner_base_gain_db,
            )

            timeline.append(
                {
                    "start_sec": _round_sec(cursor),
                    "end_sec": _round_sec(cursor + used_duration),
                    "mood": mood,
                    "music_category": category,
                    "requested_music_category": requested_category,
                    "track_path": track_path,
                    "track_duration_sec": _round_sec(available_track_duration),
                    "track_usable_duration_sec": _round_sec(track_usable_duration),
                    "track_start_sec": _round_sec(float(usable_window["track_source_start_sec"])),
                    "track_source_start_sec": _round_sec(float(usable_window["track_source_start_sec"])),
                    "track_source_end_sec": _round_sec(float(usable_window["track_source_start_sec"]) + used_duration),
                    "track_used_duration_sec": _round_sec(used_duration),
                    "reused_track": category_usage.get(track_path, 0) > 0,
                    "segment_is_micro_tail": (
                        segment_end - (cursor + used_duration) <= 0.001
                        and used_duration < MINIMUM_MUSIC_SEGMENT_DURATION_SEC
                    ),
                    "segment_has_real_music_source": True,
                    "gain_db": gain["final_gain_db"],
                    "raw_gain_db": gain["raw_gain_db"],
                    "clamped": gain["clamped"],
                    "transition_type": "cut_or_short_crossfade",
                }
            )

            category_usage[track_path] = category_usage.get(track_path, 0) + 1
            last_track_path = track_path
            cursor += used_duration

            if used_duration <= 0.001:
                raise MusicTimelinePlannerError("planner made no progress")

    used_categories = sorted({segment["music_category"] for segment in timeline})
    selected_tracks = []
    seen = set()
    for segment in timeline:
        track_path = segment["track_path"]
        if track_path in seen:
            continue
        seen.add(track_path)
        selected_tracks.append(track_path)

    direct_repeat_found = any(
        timeline[index]["track_path"] == timeline[index - 1]["track_path"]
        for index in range(1, len(timeline))
    )

    return {
        "status": "ok",
        "music_timeline_planner_enabled": True,
        "video_duration_sec": _round_sec(duration),
        "music_timeline": timeline,
        "music_timeline_segment_count": len(timeline),
        "selected_music_track_count": len(selected_tracks),
        "timeline_selected_music_tracks": selected_tracks,
        "used_music_categories": used_categories,
        "single_song_loop": len(selected_tracks) == 1 and len(timeline) > 1,
        "direct_repeat_allowed": False,
        "direct_repeat_found": direct_repeat_found,
        "track_duration_aware_selection": True,
        "duration_based_song_count": True,
        "mood_category_mapping_enabled": mood_category_mapping_enabled,
        "mood_based_category_switching": "fallback_only",
        "true_ai_mood_detection_used": true_ai_mood_detection_used,
        "mood_analysis_source": mood_analysis_source,
        "adaptive_track_gain_enabled": True,
        "gain_range_db": list(owner_gain_range_db),
        "all_timeline_gains_between_minus_40_and_minus_35": all(
            min(owner_gain_range_db) <= segment["gain_db"] <= max(owner_gain_range_db)
            for segment in timeline
        ),
    }
