from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PATH = ROOT / "core" / "gaming_pipeline.py"


def _pipeline_text() -> str:
    return PIPELINE_PATH.read_text(encoding="utf-8")


def test_pipeline_imports_dynamic_pacing_runner() -> None:
    text = _pipeline_text()

    assert "from core.dynamic_pacing_runner import" in text
    assert "run_dynamic_pacing_for_job" in text
    assert "apply_dynamic_pacing_run_report_to_job" in text


def test_pipeline_runs_dynamic_pacing_after_emotional_arc() -> None:
    text = _pipeline_text()

    arc_index = text.index("run_emotional_arc_builder_for_job(")
    arc_apply_index = text.index("apply_emotional_arc_run_report_to_job(")
    pacing_index = text.index("run_dynamic_pacing_for_job(")
    pacing_apply_index = text.index("apply_dynamic_pacing_run_report_to_job(")

    assert arc_index < arc_apply_index < pacing_index < pacing_apply_index


def test_pipeline_dynamic_pacing_metadata_is_review_only() -> None:
    text = _pipeline_text()
    start = text.index("run_dynamic_pacing_for_job(")
    block = text[start : start + 1600]

    required_tokens = [
        '"phase": "2B-39"',
        '"block": "block7_story_pacing"',
        '"review_only": True',
        '"dynamic_pacing_only": True',
        '"media_unchanged": True',
        '"no_execution_in_2b_39": True',
        '"no_render_in_2b_39": True',
        '"no_timeline_reorder_in_2b_39": True',
        '"no_pacing_apply_in_2b_39": True',
        '"no_split_merge_trim_extend_in_2b_39": True',
    ]

    for token in required_tokens:
        assert token in block


def test_pipeline_dynamic_pacing_never_allows_execution_flags() -> None:
    text = _pipeline_text()
    start = text.index("DYNAMIC_PACING_ENGINE_STARTED")
    end = text.index("timeline_safety_validation_status", start)
    block = text[start:end]

    assert '"can_apply_pacing": False' in block
    assert '"can_split_clips": False' in block
    assert '"can_merge_clips": False' in block
    assert '"can_trim": False' in block
    assert '"can_extend": False' in block
    assert '"can_reorder_timeline": False' in block
    assert '"can_render": False' in block
    assert 'step_name="dynamic_pacing_engine_done"' in block


def test_pipeline_dynamic_pacing_file_has_no_bom_and_ends_with_newline() -> None:
    content = PIPELINE_PATH.read_bytes()

    assert not content.startswith(b"\xef\xbb\xbf")
    assert content.endswith(b"\n")
