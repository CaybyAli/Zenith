from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from core.transcript_segment_normalizer import normalize_transcript_segments
from models.profanity_censor import (
    CENSOR_ACTION_NONE,
    CENSOR_ACTION_SFX_OVERLAY_CANDIDATE,
    CATEGORY_GAMING_FRUSTRATION,
    CATEGORY_SEVERE_PROFANITY,
    CATEGORY_UNKNOWN,
    REPLACEMENT_SFX_OPTIONS,
    SEVERITY_MILD,
    SEVERITY_SEVERE,
    SEVERITY_UNKNOWN,
    STATUS_COMPLETED_WITH_WARNINGS,
    STATUS_FAILED,
    STATUS_OK,
    STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS,
    TIMING_SOURCE_SEGMENT_FALLBACK,
    TIMING_SOURCE_UNKNOWN,
    TIMING_SOURCE_WORD_TIMESTAMP,
    ProfanityCensorMatch,
    ProfanityCensorResult,
    ProfanityCensorSegmentResult,
)


_TOKEN_RE = re.compile(r"\w+", re.UNICODE)
_PUNCT_RE = re.compile(r"[^\w\s]+", re.UNICODE)
_DEFAULT_MANIFEST_PATH = (
    Path(__file__).resolve().parents[1]
    / "assets"
    / "sfx"
    / "censor"
    / "censor_sfx_manifest.json"
)


def _safe_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    return {}


def _safe_list(value: Any) -> list:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clamp(value: Any, default: float = 0.0) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        result = default
    return max(0.0, min(1.0, result))


def _center(start_seconds: float | None, end_seconds: float | None) -> float | None:
    if start_seconds is None or end_seconds is None:
        return None
    return (start_seconds + end_seconds) / 2.0


def _duration(start_seconds: float | None, end_seconds: float | None) -> float | None:
    if start_seconds is None or end_seconds is None:
        return None
    return max(0.0, end_seconds - start_seconds)


def _ascii_fold(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_profanity_text(text: Any) -> str:
    if text is None:
        return ""
    try:
        value = str(text)
    except Exception:
        return ""
    value = _ascii_fold(value.strip().lower())
    value = _PUNCT_RE.sub(" ", value)
    return " ".join(value.split())


def _default_profile() -> dict[str, Any]:
    return {
        "mild_terms": ["scheiss", "mist", "damn", "crap"],
        "severe_terms": ["severe_token"],
        "default_replacement_sfx": "quack",
        "replacement_sfx_options": list(REPLACEMENT_SFX_OPTIONS),
        "mild_category": CATEGORY_GAMING_FRUSTRATION,
        "severe_category": CATEGORY_SEVERE_PROFANITY,
        "mild_confidence": 0.66,
        "severe_confidence": 0.9,
    }


def _profile(profile: dict[str, Any] | None = None) -> dict[str, Any]:
    merged = _default_profile()
    if isinstance(profile, dict):
        merged.update(profile)
    return merged


def _normalized_terms(values: Any) -> set[str]:
    return {
        normalized
        for normalized in (normalize_profanity_text(item) for item in _safe_list(values))
        if normalized
    }


def classify_profanity_token(
    token_or_phrase: Any,
    profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active_profile = _profile(profile)
    normalized = normalize_profanity_text(token_or_phrase)
    severe_terms = _normalized_terms(active_profile.get("severe_terms"))
    mild_terms = _normalized_terms(active_profile.get("mild_terms"))

    if normalized in severe_terms:
        return {
            "normalized_match": normalized,
            "severity": SEVERITY_SEVERE,
            "category": str(
                active_profile.get("severe_category") or CATEGORY_SEVERE_PROFANITY
            ),
            "censor_required": True,
            "censor_action": CENSOR_ACTION_SFX_OVERLAY_CANDIDATE,
            "confidence": _clamp(active_profile.get("severe_confidence"), 0.9),
        }

    if normalized in mild_terms:
        return {
            "normalized_match": normalized,
            "severity": SEVERITY_MILD,
            "category": str(
                active_profile.get("mild_category") or CATEGORY_GAMING_FRUSTRATION
            ),
            "censor_required": False,
            "censor_action": CENSOR_ACTION_NONE,
            "confidence": _clamp(active_profile.get("mild_confidence"), 0.66),
        }

    return {
        "normalized_match": normalized,
        "severity": SEVERITY_UNKNOWN,
        "category": CATEGORY_UNKNOWN,
        "censor_required": False,
        "censor_action": CENSOR_ACTION_NONE,
        "confidence": 0.0,
    }


def build_default_censor_sfx_manifest() -> dict[str, Any]:
    return {
        "version": 1,
        "default": "quack",
        "options": {
            "quack": {
                "path": "assets/sfx/censor/quack.wav",
                "description": "Funny duck/quack censor overlay",
            },
            "dolphin": {
                "path": "assets/sfx/censor/dolphin.wav",
                "description": "Funny dolphin censor overlay",
            },
            "beep": {
                "path": "assets/sfx/censor/beep.wav",
                "description": "Classic beep censor overlay",
            },
        },
        "notes": [
            "Audio files may be added later.",
            "This manifest is for planned censor SFX routing only.",
            "No audio overlay is rendered in 2B-24.5.",
        ],
    }


def load_censor_sfx_manifest(manifest_path: str | Path | None = None) -> dict[str, Any]:
    path = Path(manifest_path) if manifest_path else _DEFAULT_MANIFEST_PATH
    try:
        if path.is_file():
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except Exception:
        return build_default_censor_sfx_manifest()
    return build_default_censor_sfx_manifest()


def choose_replacement_sfx(
    match: ProfanityCensorMatch | dict[str, Any] | None,
    profile: dict[str, Any] | None = None,
) -> str | None:
    active_profile = _profile(profile)
    censor_required = False
    if isinstance(match, ProfanityCensorMatch):
        censor_required = bool(match.censor_required)
    elif isinstance(match, dict):
        censor_required = bool(match.get("censor_required"))
    if not censor_required:
        return None

    allowed = set(REPLACEMENT_SFX_OPTIONS)
    options = _safe_list(active_profile.get("replacement_sfx_options"))
    if options:
        allowed = {str(option) for option in options if str(option) in allowed}
    if not allowed:
        allowed = set(REPLACEMENT_SFX_OPTIONS)

    requested = str(active_profile.get("default_replacement_sfx") or "").strip()
    if requested in allowed:
        return requested

    manifest_default = str(load_censor_sfx_manifest().get("default") or "").strip()
    if manifest_default in allowed:
        return manifest_default

    return "quack"


def _make_match(
    *,
    match_id: str,
    text: str,
    matched_text: str,
    classification: dict[str, Any],
    start_seconds: float | None,
    end_seconds: float | None,
    timing_source: str,
    source_segment_index: int | None,
    source_word_index: int | None = None,
    metadata: dict[str, Any] | None = None,
    warnings: list[str] | None = None,
    errors: list[str] | None = None,
    profile: dict[str, Any] | None = None,
) -> ProfanityCensorMatch:
    temporary = {
        "censor_required": bool(classification.get("censor_required")),
    }
    replacement_sfx = choose_replacement_sfx(temporary, profile=profile)
    return ProfanityCensorMatch(
        match_id=match_id,
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        center_seconds=_center(start_seconds, end_seconds),
        duration_seconds=_duration(start_seconds, end_seconds),
        text=text,
        matched_text=matched_text,
        normalized_match=str(classification.get("normalized_match") or ""),
        severity=str(classification.get("severity") or SEVERITY_UNKNOWN),
        category=str(classification.get("category") or CATEGORY_UNKNOWN),
        censor_required=bool(classification.get("censor_required")),
        censor_action=str(classification.get("censor_action") or CENSOR_ACTION_NONE),
        replacement_sfx=replacement_sfx,
        timing_source=timing_source,
        confidence=_clamp(classification.get("confidence"), 0.0),
        source_segment_index=source_segment_index,
        source_word_index=source_word_index,
        metadata=dict(metadata or {}),
        warnings=list(warnings or []),
        errors=list(errors or []),
    )


def detect_profanity_in_words(
    words: Any,
    segment_start: float | None = None,
    segment_end: float | None = None,
    source_index: int = 0,
    profile: dict[str, Any] | None = None,
) -> list[ProfanityCensorMatch]:
    if not isinstance(words, list):
        return []

    matches: list[ProfanityCensorMatch] = []
    for word_index, word in enumerate(words):
        word_dict = _safe_dict(word)
        raw_text = (
            word_dict.get("word")
            or word_dict.get("text")
            or (word if isinstance(word, str) else "")
        )
        text = str(raw_text or "").strip()
        if not text:
            continue

        classification = classify_profanity_token(text, profile=profile)
        if classification["severity"] == SEVERITY_UNKNOWN:
            continue

        start_seconds = _safe_float(word_dict.get("start_seconds"))
        if start_seconds is None:
            start_seconds = _safe_float(word_dict.get("start"))
        end_seconds = _safe_float(word_dict.get("end_seconds"))
        if end_seconds is None:
            end_seconds = _safe_float(word_dict.get("end"))

        timing_source = TIMING_SOURCE_WORD_TIMESTAMP
        warnings = [str(item) for item in _safe_list(word_dict.get("warnings"))]
        errors = [str(item) for item in _safe_list(word_dict.get("errors"))]
        if start_seconds is None or end_seconds is None:
            start_seconds = segment_start
            end_seconds = segment_end
            timing_source = (
                TIMING_SOURCE_SEGMENT_FALLBACK
                if start_seconds is not None and end_seconds is not None
                else TIMING_SOURCE_UNKNOWN
            )
            warnings.append("word_timestamp_missing_used_segment_fallback")

        matches.append(
            _make_match(
                match_id=f"profanity_censor_{source_index}_{word_index}",
                text=text,
                matched_text=text,
                classification=classification,
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                timing_source=timing_source,
                source_segment_index=source_index,
                source_word_index=word_index,
                metadata={"source": "word"},
                warnings=warnings,
                errors=errors,
                profile=profile,
            )
        )

    return matches


def _text_matches(
    text: str,
    start_seconds: float | None,
    end_seconds: float | None,
    source_index: int,
    profile: dict[str, Any] | None = None,
) -> list[ProfanityCensorMatch]:
    active_profile = _profile(profile)
    terms: list[str] = []
    terms.extend(_normalized_terms(active_profile.get("severe_terms")))
    terms.extend(_normalized_terms(active_profile.get("mild_terms")))
    terms = sorted(set(terms), key=lambda item: len(item.split()), reverse=True)

    normalized_text = normalize_profanity_text(text)
    if not normalized_text:
        return []

    matches: list[ProfanityCensorMatch] = []
    occupied_spans: list[tuple[int, int]] = []

    for term in terms:
        pattern = re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.UNICODE)
        for found in pattern.finditer(normalized_text):
            span = found.span()
            if any(not (span[1] <= old[0] or span[0] >= old[1]) for old in occupied_spans):
                continue
            classification = classify_profanity_token(term, profile=profile)
            if classification["severity"] == SEVERITY_UNKNOWN:
                continue
            occupied_spans.append(span)
            matches.append(
                _make_match(
                    match_id=f"profanity_censor_{source_index}_segment_{len(matches)}",
                    text=text,
                    matched_text=term,
                    classification=classification,
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                    timing_source=(
                        TIMING_SOURCE_SEGMENT_FALLBACK
                        if start_seconds is not None and end_seconds is not None
                        else TIMING_SOURCE_UNKNOWN
                    ),
                    source_segment_index=source_index,
                    metadata={"source": "segment_text"},
                    warnings=["segment_timing_used_for_match"],
                    profile=profile,
                )
            )

    matches.sort(key=lambda match: match.match_id)
    return matches


def detect_profanity_in_segment(
    segment: Any,
    source_index: int = 0,
    profile: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> ProfanityCensorSegmentResult:
    segment_dict = _safe_dict(segment)
    text = str(segment_dict.get("text") or "").strip()
    start_seconds = _safe_float(segment_dict.get("start_seconds"))
    end_seconds = _safe_float(segment_dict.get("end_seconds"))
    duration_seconds = _safe_float(segment_dict.get("duration_seconds"))
    if duration_seconds is None:
        duration_seconds = _duration(start_seconds, end_seconds)
    warnings = [str(item) for item in _safe_list(segment_dict.get("warnings"))]
    errors = [str(item) for item in _safe_list(segment_dict.get("errors"))]

    words = segment_dict.get("words")
    word_matches: list[ProfanityCensorMatch] = []
    words_have_timestamps = False
    if isinstance(words, list):
        words_have_timestamps = any(
            _safe_float(_safe_dict(word).get("start_seconds")) is not None
            and _safe_float(_safe_dict(word).get("end_seconds")) is not None
            for word in words
        )
        word_matches = detect_profanity_in_words(
            words,
            segment_start=start_seconds,
            segment_end=end_seconds,
            source_index=source_index,
            profile=profile,
        )

    matches = word_matches if words_have_timestamps else []
    if not words_have_timestamps:
        matches = _text_matches(
            text=text,
            start_seconds=start_seconds,
            end_seconds=end_seconds,
            source_index=source_index,
            profile=profile,
        )
        if isinstance(words, list) and words:
            warnings.append("word_timestamps_unavailable_used_segment_fallback")

    severe_match_count = sum(1 for match in matches if match.severity == SEVERITY_SEVERE)
    mild_match_count = sum(1 for match in matches if match.severity == SEVERITY_MILD)
    censor_required_count = sum(1 for match in matches if match.censor_required)
    preferred_sfx = next(
        (match.replacement_sfx for match in matches if match.replacement_sfx),
        None,
    )
    if censor_required_count:
        recommendation = "review_censor_sfx_overlay_candidates"
    elif mild_match_count:
        recommendation = "mild_profanity_no_censor_required"
    else:
        recommendation = "no_profanity_censor_candidates"

    return ProfanityCensorSegmentResult(
        segment_id=str(
            segment_dict.get("segment_id")
            or segment_dict.get("id")
            or f"segment_{source_index}"
        ),
        start_seconds=start_seconds,
        end_seconds=end_seconds,
        duration_seconds=duration_seconds,
        text=text,
        match_count=len(matches),
        severe_match_count=severe_match_count,
        mild_match_count=mild_match_count,
        censor_required_count=censor_required_count,
        preferred_replacement_sfx=preferred_sfx,
        recommendation=recommendation,
        matches=[match.to_dict() for match in matches],
        metadata={
            **(dict(metadata) if isinstance(metadata, dict) else {}),
            "source_index": source_index,
            "words_have_timestamps": words_have_timestamps,
        },
        warnings=sorted(set(warnings)),
        errors=sorted(set(errors)),
    )


def detect_profanity_censor_candidates(
    transcript_segments: Any,
    profile: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> ProfanityCensorResult:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}
    if not transcript_segments:
        return ProfanityCensorResult(
            status=STATUS_SKIPPED_NO_TRANSCRIPT_SEGMENTS,
            recommendation="profanity_censor_skipped_no_transcript",
            warnings=["no_transcript_segments_available"],
            metadata=safe_metadata,
        )

    try:
        normalization_result = normalize_transcript_segments(
            transcript_segments,
            metadata={"stage": safe_metadata.get("stage")},
        )
        if not normalization_result.valid_segments:
            return ProfanityCensorResult(
                status=STATUS_COMPLETED_WITH_WARNINGS,
                recommendation="profanity_censor_no_valid_transcript_segments",
                warnings=sorted(
                    set(
                        list(normalization_result.warnings or [])
                        + ["no_valid_transcript_segments"]
                    )
                ),
                errors=list(normalization_result.errors or []),
                metadata={
                    **safe_metadata,
                    "normalization_status": normalization_result.status,
                },
            )

        segment_results: list[ProfanityCensorSegmentResult] = []
        matches: list[ProfanityCensorMatch] = []
        for index, segment in enumerate(normalization_result.valid_segments):
            source_index = int(segment.get("source_index", index) or index)
            segment_result = detect_profanity_in_segment(
                segment,
                source_index=source_index,
                profile=profile,
                metadata=safe_metadata,
            )
            segment_results.append(segment_result)
            matches.extend(
                ProfanityCensorMatch.from_dict(match)
                for match in segment_result.matches
            )

        severe_match_count = sum(1 for match in matches if match.severity == SEVERITY_SEVERE)
        mild_match_count = sum(1 for match in matches if match.severity == SEVERITY_MILD)
        censor_required_count = sum(1 for match in matches if match.censor_required)
        word_level_match_count = sum(
            1 for match in matches if match.timing_source == TIMING_SOURCE_WORD_TIMESTAMP
        )
        segment_fallback_match_count = sum(
            1 for match in matches if match.timing_source == TIMING_SOURCE_SEGMENT_FALLBACK
        )
        warnings = sorted(
            set(
                list(normalization_result.warnings or [])
                + [
                    warning
                    for segment_result in segment_results
                    for warning in segment_result.warnings
                ]
            )
        )
        errors = sorted(
            set(
                list(normalization_result.errors or [])
                + [
                    error
                    for segment_result in segment_results
                    for error in segment_result.errors
                ]
            )
        )
        if censor_required_count:
            recommendation = "review_censor_sfx_overlay_candidates"
        elif mild_match_count:
            recommendation = "mild_profanity_no_censor_required"
        else:
            recommendation = "no_profanity_censor_candidates"

        status = STATUS_COMPLETED_WITH_WARNINGS if warnings or errors else STATUS_OK
        return ProfanityCensorResult(
            status=status,
            matches=matches,
            segment_results=segment_results,
            match_count=len(matches),
            severe_match_count=severe_match_count,
            mild_match_count=mild_match_count,
            censor_required_count=censor_required_count,
            word_level_match_count=word_level_match_count,
            segment_fallback_match_count=segment_fallback_match_count,
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
        return ProfanityCensorResult(
            status=STATUS_FAILED,
            recommendation="profanity_censor_failed",
            errors=[f"profanity_censor_detection_failed:{exc}"],
            metadata=safe_metadata,
        )
