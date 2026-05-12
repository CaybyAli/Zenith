from __future__ import annotations

from pathlib import Path

from core.sentence_boundary_protector import (
    analyze_sentence_boundaries,
    build_sentence_boundary_points,
    build_sentence_protection_zones,
    classify_sentence_text,
    is_question_text,
    is_sentence_complete,
)
from models.sentence_boundary import (
    BOUNDARY_OPEN_FRAGMENT,
    BOUNDARY_QUESTION,
    STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS,
    ZONE_PROTECT_OPEN_FRAGMENT,
    ZONE_PROTECT_QUESTION_CONTEXT,
    SentenceBoundaryPoint,
    SentenceBoundaryProtectionZone,
    SentenceBoundaryResult,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _path(relative_path: str) -> Path:
    return PROJECT_ROOT / relative_path


def test_sentence_boundary_point_roundtrip() -> None:
    point = SentenceBoundaryPoint(
        boundary_id="b1",
        start_seconds=1.0,
        end_seconds=2.0,
        center_seconds=1.5,
        text="What happened?",
        normalized_text="what happened?",
        boundary_type=BOUNDARY_QUESTION,
        protection_level="soft",
        is_complete_sentence=True,
        is_question=True,
        confidence=0.9,
        recommendation="protect_question_context",
        source_segment_index=0,
        metadata={"k": "v"},
        warnings=["w"],
        errors=[],
    )

    restored = SentenceBoundaryPoint.from_dict(point.to_dict())

    assert restored.boundary_id == point.boundary_id
    assert restored.boundary_type == BOUNDARY_QUESTION
    assert restored.is_question is True
    assert restored.metadata == {"k": "v"}


def test_sentence_boundary_protection_zone_roundtrip() -> None:
    zone = SentenceBoundaryProtectionZone(
        zone_id="z1",
        start_seconds=1.0,
        end_seconds=3.0,
        duration_seconds=2.0,
        zone_type=ZONE_PROTECT_QUESTION_CONTEXT,
        protection_level="soft",
        reason="question_context_should_be_preserved",
        confidence=0.8,
        source_boundary_ids=["b1"],
        metadata={"source": "test"},
        warnings=[],
        errors=[],
    )

    restored = SentenceBoundaryProtectionZone.from_dict(zone.to_dict())

    assert restored.zone_id == "z1"
    assert restored.zone_type == ZONE_PROTECT_QUESTION_CONTEXT
    assert restored.source_boundary_ids == ["b1"]


def test_sentence_boundary_result_roundtrip() -> None:
    result = SentenceBoundaryResult(
        status="ok",
        boundaries=[SentenceBoundaryPoint(boundary_id="b1")],
        protection_zones=[SentenceBoundaryProtectionZone(zone_id="z1")],
        boundary_count=1,
        protection_zone_count=1,
        recommendation="use_sentence_boundary_protection",
    )

    restored = SentenceBoundaryResult.from_dict(result.to_dict())

    assert restored.status == "ok"
    assert restored.boundary_count == 1
    assert restored.protection_zone_count == 1
    assert restored.boundaries[0].boundary_id == "b1"


def test_is_sentence_complete_recognizes_period() -> None:
    assert is_sentence_complete("This is complete.")


def test_is_sentence_complete_recognizes_question_mark() -> None:
    assert is_sentence_complete("Is this complete?")


def test_open_sentence_without_punctuation_is_open_fragment() -> None:
    classification = classify_sentence_text("this sentence keeps going")

    assert classification["boundary_type"] == BOUNDARY_OPEN_FRAGMENT
    assert classification["is_open_fragment"] is True


def test_question_is_question_boundary() -> None:
    classification = classify_sentence_text("What happened?")

    assert classification["boundary_type"] == BOUNDARY_QUESTION
    assert classification["is_question"] is True


def test_german_question_words_are_recognized() -> None:
    assert is_question_text("Warum ist das so")
    assert is_question_text("Wie geht das")


def test_english_question_words_are_recognized() -> None:
    assert is_question_text("Where did it go")
    assert is_question_text("How does this work")


def test_turkish_question_words_are_recognized() -> None:
    assert is_question_text("Neden boyle oldu")
    assert is_question_text("Nasıl oynadın")


def test_analyze_empty_transcript_segments_skips() -> None:
    result = analyze_sentence_boundaries([])

    assert result.status == STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS
    assert result.recommendation == "sentence_boundary_skipped_no_transcript"
    assert result.boundary_count == 0


def test_invalid_segments_do_not_crash() -> None:
    result = analyze_sentence_boundaries([{"start_seconds": 3.0, "text": ""}, None])

    assert result.status in {"completed_with_warnings", "failed"}
    assert isinstance(result.to_dict(), dict)
    assert isinstance(result.errors, list)


def test_protection_zone_for_open_fragment_is_built() -> None:
    boundaries = build_sentence_boundary_points(
        [
            {
                "start_seconds": 0.0,
                "end_seconds": 2.0,
                "duration_seconds": 2.0,
                "text": "I was going to say",
                "source_index": 0,
                "is_valid": True,
            }
        ]
    )
    zones = build_sentence_protection_zones(boundaries)

    assert any(zone.zone_type == ZONE_PROTECT_OPEN_FRAGMENT for zone in zones)


def test_protection_zone_for_question_context_is_built() -> None:
    result = analyze_sentence_boundaries(
        [
            {"start_seconds": 0.0, "end_seconds": 1.0, "text": "What happened?"},
            {"start_seconds": 1.2, "end_seconds": 2.0, "text": "It crashed."},
        ]
    )

    assert any(
        zone.zone_type == ZONE_PROTECT_QUESTION_CONTEXT
        for zone in result.protection_zones
    )


def test_sentence_boundary_files_have_no_bom() -> None:
    for relative_path in [
        "models/sentence_boundary.py",
        "core/sentence_boundary_protector.py",
        "tests/test_sentence_boundary_foundation_smoke.py",
    ]:
        assert not _path(relative_path).read_bytes().startswith(b"\xef\xbb\xbf")


def test_sentence_boundary_files_end_with_newline() -> None:
    for relative_path in [
        "models/sentence_boundary.py",
        "core/sentence_boundary_protector.py",
        "tests/test_sentence_boundary_foundation_smoke.py",
    ]:
        assert _path(relative_path).read_bytes().endswith(b"\n")
