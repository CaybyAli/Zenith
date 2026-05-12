from __future__ import annotations

from pathlib import Path

from core.face_reaction_signal_adapter import (
    FaceReactionSignalAdapterResult,
    adapt_face_reaction_report_to_signals,
    adapt_face_reaction_segments_to_signals,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _segment(
    reaction_type: str,
    avg_reaction_score: float,
    max_reaction_score: float,
    recommendation: str = "review",
) -> dict:
    return {
        "start_seconds": 1.0,
        "end_seconds": 4.0,
        "duration_seconds": 3.0,
        "avg_reaction_score": avg_reaction_score,
        "max_reaction_score": max_reaction_score,
        "avg_face_area_ratio": 0.08,
        "reaction_type": reaction_type,
        "recommendation": recommendation,
        "warnings": [],
        "errors": [],
    }


def test_hype_becomes_high_reaction_segment_signal():
    result = adapt_face_reaction_segments_to_signals(
        [_segment("hype_candidate", avg_reaction_score=0.70, max_reaction_score=0.90)]
    )

    assert result.status == "ok"
    assert result.signal_count == 1
    assert result.high_reaction_signal_count == 1
    assert result.signals[0]["signal_type"] == "face_high_reaction_segment"
    assert result.signals[0]["source"] == "face_reaction"
    assert result.signals[0]["action_hint"] == "keep_or_emphasize_reaction"
    assert result.signals[0]["priority"] == "high"
    assert result.signals[0]["reason"] == "high_face_reaction_detected"


def test_expressive_becomes_high_reaction_segment_signal():
    result = adapt_face_reaction_segments_to_signals(
        [
            _segment(
                "expressive_reaction_candidate",
                avg_reaction_score=0.68,
                max_reaction_score=0.88,
            )
        ]
    )

    assert result.status == "ok"
    assert result.signals[0]["signal_type"] == "face_high_reaction_segment"
    assert result.signals[0]["action_hint"] == "keep_or_emphasize_reaction"


def test_shock_becomes_shock_reaction_candidate_signal():
    result = adapt_face_reaction_segments_to_signals(
        [_segment("shock_candidate", avg_reaction_score=0.75, max_reaction_score=0.95)]
    )

    assert result.status == "ok"
    assert result.shock_signal_count == 1
    assert result.signals[0]["signal_type"] == "face_shock_reaction_candidate"
    assert result.signals[0]["action_hint"] == "review_reaction_zoom_candidate"
    assert result.signals[0]["priority"] == "high"
    assert result.signals[0]["reason"] == "shock_reaction_candidate_detected"


def test_laugh_becomes_laugh_reaction_candidate_signal():
    result = adapt_face_reaction_segments_to_signals(
        [_segment("laugh_candidate", avg_reaction_score=0.72, max_reaction_score=0.91)]
    )

    assert result.status == "ok"
    assert result.laugh_signal_count == 1
    assert result.signals[0]["signal_type"] == "face_laugh_reaction_candidate"
    assert result.signals[0]["action_hint"] == "review_reaction_moment"
    assert result.signals[0]["priority"] == "high"
    assert result.signals[0]["reason"] == "laugh_reaction_candidate_detected"


def test_mouth_open_becomes_mouth_open_candidate_signal():
    result = adapt_face_reaction_segments_to_signals(
        [
            _segment(
                "mouth_open_candidate",
                avg_reaction_score=0.50,
                max_reaction_score=0.66,
            )
        ]
    )

    assert result.status == "ok"
    assert result.mouth_open_signal_count == 1
    assert result.signals[0]["signal_type"] == "face_mouth_open_candidate"
    assert result.signals[0]["action_hint"] == "review_reaction_moment"
    assert result.signals[0]["priority"] == "medium"
    assert result.signals[0]["reason"] == "mouth_open_candidate_detected"


def test_neutral_becomes_neutral_presence_segment_signal():
    result = adapt_face_reaction_segments_to_signals(
        [_segment("neutral_face", avg_reaction_score=0.20, max_reaction_score=0.30)]
    )

    assert result.status == "ok"
    assert result.signals[0]["signal_type"] == "face_neutral_presence_segment"
    assert result.signals[0]["action_hint"] == "context_face_presence"
    assert result.signals[0]["priority"] == "low"
    assert result.signals[0]["signal_score"] == 0.20
    assert result.signals[0]["reason"] == "neutral_face_presence_detected"


def test_signal_adapter_does_not_execute_automatic_zoom_or_render_actions():
    result = adapt_face_reaction_segments_to_signals(
        [_segment("shock_candidate", avg_reaction_score=0.75, max_reaction_score=0.95)]
    )

    action_hint = result.signals[0]["action_hint"]

    assert action_hint == "review_reaction_zoom_candidate"
    assert "execute_zoom" not in action_hint
    assert "auto_zoom" not in action_hint
    assert "render" not in action_hint


def test_empty_report_does_not_crash():
    result = adapt_face_reaction_report_to_signals({})

    assert result.status == "skipped_no_face_reaction_segments"
    assert result.signal_count == 0
    assert result.signals == []
    assert result.warnings


def test_invalid_segment_entries_do_not_crash():
    result = adapt_face_reaction_segments_to_signals(
        [
            None,
            "bad_segment",
            _segment("hype_candidate", avg_reaction_score=0.70, max_reaction_score=0.90),
        ]
    )

    assert result.status == "completed_with_warnings"
    assert result.signal_count == 1
    assert result.signals[0]["signal_type"] == "face_high_reaction_segment"
    assert result.warnings


def test_signal_contains_required_fields():
    result = adapt_face_reaction_segments_to_signals(
        [_segment("hype_candidate", avg_reaction_score=0.70, max_reaction_score=0.90)]
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


def test_signal_metadata_contains_face_reaction_details():
    result = adapt_face_reaction_segments_to_signals(
        [_segment("hype_candidate", avg_reaction_score=0.70, max_reaction_score=0.90)]
    )

    metadata = result.signals[0]["metadata"]

    assert metadata["original_reaction_type"] == "hype_candidate"
    assert metadata["avg_reaction_score"] == 0.70
    assert metadata["max_reaction_score"] == 0.90
    assert metadata["avg_face_area_ratio"] == 0.08
    assert metadata["recommendation"] == "review"
    assert metadata["source_index"] == 0
    assert metadata["warnings"] == []
    assert metadata["errors"] == []


def test_adapter_can_read_face_reaction_report_dict():
    report = {
        "face_reaction_segments": [
            _segment(
                "mouth_open_candidate",
                avg_reaction_score=0.50,
                max_reaction_score=0.66,
            )
        ]
    }

    result = adapt_face_reaction_report_to_signals(report)

    assert result.status == "ok"
    assert result.signal_count == 1
    assert result.signals[0]["signal_type"] == "face_mouth_open_candidate"


def test_adapter_result_roundtrip():
    result = adapt_face_reaction_segments_to_signals(
        [_segment("hype_candidate", avg_reaction_score=0.70, max_reaction_score=0.90)]
    )

    restored = FaceReactionSignalAdapterResult.from_dict(result.to_dict())

    assert restored.to_dict() == result.to_dict()


def test_face_reaction_signal_adapter_files_do_not_have_bom():
    files = [
        REPO_ROOT / "core" / "face_reaction_signal_adapter.py",
        REPO_ROOT / "tests" / "test_face_reaction_signal_adapter_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has BOM"


def test_face_reaction_signal_adapter_files_end_with_newline():
    files = [
        REPO_ROOT / "core" / "face_reaction_signal_adapter.py",
        REPO_ROOT / "tests" / "test_face_reaction_signal_adapter_smoke.py",
    ]

    for file_path in files:
        content = file_path.read_bytes()
        assert content.endswith(b"\n"), f"{file_path} does not end with newline"
