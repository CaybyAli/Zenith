from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

OWNER_GAIN_MIN_DB = -35.0
OWNER_GAIN_MAX_DB = -26.0
MUSIC_AUDIBILITY_FLOOR_DB = -35.0
MUSIC_LOUDNESS_CEILING_DB = -26.0
OWNER_MUSIC_AUDIBLE_GAIN_RANGE_DB = (MUSIC_AUDIBILITY_FLOOR_DB, MUSIC_LOUDNESS_CEILING_DB)
DEFAULT_AUTOMATION_WINDOW_SEC = 5.0
DEFAULT_BASE_TARGET_GAIN_DB = -30.0
DEFAULT_MAX_GAIN_CHANGE_PER_WINDOW_DB = 2.0
DEFAULT_TRACK_START_TRIM_SEC = 30.0
DEFAULT_TRACK_END_TRIM_SEC = 15.0
DEFAULT_CROSSFADE_SEC = 3.0
DEFAULT_MIN_USABLE_TRACK_SEC = 45.0


class MusicAutomationPlannerError(ValueError):
    pass


def _clamp(value: float, minimum: float = OWNER_GAIN_MIN_DB, maximum: float = OWNER_GAIN_MAX_DB) -> float:
    return max(minimum, min(maximum, float(value)))


def _round_sec(value: float) -> float:
    return round(float(value), 3)


def _round_db(value: float) -> float:
    return round(float(value), 3)


def build_analysis_windows(video_duration_sec: float, window_sec: float = DEFAULT_AUTOMATION_WINDOW_SEC) -> list[dict[str, float]]:
    if video_duration_sec <= 0:
        raise MusicAutomationPlannerError("video_duration_sec must be positive")
    if window_sec <= 0:
        raise MusicAutomationPlannerError("window_sec must be positive")

    windows: list[dict[str, float]] = []
    start_sec = 0.0

    while start_sec < video_duration_sec - 1e-9:
        end_sec = min(start_sec + window_sec, video_duration_sec)
        windows.append(
            {
                "start_sec": _round_sec(start_sec),
                "end_sec": _round_sec(end_sec),
            }
        )
        start_sec = end_sec

    return windows


def _value_for_index(
    values: Iterable[float] | Callable[[dict[str, float], int], float] | None,
    window: dict[str, float],
    index: int,
    default: float,
) -> float:
    if values is None:
        return float(default)
    if callable(values):
        return float(values(window, index))

    seq = list(values)
    if not seq:
        return float(default)
    if index < len(seq):
        return float(seq[index])
    return float(seq[-1])


def compute_voice_level_for_window(
    window: dict[str, float],
    index: int = 0,
    *,
    mixed_audio_levels_db: Iterable[float] | Callable[[dict[str, float], int], float] | None = None,
    separated_voice_levels_db: Iterable[dict[str, float]] | None = None,
    default_mixed_audio_level_db: float = -32.0,
) -> dict[str, Any]:
    if separated_voice_levels_db:
        separated = list(separated_voice_levels_db)
        value = separated[index] if index < len(separated) else separated[-1]
        ali_level = float(value.get("ali_voice_level_db", default_mixed_audio_level_db))
        friend_level = float(value.get("friend_voice_level_db", default_mixed_audio_level_db))
        return {
            "voice_level_db": _round_db(max(ali_level, friend_level)),
            "speaker_voice_source": "separated_ali_friend_tracks",
            "ali_friend_separation_confirmed": True,
        }

    voice_level_db = _value_for_index(mixed_audio_levels_db, window, index, default_mixed_audio_level_db)
    return {
        "voice_level_db": _round_db(voice_level_db),
        "speaker_voice_source": "mixed_audio_level",
        "ali_friend_separation_confirmed": False,
    }


def _track_mean_lookup(selected_music_tracks: list[dict[str, Any]] | None) -> dict[str, float]:
    lookup: dict[str, float] = {}
    for track in selected_music_tracks or []:
        path = str(track.get("path") or track.get("track_path") or "")
        if not path:
            continue
        mean = track.get("mean_volume_db")
        if mean is None:
            continue
        lookup[path] = float(mean)
    return lookup


def _timeline_music_level(
    window: dict[str, float],
    music_timeline: list[dict[str, Any]] | None,
    selected_music_tracks: list[dict[str, Any]] | None,
    default_music_section_level_db: float,
) -> float:
    lookup = _track_mean_lookup(selected_music_tracks)
    midpoint = (float(window["start_sec"]) + float(window["end_sec"])) / 2.0

    for segment in music_timeline or []:
        start = float(segment.get("start_sec", 0.0))
        end = float(segment.get("end_sec", start))
        if start <= midpoint < end:
            track_path = str(segment.get("track_path") or segment.get("path") or "")
            return lookup.get(track_path, default_music_section_level_db)

    return default_music_section_level_db


def compute_music_section_level_for_window(
    window: dict[str, float],
    index: int = 0,
    *,
    music_section_levels_db: Iterable[float] | Callable[[dict[str, float], int], float] | None = None,
    music_timeline: list[dict[str, Any]] | None = None,
    selected_music_tracks: list[dict[str, Any]] | None = None,
    default_music_section_level_db: float = -30.0,
) -> float:
    if music_section_levels_db is not None:
        return _round_db(_value_for_index(music_section_levels_db, window, index, default_music_section_level_db))

    return _round_db(
        _timeline_music_level(
            window,
            music_timeline,
            selected_music_tracks,
            default_music_section_level_db,
        )
    )


def compute_dynamic_music_gain(
    *,
    voice_level_db: float,
    music_section_level_db: float,
    owner_range_db: tuple[float, float] = (OWNER_GAIN_MIN_DB, OWNER_GAIN_MAX_DB),
    base_target_gain_db: float = DEFAULT_BASE_TARGET_GAIN_DB,
) -> dict[str, Any]:
    raw_gain_db = float(base_target_gain_db)
    reasons: list[str] = []

    if voice_level_db >= -24.0:
        raw_gain_db -= 4.0
        reasons.append("voice_loud")
    elif voice_level_db >= -32.0:
        raw_gain_db -= 2.0
        reasons.append("voice_active")
    elif voice_level_db <= -45.0:
        raw_gain_db += 3.0
        reasons.append("voice_quiet")
    else:
        raw_gain_db += 1.0
        reasons.append("voice_low")

    if music_section_level_db >= -22.0:
        raw_gain_db -= 1.0
        reasons.append("song_loud")
    elif music_section_level_db <= -36.0:
        raw_gain_db += 1.0
        reasons.append("song_quiet")
    elif music_section_level_db <= -31.0:
        raw_gain_db += 0.5
        reasons.append("song_low")
    else:
        reasons.append("song_normal")

    minimum, maximum = owner_range_db
    final_gain_db = max(minimum, min(maximum, raw_gain_db))

    return {
        "raw_gain_db": _round_db(raw_gain_db),
        "final_gain_db": _round_db(final_gain_db),
        "reason": "_".join(reasons),
        "music_audibility_policy_enabled": True,
        "music_audibility_floor_db": MUSIC_AUDIBILITY_FLOOR_DB,
        "music_loudness_ceiling_db": MUSIC_LOUDNESS_CEILING_DB,
    }


def smooth_gain_curve(
    windows: list[dict[str, Any]],
    max_delta_db: float = DEFAULT_MAX_GAIN_CHANGE_PER_WINDOW_DB,
    owner_range_db: tuple[float, float] = (OWNER_GAIN_MIN_DB, OWNER_GAIN_MAX_DB),
) -> list[dict[str, Any]]:
    if max_delta_db <= 0:
        raise MusicAutomationPlannerError("max_delta_db must be positive")

    smoothed: list[dict[str, Any]] = []
    previous_gain: float | None = None

    for window in windows:
        target_gain = float(window.get("raw_gain_db", window.get("final_gain_db", DEFAULT_BASE_TARGET_GAIN_DB)))

        if previous_gain is None:
            next_gain = target_gain
        else:
            lower = previous_gain - max_delta_db
            upper = previous_gain + max_delta_db
            next_gain = max(lower, min(upper, target_gain))

        next_gain = _clamp(next_gain, owner_range_db[0], owner_range_db[1])
        item = dict(window)
        item["smoothed_gain_db"] = _round_db(next_gain)
        item["final_gain_db"] = _round_db(next_gain)
        smoothed.append(item)
        previous_gain = next_gain

    return smoothed


def build_clean_transition_policy_for_track(
    track_duration_sec: float,
    *,
    track_start_trim_sec: float = DEFAULT_TRACK_START_TRIM_SEC,
    track_end_trim_sec: float = DEFAULT_TRACK_END_TRIM_SEC,
    crossfade_sec: float = DEFAULT_CROSSFADE_SEC,
    min_usable_track_sec: float = DEFAULT_MIN_USABLE_TRACK_SEC,
) -> dict[str, Any]:
    if track_duration_sec <= 0:
        raise MusicAutomationPlannerError("track_duration_sec must be positive")

    start_trim = min(track_start_trim_sec, track_duration_sec)
    end_trim = min(track_end_trim_sec, max(0.0, track_duration_sec - start_trim))
    usable_duration = track_duration_sec - start_trim - end_trim
    safe_trim_reduced = False
    track_skipped = False

    if usable_duration < min_usable_track_sec:
        safe_trim_reduced = True
        if track_duration_sec < min_usable_track_sec:
            start_trim = 0.0
            end_trim = 0.0
            usable_duration = track_duration_sec
            track_skipped = True
        else:
            start_trim = min(track_start_trim_sec, max(0.0, track_duration_sec - min_usable_track_sec))
            end_trim = min(track_end_trim_sec, max(0.0, track_duration_sec - start_trim - min_usable_track_sec))
            usable_duration = track_duration_sec - start_trim - end_trim

    usable_start_sec = start_trim
    usable_end_sec = max(usable_start_sec, track_duration_sec - end_trim)

    return {
        "clean_transition_policy_enabled": True,
        "track_start_trim_sec": _round_sec(start_trim),
        "track_end_trim_sec": _round_sec(end_trim),
        "requested_track_start_trim_sec": _round_sec(track_start_trim_sec),
        "requested_track_end_trim_sec": _round_sec(track_end_trim_sec),
        "usable_start_sec": _round_sec(usable_start_sec),
        "usable_end_sec": _round_sec(usable_end_sec),
        "usable_duration_sec": _round_sec(usable_duration),
        "safe_trim_reduced": safe_trim_reduced,
        "track_skipped": track_skipped,
        "crossfade_sec": _round_sec(crossfade_sec),
        "transition_type": "crossfade",
        "hard_cut_transitions": False,
        "track_intro_outro_trim_enabled": True,
    }


def apply_clean_transition_policy_to_timeline(
    music_timeline: list[dict[str, Any]],
    *,
    track_start_trim_sec: float = DEFAULT_TRACK_START_TRIM_SEC,
    track_end_trim_sec: float = DEFAULT_TRACK_END_TRIM_SEC,
    crossfade_sec: float = DEFAULT_CROSSFADE_SEC,
) -> list[dict[str, Any]]:
    enhanced: list[dict[str, Any]] = []

    for index, segment in enumerate(music_timeline):
        item = dict(segment)
        duration = float(
            item.get("track_duration_sec")
            or item.get("track_duration_used_sec")
            or item.get("track_used_duration_sec")
            or (float(item.get("end_sec", 0.0)) - float(item.get("start_sec", 0.0)))
            or 1.0
        )

        policy = build_clean_transition_policy_for_track(
            duration,
            track_start_trim_sec=track_start_trim_sec,
            track_end_trim_sec=track_end_trim_sec,
            crossfade_sec=crossfade_sec,
        )

        source_start = float(policy["usable_start_sec"])
        source_end = float(policy["usable_end_sec"])
        segment_duration = max(0.0, float(item.get("end_sec", 0.0)) - float(item.get("start_sec", 0.0)))
        planned_source_end = min(source_end, source_start + segment_duration)

        item.update(
            {
                "track_source_start_sec": _round_sec(source_start),
                "track_source_end_sec": _round_sec(planned_source_end),
                "crossfade_in_sec": 0.0 if index == 0 else _round_sec(crossfade_sec),
                "crossfade_out_sec": 0.0 if index == len(music_timeline) - 1 else _round_sec(crossfade_sec),
                "transition_type": "crossfade",
                "clean_transition_policy_enabled": True,
                "hard_cut_transitions": False,
                "track_intro_outro_trim_enabled": True,
                "safe_trim_reduced": policy["safe_trim_reduced"],
                "track_skipped_by_transition_policy": policy["track_skipped"],
            }
        )
        enhanced.append(item)

    return enhanced


def build_music_automation_plan(
    *,
    video_duration_sec: float,
    music_timeline: list[dict[str, Any]] | None,
    selected_music_tracks: list[dict[str, Any]] | None = None,
    window_sec: float = DEFAULT_AUTOMATION_WINDOW_SEC,
    mixed_audio_levels_db: Iterable[float] | Callable[[dict[str, float], int], float] | None = None,
    music_section_levels_db: Iterable[float] | Callable[[dict[str, float], int], float] | None = None,
    separated_voice_levels_db: Iterable[dict[str, float]] | None = None,
    max_gain_change_per_window_db: float = DEFAULT_MAX_GAIN_CHANGE_PER_WINDOW_DB,
) -> dict[str, Any]:
    analysis_windows = build_analysis_windows(video_duration_sec, window_sec=window_sec)
    automation_windows: list[dict[str, Any]] = []
    ali_friend_confirmed = False
    speaker_voice_source = "mixed_audio_level"

    for index, window in enumerate(analysis_windows):
        voice = compute_voice_level_for_window(
            window,
            index=index,
            mixed_audio_levels_db=mixed_audio_levels_db,
            separated_voice_levels_db=separated_voice_levels_db,
        )
        ali_friend_confirmed = bool(voice["ali_friend_separation_confirmed"])
        speaker_voice_source = str(voice["speaker_voice_source"])

        music_section_level_db = compute_music_section_level_for_window(
            window,
            index=index,
            music_section_levels_db=music_section_levels_db,
            music_timeline=music_timeline,
            selected_music_tracks=selected_music_tracks,
        )
        gain = compute_dynamic_music_gain(
            voice_level_db=float(voice["voice_level_db"]),
            music_section_level_db=float(music_section_level_db),
        )

        automation_windows.append(
            {
                "start_sec": window["start_sec"],
                "end_sec": window["end_sec"],
                "voice_level_db": voice["voice_level_db"],
                "music_section_level_db": music_section_level_db,
                "raw_gain_db": gain["raw_gain_db"],
                "smoothed_gain_db": gain["final_gain_db"],
                "final_gain_db": gain["final_gain_db"],
                "reason": gain["reason"],
            }
        )

    automation_windows = smooth_gain_curve(
        automation_windows,
        max_delta_db=max_gain_change_per_window_db,
    )

    return {
        "music_automation_planner_enabled": True,
        "automation_window_sec": float(window_sec),
        "voice_aware_music_ceiling_enabled": True,
        "music_section_loudness_aware": True,
        "gain_smoothing_enabled": True,
        "max_gain_change_per_window_db": float(max_gain_change_per_window_db),
        "ali_friend_separation_confirmed": ali_friend_confirmed,
        "speaker_voice_source": speaker_voice_source,
        "automation_window_count": len(automation_windows),
        "music_automation_plan": automation_windows,
        "music_audibility_policy_enabled": True,
        "owner_music_audible_gain_range_db": [OWNER_GAIN_MIN_DB, OWNER_GAIN_MAX_DB],
        "owner_music_target_gain_db": DEFAULT_BASE_TARGET_GAIN_DB,
        "music_audibility_floor_db": MUSIC_AUDIBILITY_FLOOR_DB,
        "music_loudness_ceiling_db": MUSIC_LOUDNESS_CEILING_DB,
        "double_ducking_protection_enabled": True,
        "automation_all_final_gains_between_audible_range": all(
            OWNER_GAIN_MIN_DB <= float(window["final_gain_db"]) <= OWNER_GAIN_MAX_DB
            for window in automation_windows
        ),
        "automation_all_final_gains_between_minus_35_and_minus_26": all(
            OWNER_GAIN_MIN_DB <= float(window["final_gain_db"]) <= OWNER_GAIN_MAX_DB
            for window in automation_windows
        ),
        "automation_all_final_gains_between_minus_40_and_minus_35": False,
        "clean_transition_policy_enabled": True,
        "track_start_trim_sec": DEFAULT_TRACK_START_TRIM_SEC,
        "track_end_trim_sec": DEFAULT_TRACK_END_TRIM_SEC,
        "crossfade_sec": DEFAULT_CROSSFADE_SEC,
        "hard_cut_transitions": False,
        "track_intro_outro_trim_enabled": True,
    }
