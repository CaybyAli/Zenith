
from types import SimpleNamespace

from core.final_render_driver import FinalRenderDriver


def test_p5_g5_facecam_emphasis_keeps_gameplay_visible_for_32x9_source():
    driver = FinalRenderDriver()

    segment = SimpleNamespace(
        segment_id="seg_owner_no_go",
        segment_role="hook",
    )

    focus_policy = {
        "layout_kind": "facecam_emphasis",
        "policy_source": "focus_decision",
        "focus_target": "facecam",
    }

    filter_complex, out_label = driver._build_filter_complex(
        segment=segment,
        reframe_plan=None,
        dynamic_edit_plan=None,
        audio_peaks=[],
        src_w=3840,
        src_h=1080,
        focus_policy=focus_policy,
        smooth_zoom_policy=None,
    )

    assert out_label == "[out]"
    assert "overlay=" in filter_complex
    assert "[gp][fc]overlay=" in filter_complex

    # Right half is gameplay and must remain the main 1920x1080 image.
    assert "crop=1920:1080:1920:0" in filter_complex

    # Left half is facecam, but only as PiP.
    assert "[fc_src]crop=" in filter_complex
    assert "scale_cuda=720:405" in filter_complex


def test_p5_g5_gameplay_crop_still_renders_gameplay_only_for_32x9_source():
    driver = FinalRenderDriver()

    segment = SimpleNamespace(
        segment_id="seg_gameplay_only",
        segment_role="peak",
    )

    focus_policy = {
        "layout_kind": "gameplay_crop",
        "policy_source": "focus_decision",
        "focus_target": "gameplay",
    }

    filter_complex, out_label = driver._build_filter_complex(
        segment=segment,
        reframe_plan=None,
        dynamic_edit_plan=None,
        audio_peaks=[],
        src_w=3840,
        src_h=1080,
        focus_policy=focus_policy,
        smooth_zoom_policy=None,
    )

    assert out_label == "[out]"
    assert "crop=1920:1080:1920:0" in filter_complex
    assert "overlay=" not in filter_complex
