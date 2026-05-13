from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_FILE = ROOT / "core" / "gaming_pipeline.py"
TEST_FILE = ROOT / "tests" / "test_transition_decision_pipeline_integration_smoke.py"


def _pipeline_text() -> str:
    return PIPELINE_FILE.read_text(encoding="utf-8")


def _transition_decision_block() -> str:
    text = _pipeline_text()
    start_marker = "# -- Transition Decision Engine (2B-29-C)"
    end_marker = "# -- End Transition Decision Engine"

    assert start_marker in text
    assert end_marker in text

    start = text.index(start_marker)
    end = text.index(end_marker, start)

    return text[start:end]


def _safe_block_for_forbidden_scan() -> str:
    block = _transition_decision_block()
    block = block.replace(
        "apply_transition_decision_run_report_to_job",
        "safe_write_transition_decision_run_report_to_job",
    )
    return block.lower()


def test_transition_decision_runner_imports_exist():
    text = _pipeline_text()

    assert "from core.transition_decision_runner import (" in text
    assert "apply_transition_decision_run_report_to_job" in text
    assert "run_transition_decision_for_job" in text


def test_transition_decision_events_exist():
    text = _pipeline_text()

    assert "TRANSITION_DECISION_STARTED" in text
    assert "TRANSITION_DECISION_DONE" in text
    assert "TRANSITION_DECISION_SKIPPED" in text
    assert "TRANSITION_DECISION_FAILED" in text


def test_transition_decision_checkpoint_exists():
    text = _pipeline_text()

    assert 'step_name="transition_decision_done"' in text


def test_transition_decision_runner_and_apply_are_used():
    block = _transition_decision_block()

    assert "run_transition_decision_for_job(" in block
    assert "apply_transition_decision_run_report_to_job(" in block
    assert "transition_decision_report = run_transition_decision_for_job" in block


def test_transition_decision_block_has_safe_try_except():
    block = _transition_decision_block()

    assert "try:" in block
    assert "except Exception as transition_decision_exc:" in block
    assert 'job.transition_decision_status = "failed"' in block
    assert 'job.transition_decision_recommendation = "transition_decision_failed"' in block


def test_transition_decision_block_is_after_clip_duration_optimization_done():
    text = _pipeline_text()

    clip_duration_done_index = text.index('step_name="clip_duration_optimization_done"')
    transition_decision_start_index = text.index(
        "# -- Transition Decision Engine (2B-29-C)"
    )

    assert transition_decision_start_index > clip_duration_done_index


def test_transition_decision_block_is_before_state_analyzing():
    text = _pipeline_text()

    transition_decision_start_index = text.index(
        "# -- Transition Decision Engine (2B-29-C)"
    )
    state_analyzing_index = text.index('event_type="STATE_ANALYZING"', transition_decision_start_index)

    assert transition_decision_start_index < state_analyzing_index


def test_transition_decision_block_does_not_use_timeline_or_highlight_selector():
    block = _transition_decision_block()

    forbidden = [
        "TimelineBuilder",
        "LongformTimelineBuilder",
        "HighlightSelector",
        "highlight_selector",
    ]

    for word in forbidden:
        assert word not in block


def test_transition_decision_block_does_not_execute_render_or_ffmpeg():
    block = _safe_block_for_forbidden_scan()

    forbidden = [
        "ffmpeg",
        "render_processor",
        "finalrenderdriver",
        "final_render_driver",
        "render_video",
        "render_now",
        "execute_cut",
        "final_cut",
    ]

    for word in forbidden:
        assert word not in block


def test_transition_decision_block_does_not_apply_cut_or_transition_actions():
    block = _safe_block_for_forbidden_scan()

    forbidden = [
        "force_cut",
        "auto_remove",
        "hard_remove",
        "remove_now",
        "auto_cut",
        "auto_trim",
        "auto_transition",
        "auto_fade",
        "auto_j_cut",
        "auto_l_cut",
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
        "apply_transition",
    ]

    for word in forbidden:
        assert word not in block


def test_transition_decision_block_logs_review_only_details():
    block = _transition_decision_block()

    assert '"decision_count": transition_decision_report.decision_count' in block
    assert (
        '"hard_cut_review_count": transition_decision_report.hard_cut_review_count'
        in block
    )
    assert '"j_cut_review_count": transition_decision_report.j_cut_review_count' in block
    assert '"l_cut_review_count": transition_decision_report.l_cut_review_count' in block
    assert (
        "transition_decision_report.quick_fade_review_count"
        in block
    )
    assert (
        '"no_cut_protect_count": transition_decision_report.no_cut_protect_count'
        in block
    )
    assert (
        '"censor_safe_keep_count": transition_decision_report.censor_safe_keep_count'
        in block
    )
    assert (
        "transition_decision_report.technical_transition_review_count"
        in block
    )
    assert '"review_only": True' in block


def test_new_test_file_has_no_bom_and_ends_with_newline():
    for file_path in [TEST_FILE, PIPELINE_FILE]:
        raw = file_path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), file_path
        assert raw.endswith(b"\n"), file_path
