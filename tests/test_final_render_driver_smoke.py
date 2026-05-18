from __future__ import annotations

import json
import os
import shutil
import subprocess

from core.ffmpeg_helper import get_ffmpeg_path

import pytest

from moviepy import VideoFileClip

from core.final_render_driver import FinalRenderDriver
from models.dynamic_edit_plan import DynamicEditPlan
from models.edit_timeline import EditTimeline
from models.framing_instruction import FramingInstruction
from models.reframe_plan import ReframePlan
from models.timeline_segment import TimelineSegment
from models.zoom_instruction import ZoomInstruction


# ------------------------------------------------------------------ #
#  Fixtures                                                            #
# ------------------------------------------------------------------ #

def _make_source_video(path: str, duration: int = 30) -> None:
    """Synthetic test video using FFmpeg lavfi sources (no GPU needed)."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    cmd = [
        get_ffmpeg_path(),
        "-y",
        "-f", "lavfi", "-i", f"testsrc=size=1920x1080:rate=30:duration={duration}",
        "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=44100:duration={duration}",
        "-c:v", "libx264", "-preset", "ultrafast",
        "-c:a", "aac",
        path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def _make_job(job_id: str, raw_video_path: str):
    from types import SimpleNamespace
    from shared.enums import ChannelType
    return SimpleNamespace(
        job_id=job_id,
        raw_video_path=raw_video_path,
        channel_type=ChannelType.GAMING_MAIN,
    )


def _make_timeline(job_id: str) -> EditTimeline:
    segments = [
        TimelineSegment(
            segment_id="seg_hook_001",
            job_id=job_id,
            candidate_id=None,
            start_time=2.0,
            end_time=7.0,
            segment_role="hook",
            selection_score=0.91,
        ),
        TimelineSegment(
            segment_id="seg_build_001",
            job_id=job_id,
            candidate_id=None,
            start_time=10.0,
            end_time=17.0,
            segment_role="build",
            selection_score=0.78,
        ),
        TimelineSegment(
            segment_id="seg_payoff_001",
            job_id=job_id,
            candidate_id=None,
            start_time=22.0,
            end_time=28.0,
            segment_role="payoff",
            selection_score=0.85,
        ),
    ]
    return EditTimeline(
        timeline_id="timeline_smoke_001",
        job_id=job_id,
        target_duration=18.0,
        selected_segments=segments,
        hook_segment_id="seg_hook_001",
        peak_segment_ids=[],
        payoff_segment_id="seg_payoff_001",
        timeline_score=0.85,
    )


def _make_reframe_plan(job_id: str) -> ReframePlan:
    # Normalised crop: take the centre 80 % horizontally, full height
    instructions = [
        FramingInstruction(
            instruction_id="fi_hook_001",
            job_id=job_id,
            timeline_id="timeline_smoke_001",
            segment_id="seg_hook_001",
            focus_kind="gameplay",
            layout_kind="full_gameplay",
            source_aspect_ratio="16:9",
            target_aspect_ratio="16:9",
            crop_window={"x": 0.10, "y": 0.0, "width": 0.80, "height": 1.0},
        ),
        FramingInstruction(
            instruction_id="fi_payoff_001",
            job_id=job_id,
            timeline_id="timeline_smoke_001",
            segment_id="seg_payoff_001",
            focus_kind="action",
            layout_kind="full_gameplay",
            source_aspect_ratio="16:9",
            target_aspect_ratio="16:9",
            crop_window={"x": 0.05, "y": 0.05, "width": 0.90, "height": 0.90},
        ),
    ]
    return ReframePlan(
        plan_id="reframe_smoke_001",
        job_id=job_id,
        timeline_id="timeline_smoke_001",
        source_aspect_ratio="16:9",
        primary_target_aspect_ratio="16:9",
        instructions=instructions,
        plan_score=0.82,
    )


def _make_dynamic_edit_plan(job_id: str) -> DynamicEditPlan:
    zoom_instrs = [
        ZoomInstruction(
            instruction_id="zoom_build_001",
            job_id=job_id,
            timeline_id="timeline_smoke_001",
            segment_id="seg_build_001",
            moment_id=None,
            zoom_kind="in",
            focus_kind="action",
            intensity=0.6,
            start_time=10.0,
            end_time=17.0,
        ),
    ]
    return DynamicEditPlan(
        plan_id="dep_smoke_001",
        job_id=job_id,
        timeline_id="timeline_smoke_001",
        zoom_instructions=zoom_instrs,
        plan_score=0.75,
    )


# ------------------------------------------------------------------ #
#  Tests                                                               #
# ------------------------------------------------------------------ #

@pytest.mark.ffmpeg_integration
def test_basic_render_consumes_timeline() -> None:
    """Driver must produce a file whose duration equals segment sum, not 60 s."""
    test_dir = os.path.join("tmp", "final_render_driver_smoke_basic")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    source_path = os.path.join(test_dir, "source.mp4")
    _make_source_video(source_path, duration=30)

    job = _make_job("job_frd_basic_001", source_path)
    timeline = _make_timeline(job.job_id)

    expected_duration = timeline.total_selected_duration  # 5 + 7 + 6 = 18.0 s

    output_path = FinalRenderDriver().render(
        job=job,
        source_path=source_path,
        edit_timeline=timeline,
        output_dir=test_dir,
    )

    assert os.path.exists(output_path), f"Output not found: {output_path}"

    with VideoFileClip(output_path) as clip:
        actual_duration = float(clip.duration or 0.0)

    # Allow Â±1 s tolerance for codec rounding
    assert abs(actual_duration - expected_duration) <= 1.0, (
        f"Duration mismatch: expected ~{expected_duration:.1f}s, "
        f"got {actual_duration:.3f}s  (NOT the hardcoded 60 s)"
    )

    # Context JSON
    context_path = os.path.join(test_dir, f"{job.job_id}_final_render_driver_context.json")
    assert os.path.exists(context_path)
    with open(context_path, encoding="utf-8") as f:
        ctx = json.load(f)

    assert ctx["segments_count"] == 3
    assert ctx["codec_video"] == "h264_nvenc"
    assert ctx["reframe_plan_used"] is False

    roles = [s["role"] for s in ctx["segments"]]
    assert roles == ["hook", "build", "payoff"]

    print(f"\n[PASS] test_basic_render_consumes_timeline")
    print(f"  expected={expected_duration:.1f}s  actual={actual_duration:.3f}s")


@pytest.mark.ffmpeg_integration
def test_render_with_reframe_and_zoom() -> None:
    """Driver must apply crop + zoom without errors and still honour segment durations."""
    test_dir = os.path.join("tmp", "final_render_driver_smoke_layers")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    source_path = os.path.join(test_dir, "source.mp4")
    _make_source_video(source_path, duration=30)

    job = _make_job("job_frd_layers_001", source_path)
    timeline = _make_timeline(job.job_id)
    reframe_plan = _make_reframe_plan(job.job_id)
    dynamic_edit_plan = _make_dynamic_edit_plan(job.job_id)

    expected_duration = timeline.total_selected_duration  # 18.0 s

    output_path = FinalRenderDriver().render(
        job=job,
        source_path=source_path,
        edit_timeline=timeline,
        reframe_plan=reframe_plan,
        dynamic_edit_plan=dynamic_edit_plan,
        output_dir=test_dir,
    )

    assert os.path.exists(output_path)

    with VideoFileClip(output_path) as clip:
        actual_duration = float(clip.duration or 0.0)
        actual_w = clip.w
        actual_h = clip.h

    assert abs(actual_duration - expected_duration) <= 1.0, (
        f"Duration mismatch: expected ~{expected_duration:.1f}s, got {actual_duration:.3f}s"
    )
    assert actual_w == 1920, f"Expected width=1920, got {actual_w}"
    assert actual_h == 1080, f"Expected height=1080, got {actual_h}"

    context_path = os.path.join(test_dir, f"{job.job_id}_final_render_driver_context.json")
    with open(context_path, encoding="utf-8") as f:
        ctx = json.load(f)

    assert ctx["reframe_plan_used"] is True
    assert ctx["reframe_instructions_count"] == 2
    assert ctx["dynamic_edit_plan_used"] is True
    assert ctx["zoom_instructions_count"] == 1

    print(f"\n[PASS] test_render_with_reframe_and_zoom")
    print(
        f"  duration={actual_duration:.3f}s  "
        f"resolution={actual_w}x{actual_h}  "
        f"reframe_instrs={ctx['reframe_instructions_count']}  "
        f"zoom_instrs={ctx['zoom_instructions_count']}"
    )


@pytest.mark.ffmpeg_integration
def test_single_segment_renders_without_concat() -> None:
    """A single-segment timeline must render cleanly (no concat filter needed)."""
    test_dir = os.path.join("tmp", "final_render_driver_smoke_single")
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir, exist_ok=True)

    source_path = os.path.join(test_dir, "source.mp4")
    _make_source_video(source_path, duration=20)

    job = _make_job("job_frd_single_001", source_path)

    single_seg_timeline = EditTimeline(
        timeline_id="timeline_single_smoke",
        job_id=job.job_id,
        target_duration=8.0,
        selected_segments=[
            TimelineSegment(
                segment_id="seg_only_001",
                job_id=job.job_id,
                candidate_id=None,
                start_time=5.0,
                end_time=13.0,
                segment_role="hook",
                selection_score=0.88,
            )
        ],
        hook_segment_id="seg_only_001",
        timeline_score=0.88,
    )

    output_path = FinalRenderDriver().render(
        job=job,
        source_path=source_path,
        edit_timeline=single_seg_timeline,
        output_dir=test_dir,
    )

    assert os.path.exists(output_path)

    with VideoFileClip(output_path) as clip:
        actual_duration = float(clip.duration or 0.0)

    assert abs(actual_duration - 8.0) <= 1.0, (
        f"Expected ~8.0s, got {actual_duration:.3f}s"
    )

    print(f"\n[PASS] test_single_segment_renders_without_concat")
    print(f"  duration={actual_duration:.3f}s")


# ------------------------------------------------------------------ #
#  Entry point                                                         #
# ------------------------------------------------------------------ #

def main() -> None:
    test_basic_render_consumes_timeline()
    test_render_with_reframe_and_zoom()
    test_single_segment_renders_without_concat()
    print("\n=== ALL FINAL RENDER DRIVER SMOKE TESTS PASSED ===")


if __name__ == "__main__":
    main()
