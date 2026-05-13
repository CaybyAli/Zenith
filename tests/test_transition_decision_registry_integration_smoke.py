from pathlib import Path

from core.unified_edit_signal_registry import run_unified_edit_signal_registry_for_job
from models.job import Job


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "core" / "unified_edit_signal_registry.py"
TEST_FILE = ROOT / "tests" / "test_transition_decision_registry_integration_smoke.py"

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
        "job_id": "job_transition_decision_registry_test",
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


def _transition_decision(transition_type: str, index: int):
    return {
        "decision_id": f"transition_decision_{index}",
        "source_item_id": f"cut_item_{index}",
        "segment_id": f"seg_{index}",
        "start_seconds": float(index * 10),
        "end_seconds": float(index * 10 + 8),
        "center_seconds": float(index * 10 + 4),
        "duration_seconds": 8.0,
        "transition_type": transition_type,
        "transition_confidence": 0.8,
        "priority": "medium",
        "proposed_action": "review_transition",
        "cut_list_action": "KEEP",
        "duration_status": "duration_ok",
        "murch_score": 0.75,
        "is_protected": transition_type == "no_cut_protect",
        "is_censor_keep": transition_type == "censor_safe_keep",
        "is_technical_review": transition_type == "technical_transition_review",
        "is_scene_change_aligned": transition_type in {
            "hard_cut_review",
            "quick_fade_review",
        },
        "is_beat_aligned": transition_type == "hard_cut_review",
        "is_sentence_safe": transition_type == "no_cut_protect",
        "is_dialogue_context": transition_type in {"j_cut_review", "l_cut_review"},
        "reason": f"{transition_type}_reason",
        "decision_basis": {"review_only": True},
        "source_signal_ids": [],
        "warnings": [],
        "errors": [],
        "metadata": {"review_only": True},
    }


def _all_transition_decisions():
    return [
        _transition_decision("hard_cut_review", 1),
        _transition_decision("j_cut_review", 2),
        _transition_decision("l_cut_review", 3),
        _transition_decision("quick_fade_review", 4),
        _transition_decision("no_cut_protect", 5),
        _transition_decision("censor_safe_keep", 6),
        _transition_decision("technical_transition_review", 7),
        _transition_decision("transition_unknown_review", 8),
    ]


def test_registry_collects_transition_decision_source_counts():
    job = _make_job(
        {
            "transition_decision_report": {
                "status": "ok",
                "decisions": _all_transition_decisions(),
            }
        }
    )

    result = run_unified_edit_signal_registry_for_job(job)

    assert result.source_counts["transition_decision"] == 8


def test_registry_collects_transition_decision_type_counts():
    job = _make_job(
        {
            "transition_decision_report": {
                "status": "ok",
                "decisions": _all_transition_decisions(),
            }
        }
    )

    result = run_unified_edit_signal_registry_for_job(job)

    assert result.type_counts["transition_hard_cut_review"] == 1
    assert result.type_counts["transition_j_cut_review"] == 1
    assert result.type_counts["transition_l_cut_review"] == 1
    assert result.type_counts["transition_quick_fade_review"] == 1
    assert result.type_counts["transition_no_cut_protect"] == 1
    assert result.type_counts["transition_censor_safe_keep"] == 1
    assert result.type_counts["transition_technical_review"] == 1
    assert result.type_counts["transition_unknown_review"] == 1


def test_registry_fallback_uses_transition_decision_decisions():
    job = _make_job(
        {
            "transition_decision_decisions": [
                _transition_decision("hard_cut_review", 1),
                _transition_decision("censor_safe_keep", 2),
            ]
        }
    )

    result = run_unified_edit_signal_registry_for_job(job)

    assert result.source_counts["transition_decision"] == 2
    assert result.type_counts["transition_hard_cut_review"] == 1
    assert result.type_counts["transition_censor_safe_keep"] == 1


def test_transition_review_signals_remain_review_only():
    job = _make_job(
        {
            "transition_decision_report": {
                "status": "ok",
                "decisions": [
                    _transition_decision("hard_cut_review", 1),
                ],
            }
        }
    )

    result = run_unified_edit_signal_registry_for_job(job)

    signal = next(
        signal
        for signal in result.signals
        if signal["signal_type"] == "transition_hard_cut_review"
    )

    assert signal["action_hint"] == "review_hard_cut_transition"
    assert signal["metadata"]["review_only"] is True


def test_registry_has_no_forbidden_transition_decision_action_hints():
    job = _make_job(
        {
            "transition_decision_report": {
                "status": "ok",
                "decisions": _all_transition_decisions(),
            }
        }
    )

    result = run_unified_edit_signal_registry_for_job(job)

    transition_signals = [
        signal
        for signal in result.signals
        if signal.get("source") == "transition_decision"
    ]

    assert transition_signals

    dumped = str(transition_signals).lower()

    for forbidden in FORBIDDEN_ACTION_HINTS:
        assert forbidden not in dumped


def test_existing_source_constants_still_exist():
    text = REGISTRY_PATH.read_text(encoding="utf-8")

    existing_sources = [
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


def test_transition_decision_static_registry_integration_exists():
    text = REGISTRY_PATH.read_text(encoding="utf-8")

    assert "adapt_transition_decision_report_to_signals" in text
    assert 'SOURCE_TRANSITION_DECISION = "transition_decision"' in text
    assert "source_counts[SOURCE_TRANSITION_DECISION]" in text
    assert "transition_decision_report" in text
    assert "transition_decision_decisions" in text


def test_existing_adapter_calls_still_exist():
    text = REGISTRY_PATH.read_text(encoding="utf-8")

    adapters = [
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
