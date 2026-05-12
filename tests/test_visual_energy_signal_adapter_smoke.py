from __future__ import annotations

from pathlib import Path

from core.visual_energy_signal_adapter import (
    VisualEnergySignalAdapterResult,
    adapt_visual_energy_report_to_signals,
    adapt_visual_energy_segments_to_signals,
    build_visual_energy_signal,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _segment(
    classification: str,
    start_seconds: float = 1.0,
    end_seconds: float = 2.0,
    avg_visual_energy_score: float = 0.80,
    max_visual_energy_score: float = 0.90,
    min_visual_energy_score: float = 0.70,
    recommendation: str = "review",
) -> dict:
    return {
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "duration_seconds": end_seconds - start_seconds,
        "avg_visual_energy_score": avg_visual_energy_score,
        "max_visual_energy_score": max_visual_energy_score,
        "min_visual_energy_score": min_visual_energy_score,
        "classification": classification,
        "recommendation": recommendation,
        "warnings": [],
        "errors": [],
    }


def _single_signal(classification: str) -> dict:
    result = adapt_visual_energy_segments_to_signals([_segment(classification)])

    assert result.status == "ok"
    assert result.signal_count == 1
    return result.signals[0]


def test_peak_visual_energy_maps_to_peak_signal() -> None:
    signal = _single_signal("peak_visual_energy")

    assert signal["signal_type"] == "visual_peak_energy_segment"
    assert signal["source"] == "visual_energy"
    assert signal["action_hint"] == "review_visual_highlight_candidate"
    assert signal["priority"] == "high"
    assert signal["reason"] == "peak_visual_energy_detected"


def test_high_visual_energy_maps_to_high_signal() -> None:
    signal = _single_signal("high_visual_energy")

    assert signal["signal_type"] == "visual_high_energy_segment"
    assert signal["source"] == "visual_energy"
    assert signal["action_hint"] == "review_visual_engagement_candidate"
    assert signal["priority"] == "high"
    assert signal["reason"] == "high_visual_energy_detected"


def test_low_visual_energy_maps_to_low_signal() -> None:
    signal = _single_signal("low_visual_energy")

    assert signal["signal_type"] == "visual_low_energy_segment"
    assert signal["source"] == "visual_energy"
    assert signal["action_hint"] == "review_possible_trim_low_visual_energy"
    assert signal["priority"] == "medium"
    assert signal["reason"] == "low_visual_energy_detected"


def test_technical_warning_maps_to_warning_signal() -> None:
    signal = _single_signal("technical_warning")

    assert signal["signal_type"] == "visual_technical_warning_segment"
    assert signal["source"] == "visual_energy"
    assert signal["action_hint"] == "review_visual_technical_warning"
    assert signal["priority"] == "high"
    assert signal["reason"] == "visual_technical_warning_detected"


def test_visual_energy_signals_do_not_auto_remove_or_auto_highlight() -> None:
    result = adapt_visual_energy_segments_to_signals(
        [
            _segment("peak_visual_energy"),
            _segment("high_visual_energy", 3.0, 4.0),
            _segment("low_visual_energy", 5.0, 6.0),
            _segment("technical_warning", 7.0, 8.0),
        ]
    )

    forbidden = {
        "remove_now",
        "hard_remove",
        "auto_remove",
        "auto_highlight",
        "force_cut",
    }

    for signal in result.signals:
        assert signal["action_hint"] not in forbidden
        assert signal["metadata"]["no_cut_decision"] is True
        assert signal["metadata"]["no_auto_remove"] is True
        assert signal["metadata"]["no_auto_highlight"] is True


def test_empty_report_is_safe() -> None:
    result = adapt_visual_energy_report_to_signals({})

    assert result.status == "skipped_no_visual_energy_segments"
    assert result.signal_count == 0
    assert result.warnings
    assert result.errors == []


def test_invalid_entries_are_safe() -> None:
    result = adapt_visual_energy_segments_to_signals(
        [None, "bad", _segment("unknown"), _segment("high_visual_energy")]
    )

    assert result.status == "completed_with_warnings"
    assert result.signal_count == 1
    assert result.high_signal_count == 1
    assert result.warnings


def test_required_signal_fields_are_present() -> None:
    signal = build_visual_energy_signal(_segment("technical_warning"), source_index=7)

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

    for field_name in required_fields:
        assert field_name in signal


def test_signal_metadata_contains_visual_energy_context() -> None:
    segment = _segment(
        "peak_visual_energy",
        avg_visual_energy_score=0.91,
        max_visual_energy_score=0.97,
        min_visual_energy_score=0.86,
        recommendation="review_visual_highlight_candidate",
    )

    signal = build_visual_energy_signal(segment, source_index=3)
    metadata = signal["metadata"]

    assert metadata["classification"] == "peak_visual_energy"
    assert metadata["avg_visual_energy_score"] == 0.91
    assert metadata["max_visual_energy_score"] == 0.97
    assert metadata["min_visual_energy_score"] == 0.86
    assert metadata["recommendation"] == "review_visual_highlight_candidate"
    assert metadata["source_index"] == 3
    assert metadata["warnings"] == []
    assert metadata["errors"] == []
    assert metadata["no_cut_decision"] is True
    assert metadata["no_auto_remove"] is True
    assert metadata["no_auto_highlight"] is True


def test_visual_energy_signal_adapter_result_roundtrip() -> None:
    result = adapt_visual_energy_segments_to_signals(
        [_segment("peak_visual_energy"), _segment("low_visual_energy", 3.0, 4.0)]
    )

    restored = VisualEnergySignalAdapterResult.from_dict(result.to_dict())

    assert restored.to_dict() == result.to_dict()


def test_report_extraction_from_visual_energy_report_is_supported() -> None:
    result = adapt_visual_energy_report_to_signals(
        {
            "visual_energy_segments": [
                _segment("high_visual_energy"),
                _segment("technical_warning", 3.0, 4.0),
            ]
        }
    )

    assert result.status == "ok"
    assert result.signal_count == 2
    assert result.high_signal_count == 1
    assert result.technical_warning_signal_count == 1


def test_report_extraction_from_visual_energy_result_is_supported() -> None:
    result = adapt_visual_energy_report_to_signals(
        {
            "visual_energy_result": {
                "segments": [
                    _segment("peak_visual_energy"),
                ]
            }
        }
    )

    assert result.status == "ok"
    assert result.signal_count == 1
    assert result.peak_signal_count == 1


def test_visual_energy_signal_adapter_files_do_not_have_bom() -> None:
    files = [
        REPO_ROOT / "core" / "visual_energy_signal_adapter.py",
        REPO_ROOT / "tests" / "test_visual_energy_signal_adapter_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has BOM"


def test_visual_energy_signal_adapter_files_end_with_newline() -> None:
    files = [
        REPO_ROOT / "core" / "visual_energy_signal_adapter.py",
        REPO_ROOT / "tests" / "test_visual_energy_signal_adapter_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert content.endswith(b"\n"), f"{file_path} does not end with newline"
