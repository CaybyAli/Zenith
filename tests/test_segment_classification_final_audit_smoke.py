from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


PRODUCT_FILES = [
    ROOT / "models" / "segment_classification.py",
    ROOT / "core" / "segment_classifier.py",
    ROOT / "models" / "segment_classification_run.py",
    ROOT / "core" / "segment_classification_runner.py",
    ROOT / "core" / "segment_classification_signal_adapter.py",
]

CHANGED_CORE_FILES = [
    ROOT / "core" / "gaming_pipeline.py",
    ROOT / "core" / "unified_edit_signal_registry.py",
    ROOT / "models" / "job.py",
]

TEST_FILES = [
    ROOT / "tests" / "test_segment_classifier_foundation_smoke.py",
    ROOT / "tests" / "test_segment_classification_runner_smoke.py",
    ROOT / "tests" / "test_segment_classification_pipeline_integration_smoke.py",
    ROOT / "tests" / "test_segment_classification_signal_adapter_smoke.py",
    ROOT / "tests" / "test_segment_classification_registry_integration_smoke.py",
    ROOT / "tests" / "test_segment_classification_final_audit_smoke.py",
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


def test_all_2b25_product_files_exist() -> None:
    for path in PRODUCT_FILES:
        assert path.exists(), f"Missing product file: {path}"


def test_all_2b25_test_files_exist() -> None:
    for path in TEST_FILES:
        assert path.exists(), f"Missing test file: {path}"


def test_job_fields_exist() -> None:
    text = _read(ROOT / "models" / "job.py")

    expected_fields = [
        "segment_classification_report",
        "segment_classification_status",
        "segment_classification_segments",
        "segment_classification_segment_count",
        "segment_classification_highlight_count",
        "segment_classification_hook_candidate_count",
        "segment_classification_protected_context_count",
        "segment_classification_dead_candidate_count",
        "segment_classification_filler_count",
        "segment_classification_transition_count",
        "segment_classification_censor_required_count",
        "segment_classification_technical_warning_count",
        "segment_classification_recommendation",
    ]

    for field in expected_fields:
        assert field in text


def test_pipeline_contains_segment_classification_block() -> None:
    text = _read(ROOT / "core" / "gaming_pipeline.py")

    assert "from core.segment_classification_runner import (" in text
    assert "run_segment_classification_for_job" in text
    assert "apply_segment_classification_run_report_to_job" in text
    assert "SEGMENT_CLASSIFICATION_STARTED" in text
    assert "SEGMENT_CLASSIFICATION_DONE" in text
    assert "SEGMENT_CLASSIFICATION_SKIPPED" in text
    assert "SEGMENT_CLASSIFICATION_FAILED" in text
    assert 'step_name="segment_classification_done"' in text


def test_pipeline_position_is_after_unified_registry() -> None:
    text = _read(ROOT / "core" / "gaming_pipeline.py")

    unified_position = text.index('step_name="unified_edit_signals_done"')
    segment_position = text.index("# ── Segment Classification (2B-25-C)")

    assert unified_position < segment_position


def test_registry_imports_and_processes_segment_classifier() -> None:
    text = _read(ROOT / "core" / "unified_edit_signal_registry.py")

    assert "adapt_segment_classification_report_to_signals" in text
    assert 'SOURCE_SEGMENT_CLASSIFIER = "segment_classifier"' in text
    assert "_job_attr(job, \"segment_classification_report\")" in text
    assert "\"segment_classification_segments\"" in text
    assert "source_counts[SOURCE_SEGMENT_CLASSIFIER]" in text
    assert "_normalize_signal(signal, SOURCE_SEGMENT_CLASSIFIER)" in text


def test_safety_no_forbidden_strings_in_new_product_files() -> None:
    for path in PRODUCT_FILES:
        text = _read(path).lower()
        for forbidden in FORBIDDEN_STRINGS:
            assert forbidden not in text, f"{forbidden} found in {path}"


def test_pipeline_segment_block_has_no_forbidden_cut_logic() -> None:
    text = _read(ROOT / "core" / "gaming_pipeline.py").lower()
    start = text.index("# ── segment classification (2b-25-c)")
    end = text.index("# ── end segment classification")
    block = text[start:end]

    for forbidden in FORBIDDEN_STRINGS:
        assert forbidden not in block, f"{forbidden} found in pipeline segment block"

    extra_forbidden = [
        "ffmpeg",
        "timelinebuilder",
        "timeline_builder",
        "longformtimelinebuilder",
        "highlightselector",
        "highlight_selector",
        "build_timeline",
        "final_cutlist",
    ]

    for forbidden in extra_forbidden:
        assert forbidden not in block, f"{forbidden} found in pipeline segment block"


def test_files_have_no_bom_and_end_with_newline() -> None:
    for path in PRODUCT_FILES + CHANGED_CORE_FILES + TEST_FILES:
        content = path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert content.endswith(b"\n"), f"{path} does not end with newline"
