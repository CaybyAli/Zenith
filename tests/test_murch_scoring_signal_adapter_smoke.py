from __future__ import annotations

from pathlib import Path

from core.murch_scoring_signal_adapter import (
    STATUS_OK,
    STATUS_SKIPPED_NO_MURCH_SCORES,
    MurchScoringSignalAdapterResult,
    adapt_murch_scoring_report_to_signals,
)

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
    "apply_cut",
    "render_now",
}


PROJECT_ROOT = Path(__file__).resolve().parents[1]

NEW_FILES = [
    PROJECT_ROOT / "core" / "murch_scoring_signal_adapter.py",
    PROJECT_ROOT / "tests" / "test_murch_scoring_signal_adapter_smoke.py",
]


def _score(
    tier: str,
    segment_id: str = "segment_1",
    murch_score: float = 0.7,
    emotion_score: float = 0.4,
    story_score: float = 0.4,
    censor_required: bool = False,
) -> dict:
    return {
        "segment_id": segment_id,
        "start_seconds": 1.0,
        "end_seconds": 5.0,
        "center_seconds": 3.0,
        "duration_seconds": 4.0,
        "segment_type": "normal_content",
        "murch_score": murch_score,
        "murch_tier": tier,
        "emotion_score": emotion_score,
        "story_score": story_score,
        "rhythm_score": 0.5,
        "eye_trace_score": 0.5,
        "screen_direction_score": 0.5,
        "spatial_continuity_score": 0.5,
        "protection_score": 0.0,
        "risk_score": 0.0,
        "dead_content_risk_score": 0.0,
        "technical_risk_score": 0.0,
        "censor_required": censor_required,
        "is_censor_required": censor_required,
        "is_protected_context": tier == "protected",
        "recommendation": "review_murch_score_segment",
        "evidence": {"reason": "smoke"},
        "source_signal_ids": ["source_signal_1"],
        "warnings": [],
        "errors": [],
        "metadata": {"source": "test"},
    }


def _types(result) -> set[str]:
    return {signal["signal_type"] for signal in result.signals}


def _only_signal(result, signal_type: str) -> dict:
    matches = [
        signal for signal in result.signals
        if signal.get("signal_type") == signal_type
    ]
    assert len(matches) == 1
    return matches[0]


def test_high_maps_to_murch_high_score_segment() -> None:
    result = adapt_murch_scoring_report_to_signals(
        {"segment_scores": [_score("high", murch_score=0.9)]}
    )

    assert result.status == STATUS_OK
    assert "murch_high_score_segment" in _types(result)
    assert result.high_score_signal_count == 1

    signal = _only_signal(result, "murch_high_score_segment")
    assert signal["source"] == "murch_scoring"
    assert signal["action_hint"] == "review_high_murch_score_segment"
    assert signal["priority"] == "high"


def test_medium_maps_to_murch_medium_score_segment() -> None:
    result = adapt_murch_scoring_report_to_signals(
        {"segment_scores": [_score("medium", murch_score=0.55)]}
    )

    assert "murch_medium_score_segment" in _types(result)
    assert result.medium_score_signal_count == 1

    signal = _only_signal(result, "murch_medium_score_segment")
    assert signal["action_hint"] == "review_medium_murch_score_segment"
    assert signal["priority"] == "medium"


def test_low_maps_to_murch_low_score_segment_without_remove() -> None:
    result = adapt_murch_scoring_report_to_signals(
        {"segment_scores": [_score("low", murch_score=0.2)]}
    )

    assert "murch_low_score_segment" in _types(result)
    assert result.low_score_signal_count == 1

    signal = _only_signal(result, "murch_low_score_segment")
    assert signal["action_hint"] == "review_low_murch_score_segment"
    assert "remove" not in signal["action_hint"]
    assert "delete" not in signal["action_hint"]


def test_protected_maps_to_murch_protected_context() -> None:
    result = adapt_murch_scoring_report_to_signals(
        {"segment_scores": [_score("protected", murch_score=0.5)]}
    )

    assert "murch_protected_context" in _types(result)
    assert result.protected_context_signal_count == 1

    signal = _only_signal(result, "murch_protected_context")
    assert signal["action_hint"] == "protect_murch_context"
    assert signal["priority"] == "high"


def test_technical_warning_maps_to_murch_technical_warning() -> None:
    result = adapt_murch_scoring_report_to_signals(
        {"segment_scores": [_score("technical_warning", murch_score=0.4)]}
    )

    assert "murch_technical_warning" in _types(result)
    assert result.technical_warning_signal_count == 1

    signal = _only_signal(result, "murch_technical_warning")
    assert signal["action_hint"] == "review_murch_technical_warning"
    assert signal["priority"] == "high"


def test_censor_required_maps_to_murch_censor_required_context() -> None:
    result = adapt_murch_scoring_report_to_signals(
        {
            "segment_scores": [
                _score(
                    "medium",
                    murch_score=0.6,
                    censor_required=True,
                )
            ]
        }
    )

    assert "murch_censor_required_context" in _types(result)
    assert result.censor_required_signal_count == 1

    signal = _only_signal(result, "murch_censor_required_context")
    assert signal["action_hint"] == "preserve_murch_segment_with_censor_sfx_review"
    assert signal["priority"] == "high"


def test_emotion_high_maps_to_murch_emotion_high() -> None:
    result = adapt_murch_scoring_report_to_signals(
        {
            "segment_scores": [
                _score(
                    "high",
                    murch_score=0.9,
                    emotion_score=0.85,
                    story_score=0.4,
                )
            ]
        }
    )

    assert "murch_emotion_high" in _types(result)
    assert result.emotion_high_signal_count == 1

    signal = _only_signal(result, "murch_emotion_high")
    assert signal["action_hint"] == "review_high_emotion_segment"
    assert signal["priority"] == "high"


def test_story_high_maps_to_murch_story_high() -> None:
    result = adapt_murch_scoring_report_to_signals(
        {
            "segment_scores": [
                _score(
                    "high",
                    murch_score=0.9,
                    emotion_score=0.4,
                    story_score=0.85,
                )
            ]
        }
    )

    assert "murch_story_high" in _types(result)
    assert result.story_high_signal_count == 1

    signal = _only_signal(result, "murch_story_high")
    assert signal["action_hint"] == "review_high_story_segment"
    assert signal["priority"] == "high"


def test_no_forbidden_action_hints_are_created() -> None:
    result = adapt_murch_scoring_report_to_signals(
        {
            "segment_scores": [
                _score("high", murch_score=0.9, emotion_score=0.85, story_score=0.85),
                _score("medium", segment_id="segment_2", murch_score=0.5),
                _score("low", segment_id="segment_3", murch_score=0.2),
                _score("protected", segment_id="segment_4", murch_score=0.5),
                _score("technical_warning", segment_id="segment_5", murch_score=0.4),
                _score("medium", segment_id="segment_6", censor_required=True),
            ]
        }
    )

    action_hints = {
        signal.get("action_hint", "")
        for signal in result.signals
    }

    assert action_hints.isdisjoint(FORBIDDEN_ACTION_HINTS)


def test_empty_source_is_safe() -> None:
    result = adapt_murch_scoring_report_to_signals({"segment_scores": []})

    assert result.status == STATUS_SKIPPED_NO_MURCH_SCORES
    assert result.signals == []
    assert result.signal_count == 0


def test_invalid_source_is_safe() -> None:
    result = adapt_murch_scoring_report_to_signals(None)

    assert result.status == STATUS_SKIPPED_NO_MURCH_SCORES
    assert result.signals == []
    assert result.signal_count == 0


def test_signals_have_required_fields() -> None:
    result = adapt_murch_scoring_report_to_signals(
        {"segment_scores": [_score("high", murch_score=0.9)]}
    )

    signal = _only_signal(result, "murch_high_score_segment")

    for key in [
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
    ]:
        assert key in signal


def test_metadata_is_preserved_and_extended() -> None:
    result = adapt_murch_scoring_report_to_signals(
        {"segment_scores": [_score("high", murch_score=0.9)]},
        metadata={"phase": "2B-26-D"},
    )

    signal = _only_signal(result, "murch_high_score_segment")

    assert signal["metadata"]["source_segment_id"] == "segment_1"
    assert signal["metadata"]["murch_tier"] == "high"
    assert signal["metadata"]["phase"] == "2B-26-D"


def test_result_roundtrip() -> None:
    result = adapt_murch_scoring_report_to_signals(
        {"segment_scores": [_score("high", murch_score=0.9)]}
    )

    loaded = MurchScoringSignalAdapterResult.from_dict(result.to_dict())

    assert loaded.to_dict() == result.to_dict()


def test_new_files_have_no_bom_and_end_with_newline() -> None:
    for path in NEW_FILES:
        data = path.read_bytes()

        assert data.startswith(b"\xef\xbb\xbf") is False
        assert data.endswith(b"\n")
