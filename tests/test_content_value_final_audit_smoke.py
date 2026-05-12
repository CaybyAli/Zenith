from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from types import SimpleNamespace

from core.unified_edit_signal_registry import build_unified_edit_signal_result
from models.job import Job


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_FILES = [
    "models/content_value.py",
    "core/content_value_calculator.py",
    "models/content_value_run.py",
    "core/content_value_runner.py",
    "core/content_value_signal_adapter.py",
    "core/gaming_pipeline.py",
    "core/unified_edit_signal_registry.py",
    "models/job.py",
]
TEST_FILES = [
    "tests/test_content_value_foundation_smoke.py",
    "tests/test_content_value_runner_smoke.py",
    "tests/test_content_value_pipeline_integration_smoke.py",
    "tests/test_content_value_signal_adapter_smoke.py",
    "tests/test_content_value_registry_integration_smoke.py",
    "tests/test_content_value_final_audit_smoke.py",
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
    "auto_hook",
    "auto_mute",
    "censor_now",
    "delete_segment",
    "drop_segment",
    "timeline_apply_now",
]


def _path(relative_path: str) -> Path:
    return PROJECT_ROOT / relative_path


def _read(relative_path: str) -> str:
    return _path(relative_path).read_text(encoding="utf-8")


def test_all_2b24_product_files_exist() -> None:
    for relative_path in PRODUCT_FILES[:5]:
        assert _path(relative_path).is_file(), f"Missing 2B-24 file: {relative_path}"


def test_all_2b24_tests_exist() -> None:
    for relative_path in TEST_FILES:
        assert _path(relative_path).is_file(), f"Missing 2B-24 test: {relative_path}"


def test_job_has_content_value_fields() -> None:
    field_names = {field.name for field in fields(Job)}
    required = {
        "content_value_report",
        "content_value_status",
        "content_value_segment_scores",
        "content_value_segment_score_count",
        "content_value_high_value_count",
        "content_value_mid_value_count",
        "content_value_low_value_count",
        "content_value_protected_context_count",
        "content_value_hook_candidate_count",
        "content_value_technical_warning_count",
        "content_value_avg_score",
        "content_value_max_score",
        "content_value_min_score",
        "content_value_recommendation",
    }

    assert not (required - field_names)


def test_pipeline_contains_content_value_block() -> None:
    source = _read("core/gaming_pipeline.py")

    assert "CONTENT_VALUE_STARTED" in source
    assert "CONTENT_VALUE_DONE" in source
    assert "CONTENT_VALUE_SKIPPED" in source
    assert "CONTENT_VALUE_FAILED" in source
    assert "run_content_value_for_job(" in source
    assert "apply_content_value_run_report_to_job(" in source
    assert 'step_name="content_value_done"' in source


def test_pipeline_position_after_dead_content_before_registry() -> None:
    source = _read("core/gaming_pipeline.py")

    dead_index = source.index("DEAD_CONTENT_STARTED")
    content_index = source.index("CONTENT_VALUE_STARTED")
    registry_index = source.index("UNIFIED_EDIT_SIGNALS_STARTED")

    assert dead_index < content_index < registry_index


def test_registry_imports_and_processes_content_value() -> None:
    source = _read("core/unified_edit_signal_registry.py")

    assert "from core.content_value_signal_adapter import" in source
    assert "adapt_content_value_report_to_signals" in source
    assert 'SOURCE_CONTENT_VALUE = "content_value"' in source

    job = SimpleNamespace(
        energy_peak_report={},
        filler_word_report={},
        audio_normalization_report={},
        beat_detection_report={},
        silence_detection_report={},
        silence_classifications=[],
        sentence_boundary_report={},
        keyword_emotion_report={},
        interaction_classification_report={},
        scene_change_report={},
        motion_analysis_report={},
        face_reaction_report={},
        stutter_detection_report={},
        screen_content_report={},
        visual_energy_report={},
        dead_content_report={},
        dead_content_candidates=[],
        dead_content_segment_scores=[],
        content_value_report={
            "segment_scores": [
                {
                    "segment_id": "cv1",
                    "start_seconds": 1.0,
                    "end_seconds": 2.0,
                    "value_tier": "high",
                    "final_score": 0.85,
                    "content_value_score": 0.85,
                    "review_label": "review_high_value_segment",
                    "recommendation": "review_high_value_segment",
                    "warnings": [],
                    "errors": [],
                }
            ]
        },
        content_value_segment_scores=[],
    )

    result = build_unified_edit_signal_result(job)

    assert result.source_counts["content_value"] == 1
    assert result.type_counts["content_value_high_segment"] == 1


def test_no_automatic_cut_remove_highlight_hook_mute_or_delete_logic() -> None:
    for relative_path in PRODUCT_FILES:
        source = _read(relative_path)
        for forbidden in FORBIDDEN_PRODUCT_STRINGS:
            assert forbidden not in source, f"{forbidden} found in {relative_path}"


def test_2b24_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in PRODUCT_FILES + TEST_FILES:
        content = _path(relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{relative_path} has BOM"
        assert content.endswith(b"\n"), f"{relative_path} must end with newline"
