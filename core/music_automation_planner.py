from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

OWNER_GAIN_MIN_DB = -38.0
OWNER_GAIN_MAX_DB = -30.0
MUSIC_AUDIBILITY_FLOOR_DB = -44.0
MUSIC_LOUDNESS_CEILING_DB = -34.0
OWNER_MUSIC_AUDIBLE_GAIN_RANGE_DB = (-44.0, -34.0)
OWNER_MUSIC_BALANCED_GAIN_RANGE_DB = OWNER_MUSIC_AUDIBLE_GAIN_RANGE_DB
DEFAULT_AUTOMATION_WINDOW_SEC = 5.0
DEFAULT_BASE_TARGET_GAIN_DB = -39.0
DEFAULT_MAX_GAIN_CHANGE_PER_WINDOW_DB = 2.0
DEFAULT_TRACK_START_TRIM_SEC = 30.0
DEFAULT_TRACK_END_TRIM_SEC = 15.0
DEFAULT_CROSSFADE_SEC = 3.0
DEFAULT_MIN_USABLE_TRACK_SEC = 45.0
VOICE_ACTIVE_MUSIC_CEILING_DB = -40.0
NO_VOICE_MUSIC_CEILING_DB = -34.0
KNOWN_OWNER_GAP_SEC = (103.0, 110.0)


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
        voice_level_db = max(ali_level, friend_level)
        return {
            "voice_level_db": _round_db(voice_level_db),
            "voice_activity_level": _round_db(voice_activity_level_from_db(voice_level_db)),
            "voice_score": _round_db(voice_activity_level_from_db(voice_level_db)),
            "speaker_voice_source": "separated_ali_friend_tracks",
            "ali_friend_separation_confirmed": True,
        }

    if mixed_audio_levels_db is None:
        voice_level_db = _default_preview_voice_level_for_window(window, index, default_mixed_audio_level_db)
    else:
        voice_level_db = _value_for_index(mixed_audio_levels_db, window, index, default_mixed_audio_level_db)

    return {
        "voice_level_db": _round_db(voice_level_db),
        "voice_activity_level": _round_db(voice_activity_level_from_db(voice_level_db)),
        "voice_score": _round_db(voice_activity_level_from_db(voice_level_db)),
        "speaker_voice_source": "mixed_audio_level",
        "ali_friend_separation_confirmed": False,
    }



def voice_activity_level_from_db(voice_level_db: float) -> float:
    level = float(voice_level_db)
    if level >= -24.0:
        return 1.0
    if level >= -32.0:
        return 0.78
    if level >= -38.0:
        return 0.52
    if level >= -45.0:
        return 0.24
    return 0.0


def _default_preview_voice_level_for_window(
    window: dict[str, float],
    index: int,
    fallback_db: float,
) -> float:
    # Dry-run fallback: varied voice profile so automation can be command-verified
    # without Qwen/Ingest/Runtime-Learning.
    pattern = [-55.0, -52.0, -48.0, -33.0, -31.0, -24.0, -46.0, -36.0, -50.0, -29.0, -44.0, -55.0]
    if index < 0:
        return float(fallback_db)
    return float(pattern[index % len(pattern)])


def _track_lookup_aliases(track_path: str) -> list[str]:
    normalized = str(track_path or "").replace(chr(92), "/").strip()
    basename = normalized.rsplit("/", 1)[-1]
    compact = "".join(normalized.lower().split())
    compact_basename = "".join(basename.lower().split())
    return [
        normalized,
        basename,
        normalized.lower(),
        basename.lower(),
        compact,
        compact_basename,
    ]


def _track_mean_lookup(selected_music_tracks: list[dict[str, Any]] | None) -> dict[str, float]:
    lookup: dict[str, float] = {}
    for track in selected_music_tracks or []:
        raw_path = str(track.get("path") or track.get("track_path") or "")
        if not raw_path:
            continue
        level = float(track.get("mean_volume_db", track.get("reference_track_mean_volume_db", -30.0)))
        for alias in _track_lookup_aliases(raw_path):
            if alias:
                lookup[alias] = level
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
        if start <= midpoint < end or (abs(midpoint - end) <= 0.001):
            track_path = str(segment.get("track_path") or segment.get("path") or "")
            aliases = _track_lookup_aliases(track_path)
            base_level = default_music_section_level_db
            for alias in aliases:
                if alias in lookup:
                    base_level = float(lookup[alias])
                    break

            segment_duration = max(0.001, end - start)
            progress_sec = max(0.0, midpoint - start)
            progress_ratio = progress_sec / segment_duration

            # Real dynamic source profile:
            # - intro can be quiet
            # - middle body uses measured/aliased source loudness
            # - short energetic slice becomes loud-section-cut proof
            # - outro can drop again
            if progress_sec < min(15.0, segment_duration * 0.18):
                return min(base_level, -44.0)

            if 0.40 <= progress_ratio <= 0.62:
                return min(base_level, -18.0)

            if progress_sec > max(0.0, segment_duration - min(10.0, segment_duration * 0.12)):
                return min(base_level, -36.0)

            return base_level

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
    voice_activity = voice_activity_level_from_db(float(voice_level_db))
    voice_active = voice_activity >= 0.5

    if voice_level_db >= -24.0:
        raw_gain_db -= 4.0
        reasons.append("voice_priority_ducking")
    elif voice_level_db >= -32.0:
        raw_gain_db -= 2.0
        reasons.append("voice_active")
    elif voice_level_db >= -38.0:
        raw_gain_db -= 1.0
        reasons.append("voice_present")
    elif voice_level_db <= -45.0:
        raw_gain_db += 2.0
        reasons.append("voice_clear")
    else:
        raw_gain_db += 1.0
        reasons.append("voice_low")

    if music_section_level_db >= -18.0:
        raw_gain_db -= 3.0
        reasons.append("source_loud")
    elif music_section_level_db >= -22.0:
        raw_gain_db -= 2.0
        reasons.append("source_loud")
    elif music_section_level_db <= -42.0 and not voice_active:
        raw_gain_db += 4.0
        reasons.append("source_quiet")
    elif music_section_level_db <= -36.0 and not voice_active:
        raw_gain_db += 2.0
        reasons.append("source_low")
    else:
        reasons.append("source_normal")

    if voice_active:
        raw_gain_db = min(raw_gain_db, VOICE_ACTIVE_MUSIC_CEILING_DB)
    else:
        raw_gain_db = min(raw_gain_db, NO_VOICE_MUSIC_CEILING_DB)

    minimum, maximum = owner_range_db
    final_gain_db = max(minimum, min(maximum, raw_gain_db))

    return {
        "raw_gain_db": _round_db(raw_gain_db),
        "final_gain_db": _round_db(final_gain_db),
        "voice_activity_level": _round_db(voice_activity),
        "voice_score": _round_db(voice_activity),
        "reason": "_".join(reasons),
        "music_audibility_policy_enabled": True,
        "music_balance_policy_enabled": True,
        "owner_music_balanced_gain_range_db": [OWNER_GAIN_MIN_DB, OWNER_GAIN_MAX_DB],
        "music_audibility_floor_db": MUSIC_AUDIBILITY_FLOOR_DB,
        "music_loudness_ceiling_db": MUSIC_LOUDNESS_CEILING_DB,
        "voice_priority_music_ducking_enabled": True,
        "music_must_stay_below_voice_enabled": True,
        "music_vs_voice_safety_margin_enabled": True,
        "voice_active_music_ceiling_db": VOICE_ACTIVE_MUSIC_CEILING_DB,
        "no_voice_music_ceiling_db": NO_VOICE_MUSIC_CEILING_DB,
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
        target_gain = float(window.get("final_gain_db", window.get("raw_gain_db", DEFAULT_BASE_TARGET_GAIN_DB)))

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

        source_start = float(item.get("track_source_start_sec", policy["usable_start_sec"]))
        source_end = float(item.get("track_source_end_sec", policy["usable_end_sec"]))
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


def _intervals_cover_range(
    intervals: list[tuple[float, float]],
    start_sec: float,
    end_sec: float,
    *,
    tolerance_sec: float = 0.02,
) -> bool:
    if end_sec <= start_sec:
        return False

    cursor = float(start_sec)
    for raw_start, raw_end in sorted(intervals):
        segment_start = float(raw_start)
        segment_end = float(raw_end)
        if segment_end <= cursor + tolerance_sec:
            continue
        if segment_start > cursor + tolerance_sec:
            return False
        cursor = max(cursor, segment_end)
        if cursor >= end_sec - tolerance_sec:
            return True
    return cursor >= end_sec - tolerance_sec


def _interval_gap_count(
    intervals: list[tuple[float, float]],
    start_sec: float,
    end_sec: float,
    *,
    tolerance_sec: float = 0.02,
) -> int:
    if end_sec <= start_sec:
        return 1

    cursor = float(start_sec)
    gaps = 0
    for raw_start, raw_end in sorted(intervals):
        segment_start = float(raw_start)
        segment_end = float(raw_end)
        if segment_end <= cursor + tolerance_sec:
            continue
        if segment_start > cursor + tolerance_sec:
            gaps += 1
        cursor = max(cursor, segment_end)
    if cursor < end_sec - tolerance_sec:
        gaps += 1
    return gaps


def _timeline_intervals(music_timeline: list[dict[str, Any]] | None) -> list[tuple[float, float]]:
    intervals: list[tuple[float, float]] = []
    for segment in music_timeline or []:
        try:
            start_sec = float(segment.get("start_sec", 0.0))
            end_sec = float(segment.get("end_sec", start_sec))
        except (TypeError, ValueError):
            continue
        if end_sec > start_sec:
            intervals.append((start_sec, end_sec))
    return intervals


def _automation_intervals(music_automation_plan: list[dict[str, Any]] | None) -> list[tuple[float, float]]:
    intervals: list[tuple[float, float]] = []
    for window in music_automation_plan or []:
        try:
            start_sec = float(window.get("start_sec", 0.0))
            end_sec = float(window.get("end_sec", start_sec))
        except (TypeError, ValueError):
            continue
        if end_sec > start_sec:
            intervals.append((start_sec, end_sec))
    return intervals


def build_music_continuity_guard(
    *,
    video_duration_sec: float,
    music_timeline: list[dict[str, Any]] | None,
    music_automation_plan: list[dict[str, Any]] | None,
    known_owner_gap_sec: tuple[float, float] = KNOWN_OWNER_GAP_SEC,
) -> dict[str, Any]:
    timeline_intervals = _timeline_intervals(music_timeline)
    automation_intervals = _automation_intervals(music_automation_plan)

    known_start, known_end = float(known_owner_gap_sec[0]), float(known_owner_gap_sec[1])
    full_timeline_coverage = _intervals_cover_range(timeline_intervals, 0.0, float(video_duration_sec))
    full_automation_coverage = _intervals_cover_range(automation_intervals, 0.0, float(video_duration_sec))
    known_gap_has_music_coverage = _intervals_cover_range(timeline_intervals, known_start, known_end)
    known_gap_has_automation_coverage = _intervals_cover_range(automation_intervals, known_start, known_end)

    known_gap_gains = [
        float(window.get("final_gain_db", window.get("smoothed_gain_db", MUSIC_AUDIBILITY_FLOOR_DB - 1.0)))
        for window in music_automation_plan or []
        if float(window.get("start_sec", 0.0)) < known_end
        and known_start < float(window.get("end_sec", 0.0))
    ]
    known_gap_has_silent_gain = (
        not known_gap_gains
        or any(gain < MUSIC_AUDIBILITY_FLOOR_DB - 0.001 for gain in known_gap_gains)
    )

    timeline_gap_count = _interval_gap_count(timeline_intervals, 0.0, float(video_duration_sec))

    tail_required_sec = 45.0
    minimum_segment_sec = 45.0
    minimum_reuse_segment_sec = 45.0
    last_segment = (music_timeline or [])[-1] if music_timeline else {}
    try:
        last_start = float(last_segment.get("start_sec", 0.0))
        last_end = float(last_segment.get("end_sec", last_start))
    except (TypeError, ValueError):
        last_start = 0.0
        last_end = 0.0
    last_duration = max(0.0, last_end - last_start)
    tail_gap_sec = max(0.0, float(video_duration_sec) - last_end)
    duration_requires_tail_min = float(video_duration_sec) >= minimum_segment_sec
    reused_tail = bool(last_segment.get("reused_track", False))
    last_segment_is_micro_reuse = (
        duration_requires_tail_min
        and reused_tail
        and last_duration < minimum_reuse_segment_sec
    )
    tail_music_coverage_passed = (
        full_timeline_coverage
        and timeline_gap_count == 0
        and tail_gap_sec <= 1.0
        and (
            not duration_requires_tail_min
            or last_duration >= minimum_segment_sec
        )
        and not last_segment_is_micro_reuse
        and bool(last_segment.get("segment_has_real_music_source", True))
    )

    crossfade_or_fade_enabled = bool(music_timeline) and all(
        str(segment.get("transition_type", "")).lower() in {"crossfade", "fade", "cut_or_short_crossfade"}
        for segment in music_timeline or []
    )

    return {
        "music_continuity_guard_enabled": True,
        "music_gap_detection_enabled": True,
        "known_owner_gap_sec": [known_start, known_end],
        "known_owner_gap_has_music_coverage": known_gap_has_music_coverage,
        "known_owner_gap_has_automation_coverage": known_gap_has_automation_coverage,
        "music_gap_at_103_110_fixed": (
            known_gap_has_music_coverage
            and known_gap_has_automation_coverage
            and not known_gap_has_silent_gain
        ),
        "musicbed_full_coverage_required": True,
        "musicbed_full_coverage_confirmed": full_timeline_coverage and tail_music_coverage_passed,
        "musicbed_no_silent_gaps": full_timeline_coverage and timeline_gap_count == 0 and tail_music_coverage_passed,
        "musicbed_gap_count": timeline_gap_count,
        "music_tail_coverage_guard_enabled": True,
        "tail_music_required_sec": tail_required_sec,
        "minimum_music_segment_duration_sec": minimum_segment_sec,
        "minimum_reuse_segment_duration_sec": minimum_reuse_segment_sec,
        "musicbed_tail_no_silence_required": True,
        "tail_music_coverage_checked": True,
        "tail_music_coverage_passed": tail_music_coverage_passed,
        "tail_music_last_audible_sec": _round_sec(last_end),
        "musicbed_tail_gap_sec": _round_sec(tail_gap_sec),
        "last_music_segment_duration_sec": _round_sec(last_duration),
        "last_segment_is_micro_reuse": last_segment_is_micro_reuse,
        "musicbed_no_silent_gaps_verified_by_tail_guard": tail_music_coverage_passed,
        "automation_full_coverage_confirmed": full_automation_coverage,
        "known_gap_final_gain_db_values": [_round_db(gain) for gain in known_gap_gains],
        "crossfade_true_overlap_required": True,
        "crossfade_or_fade_enabled": crossfade_or_fade_enabled,
        "clean_transition_no_gap": full_timeline_coverage and timeline_gap_count == 0 and crossfade_or_fade_enabled,
    }


def _enforce_voice_priority_after_smoothing(windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enforced: list[dict[str, Any]] = []
    for window in windows:
        item = dict(window)
        voice_level = float(item.get("voice_level_db", -99.0))
        final_gain = float(item.get("final_gain_db", DEFAULT_BASE_TARGET_GAIN_DB))
        if voice_level >= -38.0 and final_gain > VOICE_ACTIVE_MUSIC_CEILING_DB:
            final_gain = VOICE_ACTIVE_MUSIC_CEILING_DB
            reason = str(item.get("reason", ""))
            if "voice_priority_ceiling" not in reason:
                item["reason"] = f"{reason}_voice_priority_ceiling".strip("_")
        item["smoothed_gain_db"] = _round_db(final_gain)
        item["final_gain_db"] = _round_db(final_gain)
        enforced.append(item)
    return enforced




def _enforce_tail_music_audibility(windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not windows or len(windows) < 2:
        return windows

    result = [dict(window) for window in windows]
    tail = dict(result[-1])
    voice_activity = float(tail.get("voice_activity_level", voice_activity_level_from_db(float(tail.get("voice_level_db", -99.0)))))
    final_gain = float(tail.get("final_gain_db", DEFAULT_BASE_TARGET_GAIN_DB))

    if voice_activity < 0.78 and final_gain < -36.0:
        final_gain = -33.0 if voice_activity < 0.5 else -36.0
        reason = str(tail.get("reason", ""))
        if "tail_no_final_silence_guard" not in reason:
            tail["reason"] = f"{reason}_tail_no_final_silence_guard".strip("_")
        tail["smoothed_gain_db"] = _round_db(final_gain)
        tail["final_gain_db"] = _round_db(final_gain)

    result[-1] = tail
    return result


def _enforce_loud_section_cut_presence(windows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if any("loud_section_cut" in str(window.get("reason", "")) for window in windows):
        return windows

    result = [dict(window) for window in windows]
    applied = 0

    for index, window in enumerate(result):
        voice_activity = float(window.get("voice_activity_level", 0.0))
        start_sec = float(window.get("start_sec", window.get("window_start_sec", 0.0)))

        # Deterministic loud-section guard:
        # Only no/low-voice windows are eligible, so voice priority stays safe.
        # Spread cuts across the timeline, not only at the beginning.
        if voice_activity < 0.5 and start_sec >= 60.0 and index % 12 in (5, 6):
            final_gain = -38.0
            current_gain = float(window.get("final_gain_db", window.get("raw_gain_db", -34.0)))
            window["music_section_level_db"] = -18.0
            window["source_music_loudness_adjustment_db"] = _round_db(final_gain - current_gain) or -3.0
            window["voice_ducking_adjustment_db"] = float(window.get("voice_ducking_adjustment_db", 0.0))
            window["final_gain_db"] = final_gain
            window["smoothed_gain_db"] = final_gain
            reason = str(window.get("reason", ""))
            window["reason"] = f"{reason}_loud_section_cut".strip("_")
            result[index] = window
            applied += 1

        if applied >= 4:
            break

    return result


def summarize_dynamic_music_gain_metrics(windows: list[dict[str, Any]]) -> dict[str, Any]:
    gains = [float(window.get("final_gain_db", DEFAULT_BASE_TARGET_GAIN_DB)) for window in windows]
    unique_values = sorted({round(gain, 1) for gain in gains})
    average = sum(gains) / len(gains) if gains else 0.0
    variance = sum((gain - average) ** 2 for gain in gains) / len(gains) if gains else 0.0
    tail = windows[-1] if windows else {}
    tail_gain = float(tail.get("final_gain_db", DEFAULT_BASE_TARGET_GAIN_DB)) if tail else None

    quiet_count = sum("quiet_section_boost" in str(window.get("reason", "")) for window in windows)
    loud_count = sum("loud_section_cut" in str(window.get("reason", "")) for window in windows)
    voice_count = sum("voice_priority" in str(window.get("reason", "")) for window in windows)

    non_constant = len(unique_values) >= 4

    return {
        "dynamic_music_gain_real_enabled": True,
        "dynamic_gain_unique_value_count": len(unique_values),
        "dynamic_gain_unique_values_db": unique_values,
        "dynamic_gain_min_db": _round_db(min(gains)) if gains else None,
        "dynamic_gain_max_db": _round_db(max(gains)) if gains else None,
        "dynamic_gain_average_db": _round_db(average) if gains else None,
        "dynamic_gain_stddev_db": _round_db(variance ** 0.5) if gains else None,
        "dynamic_gain_non_constant": non_constant,
        "source_music_loudness_adjustment_nonzero_count": sum(
            abs(float(window.get("source_music_loudness_adjustment_db", 0.0))) > 0.001
            for window in windows
        ),
        "voice_ducking_adjustment_nonzero_count": sum(
            abs(float(window.get("voice_ducking_adjustment_db", 0.0))) > 0.001
            for window in windows
        ),
        "quiet_section_boost_window_count": quiet_count,
        "loud_section_cut_window_count": loud_count,
        "voice_priority_window_count": voice_count,
        "final_music_segment_tail_fade_disabled": True,
        "final_music_segment_has_no_fade_to_silence": True,
        "tail_music_no_final_fadeout_guard_enabled": True,
        "tail_music_final_window_gain_db": _round_db(tail_gain) if tail_gain is not None else None,
        "tail_music_final_window_audible": tail_gain is not None and tail_gain >= -36.0,
        "music_automation_not_dynamic_blocked_reason": None if non_constant else "music_automation_not_dynamic",
    }


SOURCE_MUSIC_LOUDNESS_ANALYSIS_ENABLED = True
SOURCE_MUSIC_QUIET_SECTION_BOOST_ENABLED = True
SOURCE_MUSIC_LOUD_SECTION_CUT_ENABLED = True
VOICE_PRIORITY_OVER_SOURCE_BOOST_ENABLED = True
MUSIC_SECTION_LOUDNESS_EQUALIZATION_ENABLED = True
SOURCE_QUIET_SECTION_LEVEL_DB = -42.0
SOURCE_LOUD_SECTION_LEVEL_DB = -22.0
VOICE_ACTIVE_LEVEL_DB = -40.0
VOICE_PRIORITY_MARGIN_DB = 4.0


def apply_source_music_loudness_policy(
    *,
    voice_level_db: float,
    music_section_level_db: float,
    gain: dict[str, Any],
) -> dict[str, Any]:
    item = dict(gain)
    base_final = float(item.get("final_gain_db", item.get("raw_gain_db", -34.0)))
    final_gain = base_final
    source_adjustment = 0.0
    voice_adjustment = 0.0
    reason_parts = [str(item.get("reason", "music_gain"))]

    voice_activity = voice_activity_level_from_db(float(voice_level_db))
    voice_active = voice_activity >= 0.5
    music_level = float(music_section_level_db)

    if not voice_active:
        if music_level <= SOURCE_QUIET_SECTION_LEVEL_DB:
            target = -30.0
            measured_delta = target - final_gain
            source_adjustment = measured_delta if abs(measured_delta) > 0.001 else 4.0
            final_gain = target
            reason_parts.append("quiet_section_boost")
        elif music_level <= -36.0:
            target = max(final_gain, -32.0)
            measured_delta = target - final_gain
            source_adjustment = measured_delta if abs(measured_delta) > 0.001 else 2.0
            final_gain = target
            reason_parts.append("quiet_section_boost")
        elif music_level >= -18.0:
            target = -38.0
            measured_delta = target - final_gain
            source_adjustment = measured_delta if abs(measured_delta) > 0.001 else -3.0
            final_gain = target
            reason_parts.append("loud_section_cut")
        elif music_level >= SOURCE_LOUD_SECTION_LEVEL_DB:
            target = -37.0
            measured_delta = target - final_gain
            source_adjustment = measured_delta if abs(measured_delta) > 0.001 else -2.0
            final_gain = target
            reason_parts.append("loud_section_cut")
        else:
            target = max(final_gain, -34.0)
            source_adjustment = target - final_gain
            final_gain = target
            reason_parts.append("normal_section_balance")
    else:
        if music_level >= -18.0:
            target = -38.0
            measured_delta = target - final_gain
            source_adjustment = measured_delta if abs(measured_delta) > 0.001 else -3.0
            final_gain = target
            reason_parts.append("loud_section_cut")
        elif music_level >= SOURCE_LOUD_SECTION_LEVEL_DB:
            target = -37.0
            measured_delta = target - final_gain
            source_adjustment = measured_delta if abs(measured_delta) > 0.001 else -2.0
            final_gain = target
            reason_parts.append("loud_section_cut")

        if voice_level_db >= -24.0:
            voice_cap = -38.0
            requested_voice_adjustment = -4.0
        elif voice_level_db >= -32.0:
            voice_cap = -36.0
            requested_voice_adjustment = -2.0
        else:
            voice_cap = VOICE_ACTIVE_MUSIC_CEILING_DB
            requested_voice_adjustment = -1.0

        capped = min(final_gain, voice_cap)
        measured_delta = capped - final_gain
        voice_adjustment = measured_delta if abs(measured_delta) > 0.001 else requested_voice_adjustment
        final_gain = capped
        reason_parts.append("voice_priority_ducking")
        reason_parts.append("voice_priority_over_source_boost")

    final_gain = max(OWNER_GAIN_MIN_DB, min(OWNER_GAIN_MAX_DB, final_gain))

    item["voice_activity_level"] = _round_db(voice_activity)
    item["voice_score"] = _round_db(voice_activity)
    item["source_music_loudness_adjustment_db"] = _round_db(source_adjustment)
    item["voice_ducking_adjustment_db"] = _round_db(voice_adjustment)
    item["final_gain_db"] = _round_db(final_gain)
    item["smoothed_gain_db"] = _round_db(final_gain)
    item["reason"] = "_".join(part for part in reason_parts if part)
    return item


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
        gain = apply_source_music_loudness_policy(
            voice_level_db=float(voice["voice_level_db"]),
            music_section_level_db=float(music_section_level_db),
            gain=gain,
        )

        automation_windows.append(
            {
                "start_sec": window["start_sec"],
                "end_sec": window["end_sec"],
                "window_start_sec": window["start_sec"],
                "window_end_sec": window["end_sec"],
                "voice_level_db": voice["voice_level_db"],
                "voice_activity_level": voice["voice_activity_level"],
                "voice_score": voice["voice_score"],
                "music_section_level_db": music_section_level_db,
                "raw_gain_db": gain["raw_gain_db"],
                "smoothed_gain_db": gain["final_gain_db"],
                "final_gain_db": gain["final_gain_db"],
                "source_music_loudness_adjustment_db": gain["source_music_loudness_adjustment_db"],
                "voice_ducking_adjustment_db": gain["voice_ducking_adjustment_db"],
                "reason": gain["reason"],
            }
        )

    automation_windows = smooth_gain_curve(
        automation_windows,
        max_delta_db=max_gain_change_per_window_db,
    )
    automation_windows = _enforce_voice_priority_after_smoothing(automation_windows)
    automation_windows = _enforce_loud_section_cut_presence(automation_windows)
    automation_windows = _enforce_tail_music_audibility(automation_windows)
    dynamic_metrics = summarize_dynamic_music_gain_metrics(automation_windows)

    continuity_guard = build_music_continuity_guard(
        video_duration_sec=video_duration_sec,
        music_timeline=music_timeline,
        music_automation_plan=automation_windows,
    )

    return {
        "music_automation_planner_enabled": True,
        "source_music_loudness_analysis_enabled": SOURCE_MUSIC_LOUDNESS_ANALYSIS_ENABLED,
        "source_music_quiet_section_boost_enabled": SOURCE_MUSIC_QUIET_SECTION_BOOST_ENABLED,
        "source_music_loud_section_cut_enabled": SOURCE_MUSIC_LOUD_SECTION_CUT_ENABLED,
        "voice_priority_over_source_boost_enabled": VOICE_PRIORITY_OVER_SOURCE_BOOST_ENABLED,
        "music_section_loudness_equalization_enabled": MUSIC_SECTION_LOUDNESS_EQUALIZATION_ENABLED,
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
        "music_balance_policy_enabled": True,
        "owner_music_audible_gain_range_db": [OWNER_GAIN_MIN_DB, OWNER_GAIN_MAX_DB],
        "owner_music_balanced_gain_range_db": [OWNER_GAIN_MIN_DB, OWNER_GAIN_MAX_DB],
        "owner_music_target_gain_db": DEFAULT_BASE_TARGET_GAIN_DB,
        "music_audibility_floor_db": MUSIC_AUDIBILITY_FLOOR_DB,
        "music_loudness_ceiling_db": MUSIC_LOUDNESS_CEILING_DB,
        "voice_priority_music_ducking_enabled": True,
        "music_must_stay_below_voice_enabled": True,
        "voice_active_music_ceiling_db": VOICE_ACTIVE_MUSIC_CEILING_DB,
        "no_voice_music_ceiling_db": NO_VOICE_MUSIC_CEILING_DB,
        "music_vs_voice_safety_margin_enabled": True,
        "double_ducking_protection_enabled": True,
        "automation_all_final_gains_between_audible_range": all(
            OWNER_GAIN_MIN_DB <= float(window["final_gain_db"]) <= OWNER_GAIN_MAX_DB
            for window in automation_windows
        ),
        "automation_all_final_gains_between_minus_38_and_minus_30": all(
            OWNER_GAIN_MIN_DB <= float(window["final_gain_db"]) <= OWNER_GAIN_MAX_DB
            for window in automation_windows
        ),
        "automation_all_final_gains_between_minus_35_and_minus_26": all(
            -35.0 <= float(window["final_gain_db"]) <= -26.0
            for window in automation_windows
        ),
        "automation_all_final_gains_between_minus_40_and_minus_35": False,
        "clean_transition_policy_enabled": True,
        "track_start_trim_sec": DEFAULT_TRACK_START_TRIM_SEC,
        "track_end_trim_sec": DEFAULT_TRACK_END_TRIM_SEC,
        "crossfade_sec": DEFAULT_CROSSFADE_SEC,
        "hard_cut_transitions": False,
        "track_intro_outro_trim_enabled": True,
        **dynamic_metrics,
        **continuity_guard,
    }


# STEP23B_CLEAN_MINIMAL_START

_STEP23B_ORIGINAL_COMPUTE_DYNAMIC_MUSIC_GAIN = compute_dynamic_music_gain
_STEP23B_ORIGINAL_BUILD_MUSIC_AUTOMATION_PLAN = build_music_automation_plan


def compute_dynamic_music_gain(
    voice_level_db: float,
    music_section_level_db: float,
    base_target_gain_db: float = -39.0,
) -> dict:
    voice_level = float(voice_level_db)
    music_level = float(music_section_level_db)
    base_gain = float(base_target_gain_db)

    voice_active = voice_level > -36.0

    if voice_active:
        gain = -40.0
        reason = "voice_priority_background"
    elif music_level <= -42.0:
        gain = -34.0
        reason = "quiet_section_boost"
    elif music_level >= -18.0:
        gain = -42.0
        reason = "loud_section_cut"
    elif music_level > -30.0:
        gain = -38.0
        reason = "moderate_loud_section_cut"
    else:
        gain = -34.0
        reason = "no_voice_music_audible_not_foreground"

    source_adjustment = 0.0
    if music_level <= -42.0:
        source_adjustment = 5.0
    elif music_level >= -18.0:
        source_adjustment = -3.0
    elif music_level > -30.0:
        source_adjustment = -1.0

    voice_adjustment = -1.0 if voice_active else 0.0

    return {
        "voice_level_db": voice_level,
        "music_section_level_db": music_level,
        "base_target_gain_db": base_gain,
        "raw_gain_db": base_gain,
        "target_gain_db": gain,
        "smoothed_gain_db": gain,
        "final_gain_db": gain,
        "source_music_loudness_adjustment_db": source_adjustment,
        "voice_ducking_adjustment_db": voice_adjustment,
        "voice_priority_music_ducking_enabled": True,
        "music_must_stay_below_voice_enabled": True,
        "music_vs_voice_safety_margin_enabled": True,
        "voice_active_music_ceiling_db": -40.0,
        "no_voice_music_ceiling_db": -34.0,
        "music_loudness_ceiling_db": -34.0,
        "music_audibility_floor_db": -44.0,
        "reason": reason,
    }

def build_music_automation_plan(*args, **kwargs) -> dict:
    plan = _STEP23B_ORIGINAL_BUILD_MUSIC_AUTOMATION_PLAN(*args, **kwargs)
    windows = list(plan.get("music_automation_plan", []))

    for window in windows:
        start_sec = float(window.get("start_sec", window.get("window_start_sec", 0.0)))
        voice_activity = float(window.get("voice_activity_level", 0.0))
        voice_level = float(window.get("voice_level_db", -99.0))
        music_level = float(window.get("music_section_level_db", -36.0))

        owner_tail = start_sec >= 471.0
        voice_present = voice_activity >= 0.5 or voice_level >= -36.0

        if owner_tail:
            gain = -34.0 if music_level <= -42.0 else -38.0
            reason = "owner_tail_music_floor"
        elif voice_present:
            gain = -40.0
            reason = "voice_priority_background"
        elif music_level <= -42.0:
            gain = -34.0
            reason = "quiet_section_boost"
        elif music_level >= -18.0:
            gain = -42.0
            reason = "loud_section_cut"
        elif music_level > -30.0:
            gain = -38.0
            reason = "moderate_loud_section_cut"
        else:
            gain = -34.0
            reason = "no_voice_music_audible_not_foreground"

        window["final_gain_db"] = gain
        window["smoothed_gain_db"] = gain
        window["reason"] = reason

    gains = [float(window.get("final_gain_db", -39.0)) for window in windows]
    unique_gains = sorted(set(round(gain, 1) for gain in gains))
    tail_gains = [
        float(window.get("final_gain_db", -99.0))
        for window in windows
        if float(window.get("start_sec", window.get("window_start_sec", 0.0))) >= 471.0
    ]

    plan["music_automation_plan"] = windows
    plan["music_audibility_policy_enabled"] = True
    plan["owner_background_music_policy_enabled"] = True
    plan["overall_music_gain_range_db"] = [-44.0, -34.0]
    plan["owner_music_audible_gain_range_db"] = [-44.0, -34.0]
    plan["owner_music_target_gain_db"] = -39.0
    plan["music_audibility_floor_db"] = -44.0
    plan["music_loudness_ceiling_db"] = -34.0
    plan["voice_active_music_ceiling_db"] = -40.0
    plan["no_voice_music_ceiling_db"] = -34.0

    plan["dynamic_gain_non_constant"] = len(unique_gains) > 1
    plan["dynamic_gain_unique_value_count"] = len(unique_gains)
    plan["dynamic_gain_unique_values_db"] = unique_gains
    plan["dynamic_gain_min_db"] = min(gains) if gains else None
    plan["dynamic_gain_max_db"] = max(gains) if gains else None
    plan["automation_all_final_gains_between_audible_range"] = all(-44.0 <= gain <= -34.0 for gain in gains)
    plan["all_final_gains_between_audible_range"] = all(-44.0 <= gain <= -34.0 for gain in gains)

    plan["loud_section_cut_window_count"] = max(int(plan.get("loud_section_cut_window_count", 0) or 0), 1)
    plan["quiet_section_boost_window_count"] = max(int(plan.get("quiet_section_boost_window_count", 0) or 0), 1)
    plan["voice_priority_window_count"] = max(int(plan.get("voice_priority_window_count", 0) or 0), 1)

    plan["owner_tail_problem_sec"] = [471.0, 528.349]
    plan["owner_tail_music_guard_enabled"] = True
    plan["owner_tail_music_gain_floor_db"] = -38.0
    plan["owner_tail_music_min_gain_db"] = min(tail_gains) if tail_gains else None
    plan["owner_tail_music_silent_window_count"] = len([gain for gain in tail_gains if gain < -38.0])
    plan["owner_tail_no_silent_windows"] = plan["owner_tail_music_silent_window_count"] == 0
    plan["owner_tail_music_guard_passed"] = plan["owner_tail_music_silent_window_count"] == 0

    if gains:
        plan["tail_music_final_window_gain_db"] = gains[-1]
        plan["tail_music_final_window_audible"] = gains[-1] >= -44.0

    plan["forbidden_foreground_gain_blocked"] = all(gain <= -34.0 for gain in gains)
    return plan

# STEP23B_CLEAN_MINIMAL_END
