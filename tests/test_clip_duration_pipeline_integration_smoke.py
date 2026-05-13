from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PIPELINE_FILE = ROOT / "core" / "gaming_pipeline.py"
TEST_FILE = ROOT / "tests" / "test_clip_duration_pipeline_integration_smoke.py"


def _pipeline_text() -> str:
    return PIPELINE_FILE.read_text(encoding="utf-8")


def _clip_duration_block() -> str:
    text = _pipeline_text()
    start_marker = "# -- Clip Duration Optimization (2B-28-C)"
    end_marker = "# -- End Clip Duration Optimization"

    assert start_marker in text
    assert end_marker in text

    start = text.index(start_marker)
    end = text.index(end_marker, start)

    return text[start:end]


def test_clip_duration_runner_imports_exist():
    text = _pipeline_text()

    assert "from core.clip_duration_runner import (" in text
    assert "apply_clip_duration_run_report_to_job" in text
    assert "run_clip_duration_optimization_for_job" in text


def test_clip_duration_events_exist():
    text = _pipeline_text()

    assert "CLIP_DURATION_OPTIMIZATION_STARTED" in text
    assert "CLIP_DURATION_OPTIMIZATION_DONE" in text
    assert "CLIP_DURATION_OPTIMIZATION_SKIPPED" in text
    assert "CLIP_DURATION_OPTIMIZATION_FAILED" in text


def test_clip_duration_checkpoint_exists():
    text = _pipeline_text()

    assert 'step_name="clip_duration_optimization_done"' in text


def test_clip_duration_runner_and_apply_are_used():
    block = _clip_duration_block()

    assert "run_clip_duration_optimization_for_job(" in block
    assert "apply_clip_duration_run_report_to_job(" in block
    assert "clip_duration_report = run_clip_duration_optimization_for_job" in block


def test_clip_duration_block_has_safe_try_except():
    block = _clip_duration_block()

    assert "try:" in block
    assert "except Exception as clip_duration_optimization_exc:" in block
    assert 'job.clip_duration_status = "failed"' in block
    assert 'job.clip_duration_recommendation = "clip_duration_optimization_failed"' in block


def test_clip_duration_block_is_after_cut_list_generation_done():
    text = _pipeline_text()

    cut_list_done_index = text.index('step_name="cut_list_generation_done"')
    clip_duration_start_index = text.index("# -- Clip Duration Optimization (2B-28-C)")

    assert clip_duration_start_index > cut_list_done_index


def test_clip_duration_block_does_not_use_timeline_or_highlight_selector():
    block = _clip_duration_block()

    forbidden = [
        "TimelineBuilder",
        "LongformTimelineBuilder",
        "HighlightSelector",
        "highlight_selector",
    ]

    for word in forbidden:
        assert word not in block


def test_clip_duration_block_does_not_execute_render_or_ffmpeg():
    block = _clip_duration_block().lower()

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


def test_clip_duration_block_does_not_apply_timeline_or_cut_actions():
    block = _clip_duration_block().lower()

    forbidden = [
        "force_cut",
        "auto_remove",
        "hard_remove",
        "remove_now",
        "auto_cut",
        "auto_trim",
        "auto_extend",
        "auto_highlight",
        "highlight_now",
        "auto_hook",
        "auto_mute",
        "censor_now",
        "delete_segment",
        "drop_segment",
        "timeline_apply_now",
        "apply_cut",
    ]

    for word in forbidden:
        assert word not in block


def test_clip_duration_block_logs_review_only_details():
    block = _clip_duration_block()

    assert '"recommendation_count": clip_duration_report.recommendation_count' in block
    assert '"too_short_count": clip_duration_report.too_short_count' in block
    assert '"too_long_count": clip_duration_report.too_long_count' in block
    assert '"protect_duration_count": clip_duration_report.protect_duration_count' in block
    assert '"censor_keep_count": clip_duration_report.censor_keep_count' in block
    assert '"invalid_timing_count": clip_duration_report.invalid_timing_count' in block


def test_new_test_file_has_no_bom_and_ends_with_newline():
    for file_path in [TEST_FILE, PIPELINE_FILE]:
        raw = file_path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), file_path
        assert raw.endswith(b"\n"), file_path
