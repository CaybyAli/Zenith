from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from types import SimpleNamespace

from core.unified_edit_signal_registry import build_unified_edit_signal_result
from models.job import Job


PROJECT_ROOT = Path(__file__).resolve().parents[1]

PRODUCT_FILES = [
    "models/keyword_emotion.py",
    "core/keyword_emotion_scorer.py",
    "models/keyword_emotion_run.py",
    "core/keyword_emotion_runner.py",
    "core/keyword_emotion_signal_adapter.py",
    "core/gaming_pipeline.py",
    "core/unified_edit_signal_registry.py",
    "models/job.py",
]
TEST_FILES = [
    "tests/test_keyword_emotion_foundation_smoke.py",
    "tests/test_keyword_emotion_runner_smoke.py",
    "tests/test_keyword_emotion_pipeline_integration_smoke.py",
    "tests/test_keyword_emotion_signal_adapter_smoke.py",
    "tests/test_keyword_emotion_registry_integration_smoke.py",
    "tests/test_keyword_emotion_final_audit_smoke.py",
]
FORBIDDEN_PRODUCT_STRINGS = [
    "force_cut",
    "auto_remove",
    "hard_remove",
    "remove_now",
    "auto_cut",
    "auto_trim",
    "auto_highlight",
    "highlight_now",
    "timeline_apply_now",
]


def _path(relative_path: str) -> Path:
    return PROJECT_ROOT / relative_path


def _read(relative_path: str) -> str:
    return _path(relative_path).read_text(encoding="utf-8")


def test_all_2b21_product_files_exist() -> None:
    for relative_path in PRODUCT_FILES[:5]:
        assert _path(relative_path).is_file(), f"Missing 2B-21 file: {relative_path}"


def test_all_2b21_tests_exist() -> None:
    for relative_path in TEST_FILES:
        assert _path(relative_path).is_file(), f"Missing 2B-21 test: {relative_path}"


def test_job_has_keyword_emotion_fields() -> None:
    field_names = {field.name for field in fields(Job)}
    required_fields = {
        "keyword_emotion_report",
        "keyword_emotion_status",
        "keyword_emotion_matches",
        "keyword_emotion_segment_scores",
        "keyword_emotion_match_count",
        "keyword_emotion_segment_score_count",
        "keyword_emotion_hype_match_count",
        "keyword_emotion_frustration_match_count",
        "keyword_emotion_shock_match_count",
        "keyword_emotion_laugh_match_count",
        "keyword_emotion_question_match_count",
        "keyword_emotion_high_value_segment_count",
        "keyword_emotion_recommendation",
    }

    missing = required_fields - field_names
    assert not missing, f"Missing keyword emotion Job fields: {sorted(missing)}"


def test_pipeline_contains_keyword_emotion_block() -> None:
    source = _read("core/gaming_pipeline.py")

    assert "KEYWORD_EMOTION_STARTED" in source
    assert "run_keyword_emotion_for_job(" in source
    assert "apply_keyword_emotion_run_report_to_job(" in source
    assert 'step_name="keyword_emotion_done"' in source


def test_pipeline_position_is_after_sentence_boundary_and_before_filler_word() -> None:
    source = _read("core/gaming_pipeline.py")

    sentence_boundary_index = source.index("SENTENCE_BOUNDARY_STARTED")
    keyword_emotion_index = source.index("KEYWORD_EMOTION_STARTED")
    filler_index = source.index("FILLER_WORD_DETECTION_STARTED")

    assert sentence_boundary_index < keyword_emotion_index < filler_index


def test_registry_imports_keyword_emotion_adapter() -> None:
    source = _read("core/unified_edit_signal_registry.py")

    assert "from core.keyword_emotion_signal_adapter import" in source
    assert "adapt_keyword_emotion_report_to_signals" in source


def test_registry_processes_keyword_emotion_source() -> None:
    job = SimpleNamespace(
        energy_peak_report={},
        filler_word_report={},
        audio_normalization_report={},
        beat_detection_report={},
        silence_detection_report={},
        silence_classifications=[],
        sentence_boundary_report={},
        keyword_emotion_report={
            "segment_scores": [
                {
                    "segment_id": "kw_1",
                    "start_seconds": 1.0,
                    "end_seconds": 2.0,
                    "duration_seconds": 1.0,
                    "text": "insane",
                    "categories": {"hype": 0.8},
                    "dominant_category": "hype",
                    "overall_keyword_score": 0.7,
                    "match_count": 1,
                    "recommendation": "review_high_value_keyword_segment",
                    "metadata": {},
                    "warnings": [],
                    "errors": [],
                }
            ]
        },
    )

    result = build_unified_edit_signal_result(job)

    assert result.source_counts["keyword_emotion"] == 2
    assert result.type_counts["keyword_hype_segment"] == 1
    assert result.type_counts["keyword_high_value_segment"] == 1


def test_no_automatic_cut_remove_or_highlight_logic_in_2b21_product_files() -> None:
    for relative_path in PRODUCT_FILES:
        source = _read(relative_path)
        for forbidden in FORBIDDEN_PRODUCT_STRINGS:
            assert forbidden not in source, f"{forbidden} found in {relative_path}"


def test_2b21_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in PRODUCT_FILES + TEST_FILES:
        content = _path(relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{relative_path} has UTF-8 BOM"
        assert content.endswith(b"\n"), f"{relative_path} must end with newline"
