from __future__ import annotations

from types import SimpleNamespace

from core.unified_edit_signal_registry import build_unified_edit_signal_result


REQUIRED_SOURCES = {
    "sentence_boundary",
    "keyword_emotion",
    "interaction_classification",
    "dead_content",
    "content_value",
}


REQUIRED_TYPES = {
    "sentence_boundary_protection",
    "sentence_question_context_protection",
    "sentence_protection_zone",
    "keyword_hype_segment",
    "keyword_shock_segment",
    "keyword_high_value_segment",
    "interaction_dialogue_segment",
    "interaction_question_answer_segment",
    "interaction_context_needed_segment",
    "interaction_private_or_meta_candidate",
    "dead_content_low_value_candidate",
    "dead_content_protected_context_candidate",
    "dead_content_high_score_candidate",
    "content_value_high_segment",
    "content_value_low_segment",
    "content_value_protected_context",
    "content_value_hook_candidate",
    "content_value_technical_warning",
}


REQUIRED_SIGNAL_FIELDS = {
    "signal_id",
    "signal_type",
    "source",
    "start_seconds",
    "end_seconds",
    "center_seconds",
    "signal_score",
    "priority",
    "action_hint",
    "reason",
    "confidence",
    "metadata",
}


FORBIDDEN_ACTION_HINTS = {
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
}


def _synthetic_job() -> SimpleNamespace:
    return SimpleNamespace(
        sentence_boundary_report={
            "boundaries": [
                {
                    "boundary_id": "sb_open_fragment_1",
                    "boundary_type": "open_sentence_fragment",
                    "start_seconds": 1.0,
                    "end_seconds": 2.0,
                    "confidence": 0.91,
                    "text": "Wait this is not finished",
                    "protection_level": "high",
                },
                {
                    "boundary_id": "sb_question_1",
                    "boundary_type": "question_boundary",
                    "start_seconds": 3.0,
                    "end_seconds": 4.0,
                    "confidence": 0.88,
                    "text": "Where is the enemy?",
                    "protection_level": "high",
                },
            ],
            "protection_zones": [
                {
                    "zone_id": "zone_question_context_1",
                    "start_seconds": 3.0,
                    "end_seconds": 5.5,
                    "duration_seconds": 2.5,
                    "confidence": 0.86,
                    "protection_level": "high",
                    "reason": "question needs answer context",
                    "source_boundary_ids": ["sb_question_1"],
                    "metadata": {
                        "source_boundary_type": "question_boundary",
                    },
                }
            ],
        },
        keyword_emotion_report={
            "segment_scores": [
                {
                    "segment_id": "keyword_hype_1",
                    "start_seconds": 6.0,
                    "end_seconds": 8.0,
                    "duration_seconds": 2.0,
                    "text": "let's go that was insane",
                    "categories": {
                        "hype": 0.95,
                        "shock": 0.88,
                    },
                    "dominant_category": "hype",
                    "overall_keyword_score": 0.93,
                    "match_count": 2,
                    "recommendation": "review_keyword_moment",
                }
            ],
            "matches": [],
        },
        interaction_classification_report={
            "segment_classifications": [
                {
                    "segment_id": "interaction_dialogue_1",
                    "interaction_type": "interaction",
                    "start_seconds": 9.0,
                    "end_seconds": 11.0,
                    "duration_seconds": 2.0,
                    "text": "come here come here",
                    "confidence": 0.86,
                    "context_needed": False,
                    "recommendation": "review_interaction_context",
                },
                {
                    "segment_id": "interaction_question_answer_1",
                    "interaction_type": "question_answer",
                    "start_seconds": 12.0,
                    "end_seconds": 15.0,
                    "duration_seconds": 3.0,
                    "text": "where is he? there on the left",
                    "confidence": 0.89,
                    "context_needed": True,
                    "recommendation": "protect_question_answer_context",
                },
                {
                    "segment_id": "interaction_private_meta_1",
                    "interaction_type": "private_or_meta_candidate",
                    "start_seconds": 16.0,
                    "end_seconds": 18.0,
                    "duration_seconds": 2.0,
                    "text": "private setup talk",
                    "confidence": 0.84,
                    "context_needed": False,
                    "recommendation": "review_private_or_meta_candidate",
                },
            ],
        },
        dead_content_report={
            "candidates": [
                {
                    "candidate_id": "dead_low_value_1",
                    "candidate_type": "low_value_content_candidate",
                    "start_seconds": 19.0,
                    "end_seconds": 23.0,
                    "center_seconds": 21.0,
                    "duration_seconds": 4.0,
                    "dead_content_score": 0.74,
                    "confidence": 0.78,
                    "protected_by_context": False,
                    "recommendation": "review_low_value_content_candidate",
                    "metadata": {
                        "content_value_score": 0.18,
                    },
                },
                {
                    "candidate_id": "dead_protected_1",
                    "candidate_type": "protected_context_candidate",
                    "start_seconds": 24.0,
                    "end_seconds": 26.0,
                    "center_seconds": 25.0,
                    "duration_seconds": 2.0,
                    "dead_content_score": 0.45,
                    "confidence": 0.8,
                    "protected_by_context": True,
                    "protection_reasons": ["question_answer_context"],
                    "recommendation": "protect_context_from_dead_content_cut",
                    "metadata": {
                        "content_value_score": 0.72,
                    },
                },
                {
                    "candidate_id": "dead_high_score_1",
                    "candidate_type": "dead_air_candidate",
                    "start_seconds": 27.0,
                    "end_seconds": 30.0,
                    "center_seconds": 28.5,
                    "duration_seconds": 3.0,
                    "dead_content_score": 0.91,
                    "confidence": 0.9,
                    "protected_by_context": False,
                    "recommendation": "review_dead_content_candidate",
                    "metadata": {
                        "content_value_score": 0.05,
                    },
                },
            ],
        },
        content_value_report={
            "segment_scores": [
                {
                    "segment_id": "content_high_hook_1",
                    "value_tier": "high",
                    "start_seconds": 31.0,
                    "end_seconds": 34.0,
                    "center_seconds": 32.5,
                    "duration_seconds": 3.0,
                    "content_value_score": 0.94,
                    "final_score": 0.94,
                    "protection_score": 0.2,
                    "is_hook_candidate": True,
                    "is_protected_context": False,
                    "review_label": "high_value",
                    "recommendation": "review_high_value_segment",
                },
                {
                    "segment_id": "content_low_1",
                    "value_tier": "low",
                    "start_seconds": 35.0,
                    "end_seconds": 38.0,
                    "center_seconds": 36.5,
                    "duration_seconds": 3.0,
                    "content_value_score": 0.16,
                    "final_score": 0.16,
                    "protection_score": 0.0,
                    "is_hook_candidate": False,
                    "is_protected_context": False,
                    "review_label": "low_value",
                    "recommendation": "review_low_value_segment",
                },
                {
                    "segment_id": "content_protected_1",
                    "value_tier": "protected",
                    "start_seconds": 39.0,
                    "end_seconds": 42.0,
                    "center_seconds": 40.5,
                    "duration_seconds": 3.0,
                    "content_value_score": 0.7,
                    "final_score": 0.76,
                    "protection_score": 0.95,
                    "is_hook_candidate": False,
                    "is_protected_context": True,
                    "review_label": "protected_context",
                    "recommendation": "protect_context_from_blind_cut",
                },
                {
                    "segment_id": "content_technical_warning_1",
                    "value_tier": "technical_warning",
                    "start_seconds": 43.0,
                    "end_seconds": 45.0,
                    "center_seconds": 44.0,
                    "duration_seconds": 2.0,
                    "content_value_score": 0.2,
                    "final_score": 0.22,
                    "technical_penalty_score": 0.8,
                    "is_hook_candidate": False,
                    "is_protected_context": False,
                    "review_label": "technical_warning",
                    "recommendation": "review_technical_warning",
                },
            ],
        },
    )


def test_block4_synthetic_job_collects_all_speech_content_sources() -> None:
    result = build_unified_edit_signal_result(_synthetic_job())

    assert result.signal_count >= 15
    assert REQUIRED_SOURCES.issubset(set(result.source_counts))


def test_block4_synthetic_job_contains_required_signal_types() -> None:
    result = build_unified_edit_signal_result(_synthetic_job())

    missing = REQUIRED_TYPES - set(result.type_counts)

    assert not missing, f"Missing Block-4 signal types: {sorted(missing)}"


def test_block4_all_unified_signals_have_required_contract_fields() -> None:
    result = build_unified_edit_signal_result(_synthetic_job())

    assert result.signals

    for signal in result.signals:
        missing = REQUIRED_SIGNAL_FIELDS - set(signal)
        assert not missing, f"Signal missing fields {sorted(missing)}: {signal}"

        assert isinstance(signal["metadata"], dict)
        assert signal["start_seconds"] is not None
        assert signal["end_seconds"] is not None
        assert signal["center_seconds"] is not None


def test_block4_unified_signals_do_not_use_forbidden_action_hints() -> None:
    result = build_unified_edit_signal_result(_synthetic_job())

    action_hints = {
        str(signal.get("action_hint") or "")
        for signal in result.signals
    }

    forbidden_found = FORBIDDEN_ACTION_HINTS & action_hints

    assert not forbidden_found, f"Forbidden action hints found: {sorted(forbidden_found)}"
    assert "review_hook_candidate" in action_hints
    assert "auto_hook" not in action_hints
    assert "highlight_now" not in action_hints
