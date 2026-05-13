from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PRODUCT_FILES = [
    ROOT / "models" / "murch_scoring.py",
    ROOT / "core" / "murch_scoring_system.py",
    ROOT / "models" / "murch_scoring_run.py",
    ROOT / "core" / "murch_scoring_runner.py",
    ROOT / "core" / "murch_scoring_signal_adapter.py",
]

REQUIRED_FILES = [
    *PRODUCT_FILES,
    ROOT / "core" / "gaming_pipeline.py",
    ROOT / "core" / "unified_edit_signal_registry.py",
    ROOT / "models" / "job.py",
]

REQUIRED_TESTS = [
    ROOT / "tests" / "test_murch_scoring_foundation_smoke.py",
    ROOT / "tests" / "test_murch_scoring_runner_smoke.py",
    ROOT / "tests" / "test_murch_scoring_pipeline_integration_smoke.py",
    ROOT / "tests" / "test_murch_scoring_signal_adapter_smoke.py",
    ROOT / "tests" / "test_murch_scoring_registry_integration_smoke.py",
    ROOT / "tests" / "test_murch_scoring_final_audit_smoke.py",
]

FORBIDDEN_STRINGS = [
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
]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _murch_pipeline_block() -> str:
    text = _read(ROOT / "core" / "gaming_pipeline.py")
    start = text.index("# ── Murch Scoring (2B-26-C)")
    end = text.index("# ── End Murch Scoring", start)
    return text[start:end]


def test_all_2b26_product_files_exist() -> None:
    for path in REQUIRED_FILES:
        assert path.exists(), f"Missing required file: {path}"


def test_all_2b26_tests_exist() -> None:
    for path in REQUIRED_TESTS:
        assert path.exists(), f"Missing required test: {path}"


def test_job_fields_exist() -> None:
    text = _read(ROOT / "models" / "job.py")

    required_fields = [
        "murch_scoring_report",
        "murch_scoring_status",
        "murch_scoring_segment_scores",
        "murch_scoring_segment_score_count",
        "murch_scoring_high_score_count",
        "murch_scoring_medium_score_count",
        "murch_scoring_low_score_count",
        "murch_scoring_protected_context_count",
        "murch_scoring_censor_required_count",
        "murch_scoring_technical_warning_count",
        "murch_scoring_avg_score",
        "murch_scoring_max_score",
        "murch_scoring_min_score",
        "murch_scoring_recommendation",
    ]

    for field in required_fields:
        assert field in text


def test_pipeline_contains_murch_scoring_block() -> None:
    text = _read(ROOT / "core" / "gaming_pipeline.py")
    block = _murch_pipeline_block()

    assert "from core.murch_scoring_runner import (" in text
    assert "run_murch_scoring_for_job" in block
    assert "apply_murch_scoring_run_report_to_job" in block
    assert "MURCH_SCORING_STARTED" in block
    assert "MURCH_SCORING_DONE" in block
    assert "MURCH_SCORING_SKIPPED" in block
    assert "MURCH_SCORING_FAILED" in block
    assert 'step_name="murch_scoring_done"' in block


def test_pipeline_position_is_after_segment_classification() -> None:
    text = _read(ROOT / "core" / "gaming_pipeline.py")

    segment_checkpoint = text.index('step_name="segment_classification_done"')
    murch_started = text.index('event_type="MURCH_SCORING_STARTED"')

    assert segment_checkpoint < murch_started


def test_registry_imports_and_processes_murch_scoring() -> None:
    text = _read(ROOT / "core" / "unified_edit_signal_registry.py")

    assert "adapt_murch_scoring_report_to_signals" in text
    assert 'SOURCE_MURCH_SCORING = "murch_scoring"' in text
    assert '_job_attr(job, "murch_scoring_report")' in text
    assert '"murch_scoring_segment_scores"' in text
    assert "source_counts[SOURCE_MURCH_SCORING]" in text
    assert "_normalize_signal(signal, SOURCE_MURCH_SCORING)" in text


def test_murch_signal_types_are_supported() -> None:
    text = _read(ROOT / "core" / "murch_scoring_signal_adapter.py")

    required_signal_types = [
        "murch_high_score_segment",
        "murch_medium_score_segment",
        "murch_low_score_segment",
        "murch_protected_context",
        "murch_technical_warning",
        "murch_censor_required_context",
        "murch_emotion_high",
        "murch_story_high",
    ]

    for signal_type in required_signal_types:
        assert signal_type in text


def test_safety_no_forbidden_actions_in_murch_product_files() -> None:
    for path in PRODUCT_FILES:
        text = _read(path)

        for forbidden in FORBIDDEN_STRINGS:
            assert forbidden not in text, f"{forbidden} found in {path}"


def test_safety_no_forbidden_actions_in_murch_pipeline_block() -> None:
    block = _murch_pipeline_block()

    for forbidden in FORBIDDEN_STRINGS:
        assert forbidden not in block, f"{forbidden} found in Murch pipeline block"


def test_no_timeline_builder_or_highlight_selector_in_murch_pipeline_block() -> None:
    block = _murch_pipeline_block()

    forbidden = [
        "TimelineBuilder",
        "LongformTimelineBuilder",
        "HighlightSelector",
        "final_cutlist",
        "cut_list",
    ]

    for item in forbidden:
        assert item not in block


def test_files_have_no_bom_and_end_with_newline() -> None:
    files = REQUIRED_FILES + REQUIRED_TESTS

    for path in files:
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert data.endswith(b"\n"), f"{path} does not end with newline"
