from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from types import SimpleNamespace

from core.unified_edit_signal_registry import build_unified_edit_signal_result
from models.job import Job


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_FILES = [
    "models/interaction_classification.py",
    "core/interaction_classifier.py",
    "models/interaction_classification_run.py",
    "core/interaction_classification_runner.py",
    "core/interaction_classification_signal_adapter.py",
    "core/gaming_pipeline.py",
    "core/unified_edit_signal_registry.py",
    "models/job.py",
]
TEST_FILES = [
    "tests/test_interaction_classification_foundation_smoke.py",
    "tests/test_interaction_classification_runner_smoke.py",
    "tests/test_interaction_classification_pipeline_integration_smoke.py",
    "tests/test_interaction_classification_signal_adapter_smoke.py",
    "tests/test_interaction_classification_registry_integration_smoke.py",
    "tests/test_interaction_classification_final_audit_smoke.py",
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
    "timeline_apply_now",
]


def _path(relative_path: str) -> Path:
    return PROJECT_ROOT / relative_path


def _read(relative_path: str) -> str:
    return _path(relative_path).read_text(encoding="utf-8")


def test_all_2b22_product_files_exist() -> None:
    for relative_path in PRODUCT_FILES[:5]:
        assert _path(relative_path).is_file(), f"Missing 2B-22 file: {relative_path}"


def test_all_2b22_tests_exist() -> None:
    for relative_path in TEST_FILES:
        assert _path(relative_path).is_file(), f"Missing 2B-22 test: {relative_path}"


def test_job_has_interaction_classification_fields() -> None:
    field_names = {field.name for field in fields(Job)}
    required_fields = {
        "interaction_classification_report",
        "interaction_classification_status",
        "interaction_classification_points",
        "interaction_classification_segments",
        "interaction_classification_point_count",
        "interaction_classification_segment_count",
        "interaction_classification_monologue_count",
        "interaction_classification_interaction_count",
        "interaction_classification_question_answer_count",
        "interaction_classification_chat_reaction_count",
        "interaction_classification_callout_count",
        "interaction_classification_commentary_count",
        "interaction_classification_private_or_meta_count",
        "interaction_classification_context_needed_count",
        "interaction_classification_recommendation",
    }

    missing = required_fields - field_names
    assert not missing, f"Missing interaction classification Job fields: {sorted(missing)}"


def test_pipeline_contains_interaction_classification_block() -> None:
    source = _read("core/gaming_pipeline.py")

    assert "INTERACTION_CLASSIFICATION_STARTED" in source
    assert "run_interaction_classification_for_job(" in source
    assert "apply_interaction_classification_run_report_to_job(" in source
    assert 'step_name="interaction_classification_done"' in source


def test_pipeline_position_after_keyword_emotion_before_filler_word() -> None:
    source = _read("core/gaming_pipeline.py")

    keyword_index = source.index("KEYWORD_EMOTION_STARTED")
    interaction_index = source.index("INTERACTION_CLASSIFICATION_STARTED")
    filler_index = source.index("FILLER_WORD_DETECTION_STARTED")

    assert keyword_index < interaction_index < filler_index


def test_registry_imports_interaction_adapter() -> None:
    source = _read("core/unified_edit_signal_registry.py")

    assert "from core.interaction_classification_signal_adapter import" in source
    assert "adapt_interaction_classification_report_to_signals" in source


def test_registry_processes_interaction_classification_source() -> None:
    job = SimpleNamespace(
        energy_peak_report={},
        filler_word_report={},
        audio_normalization_report={},
        beat_detection_report={},
        silence_detection_report={},
        silence_classifications=[],
        sentence_boundary_report={},
        keyword_emotion_report={},
        scene_change_report={},
        motion_analysis_report={},
        face_reaction_report={},
        stutter_detection_report={},
        screen_content_report={},
        visual_energy_report={},
        interaction_classification_report={
            "segment_classifications": [
                {
                    "segment_id": "interaction_1",
                    "start_seconds": 1.0,
                    "end_seconds": 2.0,
                    "duration_seconds": 1.0,
                    "text": "Nils komm",
                    "interaction_type": "interaction",
                    "confidence": 0.8,
                    "context_needed": True,
                    "recommendation": "review_interaction_context",
                    "metadata": {},
                    "warnings": [],
                    "errors": [],
                }
            ]
        },
    )

    result = build_unified_edit_signal_result(job)

    assert result.source_counts["interaction_classification"] == 2
    assert result.type_counts["interaction_dialogue_segment"] == 1
    assert result.type_counts["interaction_context_needed_segment"] == 1


def test_no_automatic_cut_remove_highlight_or_mute_logic_in_2b22_product_files() -> None:
    for relative_path in PRODUCT_FILES:
        source = _read(relative_path)
        for forbidden in FORBIDDEN_PRODUCT_STRINGS:
            assert forbidden not in source, f"{forbidden} found in {relative_path}"


def test_2b22_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in PRODUCT_FILES + TEST_FILES:
        content = _path(relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{relative_path} has UTF-8 BOM"
        assert content.endswith(b"\n"), f"{relative_path} must end with newline"
