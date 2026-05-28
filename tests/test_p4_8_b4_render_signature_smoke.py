from __future__ import annotations

from inspect import signature
from pathlib import Path

from core.final_render_driver import FinalRenderDriver


def test_final_render_driver_render_accepts_smooth_zoom_curve() -> None:
    params = signature(FinalRenderDriver.render).parameters

    assert "smooth_zoom_curve" in params
    assert "dynamic_edit_plan" in params
    assert list(params).index("smooth_zoom_curve") > list(params).index("dynamic_edit_plan")


def test_gaming_pipeline_passes_smooth_zoom_curve_to_renderer() -> None:
    text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")

    assert "active_renderer.render(" in text
    assert "smooth_zoom_curve=smooth_zoom_curve" in text


def test_final_render_driver_records_smooth_zoom_context() -> None:
    text = Path("core/final_render_driver.py").read_text(encoding="utf-8")

    assert '"smooth_zoom_available": smooth_zoom_curve is not None' in text
    assert '"smooth_zoom_used": any(' in text
    assert '"smooth_zoom_records": smooth_zoom_records' in text
