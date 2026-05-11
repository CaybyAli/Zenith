from __future__ import annotations

import re
from typing import Any

from models.filler_word import FillerWordDetectionResult, FillerWordOccurrence

DEFAULT_FILLER_CONFIDENCE = 0.75
DEFAULT_REPEAT_MAX_GAP_SECONDS = 0.35

_PUNCT_STRIP = re.compile(r"[.,:!?;\"'()\[\]{}]+")


def normalize_token(token: Any) -> str:
    if token is None:
        return ""
    try:
        text = str(token)
    except Exception:
        return ""
    text = text.strip().lower()
    text = _PUNCT_STRIP.sub("", text)
    text = text.strip()
    return text


def get_default_filler_lexicon() -> dict[str, dict[str, Any]]:
    return {
        # German hesitations
        "äh": {"filler_type": "hesitation", "language": "de", "confidence": 0.75, "remove_candidate": True},
        "ähm": {"filler_type": "hesitation", "language": "de", "confidence": 0.75, "remove_candidate": True},
        "eh": {"filler_type": "hesitation", "language": "de", "confidence": 0.70, "remove_candidate": True},
        "ehm": {"filler_type": "hesitation", "language": "de", "confidence": 0.75, "remove_candidate": True},
        "öhm": {"filler_type": "hesitation", "language": "de", "confidence": 0.75, "remove_candidate": True},
        # German discourse markers
        "halt": {"filler_type": "discourse_marker", "language": "de", "confidence": 0.65, "remove_candidate": True},
        "also": {"filler_type": "discourse_marker", "language": "de", "confidence": 0.60, "remove_candidate": True},
        "quasi": {"filler_type": "discourse_marker", "language": "de", "confidence": 0.65, "remove_candidate": True},
        # English hesitations
        "um": {"filler_type": "hesitation", "language": "en", "confidence": 0.75, "remove_candidate": True},
        "uh": {"filler_type": "hesitation", "language": "en", "confidence": 0.75, "remove_candidate": True},
        "erm": {"filler_type": "hesitation", "language": "en", "confidence": 0.75, "remove_candidate": True},
        "er": {"filler_type": "hesitation", "language": "en", "confidence": 0.65, "remove_candidate": True},
        # English discourse markers
        "like": {"filler_type": "discourse_marker", "language": "en", "confidence": 0.60, "remove_candidate": True},
        # English phrase fillers
        "you know": {"filler_type": "phrase_filler", "language": "en", "confidence": 0.80, "remove_candidate": True},
        "i mean": {"filler_type": "phrase_filler", "language": "en", "confidence": 0.80, "remove_candidate": True},
        # Turkish hesitations
        "şey": {"filler_type": "hesitation", "language": "tr", "confidence": 0.75, "remove_candidate": True},
        # Turkish discourse markers
        "yani": {"filler_type": "discourse_marker", "language": "tr", "confidence": 0.70, "remove_candidate": True},
        "işte": {"filler_type": "discourse_marker", "language": "tr", "confidence": 0.70, "remove_candidate": True},
    }


def _safe_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _read_word_text(item: dict[str, Any]) -> str:
    for key in ("word", "text", "token", "value"):
        val = item.get(key)
        if val is not None:
            s = str(val).strip()
            if s:
                return s
    return ""


def _read_start(item: dict[str, Any]) -> float | None:
    for key in ("start_seconds", "start", "start_time"):
        val = _safe_float(item.get(key))
        if val is not None:
            return val
    return None


def _read_end(item: dict[str, Any]) -> float | None:
    for key in ("end_seconds", "end", "end_time"):
        val = _safe_float(item.get(key))
        if val is not None:
            return val
    return None


def _build_word_item(
    text: str,
    start: float | None,
    end: float | None,
    seg_idx: int | None,
    word_idx: int | None,
    source_item: dict[str, Any],
) -> dict[str, Any]:
    center: float | None = None
    if start is not None and end is not None:
        center = (start + end) / 2.0
    return {
        "text": text,
        "normalized_text": normalize_token(text),
        "start_seconds": start,
        "end_seconds": end,
        "center_seconds": center,
        "source_segment_index": seg_idx,
        "source_word_index": word_idx,
        "source_item": source_item,
    }


def _extract_from_word_dict(item: dict[str, Any], seg_idx: int | None, word_idx: int) -> dict[str, Any] | None:
    text = _read_word_text(item)
    if not text:
        return None
    start = _read_start(item)
    end = _read_end(item)
    return _build_word_item(text, start, end, seg_idx, word_idx, item)


def _extract_from_segment_dict(seg: dict[str, Any], seg_idx: int) -> list[dict[str, Any]]:
    raw_text = seg.get("text", "")
    if not raw_text or not isinstance(raw_text, str):
        return []
    words = raw_text.split()
    if not words:
        return []

    seg_start = _read_start(seg)
    seg_end = _read_end(seg)

    result: list[dict[str, Any]] = []
    n = len(words)
    for wi, word in enumerate(words):
        word = word.strip()
        if not word:
            continue
        start: float | None = None
        end: float | None = None
        if seg_start is not None and seg_end is not None and n > 0:
            duration = seg_end - seg_start
            step = duration / n
            start = seg_start + wi * step
            end = start + step
        result.append(_build_word_item(word, start, end, seg_idx, wi, seg))
    return result


def extract_word_items(transcript_data: Any) -> list[dict[str, Any]]:
    if transcript_data is None:
        return []

    # Case 1/2/5: list input
    if isinstance(transcript_data, list):
        if not transcript_data:
            return []

        result: list[dict[str, Any]] = []

        # Peek at first non-None item
        first = next((x for x in transcript_data if x is not None), None)
        if first is None:
            return []

        if isinstance(first, str):
            # list[str]
            for wi, item in enumerate(transcript_data):
                if item is None:
                    continue
                text = str(item).strip()
                if not text:
                    continue
                result.append(_build_word_item(text, None, None, None, wi, {}))
            return result

        if isinstance(first, dict):
            # Could be word dicts or segment dicts
            # Detect: if any item has "text" key but no word/token keys AND has start/end that span > 2s, treat as segment
            # Simple heuristic: if "word" or "token" key present → word dict; else if "text" with whitespace → segment
            word_results: list[dict[str, Any]] = []
            seg_results: list[dict[str, Any]] = []

            for i, item in enumerate(transcript_data):
                if not isinstance(item, dict):
                    continue
                try:
                    # Check if it's a word dict
                    has_word_key = any(k in item for k in ("word", "token", "value"))
                    text_val = item.get("text", "")
                    text_has_spaces = isinstance(text_val, str) and " " in text_val.strip()

                    if has_word_key or (isinstance(text_val, str) and text_val and not text_has_spaces):
                        # word dict
                        wi = _extract_from_word_dict(item, None, i)
                        if wi is not None:
                            word_results.append(wi)
                    else:
                        # segment dict
                        seg_results.extend(_extract_from_segment_dict(item, i))
                except Exception:
                    continue

            return word_results if word_results else seg_results

        # Objects with .text attribute treated as segments
        seg_results2: list[dict[str, Any]] = []
        for i, item in enumerate(transcript_data):
            try:
                if hasattr(item, "words"):
                    words_attr = item.words
                    if isinstance(words_attr, list):
                        for wi, w in enumerate(words_attr):
                            if isinstance(w, dict):
                                r = _extract_from_word_dict(w, i, wi)
                                if r is not None:
                                    seg_results2.append(r)
                elif hasattr(item, "text"):
                    fake_seg = {"text": str(item.text)}
                    if hasattr(item, "start_seconds"):
                        fake_seg["start_seconds"] = item.start_seconds
                    if hasattr(item, "end_seconds"):
                        fake_seg["end_seconds"] = item.end_seconds
                    seg_results2.extend(_extract_from_segment_dict(fake_seg, i))
            except Exception:
                continue
        return seg_results2

    # Case 3: dict with "words"
    if isinstance(transcript_data, dict):
        if "words" in transcript_data:
            raw_words = transcript_data["words"]
            if isinstance(raw_words, list):
                result2: list[dict[str, Any]] = []
                for wi, item in enumerate(raw_words):
                    if isinstance(item, dict):
                        r = _extract_from_word_dict(item, None, wi)
                        if r is not None:
                            result2.append(r)
                    elif isinstance(item, str):
                        text = item.strip()
                        if text:
                            result2.append(_build_word_item(text, None, None, None, wi, {}))
                return result2

        # Case 4: dict with "segments"
        if "segments" in transcript_data:
            raw_segs = transcript_data["segments"]
            if isinstance(raw_segs, list):
                result3: list[dict[str, Any]] = []
                for si, seg in enumerate(raw_segs):
                    if isinstance(seg, dict):
                        result3.extend(_extract_from_segment_dict(seg, si))
                return result3

        return []

    # Object with .words or .segments attribute
    if hasattr(transcript_data, "words"):
        return extract_word_items({"words": transcript_data.words})
    if hasattr(transcript_data, "segments"):
        return extract_word_items({"segments": transcript_data.segments})

    return []


def detect_filler_word_at_index(
    word_items: list[dict[str, Any]],
    index: int,
    filler_lexicon: dict[str, dict[str, Any]] | None = None,
    detect_repeated_words: bool = True,
    repeat_max_gap_seconds: float = DEFAULT_REPEAT_MAX_GAP_SECONDS,
) -> FillerWordOccurrence | None:
    if not word_items or index < 0 or index >= len(word_items):
        return None

    if filler_lexicon is None:
        filler_lexicon = get_default_filler_lexicon()

    try:
        current = word_items[index]
        norm = current.get("normalized_text") or normalize_token(current.get("text", ""))

        if not norm:
            return None

        # 1. Check phrase fillers (multi-token)
        phrase_keys = [k for k in filler_lexicon if " " in k]
        for phrase in phrase_keys:
            parts = phrase.split()
            if len(parts) < 2:
                continue
            if norm == parts[0] and index + 1 < len(word_items):
                next_item = word_items[index + 1]
                next_norm = next_item.get("normalized_text") or normalize_token(next_item.get("text", ""))
                if next_norm == parts[1]:
                    lex = filler_lexicon[phrase]
                    start = current.get("start_seconds")
                    end = next_item.get("end_seconds")
                    center: float | None = None
                    if start is not None and end is not None:
                        center = (start + end) / 2.0
                    duration: float | None = None
                    if start is not None and end is not None:
                        duration = end - start
                    return FillerWordOccurrence(
                        text=phrase,
                        normalized_text=phrase,
                        filler_type=lex.get("filler_type", "phrase_filler"),
                        language=lex.get("language", "unknown"),
                        start_seconds=start,
                        end_seconds=end,
                        center_seconds=center,
                        duration_seconds=duration,
                        confidence=float(lex.get("confidence", DEFAULT_FILLER_CONFIDENCE)),
                        remove_candidate=bool(lex.get("remove_candidate", True)),
                        reason="phrase_filler_detected",
                        source_segment_index=current.get("source_segment_index"),
                        source_word_index=current.get("source_word_index") if current.get("source_word_index") is not None else index,
                        source_item=dict(current.get("source_item") or {}),
                    )

        # 2. Single-token filler
        if norm in filler_lexicon:
            lex = filler_lexicon[norm]
            start = current.get("start_seconds")
            end = current.get("end_seconds")
            center2: float | None = current.get("center_seconds")
            if center2 is None and start is not None and end is not None:
                center2 = (start + end) / 2.0
            duration2: float | None = None
            if start is not None and end is not None:
                duration2 = end - start
            return FillerWordOccurrence(
                text=current.get("text", norm),
                normalized_text=norm,
                filler_type=lex.get("filler_type", "unknown"),
                language=lex.get("language", "unknown"),
                start_seconds=start,
                end_seconds=end,
                center_seconds=center2,
                duration_seconds=duration2,
                confidence=float(lex.get("confidence", DEFAULT_FILLER_CONFIDENCE)),
                remove_candidate=bool(lex.get("remove_candidate", True)),
                reason="lexicon_match",
                source_segment_index=current.get("source_segment_index"),
                source_word_index=current.get("source_word_index") if current.get("source_word_index") is not None else index,
                source_item=dict(current.get("source_item") or {}),
            )

        # 3. Repeated word detection
        if detect_repeated_words and index > 0:
            prev = word_items[index - 1]
            prev_norm = prev.get("normalized_text") or normalize_token(prev.get("text", ""))
            if norm and prev_norm and norm == prev_norm and not _is_punctuation_only(norm):
                # Check time gap if available
                gap_ok = True
                prev_end = prev.get("end_seconds")
                curr_start = current.get("start_seconds")
                if prev_end is not None and curr_start is not None:
                    gap = curr_start - prev_end
                    if gap > repeat_max_gap_seconds:
                        gap_ok = False

                if gap_ok:
                    start3 = current.get("start_seconds")
                    end3 = current.get("end_seconds")
                    center3: float | None = current.get("center_seconds")
                    if center3 is None and start3 is not None and end3 is not None:
                        center3 = (start3 + end3) / 2.0
                    duration3: float | None = None
                    if start3 is not None and end3 is not None:
                        duration3 = end3 - start3
                    return FillerWordOccurrence(
                        text=current.get("text", norm),
                        normalized_text=norm,
                        filler_type="repeated_word",
                        language="unknown",
                        start_seconds=start3,
                        end_seconds=end3,
                        center_seconds=center3,
                        duration_seconds=duration3,
                        confidence=0.65,
                        remove_candidate=True,
                        reason="repeated_word_detected",
                        source_segment_index=current.get("source_segment_index"),
                        source_word_index=current.get("source_word_index") if current.get("source_word_index") is not None else index,
                        source_item=dict(current.get("source_item") or {}),
                    )

    except Exception:
        pass

    return None


def _is_punctuation_only(text: str) -> bool:
    return bool(text) and all(c in ".,:!?;\"'()[]{}" for c in text)


def detect_filler_words(
    transcript_data: Any,
    filler_lexicon: dict[str, dict[str, Any]] | None = None,
    detect_repeated_words: bool = True,
    repeat_max_gap_seconds: float = DEFAULT_REPEAT_MAX_GAP_SECONDS,
    max_occurrences: int | None = None,
    metadata: dict[str, Any] | None = None,
) -> FillerWordDetectionResult:
    if filler_lexicon is None:
        filler_lexicon = get_default_filler_lexicon()
    if metadata is None:
        metadata = {}

    warnings: list[str] = []
    errors: list[str] = []
    occurrences: list[FillerWordOccurrence] = []

    try:
        word_items = extract_word_items(transcript_data)

        if not word_items:
            warnings.append("no_words_available")
            return FillerWordDetectionResult(
                status="completed_with_warnings",
                occurrences=[],
                occurrence_count=0,
                remove_candidate_count=0,
                counts_by_filler_type={},
                counts_by_language={},
                total_filler_duration_seconds=0.0,
                warnings=warnings,
                errors=errors,
                metadata=metadata,
            )

        index = 0
        while index < len(word_items):
            if max_occurrences is not None and len(occurrences) >= max_occurrences:
                break

            occ = detect_filler_word_at_index(
                word_items,
                index,
                filler_lexicon=filler_lexicon,
                detect_repeated_words=detect_repeated_words,
                repeat_max_gap_seconds=repeat_max_gap_seconds,
            )

            if occ is not None:
                occurrences.append(occ)
                # Advance by 2 for phrase fillers, 1 for single-token
                if " " in occ.text:
                    index += 2
                else:
                    index += 1
            else:
                index += 1

        # Build counts
        occurrence_count = len(occurrences)
        remove_candidate_count = sum(1 for o in occurrences if o.remove_candidate)
        counts_by_filler_type: dict[str, int] = {}
        counts_by_language: dict[str, int] = {}
        total_duration = 0.0

        for occ in occurrences:
            ft = occ.filler_type or "unknown"
            counts_by_filler_type[ft] = counts_by_filler_type.get(ft, 0) + 1
            lang = occ.language or "unknown"
            counts_by_language[lang] = counts_by_language.get(lang, 0) + 1
            if occ.duration_seconds is not None:
                total_duration += occ.duration_seconds

        status = "ok" if occurrence_count > 0 and not warnings else "completed_with_warnings"

        return FillerWordDetectionResult(
            status=status,
            occurrences=occurrences,
            occurrence_count=occurrence_count,
            remove_candidate_count=remove_candidate_count,
            counts_by_filler_type=counts_by_filler_type,
            counts_by_language=counts_by_language,
            total_filler_duration_seconds=round(total_duration, 4),
            warnings=warnings,
            errors=errors,
            metadata=metadata,
        )

    except Exception as exc:
        errors.append("filler_word_detection_failed")
        return FillerWordDetectionResult(
            status="failed",
            occurrences=[],
            occurrence_count=0,
            remove_candidate_count=0,
            counts_by_filler_type={},
            counts_by_language={},
            total_filler_duration_seconds=0.0,
            warnings=warnings,
            errors=errors,
            metadata=metadata,
        )
