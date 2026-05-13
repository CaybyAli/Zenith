from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


BLOCK4_PRODUCT_FILES = [
    "core/transcript_source_selector.py",
    "core/transcript_processor.py",
    "core/transcript_runner.py",
    "core/transcript_segment_normalizer.py",
    "models/transcript_result.py",
    "models/transcript_run.py",
    "models/sentence_boundary.py",
    "core/sentence_boundary_protector.py",
    "models/sentence_boundary_run.py",
    "core/sentence_boundary_runner.py",
    "core/sentence_boundary_signal_adapter.py",
    "models/keyword_emotion.py",
    "core/keyword_emotion_scorer.py",
    "models/keyword_emotion_run.py",
    "core/keyword_emotion_runner.py",
    "core/keyword_emotion_signal_adapter.py",
    "models/interaction_classification.py",
    "core/interaction_classifier.py",
    "models/interaction_classification_run.py",
    "core/interaction_classification_runner.py",
    "core/interaction_classification_signal_adapter.py",
    "models/dead_content.py",
    "core/dead_content_detector.py",
    "models/dead_content_run.py",
    "core/dead_content_runner.py",
    "core/dead_content_signal_adapter.py",
    "models/content_value.py",
    "core/content_value_calculator.py",
    "models/content_value_run.py",
    "core/content_value_runner.py",
    "core/content_value_signal_adapter.py",
    "core/gaming_pipeline.py",
    "core/unified_edit_signal_registry.py",
    "models/job.py",
]


BLOCK4_TEST_FILES = [
    "tests/test_speech_to_text_final_audit_smoke.py",
    "tests/test_transcript_real_word_level_probe_smoke.py",
    "tests/test_speech_to_text_lifeline_audit_smoke.py",
    "tests/test_transcript_segment_normalizer_smoke.py",
    "tests/test_transcript_runner_normalizer_integration_smoke.py",
    "tests/test_transcript_word_count_cache_safety_smoke.py",
    "tests/test_sentence_boundary_foundation_smoke.py",
    "tests/test_sentence_boundary_runner_smoke.py",
    "tests/test_sentence_boundary_pipeline_integration_smoke.py",
    "tests/test_sentence_boundary_signal_adapter_smoke.py",
    "tests/test_sentence_boundary_registry_integration_smoke.py",
    "tests/test_sentence_boundary_final_audit_smoke.py",
    "tests/test_keyword_emotion_foundation_smoke.py",
    "tests/test_keyword_emotion_runner_smoke.py",
    "tests/test_keyword_emotion_pipeline_integration_smoke.py",
    "tests/test_keyword_emotion_signal_adapter_smoke.py",
    "tests/test_keyword_emotion_registry_integration_smoke.py",
    "tests/test_keyword_emotion_final_audit_smoke.py",
    "tests/test_interaction_classification_foundation_smoke.py",
    "tests/test_interaction_classification_runner_smoke.py",
    "tests/test_interaction_classification_pipeline_integration_smoke.py",
    "tests/test_interaction_classification_signal_adapter_smoke.py",
    "tests/test_interaction_classification_registry_integration_smoke.py",
    "tests/test_interaction_classification_final_audit_smoke.py",
    "tests/test_dead_content_detection_foundation_smoke.py",
    "tests/test_dead_content_runner_smoke.py",
    "tests/test_dead_content_pipeline_integration_smoke.py",
    "tests/test_dead_content_signal_adapter_smoke.py",
    "tests/test_dead_content_registry_integration_smoke.py",
    "tests/test_dead_content_final_audit_smoke.py",
    "tests/test_content_value_foundation_smoke.py",
    "tests/test_content_value_runner_smoke.py",
    "tests/test_content_value_pipeline_integration_smoke.py",
    "tests/test_content_value_signal_adapter_smoke.py",
    "tests/test_content_value_registry_integration_smoke.py",
    "tests/test_content_value_final_audit_smoke.py",
    "tests/test_block3_video_intelligence_static_audit_smoke.py",
    "tests/test_block3_video_intelligence_unified_signal_audit_smoke.py",
    "tests/test_block3_video_intelligence_final_safety_audit_smoke.py",
    "tests/test_phase3c_unified_edit_signal_registry_smoke.py",
]


PIPELINE_TOKENS = [
    "TRANSCRIPT_STARTED",
    "TRANSCRIPT_DONE",
    "TRANSCRIPT_SKIPPED",
    "TRANSCRIPT_BLOCKED",
    "TRANSCRIPT_FAILED",
    "transcript_done",
    "SENTENCE_BOUNDARY_STARTED",
    "SENTENCE_BOUNDARY_DONE",
    "SENTENCE_BOUNDARY_SKIPPED",
    "SENTENCE_BOUNDARY_FAILED",
    "sentence_boundary_done",
    "KEYWORD_EMOTION_STARTED",
    "KEYWORD_EMOTION_DONE",
    "KEYWORD_EMOTION_SKIPPED",
    "KEYWORD_EMOTION_FAILED",
    "keyword_emotion_done",
    "INTERACTION_CLASSIFICATION_STARTED",
    "INTERACTION_CLASSIFICATION_DONE",
    "INTERACTION_CLASSIFICATION_SKIPPED",
    "INTERACTION_CLASSIFICATION_FAILED",
    "interaction_classification_done",
    "DEAD_CONTENT_STARTED",
    "DEAD_CONTENT_DONE",
    "DEAD_CONTENT_SKIPPED",
    "DEAD_CONTENT_FAILED",
    "dead_content_done",
    "CONTENT_VALUE_STARTED",
    "CONTENT_VALUE_DONE",
    "CONTENT_VALUE_SKIPPED",
    "CONTENT_VALUE_FAILED",
    "content_value_done",
]


REGISTRY_SOURCES = [
    "sentence_boundary",
    "keyword_emotion",
    "interaction_classification",
    "dead_content",
    "content_value",
]


JOB_FIELDS = [
    "transcript_report",
    "transcript_status",
    "transcript_segments",
    "transcript_text",
    "transcript_word_count",
    "transcript_has_word_level_timestamps",
    "sentence_boundary_report",
    "sentence_boundary_status",
    "sentence_boundary_boundaries",
    "sentence_boundary_protection_zones",
    "keyword_emotion_report",
    "keyword_emotion_status",
    "keyword_emotion_matches",
    "keyword_emotion_segment_scores",
    "interaction_classification_report",
    "interaction_classification_status",
    "interaction_classification_segments",
    "interaction_classification_private_or_meta_count",
    "dead_content_report",
    "dead_content_status",
    "dead_content_candidates",
    "dead_content_segment_scores",
    "content_value_report",
    "content_value_status",
    "content_value_segment_scores",
    "content_value_hook_candidate_count",
    "unified_edit_signal_report",
    "unified_edit_signals",
    "unified_edit_signal_count",
]


def _path(relative_path: str) -> Path:
    return ROOT / relative_path


def _read_text(relative_path: str) -> str:
    return _path(relative_path).read_text(encoding="utf-8")


def _assert_exists(relative_path: str) -> None:
    assert _path(relative_path).exists(), f"Missing file: {relative_path}"


def _assert_no_bom_and_final_newline(relative_path: str) -> None:
    data = _path(relative_path).read_bytes()
    assert not data.startswith(b"\xef\xbb\xbf"), f"File has UTF-8 BOM: {relative_path}"
    assert data.endswith(b"\n"), f"File does not end with newline: {relative_path}"


def test_block4_product_files_exist_and_are_clean() -> None:
    for relative_path in BLOCK4_PRODUCT_FILES:
        _assert_exists(relative_path)
        _assert_no_bom_and_final_newline(relative_path)


def test_block4_expected_test_files_exist_and_are_clean() -> None:
    for relative_path in BLOCK4_TEST_FILES:
        _assert_exists(relative_path)
        _assert_no_bom_and_final_newline(relative_path)


def test_gaming_pipeline_contains_all_block4_events_and_checkpoints() -> None:
    text = _read_text("core/gaming_pipeline.py")

    missing = [token for token in PIPELINE_TOKENS if token not in text]

    assert not missing, f"Missing Block-4 pipeline tokens: {missing}"


def test_unified_registry_contains_all_block4_sources() -> None:
    text = _read_text("core/unified_edit_signal_registry.py")

    missing = [source for source in REGISTRY_SOURCES if source not in text]

    assert not missing, f"Missing Block-4 registry sources: {missing}"


def test_job_model_contains_all_block4_state_fields() -> None:
    text = _read_text("models/job.py")

    missing = [field_name for field_name in JOB_FIELDS if field_name not in text]

    assert not missing, f"Missing Block-4 job fields: {missing}"