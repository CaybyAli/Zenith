from __future__ import annotations

from pathlib import Path

from core.sentence_boundary_signal_adapter import (
    SentenceBoundarySignalAdapterResult,
    adapt_sentence_boundary_report_to_signals,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_ACTION_HINTS = {
    "force_cut",
    "auto_remove",
    "hard_remove",
    "remove_now",
    "cut_sentence_now",
    "auto_cut",
    "auto_trim",
}


def _path(relative_path: str) -> Path:
    return PROJECT_ROOT / relative_path


def _boundary(boundary_type: str, **overrides):
    data = {
        "boundary_id": f"{boundary_type}_1",
        "start_seconds": 1.0,
        "end_seconds": 2.0,
        "center_seconds": 1.5,
        "text": "What happened?",
        "normalized_text": "what happened?",
        "boundary_type": boundary_type,
        "protection_level": "soft",
        "confidence": 0.8,
        "recommendation": "review",
        "warnings": [],
        "errors": [],
    }
    data.update(overrides)
    return data


def _zone(**overrides):
    data = {
        "zone_id": "zone_1",
        "start_seconds": 1.0,
        "end_seconds": 3.0,
        "duration_seconds": 2.0,
        "zone_type": "protect_question_context",
        "protection_level": "soft",
        "reason": "question_context_should_be_preserved",
        "confidence": 0.75,
        "source_boundary_ids": ["question_1"],
        "metadata": {"source_boundary_type": "question_boundary"},
        "warnings": [],
        "errors": [],
    }
    data.update(overrides)
    return data


def _first_signal(report):
    result = adapt_sentence_boundary_report_to_signals(report)
    assert result.signals
    return result.signals[0]


def test_safe_boundary_maps_to_sentence_safe_boundary() -> None:
    signal = _first_signal({"boundaries": [_boundary("safe_sentence_boundary")]})

    assert signal["signal_type"] == "sentence_safe_boundary"
    assert signal["source"] == "sentence_boundary"
    assert signal["action_hint"] == "boundary_safe_for_review"


def test_open_fragment_maps_to_sentence_boundary_protection() -> None:
    signal = _first_signal({"boundaries": [_boundary("open_sentence_fragment")]})

    assert signal["signal_type"] == "sentence_boundary_protection"
    assert signal["action_hint"] == "protect_sentence_from_cut"
    assert signal["priority"] == "high"


def test_question_maps_to_sentence_question_context_protection() -> None:
    signal = _first_signal({"boundaries": [_boundary("question_boundary")]})

    assert signal["signal_type"] == "sentence_question_context_protection"
    assert signal["action_hint"] == "protect_question_answer_context"


def test_answer_candidate_maps_to_sentence_answer_candidate() -> None:
    signal = _first_signal({"boundaries": [_boundary("answer_candidate")]})

    assert signal["signal_type"] == "sentence_answer_candidate"
    assert signal["action_hint"] == "review_answer_context"


def test_protection_zone_maps_to_sentence_protection_zone() -> None:
    signal = _first_signal({"protection_zones": [_zone()]})

    assert signal["signal_type"] == "sentence_protection_zone"
    assert signal["action_hint"] == "protect_transcript_zone"
    assert signal["metadata"]["source_zone_id"] == "zone_1"


def test_no_forbidden_action_hints_are_emitted() -> None:
    report = {
        "boundaries": [
            _boundary("safe_sentence_boundary"),
            _boundary("open_sentence_fragment"),
            _boundary("question_boundary"),
            _boundary("answer_candidate"),
        ],
        "protection_zones": [_zone()],
    }

    result = adapt_sentence_boundary_report_to_signals(report)

    assert result.signals
    assert not {
        str(signal.get("action_hint")) for signal in result.signals
    } & FORBIDDEN_ACTION_HINTS


def test_empty_report_is_safe() -> None:
    result = adapt_sentence_boundary_report_to_signals({})

    assert result.status == "skipped_no_sentence_boundaries"
    assert result.signal_count == 0
    assert result.errors == []


def test_invalid_entries_are_safe() -> None:
    result = adapt_sentence_boundary_report_to_signals(
        {"boundaries": ["bad", {"boundary_type": "unknown"}], "protection_zones": ["bad"]}
    )

    assert result.status == "skipped_no_sentence_boundaries"
    assert isinstance(result.warnings, list)
    assert isinstance(result.errors, list)


def test_required_signal_fields_are_present() -> None:
    signal = _first_signal({"boundaries": [_boundary("question_boundary")]})
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


def test_signal_metadata_contains_sentence_context() -> None:
    signal = _first_signal(
        {
            "boundaries": [
                _boundary(
                    "open_sentence_fragment",
                    text="This is a long open sentence fragment",
                    warnings=["sentence_ends_with_connector"],
                )
            ]
        }
    )

    metadata = signal["metadata"]
    assert metadata["original_boundary_type"] == "open_sentence_fragment"
    assert metadata["protection_level"] == "soft"
    assert metadata["text_preview"]
    assert metadata["source_boundary_id"] == "open_sentence_fragment_1"
    assert metadata["recommendation"] == "review"
    assert metadata["warnings"] == ["sentence_ends_with_connector"]
    assert metadata["errors"] == []


def test_adapter_result_roundtrip() -> None:
    original = adapt_sentence_boundary_report_to_signals(
        {"boundaries": [_boundary("safe_sentence_boundary")]}
    )

    restored = SentenceBoundarySignalAdapterResult.from_dict(original.to_dict())

    assert restored.status == original.status
    assert restored.signal_count == original.signal_count
    assert restored.safe_boundary_signal_count == 1
    assert restored.signals == original.signals


def test_sentence_boundary_signal_adapter_files_have_no_bom_and_newline() -> None:
    for relative_path in [
        "core/sentence_boundary_signal_adapter.py",
        "tests/test_sentence_boundary_signal_adapter_smoke.py",
    ]:
        content = _path(relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
