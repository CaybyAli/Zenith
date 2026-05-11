from __future__ import annotations

import os
from typing import Any

import pytest

from models.filler_word import FillerWordDetectionResult, FillerWordOccurrence
from core.filler_word_detector import (
    DEFAULT_FILLER_CONFIDENCE,
    DEFAULT_REPEAT_MAX_GAP_SECONDS,
    detect_filler_word_at_index,
    detect_filler_words,
    extract_word_items,
    get_default_filler_lexicon,
    normalize_token,
)


# ─── helpers ────────────────────────────────────────────────────────────────

def _word_items_from_strings(words: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "text": w,
            "normalized_text": normalize_token(w),
            "start_seconds": None,
            "end_seconds": None,
            "center_seconds": None,
            "source_segment_index": None,
            "source_word_index": i,
            "source_item": {},
        }
        for i, w in enumerate(words)
    ]


# ─── 1. FillerWordOccurrence roundtrip ─────────────────────────────────────

def test_filler_word_occurrence_roundtrip():
    occ = FillerWordOccurrence(
        text="ähm",
        normalized_text="ähm",
        filler_type="hesitation",
        language="de",
        start_seconds=1.0,
        end_seconds=1.4,
        center_seconds=1.2,
        duration_seconds=0.4,
        confidence=0.75,
        remove_candidate=True,
        reason="lexicon_match",
        source_segment_index=0,
        source_word_index=2,
        source_item={"raw": "ähm"},
        warnings=["w1"],
        errors=[],
        metadata={"extra": True},
    )
    d = occ.to_dict()
    occ2 = FillerWordOccurrence.from_dict(d)
    assert occ2.text == "ähm"
    assert occ2.normalized_text == "ähm"
    assert occ2.filler_type == "hesitation"
    assert occ2.language == "de"
    assert occ2.start_seconds == pytest.approx(1.0)
    assert occ2.end_seconds == pytest.approx(1.4)
    assert occ2.duration_seconds == pytest.approx(0.4)
    assert occ2.remove_candidate is True
    assert occ2.source_word_index == 2
    assert occ2.warnings == ["w1"]
    assert occ2.metadata == {"extra": True}


# ─── 2. FillerWordDetectionResult roundtrip ────────────────────────────────

def test_filler_word_detection_result_roundtrip():
    occ = FillerWordOccurrence(
        text="um",
        normalized_text="um",
        filler_type="hesitation",
        language="en",
        confidence=0.75,
        remove_candidate=True,
        reason="lexicon_match",
    )
    result = FillerWordDetectionResult(
        status="ok",
        occurrences=[occ],
        occurrence_count=1,
        remove_candidate_count=1,
        counts_by_filler_type={"hesitation": 1},
        counts_by_language={"en": 1},
        total_filler_duration_seconds=0.3,
        warnings=[],
        errors=[],
        metadata={"job": "x"},
    )
    d = result.to_dict()
    result2 = FillerWordDetectionResult.from_dict(d)
    assert result2.status == "ok"
    assert result2.occurrence_count == 1
    assert len(result2.occurrences) == 1
    assert result2.occurrences[0].text == "um"
    assert result2.counts_by_filler_type == {"hesitation": 1}
    assert result2.counts_by_language == {"en": 1}
    assert result2.total_filler_duration_seconds == pytest.approx(0.3)
    assert result2.metadata == {"job": "x"}


# ─── 3. normalize_token ────────────────────────────────────────────────────

def test_normalize_token_keeps_umlauts_and_turkish_chars():
    assert normalize_token("Ähm,") == "ähm"
    assert normalize_token(" UM! ") == "um"
    assert normalize_token("şey...") == "şey"
    assert normalize_token("Öhm.") == "öhm"
    assert normalize_token("ğüş") == "ğüş"
    assert normalize_token(None) == ""
    assert normalize_token("") == ""
    assert normalize_token("(hello)") == "hello"


# ─── 4. default lexicon ────────────────────────────────────────────────────

def test_default_lexicon_contains_de_en_tr_fillers():
    lex = get_default_filler_lexicon()
    assert "ähm" in lex
    assert lex["ähm"]["language"] == "de"
    assert "um" in lex
    assert lex["um"]["language"] == "en"
    assert "you know" in lex
    assert lex["you know"]["filler_type"] == "phrase_filler"
    assert "şey" in lex
    assert lex["şey"]["language"] == "tr"
    assert "yani" in lex
    assert "işte" in lex
    for key, val in lex.items():
        assert "filler_type" in val
        assert "language" in val
        assert "confidence" in val


# ─── 5. extract_word_items from word dicts ─────────────────────────────────

def test_extract_word_items_from_word_dicts():
    items = [
        {"word": "ähm", "start_seconds": 0.5, "end_seconds": 0.9},
        {"word": "das", "start_seconds": 1.0, "end_seconds": 1.3},
        {"word": "war", "start_seconds": 1.4, "end_seconds": 1.6},
    ]
    result = extract_word_items(items)
    assert len(result) == 3
    assert result[0]["normalized_text"] == "ähm"
    assert result[0]["center_seconds"] == pytest.approx(0.7)
    assert result[0]["source_word_index"] == 0
    assert result[1]["normalized_text"] == "das"


# ─── 6. extract_word_items from segment text ───────────────────────────────

def test_extract_word_items_from_segments_with_text():
    seg = {"text": "ähm das war krass", "start_seconds": 10.0, "end_seconds": 14.0}
    result = extract_word_items([seg])
    assert len(result) == 4
    texts = [r["text"] for r in result]
    assert "ähm" in texts
    # Times should be distributed within [10, 14]
    for item in result:
        if item["start_seconds"] is not None:
            assert item["start_seconds"] >= 10.0
            assert item["end_seconds"] <= 14.0


# ─── 7. detect single German filler ───────────────────────────────────────

def test_detect_single_german_filler():
    result = detect_filler_words(["ähm", "das", "war", "krass"])
    assert result.occurrence_count == 1
    occ = result.occurrences[0]
    assert occ.normalized_text == "ähm"
    assert occ.language == "de"
    assert occ.filler_type == "hesitation"
    assert occ.remove_candidate is True


# ─── 8. detect single English filler ──────────────────────────────────────

def test_detect_single_english_filler():
    result = detect_filler_words(["um", "that", "was", "crazy"])
    assert result.occurrence_count == 1
    occ = result.occurrences[0]
    assert occ.language == "en"
    assert occ.filler_type == "hesitation"


# ─── 9. detect single Turkish filler ──────────────────────────────────────

def test_detect_single_turkish_filler():
    result = detect_filler_words(["şey", "çok", "iyi"])
    assert result.occurrence_count == 1
    assert result.occurrences[0].language == "tr"


# ─── 10. detect phrase filler "you know" ──────────────────────────────────

def test_detect_phrase_filler_you_know():
    result = detect_filler_words(["you", "know", "this", "was", "crazy"])
    assert result.occurrence_count == 1
    occ = result.occurrences[0]
    assert occ.text == "you know"
    assert occ.filler_type == "phrase_filler"


# ─── 11. detect phrase filler "i mean" ────────────────────────────────────

def test_detect_phrase_filler_i_mean():
    result = detect_filler_words(["i", "mean", "that", "was", "bad"])
    assert result.occurrence_count == 1
    assert result.occurrences[0].text == "i mean"


# ─── 12. detect repeated word ─────────────────────────────────────────────

def test_detect_repeated_word():
    result = detect_filler_words(["ich", "ich", "glaube"])
    assert result.occurrence_count >= 1
    filler_types = [o.filler_type for o in result.occurrences]
    assert "repeated_word" in filler_types


# ─── 13. repeated word gap respected ──────────────────────────────────────

def test_repeated_word_gap_respected():
    items = [
        {"word": "ich", "start_seconds": 0.0, "end_seconds": 1.0},
        {"word": "ich", "start_seconds": 2.0, "end_seconds": 2.5},
        {"word": "glaube", "start_seconds": 2.6, "end_seconds": 3.0},
    ]
    result = detect_filler_words(items, repeat_max_gap_seconds=0.35)
    filler_types = [o.filler_type for o in result.occurrences]
    assert "repeated_word" not in filler_types


# ─── 14. multiple fillers counts ──────────────────────────────────────────

def test_detect_multiple_fillers_counts():
    result = detect_filler_words(["ähm", "ich", "ich", "meine", "um", "wow"])
    assert result.occurrence_count >= 2
    assert "hesitation" in result.counts_by_filler_type
    assert "repeated_word" in result.counts_by_filler_type
    assert result.remove_candidate_count >= 1


# ─── 15. no words available safe ──────────────────────────────────────────

def test_no_words_available_safe():
    result_empty_list = detect_filler_words([])
    assert result_empty_list.status == "completed_with_warnings"
    assert "no_words_available" in result_empty_list.warnings
    assert result_empty_list.occurrence_count == 0

    result_empty_dict = detect_filler_words({})
    assert result_empty_dict.status == "completed_with_warnings"
    assert result_empty_dict.occurrence_count == 0


# ─── 16. bad input safe ───────────────────────────────────────────────────

def test_bad_input_safe():
    result = detect_filler_words([None, {}, {"word": None}, {"text": "ähm"}])
    assert result.status in ("ok", "completed_with_warnings", "failed")
    # Must not crash — ähm should ideally be detected
    # If it reaches here, safety is proven


# ─── 17. max_occurrences limits results ───────────────────────────────────

def test_max_occurrences_limits_results():
    # 5 fillers: ähm, um, ähm, um, ähm
    transcript = ["ähm", "the", "um", "and", "ähm", "then", "um", "but", "ähm", "done"]
    result = detect_filler_words(transcript, max_occurrences=2)
    assert result.occurrence_count == 2
    assert len(result.occurrences) == 2


# ─── 18. BOM and newline hygiene ──────────────────────────────────────────

def test_filler_detector_files_have_no_bom_and_end_with_newline():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = [
        os.path.join(base, "models", "filler_word.py"),
        os.path.join(base, "core", "filler_word_detector.py"),
        os.path.join(base, "tests", "test_filler_word_detector_foundation_smoke.py"),
    ]
    for path in files:
        assert os.path.isfile(path), f"Missing: {path}"
        with open(path, "rb") as f:
            raw = f.read()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {path}"
        assert raw.endswith(b"\n"), f"No trailing newline in {path}"
