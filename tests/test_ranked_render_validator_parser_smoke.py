from __future__ import annotations

from scripts.ranked_render_v1_validate import (
    parse_gpu_monitor_csv,
    parse_gpu_summary_from_log,
    parse_render_log_segment_total,
    parse_render_seconds_from_log,
    read_text_auto,
)


def test_render_log_parser_reads_segment_total_and_trailing_render_seconds() -> None:
    text = """
[SEG] SEGMENT 1/26 (3%) - ACTIVE_PLAY
[SEG] SEGMENT 26/26 (100%) - ACTIVE_PLAY
audio_depop_exit_code=0
render_seconds=221.982
"""

    assert parse_render_log_segment_total(text) == 26
    assert parse_render_seconds_from_log(text) == "221.982"


def test_render_log_parser_reads_utf16_and_locale_decimal(tmp_path) -> None:
    log_path = tmp_path / "render.log"
    log_path.write_text(
        "[CUT] RENDERING GESTARTET: 80 Segmente\n"
        "[SEG] SEGMENT 80/80 (100%) - ACTIVE_PLAY\n"
        "render_seconds=643,726\n",
        encoding="utf-16",
    )

    text = read_text_auto(log_path)

    assert parse_render_log_segment_total(text) == 80
    assert parse_render_seconds_from_log(text) == "643.726"


def test_render_log_parser_reads_gpu_summary_from_report_style_line() -> None:
    text = "gpu_summary={'exists': True, 'rows': 5, 'gpu_avg': 42.5}\n"

    parsed = parse_gpu_summary_from_log(text)

    assert parsed is not None
    assert parsed["rows"] == 5
    assert parsed["gpu_avg"] == 42.5


def test_gpu_monitor_csv_parser_keeps_summary_fields() -> None:
    csv_text = """time,gpu,enc,power
0,10,20,100
1,30,40,140
"""

    summary = parse_gpu_monitor_csv(csv_text)

    assert summary["exists"] is True
    assert summary["rows"] == 2
    assert summary["gpu_avg"] == 20.0
    assert summary["enc_max"] == 40.0
