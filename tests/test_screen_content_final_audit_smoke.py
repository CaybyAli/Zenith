from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


SCREEN_CONTENT_FILES = [
    "models/screen_content_classification.py",
    "core/screen_content_classifier.py",
    "models/screen_content_source.py",
    "models/screen_content_run.py",
    "core/screen_content_source_selector.py",
    "core/screen_content_runner.py",
    "core/screen_content_signal_adapter.py",
]

SCREEN_CONTENT_TEST_FILES = [
    "tests/test_screen_content_classification_foundation_smoke.py",
    "tests/test_screen_content_source_selector_smoke.py",
    "tests/test_screen_content_runner_smoke.py",
    "tests/test_screen_content_pipeline_integration_smoke.py",
    "tests/test_screen_content_signal_adapter_smoke.py",
    "tests/test_screen_content_registry_integration_smoke.py",
    "tests/test_screen_content_final_audit_smoke.py",
]


def _read_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_all_screen_content_implementation_files_exist():
    for relative_path in SCREEN_CONTENT_FILES:
        assert (REPO_ROOT / relative_path).is_file(), relative_path


def test_all_screen_content_test_files_exist():
    for relative_path in SCREEN_CONTENT_TEST_FILES:
        assert (REPO_ROOT / relative_path).is_file(), relative_path


def test_gaming_pipeline_contains_screen_content_block():
    text = _read_text("core/gaming_pipeline.py")

    assert "Screen Content Classification (2B-17-C)" in text
    assert "run_screen_content_classification_for_job(job)" in text
    assert "apply_screen_content_run_report_to_job(job, screen_content_report)" in text
    assert "SCREEN_CONTENT_STARTED" in text
    assert "SCREEN_CONTENT_DONE" in text
    assert "SCREEN_CONTENT_SKIPPED" in text
    assert "SCREEN_CONTENT_BLOCKED" in text
    assert "SCREEN_CONTENT_FAILED" in text
    assert 'step_name="screen_content_done"' in text


def test_unified_registry_imports_screen_content_adapter():
    text = _read_text("core/unified_edit_signal_registry.py")

    assert (
        "from core.screen_content_signal_adapter "
        "import adapt_screen_content_report_to_signals"
    ) in text


def test_unified_registry_processes_screen_content_source():
    text = _read_text("core/unified_edit_signal_registry.py")

    assert 'SOURCE_SCREEN_CONTENT = "screen_content"' in text
    assert 'screen_content_report = _job_attr(job, "screen_content_report")' in text
    assert 'screen_content_segments = _job_attr(job, "screen_content_segments")' in text
    assert 'screen_content_result = _job_attr(job, "screen_content_result")' in text
    assert "adapt_screen_content_report_to_signals(screen_content_report)" in text
    assert "source_counts[SOURCE_SCREEN_CONTENT]" in text
    assert "_normalize_signal(signal, SOURCE_SCREEN_CONTENT)" in text


def test_screen_content_signal_adapter_has_no_automatic_removal():
    text = _read_text("core/screen_content_signal_adapter.py")

    assert "screen_gameplay_segment" in text
    assert "screen_menu_segment" in text
    assert "screen_lobby_segment" in text
    assert "screen_loading_segment" in text
    assert "screen_scoreboard_segment" in text
    assert "screen_death_segment" in text
    assert "screen_victory_segment" in text
    assert "screen_black_segment" in text
    assert "keep_content_context" in text
    assert "review_possible_trim_loading" in text
    assert "review_possible_trim_black_screen" in text
    assert "remove_now" not in text
    assert "hard_remove" not in text
    assert "auto_remove" not in text
    assert "delete_segment" not in text


def test_final_audit_file_has_no_bom():
    content = (
        REPO_ROOT / "tests" / "test_screen_content_final_audit_smoke.py"
    ).read_bytes()

    assert not content.startswith(b"\xef\xbb\xbf")


def test_final_audit_file_ends_with_newline():
    content = (
        REPO_ROOT / "tests" / "test_screen_content_final_audit_smoke.py"
    ).read_bytes()

    assert content.endswith(b"\n")
