from __future__ import annotations

from pathlib import Path

from core.profanity_censor_signal_adapter import (
    ProfanityCensorSignalAdapterResult,
    adapt_profanity_censor_report_to_signals,
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


def _match(timing_source: str = "word_timestamp", **overrides) -> dict:
    data = {
        "match_id": f"m_{timing_source}",
        "start_seconds": 1.0,
        "end_seconds": 1.2,
        "center_seconds": 1.1,
        "duration_seconds": 0.2,
        "text": "SEVERE_TOKEN",
        "matched_text": "SEVERE_TOKEN",
        "normalized_match": "severe_token",
        "severity": "severe",
        "category": "severe_profanity",
        "censor_required": True,
        "censor_action": "censor_sfx_overlay_candidate",
        "replacement_sfx": "quack",
        "timing_source": timing_source,
        "confidence": 0.9,
        "warnings": [],
        "errors": [],
    }
    data.update(overrides)
    return data


def test_severe_match_maps_to_required_signal() -> None:
    result = adapt_profanity_censor_report_to_signals({"matches": [_match()]})

    assert result.censor_required_signal_count == 1
    assert any(
        signal["signal_type"] == "profanity_censor_sfx_required"
        for signal in result.signals
    )


def test_word_timestamp_maps_to_word_timed_signal() -> None:
    result = adapt_profanity_censor_report_to_signals({"matches": [_match()]})

    assert result.word_timed_signal_count == 1
    assert any(
        signal["signal_type"] == "profanity_censor_word_timed_overlay"
        for signal in result.signals
    )


def test_segment_fallback_maps_to_segment_fallback_signal() -> None:
    result = adapt_profanity_censor_report_to_signals(
        {"matches": [_match("segment_fallback")]}
    )

    assert result.segment_fallback_signal_count == 1
    assert any(
        signal["signal_type"] == "profanity_censor_segment_fallback_overlay"
        for signal in result.signals
    )


def test_mild_match_creates_no_censor_required_signal() -> None:
    mild = _match(
        severity="mild",
        censor_required=False,
        censor_action="none",
        replacement_sfx=None,
    )

    result = adapt_profanity_censor_report_to_signals({"matches": [mild]})

    assert result.status == "skipped_no_censor_required_matches"
    assert result.signal_count == 0


def test_replacement_sfx_is_preserved_in_metadata() -> None:
    result = adapt_profanity_censor_report_to_signals({"matches": [_match()]})

    assert result.signals[0]["metadata"]["replacement_sfx"] == "quack"


def test_no_forbidden_action_hints_are_emitted() -> None:
    result = adapt_profanity_censor_report_to_signals(
        {"matches": [_match(), _match("segment_fallback")]}
    )

    hints = {signal["action_hint"] for signal in result.signals}
    assert hints
    assert not hints.intersection(FORBIDDEN_ACTION_HINTS)


def test_empty_report_is_safe() -> None:
    result = adapt_profanity_censor_report_to_signals({})

    assert result.status == "skipped_no_censor_required_matches"
    assert result.signal_count == 0


def test_invalid_entries_are_safe() -> None:
    result = adapt_profanity_censor_report_to_signals(
        {"matches": [None, "bad", {"severity": "unknown"}]}
    )

    assert result.status == "skipped_no_censor_required_matches"
    assert result.signal_count == 0
    assert result.warnings


def test_signals_contain_required_fields() -> None:
    result = adapt_profanity_censor_report_to_signals({"matches": [_match()]})
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
    result = adapt_profanity_censor_report_to_signals({"matches": [_match()]})
    metadata = result.signals[0]["metadata"]

    assert metadata["severity"] == "severe"
    assert metadata["category"] == "severe_profanity"
    assert metadata["matched_text"] == "SEVERE_TOKEN"
    assert metadata["normalized_match"] == "severe_token"
    assert metadata["replacement_sfx"] == "quack"
    assert metadata["censor_required"] is True
    assert metadata["censor_action"] == "censor_sfx_overlay_candidate"
    assert metadata["timing_source"] == "word_timestamp"
    assert metadata["source_match_id"]


def test_adapter_result_roundtrip() -> None:
    result = adapt_profanity_censor_report_to_signals({"matches": [_match()]})

    restored = ProfanityCensorSignalAdapterResult.from_dict(result.to_dict())

    assert restored.to_dict() == result.to_dict()


def test_profanity_censor_signal_adapter_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in (
        "core/profanity_censor_signal_adapter.py",
        "tests/test_profanity_censor_signal_adapter_smoke.py",
    ):
        content = (PROJECT_ROOT / relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
