from __future__ import annotations

from core.final_render_driver import FinalRenderDriver
from models.framing_instruction import FramingInstruction
from models.reframe_plan import ReframePlan
from models.timeline_segment import TimelineSegment


def test_static_tiny_facecam_overrides_big_facecam_and_audio_peak_growth():
    job_id = "job_static_tiny"
    segment_id = "g8_seg_static_tiny"

    segment = TimelineSegment(
        segment_id=segment_id,
        job_id=job_id,
        candidate_id=None,
        start_time=0.0,
        end_time=8.0,
        segment_role="active_play",
        selection_score=1.0,
    )

    reframe_plan = ReframePlan(
        plan_id="reframe_static_tiny",
        job_id=job_id,
        timeline_id="timeline_static_tiny",
        source_aspect_ratio="32:9",
        primary_target_aspect_ratio="16:9",
        instructions=[
            FramingInstruction(
                instruction_id="fi_static_tiny",
                job_id=job_id,
                timeline_id="timeline_static_tiny",
                segment_id=segment_id,
                focus_kind="facecam_emphasis",
                layout_kind="facecam_emphasis",
                source_aspect_ratio="32:9",
                target_aspect_ratio="16:9",
                crop_window={},
            )
        ],
        plan_score=1.0,
    )

    fc, label = FinalRenderDriver()._build_filter_complex(
        segment=segment,
        reframe_plan=reframe_plan,
        dynamic_edit_plan=None,
        audio_peaks=[
            {"start": 1.0, "end": 4.0, "peak_db": -8.0},
        ],
        src_w=3840,
        src_h=1080,
        facecam_static_tiny=True,
    )

    assert label == "[out]"
    assert "crop=1920:1080:1920:0" in fc
    assert "scale_cuda=1920:1080" in fc
    assert "scale_cuda=480:270" in fc
    assert "overlay=20:100" in fc

    assert "scale_cuda=720:405" not in fc
    assert "split=5" not in fc
    assert "between(t" not in fc
