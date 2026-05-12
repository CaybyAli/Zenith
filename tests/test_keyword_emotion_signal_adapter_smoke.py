from __future__ import annotations

from pathlib import Path

from core.keyword_emotion_signal_adapter import (
    KeywordEmotionSignalAdapterResult,
    adapt_keyword_emotion_report_to_signals,
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
}


def _path(relative_path: str) -> Path:
    return PROJECT_ROOT / relative_path


def _segment(**overrides):
    data = {
        "segment_id": "seg_1",
        "start_seconds": 1.0,
        "end_seconds": 3.0,
        "duration_seconds": 2.0,
        "text": "insane no way haha why",
        "categories": {},
        "dominant_category": "neutral",
        "emotion_score": 0.0,
        "hype_score": 0.0,
        "frustration_score": 0.0,
        "shock_score": 0.0,
        "laugh_score": 0.0,
        "question_score": 0.0,
        "overall_keyword_score": 0.0,
        "match_count": 1,
        "recommendation": "review",
        "metadata": {},
        "warnings": [],
        "errors": [],
    }
    data.update(overrides)
    return data


def _first_signal(report):
    result = adapt_keyword_emotion_report_to_signals(report)
    assert result.signals
    return result.signals[0]


def test_hype_segment_maps_to_keyword_hype_segment() -> None:
    signal = _first_signal(
        {"segment_scores": [_segment(categories={"hype": 0.8}, dominant_category="hype")]}
    )

    assert signal["signal_type"] == "keyword_hype_segment"
    assert signal["source"] == "keyword_emotion"
    assert signal["action_hint"] == "review_hype_keyword_moment"


def test_shock_segment_maps_to_keyword_shock_segment() -> None:
    signal = _first_signal(
        {"segment_scores": [_segment(categories={"shock": 0.85}, dominant_category="shock")]}
    )

    assert signal["signal_type"] == "keyword_shock_segment"
    assert signal["action_hint"] == "review_shock_keyword_moment"


def test_laugh_segment_maps_to_keyword_laugh_segment() -> None:
    signal = _first_signal(
        {"segment_scores": [_segment(categories={"laugh": 0.75}, dominant_category="laugh")]}
    )

    assert signal["signal_type"] == "keyword_laugh_segment"
    assert signal["action_hint"] == "review_comedy_keyword_moment"


def test_frustration_segment_maps_to_keyword_frustration_segment() -> None:
    signal = _first_signal(
        {
            "segment_scores": [
                _segment(categories={"frustration": 0.7}, dominant_category="frustration")
            ]
        }
    )

    assert signal["signal_type"] == "keyword_frustration_segment"
    assert signal["action_hint"] == "review_frustration_keyword_moment"
    assert signal["priority"] == "medium"


def test_question_segment_maps_to_keyword_question_segment() -> None:
    signal = _first_signal(
        {"segment_scores": [_segment(categories={"question": 0.65}, dominant_category="question")]}
    )

    assert signal["signal_type"] == "keyword_question_segment"
    assert signal["action_hint"] == "review_question_keyword_context"


def test_high_score_maps_to_keyword_high_value_segment() -> None:
    result = adapt_keyword_emotion_report_to_signals(
        {
            "segment_scores": [
                _segment(
                    categories={"hype": 0.8},
                    dominant_category="hype",
                    overall_keyword_score=0.72,
                )
            ]
        }
    )

    assert any(signal["signal_type"] == "keyword_high_value_segment" for signal in result.signals)
    assert result.high_value_signal_count == 1


def test_no_forbidden_action_hints_are_emitted() -> None:
    report = {
        "segment_scores": [
            _segment(
                categories={
                    "hype": 0.8,
                    "shock": 0.8,
                    "laugh": 0.8,
                    "frustration": 0.7,
                    "question": 0.6,
                },
                overall_keyword_score=0.8,
            )
        ]
    }

    result = adapt_keyword_emotion_report_to_signals(report)

    assert result.signals
    assert not {
        str(signal.get("action_hint")) for signal in result.signals
    } & FORBIDDEN_ACTION_HINTS


def test_empty_report_is_safe() -> None:
    result = adapt_keyword_emotion_report_to_signals({})

    assert result.status == "skipped_no_keyword_emotion_segments"
    assert result.signal_count == 0
    assert result.errors == []


def test_invalid_entries_are_safe() -> None:
    result = adapt_keyword_emotion_report_to_signals(
        {"segment_scores": ["bad", {"categories": {}}]}
    )

    assert result.status == "skipped_no_keyword_emotion_segments"
    assert isinstance(result.warnings, list)
    assert isinstance(result.errors, list)


def test_required_signal_fields_are_present() -> None:
    signal = _first_signal(
        {"segment_scores": [_segment(categories={"hype": 0.8}, dominant_category="hype")]}
    )
    required_fields = {
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
    }

    assert required_fields.issubset(signal.keys())


def test_signal_metadata_contains_keyword_context() -> None:
    signal = _first_signal(
        {
            "segment_scores": [
                _segment(
                    segment_id="seg_meta",
                    categories={"hype": 0.8},
                    dominant_category="hype",
                    text="That was insane",
                    match_count=2,
                    recommendation="review_high_value_keyword_segment",
                    warnings=["w"],
                )
            ]
        }
    )

    metadata = signal["metadata"]
    assert metadata["dominant_category"] == "hype"
    assert metadata["categories"] == {"hype": 0.8}
    assert metadata["text_preview"] == "That was insane"
    assert metadata["match_count"] == 2
    assert metadata["source_segment_id"] == "seg_meta"
    assert metadata["warnings"] == ["w"]


def test_adapter_result_roundtrip() -> None:
    original = adapt_keyword_emotion_report_to_signals(
        {"segment_scores": [_segment(categories={"hype": 0.8}, dominant_category="hype")]}
    )

    restored = KeywordEmotionSignalAdapterResult.from_dict(original.to_dict())

    assert restored.status == original.status
    assert restored.signal_count == original.signal_count
    assert restored.hype_signal_count == 1
    assert restored.signals == original.signals


def test_keyword_emotion_signal_adapter_files_have_no_bom_and_newline() -> None:
    for relative_path in [
        "core/keyword_emotion_signal_adapter.py",
        "tests/test_keyword_emotion_signal_adapter_smoke.py",
    ]:
        content = _path(relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
