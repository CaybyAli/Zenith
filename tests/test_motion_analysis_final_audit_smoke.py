from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


MOTION_ANALYSIS_FILES = [
    "models/motion_analysis.py",
    "core/motion_analyzer.py",
    "models/motion_analysis_source.py",
    "models/motion_analysis_run.py",
    "core/motion_analysis_source_selector.py",
    "core/motion_analysis_runner.py",
    "core/motion_analysis_signal_adapter.py",
]

MOTION_ANALYSIS_TEST_FILES = [
    "tests/test_motion_analysis_foundation_smoke.py",
    "tests/test_motion_analysis_source_selector_smoke.py",
    "tests/test_motion_analysis_runner_smoke.py",
    "tests/test_motion_analysis_pipeline_integration_smoke.py",
    "tests/test_motion_analysis_signal_adapter_smoke.py",
    "tests/test_motion_analysis_registry_integration_smoke.py",
]


def _read_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_all_motion_analysis_implementation_files_exist():
    for relative_path in MOTION_ANALYSIS_FILES:
        assert (REPO_ROOT / relative_path).is_file(), relative_path


def test_all_motion_analysis_test_files_exist():
    for relative_path in MOTION_ANALYSIS_TEST_FILES:
        assert (REPO_ROOT / relative_path).is_file(), relative_path


def test_gaming_pipeline_contains_motion_analysis_block():
    text = _read_text("core/gaming_pipeline.py")

    assert "Motion Analysis (2B-14-C)" in text
    assert "run_motion_analysis_for_job(job)" in text
    assert "apply_motion_analysis_run_report_to_job(job, motion_analysis_report)" in text
    assert "MOTION_ANALYSIS_STARTED" in text
    assert "MOTION_ANALYSIS_DONE" in text
    assert 'step_name="motion_analysis_done"' in text


def test_unified_registry_imports_motion_analysis_adapter():
    text = _read_text("core/unified_edit_signal_registry.py")

    assert (
        "from core.motion_analysis_signal_adapter "
        "import adapt_motion_analysis_report_to_signals"
    ) in text


def test_unified_registry_processes_motion_analysis_source():
    text = _read_text("core/unified_edit_signal_registry.py")

    assert 'SOURCE_MOTION_ANALYSIS = "motion_analysis"' in text
    assert "motion_analysis_report = _job_attr(job, \"motion_analysis_report\")" in text
    assert "motion_analysis_segments = _job_attr(job, \"motion_analysis_segments\")" in text
    assert "motion_analysis_result = _job_attr(job, \"motion_analysis_result\")" in text
    assert "adapt_motion_analysis_report_to_signals(motion_analysis_report)" in text
    assert "source_counts[SOURCE_MOTION_ANALYSIS]" in text
    assert "_normalize_signal(signal, SOURCE_MOTION_ANALYSIS)" in text


def test_motion_analysis_signal_adapter_keeps_dead_visual_safe():
    text = _read_text("core/motion_analysis_signal_adapter.py")

    assert "motion_dead_visual_candidate" in text
    assert "review_or_trim_dead_visual" in text
    assert "remove_now" not in text
    assert "hard_remove" not in text
    assert "auto_remove" not in text


def test_final_audit_file_has_no_bom():
    content = (REPO_ROOT / "tests" / "test_motion_analysis_final_audit_smoke.py").read_bytes()

    assert not content.startswith(b"\xef\xbb\xbf")


def test_final_audit_file_ends_with_newline():
    content = (REPO_ROOT / "tests" / "test_motion_analysis_final_audit_smoke.py").read_bytes()

    assert content.endswith(b"\n")
