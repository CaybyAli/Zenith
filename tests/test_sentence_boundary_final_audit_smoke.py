from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from types import SimpleNamespace

from core.unified_edit_signal_registry import build_unified_edit_signal_result
from models.job import Job


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PRODUCT_FILES = [
    "models/sentence_boundary.py",
    "core/sentence_boundary_protector.py",
    "models/sentence_boundary_run.py",
    "core/sentence_boundary_runner.py",
    "core/sentence_boundary_signal_adapter.py",
    "core/gaming_pipeline.py",
    "core/unified_edit_signal_registry.py",
    "models/job.py",
]
TEST_FILES = [
    "tests/test_sentence_boundary_foundation_smoke.py",
    "tests/test_sentence_boundary_runner_smoke.py",
    "tests/test_sentence_boundary_pipeline_integration_smoke.py",
    "tests/test_sentence_boundary_signal_adapter_smoke.py",
    "tests/test_sentence_boundary_registry_integration_smoke.py",
    "tests/test_sentence_boundary_final_audit_smoke.py",
]
FORBIDDEN_PRODUCT_STRINGS = [
    "force_cut",
    "auto_remove",
    "hard_remove",
    "remove_now",
    "cut_sentence_now",
    "auto_cut",
    "auto_trim",
    "timeline_apply_now",
    "highlight_now",
]


def _path(relative_path: str) -> Path:
    return PROJECT_ROOT / relative_path


def _read(relative_path: str) -> str:
    return _path(relative_path).read_text(encoding="utf-8")


def test_all_2b20_product_files_exist() -> None:
    for relative_path in PRODUCT_FILES[:5]:
        assert _path(relative_path).is_file(), f"Missing 2B-20 file: {relative_path}"


def test_all_2b20_tests_exist() -> None:
    for relative_path in TEST_FILES:
        assert _path(relative_path).is_file(), f"Missing 2B-20 test: {relative_path}"


def test_job_has_sentence_boundary_fields() -> None:
    field_names = {field.name for field in fields(Job)}
    required_fields = {
        "sentence_boundary_report",
        "sentence_boundary_status",
        "sentence_boundary_boundaries",
        "sentence_boundary_protection_zones",
        "sentence_boundary_boundary_count",
        "sentence_boundary_protection_zone_count",
        "sentence_boundary_complete_sentence_count",
        "sentence_boundary_open_fragment_count",
        "sentence_boundary_question_count",
        "sentence_boundary_open_question_count",
        "sentence_boundary_safe_boundary_count",
        "sentence_boundary_unsafe_boundary_count",
        "sentence_boundary_recommendation",
    }

    missing = required_fields - field_names
    assert not missing, f"Missing sentence boundary Job fields: {sorted(missing)}"


def test_pipeline_contains_sentence_boundary_block() -> None:
    source = _read("core/gaming_pipeline.py")

    assert "SENTENCE_BOUNDARY_STARTED" in source
    assert "run_sentence_boundary_for_job(" in source
    assert "apply_sentence_boundary_run_report_to_job(" in source
    assert 'step_name="sentence_boundary_done"' in source


def test_pipeline_position_is_after_transcript_and_before_filler_word() -> None:
    source = _read("core/gaming_pipeline.py")

    transcript_index = source.index("TRANSCRIPT_DONE")
    sentence_boundary_index = source.index("SENTENCE_BOUNDARY_STARTED")
    filler_index = source.index("FILLER_WORD_DETECTION_STARTED")

    assert transcript_index < sentence_boundary_index < filler_index


def test_registry_imports_sentence_boundary_adapter() -> None:
    source = _read("core/unified_edit_signal_registry.py")

    assert "from core.sentence_boundary_signal_adapter import" in source
    assert "adapt_sentence_boundary_report_to_signals" in source


def test_registry_processes_sentence_boundary_source() -> None:
    job = SimpleNamespace(
        energy_peak_report={},
        filler_word_report={},
        audio_normalization_report={},
        beat_detection_report={},
        silence_detection_report={},
        silence_classifications=[],
        sentence_boundary_report={
            "boundaries": [
                {
                    "boundary_id": "safe_1",
                    "start_seconds": 1.0,
                    "end_seconds": 2.0,
                    "center_seconds": 1.5,
                    "text": "Complete sentence.",
                    "boundary_type": "safe_sentence_boundary",
                    "protection_level": "none",
                    "confidence": 0.8,
                    "recommendation": "boundary_safe_for_review",
                    "warnings": [],
                    "errors": [],
                }
            ],
            "protection_zones": [],
        },
    )

    result = build_unified_edit_signal_result(job)

    assert result.source_counts["sentence_boundary"] == 1
    assert result.type_counts["sentence_safe_boundary"] == 1


def test_no_automatic_cut_or_remove_logic_in_2b20_product_files() -> None:
    for relative_path in PRODUCT_FILES:
        source = _read(relative_path)
        for forbidden in FORBIDDEN_PRODUCT_STRINGS:
            assert forbidden not in source, f"{forbidden} found in {relative_path}"


def test_2b20_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in PRODUCT_FILES + TEST_FILES:
        content = _path(relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{relative_path} has UTF-8 BOM"
        assert content.endswith(b"\n"), f"{relative_path} must end with newline"
