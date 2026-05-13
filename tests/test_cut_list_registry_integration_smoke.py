from pathlib import Path

from core.unified_edit_signal_registry import run_unified_edit_signal_registry_for_job
from models.job import Job


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "core" / "unified_edit_signal_registry.py"


def _make_job(extra=None):
    data = {
        "job_id": "job_cut_list_registry_test",
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


def _cut_list_item(action: str, index: int):
    return {
        "item_id": f"item_{index}",
        "segment_id": f"seg_{index}",
        "start_seconds": float(index * 10),
        "end_seconds": float(index * 10 + 5),
        "center_seconds": float(index * 10 + 2.5),
        "duration_seconds": 5.0,
        "proposed_action": action,
        "action_confidence": 0.8,
        "priority": "medium",
        "segment_type": "test",
        "murch_score": 0.7,
        "content_value_score": 0.6,
        "risk_score": 0.1,
        "protection_score": 0.0,
        "censor_required": action == "CENSOR_KEEP",
        "is_protected": action == "PROTECT",
        "is_review_required": action != "KEEP",
        "reason": f"reason {action}",
        "decision_basis": {"test": True},
        "source_signal_ids": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


def test_registry_collects_cut_list_source_counts():
    job = _make_job(
        {
            "cut_list_report": {
                "status": "ok",
                "items": [
                    _cut_list_item("KEEP", 1),
                    _cut_list_item("REVIEW_KEEP", 2),
                    _cut_list_item("REVIEW_TRIM", 3),
                    _cut_list_item("REVIEW_REMOVE", 4),
                    _cut_list_item("PROTECT", 5),
                    _cut_list_item("CENSOR_KEEP", 6),
                    _cut_list_item("TECHNICAL_REVIEW", 7),
                    _cut_list_item("UNKNOWN_REVIEW", 8),
                ],
            }
        }
    )

    result = run_unified_edit_signal_registry_for_job(job)

    assert result.source_counts["cut_list_generator"] == 8


def test_registry_collects_all_cut_list_type_counts():
    job = _make_job(
        {
            "cut_list_report": {
                "status": "ok",
                "items": [
                    _cut_list_item("KEEP", 1),
                    _cut_list_item("REVIEW_KEEP", 2),
                    _cut_list_item("REVIEW_TRIM", 3),
                    _cut_list_item("REVIEW_REMOVE", 4),
                    _cut_list_item("PROTECT", 5),
                    _cut_list_item("CENSOR_KEEP", 6),
                    _cut_list_item("TECHNICAL_REVIEW", 7),
                    _cut_list_item("UNKNOWN_REVIEW", 8),
                ],
            }
        }
    )

    result = run_unified_edit_signal_registry_for_job(job)

    assert result.type_counts["cut_list_keep_candidate"] == 1
    assert result.type_counts["cut_list_review_keep"] == 1
    assert result.type_counts["cut_list_review_trim"] == 1
    assert result.type_counts["cut_list_review_remove"] == 1
    assert result.type_counts["cut_list_protect_segment"] == 1
    assert result.type_counts["cut_list_censor_keep"] == 1
    assert result.type_counts["cut_list_technical_review"] == 1
    assert result.type_counts["cut_list_unknown_review"] == 1


def test_registry_cut_list_fallback_uses_cut_list_items():
    job = _make_job(
        {
            "cut_list_items": [
                _cut_list_item("KEEP", 1),
                _cut_list_item("CENSOR_KEEP", 2),
            ]
        }
    )

    result = run_unified_edit_signal_registry_for_job(job)

    assert result.source_counts["cut_list_generator"] == 2
    assert result.type_counts["cut_list_keep_candidate"] == 1
    assert result.type_counts["cut_list_censor_keep"] == 1


def test_review_remove_is_only_review_signal():
    job = _make_job(
        {
            "cut_list_report": {
                "status": "ok",
                "items": [_cut_list_item("REVIEW_REMOVE", 1)],
            }
        }
    )

    result = run_unified_edit_signal_registry_for_job(job)

    signal = next(
        signal
        for signal in result.signals
        if signal["signal_type"] == "cut_list_review_remove"
    )

    assert signal["action_hint"] == "review_remove_candidate"
    assert signal["action_hint"] != "remove_now"
    assert signal["action_hint"] != "auto_remove"


def test_registry_has_no_forbidden_cut_list_action_hints():
    job = _make_job(
        {
            "cut_list_report": {
                "status": "ok",
                "items": [
                    _cut_list_item("REVIEW_REMOVE", 1),
                    _cut_list_item("REVIEW_TRIM", 2),
                    _cut_list_item("CENSOR_KEEP", 3),
                    _cut_list_item("PROTECT", 4),
                ],
            }
        }
    )

    result = run_unified_edit_signal_registry_for_job(job)

    forbidden = [
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
        "apply_cut",
        "render_now",
        "execute_cut",
        "final_cut",
    ]

    cut_list_signals = [
        signal
        for signal in result.signals
        if signal.get("source") == "cut_list_generator"
    ]

    assert cut_list_signals

    for signal in cut_list_signals:
        action_hint = str(signal.get("action_hint") or "").lower()
        for word in forbidden:
            assert word not in action_hint


def test_registry_static_contains_cut_list_adapter_and_source():
    text = REGISTRY_PATH.read_text(encoding="utf-8")

    assert "adapt_cut_list_report_to_signals" in text
    assert 'SOURCE_CUT_LIST_GENERATOR = "cut_list_generator"' in text
    assert 'source_counts[SOURCE_CUT_LIST_GENERATOR]' in text
    assert "cut_list_report" in text
    assert "cut_list_items" in text


def test_existing_source_constants_still_exist():
    text = REGISTRY_PATH.read_text(encoding="utf-8")

    existing_sources = [
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
    files = [
        REGISTRY_PATH,
        ROOT / "tests" / "test_cut_list_registry_integration_smoke.py",
    ]

    for path in files:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf")
        assert raw.endswith(b"\n")
