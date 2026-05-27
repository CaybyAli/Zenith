from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TranscriptSegmentNormalizationResult:
    status: str
    segments: list[dict[str, Any]] = field(default_factory=list)
    valid_segments: list[dict[str, Any]] = field(default_factory=list)
    invalid_segments: list[dict[str, Any]] = field(default_factory=list)
    segment_count: int = 0
    valid_segment_count: int = 0
    invalid_segment_count: int = 0
    word_count: int = 0
    word_timestamp_count: int = 0
    has_word_level_timestamps: bool = False
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    recommendation: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "segments": list(self.segments),
            "valid_segments": list(self.valid_segments),
            "invalid_segments": list(self.invalid_segments),
            "segment_count": self.segment_count,
            "valid_segment_count": self.valid_segment_count,
            "invalid_segment_count": self.invalid_segment_count,
            "word_count": self.word_count,
            "word_timestamp_count": self.word_timestamp_count,
            "has_word_level_timestamps": self.has_word_level_timestamps,
            "warnings": list(self.warnings),
            "errors": list(self.errors),
            "recommendation": self.recommendation,
            "metadata": dict(self.metadata),
        }


def _get_value(source: Any, key: str) -> Any:
    if isinstance(source, dict):
        return source.get(key)

    return getattr(source, key, None)


def _first_value(source: Any, keys: list[str]) -> Any:
    for key in keys:
        value = _get_value(source, key)
        if value is not None:
            return value

    return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _safe_text(value: Any) -> str:
    if value is None:
        return ""

    try:
        return str(value).strip()
    except Exception:
        return ""


def _safe_confidence(value: Any) -> float | None:
    confidence = _to_float(value)

    if confidence is None:
        return None

    return confidence


def _safe_audio_track(value: Any) -> str:
    clean = _safe_text(value).lower()
    return clean or "mic"


def _safe_speaker(value: Any) -> str:
    clean = _safe_text(value).lower()
    if clean in {"ali", "friend", "unknown"}:
        return clean
    return "unknown"


def _metadata_from(source: Any) -> dict[str, Any]:
    metadata = _get_value(source, "metadata")

    if isinstance(metadata, dict):
        return dict(metadata)

    return {}


def normalize_transcript_word(
    word: Any,
    source_index: int = 0,
    word_index: int = 0,
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    if word is None:
        return {
            "word": "",
            "start_seconds": None,
            "end_seconds": None,
            "confidence": None,
            "source_index": int(source_index),
            "word_index": int(word_index),
            "is_valid": False,
            "warnings": [],
            "errors": ["invalid_word"],
            "metadata": {},
        }

    word_text = _safe_text(_first_value(word, ["word", "text"]))
    start_seconds = _to_float(_first_value(word, ["start_seconds", "start"]))
    end_seconds = _to_float(_first_value(word, ["end_seconds", "end"]))
    confidence = _safe_confidence(_get_value(word, "confidence"))

    if not word_text:
        errors.append("empty_word")

    has_start = start_seconds is not None
    has_end = end_seconds is not None

    if has_start != has_end:
        warnings.append("word_partial_timestamp")

    if not has_start and not has_end:
        warnings.append("word_without_timestamps")

    if start_seconds is not None and start_seconds < 0:
        errors.append("negative_timestamp")

    if end_seconds is not None and end_seconds < 0:
        errors.append("negative_timestamp")

    if (
        start_seconds is not None
        and end_seconds is not None
        and end_seconds < start_seconds
    ):
        errors.append("end_before_start")

    return {
        "word": word_text,
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "confidence": confidence,
        "source_index": int(source_index),
        "word_index": int(word_index),
        "is_valid": bool(word_text) and not errors,
        "warnings": warnings,
        "errors": errors,
        "metadata": _metadata_from(word),
    }


def normalize_transcript_segment(
    segment: Any,
    source_index: int = 0,
) -> dict[str, Any]:
    warnings: list[str] = []
    errors: list[str] = []

    if segment is None:
        return {
            "start_seconds": None,
            "end_seconds": None,
            "duration_seconds": None,
            "text": "",
            "words": [],
            "confidence": None,
            "source_index": int(source_index),
            "is_valid": False,
            "warnings": [],
            "errors": ["invalid_segment"],
            "metadata": {},
        }

    start_seconds = _to_float(_first_value(segment, ["start_seconds", "start"]))
    end_seconds = _to_float(_first_value(segment, ["end_seconds", "end"]))
    text = _safe_text(_get_value(segment, "text"))
    confidence = _safe_confidence(_get_value(segment, "confidence"))
    audio_track = _safe_audio_track(_get_value(segment, "audio_track"))
    speaker = _safe_speaker(_get_value(segment, "speaker"))

    if start_seconds is None:
        errors.append("missing_start_seconds")

    if end_seconds is None:
        errors.append("missing_end_seconds")

    if not text:
        errors.append("empty_text")

    if start_seconds is not None and start_seconds < 0:
        errors.append("negative_timestamp")

    if end_seconds is not None and end_seconds < 0:
        errors.append("negative_timestamp")

    if (
        start_seconds is not None
        and end_seconds is not None
        and end_seconds < start_seconds
    ):
        errors.append("end_before_start")

    duration_seconds: float | None = None
    if (
        start_seconds is not None
        and end_seconds is not None
        and start_seconds >= 0
        and end_seconds >= start_seconds
    ):
        duration_seconds = end_seconds - start_seconds

    raw_words = _get_value(segment, "words")
    words: list[dict[str, Any]] = []

    if raw_words is None:
        words = []
    elif isinstance(raw_words, list):
        for word_index, raw_word in enumerate(raw_words):
            normalized_word = normalize_transcript_word(
                raw_word,
                source_index=source_index,
                word_index=word_index,
            )
            words.append(normalized_word)

        if words and not any(
            word_item.get("start_seconds") is not None
            and word_item.get("end_seconds") is not None
            for word_item in words
        ):
            warnings.append("words_without_timestamps")
    else:
        warnings.append("invalid_words_payload")

    return {
        "start_seconds": start_seconds,
        "end_seconds": end_seconds,
        "duration_seconds": duration_seconds,
        "text": text,
        "words": words,
        "confidence": confidence,
        "audio_track": audio_track,
        "speaker": speaker,
        "source_index": int(source_index),
        "is_valid": not errors,
        "warnings": warnings,
        "errors": errors,
        "metadata": _metadata_from(segment),
    }


def normalize_transcript_segments(
    segments: Any,
    metadata: dict[str, Any] | None = None,
) -> TranscriptSegmentNormalizationResult:
    safe_metadata = dict(metadata) if isinstance(metadata, dict) else {}

    if segments is None:
        return TranscriptSegmentNormalizationResult(
            status="skipped_no_segments",
            recommendation="no_transcript_segments_available",
            warnings=["segments_missing"],
            metadata=safe_metadata,
        )

    if not isinstance(segments, list):
        return TranscriptSegmentNormalizationResult(
            status="failed",
            recommendation="provide_segments_as_list",
            errors=["invalid_segments_payload"],
            metadata=safe_metadata,
        )

    if not segments:
        return TranscriptSegmentNormalizationResult(
            status="skipped_no_segments",
            recommendation="no_transcript_segments_available",
            warnings=["segments_empty"],
            metadata=safe_metadata,
        )

    normalized_segments: list[dict[str, Any]] = []
    valid_segments: list[dict[str, Any]] = []
    invalid_segments: list[dict[str, Any]] = []
    warnings: list[str] = []
    errors: list[str] = []
    word_count = 0
    word_timestamp_count = 0
    has_word_level_timestamps = False

    for source_index, raw_segment in enumerate(segments):
        normalized = normalize_transcript_segment(
            raw_segment,
            source_index=source_index,
        )
        normalized_segments.append(normalized)

        if normalized.get("is_valid"):
            valid_segments.append(normalized)
        else:
            invalid_segments.append(normalized)

        warnings.extend(str(item) for item in normalized.get("warnings", []))
        errors.extend(str(item) for item in normalized.get("errors", []))

        words = normalized.get("words") or []
        word_count += len(words)

        current_word_timestamp_count = sum(
            1
            for word_item in words
            if word_item.get("start_seconds") is not None
            and word_item.get("end_seconds") is not None
        )
        word_timestamp_count += current_word_timestamp_count

        if current_word_timestamp_count > 0:
            has_word_level_timestamps = True

    if valid_segments and invalid_segments:
        status = "completed_with_warnings"
        recommendation = "use_valid_segments_review_invalid_segments"
    elif valid_segments:
        status = "ok"
        recommendation = "use_normalized_segments"
    else:
        status = "failed"
        recommendation = "fix_transcript_segments"

    return TranscriptSegmentNormalizationResult(
        status=status,
        segments=normalized_segments,
        valid_segments=valid_segments,
        invalid_segments=invalid_segments,
        segment_count=len(normalized_segments),
        valid_segment_count=len(valid_segments),
        invalid_segment_count=len(invalid_segments),
        word_count=word_count,
        word_timestamp_count=word_timestamp_count,
        has_word_level_timestamps=has_word_level_timestamps,
        warnings=sorted(set(warnings)),
        errors=sorted(set(errors)),
        recommendation=recommendation,
        metadata=safe_metadata,
    )
