from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.profanity_censor_detector import detect_profanity_censor_candidates
from core.unified_edit_signal_registry import build_unified_edit_signal_result


PROJECT_ROOT = Path(__file__).resolve().parents[1]
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
PRODUCT_FILES = [
    "models/profanity_censor.py",
    "core/profanity_censor_detector.py",
    "models/profanity_censor_run.py",
    "core/profanity_censor_runner.py",
    "core/profanity_censor_signal_adapter.py",
    "core/gaming_pipeline.py",
    "core/unified_edit_signal_registry.py",
    "models/job.py",
]


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def _base_job(**overrides) -> SimpleNamespace:
    data = {
        "energy_peak_report": {},
        "filler_word_report": {},
        "audio_normalization_report": {},
        "beat_detection_report": {},
        "silence_detection_report": {},
        "silence_classifications": [],
        "sentence_boundary_report": {},
        "keyword_emotion_report": {},
        "interaction_classification_report": {},
        "scene_change_report": {},
        "motion_analysis_report": {},
        "face_reaction_report": {},
        "stutter_detection_report": {},
        "screen_content_report": {},
        "visual_energy_report": {},
        "dead_content_report": {},
        "dead_content_candidates": [],
        "dead_content_segment_scores": [],
        "content_value_report": {},
        "content_value_segment_scores": [],
        "profanity_censor_report": {},
        "profanity_censor_matches": [],
        "profanity_censor_segment_results": [],
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def test_block4_final_audits_still_exist() -> None:
    required = [
        "tests/test_block4_speech_content_static_audit_smoke.py",
        "tests/test_block4_speech_content_unified_signal_audit_smoke.py",
        "tests/test_block4_speech_content_final_safety_audit_smoke.py",
    ]

    for relative_path in required:
        assert (PROJECT_ROOT / relative_path).is_file()


def test_profanity_censor_is_pipeline_effective() -> None:
    source = _read("core/gaming_pipeline.py")

    assert "PROFANITY_CENSOR_STARTED" in source
    assert "run_profanity_censor_for_job(" in source
    assert "apply_profanity_censor_run_report_to_job(" in source
    assert 'step_name="profanity_censor_done"' in source


def test_profanity_censor_is_registry_effective() -> None:
    source = _read("core/unified_edit_signal_registry.py")

    assert "adapt_profanity_censor_report_to_signals" in source
    assert 'SOURCE_PROFANITY_CENSOR = "profanity_censor"' in source


def test_mild_stays_without_sfx() -> None:
    result = detect_profanity_censor_candidates(
        [{"start_seconds": 1.0, "end_seconds": 2.0, "text": "mildword"}],
        profile={"mild_terms": ["mildword"], "severe_terms": ["severe_token"]},
    )

    assert result.mild_match_count == 1
    assert result.censor_required_count == 0
    assert result.matches[0].replacement_sfx is None


def test_severe_creates_sfx_review_signal() -> None:
    detection = detect_profanity_censor_candidates(
        [{"start_seconds": 1.0, "end_seconds": 2.0, "text": "SEVERE_TOKEN"}],
        profile={"mild_terms": ["mildword"], "severe_terms": ["severe_token"]},
    )
    job = _base_job(profanity_censor_report=detection.to_dict())
    registry = build_unified_edit_signal_result(job)

    assert registry.source_counts["profanity_censor"] >= 1
    assert registry.type_counts["profanity_censor_sfx_required"] == 1
    assert any(
        signal["action_hint"] == "review_censor_sfx_overlay"
        for signal in registry.signals
        if signal.get("source") == "profanity_censor"
    )


def test_no_auto_cut_remove_or_delete_product_logic() -> None:
    for relative_path in PRODUCT_FILES:
        source = _read(relative_path)
        forbidden_found = [
            token for token in FORBIDDEN_PRODUCT_STRINGS if token in source
        ]

        assert not forbidden_found, (
            f"Forbidden automatic action strings in {relative_path}: "
            f"{forbidden_found}"
        )


def test_censor_sfx_manifest_exists() -> None:
    assert (PROJECT_ROOT / "assets/sfx/censor/censor_sfx_manifest.json").is_file()


def test_block5_can_start_after_content_safety_foundation() -> None:
    assert (PROJECT_ROOT / "tests/test_profanity_censor_final_audit_smoke.py").is_file()
    assert (PROJECT_ROOT / "tests/test_block45_content_safety_final_audit_smoke.py").is_file()
