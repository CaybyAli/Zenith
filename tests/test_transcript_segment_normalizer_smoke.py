from __future__ import annotations

from pathlib import Path
from typing import Any

from core.transcript_segment_normalizer import (
    TranscriptSegmentNormalizationResult,
    normalize_transcript_segment,
    normalize_transcript_segments,
    normalize_transcript_word,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class SegmentObject:
    def __init__(self) -> None:
        self.start_seconds = 1.0
        self.end_seconds = 2.5
        self.text = "Objekt Segment"
        self.confidence = 0.88
        self.metadata = {"source": "object-test"}


def test_dict_with_start_seconds_end_seconds_text_is_normalized() -> None:
    segment = normalize_transcript_segment(
        {
            "start_seconds": 0,
            "end_seconds": 2.5,
            "text": "Hallo Welt",
            "confidence": 0.95,
        },
        source_index=3,
    )

    assert segment["start_seconds"] == 0.0
    assert segment["end_seconds"] == 2.5
    assert segment["duration_seconds"] == 2.5
    assert segment["text"] == "Hallo Welt"
    assert segment["confidence"] == 0.95
    assert segment["source_index"] == 3
    assert segment["is_valid"] is True
    assert segment["errors"] == []


def test_dict_with_start_end_fallback_is_normalized() -> None:
    segment = normalize_transcript_segment(
        {
            "start": 1.2,
            "end": 4.0,
            "text": "Fallback Segment",
        }
    )

    assert segment["start_seconds"] == 1.2
    assert segment["end_seconds"] == 4.0
    assert segment["duration_seconds"] == 2.8
    assert segment["text"] == "Fallback Segment"
    assert segment["is_valid"] is True


def test_object_with_attributes_is_normalized() -> None:
    segment = normalize_transcript_segment(SegmentObject())

    assert segment["start_seconds"] == 1.0
    assert segment["end_seconds"] == 2.5
    assert segment["duration_seconds"] == 1.5
    assert segment["text"] == "Objekt Segment"
    assert segment["confidence"] == 0.88
    assert segment["metadata"] == {"source": "object-test"}
    assert segment["is_valid"] is True


def test_negative_timestamps_are_invalid() -> None:
    segment = normalize_transcript_segment(
        {
            "start_seconds": -1.0,
            "end_seconds": 2.0,
            "text": "Negative Zeit",
        }
    )

    assert segment["is_valid"] is False
    assert "negative_timestamp" in segment["errors"]


def test_end_before_start_is_invalid() -> None:
    segment = normalize_transcript_segment(
        {
            "start_seconds": 5.0,
            "end_seconds": 2.0,
            "text": "Falsche Reihenfolge",
        }
    )

    assert segment["is_valid"] is False
    assert "end_before_start" in segment["errors"]


def test_empty_text_is_invalid() -> None:
    segment = normalize_transcript_segment(
        {
            "start_seconds": 0.0,
            "end_seconds": 1.0,
            "text": "   ",
        }
    )

    assert segment["is_valid"] is False
    assert "empty_text" in segment["errors"]


def test_word_with_timestamps_is_normalized() -> None:
    word = normalize_transcript_word(
        {
            "word": "Hallo",
            "start": 0.1,
            "end": 0.4,
            "confidence": 0.91,
        },
        source_index=2,
        word_index=5,
    )

    assert word["word"] == "Hallo"
    assert word["start_seconds"] == 0.1
    assert word["end_seconds"] == 0.4
    assert word["confidence"] == 0.91
    assert word["source_index"] == 2
    assert word["word_index"] == 5
    assert word["is_valid"] is True


def test_segment_words_with_timestamps_enable_word_level_readiness() -> None:
    result = normalize_transcript_segments(
        [
            {
                "start_seconds": 0.0,
                "end_seconds": 1.5,
                "text": "Hallo Welt",
                "words": [
                    {"word": "Hallo", "start": 0.0, "end": 0.6},
                    {"word": "Welt", "start": 0.7, "end": 1.2},
                ],
            }
        ]
    )

    assert result.status == "ok"
    assert result.has_word_level_timestamps is True
    assert result.word_count == 2
    assert result.valid_segment_count == 1


def test_words_without_timestamps_create_warning() -> None:
    segment = normalize_transcript_segment(
        {
            "start_seconds": 0.0,
            "end_seconds": 1.5,
            "text": "Hallo Welt",
            "words": [
                {"word": "Hallo"},
                {"word": "Welt"},
            ],
        }
    )

    result = normalize_transcript_segments([segment])

    assert segment["is_valid"] is True
    assert "words_without_timestamps" in segment["warnings"]
    assert result.has_word_level_timestamps is False
    assert "words_without_timestamps" in result.warnings


def test_missing_words_mean_no_word_level_timestamps() -> None:
    result = normalize_transcript_segments(
        [
            {
                "start_seconds": 0.0,
                "end_seconds": 1.5,
                "text": "Nur Segment Text",
            }
        ]
    )

    assert result.status == "ok"
    assert result.has_word_level_timestamps is False
    assert result.word_count == 0


def test_none_and_invalid_payloads_do_not_crash() -> None:
    segment = normalize_transcript_segment(None)
    result_none = normalize_transcript_segments(None)
    result_invalid = normalize_transcript_segments("not-a-list")

    assert segment["is_valid"] is False
    assert "invalid_segment" in segment["errors"]

    assert result_none.status == "skipped_no_segments"
    assert "segments_missing" in result_none.warnings

    assert result_invalid.status == "failed"
    assert "invalid_segments_payload" in result_invalid.errors


def test_empty_segment_list_is_skipped_no_segments() -> None:
    result = normalize_transcript_segments([])

    assert result.status == "skipped_no_segments"
    assert result.segment_count == 0
    assert result.valid_segment_count == 0
    assert result.invalid_segment_count == 0
    assert result.recommendation == "no_transcript_segments_available"


def test_mixed_segments_result_is_completed_with_warnings() -> None:
    result = normalize_transcript_segments(
        [
            {
                "start_seconds": 0.0,
                "end_seconds": 1.0,
                "text": "Gültig",
            },
            {
                "start_seconds": 3.0,
                "end_seconds": 2.0,
                "text": "Ungültig",
            },
        ]
    )

    assert result.status == "completed_with_warnings"
    assert result.segment_count == 2
    assert result.valid_segment_count == 1
    assert result.invalid_segment_count == 1
    assert "end_before_start" in result.errors


def test_result_to_dict_roundtrip_shape() -> None:
    result = TranscriptSegmentNormalizationResult(
        status="ok",
        segments=[{"text": "A"}],
        valid_segments=[{"text": "A"}],
        invalid_segments=[],
        segment_count=1,
        valid_segment_count=1,
        invalid_segment_count=0,
        word_count=0,
        has_word_level_timestamps=False,
        warnings=[],
        errors=[],
        recommendation="use_normalized_segments",
        metadata={"stage": "test"},
    )

    data = result.to_dict()

    assert data["status"] == "ok"
    assert data["segments"] == [{"text": "A"}]
    assert data["valid_segment_count"] == 1
    assert data["metadata"] == {"stage": "test"}


def test_normalizer_files_have_no_bom_and_end_with_newline() -> None:
    checked_files = [
        "core/transcript_segment_normalizer.py",
        "tests/test_transcript_segment_normalizer_smoke.py",
    ]

    for relative_path in checked_files:
        data = (PROJECT_ROOT / relative_path).read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"{relative_path} has UTF-8 BOM"
        assert data.endswith(b"\n"), f"{relative_path} must end with newline"


def test_normalizer_does_not_contain_cut_logic() -> None:
    source = (PROJECT_ROOT / "core/transcript_segment_normalizer.py").read_text(encoding="utf-8")

    forbidden_strings = [
        "force_cut",
        "auto_remove",
        "hard_remove",
        "remove_now",
        "cut_sentence_now",
        "timeline_builder",
        "highlight_selector",
    ]

    for forbidden in forbidden_strings:
        assert forbidden not in source
