from __future__ import annotations

from pathlib import Path

from core.content_value_calculator import (
    calculate_content_value,
    classify_content_value_tier,
    clamp_score,
)
from models.content_value import ContentValueResult, ContentValueSegmentScore


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _segment(text: str = "what a huge win", start: float = 1.0) -> dict:
    return {
        "segment_id": f"s_{start}",
        "start_seconds": start,
        "end_seconds": start + 2.0,
        "duration_seconds": 2.0,
        "text": text,
    }


def _high_reports() -> dict:
    return {
        "keyword_emotion_report": {
            "segment_scores": [
                {
                    "segment_id": "s_1.0",
                    "start_seconds": 1.0,
                    "end_seconds": 3.0,
                    "dominant_category": "hype",
                    "overall_keyword_score": 0.92,
                }
            ]
        },
        "interaction_classification_report": {
            "segment_classifications": [
                {
                    "segment_id": "s_1.0",
                    "start_seconds": 1.0,
                    "end_seconds": 3.0,
                    "interaction_type": "question_answer",
                    "confidence": 0.9,
                }
            ]
        },
        "visual_energy_report": {
            "visual_energy_segments": [
                {
                    "segment_id": "s_1.0",
                    "start_seconds": 1.0,
                    "end_seconds": 3.0,
                    "classification": "peak_visual_energy",
                    "max_visual_energy_score": 0.92,
                }
            ]
        },
        "face_reaction_report": {
            "face_reaction_segments": [
                {
                    "segment_id": "s_1.0",
                    "start_seconds": 1.0,
                    "end_seconds": 3.0,
                    "reaction_type": "shock",
                    "reaction_score": 0.9,
                }
            ]
        },
        "motion_analysis_report": {
            "motion_analysis_segments": [
                {
                    "segment_id": "s_1.0",
                    "start_seconds": 1.0,
                    "end_seconds": 3.0,
                    "motion_classification": "high_motion",
                    "motion_score": 0.85,
                }
            ]
        },
        "screen_content_report": {
            "screen_content_segments": [
                {
                    "segment_id": "s_1.0",
                    "start_seconds": 1.0,
                    "end_seconds": 3.0,
                    "screen_type": "victory_screen",
                    "confidence": 0.9,
                }
            ]
        },
        "energy_peak_report": {
            "energy_peaks": [
                {
                    "segment_id": "s_1.0",
                    "start_seconds": 1.5,
                    "end_seconds": 1.6,
                    "peak_type": "high_energy_peak",
                    "peak_score": 0.91,
                }
            ]
        },
        "sentence_boundary_report": {
            "boundaries": [
                {
                    "segment_id": "s_1.0",
                    "start_seconds": 1.0,
                    "end_seconds": 3.0,
                    "boundary_type": "complete_sentence",
                }
            ]
        },
    }


def test_content_value_segment_score_roundtrip() -> None:
    score = ContentValueSegmentScore(
        segment_id="s1",
        final_score=0.7,
        value_tier="high",
        evidence={"why": "test"},
        warnings=["warn"],
    )

    restored = ContentValueSegmentScore.from_dict(score.to_dict())

    assert restored.to_dict() == score.to_dict()


def test_content_value_result_roundtrip() -> None:
    score = ContentValueSegmentScore(segment_id="s1", final_score=0.7)
    result = ContentValueResult(
        status="ok",
        segment_scores=[score],
        segment_score_count=1,
        high_value_count=1,
    )

    restored = ContentValueResult.from_dict(result.to_dict())

    assert restored.to_dict() == result.to_dict()


def test_skipped_no_inputs_for_empty_input() -> None:
    result = calculate_content_value(transcript_segments=[])

    assert result.status == "skipped_no_inputs"
    assert result.recommendation == "content_value_skipped_no_inputs"


def test_high_keyword_interaction_visual_input_creates_high_value() -> None:
    result = calculate_content_value(
        transcript_segments=[_segment()],
        **_high_reports(),
    )

    assert result.status == "ok"
    assert result.high_value_count == 1
    assert result.segment_scores[0].value_tier == "high"


def test_dead_content_penalty_lowers_score() -> None:
    base = calculate_content_value(transcript_segments=[_segment()], **_high_reports())
    penalized = calculate_content_value(
        transcript_segments=[_segment()],
        dead_content_report={
            "candidates": [
                {
                    "segment_id": "s_1.0",
                    "start_seconds": 1.0,
                    "end_seconds": 3.0,
                    "candidate_type": "dead_air_candidate",
                    "dead_content_score": 0.95,
                }
            ]
        },
        **_high_reports(),
    )

    assert penalized.segment_scores[0].final_score < base.segment_scores[0].final_score
    assert penalized.segment_scores[0].dead_content_penalty_score >= 0.9


def test_protected_context_is_protected_not_low_delete() -> None:
    result = calculate_content_value(
        transcript_segments=[_segment("why?", start=5.0)],
        interaction_classification_report={
            "segment_classifications": [
                {
                    "segment_id": "s_5.0",
                    "start_seconds": 5.0,
                    "end_seconds": 7.0,
                    "interaction_type": "context_needed",
                    "context_needed": True,
                    "confidence": 0.9,
                }
            ]
        },
        sentence_boundary_report={
            "protection_zones": [
                {"segment_id": "s_5.0", "start_seconds": 5.0, "end_seconds": 7.0}
            ]
        },
    )

    score = result.segment_scores[0]
    assert score.value_tier == "protected"
    assert score.review_label == "review_protected_context"
    assert score.recommendation == "review_protected_context"


def test_technical_warning_tier() -> None:
    result = calculate_content_value(
        transcript_segments=[_segment("this froze badly", start=8.0)],
        stutter_detection_report={
            "stutter_detection_segments": [
                {
                    "segment_id": "s_8.0",
                    "start_seconds": 8.0,
                    "end_seconds": 10.0,
                    "classification": "freeze",
                    "confidence": 0.9,
                }
            ]
        },
    )

    assert result.segment_scores[0].value_tier == "technical_warning"
    assert result.technical_warning_count == 1


def test_hook_candidate_is_marked_without_selection() -> None:
    result = calculate_content_value(
        transcript_segments=[_segment()],
        **_high_reports(),
    )
    score = result.segment_scores[0]

    assert score.is_hook_candidate is True
    assert score.recommendation == "review_high_value_segment"


def test_low_input_creates_low_value() -> None:
    result = calculate_content_value(transcript_segments=[_segment("", start=11.0)])

    assert result.low_value_count == 1
    assert result.segment_scores[0].value_tier == "low"


def test_invalid_segments_do_not_crash() -> None:
    result = calculate_content_value(transcript_segments=[None, "bad", {"text": ""}])

    assert result.status in {"ok", "completed_with_warnings"}
    assert result.segment_score_count == 1
    assert result.segment_scores[0].warnings == []


def test_scores_are_clamped_to_zero_one() -> None:
    assert clamp_score(-10) == 0.0
    assert clamp_score(10) == 1.0
    assert classify_content_value_tier(2.0) == "high"
    result = calculate_content_value(
        transcript_segments=[_segment()],
        keyword_emotion_report={
            "segment_scores": [
                {"segment_id": "s_1.0", "overall_keyword_score": 10.0}
            ]
        },
    )

    for score in result.segment_scores:
        for key, value in score.to_dict().items():
            if key.endswith("_score"):
                assert 0.0 <= value <= 1.0


def test_new_files_have_no_bom_and_end_with_newline() -> None:
    for relative_path in (
        "models/content_value.py",
        "core/content_value_calculator.py",
        "tests/test_content_value_foundation_smoke.py",
    ):
        content = (PROJECT_ROOT / relative_path).read_bytes()
        assert not content.startswith(b"\xef\xbb\xbf")
        assert content.endswith(b"\n")
