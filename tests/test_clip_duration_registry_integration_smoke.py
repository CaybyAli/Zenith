from pathlib import Path

from core.unified_edit_signal_registry import run_unified_edit_signal_registry_for_job
from models.job import Job


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "core" / "unified_edit_signal_registry.py"
TEST_FILE = ROOT / "tests" / "test_clip_duration_registry_integration_smoke.py"

FORBIDDEN_ACTION_HINTS = [
    "force_cut",
    "auto_remove",
    "hard_remove",
    "remove_now",
    "auto_cut",
    "auto_trim",
    "auto_extend",
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
]


def _make_job(extra=None):
    data = {
        "job_id": "job_clip_duration_registry_test",
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


def _clip_duration_recommendation(status: str, index: int):
    return {
        "recommendation_id": f"clip_duration_{index}",
        "source_item_id": f"cut_item_{index}",
        "segment_id": f"seg_{index}",
        "start_seconds": float(index * 10),
        "end_seconds": float(index * 10 + 8),
        "center_seconds": float(index * 10 + 4),
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
        "confidence": 0.8,
        "priority": "medium",
        "is_too_short": status in {"too_short_review", "extend_review"},
        "is_too_long": status in {"too_long_review", "trim_review"},
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
        "metadata": {"review_only": True},
    }


def test_registry_collects_clip_duration_source_counts():
    job = _make_job(
        {
            "clip_duration_report": {
                "status": "ok",
                "recommendations": [
                    _clip_duration_recommendation("duration_ok", 1),
                    _clip_duration_recommendation("too_short_review", 2),
                    _clip_duration_recommendation("too_long_review", 3),
                    _clip_duration_recommendation("protect_duration", 4),
                    _clip_duration_recommendation("censor_keep_duration", 5),
                    _clip_duration_recommendation("technical_review", 6),
                    _clip_duration_recommendation("invalid_timing_review", 7),
                    _clip_duration_recommendation("unknown_review", 8),
                ],
            }
        }
    )

    result = run_unified_edit_signal_registry_for_job(job)

    assert result.source_counts["clip_duration_optimizer"] == 8


def test_registry_collects_clip_duration_type_counts():
    job = _make_job(
        {
            "clip_duration_report": {
                "status": "ok",
                "recommendations": [
                    _clip_duration_recommendation("duration_ok", 1),
                    _clip_duration_recommendation("too_short_review", 2),
                    _clip_duration_recommendation("too_long_review", 3),
                    _clip_duration_recommendation("protect_duration", 4),
                    _clip_duration_recommendation("censor_keep_duration", 5),
                    _clip_duration_recommendation("technical_review", 6),
                    _clip_duration_recommendation("invalid_timing_review", 7),
                    _clip_duration_recommendation("unknown_review", 8),
                ],
            }
        }
    )

    result = run_unified_edit_signal_registry_for_job(job)

    assert result.type_counts["clip_duration_ok"] == 1
    assert result.type_counts["clip_duration_too_short_review"] == 1
    assert result.type_counts["clip_duration_too_long_review"] == 1
    assert result.type_counts["clip_duration_protected"] == 1
    assert result.type_counts["clip_duration_censor_keep"] == 1
    assert result.type_counts["clip_duration_technical_review"] == 1
    assert result.type_counts["clip_duration_invalid_timing"] == 1
    assert result.type_counts["clip_duration_unknown_review"] == 1


def test_registry_fallback_uses_clip_duration_recommendations():
    job = _make_job(
        {
            "clip_duration_recommendations": [
                _clip_duration_recommendation("duration_ok", 1),
                _clip_duration_recommendation("censor_keep_duration", 2),
            ]
        }
    )

    result = run_unified_edit_signal_registry_for_job(job)

    assert result.source_counts["clip_duration_optimizer"] == 2
    assert result.type_counts["clip_duration_ok"] == 1
    assert result.type_counts["clip_duration_censor_keep"] == 1


def test_review_trim_remains_review_only():
    job = _make_job(
        {
            "clip_duration_report": {
                "status": "ok",
                "recommendations": [
                    {
                        **_clip_duration_recommendation("trim_review", 1),
                        "suggested_start_seconds": 11.0,
                        "suggested_end_seconds": 19.0,
                    }
                ],
            }
        }
    )

    result = run_unified_edit_signal_registry_for_job(job)

    signal = next(
        signal
        for signal in result.signals
        if signal["signal_type"] == "clip_duration_too_long_review"
    )

    assert signal["action_hint"] == "review_trim_duration_candidate"
    assert signal["metadata"]["review_only"] is True


def test_registry_has_no_forbidden_clip_duration_action_hints():
    job = _make_job(
        {
            "clip_duration_report": {
                "status": "ok",
                "recommendations": [
                    _clip_duration_recommendation("duration_ok", 1),
                    _clip_duration_recommendation("extend_review", 2),
                    _clip_duration_recommendation("trim_review", 3),
                    _clip_duration_recommendation("protect_duration", 4),
                    _clip_duration_recommendation("censor_keep_duration", 5),
                    _clip_duration_recommendation("technical_review", 6),
                    _clip_duration_recommendation("invalid_timing_review", 7),
                    _clip_duration_recommendation("unknown_review", 8),
                ],
            }
        }
    )

    result = run_unified_edit_signal_registry_for_job(job)

    clip_duration_signals = [
        signal
        for signal in result.signals
        if signal.get("source") == "clip_duration_optimizer"
    ]

    assert clip_duration_signals

    dumped = str(clip_duration_signals).lower()

    for forbidden in FORBIDDEN_ACTION_HINTS:
        assert forbidden not in dumped


def test_existing_source_constants_still_exist():
    text = REGISTRY_PATH.read_text(encoding="utf-8")

    existing_sources = [
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


def test_clip_duration_static_registry_integration_exists():
    text = REGISTRY_PATH.read_text(encoding="utf-8")

    assert "adapt_clip_duration_report_to_signals" in text
    assert 'SOURCE_CLIP_DURATION_OPTIMIZER = "clip_duration_optimizer"' in text
    assert 'source_counts[SOURCE_CLIP_DURATION_OPTIMIZER]' in text
    assert "clip_duration_report" in text
    assert "clip_duration_recommendations" in text


def test_existing_adapter_calls_still_exist():
    text = REGISTRY_PATH.read_text(encoding="utf-8")

    adapters = [
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
