from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PATH = ROOT / "core" / "gaming_pipeline.py"


def _pipeline_text() -> str:
    return PIPELINE_PATH.read_text(encoding="utf-8")


def test_pipeline_imports_pattern_interrupt_runner() -> None:
    text = _pipeline_text()

    assert "from core.pattern_interrupt_runner import" in text
    assert "run_pattern_interrupt_for_job" in text
    assert "store_pattern_interrupt_run_report_to_job" in text


def test_pipeline_runs_pattern_interrupt_after_dynamic_pacing() -> None:
    text = _pipeline_text()

    pacing_index = text.index("run_dynamic_pacing_for_job(")
    pacing_apply_index = text.index("apply_dynamic_pacing_run_report_to_job(")
    pattern_index = text.index("run_pattern_interrupt_for_job(")
    pattern_apply_index = text.index("store_pattern_interrupt_run_report_to_job(")

    assert pacing_index < pacing_apply_index < pattern_index < pattern_apply_index


def test_pipeline_pattern_interrupt_metadata_is_review_only() -> None:
    text = _pipeline_text()
    start = text.index("run_pattern_interrupt_for_job(")
    block = text[start : start + 1800]

    required_tokens = [
        '"phase": "2B-40"',
        '"block": "block7_story_pacing"',
        '"review_only": True',
        '"pattern_interrupt_only": True',
        '"media_unchanged": True',
        '"no_execution_in_2b_40": True',
        '"no_render_in_2b_40": True',
        '"no_timeline_reorder_in_2b_40": True',
        '"no_pattern_apply_in_2b_40": True',
        '"no_zoom_insert_in_2b_40": True',
        '"no_text_overlay_insert_in_2b_40": True',
        '"no_sfx_insert_in_2b_40": True',
    ]

    for token in required_tokens:
        assert token in block


def test_pipeline_pattern_interrupt_never_allows_execution_flags() -> None:
    text = _pipeline_text()
    start = text.index("PATTERN_INTERRUPT_ENGINE_STARTED")
    end = text.index("timeline_safety_validation_status", start)
    block = text[start:end]

    assert '"can_apply_interrupts": False' in block
    assert '"can_insert_zoom": False' in block
    assert '"can_insert_text_overlay": False' in block
    assert '"can_insert_sfx": False' in block
    assert '"can_reorder_timeline": False' in block
    assert '"can_trim": False' in block
    assert '"can_extend": False' in block
    assert '"can_render": False' in block
    assert 'step_name="pattern_interrupt_engine_done"' in block


def test_pipeline_pattern_interrupt_file_has_no_bom_and_ends_with_newline() -> None:
    content = PIPELINE_PATH.read_bytes()

    assert not content.startswith(b"\xef\xbb\xbf")
    assert content.endswith(b"\n")
