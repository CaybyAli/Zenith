from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


STUTTER_DETECTION_FILES = [
    "models/stutter_detection.py",
    "core/stutter_detector.py",
    "models/stutter_detection_source.py",
    "models/stutter_detection_run.py",
    "core/stutter_detection_source_selector.py",
    "core/stutter_detection_runner.py",
    "core/stutter_detection_signal_adapter.py",
]

STUTTER_DETECTION_TEST_FILES = [
    "tests/test_stutter_detection_foundation_smoke.py",
    "tests/test_stutter_detection_source_selector_smoke.py",
    "tests/test_stutter_detection_runner_smoke.py",
    "tests/test_stutter_detection_pipeline_integration_smoke.py",
    "tests/test_stutter_detection_signal_adapter_smoke.py",
    "tests/test_stutter_detection_registry_integration_smoke.py",
    "tests/test_stutter_detection_final_audit_smoke.py",
]


def _read_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_all_stutter_detection_implementation_files_exist():
    for relative_path in STUTTER_DETECTION_FILES:
        assert (REPO_ROOT / relative_path).is_file(), relative_path


def test_all_stutter_detection_test_files_exist():
    for relative_path in STUTTER_DETECTION_TEST_FILES:
        assert (REPO_ROOT / relative_path).is_file(), relative_path


def test_gaming_pipeline_contains_stutter_detection_block():
    text = _read_text("core/gaming_pipeline.py")

    assert "Stutter Detection (2B-16-C)" in text
    assert "run_stutter_detection_for_job(job)" in text
    assert (
        "apply_stutter_detection_run_report_to_job(job, stutter_detection_report)"
        in text
    )
    assert "STUTTER_DETECTION_STARTED" in text
    assert "STUTTER_DETECTION_DONE" in text
    assert "STUTTER_DETECTION_SKIPPED" in text
    assert "STUTTER_DETECTION_BLOCKED" in text
    assert "STUTTER_DETECTION_FAILED" in text
    assert 'step_name="stutter_detection_done"' in text


def test_unified_registry_imports_stutter_detection_adapter():
    text = _read_text("core/unified_edit_signal_registry.py")

    assert (
        "from core.stutter_detection_signal_adapter "
        "import adapt_stutter_detection_report_to_signals"
    ) in text


def test_unified_registry_processes_stutter_detection_source():
    text = _read_text("core/unified_edit_signal_registry.py")

    assert 'SOURCE_STUTTER_DETECTION = "stutter_detection"' in text
    assert (
        "stutter_detection_report = _job_attr(job, \"stutter_detection_report\")"
        in text
    )
    assert (
        "stutter_detection_segments = _job_attr(job, \"stutter_detection_segments\")"
        in text
    )
    assert (
        "stutter_detection_result = _job_attr(job, \"stutter_detection_result\")"
        in text
    )
    assert (
        "adapt_stutter_detection_report_to_signals(stutter_detection_report)"
        in text
    )
    assert "source_counts[SOURCE_STUTTER_DETECTION]" in text
    assert "_normalize_signal(signal, SOURCE_STUTTER_DETECTION)" in text


def test_stutter_detection_signal_adapter_has_no_automatic_removal():
    text = _read_text("core/stutter_detection_signal_adapter.py")

    assert "stutter_segment_candidate" in text
    assert "freeze_segment_candidate" in text
    assert "encoding_drop_candidate" in text
    assert "review_stutter_segment" in text
    assert "review_freeze_segment" in text
    assert "review_encoding_drop_candidate" in text
    assert "remove_now" not in text
    assert "hard_remove" not in text
    assert "auto_remove" not in text
    assert "delete_segment" not in text


def test_final_audit_file_has_no_bom():
    content = (REPO_ROOT / "tests" / "test_stutter_detection_final_audit_smoke.py").read_bytes()

    assert not content.startswith(b"\xef\xbb\xbf")


def test_final_audit_file_ends_with_newline():
    content = (REPO_ROOT / "tests" / "test_stutter_detection_final_audit_smoke.py").read_bytes()

    assert content.endswith(b"\n")
