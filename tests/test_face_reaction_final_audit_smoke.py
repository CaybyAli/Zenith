from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


FACE_REACTION_FILES = [
    "models/face_reaction_analysis.py",
    "core/face_reaction_analyzer.py",
    "models/face_reaction_source.py",
    "models/face_reaction_run.py",
    "core/face_reaction_source_selector.py",
    "core/face_reaction_runner.py",
    "core/face_reaction_signal_adapter.py",
]

FACE_REACTION_TEST_FILES = [
    "tests/test_face_reaction_analysis_foundation_smoke.py",
    "tests/test_face_reaction_source_selector_smoke.py",
    "tests/test_face_reaction_runner_smoke.py",
    "tests/test_face_reaction_pipeline_integration_smoke.py",
    "tests/test_face_reaction_signal_adapter_smoke.py",
    "tests/test_face_reaction_registry_integration_smoke.py",
    "tests/test_face_reaction_final_audit_smoke.py",
]


def _read_text(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_all_face_reaction_implementation_files_exist():
    for relative_path in FACE_REACTION_FILES:
        assert (REPO_ROOT / relative_path).is_file(), relative_path


def test_all_face_reaction_test_files_exist():
    for relative_path in FACE_REACTION_TEST_FILES:
        assert (REPO_ROOT / relative_path).is_file(), relative_path


def test_gaming_pipeline_contains_face_reaction_block():
    text = _read_text("core/gaming_pipeline.py")

    assert "Face Reaction Analysis (2B-15-C)" in text
    assert "run_face_reaction_for_job(job)" in text
    assert "apply_face_reaction_run_report_to_job(job, face_reaction_report)" in text
    assert "FACE_REACTION_STARTED" in text
    assert "FACE_REACTION_DONE" in text
    assert "FACE_REACTION_SKIPPED" in text
    assert "FACE_REACTION_BLOCKED" in text
    assert "FACE_REACTION_FAILED" in text
    assert 'step_name="face_reaction_done"' in text


def test_unified_registry_imports_face_reaction_adapter():
    text = _read_text("core/unified_edit_signal_registry.py")

    assert (
        "from core.face_reaction_signal_adapter "
        "import adapt_face_reaction_report_to_signals"
    ) in text


def test_unified_registry_processes_face_reaction_source():
    text = _read_text("core/unified_edit_signal_registry.py")

    assert 'SOURCE_FACE_REACTION = "face_reaction"' in text
    assert "face_reaction_report = _job_attr(job, \"face_reaction_report\")" in text
    assert "face_reaction_segments = _job_attr(job, \"face_reaction_segments\")" in text
    assert "face_reaction_result = _job_attr(job, \"face_reaction_result\")" in text
    assert "adapt_face_reaction_report_to_signals(face_reaction_report)" in text
    assert "source_counts[SOURCE_FACE_REACTION]" in text
    assert "_normalize_signal(signal, SOURCE_FACE_REACTION)" in text


def test_face_reaction_signal_adapter_has_no_automatic_zoom_or_render_action():
    text = _read_text("core/face_reaction_signal_adapter.py")

    assert "face_high_reaction_segment" in text
    assert "face_shock_reaction_candidate" in text
    assert "face_laugh_reaction_candidate" in text
    assert "face_mouth_open_candidate" in text
    assert "face_neutral_presence_segment" in text
    assert "execute_zoom" not in text
    assert "auto_zoom" not in text
    assert "render_command" not in text
    assert "FinalRenderDriver" not in text


def test_final_audit_file_has_no_bom():
    content = (REPO_ROOT / "tests" / "test_face_reaction_final_audit_smoke.py").read_bytes()

    assert not content.startswith(b"\xef\xbb\xbf")


def test_final_audit_file_ends_with_newline():
    content = (REPO_ROOT / "tests" / "test_face_reaction_final_audit_smoke.py").read_bytes()

    assert content.endswith(b"\n")
