from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_FILE = ROOT / "core" / "gaming_pipeline.py"
TEST_FILE = ROOT / "tests" / "test_continuity_check_pipeline_integration_smoke.py"


def _pipeline_text() -> str:
    return PIPELINE_FILE.read_text(encoding="utf-8")


def _continuity_check_block() -> str:
    text = _pipeline_text()
    start_marker = "# -- Continuity Check (2B-30-C)"
    end_marker = "# -- End Continuity Check"

    assert start_marker in text
    assert end_marker in text

    start = text.index(start_marker)
    end = text.index(end_marker, start)

    return text[start:end]


def _safe_block_for_forbidden_scan() -> str:
    return _continuity_check_block().lower()


def test_continuity_check_runner_imports_exist():
    text = _pipeline_text()

    assert "from core.continuity_check_runner import (" in text
    assert "apply_continuity_check_run_report_to_job" in text
    assert "run_continuity_check_for_job" in text


def test_continuity_check_events_exist():
    text = _pipeline_text()

    assert "CONTINUITY_CHECK_STARTED" in text
    assert "CONTINUITY_CHECK_DONE" in text
    assert "CONTINUITY_CHECK_SKIPPED" in text
    assert "CONTINUITY_CHECK_FAILED" in text


def test_continuity_check_checkpoint_exists():
    text = _pipeline_text()

    assert 'step_name="continuity_check_done"' in text


def test_continuity_check_runner_and_apply_are_used():
    block = _continuity_check_block()

    assert "run_continuity_check_for_job(" in block
    assert "apply_continuity_check_run_report_to_job(" in block
    assert "continuity_check_report = run_continuity_check_for_job" in block


def test_continuity_check_block_has_safe_try_except():
    block = _continuity_check_block()

    assert "try:" in block
    assert "except Exception as continuity_check_exc:" in block
    assert 'job.continuity_check_status = "failed"' in block
    assert 'job.continuity_check_recommendation = "continuity_check_failed"' in block


def test_continuity_check_block_is_after_transition_decision_done():
    text = _pipeline_text()

    transition_decision_done_index = text.index('step_name="transition_decision_done"')
    continuity_check_start_index = text.index("# -- Continuity Check (2B-30-C)")

    assert continuity_check_start_index > transition_decision_done_index


def test_continuity_check_block_is_before_state_analyzing():
    text = _pipeline_text()

    continuity_check_start_index = text.index("# -- Continuity Check (2B-30-C)")
    state_analyzing_index = text.index('event_type="STATE_ANALYZING"', continuity_check_start_index)

    assert continuity_check_start_index < state_analyzing_index


def test_continuity_check_block_does_not_use_timeline_or_highlight_selector():
    block = _continuity_check_block()

    forbidden = [
        "TimelineBuilder",
        "LongformTimelineBuilder",
        "HighlightSelector",
        "highlight_selector",
    ]

    for word in forbidden:
        assert word not in block


def test_continuity_check_block_does_not_execute_render_or_ffmpeg():
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


def test_continuity_check_block_does_not_apply_cut_or_transition_actions():
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


def test_continuity_check_block_logs_review_only_details():
    block = _continuity_check_block()

    assert '"issue_count": continuity_check_report.issue_count' in block
    assert '"blocking_issue_count": continuity_check_report.blocking_issue_count' in block
    assert (
        "continuity_check_report.sentence_break_risk_count"
        in block
    )
    assert (
        "continuity_check_report.context_jump_risk_count"
        in block
    )
    assert (
        "continuity_check_report.censor_context_risk_count"
        in block
    )
    assert "continuity_check_report.transition_conflict_count" in block
    assert '"review_only": True' in block


def test_new_test_file_has_no_bom_and_ends_with_newline():
    for file_path in [TEST_FILE, PIPELINE_FILE]:
        raw = file_path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), file_path
        assert raw.endswith(b"\n"), file_path
