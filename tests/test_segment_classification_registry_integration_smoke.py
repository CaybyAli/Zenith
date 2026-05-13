from pathlib import Path

from core.unified_edit_signal_registry import build_unified_edit_signal_result
from models.job import Job


ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = ROOT / "core" / "unified_edit_signal_registry.py"


def _minimal_job_data() -> dict:
    return {
        "job_id": "job_segment_registry_test",
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
    start = 10.0 + (index * 10.0)
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
        "content_value_score": 0.8 if segment_type in {"highlight", "hook_candidate"} else 0.0,
        "dead_content_score": 0.8 if segment_type == "dead_candidate" else 0.0,
        "protection_score": 0.8 if segment_type == "protected_context" else 0.0,
        "technical_risk_score": 0.8 if segment_type == "technical_warning" else 0.0,
        "hook_candidate_score": 0.8 if segment_type == "hook_candidate" else 0.0,
        "censor_required": segment_type == "censor_required_segment",
        "is_highlight_candidate": segment_type == "highlight",
        "is_hook_candidate": segment_type == "hook_candidate",
        "is_protected_context": segment_type == "protected_context",
        "is_dead_candidate": segment_type == "dead_candidate",
        "is_transition_candidate": segment_type == "transition",
        "is_technical_warning": segment_type == "technical_warning",
        "recommendation": f"review_{segment_type}",
        "evidence": {"test": True},
        "source_signal_ids": [f"source_sig_{index}"],
        "warnings": [],
        "errors": [],
        "metadata": {"test": True},
    }


def _job_with_segment_classifications() -> Job:
    segment_types = [
        "highlight",
        "hook_candidate",
        "protected_context",
        "dead_candidate",
        "censor_required_segment",
        "technical_warning",
        "transition",
        "filler",
        "normal_content",
    ]

    return Job.from_dict(
        {
            **_minimal_job_data(),
            "segment_classification_report": {
                "status": "ok",
                "source": "segment_classifier",
                "segments": [
                    _segment(segment_type, index)
                    for index, segment_type in enumerate(segment_types)
                ],
                "segment_count": len(segment_types),
                "recommendation": "review_segment_classification",
            },
        }
    )


def test_registry_collects_segment_classifier_source_counts() -> None:
    job = _job_with_segment_classifications()

    result = build_unified_edit_signal_result(job)

    assert result.status in {"ok", "completed_with_warnings"}
    assert result.source_counts["segment_classifier"] == 9


def test_registry_collects_segment_classifier_type_counts() -> None:
    job = _job_with_segment_classifications()

    result = build_unified_edit_signal_result(job)

    assert result.type_counts["segment_highlight_candidate"] == 1
    assert result.type_counts["segment_hook_candidate"] == 1
    assert result.type_counts["segment_protected_context"] == 1
    assert result.type_counts["segment_dead_candidate"] == 1
    assert result.type_counts["segment_censor_required"] == 1
    assert result.type_counts["segment_technical_warning"] == 1
    assert result.type_counts["segment_transition_candidate"] == 1
    assert result.type_counts["segment_filler_candidate"] == 1
    assert result.type_counts["segment_normal_content"] == 1


def test_registry_segment_classifier_signals_are_review_only() -> None:
    job = _job_with_segment_classifications()

    result = build_unified_edit_signal_result(job)

    forbidden_action_hints = [
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

    segment_signals = [
        signal for signal in result.signals
        if signal.get("source") == "segment_classifier"
    ]

    assert segment_signals

    for signal in segment_signals:
        action_hint = str(signal.get("action_hint") or "").lower()
        for forbidden in forbidden_action_hints:
            assert forbidden not in action_hint


def test_registry_uses_segment_classification_adapter() -> None:
    text = REGISTRY_PATH.read_text(encoding="utf-8")

    assert "adapt_segment_classification_report_to_signals" in text
    assert 'SOURCE_SEGMENT_CLASSIFIER = "segment_classifier"' in text
    assert 'source_counts[SOURCE_SEGMENT_CLASSIFIER]' in text
    assert "_job_attr(job, \"segment_classification_report\")" in text
    assert "_job_attr(" in text
    assert "\"segment_classification_segments\"" in text


def test_existing_registry_sources_remain_present() -> None:
    text = REGISTRY_PATH.read_text(encoding="utf-8")

    expected_sources = [
        "content_value",
        "profanity_censor",
        "dead_content",
        "sentence_boundary",
        "keyword_emotion",
        "interaction_classification",
        "scene_change",
        "motion_analysis",
        "face_reaction",
        "stutter_detection",
        "screen_content",
        "visual_energy",
    ]

    for source in expected_sources:
        assert source in text


def test_registry_file_has_no_bom_and_ends_with_newline() -> None:
    files = [
        REGISTRY_PATH,
        ROOT / "tests" / "test_segment_classification_registry_integration_smoke.py",
    ]

    for path in files:
        content = path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert content.endswith(b"\n"), f"{path} does not end with newline"
