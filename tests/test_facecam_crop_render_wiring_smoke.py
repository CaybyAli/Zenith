from __future__ import annotations

from types import SimpleNamespace

from core.final_render_driver import FinalRenderDriver
from core.profile_manager import ProfileManager


FINAL_CROP = {"x": 0, "y": 0, "w": 1864, "h": 1072}


def _segment() -> SimpleNamespace:
    return SimpleNamespace(
        segment_id="seg_facecam_crop_001",
        segment_role="hook",
        start_time=0.0,
        end_time=4.0,
        duration=4.0,
    )


def test_profile_contains_final_manual_facecam_crop() -> None:
    profile = ProfileManager().load_profile("gaming_main")
    assert profile["facecam_crop"] == FINAL_CROP


def test_render_driver_resolves_facecam_crop_from_gaming_profile() -> None:
    driver = FinalRenderDriver()
    job = SimpleNamespace(channel_type=SimpleNamespace(value="gaming_main"))

    raw_crop, source = driver._resolve_facecam_crop_config(job=job)
    resolved = driver._coerce_facecam_crop(raw_crop, src_w=3840, src_h=1080)

    assert resolved == FINAL_CROP
    assert source == "profile:gaming_main.facecam_crop"


def test_pip_helper_uses_manual_facecam_crop() -> None:
    driver = FinalRenderDriver()

    filter_complex, label = driver._build_32x9_gameplay_with_facecam_pip_filter(
        src_w=3840,
        src_h=1080,
        pip_width=720,
        pip_height=405,
        pip_x=20,
        pip_y=100,
        facecam_crop=FINAL_CROP,
    )

    assert label == "[out]"
    assert "crop=1864:1072:0:0" in filter_complex
    assert "overlay=20:100" in filter_complex


def test_filter_complex_no_zoom_branch_uses_manual_facecam_crop() -> None:
    driver = FinalRenderDriver()

    filter_complex, label = driver._build_filter_complex(
        _segment(),
        reframe_plan=None,
        dynamic_edit_plan=None,
        audio_peaks=[],
        src_w=3840,
        src_h=1080,
        facecam_crop=FINAL_CROP,
    )

    assert label == "[out]"
    assert "crop=1864:1072:0:0" in filter_complex


def test_filter_complex_static_tiny_branch_uses_manual_facecam_crop() -> None:
    driver = FinalRenderDriver()

    filter_complex, label = driver._build_filter_complex(
        _segment(),
        reframe_plan=None,
        dynamic_edit_plan=None,
        audio_peaks=[],
        src_w=3840,
        src_h=1080,
        facecam_static_tiny=True,
        facecam_crop=FINAL_CROP,
    )

    assert label == "[out]"
    assert "crop=1864:1072:0:0" in filter_complex
    assert "scale_cuda=480:270" in filter_complex or "scale=480:270" in filter_complex
