from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.ffmpeg_helper import get_ffmpeg_path, get_ffprobe_path
from core.final_render_driver import FinalRenderDriver
from core.smooth_zoom_engine import ZoomCurve, ZoomKeyframe
from models.edit_timeline import EditTimeline
from models.framing_instruction import FramingInstruction
from models.reframe_plan import ReframePlan
from models.timeline_segment import TimelineSegment


ROOT = Path("reports/phase4_8/b5_manual/real_sample_render")
ROOT.mkdir(parents=True, exist_ok=True)

SOURCE = Path(r"D:\Zenith\tests\Rocket League Neuer Test58.mp4")
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROOF_JSON = Path("reports/phase4_8/b5_manual/03_real_sample_render_proof.json")
PROOF_TXT = Path("reports/phase4_8/b5_manual/03_real_sample_render_proof.txt")


def run(cmd: list[str]) -> subprocess.CompletedProcess:
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            + " ".join(cmd)
            + "\n\nSTDOUT:\n"
            + result.stdout[-1200:]
            + "\n\nSTDERR:\n"
            + result.stderr[-1200:]
        )
    return result


def probe_json(path: Path) -> dict:
    ffprobe = get_ffprobe_path()
    result = run([
        ffprobe,
        "-v", "error",
        "-show_entries", "stream=index,codec_type,width,height,r_frame_rate,channels,duration:format=duration,size,bit_rate",
        "-of", "json",
        str(path),
    ])
    return json.loads(result.stdout)


def segment(segment_id: str, start: float, end: float, role: str) -> TimelineSegment:
    return TimelineSegment(
        segment_id=segment_id,
        job_id="p4_8_b5_real_sample",
        candidate_id=None,
        start_time=start,
        end_time=end,
        segment_role=role,
        selection_score=1.0,
    )


def build_reframe_plan(segments: list[TimelineSegment]) -> ReframePlan:
    return ReframePlan(
        plan_id="p4_8_b5_reframe",
        job_id="p4_8_b5_real_sample",
        timeline_id="p4_8_b5_timeline",
        source_aspect_ratio="32:9",
        primary_target_aspect_ratio="16:9",
        instructions=[
            FramingInstruction(
                instruction_id=f"frame_{s.segment_id}",
                job_id="p4_8_b5_real_sample",
                timeline_id="p4_8_b5_timeline",
                segment_id=s.segment_id,
                focus_kind="balanced",
                layout_kind="balanced_split",
                source_aspect_ratio="32:9",
                target_aspect_ratio="16:9",
                crop_window={"x": 0.5, "y": 0.0, "width": 0.5, "height": 1.0},
            )
            for s in segments
        ],
        plan_score=1.0,
    )


def extract_frame(video: Path, timestamp: float, name: str) -> str:
    ffmpeg = get_ffmpeg_path()
    out = ROOT / f"{name}.png"
    run([
        ffmpeg,
        "-y",
        "-ss", f"{timestamp:.3f}",
        "-i", str(video),
        "-frames:v", "1",
        str(out),
    ])
    return str(out)


def main() -> None:
    if not SOURCE.exists():
        raise FileNotFoundError(SOURCE)

    segments = [
        segment("seg_gameplay_focus", 0.0, 3.0, "gameplay_focus"),
        segment("seg_facecam_focus", 10.0, 13.0, "facecam_focus"),
        segment("seg_balanced_pip", 20.0, 23.0, "balanced"),
    ]

    timeline = EditTimeline(
        timeline_id="p4_8_b5_timeline",
        job_id="p4_8_b5_real_sample",
        target_duration=9.0,
        selected_segments=segments,
        timeline_score=1.0,
    )

    job = SimpleNamespace(
        job_id="p4_8_b5_real_sample",
        power_profile="eco",
        focus_decisions=[
            {"timestamp": 1.5, "focus_target": "gameplay", "confidence": 0.95, "reasoning": "b5_real_gameplay"},
            {"timestamp": 11.5, "focus_target": "facecam", "confidence": 0.95, "reasoning": "b5_real_facecam"},
            {"timestamp": 21.5, "focus_target": "balanced", "confidence": 0.95, "reasoning": "b5_real_balanced"},
        ],
        profanity_censor_matches=[],
        profanity_censor_report={},
    )

    curve = ZoomCurve([
        ZoomKeyframe(0.0, 1.0, "balanced", "linear"),
        ZoomKeyframe(1.5, 1.35, "gameplay", "linear"),
        ZoomKeyframe(3.0, 1.0, "balanced", "linear"),
        ZoomKeyframe(10.0, 1.0, "balanced", "linear"),
        ZoomKeyframe(11.5, 1.6, "facecam", "linear"),
        ZoomKeyframe(13.0, 1.0, "balanced", "linear"),
        ZoomKeyframe(20.0, 1.0, "balanced", "linear"),
        ZoomKeyframe(23.0, 1.0, "balanced", "linear"),
    ])

    final_path = Path(FinalRenderDriver().render(
        job=job,
        source_path=SOURCE,
        edit_timeline=timeline,
        reframe_plan=build_reframe_plan(segments),
        dynamic_edit_plan=None,
        smooth_zoom_curve=curve,
        output_dir=OUTPUT_DIR,
    ))

    context_path = OUTPUT_DIR / "p4_8_b5_real_sample_final_render_driver_context.json"
    context = json.loads(context_path.read_text(encoding="utf-8"))

    frames = {
        "gameplay_focus_output_t1": extract_frame(final_path, 1.0, "frame_01_gameplay_focus_output_t1"),
        "facecam_focus_output_t4": extract_frame(final_path, 4.0, "frame_02_facecam_focus_output_t4"),
        "balanced_pip_output_t7": extract_frame(final_path, 7.0, "frame_03_balanced_pip_output_t7"),
    }

    output_probe = probe_json(final_path)

    streams = output_probe.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})
    duration = float(output_probe.get("format", {}).get("duration", 0.0) or 0.0)

    checks = {
        "source_exists": SOURCE.exists(),
        "output_exists": final_path.exists(),
        "context_exists": context_path.exists(),
        "output_is_1920x1080": video_stream.get("width") == 1920 and video_stream.get("height") == 1080,
        "output_duration_near_9s": 8.5 <= duration <= 9.8,
        "output_has_audio": bool(audio_stream),
        "focus_decisions_used": bool(context.get("focus_decisions_used")),
        "smooth_zoom_used": bool(context.get("smooth_zoom_used")),
        "layout_counts_ok": context.get("render_layout_counts") == {
            "balanced_split": 1,
            "facecam_emphasis": 1,
            "gameplay_crop": 1,
        },
    }

    proof = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "source": str(SOURCE),
        "final_output": str(final_path),
        "context_path": str(context_path),
        "frames": frames,
        "checks": checks,
        "output_probe": output_probe,
        "render_layout_counts": context.get("render_layout_counts"),
        "focus_decisions_used": context.get("focus_decisions_used"),
        "smooth_zoom_used": context.get("smooth_zoom_used"),
        "smooth_zoom_records": context.get("smooth_zoom_records"),
        "resolved_render_layouts": context.get("resolved_render_layouts"),
    }

    PROOF_JSON.write_text(json.dumps(proof, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    PROOF_TXT.write_text(
        "\n".join([
            f"STATUS={proof['status']}",
            f"SOURCE={SOURCE}",
            f"OUTPUT={final_path}",
            f"CONTEXT={context_path}",
            f"OUTPUT_DURATION_SECONDS={duration:.3f}",
            f"OUTPUT_VIDEO={video_stream.get('width')}x{video_stream.get('height')}",
            f"OUTPUT_HAS_AUDIO={bool(audio_stream)}",
            f"LAYOUT_COUNTS={context.get('render_layout_counts')}",
            f"FOCUS_DECISIONS_USED={context.get('focus_decisions_used')}",
            f"SMOOTH_ZOOM_USED={context.get('smooth_zoom_used')}",
        ]) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(proof, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
