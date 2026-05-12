from __future__ import annotations

from pathlib import Path

from core.motion_analysis_signal_adapter import (
    MotionAnalysisSignalAdapterResult,
    adapt_motion_analysis_report_to_signals,
    adapt_motion_segments_to_signals,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _segment(
    classification: str,
    avg_motion_score: float,
    max_motion_score: float,
    recommendation: str = "review",
) -> dict:
    return {
        "start_seconds": 1.0,
        "end_seconds": 4.0,
        "duration_seconds": 3.0,
        "avg_motion_score": avg_motion_score,
        "max_motion_score": max_motion_score,
        "classification": classification,
        "recommendation": recommendation,
        "warnings": [],
        "errors": [],
    }


def test_high_motion_becomes_high_activity_signal():
    result = adapt_motion_segments_to_signals(
        [_segment("high_motion", avg_motion_score=0.40, max_motion_score=0.80)]
    )

    assert result.status == "ok"
    assert result.signal_count == 1
    assert result.signals[0]["signal_type"] == "motion_high_activity_segment"
    assert result.signals[0]["action_hint"] == "keep_or_review_action_moment"
    assert result.signals[0]["priority"] == "high"
    assert result.signals[0]["reason"] == "high_motion_detected"


def test_dead_visual_candidate_becomes_dead_visual_signal():
    result = adapt_motion_segments_to_signals(
        [
            _segment(
                "dead_visual_candidate",
                avg_motion_score=0.01,
                max_motion_score=0.02,
                recommendation="review_or_trim_dead_visual",
            )
        ]
    )

    signal = result.signals[0]

    assert result.status == "ok"
    assert result.dead_visual_candidate_signal_count == 1
    assert signal["signal_type"] == "motion_dead_visual_candidate"
    assert signal["action_hint"] == "review_or_trim_dead_visual"
    assert signal["priority"] == "high"
    assert signal["reason"] == "dead_visual_candidate_detected"


def test_dead_visual_candidate_does_not_auto_remove():
    result = adapt_motion_segments_to_signals(
        [
            _segment(
                "dead_visual_candidate",
                avg_motion_score=0.01,
                max_motion_score=0.02,
                recommendation="review_or_trim_dead_visual",
            )
        ]
    )

    action_hint = result.signals[0]["action_hint"]

    assert action_hint != "remove_now"
    assert action_hint != "hard_remove"
    assert "remove" not in action_hint


def test_low_motion_becomes_low_activity_signal():
    result = adapt_motion_segments_to_signals(
        [_segment("low_motion", avg_motion_score=0.05, max_motion_score=0.07)]
    )

    assert result.status == "ok"
    assert result.low_motion_signal_count == 1
    assert result.signals[0]["signal_type"] == "motion_low_activity_segment"
    assert result.signals[0]["action_hint"] == "review_possible_trim"


def test_static_becomes_static_signal():
    result = adapt_motion_segments_to_signals(
        [_segment("static", avg_motion_score=0.0, max_motion_score=0.0)]
    )

    assert result.status == "ok"
    assert result.static_signal_count == 1
    assert result.signals[0]["signal_type"] == "motion_static_segment"
    assert result.signals[0]["action_hint"] == "review_possible_trim"


def test_medium_motion_becomes_medium_activity_signal():
    result = adapt_motion_segments_to_signals(
        [_segment("medium_motion", avg_motion_score=0.20, max_motion_score=0.30)]
    )

    assert result.status == "ok"
    assert result.signals[0]["signal_type"] == "motion_medium_activity_segment"
    assert result.signals[0]["action_hint"] == "context_motion_segment"
    assert result.signals[0]["priority"] == "low"


def test_empty_report_does_not_crash():
    result = adapt_motion_analysis_report_to_signals({})

    assert result.status == "skipped_no_motion_segments"
    assert result.signal_count == 0
    assert result.signals == []
    assert result.warnings


def test_invalid_segment_entries_do_not_crash():
    result = adapt_motion_segments_to_signals(
        [
            None,
            "bad_segment",
            _segment("high_motion", avg_motion_score=0.50, max_motion_score=0.90),
        ]
    )

    assert result.status == "completed_with_warnings"
    assert result.signal_count == 1
    assert result.signals[0]["signal_type"] == "motion_high_activity_segment"
    assert result.warnings


def test_signal_contains_required_fields():
    result = adapt_motion_segments_to_signals(
        [_segment("high_motion", avg_motion_score=0.40, max_motion_score=0.80)]
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


def test_signal_metadata_contains_motion_details():
    result = adapt_motion_segments_to_signals(
        [_segment("high_motion", avg_motion_score=0.40, max_motion_score=0.80)]
    )

    metadata = result.signals[0]["metadata"]

    assert metadata["original_classification"] == "high_motion"
    assert metadata["avg_motion_score"] == 0.40
    assert metadata["max_motion_score"] == 0.80
    assert metadata["recommendation"] == "review"
    assert metadata["source_index"] == 0


def test_adapter_can_read_motion_analysis_report_dict():
    report = {
        "motion_segments": [
            _segment("low_motion", avg_motion_score=0.05, max_motion_score=0.07)
        ]
    }

    result = adapt_motion_analysis_report_to_signals(report)

    assert result.status == "ok"
    assert result.signal_count == 1
    assert result.signals[0]["signal_type"] == "motion_low_activity_segment"


def test_adapter_result_roundtrip():
    result = adapt_motion_segments_to_signals(
        [_segment("high_motion", avg_motion_score=0.40, max_motion_score=0.80)]
    )

    restored = MotionAnalysisSignalAdapterResult.from_dict(result.to_dict())

    assert restored.to_dict() == result.to_dict()


def test_motion_signal_adapter_files_do_not_have_bom():
    files = [
        REPO_ROOT / "core" / "motion_analysis_signal_adapter.py",
        REPO_ROOT / "tests" / "test_motion_analysis_signal_adapter_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has BOM"


def test_motion_signal_adapter_files_end_with_newline():
    files = [
        REPO_ROOT / "core" / "motion_analysis_signal_adapter.py",
        REPO_ROOT / "tests" / "test_motion_analysis_signal_adapter_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert content.endswith(b"\n"), f"{file_path} does not end with newline"
