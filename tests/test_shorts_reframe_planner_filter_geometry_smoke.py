from __future__ import annotations

from core.shorts_reframe_planner import (
    build_facecam_centered_filter,
    build_gameplay_centered_filter,
    build_stack_filter_60_40,
)
from core.shorts_source_format_detector import SourceFormat


def _custom_source_format() -> SourceFormat:
    return SourceFormat(
        width=5000,
        height=1000,
        aspect_ratio=5.0,
        is_32_9_composite=True,
        gameplay_region=(123, 0, 2100, 1000),
        facecam_region=(2600, 0, 1900, 1000),
    )


def test_stack_filter_uses_final_p4_hotfix_a_geometry() -> None:
    filter_text = build_stack_filter_60_40(_custom_source_format())

    assert "[facecam_src]crop=1920:1080:0:0" in filter_text
    assert "scale=1080:640" in filter_text
    assert "crop=1080:640:10:0[facecam_block]" in filter_text
    assert "[gameplay_src]crop=1920:1080:1850:0" in filter_text
    assert "scale=1080:1280" in filter_text
    assert "crop=1080:1280[gameplay_block]" in filter_text
    assert "[facecam_block][gameplay_block]vstack=inputs=2[out]" in filter_text
    assert "420" not in filter_text


def test_gameplay_centered_filter_uses_source_format_gameplay_region() -> None:
    filter_text = build_gameplay_centered_filter(_custom_source_format())

    assert "crop=2100:1000:123:0" in filter_text
    assert "scale=1920:1920" in filter_text
    assert "crop=1080:1920[out]" in filter_text
    assert "420" not in filter_text


def test_facecam_centered_filter_uses_source_format_facecam_region() -> None:
    filter_text = build_facecam_centered_filter(_custom_source_format())

    assert "crop=1900:1000:2600:0" in filter_text
    assert "scale=1920:1920" in filter_text
    assert "crop=1080:1920[out]" in filter_text
    assert "420" not in filter_text


def test_all_planner_filters_avoid_render_driver_legacy_crop_normalizer() -> None:
    source = _custom_source_format()

    filters = [
        build_stack_filter_60_40(source),
        build_gameplay_centered_filter(source),
        build_facecam_centered_filter(source),
    ]

    for filter_text in filters:
        assert "[0:v]crop=" not in filter_text
        assert "420" not in filter_text
