from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from types import SimpleNamespace

from core.unified_edit_signal_registry import build_unified_edit_signal_result
from models.job import Job


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_FILES = [
    "models/dead_content.py",
    "core/dead_content_detector.py",
    "models/dead_content_run.py",
    "core/dead_content_runner.py",
    "core/dead_content_signal_adapter.py",
    "core/gaming_pipeline.py",
    "core/unified_edit_signal_registry.py",
    "models/job.py",
]
TEST_FILES = [
    "tests/test_dead_content_detection_foundation_smoke.py",
    "tests/test_dead_content_runner_smoke.py",
    "tests/test_dead_content_pipeline_integration_smoke.py",
    "tests/test_dead_content_signal_adapter_smoke.py",
    "tests/test_dead_content_registry_integration_smoke.py",
    "tests/test_dead_content_final_audit_smoke.py",
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


def test_all_2b23_product_files_exist() -> None:
    for relative_path in PRODUCT_FILES[:5]:
        assert _path(relative_path).is_file(), f"Missing 2B-23 file: {relative_path}"


def test_all_2b23_tests_exist() -> None:
    for relative_path in TEST_FILES:
        assert _path(relative_path).is_file(), f"Missing 2B-23 test: {relative_path}"


def test_job_has_dead_content_fields() -> None:
    field_names = {field.name for field in fields(Job)}
    required = {
        "dead_content_report",
        "dead_content_status",
        "dead_content_candidates",
        "dead_content_segment_scores",
        "dead_content_candidate_count",
        "dead_content_segment_score_count",
        "dead_content_dead_air_candidate_count",
        "dead_content_low_value_candidate_count",
        "dead_content_filler_pause_candidate_count",
        "dead_content_loading_or_menu_candidate_count",
        "dead_content_private_or_meta_candidate_count",
        "dead_content_protected_candidate_count",
        "dead_content_high_confidence_candidate_count",
        "dead_content_recommendation",
    }

    assert not (required - field_names)


def test_pipeline_contains_dead_content_block() -> None:
    source = _read("core/gaming_pipeline.py")

    assert "DEAD_CONTENT_STARTED" in source
    assert "DEAD_CONTENT_DONE" in source
    assert "DEAD_CONTENT_SKIPPED" in source
    assert "DEAD_CONTENT_FAILED" in source
    assert "run_dead_content_detection_for_job(" in source
    assert "apply_dead_content_run_report_to_job(" in source
    assert 'step_name="dead_content_done"' in source


def test_pipeline_position_is_after_filler_or_interaction_and_before_registry() -> None:
    source = _read("core/gaming_pipeline.py")

    interaction_index = source.index("INTERACTION_CLASSIFICATION_STARTED")
    filler_index = source.index("FILLER_WORD_DETECTION_STARTED")
    dead_index = source.index("DEAD_CONTENT_STARTED")
    registry_index = source.index("UNIFIED_EDIT_SIGNALS_STARTED")

    assert interaction_index < dead_index
    assert filler_index < dead_index
    assert dead_index < registry_index


def test_registry_imports_and_processes_dead_content() -> None:
    source = _read("core/unified_edit_signal_registry.py")

    assert "from core.dead_content_signal_adapter import" in source
    assert "adapt_dead_content_report_to_signals" in source
    assert 'SOURCE_DEAD_CONTENT = "dead_content"' in source

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
        dead_content_report={
            "candidates": [
                {
                    "candidate_id": "dead_1",
                    "candidate_type": "dead_air_candidate",
                    "start_seconds": 1.0,
                    "end_seconds": 2.0,
                    "dead_content_score": 0.9,
                    "confidence": 0.9,
                    "metadata": {},
                    "evidence": {},
                }
            ]
        },
    )

    result = build_unified_edit_signal_result(job)

    assert result.source_counts["dead_content"] >= 1
    assert result.type_counts["dead_content_dead_air_candidate"] == 1


def test_no_automatic_cut_remove_highlight_mute_or_delete_logic() -> None:
    for relative_path in PRODUCT_FILES:
        source = _read(relative_path)
        for forbidden in FORBIDDEN_PRODUCT_STRINGS:
            assert forbidden not in source, f"{forbidden} found in {relative_path}"


def test_2b23_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in PRODUCT_FILES + TEST_FILES:
        content = _path(relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{relative_path} has BOM"
        assert content.endswith(b"\n"), f"{relative_path} must end with newline"
