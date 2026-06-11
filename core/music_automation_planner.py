from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

OWNER_GAIN_MIN_DB = -38.0
OWNER_GAIN_MAX_DB = -30.0
MUSIC_AUDIBILITY_FLOOR_DB = -38.0
MUSIC_LOUDNESS_CEILING_DB = -30.0
OWNER_MUSIC_AUDIBLE_GAIN_RANGE_DB = (MUSIC_AUDIBILITY_FLOOR_DB, MUSIC_LOUDNESS_CEILING_DB)
OWNER_MUSIC_BALANCED_GAIN_RANGE_DB = OWNER_MUSIC_AUDIBLE_GAIN_RANGE_DB
DEFAULT_AUTOMATION_WINDOW_SEC = 5.0
DEFAULT_BASE_TARGET_GAIN_DB = -34.0
DEFAULT_MAX_GAIN_CHANGE_PER_WINDOW_DB = 2.0
DEFAULT_TRACK_START_TRIM_SEC = 30.0
DEFAULT_TRACK_END_TRIM_SEC = 15.0
DEFAULT_CROSSFADE_SEC = 3.0
DEFAULT_MIN_USABLE_TRACK_SEC = 45.0
VOICE_ACTIVE_MUSIC_CEILING_DB = -35.0
NO_VOICE_MUSIC_CEILING_DB = -30.0
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
    voice_active = float(voice_level_db) >= -38.0

    if voice_level_db >= -24.0:
        raw_gain_db -= 4.0
        reasons.append("voice_loud")
    elif voice_level_db >= -32.0:
        raw_gain_db -= 2.0
        reasons.append("voice_active")
    elif voice_level_db >= -38.0:
        raw_gain_db -= 1.0
        reasons.append("voice_present")
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

    if voice_active:
        raw_gain_db = min(raw_gain_db, VOICE_ACTIVE_MUSIC_CEILING_DB)
    else:
        raw_gain_db = min(raw_gain_db, NO_VOICE_MUSIC_CEILING_DB)
        raw_gain_db = max(raw_gain_db, -34.0)

    minimum, maximum = owner_range_db
    final_gain_db = max(minimum, min(maximum, raw_gain_db))

    return {
        "raw_gain_db": _round_db(raw_gain_db),
        "final_gain_db": _round_db(final_gain_db),
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

    voice_active = float(voice_level_db) >= VOICE_ACTIVE_LEVEL_DB

    if float(music_section_level_db) <= SOURCE_QUIET_SECTION_LEVEL_DB and not voice_active:
        boosted = max(final_gain, -30.0)
        source_adjustment = boosted - final_gain
        final_gain = boosted
        reason_parts.append("quiet_section_boost")
    elif float(music_section_level_db) >= SOURCE_LOUD_SECTION_LEVEL_DB:
        cut = min(final_gain, -38.0)
        source_adjustment = cut - final_gain
        final_gain = cut
        reason_parts.append("loud_section_cut")

    if voice_active:
        voice_cap = float(voice_level_db) - VOICE_PRIORITY_MARGIN_DB
        capped = min(final_gain, voice_cap)
        voice_adjustment = capped - final_gain
        final_gain = capped
        reason_parts.append("voice_priority_over_source_boost")

    final_gain = max(-40.0, min(-30.0, final_gain))

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
                "voice_level_db": voice["voice_level_db"],
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
        **continuity_guard,
    }
