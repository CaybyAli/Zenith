from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.unified_edit_signal_registry import (
    SOURCE_KEYWORD_EMOTION,
    build_unified_edit_signal_result,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_ACTION_HINTS = {
    "force_cut",
    "auto_remove",
    "hard_remove",
    "remove_now",
    "auto_cut",
    "auto_trim",
    "auto_highlight",
    "highlight_now",
}
EXISTING_SOURCES = {
    "filler_word",
    "sentence_boundary",
    "scene_change",
    "motion_analysis",
    "face_reaction",
    "stutter_detection",
    "screen_content",
    "visual_energy",
}


def _path(relative_path: str) -> Path:
    return PROJECT_ROOT / relative_path


def _keyword_emotion_report() -> dict:
    return {
        "status": "ok",
        "segment_scores": [
            {
                "segment_id": "kw_1",
                "start_seconds": 1.0,
                "end_seconds": 3.0,
                "duration_seconds": 2.0,
                "text": "insane no way haha why annoying",
                "categories": {
                    "hype": 0.82,
                    "shock": 0.88,
                    "laugh": 0.80,
                    "frustration": 0.72,
                    "question": 0.66,
                },
                "dominant_category": "shock",
                "emotion_score": 0.88,
                "hype_score": 0.82,
                "frustration_score": 0.72,
                "shock_score": 0.88,
                "laugh_score": 0.80,
                "question_score": 0.66,
                "overall_keyword_score": 0.76,
                "match_count": 5,
                "recommendation": "review_high_value_keyword_segment",
                "metadata": {},
                "warnings": [],
                "errors": [],
            }
        ],
        "matches": [],
    }


def _sentence_boundary_report() -> dict:
    return {
        "status": "ok",
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
    }


def _job_with_keyword_emotion() -> SimpleNamespace:
    return SimpleNamespace(
        energy_peak_report={},
        filler_word_report={},
        audio_normalization_report={},
        beat_detection_report={},
        silence_detection_report={},
        silence_classifications=[],
        sentence_boundary_report={},
        keyword_emotion_report=_keyword_emotion_report(),
    )


def _job_with_existing_sources() -> SimpleNamespace:
    return SimpleNamespace(
        energy_peak_report={},
        audio_normalization_report={},
        beat_detection_report={},
        silence_detection_report={},
        silence_classifications=[],
        keyword_emotion_report=_keyword_emotion_report(),
        sentence_boundary_report=_sentence_boundary_report(),
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


def test_registry_counts_keyword_emotion_source() -> None:
    result = build_unified_edit_signal_result(_job_with_keyword_emotion())

    assert result.source_counts[SOURCE_KEYWORD_EMOTION] >= 6


def test_registry_counts_keyword_hype_type() -> None:
    result = build_unified_edit_signal_result(_job_with_keyword_emotion())

    assert result.type_counts["keyword_hype_segment"] == 1


def test_registry_counts_keyword_shock_type() -> None:
    result = build_unified_edit_signal_result(_job_with_keyword_emotion())

    assert result.type_counts["keyword_shock_segment"] == 1


def test_registry_counts_keyword_laugh_type() -> None:
    result = build_unified_edit_signal_result(_job_with_keyword_emotion())

    assert result.type_counts["keyword_laugh_segment"] == 1


def test_registry_counts_keyword_frustration_type() -> None:
    result = build_unified_edit_signal_result(_job_with_keyword_emotion())

    assert result.type_counts["keyword_frustration_segment"] == 1


def test_registry_counts_keyword_question_type() -> None:
    result = build_unified_edit_signal_result(_job_with_keyword_emotion())

    assert result.type_counts["keyword_question_segment"] == 1


def test_registry_counts_keyword_high_value_type() -> None:
    result = build_unified_edit_signal_result(_job_with_keyword_emotion())

    assert result.type_counts["keyword_high_value_segment"] == 1


def test_registry_keyword_emotion_has_no_forbidden_action_hints() -> None:
    result = build_unified_edit_signal_result(_job_with_keyword_emotion())

    hints = {
        str(signal.get("action_hint"))
        for signal in result.signals
        if signal.get("source") == SOURCE_KEYWORD_EMOTION
    }
    assert not hints & FORBIDDEN_ACTION_HINTS


def test_empty_keyword_emotion_report_is_safe() -> None:
    result = build_unified_edit_signal_result(
        SimpleNamespace(
            energy_peak_report={},
            filler_word_report={},
            audio_normalization_report={},
            beat_detection_report={},
            silence_detection_report={},
            silence_classifications=[],
            sentence_boundary_report={},
            keyword_emotion_report={},
        )
    )

    assert SOURCE_KEYWORD_EMOTION not in result.source_counts
    assert result.status == "skipped_no_signals"


def test_existing_registry_sources_remain_compatible() -> None:
    result = build_unified_edit_signal_result(_job_with_existing_sources())

    missing = EXISTING_SOURCES - set(result.source_counts)
    assert not missing
    assert SOURCE_KEYWORD_EMOTION in result.source_counts


def test_keyword_emotion_registry_file_hygiene() -> None:
    for relative_path in [
        "core/unified_edit_signal_registry.py",
        "tests/test_keyword_emotion_registry_integration_smoke.py",
    ]:
        content = _path(relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
