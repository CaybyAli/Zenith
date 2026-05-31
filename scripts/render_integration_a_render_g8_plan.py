from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from types import SimpleNamespace
from typing import Any

from core.ffmpeg_helper import get_ffprobe_path
from core.final_render_driver import FinalRenderDriver
from core.g8_render_timeline_adapter import (
    build_edit_timeline_from_g8_plan,
    compare_timeline_to_g8_plan,
    load_g8_timeline_plan,
)
from core.power_profile import PowerProfile
from shared.enums import ChannelType


class RenderIntegrationJob(SimpleNamespace):
    def touch(self) -> None:
        return None


def _ffprobe_video(path: Path) -> dict[str, Any]:
    cmd = [
        get_ffprobe_path(),
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-show_entries", "format=duration",
        "-of", "json",
        str(path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-1000:])

    data = json.loads(result.stdout)
    stream = data["streams"][0]
    fmt = data["format"]
    return {
        "width": int(stream["width"]),
        "height": int(stream["height"]),
        "duration_seconds": round(float(fmt["duration"]), 3),
    }


def _compare_context_to_plan(context: dict[str, Any], plan: dict[str, Any]) -> dict[str, Any]:
    plan_segments = plan.get("timeline_segments") or []
    render_segments = context.get("segments") or []

    deviations = []
    matched = 0
    for index, plan_seg in enumerate(plan_segments):
        if index >= len(render_segments):
            deviations.append({"index": index, "reason": "missing_in_context", "plan": plan_seg})
            continue

        ctx_seg = render_segments[index]
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

    if len(render_segments) > len(plan_segments):
        deviations.append({
            "reason": "extra_context_segments",
            "extra_count": len(render_segments) - len(plan_segments),
        })

    return {
        "plan_segment_count": len(plan_segments),
        "render_context_segment_count": len(render_segments),
        "matched_segments": matched,
        "deviation_count": len(deviations),
        "deviations": deviations,
        "exact_match": len(deviations) == 0 and matched == len(plan_segments),
    }


def _write_text_report(report: dict[str, Any], path: Path) -> None:
    lines = []
    lines.append("RENDER INTEGRATION A REPORT")
    lines.append("")
    lines.append(f"plan_path: {report['plan_path']}")
    lines.append(f"source_video: {report['source_video']}")
    lines.append(f"output_video_path: {report['output_video_path']}")
    lines.append("")
    lines.append("ffprobe:")
    for k, v in report["ffprobe"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("duration:")
    for k, v in report["duration_check"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("segment_check:")
    for k, v in report["segment_check"].items():
        if k != "deviations":
            lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("anti_overcut:")
    for k, v in report["anti_overcut"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("facecam:")
    for k, v in report["facecam"].items():
        lines.append(f"- {k}: {v}")
    lines.append("")
    lines.append("audio_note:")
    lines.append("- Existing audio render path used. Audio track correctness is not final in this group.")
    lines.append("")
    lines.append(f"overall_pass: {report['overall_pass']}")
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--plan", required=True)
    parser.add_argument("--video", required=True)
    parser.add_argument("--output-dir", default="output/render_integration_a")
    args = parser.parse_args()

    plan_path = Path(args.plan)
    video_path = Path(args.video)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not video_path.exists():
        raise FileNotFoundError(video_path)

    plan = load_g8_timeline_plan(plan_path)
    label = str(plan.get("label") or plan_path.stem)
    job_id = f"render_integration_a_{label}"

    timeline = build_edit_timeline_from_g8_plan(
        job_id=job_id,
        plan_path=plan_path,
    )
    adapter_check = compare_timeline_to_g8_plan(
        timeline=timeline,
        plan_data=plan,
    )

    job = RenderIntegrationJob(
        job_id=job_id,
        raw_video_path=str(video_path),
        channel_type=ChannelType.GAMING_MAIN,
        power_profile=PowerProfile.BALANCED,
        focus_decisions=[],
        profanity_censor_matches=[],
        profanity_censor_report={},
    )

    print("RENDER INTEGRATION A - REAL RENDER")
    print(f"plan: {plan_path}")
    print(f"video: {video_path}")
    print(f"segments: {len(timeline.selected_segments)}")
    print(f"plan_duration_seconds: {timeline.total_selected_duration}")
    print("facecam_static_tiny: True")
    print("audio_note: existing audio path, not final audio-track config")
    print("")

    output_path = Path(
        FinalRenderDriver().render(
            job=job,
            source_path=video_path,
            edit_timeline=timeline,
            reframe_plan=None,
            dynamic_edit_plan=None,
            output_dir=output_dir,
            facecam_static_tiny=True,
        )
    )

    context_path = output_dir / f"{job_id}_final_render_driver_context.json"
    context = json.loads(context_path.read_text(encoding="utf-8"))
    ffprobe = _ffprobe_video(output_path)

    context_segment_check = _compare_context_to_plan(context, plan)
    expected_duration = round(float(timeline.total_selected_duration), 3)
    actual_duration = round(float(ffprobe["duration_seconds"]), 3)
    duration_delta = round(abs(actual_duration - expected_duration), 3)

    anti = plan.get("anti_overcut_audit") or {}
    anti_fail_count = int(anti.get("fail_count") or 0)

    facecam = {
        "static_tiny_used": bool(context.get("facecam_static_tiny_used")),
        "pip_default_size": context.get("facecam_pip_default_size"),
        "audio_peak_growth_disabled": bool(context.get("facecam_audio_peak_growth_disabled")),
        "facecam_emphasis_big_disabled": bool(context.get("facecam_emphasis_big_disabled")),
        "gameplay_main_output": "1920x1080",
    }

    duration_ok = duration_delta <= 2.0
    size_ok = ffprobe["width"] == 1920 and ffprobe["height"] == 1080
    segment_ok = bool(context_segment_check["exact_match"]) and bool(adapter_check["anti_overcut_preserved"])
    facecam_ok = (
        facecam["static_tiny_used"]
        and facecam["pip_default_size"] == {"width": 480, "height": 270}
        and facecam["audio_peak_growth_disabled"]
        and facecam["facecam_emphasis_big_disabled"]
    )
    anti_ok = anti_fail_count == 0 and segment_ok

    report = {
        "stage": "render_integration_a_g8_plan_to_render_static_tiny_facecam",
        "plan_path": str(plan_path),
        "source_video": str(video_path),
        "output_video_path": str(output_path),
        "context_path": str(context_path),
        "ffprobe": ffprobe,
        "duration_check": {
            "expected_plan_duration_seconds": expected_duration,
            "actual_render_duration_seconds": actual_duration,
            "delta_seconds": duration_delta,
            "pass": duration_ok,
        },
        "adapter_check": adapter_check,
        "segment_check": context_segment_check,
        "anti_overcut": {
            "plan_anti_overcut_fail_count": anti_fail_count,
            "rendered_segments_equal_g8_plan": segment_ok,
            "no_plan_active_play_missing": segment_ok,
            "pass": anti_ok,
        },
        "facecam": facecam,
        "audio_note": "Existing audio render path used. Audio track correctness is not final in this group.",
        "overall_pass": bool(size_ok and duration_ok and segment_ok and facecam_ok and anti_ok),
    }

    report_json = Path("reports/render_integration_a/render_integration_a_report.json")
    report_txt = Path("reports/render_integration_a/render_integration_a_report.txt")
    report_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    _write_text_report(report, report_txt)

    print("")
    print("RENDER INTEGRATION A SUMMARY")
    print(f"output_video_path: {output_path}")
    print(f"context_path: {context_path}")
    print(f"report_json: {report_json}")
    print(f"ffprobe_width_height: {ffprobe['width']}x{ffprobe['height']}")
    print(f"expected_plan_duration_seconds: {expected_duration}")
    print(f"actual_render_duration_seconds: {actual_duration}")
    print(f"duration_delta_seconds: {duration_delta}")
    print(f"segment_exact_match: {context_segment_check['exact_match']}")
    print(f"anti_overcut_fail_count: {anti_fail_count}")
    print(f"facecam_static_tiny_used: {facecam['static_tiny_used']}")
    print(f"facecam_pip_default_size: {facecam['pip_default_size']}")
    print(f"audio_peak_growth_disabled: {facecam['audio_peak_growth_disabled']}")
    print(f"facecam_emphasis_big_disabled: {facecam['facecam_emphasis_big_disabled']}")
    print(f"overall_pass: {report['overall_pass']}")

    return 0 if report["overall_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
