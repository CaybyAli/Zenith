from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.unified_edit_signal_registry import (
    SOURCE_INTERACTION_CLASSIFICATION,
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
    "auto_mute",
    "censor_now",
}
EXISTING_SOURCES = {
    "filler_word",
    "sentence_boundary",
    "keyword_emotion",
    "scene_change",
    "motion_analysis",
    "face_reaction",
    "stutter_detection",
    "screen_content",
    "visual_energy",
}


def _path(relative_path: str) -> Path:
    return PROJECT_ROOT / relative_path


def _interaction_segment(
    segment_id: str,
    interaction_type: str,
    start: float,
    context_needed: bool = False,
) -> dict:
    return {
        "segment_id": segment_id,
        "start_seconds": start,
        "end_seconds": start + 1.0,
        "duration_seconds": 1.0,
        "text": interaction_type,
        "interaction_type": interaction_type,
        "confidence": 0.8,
        "context_needed": context_needed,
        "recommendation": "review",
        "metadata": {},
        "warnings": [],
        "errors": [],
    }


def _interaction_report() -> dict:
    return {
        "status": "ok",
        "segment_classifications": [
            _interaction_segment("mono", "monologue", 1.0),
            _interaction_segment("dialogue", "interaction", 3.0, True),
            _interaction_segment("qa", "question_answer", 5.0),
            _interaction_segment("chat", "chat_reaction", 7.0),
            _interaction_segment("callout", "callout", 9.0),
            _interaction_segment(
                "private",
                "private_or_meta_candidate",
                11.0,
            ),
        ],
    }


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
        "scene_change_report": {},
        "motion_analysis_report": {},
        "face_reaction_report": {},
        "stutter_detection_report": {},
        "screen_content_report": {},
        "visual_energy_report": {},
        "interaction_classification_report": _interaction_report(),
    }
    data.update(overrides)
    return SimpleNamespace(**data)


def _job_with_existing_sources() -> SimpleNamespace:
    return _base_job(
        filler_word_report={
            "status": "ok",
            "occurrence_count": 1,
            "occurrences": [
                {
                    "text": "uh",
                    "normalized_text": "uh",
                    "filler_type": "hesitation",
                    "language": "en",
                    "start_seconds": 20.0,
                    "end_seconds": 20.2,
                    "center_seconds": 20.1,
                    "duration_seconds": 0.2,
                    "confidence": 0.8,
                    "remove_candidate": True,
                    "reason": "hesitation_filler",
                }
            ],
        },
        sentence_boundary_report={
            "boundaries": [
                {
                    "boundary_id": "safe_1",
                    "start_seconds": 22.0,
                    "end_seconds": 23.0,
                    "center_seconds": 22.5,
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
        keyword_emotion_report={
            "segment_scores": [
                {
                    "segment_id": "kw_1",
                    "start_seconds": 24.0,
                    "end_seconds": 25.0,
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
            ],
            "matches": [],
        },
        scene_change_report={
            "scene_changes": [
                {
                    "time_seconds": 26.0,
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
                    "start_seconds": 28.0,
                    "end_seconds": 29.0,
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
                    "start_seconds": 30.0,
                    "end_seconds": 31.0,
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
                    "start_seconds": 32.0,
                    "end_seconds": 33.0,
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
                    "start_seconds": 34.0,
                    "end_seconds": 35.0,
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
                    "start_seconds": 36.0,
                    "end_seconds": 37.0,
                    "classification": "peak_visual_energy",
                    "avg_visual_energy_score": 0.88,
                    "max_visual_energy_score": 0.98,
                    "warnings": [],
                    "errors": [],
                }
            ]
        },
    )


def test_registry_counts_interaction_classification_source() -> None:
    result = build_unified_edit_signal_result(_base_job())

    assert result.source_counts[SOURCE_INTERACTION_CLASSIFICATION] == 7


def test_registry_counts_monologue_type() -> None:
    result = build_unified_edit_signal_result(_base_job())

    assert result.type_counts["interaction_monologue_segment"] == 1


def test_registry_counts_dialogue_type() -> None:
    result = build_unified_edit_signal_result(_base_job())

    assert result.type_counts["interaction_dialogue_segment"] == 1


def test_registry_counts_question_answer_type() -> None:
    result = build_unified_edit_signal_result(_base_job())

    assert result.type_counts["interaction_question_answer_segment"] == 1


def test_registry_counts_chat_reaction_type() -> None:
    result = build_unified_edit_signal_result(_base_job())

    assert result.type_counts["interaction_chat_reaction_segment"] == 1


def test_registry_counts_callout_type() -> None:
    result = build_unified_edit_signal_result(_base_job())

    assert result.type_counts["interaction_callout_segment"] == 1


def test_registry_counts_private_or_meta_type() -> None:
    result = build_unified_edit_signal_result(_base_job())

    assert result.type_counts["interaction_private_or_meta_candidate"] == 1


def test_registry_counts_context_needed_type() -> None:
    result = build_unified_edit_signal_result(_base_job())

    assert result.type_counts["interaction_context_needed_segment"] == 1


def test_registry_interaction_has_no_forbidden_action_hints() -> None:
    result = build_unified_edit_signal_result(_base_job())
    hints = {
        str(signal.get("action_hint"))
        for signal in result.signals
        if signal.get("source") == SOURCE_INTERACTION_CLASSIFICATION
    }

    assert not hints & FORBIDDEN_ACTION_HINTS


def test_empty_interaction_report_safe() -> None:
    result = build_unified_edit_signal_result(
        _base_job(interaction_classification_report={})
    )

    assert SOURCE_INTERACTION_CLASSIFICATION not in result.source_counts
    assert result.status == "skipped_no_signals"


def test_existing_registry_sources_remain_compatible() -> None:
    result = build_unified_edit_signal_result(_job_with_existing_sources())

    missing = EXISTING_SOURCES - set(result.source_counts)
    assert not missing
    assert SOURCE_INTERACTION_CLASSIFICATION in result.source_counts


def test_interaction_registry_file_hygiene() -> None:
    for relative_path in [
        "core/unified_edit_signal_registry.py",
        "tests/test_interaction_classification_registry_integration_smoke.py",
    ]:
        content = _path(relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
