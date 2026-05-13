from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_FILE = ROOT / "core" / "gaming_pipeline.py"
TEST_FILE = ROOT / "tests" / "test_cut_list_finalizer_pipeline_integration_smoke.py"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _block() -> str:
    text = _read(PIPELINE_FILE)
    start_marker = "# -- Cut List Finalization (2B-31-C)"
    end_marker = "# -- End Cut List Finalization"

    assert start_marker in text
    assert end_marker in text

    start = text.index(start_marker)
    end = text.index(end_marker, start)
    return text[start:end]


def test_imports_are_present():
    text = _read(PIPELINE_FILE)

    assert "from core.cut_list_finalizer_runner import (" in text
    assert "run_cut_list_finalization_for_job" in text
    assert "apply_cut_list_finalization_run_report_to_job" in text


def test_cut_list_finalization_events_are_present():
    block = _block()

    assert "CUT_LIST_FINALIZATION_STARTED" in block
    assert "CUT_LIST_FINALIZATION_DONE" in block
    assert "CUT_LIST_FINALIZATION_SKIPPED" in block
    assert "CUT_LIST_FINALIZATION_FAILED" in block


def test_checkpoint_is_present():
    assert 'step_name="cut_list_finalization_done"' in _block()


def test_runner_and_apply_are_used_with_try_except():
    block = _block()

    assert "final_cut_list_report = run_cut_list_finalization_for_job" in block
    assert "apply_cut_list_finalization_run_report_to_job(" in block
    assert "try:" in block
    assert "except Exception as cut_list_finalization_exc:" in block
    assert 'job.final_cut_list_status = "failed"' in block
    assert 'job.final_cut_list_recommendation = "cut_list_finalization_failed"' in block


def test_block_comes_after_continuity_check_done():
    text = _read(PIPELINE_FILE)

    continuity_index = text.index("CONTINUITY_CHECK_DONE")
    finalizer_index = text.index("# -- Cut List Finalization (2B-31-C)")

    assert finalizer_index > continuity_index


def test_pipeline_block_does_not_use_timeline_or_highlight_selector():
    block = _block()

    forbidden = [
        "TimelineBuilder",
        "LongformTimelineBuilder",
        "HighlightSelector",
        "highlight_selector",
    ]
    for word in forbidden:
        assert word not in block


def test_pipeline_block_does_not_render_or_execute_final_plan():
    block = _block().lower()
    forbidden = [
        "ffmpeg",
        "renderprocessor",
        "finalrenderdriver",
        "render_now",
        "execute_cut",
        "apply_final_cutlist",
        "execute_final_cutlist",
        "timeline_apply_now",
    ]

    for word in forbidden:
        assert word not in block


def test_no_bom_and_newline():
    for path in [PIPELINE_FILE, TEST_FILE]:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), path
        assert raw.endswith(b"\n"), path
