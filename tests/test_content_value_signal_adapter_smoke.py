from __future__ import annotations

from pathlib import Path

from core.content_value_signal_adapter import (
    ContentValueSignalAdapterResult,
    adapt_content_value_report_to_signals,
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
    "auto_hook",
    "auto_mute",
    "censor_now",
    "delete_segment",
    "drop_segment",
    "timeline_apply_now",
}


def _score(value_tier: str, final_score: float = 0.7, **overrides) -> dict:
    data = {
        "segment_id": f"segment_{value_tier}",
        "start_seconds": 1.0,
        "end_seconds": 2.0,
        "center_seconds": 1.5,
        "duration_seconds": 1.0,
        "text": "test",
        "content_value_score": final_score,
        "final_score": final_score,
        "protection_score": 0.0,
        "dead_content_penalty_score": 0.0,
        "technical_penalty_score": 0.0,
        "value_tier": value_tier,
        "review_label": f"review_{value_tier}",
        "is_hook_candidate": False,
        "is_protected_context": value_tier == "protected",
        "evidence": {"source": "test"},
        "recommendation": f"review_{value_tier}",
        "warnings": [],
        "errors": [],
    }
    data.update(overrides)
    return data


def _adapt_one(value_tier: str, final_score: float = 0.7, **overrides):
    return adapt_content_value_report_to_signals(
        {"status": "ok", "segment_scores": [_score(value_tier, final_score, **overrides)]}
    )


def test_high_value_maps_to_signal() -> None:
    result = _adapt_one("high", 0.82)

    assert result.high_value_signal_count == 1
    assert result.signals[0]["signal_type"] == "content_value_high_segment"
    assert result.signals[0]["action_hint"] == "review_high_value_segment"


def test_medium_value_maps_to_signal() -> None:
    result = _adapt_one("medium", 0.5)

    assert result.mid_value_signal_count == 1
    assert result.signals[0]["signal_type"] == "content_value_mid_segment"


def test_low_value_maps_to_signal() -> None:
    result = _adapt_one("low", 0.2)

    assert result.low_value_signal_count == 1
    assert result.signals[0]["signal_type"] == "content_value_low_segment"


def test_protected_context_maps_to_signal() -> None:
    result = _adapt_one("protected", 0.35, protection_score=0.9)

    assert result.protected_context_signal_count == 1
    assert result.signals[0]["signal_type"] == "content_value_protected_context"
    assert result.signals[0]["action_hint"] == "protect_context_from_blind_cut"


def test_hook_candidate_maps_to_signal() -> None:
    result = _adapt_one("high", 0.85, is_hook_candidate=True)

    assert result.hook_candidate_signal_count == 1
    assert any(
        signal["signal_type"] == "content_value_hook_candidate"
        for signal in result.signals
    )


def test_technical_warning_maps_to_signal() -> None:
    result = _adapt_one("technical_warning", 0.2, technical_penalty_score=0.9)

    assert result.technical_warning_signal_count == 1
    assert result.signals[0]["signal_type"] == "content_value_technical_warning"


def test_no_forbidden_action_hints_are_emitted() -> None:
    result = adapt_content_value_report_to_signals(
        {
            "segment_scores": [
                _score("high", 0.9, is_hook_candidate=True),
                _score("low", 0.2),
                _score("protected", 0.3, protection_score=0.9),
                _score("technical_warning", 0.2, technical_penalty_score=0.9),
            ]
        }
    )

    assert result.signals
    assert not {
        signal["action_hint"] for signal in result.signals
    }.intersection(FORBIDDEN_ACTION_HINTS)


def test_empty_report_is_safe() -> None:
    result = adapt_content_value_report_to_signals({})

    assert result.status == "skipped_no_content_value_segments"
    assert result.signal_count == 0


def test_invalid_entries_are_safe() -> None:
    result = adapt_content_value_report_to_signals(
        {"segment_scores": [None, "bad", {"value_tier": "unknown"}]}
    )

    assert result.status == "skipped_no_content_value_segments"
    assert result.signal_count == 0
    assert result.warnings


def test_signal_contains_required_fields() -> None:
    result = _adapt_one("high", 0.8)
    signal = result.signals[0]
    required = {
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

    assert not (required - set(signal))


def test_signal_metadata_contains_required_values() -> None:
    result = _adapt_one("protected", 0.35, protection_score=0.9)
    metadata = result.signals[0]["metadata"]

    assert metadata["value_tier"] == "protected"
    assert metadata["content_value_score"] == 0.35
    assert metadata["final_score"] == 0.35
    assert metadata["protection_score"] == 0.9
    assert metadata["is_protected_context"] is True
    assert metadata["evidence"] == {"source": "test"}
    assert metadata["source_segment_id"]


def test_adapter_result_roundtrip() -> None:
    result = _adapt_one("high", 0.8)

    restored = ContentValueSignalAdapterResult.from_dict(result.to_dict())

    assert restored.to_dict() == result.to_dict()


def test_content_value_signal_adapter_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in (
        "core/content_value_signal_adapter.py",
        "tests/test_content_value_signal_adapter_smoke.py",
    ):
        content = (PROJECT_ROOT / relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
