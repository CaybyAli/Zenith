from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from core.ffmpeg_helper import get_ffmpeg_path
from core.final_render_driver import FinalRenderDriver
from core.smooth_zoom_engine import ZoomCurve, ZoomKeyframe
from models.edit_timeline import EditTimeline
from models.framing_instruction import FramingInstruction
from models.reframe_plan import ReframePlan
from models.timeline_segment import TimelineSegment


ROOT = Path("reports/phase4_8/b4_manual/mini_render")
ROOT.mkdir(parents=True, exist_ok=True)

SOURCE = ROOT / "synthetic_32x9_red_facecam_blue_gameplay.mp4"
OUTPUT_DIR = ROOT / "output"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

PROOF_JSON = Path("reports/phase4_8/b4_manual/03_mini_render_visual_proof.json")
PROOF_TXT = Path("reports/phase4_8/b4_manual/03_mini_render_visual_proof.txt")


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


def build_source_video() -> None:
    ffmpeg = get_ffmpeg_path()
    cmd = [
        ffmpeg,
        "-y",
        "-f", "lavfi",
        "-i", "color=c=red:s=1920x1080:r=30:d=6",
        "-f", "lavfi",
        "-i", "color=c=blue:s=1920x1080:r=30:d=6",
        "-f", "lavfi",
        "-i", "sine=frequency=800:sample_rate=48000:duration=6",
        "-filter_complex", "[0:v][1:v]hstack=inputs=2[v]",
        "-map", "[v]",
        "-map", "2:a",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "128k",
        str(SOURCE),
    ]
    run(cmd)


def segment(segment_id: str, start: float, end: float, role: str) -> TimelineSegment:
    return TimelineSegment(
        segment_id=segment_id,
        job_id="p4_8_b4_mini_render",
        candidate_id=None,
        start_time=start,
        end_time=end,
        segment_role=role,
        selection_score=1.0,
    )


def reframe_plan(segments: list[TimelineSegment]) -> ReframePlan:
    return ReframePlan(
        plan_id="p4_8_b4_reframe",
        job_id="p4_8_b4_mini_render",
        timeline_id="p4_8_b4_timeline",
        source_aspect_ratio="32:9",
        primary_target_aspect_ratio="16:9",
        instructions=[
            FramingInstruction(
                instruction_id=f"frame_{s.segment_id}",
                job_id="p4_8_b4_mini_render",
                timeline_id="p4_8_b4_timeline",
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


def sample_rgb(video: Path, timestamp: float, x: int, y: int) -> tuple[int, int, int]:
    ffmpeg = get_ffmpeg_path()
    cmd = [
        ffmpeg,
        "-v", "error",
        "-ss", f"{timestamp:.3f}",
        "-i", str(video),
        "-frames:v", "1",
        "-vf", f"crop=1:1:{x}:{y},format=rgb24",
        "-f", "rawvideo",
        "-",
    ]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0 or len(result.stdout) < 3:
        raise RuntimeError(result.stderr.decode("utf-8", errors="replace")[-1200:])
    return tuple(result.stdout[:3])  # type: ignore[return-value]


def classify(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    if r >= 140 and b <= 130:
        return "red"
    if b >= 140 and r <= 130:
        return "blue"
    return "other"


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
    build_source_video()

    segments = [
        segment("seg_gameplay_focus", 0.0, 2.0, "gameplay_focus"),
        segment("seg_facecam_focus", 2.0, 4.0, "facecam_focus"),
        segment("seg_balanced_pip", 4.0, 6.0, "balanced"),
    ]

    timeline = EditTimeline(
        timeline_id="p4_8_b4_timeline",
        job_id="p4_8_b4_mini_render",
        target_duration=6.0,
        selected_segments=segments,
        timeline_score=1.0,
    )

    job = SimpleNamespace(
        job_id="p4_8_b4_mini_render",
        power_profile="eco",
        focus_decisions=[
            {"timestamp": 0.7, "focus_target": "gameplay", "confidence": 0.95, "reasoning": "b4_visual_gameplay"},
            {"timestamp": 2.7, "focus_target": "facecam", "confidence": 0.95, "reasoning": "b4_visual_facecam"},
            {"timestamp": 4.7, "focus_target": "balanced", "confidence": 0.95, "reasoning": "b4_visual_balanced"},
        ],
        profanity_censor_matches=[],
        profanity_censor_report={},
    )

    curve = ZoomCurve([
        ZoomKeyframe(0.0, 1.0, "balanced", "linear"),
        ZoomKeyframe(1.0, 1.5, "gameplay", "linear"),
        ZoomKeyframe(2.0, 1.0, "balanced", "linear"),
        ZoomKeyframe(3.0, 2.0, "facecam", "linear"),
        ZoomKeyframe(4.0, 1.0, "balanced", "linear"),
        ZoomKeyframe(5.0, 1.0, "balanced", "linear"),
        ZoomKeyframe(6.0, 1.0, "balanced", "linear"),
    ])

    final_path = Path(FinalRenderDriver().render(
        job=job,
        source_path=SOURCE,
        edit_timeline=timeline,
        reframe_plan=reframe_plan(segments),
        dynamic_edit_plan=None,
        smooth_zoom_curve=curve,
        output_dir=OUTPUT_DIR,
    ))

    context_path = OUTPUT_DIR / "p4_8_b4_mini_render_final_render_driver_context.json"
    context = json.loads(context_path.read_text(encoding="utf-8"))

    samples = {
        "gameplay_focus_center_t1": {
            "rgb": sample_rgb(final_path, 1.0, 960, 540),
            "expected": "blue",
        },
        "facecam_focus_center_t3": {
            "rgb": sample_rgb(final_path, 3.0, 960, 540),
            "expected": "red",
        },
        "balanced_center_t5": {
            "rgb": sample_rgb(final_path, 5.0, 960, 540),
            "expected": "blue",
        },
        "balanced_pip_t5": {
            "rgb": sample_rgb(final_path, 5.0, 50, 120),
            "expected": "red",
        },
    }

    for item in samples.values():
        item["actual"] = classify(item["rgb"])
        item["passed"] = item["actual"] == item["expected"]

    frames = {
        "gameplay_focus": extract_frame(final_path, 1.0, "frame_01_gameplay_focus"),
        "facecam_focus": extract_frame(final_path, 3.0, "frame_02_facecam_focus"),
        "balanced_pip": extract_frame(final_path, 5.0, "frame_03_balanced_pip"),
    }

    checks = {
        "output_exists": final_path.exists(),
        "context_exists": context_path.exists(),
        "focus_decisions_used": bool(context.get("focus_decisions_used")),
        "smooth_zoom_used": bool(context.get("smooth_zoom_used")),
        "layout_counts_ok": context.get("render_layout_counts") == {
            "balanced_split": 1,
            "facecam_emphasis": 1,
            "gameplay_crop": 1,
        },
        "all_color_samples_passed": all(bool(item["passed"]) for item in samples.values()),
    }

    proof = {
        "status": "PASS" if all(checks.values()) else "FAIL",
        "source": str(SOURCE),
        "final_output": str(final_path),
        "context_path": str(context_path),
        "frames": frames,
        "checks": checks,
        "render_layout_counts": context.get("render_layout_counts"),
        "focus_decisions_used": context.get("focus_decisions_used"),
        "smooth_zoom_used": context.get("smooth_zoom_used"),
        "smooth_zoom_records": context.get("smooth_zoom_records"),
        "samples": samples,
    }

    PROOF_JSON.write_text(json.dumps(proof, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    PROOF_TXT.write_text(
        "\n".join([
            f"STATUS={proof['status']}",
            f"OUTPUT={final_path}",
            f"CONTEXT={context_path}",
            f"LAYOUT_COUNTS={context.get('render_layout_counts')}",
            f"FOCUS_DECISIONS_USED={context.get('focus_decisions_used')}",
            f"SMOOTH_ZOOM_USED={context.get('smooth_zoom_used')}",
            f"ALL_COLOR_SAMPLES_PASSED={checks['all_color_samples_passed']}",
        ]) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(proof, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
