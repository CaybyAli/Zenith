from __future__ import annotations

import re
from typing import Any

from core.transcript_segment_normalizer import normalize_transcript_segments
from models.sentence_boundary import (
    BOUNDARY_ANSWER_CANDIDATE,
    BOUNDARY_OPEN_FRAGMENT,
    BOUNDARY_OPEN_QUESTION,
    BOUNDARY_QUESTION,
    BOUNDARY_SAFE_SENTENCE,
    BOUNDARY_UNKNOWN,
    PROTECTION_HARD,
    PROTECTION_NONE,
    PROTECTION_REVIEW,
    PROTECTION_SOFT,
    STATUS_COMPLETED_WITH_WARNINGS,
    STATUS_FAILED,
    STATUS_OK,
    STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS,
    ZONE_PROTECT_ANSWER_CONTEXT,
    ZONE_PROTECT_OPEN_FRAGMENT,
    ZONE_PROTECT_QUESTION_CONTEXT,
    ZONE_REVIEW_BOUNDARY,
    SentenceBoundaryPoint,
    SentenceBoundaryProtectionZone,
    SentenceBoundaryResult,
)


_END_PUNCTUATION = (".", "!", "?", "...")
_QUESTION_WORDS = {
    "wer",
    "was",
    "wann",
    "wo",
    "warum",
    "wieso",
    "wie",
    "welcher",
    "welche",
    "who",
    "what",
    "when",
    "where",
    "why",
    "how",
    "kim",
    "ne",
    "nerede",
    "neden",
    "nasil",
    "nasıl",
}
_OPEN_CONNECTORS = {
    "und",
    "aber",
    "weil",
    "dass",
    "wenn",
    "obwohl",
    "dann",
    "also",
    "and",
    "but",
    "because",
    "if",
    "so",
}
_TYPICAL_CLOSINGS = {
    "okay",
    "ok",
    "genau",
    "ja",
    "nein",
    "yes",
    "no",
    "done",
    "fertig",
}


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return bool(value)


def _safe_list(value: Any) -> list:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _word_tokens(text: str) -> list[str]:
    return re.findall(r"[\wÄÖÜäöüßÇĞİÖŞÜçğıöşü]+", text.lower(), re.UNICODE)


def normalize_sentence_boundary_text(text: Any) -> str:
    if text is None:
        return ""
    try:
        value = str(text)
    except Exception:
        return ""
    return " ".join(value.replace("\n", " ").replace("\r", " ").split()).strip()


def is_question_text(text: Any) -> bool:
    normalized = normalize_sentence_boundary_text(text)
    if not normalized:
        return False

    if normalized.endswith("?"):
        return True

    tokens = _word_tokens(normalized)
    return bool(tokens and tokens[0] in _QUESTION_WORDS)


def is_sentence_complete(text: Any) -> bool:
    normalized = normalize_sentence_boundary_text(text)
    if not normalized:
        return False

    tokens = _word_tokens(normalized)
    if len(tokens) < 2 and len(normalized) < 6:
        return False

    if normalized.endswith(_END_PUNCTUATION) or normalized.endswith("…"):
        return True

    return bool(tokens and tokens[-1] in _TYPICAL_CLOSINGS and len(tokens) >= 2)


def classify_sentence_text(text: Any) -> dict[str, Any]:
    normalized = normalize_sentence_boundary_text(text)
    tokens = _word_tokens(normalized)
    warnings: list[str] = []

    if not normalized:
        return {
            "boundary_type": BOUNDARY_UNKNOWN,
            "protection_level": PROTECTION_REVIEW,
            "is_complete_sentence": False,
            "is_question": False,
            "is_answer_candidate": False,
            "is_open_fragment": True,
            "confidence": 0.2,
            "recommendation": "review_empty_sentence_boundary",
            "warnings": ["empty_sentence_text"],
        }

    is_question = is_question_text(normalized)
    is_complete = is_sentence_complete(normalized)
    ends_with_connector = bool(tokens and tokens[-1] in _OPEN_CONNECTORS)
    very_short = len(tokens) <= 2 and not is_complete

    if is_question and is_complete:
        return {
            "boundary_type": BOUNDARY_QUESTION,
            "protection_level": PROTECTION_SOFT,
            "is_complete_sentence": True,
            "is_question": True,
            "is_answer_candidate": False,
            "is_open_fragment": False,
            "confidence": 0.86,
            "recommendation": "protect_question_context",
            "warnings": warnings,
        }

    if is_question:
        return {
            "boundary_type": BOUNDARY_OPEN_QUESTION,
            "protection_level": PROTECTION_HARD,
            "is_complete_sentence": False,
            "is_question": True,
            "is_answer_candidate": False,
            "is_open_fragment": True,
            "confidence": 0.78,
            "recommendation": "protect_open_question_context",
            "warnings": warnings,
        }

    if is_complete and not ends_with_connector:
        return {
            "boundary_type": BOUNDARY_SAFE_SENTENCE,
            "protection_level": PROTECTION_NONE,
            "is_complete_sentence": True,
            "is_question": False,
            "is_answer_candidate": False,
            "is_open_fragment": False,
            "confidence": 0.82,
            "recommendation": "boundary_safe_for_review",
            "warnings": warnings,
        }

    if ends_with_connector:
        warnings.append("sentence_ends_with_connector")

    return {
        "boundary_type": BOUNDARY_OPEN_FRAGMENT,
        "protection_level": PROTECTION_HARD if not very_short else PROTECTION_REVIEW,
        "is_complete_sentence": False,
        "is_question": False,
        "is_answer_candidate": False,
        "is_open_fragment": True,
        "confidence": 0.74 if not very_short else 0.55,
        "recommendation": "protect_open_sentence_fragment",
        "warnings": warnings,
    }


def build_sentence_boundary_points(
    normalized_segments: list[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> list[SentenceBoundaryPoint]:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}
    boundaries: list[SentenceBoundaryPoint] = []
    previous_was_question = False
    previous_question_end: float | None = None

    for index, segment in enumerate(normalized_segments):
        segment_dict = dict(segment) if isinstance(segment, dict) else {}
        text = normalize_sentence_boundary_text(segment_dict.get("text"))
        classification = classify_sentence_text(text)
        warnings = [str(item) for item in _safe_list(classification.get("warnings"))]
        errors = [str(item) for item in _safe_list(segment_dict.get("errors"))]

        start_seconds = _safe_float(segment_dict.get("start_seconds"))
        end_seconds = _safe_float(segment_dict.get("end_seconds"))
        duration_seconds = _safe_float(segment_dict.get("duration_seconds"))
        if duration_seconds is None and start_seconds is not None and end_seconds is not None:
            duration_seconds = max(0.0, end_seconds - start_seconds)

        center_seconds = None
        if start_seconds is not None and end_seconds is not None:
            center_seconds = (start_seconds + end_seconds) / 2.0

        segment_is_valid = _safe_bool(segment_dict.get("is_valid"), False)
        if not segment_is_valid:
            warnings.append("invalid_transcript_segment")
            classification["boundary_type"] = BOUNDARY_OPEN_FRAGMENT
            classification["protection_level"] = PROTECTION_REVIEW
            classification["is_complete_sentence"] = False
            classification["is_open_fragment"] = True
            classification["confidence"] = min(
                float(classification.get("confidence", 0.4) or 0.4),
                0.45,
            )
            classification["recommendation"] = "review_invalid_transcript_segment"

        is_answer_candidate = False
        if previous_was_question and start_seconds is not None:
            if previous_question_end is None or start_seconds - previous_question_end <= 5.0:
                is_answer_candidate = True

        boundary_type = str(classification.get("boundary_type") or BOUNDARY_UNKNOWN)
        if is_answer_candidate and boundary_type not in {BOUNDARY_QUESTION, BOUNDARY_OPEN_QUESTION}:
            boundary_type = BOUNDARY_ANSWER_CANDIDATE

        boundary = SentenceBoundaryPoint(
            boundary_id=f"sentence_boundary_{index}",
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            center_seconds=center_seconds,
            text=text,
            normalized_text=text.lower(),
            boundary_type=boundary_type,
            protection_level=str(
                classification.get("protection_level") or PROTECTION_REVIEW
            ),
            is_complete_sentence=bool(classification.get("is_complete_sentence", False)),
            is_question=bool(classification.get("is_question", False)),
            is_answer_candidate=is_answer_candidate,
            is_open_fragment=bool(classification.get("is_open_fragment", False)),
            confidence=float(classification.get("confidence", 0.0) or 0.0),
            recommendation=str(
                classification.get("recommendation") or "review_sentence_boundary"
            ),
            source_segment_index=int(segment_dict.get("source_index", index) or 0),
            metadata={
                "duration_seconds": duration_seconds,
                "segment_is_valid": segment_is_valid,
                "stage": safe_metadata.get("stage"),
                "source_segment": segment_dict,
            },
            warnings=sorted(set(warnings)),
            errors=sorted(set(errors)),
        )
        boundaries.append(boundary)

        previous_was_question = boundary.is_question
        previous_question_end = end_seconds if boundary.is_question else previous_question_end

    return boundaries


def _zone_duration(start_seconds: float | None, end_seconds: float | None) -> float | None:
    if start_seconds is None or end_seconds is None:
        return None
    return max(0.0, end_seconds - start_seconds)


def build_sentence_protection_zones(
    boundaries: list[SentenceBoundaryPoint],
    metadata: dict[str, Any] | None = None,
) -> list[SentenceBoundaryProtectionZone]:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}
    zones: list[SentenceBoundaryProtectionZone] = []

    for index, boundary in enumerate(boundaries):
        if boundary.boundary_type in {BOUNDARY_OPEN_FRAGMENT, BOUNDARY_OPEN_QUESTION} or (
            boundary.is_open_fragment and not boundary.is_question
        ):
            zone_type = (
                ZONE_PROTECT_QUESTION_CONTEXT
                if boundary.boundary_type == BOUNDARY_OPEN_QUESTION
                else ZONE_PROTECT_OPEN_FRAGMENT
            )
            zones.append(
                SentenceBoundaryProtectionZone(
                    zone_id=f"sentence_zone_{len(zones)}",
                    start_seconds=boundary.start_seconds,
                    end_seconds=boundary.end_seconds,
                    duration_seconds=_zone_duration(
                        boundary.start_seconds,
                        boundary.end_seconds,
                    ),
                    zone_type=zone_type,
                    protection_level=boundary.protection_level,
                    reason=boundary.recommendation,
                    confidence=boundary.confidence,
                    source_boundary_ids=[boundary.boundary_id],
                    metadata={
                        "stage": safe_metadata.get("stage"),
                        "source_boundary_type": boundary.boundary_type,
                    },
                    warnings=list(boundary.warnings),
                    errors=list(boundary.errors),
                )
            )

        if boundary.boundary_type == BOUNDARY_QUESTION:
            start = boundary.start_seconds
            end = boundary.end_seconds
            source_ids = [boundary.boundary_id]
            if index + 1 < len(boundaries):
                next_boundary = boundaries[index + 1]
                source_ids.append(next_boundary.boundary_id)
                if end is None or (
                    next_boundary.end_seconds is not None
                    and next_boundary.end_seconds > end
                ):
                    end = next_boundary.end_seconds
            elif end is not None:
                end = end + 1.5

            zones.append(
                SentenceBoundaryProtectionZone(
                    zone_id=f"sentence_zone_{len(zones)}",
                    start_seconds=start,
                    end_seconds=end,
                    duration_seconds=_zone_duration(start, end),
                    zone_type=ZONE_PROTECT_QUESTION_CONTEXT,
                    protection_level=PROTECTION_SOFT,
                    reason="question_context_should_be_preserved",
                    confidence=boundary.confidence,
                    source_boundary_ids=source_ids,
                    metadata={
                        "stage": safe_metadata.get("stage"),
                        "source_boundary_type": boundary.boundary_type,
                    },
                    warnings=list(boundary.warnings),
                    errors=list(boundary.errors),
                )
            )

        if boundary.is_answer_candidate:
            zones.append(
                SentenceBoundaryProtectionZone(
                    zone_id=f"sentence_zone_{len(zones)}",
                    start_seconds=boundary.start_seconds,
                    end_seconds=boundary.end_seconds,
                    duration_seconds=_zone_duration(
                        boundary.start_seconds,
                        boundary.end_seconds,
                    ),
                    zone_type=ZONE_PROTECT_ANSWER_CONTEXT,
                    protection_level=PROTECTION_SOFT,
                    reason="answer_candidate_context_should_be_reviewed",
                    confidence=boundary.confidence,
                    source_boundary_ids=[boundary.boundary_id],
                    metadata={
                        "stage": safe_metadata.get("stage"),
                        "source_boundary_type": boundary.boundary_type,
                    },
                    warnings=list(boundary.warnings),
                    errors=list(boundary.errors),
                )
            )

        if boundary.protection_level == PROTECTION_REVIEW:
            zones.append(
                SentenceBoundaryProtectionZone(
                    zone_id=f"sentence_zone_{len(zones)}",
                    start_seconds=boundary.start_seconds,
                    end_seconds=boundary.end_seconds,
                    duration_seconds=_zone_duration(
                        boundary.start_seconds,
                        boundary.end_seconds,
                    ),
                    zone_type=ZONE_REVIEW_BOUNDARY,
                    protection_level=PROTECTION_REVIEW,
                    reason="sentence_boundary_needs_review",
                    confidence=boundary.confidence,
                    source_boundary_ids=[boundary.boundary_id],
                    metadata={
                        "stage": safe_metadata.get("stage"),
                        "source_boundary_type": boundary.boundary_type,
                    },
                    warnings=list(boundary.warnings),
                    errors=list(boundary.errors),
                )
            )

    return zones


def analyze_sentence_boundaries(
    transcript_segments: Any,
    metadata: dict[str, Any] | None = None,
) -> SentenceBoundaryResult:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}

    if not transcript_segments:
        return SentenceBoundaryResult(
            status=STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS,
            recommendation="sentence_boundary_skipped_no_transcript",
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
            return SentenceBoundaryResult(
                status=STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS,
                recommendation="sentence_boundary_skipped_no_transcript",
                warnings=list(normalization_result.warnings or [])
                + ["no_transcript_segments_available"],
                errors=list(normalization_result.errors or []),
                metadata=safe_metadata,
            )

        boundaries = build_sentence_boundary_points(
            normalized_segments,
            metadata=safe_metadata,
        )
        zones = build_sentence_protection_zones(boundaries, metadata=safe_metadata)

        warnings = sorted(
            set(
                list(normalization_result.warnings or [])
                + [
                    warning
                    for boundary in boundaries
                    for warning in list(boundary.warnings or [])
                ]
            )
        )
        errors = sorted(
            set(
                list(normalization_result.errors or [])
                + [
                    error
                    for boundary in boundaries
                    for error in list(boundary.errors or [])
                ]
            )
        )

        complete_sentence_count = sum(1 for item in boundaries if item.is_complete_sentence)
        open_fragment_count = sum(1 for item in boundaries if item.is_open_fragment)
        question_count = sum(1 for item in boundaries if item.is_question)
        open_question_count = sum(
            1 for item in boundaries if item.boundary_type == BOUNDARY_OPEN_QUESTION
        )
        safe_boundary_count = sum(
            1 for item in boundaries if item.boundary_type == BOUNDARY_SAFE_SENTENCE
        )
        unsafe_boundary_count = sum(
            1
            for item in boundaries
            if item.boundary_type in {BOUNDARY_OPEN_FRAGMENT, BOUNDARY_OPEN_QUESTION}
            or item.is_open_fragment
        )

        if errors or warnings or normalization_result.status == "completed_with_warnings":
            status = STATUS_COMPLETED_WITH_WARNINGS
            recommendation = "review_sentence_boundary_warnings"
        else:
            status = STATUS_OK
            recommendation = "use_sentence_boundary_protection"

        return SentenceBoundaryResult(
            status=status,
            boundaries=boundaries,
            protection_zones=zones,
            boundary_count=len(boundaries),
            protection_zone_count=len(zones),
            complete_sentence_count=complete_sentence_count,
            open_fragment_count=open_fragment_count,
            question_count=question_count,
            open_question_count=open_question_count,
            safe_boundary_count=safe_boundary_count,
            unsafe_boundary_count=unsafe_boundary_count,
            recommendation=recommendation,
            warnings=warnings,
            errors=errors,
            metadata={
                **safe_metadata,
                "normalization_status": normalization_result.status,
                "normalization_recommendation": normalization_result.recommendation,
            },
        )

    except Exception as exc:
        return SentenceBoundaryResult(
            status=STATUS_FAILED,
            recommendation="sentence_boundary_failed",
            errors=[f"sentence_boundary_analysis_failed:{exc}"],
            metadata=safe_metadata,
        )
