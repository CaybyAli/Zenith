from __future__ import annotations

from pathlib import Path

from core.dead_content_signal_adapter import (
    DeadContentSignalAdapterResult,
    adapt_dead_content_report_to_signals,
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
    "auto_mute",
    "censor_now",
    "delete_segment",
    "drop_segment",
}


def _candidate(candidate_type: str, score: float = 0.7) -> dict:
    return {
        "candidate_id": f"candidate_{candidate_type}",
        "start_seconds": 1.0,
        "end_seconds": 2.0,
        "center_seconds": 1.5,
        "duration_seconds": 1.0,
        "text": "test",
        "candidate_type": candidate_type,
        "dead_content_score": score,
        "confidence": score,
        "protected_by_context": candidate_type == "protected_context_candidate",
        "protection_reasons": ["context"]
        if candidate_type == "protected_context_candidate"
        else [],
        "evidence": {"source": "test"},
        "recommendation": "review_protected_context"
        if candidate_type == "protected_context_candidate"
        else "review_dead_content_candidate",
        "metadata": {"content_value_score": 0.1},
        "warnings": [],
        "errors": [],
    }


def _adapt_one(candidate_type: str, score: float = 0.7):
    return adapt_dead_content_report_to_signals(
        {"status": "ok", "candidates": [_candidate(candidate_type, score)]}
    )


def test_dead_air_candidate_maps_to_signal() -> None:
    result = _adapt_one("dead_air_candidate")

    assert result.dead_air_signal_count == 1
    assert result.signals[0]["signal_type"] == "dead_content_dead_air_candidate"
    assert result.signals[0]["action_hint"] == "review_dead_air_candidate"


def test_low_value_candidate_maps_to_signal() -> None:
    result = _adapt_one("low_value_content_candidate")

    assert result.low_value_signal_count == 1
    assert result.signals[0]["signal_type"] == "dead_content_low_value_candidate"


def test_filler_pause_candidate_maps_to_signal() -> None:
    result = _adapt_one("filler_pause_candidate")

    assert result.filler_pause_signal_count == 1
    assert result.signals[0]["signal_type"] == "dead_content_filler_pause_candidate"


def test_loading_or_menu_candidate_maps_to_signal() -> None:
    result = _adapt_one("loading_or_menu_candidate")

    assert result.loading_or_menu_signal_count == 1
    assert result.signals[0]["signal_type"] == "dead_content_loading_or_menu_candidate"


def test_private_or_meta_candidate_maps_to_signal() -> None:
    result = _adapt_one("private_or_meta_review_candidate")

    assert result.private_or_meta_signal_count == 1
    assert (
        result.signals[0]["signal_type"]
        == "dead_content_private_or_meta_review_candidate"
    )
    assert result.signals[0]["action_hint"] == "review_private_or_meta_candidate"


def test_protected_context_candidate_maps_to_signal() -> None:
    result = _adapt_one("protected_context_candidate")

    assert result.protected_context_signal_count == 1
    assert result.signals[0]["signal_type"] == "dead_content_protected_context_candidate"
    assert result.signals[0]["action_hint"] == "protect_context_from_dead_content_cut"


def test_high_score_candidate_adds_generic_high_score_signal() -> None:
    result = _adapt_one("low_value_content_candidate", score=0.91)

    assert result.high_score_signal_count == 1
    assert any(
        signal["signal_type"] == "dead_content_high_score_candidate"
        for signal in result.signals
    )


def test_no_forbidden_action_hints_are_emitted() -> None:
    result = adapt_dead_content_report_to_signals(
        {
            "candidates": [
                _candidate("dead_air_candidate", 0.9),
                _candidate("protected_context_candidate", 0.9),
                _candidate("private_or_meta_review_candidate", 0.9),
            ]
        }
    )

    assert result.signals
    assert not {
        signal["action_hint"] for signal in result.signals
    }.intersection(FORBIDDEN_ACTION_HINTS)


def test_empty_report_is_safe() -> None:
    result = adapt_dead_content_report_to_signals({})

    assert result.status == "skipped_no_dead_content_candidates"
    assert result.signal_count == 0


def test_invalid_entries_are_safe() -> None:
    result = adapt_dead_content_report_to_signals(
        {"candidates": [None, "bad", {"candidate_type": "unknown"}]}
    )

    assert result.status == "skipped_no_dead_content_candidates"
    assert result.signal_count == 0
    assert result.warnings


def test_signal_contains_required_fields() -> None:
    result = _adapt_one("dead_air_candidate")
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
    result = _adapt_one("protected_context_candidate")
    metadata = result.signals[0]["metadata"]

    assert metadata["candidate_type"] == "protected_context_candidate"
    assert metadata["dead_content_score"] == 0.7
    assert metadata["content_value_score"] == 0.1
    assert metadata["protected_by_context"] is True
    assert metadata["protection_reasons"] == ["context"]
    assert metadata["evidence"] == {"source": "test"}
    assert metadata["source_candidate_id"]


def test_adapter_result_roundtrip() -> None:
    result = _adapt_one("dead_air_candidate")

    restored = DeadContentSignalAdapterResult.from_dict(result.to_dict())

    assert restored.to_dict() == result.to_dict()


def test_dead_content_signal_adapter_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in (
        "core/dead_content_signal_adapter.py",
        "tests/test_dead_content_signal_adapter_smoke.py",
    ):
        content = (PROJECT_ROOT / relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
