from pathlib import Path

from core.unified_edit_signal_registry import run_unified_edit_signal_registry_for_job
from models.job import Job


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "core" / "unified_edit_signal_registry.py"
TEST_FILE = ROOT / "tests" / "test_continuity_check_registry_integration_smoke.py"

FORBIDDEN_ACTION_HINTS = [
    "force_cut",
    "auto_remove",
    "hard_remove",
    "remove_now",
    "auto_cut",
    "auto_trim",
    "auto_transition",
    "auto_fade",
    "auto_j_cut",
    "auto_l_cut",
    "auto_highlight",
    "highlight_now",
    "auto_hook",
    "auto_mute",
    "censor_now",
    "delete_segment",
    "drop_segment",
    "timeline_apply_now",
    "apply_cut",
    "render_now",
    "execute_cut",
    "final_cut",
    "apply_transition",
]


def _make_job(extra=None):
    data = {
        "job_id": "job_continuity_check_registry_test",
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
    if extra:
        data.update(extra)
    return Job.from_dict(data)


def _issue(issue_type: str, index: int):
    return {
        "issue_id": f"continuity_issue_{index}",
        "source_item_id": f"item_{index}",
        "segment_id": f"seg_{index}",
        "start_seconds": float(index * 10),
        "end_seconds": float(index * 10 + 4),
        "center_seconds": float(index * 10 + 2),
        "duration_seconds": 4.0,
        "issue_type": issue_type,
        "severity": "high",
        "confidence": 0.85,
        "priority": "high",
        "is_blocking": issue_type in {
            "sentence_break_risk",
            "censor_context_risk",
            "protected_context_violation",
        },
        "is_protected_context": issue_type in {
            "sentence_break_risk",
            "context_jump_risk",
            "censor_context_risk",
            "protected_context_violation",
        },
        "is_censor_context": issue_type == "censor_context_risk",
        "is_technical_issue": issue_type
        in {"invalid_timing", "overlap_risk", "gap_risk", "technical_continuity_risk"},
        "requires_review": True,
        "recommendation": "review_continuity",
        "reason": f"{issue_type}_reason",
        "evidence": {"review_only": True},
        "source_signal_ids": [],
        "warnings": [],
        "errors": [],
        "metadata": {"review_only": True},
    }


def _all_continuity_issues():
    return [
        _issue("sentence_break_risk", 1),
        _issue("context_jump_risk", 2),
        _issue("censor_context_risk", 3),
        _issue("invalid_timing", 4),
        _issue("overlap_risk", 5),
        _issue("gap_risk", 6),
        _issue("transition_conflict", 7),
        _issue("protected_context_violation", 8),
        _issue("technical_continuity_risk", 9),
        _issue("unknown_continuity_review", 10),
    ]


def test_registry_collects_continuity_check_source_counts():
    job = _make_job(
        {
            "continuity_check_report": {
                "status": "completed_with_warnings",
                "issues": _all_continuity_issues(),
            }
        }
    )

    result = run_unified_edit_signal_registry_for_job(job)

    assert result.source_counts["continuity_check"] == 10


def test_registry_collects_continuity_sentence_break_type_count():
    result = run_unified_edit_signal_registry_for_job(
        _make_job({"continuity_check_report": {"issues": _all_continuity_issues()}})
    )

    assert result.type_counts["continuity_sentence_break_risk"] == 1


def test_registry_collects_continuity_context_jump_type_count():
    result = run_unified_edit_signal_registry_for_job(
        _make_job({"continuity_check_report": {"issues": _all_continuity_issues()}})
    )

    assert result.type_counts["continuity_context_jump_risk"] == 1


def test_registry_collects_continuity_censor_context_type_count():
    result = run_unified_edit_signal_registry_for_job(
        _make_job({"continuity_check_report": {"issues": _all_continuity_issues()}})
    )

    assert result.type_counts["continuity_censor_context_risk"] == 1


def test_registry_collects_continuity_timing_type_count():
    result = run_unified_edit_signal_registry_for_job(
        _make_job({"continuity_check_report": {"issues": _all_continuity_issues()}})
    )

    assert result.type_counts["continuity_timing_issue"] == 3


def test_registry_collects_continuity_transition_conflict_type_count():
    result = run_unified_edit_signal_registry_for_job(
        _make_job({"continuity_check_report": {"issues": _all_continuity_issues()}})
    )

    assert result.type_counts["continuity_transition_conflict"] == 1


def test_registry_collects_continuity_protected_context_type_count():
    result = run_unified_edit_signal_registry_for_job(
        _make_job({"continuity_check_report": {"issues": _all_continuity_issues()}})
    )

    assert result.type_counts["continuity_protected_context_violation"] == 1


def test_registry_collects_continuity_technical_risk_type_count():
    result = run_unified_edit_signal_registry_for_job(
        _make_job({"continuity_check_report": {"issues": _all_continuity_issues()}})
    )

    assert result.type_counts["continuity_technical_risk"] == 1


def test_registry_collects_continuity_unknown_review_type_count():
    result = run_unified_edit_signal_registry_for_job(
        _make_job({"continuity_check_report": {"issues": _all_continuity_issues()}})
    )

    assert result.type_counts["continuity_unknown_review"] == 1


def test_registry_fallback_uses_continuity_check_issues():
    job = _make_job(
        {
            "continuity_check_issues": [
                _issue("sentence_break_risk", 1),
                _issue("censor_context_risk", 2),
            ]
        }
    )

    result = run_unified_edit_signal_registry_for_job(job)

    assert result.source_counts["continuity_check"] == 2
    assert result.type_counts["continuity_sentence_break_risk"] == 1
    assert result.type_counts["continuity_censor_context_risk"] == 1


def test_registry_has_no_forbidden_continuity_action_hints():
    job = _make_job(
        {
            "continuity_check_report": {
                "status": "completed_with_warnings",
                "issues": _all_continuity_issues(),
            }
        }
    )

    result = run_unified_edit_signal_registry_for_job(job)
    continuity_signals = [
        signal for signal in result.signals if signal.get("source") == "continuity_check"
    ]

    assert continuity_signals
    dumped = str(continuity_signals).lower()
    for forbidden in FORBIDDEN_ACTION_HINTS:
        assert forbidden not in dumped


def test_registry_static_contains_continuity_check_adapter_and_source():
    text = REGISTRY_PATH.read_text(encoding="utf-8")

    assert "adapt_continuity_check_report_to_signals" in text
    assert 'SOURCE_CONTINUITY_CHECK = "continuity_check"' in text
    assert "source_counts[SOURCE_CONTINUITY_CHECK]" in text
    assert "continuity_check_report" in text
    assert "continuity_check_issues" in text


def test_existing_sources_still_exist():
    text = REGISTRY_PATH.read_text(encoding="utf-8")

    existing_sources = [
        'SOURCE_TRANSITION_DECISION = "transition_decision"',
        'SOURCE_CLIP_DURATION_OPTIMIZER = "clip_duration_optimizer"',
        'SOURCE_CUT_LIST_GENERATOR = "cut_list_generator"',
        'SOURCE_MURCH_SCORING = "murch_scoring"',
        'SOURCE_SEGMENT_CLASSIFIER = "segment_classifier"',
        'SOURCE_CONTENT_VALUE = "content_value"',
        'SOURCE_PROFANITY_CENSOR = "profanity_censor"',
        'SOURCE_DEAD_CONTENT = "dead_content"',
        'SOURCE_SENTENCE_BOUNDARY = "sentence_boundary"',
        'SOURCE_KEYWORD_EMOTION = "keyword_emotion"',
        'SOURCE_INTERACTION_CLASSIFICATION = "interaction_classification"',
        'SOURCE_SCENE_CHANGE = "scene_change"',
        'SOURCE_MOTION_ANALYSIS = "motion_analysis"',
        'SOURCE_FACE_REACTION = "face_reaction"',
        'SOURCE_STUTTER_DETECTION = "stutter_detection"',
        'SOURCE_SCREEN_CONTENT = "screen_content"',
        'SOURCE_VISUAL_ENERGY = "visual_energy"',
    ]

    for source in existing_sources:
        assert source in text


def test_existing_adapter_calls_still_exist():
    text = REGISTRY_PATH.read_text(encoding="utf-8")

    adapters = [
        "adapt_transition_decision_report_to_signals",
        "adapt_clip_duration_report_to_signals",
        "adapt_cut_list_report_to_signals",
        "adapt_murch_scoring_report_to_signals",
        "adapt_segment_classification_report_to_signals",
        "adapt_content_value_report_to_signals",
        "adapt_profanity_censor_report_to_signals",
        "adapt_dead_content_report_to_signals",
        "adapt_sentence_boundary_report_to_signals",
        "adapt_keyword_emotion_report_to_signals",
        "adapt_interaction_classification_report_to_signals",
        "adapt_scene_change_report_to_signals",
        "adapt_motion_analysis_report_to_signals",
        "adapt_face_reaction_report_to_signals",
        "adapt_stutter_detection_report_to_signals",
        "adapt_screen_content_report_to_signals",
        "adapt_visual_energy_report_to_signals",
    ]

    for adapter in adapters:
        assert adapter in text


def test_new_files_have_no_bom_and_end_with_newline():
    for file_path in [REGISTRY_PATH, TEST_FILE]:
        raw = file_path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), file_path
        assert raw.endswith(b"\n"), file_path
