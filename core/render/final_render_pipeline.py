from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.ffmpeg_helper import get_ffmpeg_path, get_ffprobe_path
from core.final_render_driver import FinalRenderDriver
from core.g8_render_timeline_adapter import (
    build_edit_timeline_from_g8_plan,
    compare_timeline_to_g8_plan,
    load_g8_timeline_plan,
)
from core.power_profile import PowerProfile
from core.render.reaction_size_events import (
    ReactionSizeEventConfig,
    build_owner_loudness_size_event_payload,
    build_reaction_size_event_payload,
    build_reaction_signal_size_event_payload,
    write_reaction_size_events_json,
)
from shared.enums import ChannelType


class CombinedRenderJob(SimpleNamespace):
    def touch(self) -> None:
        return None


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8", errors="replace"))


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        text = line.strip()
        if not text:
            continue
        value = json.loads(text)
        if isinstance(value, dict):
            rows.append(value)
    return rows


def _overlap_seconds(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


def _extract_semantic_question_windows(
    *,
    semantic_analysis_path: Path,
    plan: dict[str, Any],
) -> list[dict[str, Any]]:
    if not semantic_analysis_path.exists():
        return []

    analysis = read_json(semantic_analysis_path)
    semantic_units = analysis.get("semantic_units") if isinstance(analysis, dict) else None
    if not isinstance(semantic_units, list):
        return []

    render_segments = plan.get("timeline_segments") or []
    questions: list[dict[str, Any]] = []
    for index, unit in enumerate(semantic_units, start=1):
        if not isinstance(unit, dict):
            continue
        features = unit.get("semantic_features") if isinstance(unit.get("semantic_features"), dict) else {}
        is_question = bool(unit.get("is_question") or features.get("is_question") or features.get("has_question"))
        if not is_question:
            continue

        try:
            start = float(unit.get("start_seconds"))
            end = float(unit.get("end_seconds"))
        except (TypeError, ValueError):
            continue
        if end <= start:
            continue

        selected_overlap = 0.0
        for segment in render_segments:
            try:
                seg_start = float(segment.get("start_seconds"))
                seg_end = float(segment.get("end_seconds"))
            except (TypeError, ValueError):
                continue
            selected_overlap += _overlap_seconds(start, end, seg_start, seg_end)
        if selected_overlap <= 0.0:
            continue

        questions.append(
            {
                "question_id": str(unit.get("utterance_id") or unit.get("unit_id") or f"semantic_question_{index:04d}"),
                "unit_index": index,
                "start_seconds": round(start, 3),
                "end_seconds": round(end, 3),
                "duration_seconds": round(end - start, 3),
                "selected_overlap_seconds": round(selected_overlap, 3),
                "text": unit.get("text"),
                "is_question": True,
                "source": "semantic_content_layer.semantic_units.semantic_features.has_question",
                "relevance_score": unit.get("relevance_score"),
                "raw_relevance_score": unit.get("raw_relevance_score"),
            }
        )

    return questions


def _run(cmd: list[str], *, label: str) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            f"{label} failed\nSTDOUT:\n{result.stdout[-3000:]}\nSTDERR:\n{result.stderr[-3000:]}"
        )
    return result


def _ffprobe(path: Path) -> dict[str, Any]:
    cmd = [
        get_ffprobe_path(),
        "-v", "error",
        "-show_entries",
        "stream=index,codec_type,width,height,channels,channel_layout,sample_rate",
        "-show_entries",
        "format=duration",
        "-of", "json",
        str(path),
    ]
    result = _run(cmd, label="ffprobe")
    data = json.loads(result.stdout)

    video = None
    audio = None
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video" and video is None:
            video = stream
        if stream.get("codec_type") == "audio" and audio is None:
            audio = stream

    return {
        "duration_seconds": round(float(data.get("format", {}).get("duration") or 0.0), 3),
        "video": video or {},
        "audio": audio or {},
    }


def _load_context_segments(context_path: Path) -> list[dict[str, Any]]:
    if not context_path.exists():
        raise FileNotFoundError(f"render context missing: {context_path}")
    context = json.loads(context_path.read_text(encoding="utf-8"))
    return context.get("segments") or []


def _compare_context_to_plan(context_segments: list[dict[str, Any]], plan: dict[str, Any]) -> dict[str, Any]:
    plan_segments = plan.get("timeline_segments") or []
    deviations = []
    matched = 0

    for index, plan_seg in enumerate(plan_segments):
        if index >= len(context_segments):
            deviations.append({"index": index, "reason": "missing_context_segment"})
            continue

        ctx_seg = context_segments[index]
        ps = round(float(plan_seg["start_seconds"]), 3)
        pe = round(float(plan_seg["end_seconds"]), 3)
        rs = round(float(ctx_seg["start_time"]), 3)
        re = round(float(ctx_seg["end_time"]), 3)

        if ps == rs and pe == re:
            matched += 1
        else:
            deviations.append({
                "index": index,
                "reason": "time_mismatch",
                "plan_start": ps,
                "plan_end": pe,
                "render_start": rs,
                "render_end": re,
            })

    if len(context_segments) > len(plan_segments):
        deviations.append({
            "reason": "extra_context_segments",
            "extra_count": len(context_segments) - len(plan_segments),
        })

    return {
        "plan_segment_count": len(plan_segments),
        "render_context_segment_count": len(context_segments),
        "matched_segments": matched,
        "deviation_count": len(deviations),
        "exact_match": len(deviations) == 0 and matched == len(plan_segments),
        "deviations": deviations[:20],
    }


def _build_audio_filter_script(
    *,
    segments: list[dict[str, Any]],
    filter_path: Path,
    owner_volume: float,
    friend_volume: float,
    game_volume: float,
) -> None:
    lines: list[str] = []
    mix_labels: list[str] = []

    for index, segment in enumerate(segments):
        start = float(segment["start_seconds"])
        end = float(segment["end_seconds"])

        owner = f"a{index:04d}_owner"
        friend = f"a{index:04d}_friend"
        game = f"a{index:04d}_game"
        mixed = f"a{index:04d}_mix"

        lines.append(
            f"[1:a:0]atrim=start={start:.3f}:end={end:.3f},"
            f"asetpts=PTS-STARTPTS,volume={owner_volume:.3f}[{owner}]"
        )
        lines.append(
            f"[1:a:1]atrim=start={start:.3f}:end={end:.3f},"
            f"asetpts=PTS-STARTPTS,volume={friend_volume:.3f}[{friend}]"
        )
        lines.append(
            f"[1:a:2]atrim=start={start:.3f}:end={end:.3f},"
            f"asetpts=PTS-STARTPTS,volume={game_volume:.3f}[{game}]"
        )
        lines.append(
            f"[{owner}][{friend}][{game}]"
            f"amix=inputs=3:duration=longest:dropout_transition=0:normalize=0,"
            f"alimiter=limit=0.95,aresample=48000[{mixed}]"
        )
        mix_labels.append(f"[{mixed}]")

    lines.append(
        "".join(mix_labels)
        + f"concat=n={len(mix_labels)}:v=0:a=1,"
        + "aresample=48000[aout]"
    )

    filter_path.parent.mkdir(parents=True, exist_ok=True)
    filter_path.write_text(";\n".join(lines) + "\n", encoding="utf-8")


def _mux_render_video_with_combined_audio(
    *,
    rendered_video: Path,
    source_video: Path,
    output_video: Path,
    filter_script: Path,
) -> None:
    cmd = [
        get_ffmpeg_path(),
        "-y",
        "-i", str(rendered_video),
        "-i", str(source_video),
        "-filter_complex_script", str(filter_script),
        "-map", "0:v:0",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        str(output_video),
    ]
    _run(cmd, label="combined audio mux")


def _extract_owner_loudness_windows(
    *,
    source_video: Path,
    audio_stream_index: int,
    window_seconds: float,
) -> list[dict[str, Any]]:
    sample_rate = 48000
    samples_per_window = max(1, int(round(sample_rate * max(0.05, window_seconds))))
    cmd = [
        get_ffmpeg_path(),
        "-hide_banner",
        "-nostats",
        "-i", str(source_video),
        "-map", f"0:a:{audio_stream_index}",
        "-af",
        (
            f"asetnsamples=n={samples_per_window}:p=1,"
            "astats=metadata=1:reset=1,"
            "ametadata=print:key=lavfi.astats.Overall.RMS_level"
        ),
        "-f", "null",
        "-",
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(
            "owner loudness extraction failed\n"
            f"STDOUT:\n{result.stdout[-3000:]}\nSTDERR:\n{result.stderr[-3000:]}"
        )

    windows: list[dict[str, Any]] = []
    current_start: float | None = None
    text = result.stderr + "\n" + result.stdout
    for line in text.splitlines():
        match_time = re.search(r"pts_time:([0-9]+(?:\.[0-9]+)?)", line)
        if match_time:
            current_start = float(match_time.group(1))
            continue

        match_rms = re.search(r"RMS_level=((-?\d+(?:\.\d+)?)|-inf)", line)
        if match_rms and current_start is not None:
            token = match_rms.group(1)
            rms = -120.0 if token == "-inf" else float(token)
            windows.append(
                {
                    "start_seconds": round(current_start, 3),
                    "end_seconds": round(current_start + window_seconds, 3),
                    "owner_rms_dbfs": round(rms, 6),
                    "track_role": "owner",
                    "track": "track1",
                    "audio_stream_index": audio_stream_index,
                }
            )
            current_start = None

    return windows


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _copy_json_bytes(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() == target.resolve():
        return
    target.write_bytes(source.read_bytes())


def _write_report(path: Path, report: dict[str, Any]) -> None:
    lines: list[str] = []
    lines.append("PROJECT ZENITH - COMBINED RENDER REPORT")
    lines.append("")
    lines.append(f"stage={report['stage']}")
    lines.append(f"plan_path={report['plan_path']}")
    lines.append(f"source_video={report['source_video']}")
    lines.append(f"render_a_video={report['render_a_video']}")
    lines.append(f"output_video_path={report['output_video_path']}")
    lines.append(f"context_path={report['context_path']}")
    lines.append(f"audio_filter_script={report['audio_filter_script']}")
    lines.append("")
    lines.append("VIDEO")
    lines.append(f"- width={report['ffprobe']['video'].get('width')}")
    lines.append(f"- height={report['ffprobe']['video'].get('height')}")
    lines.append(f"- duration_seconds={report['ffprobe']['duration_seconds']}")
    lines.append("")
    lines.append("AUDIO")
    lines.append(f"- present={report['audio_check']['present']}")
    lines.append(f"- channels={report['audio_check']['channels']}")
    lines.append(f"- sample_rate={report['audio_check']['sample_rate']}")
    lines.append(f"- channel_layout={report['audio_check']['channel_layout']}")
    lines.append("")
    lines.append("AUDIO MIX PROOF")
    lines.append("- ffmpeg input #1 stream mapping:")
    lines.append("- [1:a:0] = raw audio stream 1 / Owner")
    lines.append("- [1:a:1] = raw audio stream 2 / Discord-Friend")
    lines.append("- [1:a:2] = raw audio stream 3 / Game")
    lines.append(f"- owner_volume={report['audio_mix']['owner_volume']}")
    lines.append(f"- friend_volume={report['audio_mix']['friend_volume']}")
    lines.append(f"- game_volume={report['audio_mix']['game_volume']}")
    lines.append("- mix_filter=amix inputs=3 + alimiter + aresample")
    lines.append("")
    lines.append("SEGMENT CHECK")
    for key, value in report["segment_check"].items():
        if key != "deviations":
            lines.append(f"- {key}={value}")
    lines.append("")
    lines.append("DURATION CHECK")
    for key, value in report["duration_check"].items():
        lines.append(f"- {key}={value}")
    lines.append("")
    lines.append("ANTI-OVERCUT")
    for key, value in report["anti_overcut"].items():
        lines.append(f"- {key}={value}")
    lines.append("")
    lines.append("FACECAM")
    for key, value in report["facecam"].items():
        lines.append(f"- {key}={value}")
    lines.append("")
    lines.append(f"overall_pass={report['overall_pass']}")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", default="reports/word_snap_2_fix/word_snap_2_fix_final_editorial_plan.json")
    parser.add_argument("--video", required=True)
    parser.add_argument("--out-dir", default="reports/combined_render")
    parser.add_argument("--owner-volume", type=float, default=1.35)
    parser.add_argument("--friend-volume", type=float, default=1.35)
    parser.add_argument("--game-volume", type=float, default=0.45)
    parser.add_argument("--enable-reaction-size-events", action="store_true")
    parser.add_argument("--enable-highlight-gated-size-events", action="store_true")
    parser.add_argument("--reactions", default="reports/reaction_adaptive/reaction_adaptive_fortnite_reactions.json")
    parser.add_argument("--reaction-prominence-rows", default="reports/highlight_ranking_reaction_wiring/highlight_ranking_reaction_wiring_rows.json")
    parser.add_argument("--reaction-signal-windows", default="")
    parser.add_argument("--reaction-size-events-input", default="")
    parser.add_argument("--reaction-prominence-percentile", type=float, default=0.25)
    parser.add_argument("--reaction-prominence-floor", type=float, default=None)
    parser.add_argument("--semantic-content-analysis", default="reports/semantic_content_layer/semantic_content_analysis.json")
    parser.add_argument("--reaction-size-events-output", default="")
    parser.add_argument("--owner-track", default="track1")
    parser.add_argument("--friend-track", default="track2")
    parser.add_argument("--game-track", default="track3")
    parser.add_argument("--enable-owner-loudness-size-events", action="store_true")
    parser.add_argument("--owner-audio-stream-index", type=int, default=0)
    parser.add_argument("--owner-speech-regions", default="reports/combined_speech/owner_speech_regions_track_1.json")
    parser.add_argument("--owner-loudness-windows-output", default="")
    parser.add_argument("--owner-loudness-window-seconds", type=float, default=0.5)
    parser.add_argument("--baseline-reaction-size-events", default="reports/ranked_render/ranked_cut_v10_reaction_size_events.json")
    args = parser.parse_args(argv)
    if args.enable_highlight_gated_size_events and args.enable_owner_loudness_size_events:
        parser.error("--enable-highlight-gated-size-events cannot be combined with --enable-owner-loudness-size-events")
    size_events_requested = (
        args.enable_reaction_size_events
        or args.enable_highlight_gated_size_events
        or args.enable_owner_loudness_size_events
        or bool(args.reaction_size_events_input)
    )

    plan_path = Path(os.environ.get("ZENITH_RENDER_PLAN_PATH") or os.environ.get("ZENITH_G8_PLAN_PATH") or args.plan)
    source_video = Path(args.video)
    out_dir = Path(os.environ.get("ZENITH_RENDER_OUTPUT_PATH") or os.environ.get("ZENITH_OUTPUT_PATH") or args.out_dir).parent if (os.environ.get("ZENITH_RENDER_OUTPUT_PATH") or os.environ.get("ZENITH_OUTPUT_PATH")) else Path(args.out_dir)
    final_output = Path(os.environ.get("ZENITH_RENDER_OUTPUT_PATH") or os.environ.get("ZENITH_OUTPUT_PATH") or str(out_dir / "combined_render_final_plan_track_1_2_3_audio.mp4"))
    render_a_dir = out_dir / "render_a_video"
    render_a_dir.mkdir(parents=True, exist_ok=True)
    out_dir.mkdir(parents=True, exist_ok=True)

    if not plan_path.exists():
        raise FileNotFoundError(plan_path)
    if not source_video.exists():
        raise FileNotFoundError(source_video)

    plan = load_g8_timeline_plan(plan_path)
    label = str(plan.get("label") or plan_path.stem)
    job_id = f"combined_render_{label}"

    timeline = build_edit_timeline_from_g8_plan(
        job_id=job_id,
        plan_path=plan_path,
    )
    adapter_check = compare_timeline_to_g8_plan(
        timeline=timeline,
        plan_data=plan,
    )

    job = CombinedRenderJob(
        job_id=job_id,
        raw_video_path=str(source_video),
        channel_type=ChannelType.GAMING_MAIN,
        power_profile=PowerProfile.BALANCED,
        focus_decisions=[],
        profanity_censor_matches=[],
        profanity_censor_report={},
    )

    print("PROJECT ZENITH - COMBINED RENDER")
    print(f"plan={plan_path}")
    print(f"source_video={source_video}")
    print(f"segments={len(timeline.selected_segments)}")
    print(f"plan_duration_seconds={timeline.total_selected_duration}")
    print("facecam_static_tiny=True")
    print("audio_mix=raw streams 1+2+3")
    print("")

    reaction_size_payload = None
    reaction_size_events: list[dict[str, Any]] = []
    reaction_size_events_path = Path(args.reaction_size_events_output) if args.reaction_size_events_output else out_dir / f"{final_output.stem}_reaction_size_events.json"

    reaction_size_events_input_path = Path(args.reaction_size_events_input) if args.reaction_size_events_input else None

    if reaction_size_events_input_path is not None:
        if not reaction_size_events_input_path.exists():
            raise FileNotFoundError(reaction_size_events_input_path)
        reaction_size_payload = read_json(reaction_size_events_input_path)
        if not isinstance(reaction_size_payload, dict):
            raise RuntimeError(f"reaction size events input must be a JSON object: {reaction_size_events_input_path}")
        reaction_size_events = list(reaction_size_payload.get("events") or [])
        _copy_json_bytes(reaction_size_events_input_path, reaction_size_events_path)
        print("precomputed_reaction_size_events_enabled=True")
        print(f"reaction_size_events_input_path={reaction_size_events_input_path}")
        print(f"reaction_size_events_path={reaction_size_events_path}")
        print(f"reaction_size_event_count={len(reaction_size_events)}")
        print("")

    elif args.enable_owner_loudness_size_events:
        owner_speech_regions_path = Path(args.owner_speech_regions)
        if not owner_speech_regions_path.exists():
            raise FileNotFoundError(owner_speech_regions_path)

        loudness_windows_path = (
            Path(args.owner_loudness_windows_output)
            if args.owner_loudness_windows_output
            else out_dir / f"{final_output.stem}_owner_loudness_windows.json"
        )
        owner_loudness_windows = _extract_owner_loudness_windows(
            source_video=source_video,
            audio_stream_index=args.owner_audio_stream_index,
            window_seconds=args.owner_loudness_window_seconds,
        )
        _write_json(
            loudness_windows_path,
            {
                "source": "ffmpeg_astats_owner_track_loudness_windows",
                "source_video": str(source_video),
                "owner_track": args.owner_track,
                "owner_audio_stream_index": args.owner_audio_stream_index,
                "window_seconds": args.owner_loudness_window_seconds,
                "window_count": len(owner_loudness_windows),
                "windows": owner_loudness_windows,
            },
        )

        owner_speech_data = read_json(owner_speech_regions_path)
        owner_speech_regions = owner_speech_data.get("speech_regions") if isinstance(owner_speech_data, dict) else owner_speech_data

        baseline_event_count = None
        baseline_path = Path(args.baseline_reaction_size_events)
        if baseline_path.exists():
            baseline_data = read_json(baseline_path)
            if isinstance(baseline_data, dict):
                baseline_event_count = int(baseline_data.get("event_count") or 0)

        reaction_size_config = ReactionSizeEventConfig(
            owner_track=args.owner_track,
            friend_track=args.friend_track,
            game_track=args.game_track,
            min_hold_seconds=1.5,
            merge_gap_seconds=0.35,
            post_hold_seconds=0.15,
            small_loudness_percentile=0.55,
            medium_loudness_percentile=0.75,
            large_loudness_percentile=0.90,
            min_owner_speech_overlap_seconds=0.10,
        )
        reaction_size_payload = build_owner_loudness_size_event_payload(
            owner_loudness_windows=owner_loudness_windows,
            render_segments=plan.get("timeline_segments") or [],
            owner_speech_regions=owner_speech_regions or [],
            config=reaction_size_config,
            baseline_event_count=baseline_event_count,
        )
        reaction_size_payload["owner_loudness_windows_path"] = str(loudness_windows_path)
        reaction_size_payload["owner_speech_regions_path"] = str(owner_speech_regions_path)
        reaction_size_events = list(reaction_size_payload.get("events") or [])
        write_reaction_size_events_json(reaction_size_events_path, reaction_size_payload)
        print("owner_loudness_size_events_enabled=True")
        print(f"reaction_size_events_path={reaction_size_events_path}")
        print(f"owner_loudness_windows_path={loudness_windows_path}")
        print(f"reaction_size_event_count={len(reaction_size_events)}")
        print(f"owner_loudness_thresholds={reaction_size_payload.get('owner_loudness_thresholds')}")
        print(
            "reaction_size_track_roles="
            f"owner:{args.owner_track} friend:{args.friend_track} game:{args.game_track}"
        )
        print("")

    elif args.enable_reaction_size_events or args.enable_highlight_gated_size_events:
        reactions_path = Path(args.reactions)
        prominence_rows_path = Path(args.reaction_prominence_rows)
        if not prominence_rows_path.exists():
            raise FileNotFoundError(prominence_rows_path)

        prominence_percentile = (
            float(args.reaction_prominence_percentile)
            if args.enable_highlight_gated_size_events
            else 0.70
        )
        reaction_size_config = ReactionSizeEventConfig(
            owner_track=args.owner_track,
            friend_track=args.friend_track,
            game_track=args.game_track,
            prominence_percentile=prominence_percentile,
            prominence_floor=args.reaction_prominence_floor,
            min_hold_seconds=1.5,
            merge_gap_seconds=0.35,
            post_hold_seconds=0.15,
            include_medium=True,
        )
        reaction_signal_windows_path = Path(args.reaction_signal_windows) if args.reaction_signal_windows else None
        if reaction_signal_windows_path is not None:
            if not reaction_signal_windows_path.exists():
                raise FileNotFoundError(reaction_signal_windows_path)
            semantic_question_windows = _extract_semantic_question_windows(
                semantic_analysis_path=Path(args.semantic_content_analysis),
                plan=plan,
            )
            reaction_size_payload = build_reaction_signal_size_event_payload(
                reaction_signal_windows=read_jsonl(reaction_signal_windows_path),
                prominence_rows=read_json(prominence_rows_path),
                render_segments=plan.get("timeline_segments") or [],
                config=reaction_size_config,
                question_windows=semantic_question_windows,
            )
            reaction_size_payload["size_event_mode"] = "meaning_gated_reaction_signal_question_prominence_v14"
            reaction_size_payload["reaction_signal_windows_path"] = str(reaction_signal_windows_path)
            reaction_size_payload["semantic_content_analysis_path"] = str(Path(args.semantic_content_analysis))
            reaction_size_payload["semantic_question_window_count"] = len(semantic_question_windows)
        else:
            if not reactions_path.exists():
                raise FileNotFoundError(reactions_path)
            reaction_size_payload = build_reaction_size_event_payload(
                reactions=read_json(reactions_path),
                prominence_rows=read_json(prominence_rows_path),
                render_segments=plan.get("timeline_segments") or [],
                config=reaction_size_config,
            )
            reaction_size_payload["size_event_mode"] = (
                "highlight_gated_reaction_prominence_v12"
                if args.enable_highlight_gated_size_events
                else "reaction_prominence_v10"
            )
        reaction_size_payload["raw_owner_loudness_trigger_enabled"] = False
        reaction_size_events = list(reaction_size_payload.get("events") or [])
        write_reaction_size_events_json(reaction_size_events_path, reaction_size_payload)
        print("highlight_gated_size_events_enabled=True" if args.enable_highlight_gated_size_events else "reaction_size_events_enabled=True")
        print(f"reaction_size_events_path={reaction_size_events_path}")
        if reaction_size_payload.get("reaction_signal_windows_path"):
            print(f"reaction_signal_windows_path={reaction_size_payload.get('reaction_signal_windows_path')}")
        print(f"reaction_size_event_count={len(reaction_size_events)}")
        print(f"reaction_size_prominence_floor={reaction_size_payload.get('prominence_floor')}")
        print(f"reaction_size_prominence_percentile={reaction_size_payload.get('prominence_percentile')}")
        print(f"raw_owner_loudness_trigger_enabled={reaction_size_payload.get('raw_owner_loudness_trigger_enabled')}")
        print(
            "reaction_size_track_roles="
            f"owner:{args.owner_track} friend:{args.friend_track} game:{args.game_track}"
        )
        print("")

    render_a_video = Path(
        FinalRenderDriver().render(
            job=job,
            source_path=source_video,
            edit_timeline=timeline,
            reframe_plan=None,
            dynamic_edit_plan=None,
            output_dir=render_a_dir,
            facecam_static_tiny=True,
            reaction_size_events=reaction_size_events,
        )
    )

    context_path = render_a_dir / f"{job_id}_final_render_driver_context.json"
    context_segments = _load_context_segments(context_path)
    segment_check = _compare_context_to_plan(context_segments, plan)

    filter_script = out_dir / "combined_audio_track_1_2_3_filter.ffscript"

    _build_audio_filter_script(
        segments=plan.get("timeline_segments") or [],
        filter_path=filter_script,
        owner_volume=args.owner_volume,
        friend_volume=args.friend_volume,
        game_volume=args.game_volume,
    )

    _mux_render_video_with_combined_audio(
        rendered_video=render_a_video,
        source_video=source_video,
        output_video=final_output,
        filter_script=filter_script,
    )

    ffprobe = _ffprobe(final_output)

    expected_duration = round(float(timeline.total_selected_duration), 3)
    actual_duration = round(float(ffprobe["duration_seconds"]), 3)
    duration_delta = round(abs(actual_duration - expected_duration), 3)

    anti = plan.get("anti_overcut_audit") or {}
    plan_anti_fail_count = int(anti.get("fail_count") or 0)

    facecam_context = json.loads(context_path.read_text(encoding="utf-8"))

    facecam = {
        "static_tiny_used": bool(facecam_context.get("facecam_static_tiny_used")),
        "pip_default_size": facecam_context.get("facecam_pip_default_size"),
        "audio_peak_growth_disabled": bool(facecam_context.get("facecam_audio_peak_growth_disabled")),
        "facecam_emphasis_big_disabled": bool(facecam_context.get("facecam_emphasis_big_disabled")),
        "reaction_size_events_used": bool(facecam_context.get("reaction_size_events_used")),
        "reaction_size_events_count": int(facecam_context.get("reaction_size_events_count") or 0),
        "reaction_size_events_path": (
            str(reaction_size_events_path)
            if size_events_requested
            else None
        ),
        "reaction_size_prominence_floor": (
            reaction_size_payload.get("prominence_floor")
            if isinstance(reaction_size_payload, dict)
            else None
        ),
        "reaction_size_prominence_percentile": (
            reaction_size_payload.get("prominence_percentile")
            if isinstance(reaction_size_payload, dict)
            else None
        ),
        "reaction_size_mode": (
            reaction_size_payload.get("size_event_mode")
            if isinstance(reaction_size_payload, dict)
            else None
        ),
        "reaction_signal_windows_path": (
            reaction_size_payload.get("reaction_signal_windows_path")
            if isinstance(reaction_size_payload, dict)
            else None
        ),
        "raw_owner_loudness_trigger_enabled": (
            bool(reaction_size_payload.get("raw_owner_loudness_trigger_enabled"))
            if isinstance(reaction_size_payload, dict)
            else bool(args.enable_owner_loudness_size_events)
        ),
        "owner_loudness_thresholds": (
            reaction_size_payload.get("owner_loudness_thresholds")
            if isinstance(reaction_size_payload, dict)
            else None
        ),
        "owner_loudness_windows_path": (
            reaction_size_payload.get("owner_loudness_windows_path")
            if isinstance(reaction_size_payload, dict)
            else None
        ),
        "output_target": "1920x1080",
    }

    video_ok = (
        int(ffprobe["video"].get("width") or 0) == 1920
        and int(ffprobe["video"].get("height") or 0) == 1080
    )
    audio_ok = ffprobe["audio"].get("codec_type") == "audio" and int(ffprobe["audio"].get("channels") or 0) >= 1
    duration_ok = duration_delta <= 2.0
    segment_ok = bool(segment_check["exact_match"]) and bool(adapter_check.get("anti_overcut_preserved"))
    anti_ok = plan_anti_fail_count == 0 and segment_ok
    if size_events_requested:
        facecam_ok = (
            facecam["static_tiny_used"]
            and facecam["pip_default_size"] == {"width": 480, "height": 270}
            and facecam["audio_peak_growth_disabled"]
            and facecam["facecam_emphasis_big_disabled"]
            and facecam["reaction_size_events_used"]
            and facecam["reaction_size_events_count"] > 0
        )
    else:
        facecam_ok = (
            facecam["static_tiny_used"]
            and facecam["pip_default_size"] == {"width": 480, "height": 270}
            and facecam["audio_peak_growth_disabled"]
            and facecam["facecam_emphasis_big_disabled"]
        )

    report = {
        "stage": "hardcut",
        "plan_path": str(plan_path),
        "source_video": str(source_video),
        "render_a_video": str(render_a_video),
        "output_video_path": str(final_output),
        "context_path": str(context_path),
        "audio_filter_script": str(filter_script),
        "reaction_size_events_path": (
            str(reaction_size_events_path)
            if size_events_requested
            else None
        ),
        "reaction_size_events": reaction_size_payload,
        "ffprobe": ffprobe,
        "audio_mix": {
            "owner_stream": "1:a:0",
            "friend_stream": "1:a:1",
            "game_stream": "1:a:2",
            "owner_volume": args.owner_volume,
            "friend_volume": args.friend_volume,
            "game_volume": args.game_volume,
            "filter": "amix=inputs=3:duration=longest:normalize=0 + alimiter",
        },
        "audio_check": {
            "present": audio_ok,
            "channels": ffprobe["audio"].get("channels"),
            "sample_rate": ffprobe["audio"].get("sample_rate"),
            "channel_layout": ffprobe["audio"].get("channel_layout"),
        },
        "duration_check": {
            "expected_plan_duration_seconds": expected_duration,
            "actual_render_duration_seconds": actual_duration,
            "delta_seconds": duration_delta,
            "pass": duration_ok,
        },
        "adapter_check": adapter_check,
        "segment_check": segment_check,
        "anti_overcut": {
            "plan_anti_overcut_fail_count": plan_anti_fail_count,
            "rendered_segments_equal_final_plan": segment_ok,
            "pass": anti_ok,
        },
        "facecam": facecam,
        "overall_pass": bool(video_ok and audio_ok and duration_ok and segment_ok and anti_ok and facecam_ok),
    }

    report_json = out_dir / "combined_render_report.json"
    report_txt = out_dir / "combined_render_report.txt"
    _write_json(report_json, report)
    _write_report(report_txt, report)

    print("")
    print("COMBINED RENDER SUMMARY")
    print(f"output_video_path={final_output}")
    print(f"report_txt={report_txt}")
    print(f"report_json={report_json}")
    print(f"audio_filter_script={filter_script}")
    print(f"ffprobe_width_height={ffprobe['video'].get('width')}x{ffprobe['video'].get('height')}")
    print(f"expected_plan_duration_seconds={expected_duration}")
    print(f"actual_render_duration_seconds={actual_duration}")
    print(f"duration_delta_seconds={duration_delta}")
    print(f"audio_present={audio_ok}")
    print(f"audio_channels={ffprobe['audio'].get('channels')}")
    print(f"audio_sample_rate={ffprobe['audio'].get('sample_rate')}")
    print(f"segment_exact_match={segment_check['exact_match']}")
    print(f"anti_overcut_fail_count={plan_anti_fail_count}")
    print(f"facecam_static_tiny_used={facecam['static_tiny_used']}")
    print(f"facecam_pip_default_size={facecam['pip_default_size']}")
    print(f"reaction_size_events_used={facecam['reaction_size_events_used']}")
    print(f"reaction_size_events_count={facecam['reaction_size_events_count']}")
    print(f"reaction_size_events_path={facecam['reaction_size_events_path']}")
    print("audio_stream_mapping=[1:a:0 Owner] + [1:a:1 Friend] + [1:a:2 Game]")
    print(f"overall_pass={report['overall_pass']}")

    return 0 if report["overall_pass"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
