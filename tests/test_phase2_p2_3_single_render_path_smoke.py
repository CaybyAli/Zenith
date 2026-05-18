from __future__ import annotations

from pathlib import Path


def _render_block() -> str:
    source = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")
    start = source.index("# 7) Render")
    end = source.index("# 8)", start)
    return source[start:end]


def test_p2_3_gaming_main_uses_final_render_driver_single_path() -> None:
    block = _render_block()

    assert "active_renderer = FinalRenderDriver()" in block
    assert "active_renderer = renderer" not in block
    assert "RenderProcessor als Fallback" not in block
    assert "FinalRenderDriver / RenderProcessor" not in block


def test_p2_3_final_render_driver_call_uses_keyword_signature() -> None:
    block = _render_block()

    assert "active_renderer.render(job, edit_decision)" not in block
    assert "final_video_path = active_renderer.render(" in block
    assert "job=job" in block
    assert "source_path=job.raw_video_path" in block
    assert "edit_timeline=edit_timeline" in block
    assert "reframe_plan=reframe_plan" in block
    assert "dynamic_edit_plan=dynamic_edit_plan" in block


def test_p2_3_render_processor_is_marked_legacy() -> None:
    source = Path("core/render_processor.py").read_text(encoding="utf-8")

    assert "# DEPRECATED - Phase 2" in source
    assert "superseded by FinalRenderDriver" in source
    assert "class RenderProcessor" in source
