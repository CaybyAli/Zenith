from pathlib import Path

from core.unified_edit_signal_registry import run_unified_edit_signal_registry_for_job
from models.job import Job


ROOT = Path(__file__).resolve().parents[1]

BLOCK5_SOURCES = [
    "segment_classifier",
    "murch_scoring",
    "cut_list_generator",
    "clip_duration_optimizer",
    "transition_decision",
    "continuity_check",
    "cut_list_finalizer",
]

REQUIRED_SIGNAL_TYPES = {
    "segment_classifier": [
        "segment_highlight_candidate",
        "segment_protected_context",
        "segment_dead_candidate",
        "segment_censor_required",
    ],
    "murch_scoring": [
        "murch_high_score_segment",
        "murch_low_score_segment",
        "murch_protected_context",
        "murch_censor_required_context",
    ],
    "cut_list_generator": [
        "cut_list_keep_candidate",
        "cut_list_review_trim",
        "cut_list_review_remove",
        "cut_list_protect_segment",
        "cut_list_censor_keep",
    ],
    "clip_duration_optimizer": [
        "clip_duration_ok",
        "clip_duration_too_long_review",
        "clip_duration_protected",
        "clip_duration_censor_keep",
        "clip_duration_invalid_timing",
    ],
    "transition_decision": [
        "transition_hard_cut_review",
        "transition_no_cut_protect",
        "transition_censor_safe_keep",
        "transition_technical_review",
    ],
    "continuity_check": [
        "continuity_sentence_break_risk",
        "continuity_context_jump_risk",
        "continuity_censor_context_risk",
        "continuity_transition_conflict",
        "continuity_technical_risk",
    ],
    "cut_list_finalizer": [
        "final_cut_list_keep_review",
        "final_cut_list_keep_high_value",
        "final_cut_list_trim_review",
        "final_cut_list_remove_review",
        "final_cut_list_protect",
        "final_cut_list_censor_keep",
        "final_cut_list_technical_review",
        "final_cut_list_blocked_by_continuity",
    ],
}

DANGEROUS_ACTION_WORDS = [
    "auto_remove",
    "hard_remove",
    "remove_now",
    "auto_cut",
    "auto_trim",
    "auto_transition",
    "auto_fade",
    "auto_highlight",
    "censor_now",
    "delete_segment",
    "drop_segment",
    "timeline_apply_now",
    "apply_cut",
    "render_now",
    "execute_cut",
    "apply_final_cutlist",
    "execute_final_cutlist",
]


def _minimal_job_data() -> dict:
    return {
        "job_id": "job_block5_unified_signal_audit",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "short",
        "target_platforms": ["youtube"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
    }


def _segment(segment_type: str, index: int) -> dict:
    start = float(index * 10)
    end = start + 4.0

    return {
        "segment_id": f"segment_{index}_{segment_type}",
        "start_seconds": start,
        "end_seconds": end,
        "center_seconds": (start + end) / 2.0,
        "duration_seconds": end - start,
        "segment_type": segment_type,
        "confidence": 0.9,
        "segment_score": 0.85,
        "content_value_score": 0.8 if segment_type == "highlight" else 0.0,
        "dead_content_score": 0.8 if segment_type == "dead_candidate" else 0.0,
        "protection_score": 0.9 if segment_type == "protected_context" else 0.0,
        "technical_risk_score": 0.0,
        "hook_candidate_score": 0.0,
        "censor_required": segment_type == "censor_required_segment",
        "is_highlight_candidate": segment_type == "highlight",
        "is_hook_candidate": False,
        "is_protected_context": segment_type == "protected_context",
        "is_dead_candidate": segment_type == "dead_candidate",
        "is_transition_candidate": False,
        "is_technical_warning": False,
        "recommendation": f"review_{segment_type}",
        "evidence": {"audit": True},
        "source_signal_ids": [f"segment_source_{index}"],
        "warnings": [],
        "errors": [],
        "metadata": {"audit": True},
    }


def _murch_score(tier: str, index: int, censor_required: bool = False) -> dict:
    start = 100.0 + (index * 10.0)
    end = start + 4.0

    return {
        "segment_id": f"murch_segment_{index}_{tier}",
        "start_seconds": start,
        "end_seconds": end,
        "center_seconds": (start + end) / 2.0,
        "duration_seconds": end - start,
        "segment_type": "normal_content",
        "murch_score": 0.9 if tier == "high" else 0.2 if tier == "low" else 0.7,
        "murch_tier": tier,
        "emotion_score": 0.8 if tier == "high" else 0.4,
        "story_score": 0.4,
        "rhythm_score": 0.5,
        "eye_trace_score": 0.5,
        "screen_direction_score": 0.5,
        "spatial_continuity_score": 0.5,
        "protection_score": 0.9 if tier == "protected" else 0.0,
        "risk_score": 0.0,
        "dead_content_risk_score": 0.0,
        "technical_risk_score": 0.0,
        "censor_required": censor_required,
        "is_censor_required": censor_required,
        "is_protected_context": tier == "protected",
        "recommendation": f"review_{tier}",
        "evidence": {"audit": True},
        "source_signal_ids": [f"murch_source_{index}"],
        "warnings": [],
        "errors": [],
        "metadata": {"audit": True},
    }


def _cut_list_item(action: str, index: int) -> dict:
    start = 200.0 + (index * 10.0)
    return {
        "item_id": f"cut_item_{index}",
        "segment_id": f"cut_segment_{index}",
        "start_seconds": start,
        "end_seconds": start + 5.0,
        "center_seconds": start + 2.5,
        "duration_seconds": 5.0,
        "proposed_action": action,
        "action_confidence": 0.82,
        "priority": "high" if action in {"PROTECT", "CENSOR_KEEP"} else "medium",
        "segment_type": "audit",
        "murch_score": 0.7,
        "content_value_score": 0.6,
        "risk_score": 0.1,
        "protection_score": 0.9 if action == "PROTECT" else 0.0,
        "censor_required": action == "CENSOR_KEEP",
        "is_protected": action == "PROTECT",
        "is_review_required": action != "KEEP",
        "reason": f"review_{action.lower()}",
        "decision_basis": {"review_only": True},
        "source_signal_ids": [],
        "warnings": [],
        "errors": [],
        "metadata": {"audit": True},
    }


def _clip_duration_recommendation(status: str, index: int) -> dict:
    start = 300.0 + (index * 10.0)
    return {
        "recommendation_id": f"clip_duration_{index}",
        "source_item_id": f"cut_item_{index}",
        "segment_id": f"duration_segment_{index}",
        "start_seconds": start,
        "end_seconds": start + 8.0,
        "center_seconds": start + 4.0,
        "duration_seconds": 8.0,
        "proposed_action": "KEEP",
        "duration_status": status,
        "recommended_min_duration_seconds": 4.0,
        "recommended_max_duration_seconds": 90.0,
        "recommended_target_duration_seconds": 18.0,
        "suggested_start_seconds": None,
        "suggested_end_seconds": None,
        "suggested_duration_seconds": None,
        "adjustment_seconds": 0.0,
        "confidence": 0.84,
        "priority": "medium",
        "is_too_short": False,
        "is_too_long": status == "too_long_review",
        "is_duration_ok": status == "duration_ok",
        "is_protected": status == "protect_duration",
        "is_censor_keep": status == "censor_keep_duration",
        "is_review_required": status != "duration_ok",
        "is_invalid_timing": status == "invalid_timing_review",
        "reason": f"{status}_reason",
        "decision_basis": {"review_only": True},
        "source_signal_ids": [],
        "warnings": [],
        "errors": [],
        "metadata": {"audit": True},
    }


def _transition_decision(transition_type: str, index: int) -> dict:
    start = 400.0 + (index * 10.0)
    return {
        "decision_id": f"transition_decision_{index}",
        "source_item_id": f"cut_item_{index}",
        "segment_id": f"transition_segment_{index}",
        "start_seconds": start,
        "end_seconds": start + 8.0,
        "center_seconds": start + 4.0,
        "duration_seconds": 8.0,
        "transition_type": transition_type,
        "transition_confidence": 0.83,
        "priority": "medium",
        "proposed_action": "review_transition",
        "cut_list_action": "KEEP",
        "duration_status": "duration_ok",
        "murch_score": 0.75,
        "is_protected": transition_type == "no_cut_protect",
        "is_censor_keep": transition_type == "censor_safe_keep",
        "is_technical_review": transition_type == "technical_transition_review",
        "is_scene_change_aligned": transition_type == "hard_cut_review",
        "is_beat_aligned": transition_type == "hard_cut_review",
        "is_sentence_safe": transition_type == "no_cut_protect",
        "is_dialogue_context": False,
        "reason": f"{transition_type}_reason",
        "decision_basis": {"review_only": True},
        "source_signal_ids": [],
        "warnings": [],
        "errors": [],
        "metadata": {"audit": True},
    }


def _continuity_issue(issue_type: str, index: int) -> dict:
    start = 500.0 + (index * 10.0)
    return {
        "issue_id": f"continuity_issue_{index}",
        "source_item_id": f"cut_item_{index}",
        "segment_id": f"continuity_segment_{index}",
        "start_seconds": start,
        "end_seconds": start + 4.0,
        "center_seconds": start + 2.0,
        "duration_seconds": 4.0,
        "issue_type": issue_type,
        "severity": "high",
        "confidence": 0.86,
        "priority": "high",
        "is_blocking": issue_type in {"sentence_break_risk", "censor_context_risk"},
        "is_protected_context": issue_type in {
            "sentence_break_risk",
            "context_jump_risk",
            "censor_context_risk",
        },
        "is_censor_context": issue_type == "censor_context_risk",
        "is_technical_issue": issue_type == "technical_continuity_risk",
        "requires_review": True,
        "recommendation": "review_continuity",
        "reason": f"{issue_type}_reason",
        "evidence": {"review_only": True},
        "source_signal_ids": [],
        "warnings": [],
        "errors": [],
        "metadata": {"audit": True},
    }


def _final_cut_list_item(action: str, index: int) -> dict:
    start = 600.0 + (index * 10.0)
    return {
        "final_item_id": f"final_item_{index}",
        "source_item_id": f"cut_item_{index}",
        "segment_id": f"final_segment_{index}",
        "start_seconds": start,
        "end_seconds": start + 5.0,
        "center_seconds": start + 2.5,
        "duration_seconds": 5.0,
        "final_action": action,
        "final_confidence": 0.87,
        "priority": "high" if action in {"FINAL_PROTECT", "FINAL_CENSOR_KEEP"} else "medium",
        "segment_type": "audit",
        "cut_list_action": "KEEP",
        "duration_status": "duration_ok",
        "transition_type": "hard_cut_review",
        "murch_score": 0.8,
        "continuity_blocked": action == "FINAL_BLOCKED_BY_CONTINUITY",
        "is_protected": action == "FINAL_PROTECT",
        "is_censor_keep": action == "FINAL_CENSOR_KEEP",
        "is_technical_review": action == "FINAL_TECHNICAL_REVIEW",
        "is_review_required": True,
        "is_keep_candidate": action in {"FINAL_KEEP_REVIEW", "FINAL_KEEP_HIGH_VALUE"},
        "is_trim_candidate": action == "FINAL_TRIM_REVIEW",
        "is_remove_candidate": action == "FINAL_REMOVE_REVIEW",
        "is_invalid_timing": False,
        "reason": f"{action.lower()}_reason",
        "decision_basis": {"review_only": True},
        "source_signal_ids": [],
        "warnings": [],
        "errors": [],
        "metadata": {"audit": True},
    }


def _job_with_all_block5_reports() -> Job:
    return Job.from_dict(
        {
            **_minimal_job_data(),
            "segment_classification_report": {
                "status": "ok",
                "source": "segment_classifier",
                "segments": [
                    _segment("highlight", 1),
                    _segment("protected_context", 2),
                    _segment("dead_candidate", 3),
                    _segment("censor_required_segment", 4),
                ],
            },
            "murch_scoring_report": {
                "status": "ok",
                "source": "murch_scoring",
                "segment_scores": [
                    _murch_score("high", 1),
                    _murch_score("low", 2),
                    _murch_score("protected", 3),
                    _murch_score("medium", 4, censor_required=True),
                ],
            },
            "cut_list_report": {
                "status": "ok",
                "source": "cut_list_generator",
                "items": [
                    _cut_list_item("KEEP", 1),
                    _cut_list_item("REVIEW_TRIM", 2),
                    _cut_list_item("REVIEW_REMOVE", 3),
                    _cut_list_item("PROTECT", 4),
                    _cut_list_item("CENSOR_KEEP", 5),
                ],
            },
            "clip_duration_report": {
                "status": "ok",
                "source": "clip_duration_optimizer",
                "recommendations": [
                    _clip_duration_recommendation("duration_ok", 1),
                    _clip_duration_recommendation("too_long_review", 2),
                    _clip_duration_recommendation("protect_duration", 3),
                    _clip_duration_recommendation("censor_keep_duration", 4),
                    _clip_duration_recommendation("invalid_timing_review", 5),
                ],
            },
            "transition_decision_report": {
                "status": "ok",
                "source": "transition_decision",
                "decisions": [
                    _transition_decision("hard_cut_review", 1),
                    _transition_decision("no_cut_protect", 2),
                    _transition_decision("censor_safe_keep", 3),
                    _transition_decision("technical_transition_review", 4),
                ],
            },
            "continuity_check_report": {
                "status": "completed_with_warnings",
                "source": "continuity_check",
                "issues": [
                    _continuity_issue("sentence_break_risk", 1),
                    _continuity_issue("context_jump_risk", 2),
                    _continuity_issue("censor_context_risk", 3),
                    _continuity_issue("transition_conflict", 4),
                    _continuity_issue("technical_continuity_risk", 5),
                ],
            },
            "final_cut_list_report": {
                "status": "completed_with_warnings",
                "source": "cut_list_finalizer",
                "final_items": [
                    _final_cut_list_item("FINAL_KEEP_REVIEW", 1),
                    _final_cut_list_item("FINAL_KEEP_HIGH_VALUE", 2),
                    _final_cut_list_item("FINAL_TRIM_REVIEW", 3),
                    _final_cut_list_item("FINAL_REMOVE_REVIEW", 4),
                    _final_cut_list_item("FINAL_PROTECT", 5),
                    _final_cut_list_item("FINAL_CENSOR_KEEP", 6),
                    _final_cut_list_item("FINAL_TECHNICAL_REVIEW", 7),
                    _final_cut_list_item("FINAL_BLOCKED_BY_CONTINUITY", 8),
                ],
            },
        }
    )


def _block5_signals(result) -> list[dict]:
    return [
        signal
        for signal in result.signals
        if signal.get("source") in set(BLOCK5_SOURCES)
    ]


def test_unified_registry_collects_all_block5_sources() -> None:
    job = _job_with_all_block5_reports()

    result = run_unified_edit_signal_registry_for_job(job)

    assert result.status in {"ok", "completed_with_warnings"}
    for source in BLOCK5_SOURCES:
        assert result.source_counts.get(source, 0) > 0, source


def test_unified_registry_collects_required_block5_signal_types() -> None:
    result = run_unified_edit_signal_registry_for_job(_job_with_all_block5_reports())

    for source, signal_types in REQUIRED_SIGNAL_TYPES.items():
        for signal_type in signal_types:
            assert result.type_counts.get(signal_type, 0) >= 1, (source, signal_type)


def test_block5_unified_signals_have_required_fields() -> None:
    result = run_unified_edit_signal_registry_for_job(_job_with_all_block5_reports())
    signals = _block5_signals(result)

    assert signals
    for signal in signals:
        for field in (
            "signal_id",
            "signal_type",
            "source",
            "start_seconds",
            "center_seconds",
            "action_hint",
            "priority",
            "metadata",
        ):
            assert field in signal, (signal.get("source"), signal.get("signal_type"), field)

        assert isinstance(signal["metadata"], dict)


def test_block5_unified_action_hints_have_no_execution_words() -> None:
    result = run_unified_edit_signal_registry_for_job(_job_with_all_block5_reports())

    for signal in _block5_signals(result):
        action_hint = str(signal.get("action_hint") or "").lower()
        for dangerous in DANGEROUS_ACTION_WORDS:
            assert dangerous not in action_hint, (dangerous, signal)


def test_final_cut_list_signals_stay_reviewable_and_protective() -> None:
    result = run_unified_edit_signal_registry_for_job(_job_with_all_block5_reports())
    final_signals = [
        signal
        for signal in result.signals
        if signal.get("source") == "cut_list_finalizer"
    ]

    assert final_signals
    expected_action_hints = {
        "final_cut_list_keep_review": "review_final_keep_candidate",
        "final_cut_list_keep_high_value": "review_final_high_value_keep",
        "final_cut_list_trim_review": "review_final_trim_candidate",
        "final_cut_list_remove_review": "review_final_remove_candidate",
        "final_cut_list_protect": "protect_final_cutlist_segment",
        "final_cut_list_censor_keep": "preserve_final_segment_for_censor_sfx",
        "final_cut_list_technical_review": "review_final_technical_risk",
        "final_cut_list_blocked_by_continuity": "block_final_cutlist_until_review",
    }

    by_type = {signal["signal_type"]: signal for signal in final_signals}
    for signal_type, action_hint in expected_action_hints.items():
        signal = by_type[signal_type]
        assert signal["action_hint"] == action_hint
        assert signal["metadata"]["review_only"] is True
