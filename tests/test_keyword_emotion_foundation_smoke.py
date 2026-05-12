from __future__ import annotations

from pathlib import Path

from core.keyword_emotion_scorer import (
    classify_keyword_category,
    detect_keyword_language,
    find_keyword_emotion_matches,
    score_keyword_emotions,
)
from models.keyword_emotion import (
    CATEGORY_FRUSTRATION,
    CATEGORY_HYPE,
    CATEGORY_LAUGH,
    CATEGORY_QUESTION,
    CATEGORY_SHOCK,
    LANGUAGE_DE,
    LANGUAGE_EN,
    LANGUAGE_TR,
    STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS,
    KeywordEmotionMatch,
    KeywordEmotionResult,
    KeywordEmotionSegmentScore,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _path(relative_path: str) -> Path:
    return PROJECT_ROOT / relative_path


def test_keyword_emotion_match_roundtrip() -> None:
    match = KeywordEmotionMatch(
        match_id="m1",
        start_seconds=1.0,
        end_seconds=2.0,
        center_seconds=1.5,
        text="That was insane",
        matched_keyword="insane",
        normalized_keyword="insane",
        category=CATEGORY_HYPE,
        language=LANGUAGE_EN,
        intensity=0.8,
        confidence=0.9,
        source_segment_index=0,
        metadata={"source": "test"},
        warnings=[],
        errors=[],
    )

    restored = KeywordEmotionMatch.from_dict(match.to_dict())

    assert restored.match_id == "m1"
    assert restored.category == CATEGORY_HYPE
    assert restored.language == LANGUAGE_EN
    assert restored.metadata == {"source": "test"}


def test_keyword_emotion_segment_score_roundtrip() -> None:
    score = KeywordEmotionSegmentScore(
        segment_id="s1",
        start_seconds=1.0,
        end_seconds=3.0,
        duration_seconds=2.0,
        text="insane no way",
        categories={CATEGORY_HYPE: 0.8, CATEGORY_SHOCK: 0.9},
        dominant_category=CATEGORY_SHOCK,
        emotion_score=0.9,
        hype_score=0.8,
        shock_score=0.9,
        overall_keyword_score=0.65,
        match_count=2,
        recommendation="review_high_value_keyword_segment",
    )

    restored = KeywordEmotionSegmentScore.from_dict(score.to_dict())

    assert restored.segment_id == "s1"
    assert restored.dominant_category == CATEGORY_SHOCK
    assert restored.match_count == 2
    assert restored.categories[CATEGORY_HYPE] == 0.8


def test_keyword_emotion_result_roundtrip() -> None:
    result = KeywordEmotionResult(
        status="ok",
        matches=[KeywordEmotionMatch(match_id="m1")],
        segment_scores=[KeywordEmotionSegmentScore(segment_id="s1")],
        match_count=1,
        segment_score_count=1,
        hype_match_count=1,
        recommendation="use_keyword_emotion_scoring",
    )

    restored = KeywordEmotionResult.from_dict(result.to_dict())

    assert restored.status == "ok"
    assert restored.match_count == 1
    assert restored.segment_score_count == 1
    assert restored.matches[0].match_id == "m1"


def test_de_hype_keyword_is_detected() -> None:
    matches = find_keyword_emotion_matches("Das war krass.")

    assert any(match.category == CATEGORY_HYPE for match in matches)
    assert detect_keyword_language("krass") == LANGUAGE_DE


def test_en_hype_keyword_is_detected() -> None:
    matches = find_keyword_emotion_matches("That play was insane.")

    assert any(match.category == CATEGORY_HYPE for match in matches)
    assert detect_keyword_language("insane") == LANGUAGE_EN


def test_tr_hype_keyword_is_detected() -> None:
    matches = find_keyword_emotion_matches("Bu çok iyi.")

    assert any(match.category == CATEGORY_HYPE for match in matches)
    assert detect_keyword_language("çok iyi") == LANGUAGE_TR


def test_frustration_keyword_is_detected() -> None:
    matches = find_keyword_emotion_matches("This is annoying bro.")

    assert any(match.category == CATEGORY_FRUSTRATION for match in matches)
    assert classify_keyword_category("annoying") == CATEGORY_FRUSTRATION


def test_shock_keyword_is_detected() -> None:
    matches = find_keyword_emotion_matches("No way, seriously?")

    assert any(match.category == CATEGORY_SHOCK for match in matches)
    assert classify_keyword_category("no way") == CATEGORY_SHOCK


def test_laugh_keyword_is_detected() -> None:
    matches = find_keyword_emotion_matches("haha that was hilarious")

    assert any(match.category == CATEGORY_LAUGH for match in matches)
    assert classify_keyword_category("hilarious") == CATEGORY_LAUGH


def test_question_keyword_is_detected() -> None:
    matches = find_keyword_emotion_matches("why did that happen")

    assert any(match.category == CATEGORY_QUESTION for match in matches)
    assert classify_keyword_category("why") == CATEGORY_QUESTION


def test_segment_with_multiple_keywords_gets_higher_score() -> None:
    low = score_keyword_emotions(
        [{"start_seconds": 0.0, "end_seconds": 1.0, "text": "normal gameplay"}]
    )
    high = score_keyword_emotions(
        [
            {
                "start_seconds": 0.0,
                "end_seconds": 2.0,
                "text": "insane no way haha why",
            }
        ]
    )

    assert high.segment_scores[0].overall_keyword_score > low.segment_scores[0].overall_keyword_score
    assert high.segment_scores[0].match_count >= 4


def test_empty_transcript_list_skips() -> None:
    result = score_keyword_emotions([])

    assert result.status == STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS
    assert result.recommendation == "keyword_emotion_skipped_no_transcript"
    assert result.match_count == 0


def test_invalid_segments_do_not_crash() -> None:
    result = score_keyword_emotions([{"start_seconds": 5.0, "text": ""}, None])

    assert result.status in {"completed_with_warnings", "failed"}
    assert isinstance(result.to_dict(), dict)
    assert isinstance(result.errors, list)


def test_keyword_emotion_files_have_no_bom() -> None:
    for relative_path in [
        "models/keyword_emotion.py",
        "core/keyword_emotion_scorer.py",
        "tests/test_keyword_emotion_foundation_smoke.py",
    ]:
        assert not _path(relative_path).read_bytes().startswith(b"\xef\xbb\xbf")


def test_keyword_emotion_files_end_with_newline() -> None:
    for relative_path in [
        "models/keyword_emotion.py",
        "core/keyword_emotion_scorer.py",
        "tests/test_keyword_emotion_foundation_smoke.py",
    ]:
        assert _path(relative_path).read_bytes().endswith(b"\n")
