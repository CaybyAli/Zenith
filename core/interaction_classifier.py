from __future__ import annotations

import re
import unicodedata
from typing import Any

from models.interaction_classification import (
    INTERACTION_TYPE_CALLOUT,
    INTERACTION_TYPE_CHAT_REACTION,
    INTERACTION_TYPE_COMMENTARY,
    INTERACTION_TYPE_INTERACTION,
    INTERACTION_TYPE_MONOLOGUE,
    INTERACTION_TYPE_PRIVATE_OR_META_CANDIDATE,
    INTERACTION_TYPE_QUESTION_ANSWER,
    INTERACTION_TYPE_UNKNOWN,
    STATUS_COMPLETED_WITH_WARNINGS,
    STATUS_OK,
    STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS,
    InteractionClassificationPoint,
    InteractionClassificationResult,
    InteractionSegmentClassification,
)


_MONOLOGUE_TERMS = {
    "ich",
    "wir",
    "jetzt",
    "hier",
    "okay",
    "also",
    "gerade",
    "einfach",
}
_GAMEPLAY_TERMS = {
    "game",
    "gameplay",
    "runde",
    "match",
    "gegner",
    "team",
    "tor",
    "kill",
    "zone",
    "loot",
    "damage",
    "spieler",
}
_INTERACTION_TERMS = {
    "du",
    "dir",
    "dich",
    "dein",
    "deine",
    "ihr",
    "euch",
    "nils",
    "bruder",
    "bro",
    "digga",
    "komm",
    "mach",
    "guck",
    "hoer",
    "hor",
    "warte",
}
_QUESTION_TERMS = {
    "wer",
    "was",
    "wo",
    "wie",
    "warum",
    "wieso",
    "weshalb",
    "wann",
    "welche",
    "welcher",
    "welches",
    "kannst",
    "kann",
    "koennen",
    "konnen",
    "hast",
    "habt",
    "ist",
}
_CHAT_TERMS = {
    "chat",
    "leute",
    "jungs",
    "community",
    "kommentar",
    "kommentare",
    "viewer",
    "zuschauer",
    "schreibt",
    "meint",
}
_CHAT_PHRASES = {
    "im chat",
    "sag mal",
    "was meint ihr",
    "schreibt mal",
}
_CALLOUT_TERMS = {
    "links",
    "rechts",
    "oben",
    "unten",
    "pass",
    "auf",
    "push",
    "drop",
    "go",
    "komm",
    "rush",
    "flash",
    "cover",
}
_CALLOUT_PHRASES = {
    "hinter dir",
    "pass auf",
    "geh rein",
    "kommt rein",
}
_PRIVATE_META_PHRASES = {
    "nicht reinschneiden",
    "schneid das raus",
    "ich muss kurz",
    "warte kurz",
    "technisches problem",
}
_PRIVATE_META_TERMS = {
    "aufnahme",
    "recording",
    "stream",
    "discord",
    "privat",
    "offline",
}

_RECOMMENDATIONS = {
    INTERACTION_TYPE_MONOLOGUE: "keep_commentary_context",
    INTERACTION_TYPE_INTERACTION: "review_interaction_context",
    INTERACTION_TYPE_QUESTION_ANSWER: "protect_question_answer_context",
    INTERACTION_TYPE_CHAT_REACTION: "review_chat_reaction_context",
    INTERACTION_TYPE_CALLOUT: "review_gameplay_callout",
    INTERACTION_TYPE_COMMENTARY: "keep_commentary_context",
    INTERACTION_TYPE_PRIVATE_OR_META_CANDIDATE: "review_private_or_meta_candidate",
    INTERACTION_TYPE_UNKNOWN: "review_unknown_interaction_type",
}


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _safe_float_or_none(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_text_from_segment(segment: Any) -> str:
    if isinstance(segment, dict):
        return str(segment.get("text") or segment.get("transcript") or "")
    return str(getattr(segment, "text", "") or "")


def _segment_value(segment: Any, *names: str) -> Any:
    if isinstance(segment, dict):
        for name in names:
            if name in segment:
                return segment.get(name)
        return None
    for name in names:
        if hasattr(segment, name):
            return getattr(segment, name)
    return None


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text))


def _contains_phrase(text: str, phrases: set[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, value))


def _score_from_hits(hits: int, base: float = 0.0, step: float = 0.22) -> float:
    return _clamp(base + hits * step)


def _duration(start: float | None, end: float | None) -> float | None:
    if start is None or end is None:
        return None
    return max(0.0, end - start)


def _center(start: float | None, end: float | None) -> float | None:
    if start is None or end is None:
        return None
    return (start + end) / 2.0


def normalize_interaction_text(text: Any) -> str:
    value = " ".join(str(text or "").strip().lower().split())
    normalized = unicodedata.normalize("NFKD", value)
    without_marks = "".join(
        char for char in normalized if not unicodedata.combining(char)
    )
    return without_marks.replace("ß", "ss")


def score_interaction_features(text: Any) -> dict[str, Any]:
    original_text = str(text or "")
    normalized = normalize_interaction_text(original_text)
    tokens = _tokens(normalized)

    monologue_hits = len(tokens & _MONOLOGUE_TERMS)
    gameplay_hits = len(tokens & _GAMEPLAY_TERMS)
    interaction_hits = len(tokens & _INTERACTION_TERMS)
    question_hits = len(tokens & _QUESTION_TERMS)
    chat_hits = len(tokens & _CHAT_TERMS)
    callout_hits = len(tokens & _CALLOUT_TERMS)
    private_hits = len(tokens & _PRIVATE_META_TERMS)

    has_chat_phrase = _contains_phrase(normalized, _CHAT_PHRASES)
    has_callout_phrase = _contains_phrase(normalized, _CALLOUT_PHRASES)
    has_private_phrase = _contains_phrase(normalized, _PRIVATE_META_PHRASES)
    has_question_mark = "?" in original_text
    is_short_direct_address = len(tokens) <= 4 and interaction_hits > 0

    is_question = has_question_mark or (
        question_hits > 0
        and (interaction_hits > 0 or normalized.endswith("?"))
    )

    return {
        "normalized_text": normalized,
        "monologue_score": _score_from_hits(monologue_hits, base=0.18),
        "interaction_score": _score_from_hits(interaction_hits, base=0.05),
        "question_answer_score": _clamp(
            (0.58 if is_question else 0.0) + min(0.24, question_hits * 0.08)
        ),
        "chat_reaction_score": _clamp(
            _score_from_hits(chat_hits, base=0.0)
            + (0.36 if has_chat_phrase else 0.0)
        ),
        "callout_score": _clamp(
            _score_from_hits(callout_hits, base=0.0)
            + (0.34 if has_callout_phrase else 0.0)
        ),
        "commentary_score": _clamp(
            _score_from_hits(gameplay_hits, base=0.18)
            + (0.08 if monologue_hits else 0.0)
        ),
        "private_or_meta_score": _clamp(
            _score_from_hits(private_hits, base=0.0)
            + (0.52 if has_private_phrase else 0.0)
        ),
        "is_question": is_question,
        "is_chat_reaction_candidate": chat_hits > 0 or has_chat_phrase,
        "is_private_or_meta_candidate": private_hits > 0 or has_private_phrase,
        "is_short_direct_address": is_short_direct_address,
        "feature_hits": {
            "monologue": monologue_hits,
            "gameplay": gameplay_hits,
            "interaction": interaction_hits,
            "question": question_hits,
            "chat": chat_hits,
            "callout": callout_hits,
            "private_or_meta": private_hits,
            "chat_phrase": has_chat_phrase,
            "callout_phrase": has_callout_phrase,
            "private_or_meta_phrase": has_private_phrase,
            "question_mark": has_question_mark,
        },
    }


def _is_answer_candidate(
    segment: Any,
    previous_segment: Any | None,
    previous_classification: InteractionSegmentClassification | None = None,
) -> bool:
    if previous_segment is None and previous_classification is None:
        return False

    previous_question = False
    previous_end = None
    if previous_classification is not None:
        previous_question = (
            previous_classification.interaction_type
            == INTERACTION_TYPE_QUESTION_ANSWER
        ) or bool(previous_classification.metadata.get("is_question"))
        previous_end = previous_classification.end_seconds
    else:
        previous_features = score_interaction_features(
            _safe_text_from_segment(previous_segment)
        )
        previous_question = bool(previous_features["is_question"])
        previous_end = _safe_float_or_none(
            _segment_value(previous_segment, "end_seconds", "end", "end_time")
        )

    if not previous_question:
        return False

    current_start = _safe_float_or_none(
        _segment_value(segment, "start_seconds", "start", "start_time")
    )
    if previous_end is None or current_start is None:
        return True
    return 0.0 <= current_start - previous_end <= 5.0


def _sentence_boundary_context_needed(
    sentence_boundary: Any,
    source_index: int,
) -> bool:
    data = _safe_dict(sentence_boundary)
    if not data:
        return False
    if bool(data.get("context_needed")):
        return True
    boundary_type = str(data.get("boundary_type") or data.get("sentence_type") or "")
    if "open" in boundary_type or "fragment" in boundary_type:
        return True
    if bool(data.get("is_open_fragment")) or bool(data.get("open_fragment")):
        return True

    boundaries = data.get("boundaries")
    if isinstance(boundaries, list):
        for item in boundaries:
            if not isinstance(item, dict):
                continue
            item_index = item.get("source_segment_index")
            if item_index is not None and int(item_index) != source_index:
                continue
            item_type = str(item.get("boundary_type") or "")
            if "open" in item_type or "fragment" in item_type:
                return True
    return False


def _keyword_metadata_for_segment(keyword_emotion: Any) -> dict[str, Any]:
    data = _safe_dict(keyword_emotion)
    if not data:
        return {}
    return {
        "keyword_emotion_status": data.get("status"),
        "keyword_emotion_recommendation": data.get("recommendation"),
    }


def _select_interaction_type(
    features: dict[str, Any],
    answer_candidate: bool,
) -> tuple[str, float]:
    scores = {
        INTERACTION_TYPE_PRIVATE_OR_META_CANDIDATE: float(
            features["private_or_meta_score"]
        ),
        INTERACTION_TYPE_CHAT_REACTION: float(features["chat_reaction_score"]),
        INTERACTION_TYPE_QUESTION_ANSWER: float(features["question_answer_score"]),
        INTERACTION_TYPE_CALLOUT: float(features["callout_score"]),
        INTERACTION_TYPE_INTERACTION: float(features["interaction_score"]),
        INTERACTION_TYPE_COMMENTARY: float(features["commentary_score"]),
        INTERACTION_TYPE_MONOLOGUE: float(features["monologue_score"]),
    }
    if answer_candidate:
        scores[INTERACTION_TYPE_QUESTION_ANSWER] = max(
            scores[INTERACTION_TYPE_QUESTION_ANSWER],
            0.64,
        )

    priority = [
        INTERACTION_TYPE_PRIVATE_OR_META_CANDIDATE,
        INTERACTION_TYPE_CHAT_REACTION,
        INTERACTION_TYPE_QUESTION_ANSWER,
        INTERACTION_TYPE_CALLOUT,
        INTERACTION_TYPE_INTERACTION,
        INTERACTION_TYPE_COMMENTARY,
        INTERACTION_TYPE_MONOLOGUE,
    ]
    best_type = max(priority, key=lambda item: (scores[item], -priority.index(item)))
    best_score = scores[best_type]
    if best_score <= 0.0:
        return INTERACTION_TYPE_UNKNOWN, 0.0
    if best_type == INTERACTION_TYPE_MONOLOGUE and best_score < 0.18:
        return INTERACTION_TYPE_UNKNOWN, best_score
    return best_type, _clamp(max(0.45, best_score))


def classify_interaction_segment(
    segment: Any,
    previous_segment: Any | None = None,
    next_segment: Any | None = None,
    sentence_boundary: Any | None = None,
    keyword_emotion: Any | None = None,
    source_index: int = 0,
    metadata: dict[str, Any] | None = None,
) -> InteractionSegmentClassification:
    del next_segment
    warnings: list[str] = []
    errors: list[str] = []
    text = _safe_text_from_segment(segment)
    normalized_text = normalize_interaction_text(text)

    start = _safe_float_or_none(
        _segment_value(segment, "start_seconds", "start", "start_time")
    )
    end = _safe_float_or_none(_segment_value(segment, "end_seconds", "end", "end_time"))
    duration = _safe_float_or_none(_segment_value(segment, "duration_seconds", "duration"))
    if duration is None:
        duration = _duration(start, end)

    segment_id = str(
        _segment_value(segment, "segment_id", "id", "transcript_segment_id")
        or f"interaction_segment_{source_index}"
    )

    if not text.strip():
        warnings.append("empty_transcript_segment_text")

    features = score_interaction_features(text)
    answer_candidate = _is_answer_candidate(segment, previous_segment)
    interaction_type, confidence = _select_interaction_type(features, answer_candidate)
    context_needed = (
        bool(features["is_question"])
        or answer_candidate
        or interaction_type == INTERACTION_TYPE_INTERACTION
        or interaction_type == INTERACTION_TYPE_PRIVATE_OR_META_CANDIDATE
        or _sentence_boundary_context_needed(sentence_boundary, source_index)
        or bool(features["is_short_direct_address"])
    )

    safe_metadata = dict(metadata or {})
    safe_metadata.update(
        {
            "normalized_text": normalized_text,
            "source_segment_index": source_index,
            "is_question": bool(features["is_question"]),
            "is_answer_candidate": answer_candidate,
            "is_chat_reaction_candidate": bool(
                features["is_chat_reaction_candidate"]
            ),
            "is_private_or_meta_candidate": bool(
                features["is_private_or_meta_candidate"]
            ),
            "feature_hits": dict(features["feature_hits"]),
            "sentence_boundary_context_needed": _sentence_boundary_context_needed(
                sentence_boundary,
                source_index,
            ),
        }
    )
    safe_metadata.update(_keyword_metadata_for_segment(keyword_emotion))

    return InteractionSegmentClassification(
        segment_id=segment_id,
        start_seconds=start,
        end_seconds=end,
        duration_seconds=duration,
        text=text,
        interaction_type=interaction_type,
        confidence=confidence,
        monologue_score=float(features["monologue_score"]),
        interaction_score=float(features["interaction_score"]),
        question_answer_score=float(features["question_answer_score"]),
        chat_reaction_score=float(features["chat_reaction_score"]),
        callout_score=float(features["callout_score"]),
        commentary_score=float(features["commentary_score"]),
        private_or_meta_score=float(features["private_or_meta_score"]),
        context_needed=context_needed,
        recommendation=_RECOMMENDATIONS.get(
            interaction_type,
            "review_unknown_interaction_type",
        ),
        metadata=safe_metadata,
        warnings=warnings,
        errors=errors,
    )


def _point_from_classification(
    classification: InteractionSegmentClassification,
    source_index: int,
) -> InteractionClassificationPoint:
    metadata = dict(classification.metadata)
    return InteractionClassificationPoint(
        interaction_id=f"interaction_point_{source_index}_{classification.segment_id}",
        start_seconds=classification.start_seconds,
        end_seconds=classification.end_seconds,
        center_seconds=_center(
            classification.start_seconds,
            classification.end_seconds,
        ),
        text=classification.text,
        normalized_text=str(metadata.get("normalized_text") or ""),
        interaction_type=classification.interaction_type,
        confidence=classification.confidence,
        context_needed=classification.context_needed,
        is_question=bool(metadata.get("is_question")),
        is_answer_candidate=bool(metadata.get("is_answer_candidate")),
        is_chat_reaction_candidate=bool(metadata.get("is_chat_reaction_candidate")),
        is_private_or_meta_candidate=bool(
            metadata.get("is_private_or_meta_candidate")
        ),
        source_segment_index=source_index,
        metadata=metadata,
        warnings=list(classification.warnings),
        errors=list(classification.errors),
    )


def build_interaction_result(
    segment_classifications: list[InteractionSegmentClassification],
    points: list[InteractionClassificationPoint],
    metadata: dict[str, Any] | None = None,
) -> InteractionClassificationResult:
    warnings: list[str] = []
    errors: list[str] = []
    for classification in segment_classifications:
        warnings.extend(classification.warnings)
        errors.extend(classification.errors)
    for point in points:
        warnings.extend(point.warnings)
        errors.extend(point.errors)

    monologue_count = sum(
        1 for item in segment_classifications
        if item.interaction_type == INTERACTION_TYPE_MONOLOGUE
    )
    interaction_count = sum(
        1 for item in segment_classifications
        if item.interaction_type == INTERACTION_TYPE_INTERACTION
    )
    question_answer_count = sum(
        1 for item in segment_classifications
        if item.interaction_type == INTERACTION_TYPE_QUESTION_ANSWER
    )
    chat_reaction_count = sum(
        1 for item in segment_classifications
        if item.interaction_type == INTERACTION_TYPE_CHAT_REACTION
    )
    callout_count = sum(
        1 for item in segment_classifications
        if item.interaction_type == INTERACTION_TYPE_CALLOUT
    )
    commentary_count = sum(
        1 for item in segment_classifications
        if item.interaction_type == INTERACTION_TYPE_COMMENTARY
    )
    private_or_meta_count = sum(
        1 for item in segment_classifications
        if item.interaction_type == INTERACTION_TYPE_PRIVATE_OR_META_CANDIDATE
    )
    context_needed_count = sum(1 for item in segment_classifications if item.context_needed)

    if not segment_classifications:
        status = STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS
        recommendation = "interaction_classification_skipped_no_transcript"
    elif errors or warnings:
        status = STATUS_COMPLETED_WITH_WARNINGS
        recommendation = "review_interaction_classification_warnings"
    else:
        status = STATUS_OK
        recommendation = "use_interaction_classification_review_signals"

    return InteractionClassificationResult(
        status=status,
        points=points,
        segment_classifications=segment_classifications,
        point_count=len(points),
        segment_classification_count=len(segment_classifications),
        monologue_count=monologue_count,
        interaction_count=interaction_count,
        question_answer_count=question_answer_count,
        chat_reaction_count=chat_reaction_count,
        callout_count=callout_count,
        commentary_count=commentary_count,
        private_or_meta_count=private_or_meta_count,
        context_needed_count=context_needed_count,
        recommendation=recommendation,
        warnings=warnings,
        errors=errors,
        metadata=dict(metadata or {}),
    )


def classify_interactions(
    transcript_segments: Any,
    sentence_boundary_report: Any | None = None,
    keyword_emotion_report: Any | None = None,
    metadata: dict[str, Any] | None = None,
) -> InteractionClassificationResult:
    if not isinstance(transcript_segments, list) or not transcript_segments:
        return build_interaction_result(
            [],
            [],
            metadata=metadata,
        )

    classifications: list[InteractionSegmentClassification] = []
    points: list[InteractionClassificationPoint] = []
    previous_segment = None

    for index, segment in enumerate(transcript_segments):
        if not isinstance(segment, dict) and not hasattr(segment, "text"):
            classification = InteractionSegmentClassification(
                segment_id=f"interaction_segment_{index}",
                interaction_type=INTERACTION_TYPE_UNKNOWN,
                recommendation="review_unknown_interaction_type",
                metadata={"source_segment_index": index},
                warnings=[f"invalid_transcript_segment_skipped:{index}"],
            )
        else:
            classification = classify_interaction_segment(
                segment=segment,
                previous_segment=previous_segment,
                next_segment=(
                    transcript_segments[index + 1]
                    if index + 1 < len(transcript_segments)
                    else None
                ),
                sentence_boundary=sentence_boundary_report,
                keyword_emotion=keyword_emotion_report,
                source_index=index,
                metadata={"classifier": "interaction_classifier"},
            )
        classifications.append(classification)
        points.append(_point_from_classification(classification, index))
        previous_segment = segment

    return build_interaction_result(
        classifications,
        points,
        metadata=metadata,
    )
