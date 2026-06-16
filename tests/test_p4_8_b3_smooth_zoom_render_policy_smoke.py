from __future__ import annotations

from core.final_render_driver import FinalRenderDriver
from core.smooth_zoom_engine import ZoomCurve, ZoomKeyframe
from models.framing_instruction import FramingInstruction
from models.reframe_plan import ReframePlan
from models.timeline_segment import TimelineSegment


def _segment(segment_id: str = "seg_smooth_zoom") -> TimelineSegment:
    return TimelineSegment(
        segment_id=segment_id,
        job_id="job_smooth_zoom_policy",
        candidate_id=None,
        start_time=10.0,
        end_time=20.0,
        segment_role="peak",
        selection_score=1.0,
    )


def _plan(segment_id: str, layout_kind: str) -> ReframePlan:
    return ReframePlan(
        plan_id="reframe_smooth_zoom_policy",
        job_id="job_smooth_zoom_policy",
        timeline_id="timeline_smooth_zoom_policy",
        source_aspect_ratio="32:9",
        primary_target_aspect_ratio="16:9",
        instructions=[
            FramingInstruction(
                instruction_id="frame_smooth_zoom_policy",
                job_id="job_smooth_zoom_policy",
                timeline_id="timeline_smooth_zoom_policy",
                segment_id=segment_id,
                focus_kind="gameplay",
                layout_kind=layout_kind,
                source_aspect_ratio="32:9",
                target_aspect_ratio="16:9",
                crop_window={"x": 0.5, "y": 0.0, "width": 0.5, "height": 1.0},
            )
        ],
        plan_score=1.0,
    )


def test_smooth_zoom_policy_interpolates_curve_for_segment_midpoint() -> None:
    driver = FinalRenderDriver()
    segment = _segment()
    curve = ZoomCurve(
        [
            ZoomKeyframe(10.0, 1.0, "balanced", "linear"),
            ZoomKeyframe(15.0, 1.5, "gameplay", "linear"),
            ZoomKeyframe(20.0, 1.0, "balanced", "linear"),
        ]
    )

    policy = driver._resolve_smooth_zoom_policy(segment, curve)

    assert policy["smooth_zoom_used"] is True
    assert policy["timestamp"] == 15.0
    assert policy["zoom_factor"] == 1.5
    assert policy["target"] == "gameplay"


def test_gameplay_focus_uses_smooth_zoom_crop_for_32x9() -> None:
    driver = FinalRenderDriver()
    segment = _segment()
    smooth_policy = {
        "smooth_zoom_used": True,
        "zoom_factor": 1.5,
        "target": "gameplay",
    }

    fc, label = driver._build_filter_complex(
        segment=segment,
        reframe_plan=_plan(segment.segment_id, "gameplay_crop"),
        dynamic_edit_plan=None,
        audio_peaks=[],
        src_w=3840,
        src_h=1080,
        focus_policy={"layout_kind": "gameplay_crop", "policy_source": "test"},
        smooth_zoom_policy=smooth_policy,
    )

    assert label == "[out]"
    assert "crop=1920:1080:1920:0" in fc
    assert "scale=w='1920*(if(lt(t\\,0.12)" in fc
    assert "1.5" in fc
    assert "eval=frame" in fc
    assert "crop=1920:1080:x='2*floor(1920*((if(lt(t\\,0.12)" in fc
    assert ":y='2*floor(1080*((if(lt(t\\,0.12)" in fc
    assert "overlay=" not in fc


def test_facecam_focus_uses_smooth_zoom_crop_for_32x9() -> None:
    driver = FinalRenderDriver()
    segment = _segment()
    smooth_policy = {
        "smooth_zoom_used": True,
        "zoom_factor": 2.0,
        "target": "facecam",
    }

    fc, label = driver._build_filter_complex(
        segment=segment,
        reframe_plan=_plan(segment.segment_id, "facecam_emphasis"),
        dynamic_edit_plan=None,
        audio_peaks=[],
        src_w=3840,
        src_h=1080,
        focus_policy={"layout_kind": "facecam_emphasis", "policy_source": "test"},
        smooth_zoom_policy=smooth_policy,
    )

    assert label == "[out]"
    assert "crop=960:540:480:270" in fc
    assert "overlay=" not in fc
