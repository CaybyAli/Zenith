from __future__ import annotations

from pathlib import Path

from core.interaction_classification_signal_adapter import (
    InteractionClassificationSignalAdapterResult,
    adapt_interaction_classification_report_to_signals,
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
}


def _path(relative_path: str) -> Path:
    return PROJECT_ROOT / relative_path


def _segment(interaction_type: str, context_needed: bool = False) -> dict:
    return {
        "segment_id": f"seg_{interaction_type}",
        "start_seconds": 1.0,
        "end_seconds": 2.0,
        "duration_seconds": 1.0,
        "text": f"text for {interaction_type}",
        "interaction_type": interaction_type,
        "confidence": 0.8,
        "context_needed": context_needed,
        "recommendation": "review",
        "metadata": {"source_segment_index": 0},
        "warnings": [],
        "errors": [],
    }


def _report(*segments: dict) -> dict:
    return {"status": "ok", "segment_classifications": list(segments)}


def _types(result) -> set[str]:
    return {signal["signal_type"] for signal in result.signals}


def test_monologue_maps_to_signal() -> None:
    result = adapt_interaction_classification_report_to_signals(_report(_segment("monologue")))

    assert "interaction_monologue_segment" in _types(result)


def test_interaction_maps_to_signal() -> None:
    result = adapt_interaction_classification_report_to_signals(_report(_segment("interaction")))

    assert "interaction_dialogue_segment" in _types(result)


def test_question_answer_maps_to_signal() -> None:
    result = adapt_interaction_classification_report_to_signals(
        _report(_segment("question_answer"))
    )

    assert "interaction_question_answer_segment" in _types(result)


def test_chat_reaction_maps_to_signal() -> None:
    result = adapt_interaction_classification_report_to_signals(
        _report(_segment("chat_reaction"))
    )

    assert "interaction_chat_reaction_segment" in _types(result)


def test_callout_maps_to_signal() -> None:
    result = adapt_interaction_classification_report_to_signals(_report(_segment("callout")))

    assert "interaction_callout_segment" in _types(result)


def test_private_or_meta_candidate_maps_to_signal() -> None:
    result = adapt_interaction_classification_report_to_signals(
        _report(_segment("private_or_meta_candidate"))
    )

    assert "interaction_private_or_meta_candidate" in _types(result)


def test_context_needed_maps_to_signal() -> None:
    result = adapt_interaction_classification_report_to_signals(
        _report(_segment("interaction", context_needed=True))
    )

    assert "interaction_context_needed_segment" in _types(result)


def test_no_forbidden_action_hints() -> None:
    result = adapt_interaction_classification_report_to_signals(
        _report(
            _segment("monologue"),
            _segment("interaction", context_needed=True),
            _segment("private_or_meta_candidate"),
        )
    )
    hints = {signal["action_hint"] for signal in result.signals}

    assert not hints & FORBIDDEN_ACTION_HINTS


def test_empty_report_safe() -> None:
    result = adapt_interaction_classification_report_to_signals({})

    assert result.status == "skipped_no_interaction_segments"
    assert result.signal_count == 0


def test_invalid_entries_safe() -> None:
    result = adapt_interaction_classification_report_to_signals(
        {"segment_classifications": [None, {"interaction_type": "unknown"}]}
    )

    assert result.status == "skipped_no_interaction_segments"
    assert result.signal_count == 0


def test_required_signal_fields() -> None:
    result = adapt_interaction_classification_report_to_signals(_report(_segment("callout")))
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

    assert required.issubset(signal)


def test_signal_metadata() -> None:
    result = adapt_interaction_classification_report_to_signals(_report(_segment("chat_reaction")))
    metadata = result.signals[0]["metadata"]

    assert metadata["interaction_type"] == "chat_reaction"
    assert metadata["text_preview"]
    assert metadata["source_segment_id"] == "seg_chat_reaction"


def test_adapter_result_roundtrip() -> None:
    result = adapt_interaction_classification_report_to_signals(_report(_segment("monologue")))
    restored = InteractionClassificationSignalAdapterResult.from_dict(result.to_dict())

    assert restored.to_dict() == result.to_dict()


def test_interaction_signal_adapter_file_hygiene() -> None:
    for relative_path in [
        "core/interaction_classification_signal_adapter.py",
        "tests/test_interaction_classification_signal_adapter_smoke.py",
    ]:
        content = _path(relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
