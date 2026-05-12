from __future__ import annotations

import re
import unicodedata
from typing import Any

from core.transcript_segment_normalizer import normalize_transcript_segments
from models.keyword_emotion import (
    CATEGORY_CALLOUT,
    CATEGORY_FRUSTRATION,
    CATEGORY_GAMEPLAY,
    CATEGORY_HYPE,
    CATEGORY_LAUGH,
    CATEGORY_NEUTRAL,
    CATEGORY_QUESTION,
    CATEGORY_SHOCK,
    CATEGORY_UNKNOWN,
    LANGUAGE_DE,
    LANGUAGE_EN,
    LANGUAGE_MIXED,
    LANGUAGE_TR,
    LANGUAGE_UNKNOWN,
    STATUS_COMPLETED_WITH_WARNINGS,
    STATUS_FAILED,
    STATUS_OK,
    STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS,
    KeywordEmotionMatch,
    KeywordEmotionResult,
    KeywordEmotionSegmentScore,
)


_WORD_RE = re.compile(r"[\wÄÖÜäöüßÇĞİÖŞÜçğıöşü]+", re.UNICODE)
_PUNCT_RE = re.compile(r"[^\wÄÖÜäöüßÇĞİÖŞÜçğıöşü\s]+", re.UNICODE)
_CATEGORY_WEIGHTS = {
    CATEGORY_HYPE: 0.25,
    CATEGORY_SHOCK: 0.25,
    CATEGORY_LAUGH: 0.20,
    CATEGORY_FRUSTRATION: 0.15,
    CATEGORY_QUESTION: 0.15,
    CATEGORY_CALLOUT: 0.15,
}


def _clamp(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        result = default
    return max(0.0, min(1.0, result))


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _ascii_fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_keyword_text(text: Any) -> str:
    if text is None:
        return ""
    try:
        value = str(text)
    except Exception:
        return ""
    value = value.strip().lower()
    value = _PUNCT_RE.sub(" ", value)
    return " ".join(value.split())


def _matchable_variants(text: str) -> set[str]:
    normalized = normalize_keyword_text(text)
    variants = {normalized}
    folded = normalize_keyword_text(_ascii_fold(normalized))
    if folded:
        variants.add(folded)
    return {variant for variant in variants if variant}


def _keyword_entries() -> list[dict[str, Any]]:
    raw_entries: list[tuple[str, str, str, float, float]] = [
        ("krass", CATEGORY_HYPE, LANGUAGE_DE, 0.72, 0.84),
        ("stark", CATEGORY_HYPE, LANGUAGE_DE, 0.64, 0.78),
        ("geil", CATEGORY_HYPE, LANGUAGE_DE, 0.72, 0.82),
        ("krank", CATEGORY_HYPE, LANGUAGE_DE, 0.74, 0.80),
        ("lets go", CATEGORY_HYPE, LANGUAGE_MIXED, 0.88, 0.90),
        ("heftig", CATEGORY_HYPE, LANGUAGE_DE, 0.76, 0.84),
        ("brutal", CATEGORY_HYPE, LANGUAGE_DE, 0.72, 0.80),
        ("insane", CATEGORY_HYPE, LANGUAGE_EN, 0.86, 0.90),
        ("nein", CATEGORY_FRUSTRATION, LANGUAGE_DE, 0.58, 0.72),
        ("alter", CATEGORY_FRUSTRATION, LANGUAGE_DE, 0.58, 0.68),
        ("warum", CATEGORY_QUESTION, LANGUAGE_DE, 0.55, 0.78),
        ("digga", CATEGORY_FRUSTRATION, LANGUAGE_DE, 0.52, 0.68),
        ("bro", CATEGORY_FRUSTRATION, LANGUAGE_MIXED, 0.50, 0.65),
        ("was machst du", CATEGORY_FRUSTRATION, LANGUAGE_DE, 0.78, 0.84),
        ("nervt", CATEGORY_FRUSTRATION, LANGUAGE_DE, 0.70, 0.82),
        ("schlecht", CATEGORY_FRUSTRATION, LANGUAGE_DE, 0.64, 0.78),
        ("hä", CATEGORY_SHOCK, LANGUAGE_DE, 0.65, 0.78),
        ("was", CATEGORY_QUESTION, LANGUAGE_DE, 0.50, 0.76),
        ("oh mein gott", CATEGORY_SHOCK, LANGUAGE_DE, 0.88, 0.90),
        ("no way", CATEGORY_SHOCK, LANGUAGE_EN, 0.88, 0.90),
        ("niemals", CATEGORY_SHOCK, LANGUAGE_DE, 0.76, 0.84),
        ("nicht dein ernst", CATEGORY_SHOCK, LANGUAGE_DE, 0.84, 0.88),
        ("haha", CATEGORY_LAUGH, LANGUAGE_MIXED, 0.72, 0.84),
        ("hahaha", CATEGORY_LAUGH, LANGUAGE_MIXED, 0.84, 0.90),
        ("lach", CATEGORY_LAUGH, LANGUAGE_DE, 0.62, 0.74),
        ("lol", CATEGORY_LAUGH, LANGUAGE_MIXED, 0.70, 0.82),
        ("lustig", CATEGORY_LAUGH, LANGUAGE_DE, 0.62, 0.78),
        ("wer", CATEGORY_QUESTION, LANGUAGE_DE, 0.46, 0.72),
        ("wann", CATEGORY_QUESTION, LANGUAGE_DE, 0.46, 0.72),
        ("wo", CATEGORY_QUESTION, LANGUAGE_DE, 0.46, 0.72),
        ("wieso", CATEGORY_QUESTION, LANGUAGE_DE, 0.54, 0.76),
        ("wie", CATEGORY_QUESTION, LANGUAGE_DE, 0.46, 0.72),
        ("crazy", CATEGORY_HYPE, LANGUAGE_EN, 0.76, 0.84),
        ("clutch", CATEGORY_GAMEPLAY, LANGUAGE_EN, 0.82, 0.88),
        ("cracked", CATEGORY_GAMEPLAY, LANGUAGE_EN, 0.78, 0.84),
        ("huge", CATEGORY_HYPE, LANGUAGE_EN, 0.70, 0.82),
        ("massive", CATEGORY_HYPE, LANGUAGE_EN, 0.70, 0.82),
        ("no", CATEGORY_FRUSTRATION, LANGUAGE_EN, 0.52, 0.70),
        ("why", CATEGORY_QUESTION, LANGUAGE_EN, 0.54, 0.78),
        ("annoying", CATEGORY_FRUSTRATION, LANGUAGE_EN, 0.70, 0.82),
        ("bad", CATEGORY_FRUSTRATION, LANGUAGE_EN, 0.58, 0.76),
        ("terrible", CATEGORY_FRUSTRATION, LANGUAGE_EN, 0.76, 0.84),
        ("what", CATEGORY_QUESTION, LANGUAGE_EN, 0.50, 0.76),
        ("oh my god", CATEGORY_SHOCK, LANGUAGE_EN, 0.88, 0.90),
        ("seriously", CATEGORY_SHOCK, LANGUAGE_EN, 0.68, 0.78),
        ("funny", CATEGORY_LAUGH, LANGUAGE_EN, 0.62, 0.78),
        ("hilarious", CATEGORY_LAUGH, LANGUAGE_EN, 0.78, 0.86),
        ("who", CATEGORY_QUESTION, LANGUAGE_EN, 0.46, 0.72),
        ("when", CATEGORY_QUESTION, LANGUAGE_EN, 0.46, 0.72),
        ("where", CATEGORY_QUESTION, LANGUAGE_EN, 0.46, 0.72),
        ("how", CATEGORY_QUESTION, LANGUAGE_EN, 0.46, 0.72),
        ("hadi", CATEGORY_HYPE, LANGUAGE_TR, 0.70, 0.82),
        ("cok iyi", CATEGORY_HYPE, LANGUAGE_TR, 0.82, 0.86),
        ("çok iyi", CATEGORY_HYPE, LANGUAGE_TR, 0.82, 0.88),
        ("efsane", CATEGORY_HYPE, LANGUAGE_TR, 0.80, 0.86),
        ("harika", CATEGORY_HYPE, LANGUAGE_TR, 0.76, 0.84),
        ("hayir", CATEGORY_FRUSTRATION, LANGUAGE_TR, 0.58, 0.76),
        ("hayır", CATEGORY_FRUSTRATION, LANGUAGE_TR, 0.58, 0.78),
        ("neden", CATEGORY_QUESTION, LANGUAGE_TR, 0.54, 0.78),
        ("kotu", CATEGORY_FRUSTRATION, LANGUAGE_TR, 0.62, 0.78),
        ("kötü", CATEGORY_FRUSTRATION, LANGUAGE_TR, 0.62, 0.80),
        ("ne", CATEGORY_QUESTION, LANGUAGE_TR, 0.50, 0.76),
        ("nasil", CATEGORY_QUESTION, LANGUAGE_TR, 0.54, 0.78),
        ("nasıl", CATEGORY_QUESTION, LANGUAGE_TR, 0.54, 0.80),
        ("olamaz", CATEGORY_SHOCK, LANGUAGE_TR, 0.78, 0.86),
        ("komik", CATEGORY_LAUGH, LANGUAGE_TR, 0.62, 0.78),
        ("kim", CATEGORY_QUESTION, LANGUAGE_TR, 0.46, 0.72),
        ("nerede", CATEGORY_QUESTION, LANGUAGE_TR, 0.46, 0.72),
    ]

    entries: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for keyword, category, language, intensity, confidence in raw_entries:
        for normalized in _matchable_variants(keyword):
            key = (normalized, category, language)
            if key in seen:
                continue
            seen.add(key)
            entries.append(
                {
                    "keyword": keyword,
                    "normalized": normalized,
                    "category": category,
                    "language": language,
                    "intensity": intensity,
                    "confidence": confidence,
                }
            )

    entries.sort(key=lambda item: len(str(item["normalized"]).split()), reverse=True)
    return entries


_KEYWORD_ENTRIES = _keyword_entries()
_KEYWORD_BY_NORMALIZED: dict[str, dict[str, Any]] = {
    str(entry["normalized"]): entry for entry in _KEYWORD_ENTRIES
}


def detect_keyword_language(keyword: Any) -> str:
    normalized = normalize_keyword_text(keyword)
    entry = _KEYWORD_BY_NORMALIZED.get(normalized)
    if entry:
        return str(entry.get("language") or LANGUAGE_UNKNOWN)
    folded = normalize_keyword_text(_ascii_fold(normalized))
    entry = _KEYWORD_BY_NORMALIZED.get(folded)
    if entry:
        return str(entry.get("language") or LANGUAGE_UNKNOWN)
    return LANGUAGE_UNKNOWN


def classify_keyword_category(keyword: Any) -> str:
    normalized = normalize_keyword_text(keyword)
    entry = _KEYWORD_BY_NORMALIZED.get(normalized)
    if entry:
        return str(entry.get("category") or CATEGORY_UNKNOWN)
    folded = normalize_keyword_text(_ascii_fold(normalized))
    entry = _KEYWORD_BY_NORMALIZED.get(folded)
    if entry:
        return str(entry.get("category") or CATEGORY_UNKNOWN)
    return CATEGORY_UNKNOWN


def _text_contains_keyword(text: str, keyword: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", text, re.UNICODE) is not None


def _derive_center(start_seconds: float | None, end_seconds: float | None) -> float | None:
    if start_seconds is None or end_seconds is None:
        return None
    return (start_seconds + end_seconds) / 2.0


def find_keyword_emotion_matches(
    text: Any,
    start_seconds: float | None = None,
    end_seconds: float | None = None,
    source_segment_index: int | None = None,
) -> list[KeywordEmotionMatch]:
    raw_text = "" if text is None else str(text)
    normalized_text = normalize_keyword_text(raw_text)
    folded_text = normalize_keyword_text(_ascii_fold(normalized_text))
    if not normalized_text:
        return []

    matches: list[KeywordEmotionMatch] = []
    matched_spans: set[str] = set()
    center_seconds = _derive_center(start_seconds, end_seconds)

    for entry in _KEYWORD_ENTRIES:
        normalized_keyword = str(entry["normalized"])
        haystack = folded_text if normalized_keyword not in normalized_text else normalized_text
        if not _text_contains_keyword(haystack, normalized_keyword):
            continue
        if normalized_keyword in matched_spans:
            continue
        matched_spans.add(normalized_keyword)

        category = str(entry["category"])
        language = str(entry["language"])
        match = KeywordEmotionMatch(
            match_id=f"keyword_emotion_{source_segment_index if source_segment_index is not None else 0}_{len(matches)}",
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            center_seconds=center_seconds,
            text=raw_text.strip(),
            matched_keyword=str(entry["keyword"]),
            normalized_keyword=normalized_keyword,
            category=category,
            language=language,
            intensity=_clamp(entry.get("intensity"), 0.5),
            confidence=_clamp(entry.get("confidence"), 0.7),
            source_segment_index=source_segment_index,
            metadata={"source": "keyword_emotion_lexicon"},
        )
        matches.append(match)

    return matches


def _category_scores(matches: list[KeywordEmotionMatch]) -> dict[str, float]:
    scores: dict[str, float] = {}
    for match in matches:
        score = _clamp((match.intensity + match.confidence) / 2.0)
        scores[match.category] = max(scores.get(match.category, 0.0), score)
    return scores


def _dominant_category(categories: dict[str, float]) -> str:
    if not categories:
        return CATEGORY_NEUTRAL
    category, score = max(categories.items(), key=lambda item: item[1])
    return category if score > 0.0 else CATEGORY_NEUTRAL


def _recommendation_for_segment(
    overall_score: float,
    dominant_category: str,
    categories: dict[str, float],
) -> str:
    if overall_score >= 0.6:
        return "review_high_value_keyword_segment"
    if categories.get(CATEGORY_QUESTION, 0.0) > 0.0:
        return "review_question_context"
    if dominant_category == CATEGORY_FRUSTRATION:
        return "review_frustration_moment"
    if dominant_category == CATEGORY_LAUGH:
        return "review_comedy_moment"
    return "no_keyword_priority"


def score_keyword_emotion_segment(
    segment: Any,
    source_index: int = 0,
    metadata: dict[str, Any] | None = None,
) -> KeywordEmotionSegmentScore:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}
    segment_dict = dict(segment) if isinstance(segment, dict) else {}
    warnings = [str(item) for item in segment_dict.get("warnings", []) or []]
    errors = [str(item) for item in segment_dict.get("errors", []) or []]

    text = str(segment_dict.get("text") or "").strip()
    start_seconds = _safe_float(segment_dict.get("start_seconds"))
    end_seconds = _safe_float(segment_dict.get("end_seconds"))
    duration_seconds = _safe_float(segment_dict.get("duration_seconds"))
    if duration_seconds is None and start_seconds is not None and end_seconds is not None:
        duration_seconds = max(0.0, end_seconds - start_seconds)

    if not segment_dict.get("is_valid", False):
        warnings.append("invalid_transcript_segment")

    matches = find_keyword_emotion_matches(
        text,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        source_segment_index=source_index,
    )
    categories = _category_scores(matches)
    dominant_category = _dominant_category(categories)

    hype_score = categories.get(CATEGORY_HYPE, 0.0)
    frustration_score = categories.get(CATEGORY_FRUSTRATION, 0.0)
    shock_score = categories.get(CATEGORY_SHOCK, 0.0)
    laugh_score = categories.get(CATEGORY_LAUGH, 0.0)
    question_score = categories.get(CATEGORY_QUESTION, 0.0)
    callout_score = categories.get(CATEGORY_CALLOUT, 0.0)
    gameplay_score = categories.get(CATEGORY_GAMEPLAY, 0.0)

    overall_keyword_score = _clamp(
        (hype_score * _CATEGORY_WEIGHTS[CATEGORY_HYPE])
        + (shock_score * _CATEGORY_WEIGHTS[CATEGORY_SHOCK])
        + (laugh_score * _CATEGORY_WEIGHTS[CATEGORY_LAUGH])
        + (frustration_score * _CATEGORY_WEIGHTS[CATEGORY_FRUSTRATION])
        + (max(question_score, callout_score) * _CATEGORY_WEIGHTS[CATEGORY_QUESTION])
        + (gameplay_score * 0.15)
    )
    if len(matches) > 1:
        overall_keyword_score = _clamp(overall_keyword_score + min(0.25, len(matches) * 0.04))

    emotion_score = _clamp(
        max(hype_score, frustration_score, shock_score, laugh_score, gameplay_score)
    )

    return KeywordEmotionSegmentScore(
        segment_id=f"keyword_emotion_segment_{source_index}",
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        duration_seconds=duration_seconds,
        text=text,
        categories=categories,
        dominant_category=dominant_category,
        emotion_score=round(emotion_score, 6),
        hype_score=round(hype_score, 6),
        frustration_score=round(frustration_score, 6),
        shock_score=round(shock_score, 6),
        laugh_score=round(laugh_score, 6),
        question_score=round(question_score, 6),
        overall_keyword_score=round(overall_keyword_score, 6),
        match_count=len(matches),
        recommendation=_recommendation_for_segment(
            overall_keyword_score,
            dominant_category,
            categories,
        ),
        metadata={
            **safe_metadata,
            "source_index": source_index,
            "match_ids": [match.match_id for match in matches],
        },
        warnings=sorted(set(warnings)),
        errors=sorted(set(errors)),
    )


def build_keyword_emotion_result(
    segment_scores: list[KeywordEmotionSegmentScore],
    matches: list[KeywordEmotionMatch],
    metadata: dict[str, Any] | None = None,
) -> KeywordEmotionResult:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}
    warnings = sorted(
        set(warning for score in segment_scores for warning in list(score.warnings or []))
    )
    errors = sorted(
        set(error for score in segment_scores for error in list(score.errors or []))
    )

    hype_match_count = sum(1 for match in matches if match.category == CATEGORY_HYPE)
    frustration_match_count = sum(
        1 for match in matches if match.category == CATEGORY_FRUSTRATION
    )
    shock_match_count = sum(1 for match in matches if match.category == CATEGORY_SHOCK)
    laugh_match_count = sum(1 for match in matches if match.category == CATEGORY_LAUGH)
    question_match_count = sum(
        1 for match in matches if match.category == CATEGORY_QUESTION
    )
    high_value_segment_count = sum(
        1 for score in segment_scores if score.overall_keyword_score >= 0.6
    )

    if errors or warnings:
        status = STATUS_COMPLETED_WITH_WARNINGS
        recommendation = "review_keyword_emotion_warnings"
    elif matches:
        status = STATUS_OK
        recommendation = "use_keyword_emotion_scoring"
    else:
        status = STATUS_OK
        recommendation = "no_keyword_priority"

    return KeywordEmotionResult(
        status=status,
        matches=matches,
        segment_scores=segment_scores,
        match_count=len(matches),
        segment_score_count=len(segment_scores),
        hype_match_count=hype_match_count,
        frustration_match_count=frustration_match_count,
        shock_match_count=shock_match_count,
        laugh_match_count=laugh_match_count,
        question_match_count=question_match_count,
        high_value_segment_count=high_value_segment_count,
        recommendation=recommendation,
        warnings=warnings,
        errors=errors,
        metadata=safe_metadata,
    )


def score_keyword_emotions(
    transcript_segments: Any,
    metadata: dict[str, Any] | None = None,
) -> KeywordEmotionResult:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}

    if not transcript_segments:
        return KeywordEmotionResult(
            status=STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS,
            recommendation="keyword_emotion_skipped_no_transcript",
            warnings=["no_transcript_segments_available"],
            metadata=safe_metadata,
        )

    try:
        normalization_result = normalize_transcript_segments(
            transcript_segments,
            metadata={"stage": safe_metadata.get("stage")},
        )
        normalized_segments = list(normalization_result.segments)

        if not normalized_segments:
            return KeywordEmotionResult(
                status=STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS,
                recommendation="keyword_emotion_skipped_no_transcript",
                warnings=list(normalization_result.warnings or [])
                + ["no_transcript_segments_available"],
                errors=list(normalization_result.errors or []),
                metadata=safe_metadata,
            )

        segment_scores: list[KeywordEmotionSegmentScore] = []
        matches: list[KeywordEmotionMatch] = []
        for index, segment in enumerate(normalized_segments):
            score = score_keyword_emotion_segment(
                segment,
                source_index=index,
                metadata=safe_metadata,
            )
            segment_scores.append(score)
            matches.extend(
                find_keyword_emotion_matches(
                    score.text,
                    start_seconds=score.start_seconds,
                    end_seconds=score.end_seconds,
                    source_segment_index=index,
                )
            )

        result = build_keyword_emotion_result(
            segment_scores=segment_scores,
            matches=matches,
            metadata={
                **safe_metadata,
                "normalization_status": normalization_result.status,
                "normalization_recommendation": normalization_result.recommendation,
            },
        )
        result.warnings = sorted(
            set(list(result.warnings) + list(normalization_result.warnings or []))
        )
        result.errors = sorted(
            set(list(result.errors) + list(normalization_result.errors or []))
        )
        if result.warnings or result.errors or normalization_result.status != "ok":
            result.status = STATUS_COMPLETED_WITH_WARNINGS
            if result.recommendation == "use_keyword_emotion_scoring":
                result.recommendation = "review_keyword_emotion_warnings"
        return result

    except Exception as exc:
        return KeywordEmotionResult(
            status=STATUS_FAILED,
            recommendation="keyword_emotion_failed",
            errors=[f"keyword_emotion_scoring_failed:{exc}"],
            metadata=safe_metadata,
        )
