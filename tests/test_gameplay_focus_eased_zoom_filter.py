from __future__ import annotations

import pytest

from core.final_render_driver import FinalRenderDriver


def test_gameplay_focus_eased_zoom_expression_uses_target_and_scale_eval_frame() -> None:
    driver = FinalRenderDriver()

    zoom_spec = driver._build_gameplay_focus_zoom_expression(
        segment_duration=3.0,
        target_zoom=1.4,
    )
    fc, label = driver._build_32x9_focus_crop_filter(
        src_w=3840,
        src_h=1080,
        side="right",
        gameplay_zoom=1.4,
        segment_duration=3.0,
    )

    assert label == "[out]"
    assert zoom_spec["target_zoom"] == pytest.approx(1.4)
    assert zoom_spec["ease_seconds"] == pytest.approx(0.15)
    assert "if(lt(t\\,0.15)\\,1+(1.4-1)*" in zoom_spec["expression"]
    assert "if(lt(t\\,2.85)\\,1.4\\," in zoom_spec["expression"]
    assert "crop=1920:1080:1920:0" in fc
    assert "scale=w='1920*(if(lt(t\\,0.15)" in fc
    assert ":h='1080*(if(lt(t\\,0.15)" in fc
    assert "eval=frame" in fc
    assert "crop=1920:1080:x='(iw-1920)/2':y='(ih-1080)/2'" in fc


def test_gameplay_focus_eased_zoom_expression_clamps_ease_for_short_segments() -> None:
    driver = FinalRenderDriver()

    zoom_spec = driver._build_gameplay_focus_zoom_expression(
        segment_duration=0.3,
        target_zoom=1.4,
    )

    assert zoom_spec["ease_seconds"] == pytest.approx(0.1)
    assert zoom_spec["hold_until_seconds"] == pytest.approx(0.2)
    assert "if(lt(t\\,0.1)\\,1+(1.4-1)*" in zoom_spec["expression"]
    assert "if(lt(t\\,0.2)\\,1.4\\," in zoom_spec["expression"]
