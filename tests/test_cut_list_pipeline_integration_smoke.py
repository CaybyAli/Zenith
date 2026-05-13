from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_PATH = ROOT / "core" / "gaming_pipeline.py"


def _pipeline_text() -> str:
    return PIPELINE_PATH.read_text(encoding="utf-8")


def _cut_list_block() -> str:
    text = _pipeline_text()
    start = text.index("# ── Cut List Generation (2B-27-C)")
    end = text.index("# ── End Cut List Generation", start)
    return text[start:end]


def test_cut_list_runner_imports_exist():
    text = _pipeline_text()

    assert "from core.cut_list_runner import (" in text
    assert "apply_cut_list_run_report_to_job" in text
    assert "run_cut_list_generation_for_job" in text


def test_cut_list_events_exist():
    text = _pipeline_text()

    assert "CUT_LIST_GENERATION_STARTED" in text
    assert "CUT_LIST_GENERATION_DONE" in text
    assert "CUT_LIST_GENERATION_SKIPPED" in text
    assert "CUT_LIST_GENERATION_FAILED" in text


def test_cut_list_checkpoint_exists():
    text = _pipeline_text()

    assert 'step_name="cut_list_generation_done"' in text
    assert 'reason="cut_list_generation_completed_or_skipped"' in text


def test_cut_list_runner_and_apply_are_used():
    block = _cut_list_block()

    assert "run_cut_list_generation_for_job(" in block
    assert "apply_cut_list_run_report_to_job(" in block


def test_cut_list_block_has_try_except():
    block = _cut_list_block()

    assert "try:" in block
    assert "except Exception as cut_list_generation_exc:" in block
    assert 'job.cut_list_status = "failed"' in block
    assert 'job.cut_list_recommendation = "cut_list_generation_failed"' in block


def test_cut_list_block_is_after_murch_scoring_done():
    text = _pipeline_text()

    murch_done_index = text.index("MURCH_SCORING_DONE")
    cut_list_started_index = text.index("CUT_LIST_GENERATION_STARTED")

    assert cut_list_started_index > murch_done_index


def test_cut_list_block_is_after_murch_checkpoint():
    text = _pipeline_text()

    murch_checkpoint_index = text.index('step_name="murch_scoring_done"')
    cut_list_checkpoint_index = text.index('step_name="cut_list_generation_done"')

    assert cut_list_checkpoint_index > murch_checkpoint_index


def test_cut_list_block_does_not_use_timeline_or_highlight_selector():
    block = _cut_list_block()

    assert "TimelineBuilder" not in block
    assert "HighlightSelector" not in block


def test_cut_list_block_does_not_execute_render_or_ffmpeg():
    block = _cut_list_block()

    forbidden = [
        "FFmpeg",
        "ffmpeg",
        "renderer.",
        ".render(",
        "RenderProcessor",
    ]

    for word in forbidden:
        assert word not in block


def test_cut_list_block_does_not_apply_direct_cut_actions():
    block = _cut_list_block()

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
        "execute_cut",
        "final_cut",
    ]

    lowered = block.lower()
    lowered = lowered.replace("apply_cut_list_run_report_to_job", "")

    for word in forbidden:
        assert word not in lowered


def test_new_files_have_no_bom_and_end_with_newline():
    files = [
        PIPELINE_PATH,
        ROOT / "tests" / "test_cut_list_pipeline_integration_smoke.py",
    ]

    for path in files:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf")
        assert raw.endswith(b"\n")
