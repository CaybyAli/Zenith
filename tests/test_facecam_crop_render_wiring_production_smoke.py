"""Production-path facecam wiring proof.

These tests pin the reconnect of the existing camera truth onto the real
production render path (gaming_pipeline -> FinalRenderDriver.render):

  * the profile crop {1864:1072:0:0} is what the production driver emits,
  * the static-tiny base size is 480x270,
  * facecam_emphasis_big is disabled (no whole-segment 704x396),
  * audio_peak_growth is disabled (no audio-reactive medium/large),
  * the driver still *supports* dynamic growth when reaction_size_events are
    supplied (size-events > 0) -- guarding the deferred "Zoom spaeter" path.

No new camera numbers are introduced here; every value is read back from the
existing profile / driver contract.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.final_render_driver import FinalRenderDriver

FINAL_CROP = {"x": 0, "y": 0, "w": 1864, "h": 1072}
GAMING_JOB = SimpleNamespace(channel_type=SimpleNamespace(value="gaming_main"))


def _segment() -> SimpleNamespace:
    return SimpleNamespace(
        segment_id="seg_prod_facecam_001",
        segment_role="hook",
        start_time=0.0,
        end_time=4.0,
        duration=4.0,
    )


def _resolved_production_crop(driver: FinalRenderDriver) -> dict:
    """Resolve the crop exactly as render() does for a gaming_main job."""
    raw_crop, source = driver._resolve_facecam_crop_config(job=GAMING_JOB)
    assert source == "profile:gaming_main.facecam_crop"
    return driver._coerce_facecam_crop(raw_crop, src_w=3840, src_h=1080)


def _has_scale(filter_complex: str, w: int, h: int) -> bool:
    return (
        f"scale_cuda={w}:{h}" in filter_complex
        or f"scale={w}:{h}" in filter_complex
    )


def test_production_pipeline_passes_facecam_static_tiny_true() -> None:
    """gaming_pipeline must wire static_tiny=True into render() (the reconnect)."""
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    # The production render() call consumes the flag...
    assert "facecam_static_tiny=render_facecam_static_tiny" in text
    # ...and the production default is True, not the regressed False.
    assert "render_facecam_static_tiny = True" in text
    assert "render_facecam_static_tiny = False" not in text


def test_production_static_tiny_emits_profile_crop_and_480x270_base() -> None:
    driver = FinalRenderDriver()
    crop = _resolved_production_crop(driver)
    assert crop == FINAL_CROP

    filter_complex, label = driver._build_filter_complex(
        _segment(),
        reframe_plan=None,
        dynamic_edit_plan=None,
        audio_peaks=[],
        src_w=3840,
        src_h=1080,
        facecam_static_tiny=True,
        facecam_crop=crop,
        job=GAMING_JOB,
    )

    assert label == "[out]"
    assert "crop=1864:1072:0:0" in filter_complex
    assert _has_scale(filter_complex, 480, 270)


def test_production_static_tiny_disables_emphasis_big() -> None:
    """Even on a facecam_emphasis segment, static_tiny must not emit 704x396."""
    driver = FinalRenderDriver()
    crop = _resolved_production_crop(driver)

    filter_complex, _ = driver._build_filter_complex(
        _segment(),
        reframe_plan=None,
        dynamic_edit_plan=None,
        audio_peaks=[],
        src_w=3840,
        src_h=1080,
        focus_policy={"layout_kind": "facecam_emphasis", "policy_source": "test"},
        facecam_static_tiny=True,
        facecam_crop=crop,
        job=GAMING_JOB,
    )

    assert _has_scale(filter_complex, 480, 270)
    assert not _has_scale(filter_complex, 704, 396)  # emphasis-big disabled


def test_production_static_tiny_disables_audio_peak_growth() -> None:
    """Loud audio peaks must not grow the facecam when static_tiny is on."""
    driver = FinalRenderDriver()
    crop = _resolved_production_crop(driver)

    loud_peaks = [{"start": 0.5, "end": 2.0, "peak_db": -8.0}]
    filter_complex, _ = driver._build_filter_complex(
        _segment(),
        reframe_plan=None,
        dynamic_edit_plan=None,
        audio_peaks=loud_peaks,
        src_w=3840,
        src_h=1080,
        facecam_static_tiny=True,
        facecam_crop=crop,
        job=GAMING_JOB,
    )

    assert _has_scale(filter_complex, 480, 270)
    assert not _has_scale(filter_complex, 640, 360)  # no audio-reactive medium
    assert not _has_scale(filter_complex, 704, 396)  # no audio-reactive large


def test_driver_still_supports_dynamic_growth_when_size_events_present() -> None:
    """Deferred 'Zoom spaeter': size-events > 0 still drive medium/large growth."""
    driver = FinalRenderDriver()
    crop = _resolved_production_crop(driver)

    reaction_size_events = [
        {"size": "medium", "source_start_seconds": 0.5, "source_end_seconds": 1.5},
        {"size": "large", "source_start_seconds": 2.0, "source_end_seconds": 3.0},
    ]
    segment_events = driver._reaction_size_events_for_segment(
        _segment(), reaction_size_events
    )
    assert len(segment_events) > 0  # size-events > 0

    filter_complex, label = driver._build_32x9_reaction_size_switch_filter(
        segment=_segment(),
        src_w=3840,
        src_h=1080,
        reaction_size_events=reaction_size_events,
        facecam_crop=crop,
        job=GAMING_JOB,
    )

    assert label == "[out]"
    assert "crop=1864:1072:0:0" in filter_complex
    assert _has_scale(filter_complex, 480, 270)  # tiny base
    assert _has_scale(filter_complex, 640, 360)  # medium growth
    assert _has_scale(filter_complex, 704, 396)  # large growth
