from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.ffmpeg_helper import get_ffmpeg_path, get_ffprobe_path
from core.final_render_driver import FinalRenderDriver
from core.learning_corpus_audio_profile import extract_lufs_integrated, parse_loudnorm_json
from core.pair_track_truth_loader import load_truth
from core.power_profile import PowerProfile
from core.reaction_focus_decisions import inject_selected_reaction_focus_decisions
from core.smooth_zoom_engine import TARGET_BALANCED, TARGET_GAMEPLAY, ZoomCurve, ZoomKeyframe
from core.voice_intensity_analyzer import VoiceIntensityAnalyzer, VoiceIntensityPoint, read_mono_wav_samples
from models.edit_timeline import EditTimeline
from models.framing_instruction import FramingInstruction
from models.reframe_plan import ReframePlan
from models.timeline_segment import TimelineSegment
from shared.enums import ChannelType


PAIR_ID = "pair_006"
RAW_PATH = ROOT / "learning_corpus" / "pairs" / PAIR_ID / "raw.mp4"
DEFAULT_PICKS_JSON = ROOT / "reports" / "blockd_a2b3a_shadow" / "pair_006_shadow_LOCKED.json"
OUTPUT_DIR = ROOT / "reports" / "blockd_a2b3b_render"
DEFAULT_OUTPUT_PATH = OUTPUT_DIR / "pair_006_a2b3b_proof_v3.mp4"
DEFAULT_LOUDNESS_OUTPUT_PATH = OUTPUT_DIR / "pair_006_loudness_v1.mp4"

CONFIDENCE_FLOOR = 0.80
APPLY_LLM_PICKS_FOR_PROOF_RENDER = True
CLUSTER_MIN_SIZE = 2
CLUSTER_MAX_SIZE = 3
WINDOW_PAD_SECONDS = 4.0
REACTION_LEAD_IN_SECONDS = 0.0
GAMEPLAY_ZOOM = 1.4
ACTIVE_RMS_DBFS_THRESHOLD = -45.0
MIN_ACTIVE_SPEECH_SECONDS = 2.0
TRUE_PEAK_CEILING_DB = -1.0
TRUE_PEAK_LIMIT_RATIO = math.pow(10.0, TRUE_PEAK_CEILING_DB / 20.0)
VOICE_ANALYSIS_SAMPLE_RATE = 16000
VOICE_ANALYSIS_WINDOW_SECONDS = 1.0


def _truth_pair_config(pair_id: str = PAIR_ID) -> dict[str, Any]:
    truth = load_truth()
    pair = truth.get(pair_id)
    if not isinstance(pair, dict):
        raise RuntimeError(f"Missing pair_track_truth for {pair_id}")
    return pair


def _track_name_to_audio_index(track_name: str) -> int:
    if not isinstance(track_name, str) or not track_name.startswith("a"):
        raise RuntimeError(f"Unsupported track name: {track_name!r}")
    try:
        index = int(track_name[1:])
    except ValueError as exc:
        raise RuntimeError(f"Unsupported track name: {track_name!r}") from exc
    if index < 0:
        raise RuntimeError(f"Unsupported track name: {track_name!r}")
    return index


def _track_name_to_global_stream_spec(track_name: str) -> str:
    # raw.mp4 keeps video on 0:0, so track role a0 maps to container stream 0:1.
    return f"0:{_track_name_to_audio_index(track_name) + 1}"


def _track_name_to_audio_selector(track_name: str) -> str:
    return f"0:a:{_track_name_to_audio_index(track_name)}"


def _resolve_pair_audio_roles(pair_id: str = PAIR_ID) -> dict[str, dict[str, Any]]:
    pair = _truth_pair_config(pair_id)
    roles = {
        "ali": pair.get("ali_source"),
        "discord": pair.get("friend_source"),
        "game": pair.get("game_source"),
    }
    resolved: dict[str, dict[str, Any]] = {}
    for role, track_name in roles.items():
        if not isinstance(track_name, str) or not track_name:
            raise RuntimeError(f"{pair_id} missing required {role} track in pair_track_truth")
        resolved[role] = {
            "track_name": track_name,
            "audio_index": _track_name_to_audio_index(track_name),
            "global_stream_spec": _track_name_to_global_stream_spec(track_name),
            "audio_selector": _track_name_to_audio_selector(track_name),
        }
    return resolved


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _filtered_candidates(
    report: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, int]]:
    rows = report.get("candidates")
    if not isinstance(rows, list):
        raise RuntimeError("Shadow report has no candidates list")

    counters = {
        "input_candidates": len(rows),
        "excluded_not_real_reaction": 0,
        "excluded_real_below_confidence_floor": 0,
        "excluded_invalid_timing_or_confidence": 0,
        "remaining_after_filters": 0,
    }
    filtered: list[dict[str, Any]] = []
    real_below_floor: list[dict[str, Any]] = []

    for row in rows:
        if not isinstance(row, dict):
            counters["excluded_invalid_timing_or_confidence"] += 1
            continue
        try:
            start = float(row.get("start"))
            end = float(row.get("end"))
            zoom_start = float(row.get("zoom_start"))
            zoom_end = float(row.get("zoom_end"))
            confidence = float(row.get("confidence"))
        except (TypeError, ValueError):
            counters["excluded_invalid_timing_or_confidence"] += 1
            continue

        if end <= start or zoom_end <= zoom_start:
            counters["excluded_invalid_timing_or_confidence"] += 1
            continue

        normalized = {
            **row,
            "start": round(start, 3),
            "end": round(end, 3),
            "zoom_start": round(zoom_start, 3),
            "zoom_end": round(zoom_end, 3),
            "confidence": confidence,
            "friend_span_seconds": round(end - start, 3),
            "zoom_dauer": round(zoom_end - zoom_start, 3),
            "zoom_mode": str(row.get("zoom_mode") or "smooth"),
        }

        if row.get("is_real_reaction") is not True:
            counters["excluded_not_real_reaction"] += 1
            continue

        if confidence < CONFIDENCE_FLOOR:
            counters["excluded_real_below_confidence_floor"] += 1
            real_below_floor.append(normalized)
            continue

        filtered.append(normalized)

    filtered.sort(key=lambda item: (float(item["start"]), float(item["end"])))
    real_below_floor.sort(key=lambda item: (float(item["start"]), float(item["end"])))
    counters["remaining_after_filters"] = len(filtered)
    if len(filtered) < CLUSTER_MIN_SIZE:
        raise RuntimeError(
            f"Only {len(filtered)} candidates after filtering, need at least {CLUSTER_MIN_SIZE}"
        )
    return filtered, real_below_floor, counters


def _densest_cluster(rows: list[dict[str, Any]]) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    max_size = min(CLUSTER_MAX_SIZE, len(rows))
    for size in range(CLUSTER_MIN_SIZE, max_size + 1):
        for start_index in range(0, len(rows) - size + 1):
            cluster_rows = rows[start_index:start_index + size]
            cluster_start = float(cluster_rows[0]["start"])
            cluster_end = float(cluster_rows[-1]["end"])
            span = cluster_end - cluster_start
            density = float(size) / max(span, 0.001)
            candidates.append(
                {
                    "size": size,
                    "start_index": start_index,
                    "span_seconds": round(span, 3),
                    "density": round(density, 6),
                    "picks": cluster_rows,
                }
            )

    if not candidates:
        raise RuntimeError("No cluster candidates built")

    candidates.sort(
        key=lambda item: (
            -float(item["density"]),
            float(item["span_seconds"]),
            -int(item["size"]),
            float(item["picks"][0]["start"]),
        )
    )
    selected = dict(candidates[0])
    first = selected["picks"][0]
    last = selected["picks"][-1]
    window_start = max(0.0, float(first["start"]) - WINDOW_PAD_SECONDS)
    window_end = float(last["end"]) + WINDOW_PAD_SECONDS
    selected["window_start"] = round(window_start, 3)
    selected["window_end"] = round(window_end, 3)
    selected["window_duration_seconds"] = round(window_end - window_start, 3)
    return selected


def _segment(segment_id: str, job_id: str, start: float, end: float, role: str) -> TimelineSegment:
    return TimelineSegment(
        segment_id=segment_id,
        job_id=job_id,
        candidate_id=None,
        start_time=round(float(start), 3),
        end_time=round(float(end), 3),
        segment_role=role,
        selection_score=1.0,
        notes=["blockd_render_proof_a2"],
    )


def _build_timeline(
    *,
    job_id: str,
    window_start: float,
    window_end: float,
    picks: list[dict[str, Any]],
) -> EditTimeline:
    segments: list[TimelineSegment] = []
    cursor = float(window_start)
    for index, pick in enumerate(picks, start=1):
        focus_start = float(pick["zoom_start"])
        focus_end = float(pick["zoom_end"])
        candidate_index = str(pick.get("candidate_index", index))

        if focus_start > cursor:
            role = "context_before_reaction" if not segments else "context_between_reactions"
            segments.append(
                _segment(
                    f"{PAIR_ID}_context_{index:02d}",
                    job_id,
                    cursor,
                    focus_start,
                    role,
                )
            )

        segments.append(
            _segment(
                f"{PAIR_ID}_reaction_{candidate_index}",
                job_id,
                max(cursor, focus_start),
                focus_end,
                "llm_reaction_gameplay_focus",
            )
        )
        cursor = max(cursor, focus_end)

    if window_end > cursor:
        segments.append(
            _segment(
                f"{PAIR_ID}_post_context",
                job_id,
                cursor,
                window_end,
                "context_after_reaction",
            )
        )

    return EditTimeline(
        timeline_id=f"{PAIR_ID}_a2b3b_proof_window",
        job_id=job_id,
        target_duration=round(window_end - window_start, 3),
        selected_segments=[segment for segment in segments if segment.duration > 0.0],
        timeline_score=1.0,
        timeline_notes=["blockd_a2b3b_context_window"],
    )


def _build_reframe_plan(job_id: str, timeline: EditTimeline) -> ReframePlan:
    return ReframePlan(
        plan_id=f"{timeline.timeline_id}_reframe",
        job_id=job_id,
        timeline_id=timeline.timeline_id,
        source_aspect_ratio="32:9",
        primary_target_aspect_ratio="16:9",
        instructions=[
            FramingInstruction(
                instruction_id=f"frame_{segment.segment_id}",
                job_id=job_id,
                timeline_id=timeline.timeline_id,
                segment_id=segment.segment_id,
                focus_kind="balanced",
                layout_kind="balanced_split",
                source_aspect_ratio="32:9",
                target_aspect_ratio="16:9",
                crop_window={"x": 0.5, "y": 0.0, "width": 0.5, "height": 1.0},
                notes=["focus_decision_may_override"],
            )
            for segment in timeline.selected_segments
        ],
        plan_score=1.0,
    )


def _apply_a2_focus_window(decision: dict[str, Any], row: dict[str, Any]) -> dict[str, Any]:
    focus_start = float(row["zoom_start"])
    focus_end = float(row["zoom_end"])
    decision["focus_target"] = "gameplay"
    decision["facecam_opacity"] = 0.0
    decision["gameplay_zoom"] = GAMEPLAY_ZOOM
    decision["focus_start_seconds"] = round(focus_start, 3)
    decision["focus_end_seconds"] = round(focus_end, 3)
    decision["focus_duration_seconds"] = round(focus_end - focus_start, 3)
    decision["timestamp"] = round(focus_start + ((focus_end - focus_start) / 2.0), 3)
    decision["lead_in_seconds"] = REACTION_LEAD_IN_SECONDS
    decision["zoom_mode"] = str(row.get("zoom_mode") or "smooth")
    return decision


def _build_zoom_curve(*, window_start: float, window_end: float, picks: list[dict[str, Any]]) -> ZoomCurve:
    keyframes = [ZoomKeyframe(window_start, 1.0, TARGET_BALANCED, "linear")]
    for row in picks:
        focus_start = float(row["zoom_start"])
        focus_end = float(row["zoom_end"])
        keyframes.extend(
            [
                ZoomKeyframe(max(window_start, round(focus_start - 0.001, 3)), 1.0, TARGET_BALANCED, "linear"),
                ZoomKeyframe(focus_start, GAMEPLAY_ZOOM, TARGET_GAMEPLAY, "linear"),
                ZoomKeyframe(focus_end, GAMEPLAY_ZOOM, TARGET_GAMEPLAY, "linear"),
                ZoomKeyframe(min(window_end, round(focus_end + 0.001, 3)), 1.0, TARGET_BALANCED, "linear"),
            ]
        )
    keyframes.append(ZoomKeyframe(window_end, 1.0, TARGET_BALANCED, "linear"))
    return ZoomCurve(keyframes)


def _ffprobe_media(path: Path) -> dict[str, Any]:
    ffprobe_path = Path(get_ffprobe_path())
    result = subprocess.run(
        [
            str(ffprobe_path),
            "-v",
            "error",
            "-show_entries",
            "format=duration:stream=index,codec_type,width,height,channels,sample_rate",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def _format_db(value: float) -> str:
    return f"{value:.3f}dB"


def _safe_float(value: Any, *, default: float) -> float:
    try:
        converted = float(str(value).strip())
    except (TypeError, ValueError):
        return default
    if not math.isfinite(converted):
        return default
    return round(converted, 6)


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def _extract_stream_window_wav(
    *,
    source_path: Path,
    output_path: Path,
    stream_spec: str,
    start_seconds: float,
    duration_seconds: float,
) -> None:
    ffmpeg_path = get_ffmpeg_path()
    _run_command(
        [
            ffmpeg_path,
            "-y",
            "-hide_banner",
            "-v",
            "error",
            "-ss",
            f"{max(start_seconds, 0.0):.3f}",
            "-t",
            f"{max(duration_seconds, 0.001):.3f}",
            "-i",
            str(source_path),
            "-map",
            stream_spec,
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(VOICE_ANALYSIS_SAMPLE_RATE),
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
    )


def _analyze_voice_points_for_window(
    *,
    source_path: Path,
    speaker: str,
    stream_spec: str,
    start_seconds: float,
    end_seconds: float,
) -> list[VoiceIntensityPoint]:
    duration_seconds = round(max(end_seconds - start_seconds, 0.0), 3)
    if duration_seconds <= 0.0:
        raise RuntimeError(f"Invalid analysis window: {start_seconds}-{end_seconds}")

    analyzer = VoiceIntensityAnalyzer(
        ffmpeg_path=get_ffmpeg_path(),
        sample_rate=VOICE_ANALYSIS_SAMPLE_RATE,
        window_seconds=VOICE_ANALYSIS_WINDOW_SECONDS,
    )
    with tempfile.TemporaryDirectory(prefix="zenith_blockd_loudness_voice_") as temp_dir:
        wav_path = Path(temp_dir) / f"{speaker}.wav"
        _extract_stream_window_wav(
            source_path=source_path,
            output_path=wav_path,
            stream_spec=stream_spec,
            start_seconds=start_seconds,
            duration_seconds=duration_seconds,
        )
        samples, sample_rate = read_mono_wav_samples(wav_path)

    analyzed = analyzer.analyze_samples(samples=samples, sample_rate=sample_rate, speaker=speaker)
    absolute_points: list[VoiceIntensityPoint] = []
    for point in analyzed:
        absolute_points.append(
            VoiceIntensityPoint(
                timestamp=round(start_seconds + point.timestamp, 3),
                intensity=point.intensity,
                lufs=point.lufs,
                rms_dbfs=point.rms_dbfs,
                speaker=point.speaker,
            )
        )
    return absolute_points


def _is_active_voice_point(point: VoiceIntensityPoint) -> bool:
    return float(point.rms_dbfs) > ACTIVE_RMS_DBFS_THRESHOLD


def _active_seconds(points: list[VoiceIntensityPoint]) -> float:
    return round(sum(VOICE_ANALYSIS_WINDOW_SECONDS for point in points if _is_active_voice_point(point)), 3)


def _window_from_index_range(
    points: list[VoiceIntensityPoint],
    *,
    start_index: int,
    end_index: int,
) -> dict[str, Any]:
    start = float(points[start_index].timestamp)
    end = float(points[end_index - 1].timestamp) + VOICE_ANALYSIS_WINDOW_SECONDS
    subset = points[start_index:end_index]
    return {
        "start": round(start, 3),
        "end": round(end, 3),
        "duration_seconds": round(end - start, 3),
        "active_seconds": _active_seconds(subset),
        "point_count": len(subset),
    }


def _longest_active_window(
    points: list[VoiceIntensityPoint],
    *,
    speaker: str,
    minimum_seconds: float = MIN_ACTIVE_SPEECH_SECONDS,
) -> dict[str, Any]:
    if not points:
        raise RuntimeError(f"No voice analysis points for {speaker}")

    best: dict[str, Any] | None = None
    run_start: int | None = None

    def _commit(run_end: int) -> None:
        nonlocal best, run_start
        if run_start is None:
            return
        candidate = _window_from_index_range(points, start_index=run_start, end_index=run_end)
        if candidate["active_seconds"] < minimum_seconds:
            run_start = None
            return
        if best is None:
            best = candidate
        elif candidate["duration_seconds"] > best["duration_seconds"]:
            best = candidate
        elif candidate["duration_seconds"] == best["duration_seconds"] and candidate["start"] < best["start"]:
            best = candidate
        run_start = None

    for index, point in enumerate(points):
        if _is_active_voice_point(point):
            if run_start is None:
                run_start = index
            continue
        _commit(index)

    _commit(len(points))
    if best is None:
        raise RuntimeError(f"No active speech window >= {minimum_seconds:.1f}s for {speaker}")
    return {
        **best,
        "speaker": speaker,
        "active_threshold_rms_dbfs": ACTIVE_RMS_DBFS_THRESHOLD,
    }


def _select_dual_speaker_window(
    ali_points: list[VoiceIntensityPoint],
    discord_points: list[VoiceIntensityPoint],
    *,
    render_window_start: float,
    render_window_end: float,
    minimum_seconds: float = MIN_ACTIVE_SPEECH_SECONDS,
) -> dict[str, Any]:
    if len(ali_points) != len(discord_points):
        raise RuntimeError("Ali/Discord voice analysis lengths do not match")
    if not ali_points:
        raise RuntimeError("No voice analysis points available for dual-speaker window")

    ali_active_prefix = [0.0]
    discord_active_prefix = [0.0]
    for ali_point, discord_point in zip(ali_points, discord_points):
        ali_active_prefix.append(ali_active_prefix[-1] + (VOICE_ANALYSIS_WINDOW_SECONDS if _is_active_voice_point(ali_point) else 0.0))
        discord_active_prefix.append(
            discord_active_prefix[-1] + (VOICE_ANALYSIS_WINDOW_SECONDS if _is_active_voice_point(discord_point) else 0.0)
        )

    full_window = {
        "start": round(render_window_start, 3),
        "end": round(render_window_end, 3),
        "duration_seconds": round(render_window_end - render_window_start, 3),
        "active_seconds": _active_seconds(ali_points),
        "point_count": len(ali_points),
    }
    full_window["ali_active_seconds"] = round(ali_active_prefix[-1], 3)
    full_window["discord_active_seconds"] = round(discord_active_prefix[-1], 3)
    if full_window["ali_active_seconds"] >= minimum_seconds and full_window["discord_active_seconds"] >= minimum_seconds:
        full_window["window_origin"] = "full_render_window"
        return full_window

    best: dict[str, Any] | None = None
    point_count = len(ali_points)
    for start_index in range(point_count):
        for end_index in range(start_index + 1, point_count + 1):
            ali_active_seconds = round(ali_active_prefix[end_index] - ali_active_prefix[start_index], 3)
            discord_active_seconds = round(discord_active_prefix[end_index] - discord_active_prefix[start_index], 3)
            if ali_active_seconds < minimum_seconds or discord_active_seconds < minimum_seconds:
                continue
            candidate = _window_from_index_range(ali_points, start_index=start_index, end_index=end_index)
            candidate["ali_active_seconds"] = ali_active_seconds
            candidate["discord_active_seconds"] = discord_active_seconds
            candidate["window_origin"] = "trimmed_render_subwindow"
            if best is None:
                best = candidate
            elif candidate["duration_seconds"] < best["duration_seconds"]:
                best = candidate
            elif candidate["duration_seconds"] == best["duration_seconds"] and candidate["start"] < best["start"]:
                best = candidate
            break

    if best is None:
        raise RuntimeError(
            f"No window contains >= {minimum_seconds:.1f}s active Ali speech and >= {minimum_seconds:.1f}s active Discord speech"
        )
    return best


def _extract_lufs_from_stream_window(
    *,
    source_path: Path,
    speaker: str,
    stream_spec: str,
    start_seconds: float,
    end_seconds: float,
) -> float:
    duration_seconds = round(max(end_seconds - start_seconds, 0.0), 3)
    if duration_seconds <= 0.0:
        raise RuntimeError(f"Invalid LUFS window for {speaker}: {start_seconds}-{end_seconds}")

    with tempfile.TemporaryDirectory(prefix="zenith_blockd_lufs_") as temp_dir:
        clip_path = Path(temp_dir) / f"{speaker}_window.wav"
        _extract_stream_window_wav(
            source_path=source_path,
            output_path=clip_path,
            stream_spec=stream_spec,
            start_seconds=start_seconds,
            duration_seconds=duration_seconds,
        )
        return extract_lufs_integrated(clip_path, ffmpeg_path=get_ffmpeg_path())


def _extract_true_peak_db(media_path: Path) -> float:
    payload = parse_loudnorm_json(
        _run_command(
            [
                get_ffmpeg_path(),
                "-hide_banner",
                "-nostats",
                "-i",
                str(media_path),
                "-af",
                "loudnorm=I=-16:TP=-1.0:LRA=11:print_format=json",
                "-f",
                "null",
                "-",
            ]
        ).stderr
    )
    return _safe_float(payload.get("input_tp"), default=-120.0)


def _render_window_mix_audio(
    *,
    source_path: Path,
    output_path: Path,
    window_start: float,
    window_end: float,
    audio_roles: dict[str, dict[str, Any]],
    discord_gain_db: float,
    common_mix_gain_db: float = 0.0,
    limiter_enabled: bool = False,
) -> dict[str, Any]:
    duration_seconds = round(max(window_end - window_start, 0.0), 3)
    if duration_seconds <= 0.0:
        raise RuntimeError(f"Invalid loudness mix window: {window_start}-{window_end}")

    mix_label = "mix_limited" if limiter_enabled or abs(common_mix_gain_db) > 0.0001 else "mix"
    filter_steps = [
        f"[{audio_roles['ali']['audio_selector']}]volume={_format_db(0.0)}[ali_voice]",
        f"[{audio_roles['discord']['audio_selector']}]volume={_format_db(discord_gain_db)}[discord_voice]",
        f"[{audio_roles['game']['audio_selector']}]volume={_format_db(0.0)}[game_audio]",
        "[ali_voice][discord_voice][game_audio]amix=inputs=3:duration=longest:normalize=0[mix_pre]",
    ]
    if limiter_enabled or abs(common_mix_gain_db) > 0.0001:
        limiter_filter = ""
        if limiter_enabled:
            limiter_filter = f",alimiter=limit={TRUE_PEAK_LIMIT_RATIO:.8f}:attack=5:release=80:level=0"
        filter_steps.append(f"[mix_pre]volume={_format_db(common_mix_gain_db)}{limiter_filter}[{mix_label}]")
    else:
        filter_steps.append(f"[mix_pre]anull[{mix_label}]")

    _run_command(
        [
            get_ffmpeg_path(),
            "-y",
            "-hide_banner",
            "-v",
            "error",
            "-ss",
            f"{max(window_start, 0.0):.3f}",
            "-t",
            f"{duration_seconds:.3f}",
            "-i",
            str(source_path),
            "-filter_complex",
            ";".join(filter_steps),
            "-map",
            f"[{mix_label}]",
            "-c:a",
            "pcm_s16le",
            str(output_path),
        ]
    )
    return {
        "window_start": round(window_start, 3),
        "window_end": round(window_end, 3),
        "duration_seconds": duration_seconds,
        "discord_gain_db": round(discord_gain_db, 3),
        "common_mix_gain_db": round(common_mix_gain_db, 3),
        "limiter_enabled": limiter_enabled,
        "mix_filter": "amix=inputs=3:duration=longest:normalize=0",
    }


def _trim_render_video_for_window(
    *,
    rendered_video_path: Path,
    output_path: Path,
    render_window_start: float,
    target_window_start: float,
    target_window_end: float,
) -> None:
    offset_seconds = round(max(target_window_start - render_window_start, 0.0), 3)
    duration_seconds = round(max(target_window_end - target_window_start, 0.0), 3)
    if duration_seconds <= 0.0:
        raise RuntimeError(f"Invalid render trim window: {target_window_start}-{target_window_end}")

    _run_command(
        [
            get_ffmpeg_path(),
            "-y",
            "-hide_banner",
            "-v",
            "error",
            "-i",
            str(rendered_video_path),
            "-ss",
            f"{offset_seconds:.3f}",
            "-t",
            f"{duration_seconds:.3f}",
            "-map",
            "0:v:0",
            "-an",
            "-c:v",
            "copy",
            str(output_path),
        ]
    )


def _mux_video_with_audio(
    *,
    video_path: Path,
    audio_path: Path,
    output_path: Path,
) -> None:
    _run_command(
        [
            get_ffmpeg_path(),
            "-y",
            "-hide_banner",
            "-v",
            "error",
            "-i",
            str(video_path),
            "-i",
            str(audio_path),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "320k",
            "-shortest",
            str(output_path),
        ]
    )


def _build_loudness_post_step(
    *,
    proof: dict[str, Any],
    output_path: Path,
) -> dict[str, Any]:
    audio_roles = _resolve_pair_audio_roles(PAIR_ID)
    render_window_start = float(proof["window_start"])
    render_window_end = float(proof["window_end"])

    ali_points = _analyze_voice_points_for_window(
        source_path=RAW_PATH,
        speaker="ali",
        stream_spec=str(audio_roles["ali"]["global_stream_spec"]),
        start_seconds=render_window_start,
        end_seconds=render_window_end,
    )
    discord_points = _analyze_voice_points_for_window(
        source_path=RAW_PATH,
        speaker="discord",
        stream_spec=str(audio_roles["discord"]["global_stream_spec"]),
        start_seconds=render_window_start,
        end_seconds=render_window_end,
    )

    hearing_window = _select_dual_speaker_window(
        ali_points,
        discord_points,
        render_window_start=render_window_start,
        render_window_end=render_window_end,
    )
    ali_measure_window = _longest_active_window(
        [point for point in ali_points if hearing_window["start"] <= point.timestamp < hearing_window["end"]],
        speaker="ali",
    )
    discord_measure_window = _longest_active_window(
        [point for point in discord_points if hearing_window["start"] <= point.timestamp < hearing_window["end"]],
        speaker="discord",
    )

    ali_lufs_before = _extract_lufs_from_stream_window(
        source_path=RAW_PATH,
        speaker="ali_before",
        stream_spec=str(audio_roles["ali"]["global_stream_spec"]),
        start_seconds=float(ali_measure_window["start"]),
        end_seconds=float(ali_measure_window["end"]),
    )
    discord_lufs_before = _extract_lufs_from_stream_window(
        source_path=RAW_PATH,
        speaker="discord_before",
        stream_spec=str(audio_roles["discord"]["global_stream_spec"]),
        start_seconds=float(discord_measure_window["start"]),
        end_seconds=float(discord_measure_window["end"]),
    )
    discord_gain_db = round(ali_lufs_before - discord_lufs_before, 3)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="zenith_blockd_loudness_mix_") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        first_mix_audio_path = temp_dir / "mix_stage1.wav"
        final_mix_audio_path = temp_dir / "mix_final.wav"
        trimmed_video_path = temp_dir / "trimmed_visual.mp4"

        first_mix = _render_window_mix_audio(
            source_path=RAW_PATH,
            output_path=first_mix_audio_path,
            window_start=float(hearing_window["start"]),
            window_end=float(hearing_window["end"]),
            audio_roles=audio_roles,
            discord_gain_db=discord_gain_db,
        )
        first_true_peak_db = _extract_true_peak_db(first_mix_audio_path)
        common_mix_gain_db = 0.0
        limiter_enabled = False

        if first_true_peak_db > TRUE_PEAK_CEILING_DB:
            common_mix_gain_db = round(TRUE_PEAK_CEILING_DB - first_true_peak_db - 0.1, 3)
            limiter_enabled = True
            final_mix = _render_window_mix_audio(
                source_path=RAW_PATH,
                output_path=final_mix_audio_path,
                window_start=float(hearing_window["start"]),
                window_end=float(hearing_window["end"]),
                audio_roles=audio_roles,
                discord_gain_db=discord_gain_db,
                common_mix_gain_db=common_mix_gain_db,
                limiter_enabled=limiter_enabled,
            )
        else:
            shutil.copy2(first_mix_audio_path, final_mix_audio_path)
            final_mix = {
                **first_mix,
                "common_mix_gain_db": 0.0,
                "limiter_enabled": False,
            }

        final_true_peak_db = _extract_true_peak_db(final_mix_audio_path)
        if final_true_peak_db > TRUE_PEAK_CEILING_DB:
            raise RuntimeError(
                f"Mixed audio true peak still exceeds ceiling after limiter: {final_true_peak_db:.3f}dBFS > {TRUE_PEAK_CEILING_DB:.3f}dBFS"
            )

        ali_lufs_after = _extract_lufs_from_stream_window(
            source_path=final_mix_audio_path,
            speaker="ali_after",
            stream_spec="0:0",
            start_seconds=max(float(ali_measure_window["start"]) - float(hearing_window["start"]), 0.0),
            end_seconds=max(float(ali_measure_window["end"]) - float(hearing_window["start"]), 0.0),
        )
        discord_lufs_after = _extract_lufs_from_stream_window(
            source_path=final_mix_audio_path,
            speaker="discord_after",
            stream_spec="0:0",
            start_seconds=max(float(discord_measure_window["start"]) - float(hearing_window["start"]), 0.0),
            end_seconds=max(float(discord_measure_window["end"]) - float(hearing_window["start"]), 0.0),
        )

        render_video_source = Path(str(proof["target_output_path"]))
        if hearing_window["window_origin"] != "full_render_window":
            _trim_render_video_for_window(
                rendered_video_path=render_video_source,
                output_path=trimmed_video_path,
                render_window_start=render_window_start,
                target_window_start=float(hearing_window["start"]),
                target_window_end=float(hearing_window["end"]),
            )
            render_video_source = trimmed_video_path
        _mux_video_with_audio(video_path=render_video_source, audio_path=final_mix_audio_path, output_path=output_path)
        probe = _ffprobe_media(output_path)

    return {
        "output_path": str(output_path),
        "render_target_output_path": str(proof["target_output_path"]),
        "audio_roles": audio_roles,
        "hearing_window_raw": hearing_window,
        "ali_measure_window_raw": ali_measure_window,
        "discord_measure_window_raw": discord_measure_window,
        "lufs_before": {
            "ali": round(ali_lufs_before, 3),
            "discord": round(discord_lufs_before, 3),
        },
        "lufs_after_mixed_window": {
            "ali": round(ali_lufs_after, 3),
            "discord": round(discord_lufs_after, 3),
        },
        "discord_gain_db": round(discord_gain_db, 3),
        "true_peak_dbfs": {
            "before_common_gain": round(first_true_peak_db, 3),
            "after_common_gain": round(final_true_peak_db, 3),
        },
        "mix_post": {
            **final_mix,
            "true_peak_ceiling_dbfs": TRUE_PEAK_CEILING_DB,
        },
        "ffprobe": probe,
    }


def _make_runtime_job(tag: str) -> SimpleNamespace:
    return SimpleNamespace(
        job_id=f"pair_006_a2b3b_proof_{tag}",
        raw_video_path=str(RAW_PATH),
        channel_type=ChannelType.GAMING_MAIN,
        power_profile=PowerProfile.BALANCED,
        focus_decisions=[],
        focus_decisions_count=0,
        profanity_censor_matches=[],
        profanity_censor_report={},
    )


def _inject_runtime_focus_decisions(job: SimpleNamespace, picks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not APPLY_LLM_PICKS_FOR_PROOF_RENDER:
        raise RuntimeError("Scoped proof-render apply flag is disabled")

    injected = inject_selected_reaction_focus_decisions(
        job,
        picks,
        gameplay_zoom=GAMEPLAY_ZOOM,
    )
    if len(injected) != len(picks):
        raise RuntimeError(f"Injected {len(injected)} focus decisions for {len(picks)} picks")

    decisions: list[dict[str, Any]] = []
    for decision, row in zip(injected, picks):
        decision = _apply_a2_focus_window(decision, row)
        decision["scoped_apply_flag"] = "APPLY_LLM_PICKS_FOR_PROOF_RENDER"
        decisions.append(decision)
    job.focus_decisions = decisions
    job.focus_decisions_count = len(decisions)
    return decisions


def _pick_report(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_index": row.get("candidate_index"),
        "start": round(float(row["start"]), 3),
        "end": round(float(row["end"]), 3),
        "zoom_start": round(float(row["zoom_start"]), 3),
        "zoom_end": round(float(row["zoom_end"]), 3),
        "confidence": float(row["confidence"]),
        "zoom_mode": str(row.get("zoom_mode") or "smooth"),
        "friend_text": str(row.get("friend_text") or ""),
    }


def _planned_cut_segments(picks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "candidate_index": row.get("candidate_index"),
            "gameplay_crop_start": round(float(row["zoom_start"]), 3),
            "gameplay_crop_end": round(float(row["zoom_end"]), 3),
            "zoom_mode": str(row.get("zoom_mode") or "smooth"),
            "confidence": float(row["confidence"]),
            "friend_text": str(row.get("friend_text") or ""),
        }
        for row in picks
    ]


def _render_window(
    *,
    cluster: dict[str, Any],
    output_path: Path,
    tag: str,
) -> dict[str, Any]:
    picks = list(cluster["picks"])
    window_start = float(cluster["window_start"])
    window_end = float(cluster["window_end"])
    planned_segments = _planned_cut_segments(picks)

    job = _make_runtime_job(tag)
    injected = _inject_runtime_focus_decisions(job, picks)
    timeline = _build_timeline(
        job_id=job.job_id,
        window_start=window_start,
        window_end=window_end,
        picks=picks,
    )
    reframe_plan = _build_reframe_plan(job.job_id, timeline)
    zoom_curve = _build_zoom_curve(window_start=window_start, window_end=window_end, picks=picks)

    rendered_path = Path(
        FinalRenderDriver().render(
            job=job,
            source_path=str(RAW_PATH),
            edit_timeline=timeline,
            reframe_plan=reframe_plan,
            dynamic_edit_plan=None,
            smooth_zoom_curve=zoom_curve,
            output_dir=OUTPUT_DIR,
            facecam_static_tiny=False,
        )
    )
    shutil.copy2(rendered_path, output_path)
    context_path = OUTPUT_DIR / f"{job.job_id}_final_render_driver_context.json"
    context = _load_json(context_path)
    probe = _ffprobe_media(output_path)

    return {
        "target_output_path": str(output_path),
        "driver_output_path": str(rendered_path),
        "context_path": str(context_path),
        "window_start": round(window_start, 3),
        "window_end": round(window_end, 3),
        "window_duration_seconds": round(window_end - window_start, 3),
        "planned_cut_segments": planned_segments,
        "timeline_segments": [
            {
                "segment_id": segment.segment_id,
                "role": segment.segment_role,
                "start": segment.start_time,
                "end": segment.end_time,
                "duration": round(segment.duration, 3),
            }
            for segment in timeline.selected_segments
        ],
        "injected_focus_decisions": injected,
        "zoom_curve": zoom_curve.to_dict(),
        "render_context": {
            "focus_decisions_used": context.get("focus_decisions_used"),
            "smooth_zoom_used": context.get("smooth_zoom_used"),
            "render_layout_counts": context.get("render_layout_counts"),
            "resolved_render_layouts": context.get("resolved_render_layouts"),
            "smooth_zoom_records": context.get("smooth_zoom_records"),
        },
        "ffprobe": probe,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--picks-json", type=Path, default=DEFAULT_PICKS_JSON)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--tag", default="v3")
    parser.add_argument("--apply-loudness", action="store_true")
    args = parser.parse_args(argv[1:])

    picks_json = args.picks_json if args.picks_json.is_absolute() else ROOT / args.picks_json
    tag = str(args.tag).strip() or "v3"
    default_out_requested = args.out == DEFAULT_OUTPUT_PATH
    requested_output_path = args.out if args.out.is_absolute() else ROOT / args.out
    output_path = requested_output_path
    render_output_path = output_path
    if args.apply_loudness:
        if default_out_requested:
            output_path = DEFAULT_LOUDNESS_OUTPUT_PATH
        render_output_path = OUTPUT_DIR / f"{PAIR_ID}_a2b3b_proof_{tag}_visual.mp4"

    if not RAW_PATH.exists():
        raise RuntimeError(f"Raw video missing: {RAW_PATH}")
    if not picks_json.exists():
        raise RuntimeError(f"Shadow report missing: {picks_json}")

    report = _load_json(picks_json)
    filtered, real_below_floor, counters = _filtered_candidates(report)
    cluster = _densest_cluster(filtered)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("A2b-3b Artifact-Locked Proof Render")
    print(f"pair_id={PAIR_ID}")
    print(f"raw_path={RAW_PATH}")
    print(f"picks_json={picks_json}")
    print(f"output_path={output_path}")
    print(f"render_output_path={render_output_path}")
    print(f"render_tag={tag}")
    print(f"apply_loudness={args.apply_loudness}")
    print(f"confidence_floor={CONFIDENCE_FLOOR:.2f}")
    print(f"scoped_apply_flag=APPLY_LLM_PICKS_FOR_PROOF_RENDER:{APPLY_LLM_PICKS_FOR_PROOF_RENDER}")
    print(f"filter_counters={json.dumps(counters, ensure_ascii=False, sort_keys=True)}")

    print("kept_picks_ge_floor=")
    for row in filtered:
        print(json.dumps(_pick_report(row), ensure_ascii=False, sort_keys=True))

    print("real_reactions_dropped_below_floor=")
    for row in real_below_floor:
        print(json.dumps(_pick_report(row), ensure_ascii=False, sort_keys=True))

    print(
        "selected_cluster="
        f"size={cluster['size']} span={cluster['span_seconds']:.3f} "
        f"density={cluster['density']:.6f} "
        f"window={cluster['window_start']:.3f}-{cluster['window_end']:.3f} "
        f"duration={cluster['window_duration_seconds']:.3f}"
    )
    print("selected_cluster_picks=")
    for row in cluster["picks"]:
        print(json.dumps(_pick_report(row), ensure_ascii=False, sort_keys=True))

    proof = _render_window(cluster=cluster, output_path=render_output_path, tag=tag)
    print("planned_cut_segments=")
    print(json.dumps(proof["planned_cut_segments"], indent=2, ensure_ascii=False, sort_keys=True))
    print("render_proof=")
    print(json.dumps(proof, indent=2, ensure_ascii=False, sort_keys=True))
    if args.apply_loudness:
        loudness_proof = _build_loudness_post_step(proof=proof, output_path=output_path)
        print("loudness_post_step=")
        print(json.dumps(loudness_proof, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
