from __future__ import annotations

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PATH = PROJECT_ROOT / "core" / "gaming_pipeline.py"

FORBIDDEN_IN_MURCH_BLOCK = [
    "TimelineBuilder",
    "LongformTimelineBuilder",
    "HighlightSelector",
    "final cutlist",
    "final_cutlist",
    "cut_list",
    "render_now",
    "auto_remove",
    "auto_cut",
    "auto_highlight",
    "delete_segment",
    "drop_segment",
    "timeline_apply_now",
    "apply_cut",
]


def _pipeline_text() -> str:
    return PIPELINE_PATH.read_text(encoding="utf-8")


def _murch_block(text: str) -> str:
    start = text.index("# ── Murch Scoring (2B-26-C)")
    end = text.index("# ── End Murch Scoring", start)
    return text[start:end]


def test_murch_scoring_imports_exist() -> None:
    text = _pipeline_text()

    assert "from core.murch_scoring_runner import (" in text
    assert "apply_murch_scoring_run_report_to_job" in text
    assert "run_murch_scoring_for_job" in text


def test_murch_scoring_events_exist() -> None:
    text = _pipeline_text()

    assert "MURCH_SCORING_STARTED" in text
    assert "MURCH_SCORING_DONE" in text
    assert "MURCH_SCORING_SKIPPED" in text
    assert "MURCH_SCORING_FAILED" in text


def test_murch_scoring_checkpoint_exists() -> None:
    text = _pipeline_text()

    assert 'step_name="murch_scoring_done"' in text
    assert 'reason="murch_scoring_completed_or_skipped"' in text


def test_murch_scoring_runner_and_apply_are_used() -> None:
    text = _pipeline_text()
    block = _murch_block(text)

    assert "murch_scoring_report = run_murch_scoring_for_job(" in block
    assert "apply_murch_scoring_run_report_to_job(" in block


def test_murch_scoring_has_try_except_guard() -> None:
    text = _pipeline_text()
    block = _murch_block(text)

    assert "try:" in block
    assert "except Exception as murch_scoring_exc:" in block
    assert 'job.murch_scoring_status = "failed"' in block
    assert 'job.murch_scoring_recommendation = "murch_scoring_failed"' in block


def test_murch_scoring_block_is_after_segment_classification_done() -> None:
    text = _pipeline_text()

    segment_done_index = text.index('event_type="SEGMENT_CLASSIFICATION_DONE"')
    segment_checkpoint_index = text.index('step_name="segment_classification_done"')
    murch_started_index = text.index('event_type="MURCH_SCORING_STARTED"')

    assert segment_done_index < segment_checkpoint_index < murch_started_index


def test_murch_scoring_does_not_use_timeline_or_highlight_selector() -> None:
    text = _pipeline_text()
    block = _murch_block(text)

    for forbidden in FORBIDDEN_IN_MURCH_BLOCK:
        assert forbidden not in block


def test_pipeline_file_has_no_bom_and_ends_with_newline() -> None:
    data = PIPELINE_PATH.read_bytes()

    assert data.startswith(b"\xef\xbb\xbf") is False
    assert data.endswith(b"\n")
