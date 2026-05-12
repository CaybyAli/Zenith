from __future__ import annotations

from pathlib import Path

from core.dead_content_detector import detect_dead_content, score_dead_content_segment
from models.dead_content import (
    DeadContentCandidate,
    DeadContentDetectionResult,
    DeadContentSegmentScore,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _segment(text: str = "", start: float = 1.0, end: float = 2.0) -> dict:
    return {
        "segment_id": f"seg_{start}",
        "start_seconds": start,
        "end_seconds": end,
        "duration_seconds": end - start,
        "text": text,
    }


def test_dead_content_candidate_roundtrip() -> None:
    candidate = DeadContentCandidate(
        candidate_id="c1",
        start_seconds=1.0,
        end_seconds=2.0,
        center_seconds=1.5,
        duration_seconds=1.0,
        text="",
        candidate_type="low_value_content_candidate",
        dead_content_score=0.8,
        confidence=0.9,
        review_required=True,
        evidence={"empty_text": True},
    )

    restored = DeadContentCandidate.from_dict(candidate.to_dict())

    assert restored.to_dict() == candidate.to_dict()


def test_dead_content_segment_score_roundtrip() -> None:
    score = DeadContentSegmentScore(
        segment_id="s1",
        start_seconds=1.0,
        end_seconds=2.0,
        duration_seconds=1.0,
        text="hm",
        dead_content_score=0.6,
        content_value_score=0.1,
        candidate_type="low_value_content_candidate",
        review_required=True,
        evidence={"very_short_text": True},
    )

    restored = DeadContentSegmentScore.from_dict(score.to_dict())

    assert restored.to_dict() == score.to_dict()


def test_dead_content_detection_result_roundtrip() -> None:
    candidate = DeadContentCandidate(candidate_id="c1")
    score = DeadContentSegmentScore(segment_id="s1")
    result = DeadContentDetectionResult(
        status="ok",
        candidates=[candidate],
        segment_scores=[score],
        candidate_count=1,
        segment_score_count=1,
    )

    restored = DeadContentDetectionResult.from_dict(result.to_dict())

    assert restored.to_dict() == result.to_dict()


def test_empty_input_yields_skipped_no_inputs() -> None:
    result = detect_dead_content(transcript_segments=[])

    assert result.status == "skipped_no_inputs"
    assert result.candidate_count == 0
    assert result.recommendation == "dead_content_skipped_no_inputs"


def test_empty_or_very_short_segment_becomes_low_value_candidate() -> None:
    result = detect_dead_content(transcript_segments=[_segment("ok")])

    assert result.candidate_count == 1
    assert result.candidates[0].candidate_type == "low_value_content_candidate"
    assert result.candidates[0].recommendation == "review_dead_content_candidate"


def test_loading_menu_evidence_creates_loading_or_menu_candidate() -> None:
    result = detect_dead_content(
        transcript_segments=[_segment("waiting", 10.0, 12.0)],
        screen_content_report={
            "screen_content_segments": [
                {
                    "start_seconds": 10.0,
                    "end_seconds": 12.0,
                    "screen_type": "loading",
                    "avg_confidence": 0.9,
                }
            ]
        },
    )

    assert result.candidates[0].candidate_type == "loading_or_menu_candidate"
    assert result.candidates[0].recommendation == "review_loading_or_menu_candidate"


def test_low_visual_evidence_increases_dead_content_score() -> None:
    base = score_dead_content_segment(_segment("I am just walking around", 1.0, 3.0))
    low_visual = score_dead_content_segment(
        _segment("I am just walking around", 1.0, 3.0),
        related_sources={
            "visual_energy_segments": [
                {
                    "start_seconds": 1.0,
                    "end_seconds": 3.0,
                    "classification": "low_visual_energy",
                    "avg_visual_energy_score": 0.1,
                }
            ]
        },
    )

    assert low_visual.low_visual_score > 0.0
    assert low_visual.dead_content_score > base.dead_content_score


def test_keyword_high_value_protects_from_dead_content() -> None:
    result = detect_dead_content(
        transcript_segments=[_segment("wow", 1.0, 2.0)],
        keyword_emotion_report={
            "segment_scores": [
                {
                    "segment_id": "k1",
                    "start_seconds": 1.0,
                    "end_seconds": 2.0,
                    "overall_keyword_score": 0.9,
                    "categories": {"hype": 0.9},
                    "dominant_category": "hype",
                }
            ]
        },
    )

    assert result.candidates[0].protected_by_context is True
    assert result.candidates[0].recommendation == "review_protected_context"


def test_question_or_context_needed_protects_from_dead_content() -> None:
    result = detect_dead_content(
        transcript_segments=[_segment("what now?", 4.0, 5.0)],
        interaction_classification_report={
            "segment_classifications": [
                {
                    "segment_id": "i1",
                    "start_seconds": 4.0,
                    "end_seconds": 5.0,
                    "interaction_type": "question_answer",
                    "context_needed": True,
                    "confidence": 0.9,
                }
            ]
        },
    )

    assert result.candidates[0].protected_by_context is True
    assert result.candidates[0].candidate_type == "protected_context_candidate"


def test_private_or_meta_candidate_is_review_not_removal() -> None:
    result = detect_dead_content(
        transcript_segments=[_segment("my real address is", 8.0, 9.0)],
        interaction_classification_report={
            "segment_classifications": [
                {
                    "segment_id": "p1",
                    "start_seconds": 8.0,
                    "end_seconds": 9.0,
                    "interaction_type": "private_or_meta_candidate",
                    "confidence": 0.9,
                }
            ]
        },
    )

    assert result.candidates[0].candidate_type == "private_or_meta_review_candidate"
    assert result.candidates[0].recommendation == "review_private_or_meta_candidate"


def test_sentence_protection_sets_review_protected_context() -> None:
    result = detect_dead_content(
        transcript_segments=[_segment("because I was", 6.0, 7.0)],
        sentence_boundary_report={
            "boundaries": [
                {
                    "boundary_id": "b1",
                    "start_seconds": 6.0,
                    "end_seconds": 7.0,
                    "boundary_type": "open_sentence_fragment",
                    "confidence": 0.8,
                }
            ]
        },
    )

    assert result.candidates[0].protected_by_context is True
    assert result.candidates[0].recommendation == "review_protected_context"


def test_invalid_segments_do_not_crash() -> None:
    result = detect_dead_content(transcript_segments=[None, "bad", {"text": ""}])

    assert result.status in {"ok", "completed_with_warnings"}
    assert result.segment_score_count == 1


def test_dead_content_foundation_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in (
        "models/dead_content.py",
        "core/dead_content_detector.py",
        "tests/test_dead_content_detection_foundation_smoke.py",
    ):
        content = (PROJECT_ROOT / relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
