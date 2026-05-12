from __future__ import annotations

from pathlib import Path

from core.stutter_detection_signal_adapter import (
    StutterDetectionSignalAdapterResult,
    adapt_stutter_detection_report_to_signals,
    adapt_stutter_segments_to_signals,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _segment(
    classification: str,
    duplicate_frame_count: int,
    avg_duplicate_score: float,
    max_duplicate_score: float,
    recommendation: str = "review",
) -> dict:
    return {
        "start_seconds": 1.0,
        "end_seconds": 4.0,
        "duration_seconds": 3.0,
        "start_frame_index": 10,
        "end_frame_index": 40,
        "duplicate_frame_count": duplicate_frame_count,
        "avg_duplicate_score": avg_duplicate_score,
        "max_duplicate_score": max_duplicate_score,
        "classification": classification,
        "recommendation": recommendation,
        "warnings": [],
        "errors": [],
    }


def test_stutter_segment_becomes_stutter_candidate_signal():
    result = adapt_stutter_segments_to_signals(
        [_segment("stutter_segment", 4, 0.990, 0.999)]
    )

    assert result.status == "ok"
    assert result.signal_count == 1
    assert result.stutter_signal_count == 1
    assert result.signals[0]["signal_type"] == "stutter_segment_candidate"
    assert result.signals[0]["source"] == "stutter_detection"
    assert result.signals[0]["action_hint"] == "review_stutter_segment"
    assert result.signals[0]["priority"] == "high"
    assert result.signals[0]["reason"] == "stutter_segment_detected"


def test_freeze_segment_becomes_freeze_candidate_signal():
    result = adapt_stutter_segments_to_signals(
        [_segment("freeze_segment", 12, 0.995, 1.0)]
    )

    assert result.status == "ok"
    assert result.freeze_signal_count == 1
    assert result.signals[0]["signal_type"] == "freeze_segment_candidate"
    assert result.signals[0]["action_hint"] == "review_freeze_segment"
    assert result.signals[0]["priority"] == "high"
    assert result.signals[0]["reason"] == "freeze_segment_detected"


def test_encoding_drop_becomes_encoding_drop_candidate_signal():
    result = adapt_stutter_segments_to_signals(
        [_segment("encoding_drop_candidate", 2, 0.988, 0.992)]
    )

    assert result.status == "ok"
    assert result.encoding_drop_signal_count == 1
    assert result.signals[0]["signal_type"] == "encoding_drop_candidate"
    assert result.signals[0]["action_hint"] == "review_encoding_drop_candidate"
    assert result.signals[0]["priority"] == "medium"
    assert result.signals[0]["reason"] == "encoding_drop_candidate_detected"


def test_signal_adapter_does_not_auto_remove():
    result = adapt_stutter_segments_to_signals(
        [_segment("stutter_segment", 4, 0.990, 0.999)]
    )

    action_hint = result.signals[0]["action_hint"]

    forbidden = {"remove_now", "hard_remove", "auto_remove", "delete_segment"}
    assert action_hint == "review_stutter_segment"
    assert action_hint not in forbidden
    for forbidden_text in forbidden:
        assert forbidden_text not in action_hint


def test_empty_report_does_not_crash():
    result = adapt_stutter_detection_report_to_signals({})

    assert result.status == "skipped_no_stutter_segments"
    assert result.signal_count == 0
    assert result.signals == []
    assert result.warnings


def test_invalid_segment_entries_do_not_crash():
    result = adapt_stutter_segments_to_signals(
        [
            None,
            "bad_segment",
            _segment("stutter_segment", 4, 0.990, 0.999),
        ]
    )

    assert result.status == "completed_with_warnings"
    assert result.signal_count == 1
    assert result.signals[0]["signal_type"] == "stutter_segment_candidate"
    assert result.warnings


def test_signal_contains_required_fields():
    result = adapt_stutter_segments_to_signals(
        [_segment("stutter_segment", 4, 0.990, 0.999)]
    )

    signal = result.signals[0]

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


def test_signal_metadata_contains_stutter_details():
    result = adapt_stutter_segments_to_signals(
        [_segment("stutter_segment", 4, 0.990, 0.999)]
    )

    metadata = result.signals[0]["metadata"]

    assert metadata["original_classification"] == "stutter_segment"
    assert metadata["duplicate_frame_count"] == 4
    assert metadata["avg_duplicate_score"] == 0.990
    assert metadata["max_duplicate_score"] == 0.999
    assert metadata["recommendation"] == "review"
    assert metadata["source_index"] == 0
    assert metadata["start_frame_index"] == 10
    assert metadata["end_frame_index"] == 40
    assert metadata["warnings"] == []
    assert metadata["errors"] == []


def test_adapter_can_read_stutter_detection_report_dict():
    report = {
        "stutter_segments": [
            _segment("freeze_segment", 12, 0.995, 1.0)
        ]
    }

    result = adapt_stutter_detection_report_to_signals(report)

    assert result.status == "ok"
    assert result.signal_count == 1
    assert result.signals[0]["signal_type"] == "freeze_segment_candidate"


def test_adapter_result_roundtrip():
    result = adapt_stutter_segments_to_signals(
        [_segment("stutter_segment", 4, 0.990, 0.999)]
    )

    restored = StutterDetectionSignalAdapterResult.from_dict(result.to_dict())

    assert restored.to_dict() == result.to_dict()


def test_stutter_signal_adapter_files_do_not_have_bom():
    files = [
        REPO_ROOT / "core" / "stutter_detection_signal_adapter.py",
        REPO_ROOT / "tests" / "test_stutter_detection_signal_adapter_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has BOM"


def test_stutter_signal_adapter_files_end_with_newline():
    files = [
        REPO_ROOT / "core" / "stutter_detection_signal_adapter.py",
        REPO_ROOT / "tests" / "test_stutter_detection_signal_adapter_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert content.endswith(b"\n"), f"{file_path} does not end with newline"
