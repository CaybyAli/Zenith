from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any


FFMPEG_EXE = Path(r"D:\Tools\ffmpeg\bin\ffmpeg.exe")
FFPROBE_EXE = Path(r"D:\Tools\ffmpeg\bin\ffprobe.exe")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(str(value).strip().lstrip("\ufeff"))
    except Exception:
        return default
    return number if math.isfinite(number) else default


def find_segments(raw: Any) -> list[dict[str, Any]]:
    keys = ("timeline_segments", "segments", "selected_segments", "final_segments", "clips", "timeline")

    def looks(value: Any) -> bool:
        return isinstance(value, list) and value and isinstance(value[0], dict) and (
            any(key in value[0] for key in ("start_seconds", "start", "start_time"))
            and any(key in value[0] for key in ("end_seconds", "end", "end_time"))
        )

    if isinstance(raw, dict):
        for key in keys:
            if looks(raw.get(key)):
                return raw[key]
        for value in raw.values():
            if looks(value):
                return value
        for value in raw.values():
            if isinstance(value, dict):
                try:
                    return find_segments(value)
                except Exception:
                    pass
    raise RuntimeError("Keine Segmentliste gefunden")


def se(segment: dict[str, Any]) -> tuple[float, float]:
    return (
        safe_float(segment.get("start_seconds", segment.get("start", segment.get("start_time")))),
        safe_float(segment.get("end_seconds", segment.get("end", segment.get("end_time")))),
    )


def plan_duration(segments: list[dict[str, Any]]) -> float:
    return round(sum(max(0.0, se(segment)[1] - se(segment)[0]) for segment in segments), 3)


def _matches(a: float, b: float, tolerance: float = 0.05) -> bool:
    return abs(a - b) <= tolerance


def resolve_round_xfade_boundaries(
    *,
    plan: dict[str, Any],
    audit: dict[str, Any],
    xfade_seconds: float,
) -> list[dict[str, Any]]:
    segments = find_segments(plan)
    round_cuts = audit.get("round_transition_cuts") or []
    boundaries: list[dict[str, Any]] = []

    cumulative = [0.0]
    for segment in segments:
        start, end = se(segment)
        cumulative.append(cumulative[-1] + max(0.0, end - start))

    for cut in round_cuts:
        if str(cut.get("reason")) != "round_transition_tail_to_next_speech_onset":
            continue
        cut_start = safe_float(cut.get("start_seconds"))
        cut_end = safe_float(cut.get("end_seconds"))
        for index in range(len(segments) - 1):
            prev_start, prev_end = se(segments[index])
            next_start, next_end = se(segments[index + 1])
            if not (_matches(prev_end, cut_start) and _matches(next_start, cut_end)):
                continue
            if index == 0 or index + 1 >= len(segments) - 1:
                continue
            boundary_before_xfade = cumulative[index + 1]
            boundaries.append(
                {
                    "source_cut_start_seconds": round(cut_start, 3),
                    "source_cut_end_seconds": round(cut_end, 3),
                    "removed_gap_seconds": round(max(0.0, cut_end - cut_start), 3),
                    "reason": str(cut.get("reason")),
                    "segment_index_before": index + 1,
                    "segment_id_before": segments[index].get("segment_id"),
                    "segment_index_after": index + 2,
                    "segment_id_after": segments[index + 1].get("segment_id"),
                    "render_boundary_before_xfade_seconds": round(boundary_before_xfade, 3),
                    "render_boundary_after_prior_xfades_seconds": round(
                        boundary_before_xfade - (len(boundaries) * xfade_seconds),
                        3,
                    ),
                    "xfade_seconds": round(xfade_seconds, 3),
                    "video_transition": "xfade=fade",
                    "audio_transition": "acrossfade",
                }
            )
            break

    return boundaries


def expected_duration_with_overlaps(plan_duration_seconds: float, boundary_count: int, xfade_seconds: float) -> float:
    return round(plan_duration_seconds - (boundary_count * xfade_seconds), 3)


def build_xfade_filter(
    *,
    input_duration_seconds: float,
    boundary_times_seconds: list[float],
    xfade_seconds: float,
) -> str:
    boundaries = sorted(boundary_times_seconds)
    starts = [0.0] + boundaries
    ends = boundaries + [input_duration_seconds]
    lines: list[str] = []
    video_labels: list[str] = []
    audio_labels: list[str] = []
    chunk_lengths: list[float] = []

    for index, (start, end) in enumerate(zip(starts, ends)):
        length = max(0.0, end - start)
        if length <= xfade_seconds:
            raise ValueError(f"Chunk {index} too short for {xfade_seconds:.3f}s xfade")
        v_label = f"v{index}"
        a_label = f"a{index}"
        lines.append(
            f"[0:v]trim=start={start:.3f}:end={end:.3f},setpts=PTS-STARTPTS[{v_label}]"
        )
        lines.append(
            f"[0:a]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS[{a_label}]"
        )
        video_labels.append(v_label)
        audio_labels.append(a_label)
        chunk_lengths.append(length)

    current_v = video_labels[0]
    current_a = audio_labels[0]
    accumulated = chunk_lengths[0]
    for index in range(1, len(video_labels)):
        out_v = f"vx{index}"
        out_a = f"ax{index}"
        offset = accumulated - xfade_seconds
        lines.append(
            f"[{current_v}][{video_labels[index]}]"
            f"xfade=transition=fade:duration={xfade_seconds:.3f}:offset={offset:.3f}[{out_v}]"
        )
        lines.append(
            f"[{current_a}][{audio_labels[index]}]"
            f"acrossfade=d={xfade_seconds:.3f}:c1=tri:c2=tri[{out_a}]"
        )
        current_v = out_v
        current_a = out_a
        accumulated = accumulated + chunk_lengths[index] - xfade_seconds

    lines.append(f"[{current_v}]format=yuv420p[vout]")
    lines.append(f"[{current_a}]aformat=sample_rates=48000:channel_layouts=stereo[aout]")
    return ";\n".join(lines)


def ffprobe_duration(path: Path) -> float:
    cmd = [
        str(FFPROBE_EXE),
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(path),
    ]
    process = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if process.returncode != 0:
        raise RuntimeError(process.stderr)
    data = json.loads(process.stdout)
    return round(safe_float(data.get("format", {}).get("duration")), 3)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--audit", default="reports/semantic_content_layer/semantic_pacing_tighten_audit.json")
    parser.add_argument("--input", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--xfade-seconds", type=float, default=0.4)
    parser.add_argument("--report", default="reports/ranked_render/ranked_cut_v14_round_xfade_report.json")
    args = parser.parse_args()

    plan_path = Path(args.plan)
    audit_path = Path(args.audit)
    input_video = Path(args.input)
    output_video = Path(args.out)
    report_path = Path(args.report)

    plan = read_json(plan_path)
    audit = read_json(audit_path)
    segments = find_segments(plan)
    hardcut_duration = ffprobe_duration(input_video)
    xfade_seconds = max(0.001, float(args.xfade_seconds))
    boundaries = resolve_round_xfade_boundaries(plan=plan, audit=audit, xfade_seconds=xfade_seconds)

    output_video.parent.mkdir(parents=True, exist_ok=True)
    if not boundaries:
        shutil.copy2(input_video, output_video)
        report = {
            "stage": "final_xfade",
            "input_video": str(input_video),
            "output_video": str(output_video),
            "xfade_seconds": xfade_seconds,
            "boundaries": [],
            "total_overlap_seconds": 0.0,
            "video_crossfade": False,
            "audio_acrossfade": False,
            "expected_duration_seconds": hardcut_duration,
            "actual_duration_seconds": ffprobe_duration(output_video),
        }
        _write = report_path.write_text
        report_path.parent.mkdir(parents=True, exist_ok=True)
        _write(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return 0

    boundary_times = [safe_float(item["render_boundary_before_xfade_seconds"]) for item in boundaries]
    filter_complex = build_xfade_filter(
        input_duration_seconds=hardcut_duration,
        boundary_times_seconds=boundary_times,
        xfade_seconds=xfade_seconds,
    )
    filter_script = output_video.with_suffix(".round_xfade.ffscript")
    filter_script.write_text(filter_complex + ";\n", encoding="utf-8")

    cmd = [
        str(FFMPEG_EXE),
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(input_video),
        "-filter_complex_script",
        str(filter_script),
        "-map",
        "[vout]",
        "-map",
        "[aout]",
        "-c:v",
        "h264_nvenc",
        "-preset",
        "p5",
        "-cq",
        "19",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-ar",
        "48000",
        "-ac",
        "2",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(output_video),
    ]
    process = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if process.returncode != 0:
        print(process.stdout)
        print(process.stderr)
        raise SystemExit(process.returncode)

    expected_plan_duration = plan_duration(segments)
    total_overlap = round(len(boundaries) * xfade_seconds, 3)
    expected_final = expected_duration_with_overlaps(expected_plan_duration, len(boundaries), xfade_seconds)
    actual_duration = ffprobe_duration(output_video)
    report = {
        "stage": "final_xfade",
        "input_video": str(input_video),
        "output_video": str(output_video),
        "plan_path": str(plan_path),
        "audit_path": str(audit_path),
        "filter_script": str(filter_script),
        "command": cmd,
        "xfade_seconds": round(xfade_seconds, 3),
        "boundaries": boundaries,
        "boundary_count": len(boundaries),
        "total_overlap_seconds": total_overlap,
        "hardcut_duration_seconds": hardcut_duration,
        "plan_duration_seconds": expected_plan_duration,
        "expected_duration_seconds": expected_final,
        "actual_duration_seconds": actual_duration,
        "duration_delta_seconds": round(abs(actual_duration - expected_final), 3),
        "video_crossfade": True,
        "audio_acrossfade": True,
        "encoder": "h264_nvenc",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
