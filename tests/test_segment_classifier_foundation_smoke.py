from pathlib import Path

from core.segment_classifier import classify_segments_from_unified_signals
from models.segment_classification import (
    STATUS_SKIPPED_NO_UNIFIED_SIGNALS,
    SegmentClassification,
    SegmentClassificationResult,
)


ROOT = Path(__file__).resolve().parents[1]


def _signal(signal_type: str, start: float = 10.0, end: float = 12.0, score: float = 0.9) -> dict:
    return {
        "signal_id": f"sig_{signal_type}",
        "signal_type": signal_type,
        "source": "test",
        "start_seconds": start,
        "end_seconds": end,
        "score": score,
        "confidence": score,
        "metadata": {"test": True},
    }


def _single_type(signal_type: str) -> str:
    result = classify_segments_from_unified_signals([_signal(signal_type)])
    assert result.status == "ok"
    assert result.segment_count == 1
    return result.segments[0].segment_type


def test_segment_classification_roundtrip() -> None:
    segment = SegmentClassification(
        segment_id="segment_1",
        start_seconds=1.0,
        end_seconds=5.0,
        center_seconds=3.0,
        duration_seconds=4.0,
        segment_type="highlight",
        confidence=0.9,
        segment_score=0.8,
        content_value_score=0.8,
        source_signal_ids=["sig_1"],
        evidence={"reason": "high_value"},
        metadata={"source": "test"},
    )

    loaded = SegmentClassification.from_dict(segment.to_dict())

    assert loaded.segment_id == "segment_1"
    assert loaded.segment_type == "highlight"
    assert loaded.source_signal_ids == ["sig_1"]
    assert loaded.evidence["reason"] == "high_value"


def test_segment_classification_result_roundtrip() -> None:
    segment = SegmentClassification(segment_id="segment_1", segment_type="highlight")
    result = SegmentClassificationResult(
        status="ok",
        segments=[segment],
        segment_count=1,
        highlight_count=1,
        recommendation="review_segment_classification",
    )

    loaded = SegmentClassificationResult.from_dict(result.to_dict())

    assert loaded.status == "ok"
    assert loaded.segment_count == 1
    assert loaded.highlight_count == 1
    assert loaded.segments[0].segment_type == "highlight"


def test_no_signals_skips_safely() -> None:
    result = classify_segments_from_unified_signals([])

    assert result.status == STATUS_SKIPPED_NO_UNIFIED_SIGNALS
    assert result.segment_count == 0
    assert result.recommendation == "segment_classifier_skipped_no_unified_signals"


def test_content_value_high_segment_becomes_highlight() -> None:
    assert _single_type("content_value_high_segment") == "highlight"


def test_content_value_hook_candidate_becomes_hook_candidate() -> None:
    assert _single_type("content_value_hook_candidate") == "hook_candidate"


def test_sentence_protection_becomes_protected_context() -> None:
    assert _single_type("sentence_boundary_protection") == "protected_context"


def test_dead_content_becomes_dead_candidate() -> None:
    assert _single_type("dead_content_dead_air_candidate") == "dead_candidate"


def test_profanity_censor_becomes_censor_required_segment() -> None:
    assert _single_type("profanity_censor_sfx_required") == "censor_required_segment"


def test_technical_warning_becomes_technical_warning() -> None:
    assert _single_type("stutter_segment_candidate") == "technical_warning"


def test_scene_change_becomes_transition() -> None:
    assert _single_type("scene_hard_cut_point") == "transition"


def test_filler_becomes_filler() -> None:
    assert _single_type("filler_pause_candidate") == "filler"


def test_mixed_high_and_protected_keeps_protection_flag() -> None:
    result = classify_segments_from_unified_signals(
        [
            _signal("content_value_high_segment", start=20.0, end=22.0),
            _signal("sentence_question_context_protection", start=20.5, end=22.5),
        ]
    )

    assert result.status == "ok"
    assert result.segment_count == 1

    segment = result.segments[0]

    assert segment.segment_type in {"protected_context", "highlight"}
    assert segment.is_protected_context is True
    assert segment.protection_score > 0.0
    assert segment.content_value_score > 0.0


def test_no_automatic_cut_or_remove_action() -> None:
    result = classify_segments_from_unified_signals(
        [
            _signal("dead_content_dead_air_candidate"),
            _signal("profanity_censor_sfx_required", start=30.0, end=31.0),
        ]
    )

    forbidden_parts = [
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

    for segment in result.segments:
        recommendation = segment.recommendation.lower()
        for forbidden in forbidden_parts:
            assert forbidden not in recommendation


def test_new_foundation_files_have_no_bom_and_end_with_newline() -> None:
    files = [
        ROOT / "models" / "segment_classification.py",
        ROOT / "core" / "segment_classifier.py",
        ROOT / "tests" / "test_segment_classifier_foundation_smoke.py",
    ]

    for path in files:
        content = path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert content.endswith(b"\n"), f"{path} does not end with newline"
