from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.unified_edit_signal_registry import (
    SOURCE_SENTENCE_BOUNDARY,
    build_unified_edit_signal_result,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_ACTION_HINTS = {
    "force_cut",
    "auto_remove",
    "hard_remove",
    "remove_now",
    "cut_sentence_now",
    "auto_cut",
    "auto_trim",
}
EXISTING_SOURCES = {
    "filler_word",
    "scene_change",
    "motion_analysis",
    "face_reaction",
    "stutter_detection",
    "screen_content",
    "visual_energy",
}


def _path(relative_path: str) -> Path:
    return PROJECT_ROOT / relative_path


def _sentence_boundary_report() -> dict:
    return {
        "status": "ok",
        "boundaries": [
            {
                "boundary_id": "safe_1",
                "start_seconds": 1.0,
                "end_seconds": 2.0,
                "center_seconds": 1.5,
                "text": "This is complete.",
                "boundary_type": "safe_sentence_boundary",
                "protection_level": "none",
                "confidence": 0.82,
                "recommendation": "boundary_safe_for_review",
                "warnings": [],
                "errors": [],
            },
            {
                "boundary_id": "open_1",
                "start_seconds": 3.0,
                "end_seconds": 4.0,
                "center_seconds": 3.5,
                "text": "because we",
                "boundary_type": "open_sentence_fragment",
                "protection_level": "hard",
                "confidence": 0.75,
                "recommendation": "protect_open_sentence_fragment",
                "warnings": [],
                "errors": [],
            },
            {
                "boundary_id": "question_1",
                "start_seconds": 5.0,
                "end_seconds": 6.0,
                "center_seconds": 5.5,
                "text": "What happened?",
                "boundary_type": "question_boundary",
                "protection_level": "soft",
                "confidence": 0.85,
                "recommendation": "protect_question_context",
                "warnings": [],
                "errors": [],
            },
        ],
        "protection_zones": [
            {
                "zone_id": "zone_1",
                "start_seconds": 3.0,
                "end_seconds": 4.0,
                "duration_seconds": 1.0,
                "zone_type": "protect_open_fragment",
                "protection_level": "hard",
                "reason": "protect_open_sentence_fragment",
                "confidence": 0.75,
                "source_boundary_ids": ["open_1"],
                "metadata": {"source_boundary_type": "open_sentence_fragment"},
                "warnings": [],
                "errors": [],
            }
        ],
    }


def _job_with_sentence_boundary() -> SimpleNamespace:
    return SimpleNamespace(
        energy_peak_report={},
        audio_normalization_report={},
        beat_detection_report={},
        silence_detection_report={},
        silence_classifications=[],
        filler_word_report={},
        sentence_boundary_report=_sentence_boundary_report(),
    )


def _job_with_existing_sources() -> SimpleNamespace:
    return SimpleNamespace(
        energy_peak_report={},
        audio_normalization_report={},
        beat_detection_report={},
        silence_detection_report={},
        silence_classifications=[],
        filler_word_report={
            "status": "ok",
            "occurrence_count": 1,
            "occurrences": [
                {
                    "text": "uh",
                    "normalized_text": "uh",
                    "filler_type": "hesitation",
                    "language": "en",
                    "start_seconds": 0.0,
                    "end_seconds": 0.2,
                    "center_seconds": 0.1,
                    "duration_seconds": 0.2,
                    "confidence": 0.8,
                    "remove_candidate": True,
                    "reason": "hesitation_filler",
                }
            ],
        },
        sentence_boundary_report=_sentence_boundary_report(),
        scene_change_report={
            "scene_changes": [
                {
                    "time_seconds": 10.0,
                    "frame_index": 300,
                    "change_type": "hard_scene_change",
                    "scene_score": 0.91,
                    "confidence": 0.93,
                    "warnings": [],
                    "errors": [],
                }
            ]
        },
        motion_analysis_report={
            "motion_segments": [
                {
                    "start_seconds": 20.0,
                    "end_seconds": 24.0,
                    "duration_seconds": 4.0,
                    "classification": "high_motion",
                    "avg_motion_score": 0.72,
                    "max_motion_score": 0.94,
                    "confidence": 0.91,
                    "warnings": [],
                    "errors": [],
                }
            ]
        },
        face_reaction_report={
            "face_reaction_segments": [
                {
                    "start_seconds": 40.0,
                    "end_seconds": 43.0,
                    "duration_seconds": 3.0,
                    "reaction_type": "hype_candidate",
                    "avg_reaction_score": 0.78,
                    "max_reaction_score": 0.95,
                    "confidence": 0.92,
                    "warnings": [],
                    "errors": [],
                }
            ]
        },
        stutter_detection_report={
            "stutter_detection_segments": [
                {
                    "start_seconds": 60.0,
                    "end_seconds": 62.0,
                    "duration_seconds": 2.0,
                    "classification": "stutter_segment",
                    "avg_duplicate_score": 0.74,
                    "max_duplicate_score": 0.91,
                    "confidence": 0.89,
                    "warnings": [],
                    "errors": [],
                }
            ]
        },
        screen_content_report={
            "screen_content_segments": [
                {
                    "start_seconds": 80.0,
                    "end_seconds": 90.0,
                    "duration_seconds": 10.0,
                    "screen_type": "gameplay",
                    "avg_confidence": 0.88,
                    "max_confidence": 0.96,
                    "confidence": 0.94,
                    "warnings": [],
                    "errors": [],
                }
            ]
        },
        visual_energy_report={
            "visual_energy_segments": [
                {
                    "start_seconds": 110.0,
                    "end_seconds": 113.0,
                    "duration_seconds": 3.0,
                    "classification": "peak_visual_energy",
                    "avg_visual_energy_score": 0.88,
                    "max_visual_energy_score": 0.98,
                    "warnings": [],
                    "errors": [],
                }
            ]
        },
    )


def test_registry_counts_sentence_boundary_source() -> None:
    result = build_unified_edit_signal_result(_job_with_sentence_boundary())

    assert result.source_counts[SOURCE_SENTENCE_BOUNDARY] >= 4


def test_registry_counts_sentence_safe_boundary_type() -> None:
    result = build_unified_edit_signal_result(_job_with_sentence_boundary())

    assert result.type_counts["sentence_safe_boundary"] == 1


def test_registry_counts_sentence_boundary_protection_type() -> None:
    result = build_unified_edit_signal_result(_job_with_sentence_boundary())

    assert result.type_counts["sentence_boundary_protection"] == 1


def test_registry_counts_question_context_type() -> None:
    result = build_unified_edit_signal_result(_job_with_sentence_boundary())

    assert result.type_counts["sentence_question_context_protection"] == 1


def test_registry_counts_sentence_protection_zone_type() -> None:
    result = build_unified_edit_signal_result(_job_with_sentence_boundary())

    assert result.type_counts["sentence_protection_zone"] == 1


def test_registry_sentence_boundary_has_no_forbidden_action_hints() -> None:
    result = build_unified_edit_signal_result(_job_with_sentence_boundary())

    hints = {
        str(signal.get("action_hint"))
        for signal in result.signals
        if signal.get("source") == SOURCE_SENTENCE_BOUNDARY
    }
    assert not hints & FORBIDDEN_ACTION_HINTS


def test_empty_sentence_boundary_report_is_safe() -> None:
    result = build_unified_edit_signal_result(
        SimpleNamespace(
            energy_peak_report={},
            filler_word_report={},
            audio_normalization_report={},
            beat_detection_report={},
            silence_detection_report={},
            silence_classifications=[],
            sentence_boundary_report={},
        )
    )

    assert SOURCE_SENTENCE_BOUNDARY not in result.source_counts
    assert result.status == "skipped_no_signals"


def test_existing_registry_sources_remain_compatible() -> None:
    result = build_unified_edit_signal_result(_job_with_existing_sources())

    missing = EXISTING_SOURCES - set(result.source_counts)
    assert not missing
    assert SOURCE_SENTENCE_BOUNDARY in result.source_counts


def test_sentence_boundary_registry_file_hygiene() -> None:
    for relative_path in [
        "core/unified_edit_signal_registry.py",
        "tests/test_sentence_boundary_registry_integration_smoke.py",
    ]:
        content = _path(relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
