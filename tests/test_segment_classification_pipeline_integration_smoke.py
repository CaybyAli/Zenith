from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PATH = ROOT / "core" / "gaming_pipeline.py"


def _pipeline_text() -> str:
    return PIPELINE_PATH.read_text(encoding="utf-8")


def _segment_classification_block() -> str:
    text = _pipeline_text()
    start = text.index("# ── Segment Classification (2B-25-C)")
    end = text.index("# ── End Segment Classification")
    return text[start:end]


def test_segment_classification_imports_exist() -> None:
    text = _pipeline_text()

    assert "from core.segment_classification_runner import (" in text
    assert "apply_segment_classification_run_report_to_job" in text
    assert "run_segment_classification_for_job" in text


def test_segment_classification_events_exist() -> None:
    text = _pipeline_text()

    assert "SEGMENT_CLASSIFICATION_STARTED" in text
    assert "SEGMENT_CLASSIFICATION_DONE" in text
    assert "SEGMENT_CLASSIFICATION_SKIPPED" in text
    assert "SEGMENT_CLASSIFICATION_FAILED" in text


def test_segment_classification_checkpoint_exists() -> None:
    text = _pipeline_text()

    assert 'step_name="segment_classification_done"' in text
    assert "segment_classification_completed_or_skipped" in text


def test_runner_and_apply_are_used() -> None:
    block = _segment_classification_block()

    assert "run_segment_classification_for_job(" in block
    assert "apply_segment_classification_run_report_to_job(" in block


def test_segment_classification_block_has_try_except() -> None:
    block = _segment_classification_block()

    assert "try:" in block
    assert "except Exception as segment_classification_exc:" in block
    assert 'job.segment_classification_status = "failed"' in block
    assert (
        'job.segment_classification_recommendation = "segment_classification_failed"'
        in block
    )


def test_segment_classification_runs_after_unified_registry() -> None:
    text = _pipeline_text()

    unified_pos = text.index('step_name="unified_edit_signals_done"')
    segment_pos = text.index("# ── Segment Classification (2B-25-C)")

    assert unified_pos < segment_pos


def test_no_timeline_builder_or_highlight_selector_integration() -> None:
    block = _segment_classification_block()

    forbidden = [
        "TimelineBuilder",
        "timeline_builder",
        "LongformTimelineBuilder",
        "HighlightSelector",
        "highlight_selector",
        "select_highlight",
        "build_timeline",
        "final_cutlist",
    ]

    for forbidden_text in forbidden:
        assert forbidden_text not in block


def test_no_automatic_cut_remove_or_render_logic_in_segment_block() -> None:
    block = _segment_classification_block().lower()

    forbidden = [
        "force_cut",
        "auto_remove",
        "hard_remove",
        "remove_now",
        "auto_cut",
        "auto_trim",
        "auto_highlight",
        "highlight_now",
        "auto_hook",
        "auto_mute",
        "censor_now",
        "delete_segment",
        "drop_segment",
        "timeline_apply_now",
        "apply_cut",
        "render_now",
        "ffmpeg",
    ]

    for forbidden_text in forbidden:
        assert forbidden_text not in block


def test_pipeline_file_has_no_bom_and_ends_with_newline() -> None:
    content = PIPELINE_PATH.read_bytes()

    assert not content.startswith(b"\xef\xbb\xbf")
    assert content.endswith(b"\n")
