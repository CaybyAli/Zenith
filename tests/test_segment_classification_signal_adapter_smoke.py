from pathlib import Path

from core.segment_classification_signal_adapter import (
    SegmentClassificationSignalAdapterResult,
    adapt_segment_classification_report_to_signals,
)


ROOT = Path(__file__).resolve().parents[1]


def _segment(segment_type: str, segment_id: str | None = None) -> dict:
    return {
        "segment_id": segment_id or f"segment_{segment_type}",
        "start_seconds": 10.0,
        "end_seconds": 15.0,
        "center_seconds": 12.5,
        "duration_seconds": 5.0,
        "segment_type": segment_type,
        "confidence": 0.9,
        "segment_score": 0.85,
        "content_value_score": 0.8,
        "dead_content_score": 0.0,
        "protection_score": 0.0,
        "technical_risk_score": 0.0,
        "hook_candidate_score": 0.0,
        "censor_required": segment_type == "censor_required_segment",
        "is_highlight_candidate": segment_type == "highlight",
        "is_hook_candidate": segment_type == "hook_candidate",
        "is_protected_context": segment_type == "protected_context",
        "is_dead_candidate": segment_type == "dead_candidate",
        "is_transition_candidate": segment_type == "transition",
        "is_technical_warning": segment_type == "technical_warning",
        "recommendation": f"review_{segment_type}",
        "evidence": {"test": True},
        "source_signal_ids": ["sig_1"],
        "warnings": [],
        "errors": [],
        "metadata": {"source_test": True},
    }


def _single_signal(segment_type: str) -> dict:
    result = adapt_segment_classification_report_to_signals(
        {"segments": [_segment(segment_type)]},
        metadata={"job_id": "job_test"},
    )

    assert result.status == "ok"
    assert result.signal_count == 1

    return result.signals[0]


def test_highlight_maps_to_segment_highlight_candidate() -> None:
    signal = _single_signal("highlight")

    assert signal["signal_type"] == "segment_highlight_candidate"
    assert signal["source"] == "segment_classifier"
    assert signal["action_hint"] == "review_segment_highlight_candidate"
    assert signal["priority"] == "high"


def test_hook_maps_to_segment_hook_candidate() -> None:
    signal = _single_signal("hook_candidate")

    assert signal["signal_type"] == "segment_hook_candidate"
    assert signal["source"] == "segment_classifier"
    assert signal["action_hint"] == "review_segment_hook_candidate"
    assert signal["priority"] == "high"


def test_protected_maps_to_segment_protected_context() -> None:
    signal = _single_signal("protected_context")

    assert signal["signal_type"] == "segment_protected_context"
    assert signal["source"] == "segment_classifier"
    assert signal["action_hint"] == "protect_segment_context"
    assert signal["priority"] == "high"


def test_dead_maps_to_segment_dead_candidate() -> None:
    signal = _single_signal("dead_candidate")

    assert signal["signal_type"] == "segment_dead_candidate"
    assert signal["source"] == "segment_classifier"
    assert signal["action_hint"] == "review_segment_dead_candidate"
    assert signal["priority"] == "medium"


def test_censor_maps_to_segment_censor_required() -> None:
    signal = _single_signal("censor_required_segment")

    assert signal["signal_type"] == "segment_censor_required"
    assert signal["source"] == "segment_classifier"
    assert signal["action_hint"] == "preserve_segment_with_censor_sfx_review"
    assert signal["priority"] == "high"


def test_technical_maps_to_segment_technical_warning() -> None:
    signal = _single_signal("technical_warning")

    assert signal["signal_type"] == "segment_technical_warning"
    assert signal["source"] == "segment_classifier"
    assert signal["action_hint"] == "review_segment_technical_warning"
    assert signal["priority"] == "high"


def test_transition_maps_to_segment_transition_candidate() -> None:
    signal = _single_signal("transition")

    assert signal["signal_type"] == "segment_transition_candidate"
    assert signal["source"] == "segment_classifier"
    assert signal["action_hint"] == "review_segment_transition"
    assert signal["priority"] == "medium"


def test_filler_maps_to_segment_filler_candidate() -> None:
    signal = _single_signal("filler")

    assert signal["signal_type"] == "segment_filler_candidate"
    assert signal["source"] == "segment_classifier"
    assert signal["action_hint"] == "review_segment_filler_candidate"
    assert signal["priority"] == "medium"


def test_normal_content_maps_to_segment_normal_content() -> None:
    signal = _single_signal("normal_content")

    assert signal["signal_type"] == "segment_normal_content"
    assert signal["source"] == "segment_classifier"
    assert signal["action_hint"] == "review_segment_normal_content"
    assert signal["priority"] == "low"


def test_no_unsafe_action_hints_are_created() -> None:
    result = adapt_segment_classification_report_to_signals(
        {
            "segments": [
                _segment("highlight"),
                _segment("hook_candidate"),
                _segment("protected_context"),
                _segment("dead_candidate"),
                _segment("censor_required_segment"),
                _segment("technical_warning"),
                _segment("transition"),
                _segment("filler"),
            ]
        }
    )

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

    for signal in result.signals:
        action_hint = str(signal.get("action_hint") or "").lower()
        for forbidden in forbidden_action_hints:
            assert forbidden not in action_hint


def test_empty_input_is_safe() -> None:
    result = adapt_segment_classification_report_to_signals({})

    assert result.status == "skipped_no_segment_classifications"
    assert result.signal_count == 0
    assert result.signals == []


def test_invalid_input_is_safe() -> None:
    result = adapt_segment_classification_report_to_signals(None)

    assert result.status == "skipped_no_segment_classifications"
    assert result.signal_count == 0
    assert isinstance(result.errors, list)


def test_required_signal_fields_exist() -> None:
    signal = _single_signal("highlight")

    required_fields = [
        "signal_id",
        "signal_type",
        "source",
        "start_seconds",
        "end_seconds",
        "center_seconds",
        "duration_seconds",
        "signal_score",
        "priority",
        "action_hint",
        "reason",
        "confidence",
        "metadata",
    ]

    for field in required_fields:
        assert field in signal


def test_signal_metadata_is_preserved() -> None:
    signal = _single_signal("protected_context")

    assert signal["metadata"]["source_segment_id"] == "segment_protected_context"
    assert signal["metadata"]["segment_type"] == "protected_context"
    assert signal["metadata"]["source_signal_ids"] == ["sig_1"]
    assert signal["metadata"]["job_id"] == "job_test"


def test_adapter_result_roundtrip() -> None:
    result = adapt_segment_classification_report_to_signals(
        {"segments": [_segment("highlight")]}
    )

    loaded = SegmentClassificationSignalAdapterResult.from_dict(result.to_dict())

    assert loaded.status == "ok"
    assert loaded.signal_count == 1
    assert loaded.highlight_signal_count == 1
    assert loaded.signals[0]["signal_type"] == "segment_highlight_candidate"


def test_signal_adapter_files_have_no_bom_and_end_with_newline() -> None:
    files = [
        ROOT / "core" / "segment_classification_signal_adapter.py",
        ROOT / "tests" / "test_segment_classification_signal_adapter_smoke.py",
    ]

    for path in files:
        content = path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert content.endswith(b"\n"), f"{path} does not end with newline"
