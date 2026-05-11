from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from models.filler_word import FillerWordOccurrence
from models.filler_word_run import FillerWordRunReport
from models.filler_word_signal import FillerWordSignalAdapterResult
from core.filler_word_signal_adapter import (
    adapt_filler_word_run_report_to_signals,
    adapt_filler_words_to_signals,
    extract_filler_occurrence_dicts,
    filler_occurrence_to_signal,
)

_REPO_ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_occ_dict(
    text: str = "ähm",
    filler_type: str = "hesitation",
    start: float = 1.0,
    end: float = 1.2,
    confidence: float = 0.80,
    remove_candidate: bool = True,
) -> dict:
    return {
        "text": text,
        "normalized_text": text.lower(),
        "filler_type": filler_type,
        "language": "de",
        "start_seconds": start,
        "end_seconds": end,
        "center_seconds": (start + end) / 2.0,
        "duration_seconds": round(end - start, 4),
        "confidence": confidence,
        "remove_candidate": remove_candidate,
        "reason": "lexicon_match",
        "source_segment_index": 0,
        "source_word_index": 0,
        "source_item": {},
        "warnings": [],
        "errors": [],
        "metadata": {},
    }


# ---------------------------------------------------------------------------
# 1. Roundtrip
# ---------------------------------------------------------------------------

def test_filler_word_signal_adapter_result_roundtrip():
    result = FillerWordSignalAdapterResult(
        status="ok",
        signals=[{"signal_type": "hesitation_filler", "signal_score": 0.9}],
        signal_count=1,
        occurrence_count=1,
        high_priority_signal_count=1,
        signal_types={"hesitation_filler": 1},
        max_signal_score=0.9,
        avg_signal_score=0.9,
        total_signal_duration_seconds=0.2,
        warnings=[],
        errors=[],
        recommendation="use_filler_edit_signals",
        metadata={"foo": "bar"},
    )
    d = result.to_dict()
    restored = FillerWordSignalAdapterResult.from_dict(d)

    assert restored.status == "ok"
    assert restored.signal_count == 1
    assert restored.occurrence_count == 1
    assert restored.high_priority_signal_count == 1
    assert restored.signal_types == {"hesitation_filler": 1}
    assert abs(restored.max_signal_score - 0.9) < 1e-9
    assert abs(restored.avg_signal_score - 0.9) < 1e-9
    assert abs(restored.total_signal_duration_seconds - 0.2) < 1e-9
    assert restored.recommendation == "use_filler_edit_signals"
    assert restored.metadata == {"foo": "bar"}
    assert len(restored.signals) == 1
    assert restored.signals[0]["signal_type"] == "hesitation_filler"


# ---------------------------------------------------------------------------
# 2. extract_filler_occurrence_dicts — list of dicts
# ---------------------------------------------------------------------------

def test_extract_occurrence_dicts_from_list_of_dicts():
    occs = [_make_occ_dict("ähm"), _make_occ_dict("äh", start=2.0, end=2.1)]
    result = extract_filler_occurrence_dicts(occs)
    assert len(result) == 2
    assert result[0]["text"] == "ähm"
    assert result[1]["text"] == "äh"


# ---------------------------------------------------------------------------
# 3. extract_filler_occurrence_dicts — FillerWordOccurrence objects
# ---------------------------------------------------------------------------

def test_extract_occurrence_dicts_from_filler_occurrence_objects():
    occ = FillerWordOccurrence(
        text="ähm",
        normalized_text="ähm",
        filler_type="hesitation",
        start_seconds=5.0,
        end_seconds=5.3,
        confidence=0.85,
    )
    result = extract_filler_occurrence_dicts([occ])
    assert len(result) == 1
    assert result[0]["text"] == "ähm"
    assert result[0]["filler_type"] == "hesitation"
    assert result[0]["start_seconds"] == 5.0


# ---------------------------------------------------------------------------
# 4. extract_filler_occurrence_dicts — dict with "occurrences"
# ---------------------------------------------------------------------------

def test_extract_occurrence_dicts_from_run_report_dict():
    report_dict = {
        "status": "ok",
        "occurrences": [_make_occ_dict("also"), _make_occ_dict("halt", start=3.0, end=3.2)],
    }
    result = extract_filler_occurrence_dicts(report_dict)
    assert len(result) == 2
    assert result[0]["text"] == "also"


# ---------------------------------------------------------------------------
# 5. extract_filler_occurrence_dicts — job-like object
# ---------------------------------------------------------------------------

def test_extract_occurrence_dicts_from_job_like_object():
    job = SimpleNamespace(
        filler_word_occurrences=[
            _make_occ_dict("genau"),
            _make_occ_dict("ne", start=7.0, end=7.1),
        ]
    )
    result = extract_filler_occurrence_dicts(job)
    assert len(result) == 2
    assert result[0]["text"] == "genau"


# ---------------------------------------------------------------------------
# 6. hesitation occurrence → hesitation_filler signal
# ---------------------------------------------------------------------------

def test_filler_occurrence_to_signal_hesitation():
    occ = {
        "text": "ähm",
        "normalized_text": "ähm",
        "filler_type": "hesitation",
        "language": "de",
        "start_seconds": 10.0,
        "end_seconds": 10.2,
        "center_seconds": 10.1,
        "duration_seconds": 0.2,
        "confidence": 0.75,
        "remove_candidate": True,
        "reason": "lexicon_match",
    }
    sig = filler_occurrence_to_signal(occ)

    assert sig["signal_type"] == "hesitation_filler"
    assert sig["remove_candidate"] is True
    # score: 0.75 + 0.05 (remove) + 0.05 (hesitation) = 0.85
    assert abs(sig["signal_score"] - 0.85) < 1e-9
    # priority: 0.85 >= 0.80 → high
    assert sig["priority"] == "high"
    assert abs(sig["recommended_start_seconds"] - 9.85) < 1e-9
    assert abs(sig["recommended_end_seconds"] - 10.35) < 1e-9


# ---------------------------------------------------------------------------
# 7. discourse_marker → discourse_marker_filler
# ---------------------------------------------------------------------------

def test_filler_occurrence_to_signal_discourse_marker():
    occ = _make_occ_dict("also", filler_type="discourse_marker")
    sig = filler_occurrence_to_signal(occ)
    assert sig["signal_type"] == "discourse_marker_filler"


# ---------------------------------------------------------------------------
# 8. phrase_filler → phrase_filler
# ---------------------------------------------------------------------------

def test_filler_occurrence_to_signal_phrase_filler():
    occ = _make_occ_dict("ich meine", filler_type="phrase_filler")
    sig = filler_occurrence_to_signal(occ)
    assert sig["signal_type"] == "phrase_filler"


# ---------------------------------------------------------------------------
# 9. repeated_word → repeated_word_filler, higher score
# ---------------------------------------------------------------------------

def test_filler_occurrence_to_signal_repeated_word():
    occ = _make_occ_dict("das das", filler_type="repeated_word", confidence=0.70)
    sig = filler_occurrence_to_signal(occ)
    assert sig["signal_type"] == "repeated_word_filler"
    # score: 0.70 + 0.05 (remove) + 0.10 (repeated_word) = 0.85 → higher than confidence 0.70
    assert sig["signal_score"] > 0.70
    assert sig["priority"] in ("high", "medium")


# ---------------------------------------------------------------------------
# 10. center-only → recommended window around center
# ---------------------------------------------------------------------------

def test_filler_occurrence_to_signal_center_only():
    occ = {
        "text": "ehm",
        "normalized_text": "ehm",
        "filler_type": "hesitation",
        "language": "en",
        "start_seconds": None,
        "end_seconds": None,
        "center_seconds": 20.0,
        "confidence": 0.70,
        "remove_candidate": True,
        "reason": "",
    }
    sig = filler_occurrence_to_signal(occ)
    assert sig["recommended_start_seconds"] is not None
    assert sig["recommended_end_seconds"] is not None
    assert abs(sig["recommended_start_seconds"] - 19.85) < 1e-9
    assert abs(sig["recommended_end_seconds"] - 20.15) < 1e-9


# ---------------------------------------------------------------------------
# 11. adapt_filler_words_to_signals basic — 3 occurrences
# ---------------------------------------------------------------------------

def test_adapt_filler_words_to_signals_basic():
    occs = [
        _make_occ_dict("ähm", filler_type="hesitation", start=1.0, end=1.2, confidence=0.80),
        _make_occ_dict("also", filler_type="discourse_marker", start=3.0, end=3.3, confidence=0.70),
        _make_occ_dict("das das", filler_type="repeated_word", start=5.0, end=5.4, confidence=0.75),
    ]
    result = adapt_filler_words_to_signals(occs)

    assert result.signal_count == 3
    assert "hesitation_filler" in result.signal_types
    assert "discourse_marker_filler" in result.signal_types
    assert "repeated_word_filler" in result.signal_types
    assert result.max_signal_score > 0.0
    assert result.status in ("ok", "completed_with_warnings")


# ---------------------------------------------------------------------------
# 12. adapt_filler_words_to_signals max_signals=2
# ---------------------------------------------------------------------------

def test_adapt_filler_words_to_signals_max_signals():
    occs = [
        _make_occ_dict("ähm", filler_type="hesitation", start=1.0, end=1.2, confidence=0.90),
        _make_occ_dict("ne", filler_type="discourse_marker", start=2.0, end=2.1, confidence=0.50),
        _make_occ_dict("das das", filler_type="repeated_word", start=5.0, end=5.4, confidence=0.85),
    ]
    result = adapt_filler_words_to_signals(occs, max_signals=2)

    assert result.signal_count == 2
    scores = [s["signal_score"] for s in result.signals]
    # The 2 strongest should be kept (hesitation: 0.90+0.05+0.05=1.0, repeated_word: 0.85+0.05+0.10=1.0)
    assert all(sc >= 0.0 for sc in scores)


# ---------------------------------------------------------------------------
# 13. no occurrences → skipped_no_fillers
# ---------------------------------------------------------------------------

def test_adapt_filler_words_to_signals_no_occurrences():
    result = adapt_filler_words_to_signals([])
    assert result.status == "skipped_no_fillers"
    assert result.recommendation == "no_filler_occurrences_available"
    assert result.signal_count == 0


# ---------------------------------------------------------------------------
# 14. adapt_filler_word_run_report_to_signals
# ---------------------------------------------------------------------------

def test_adapt_filler_word_run_report_to_signals():
    report = FillerWordRunReport(
        status="ok",
        recommendation="review",
        occurrences=[
            _make_occ_dict("ähm", filler_type="hesitation", start=1.0, end=1.2),
            _make_occ_dict("also", filler_type="discourse_marker", start=3.0, end=3.3),
        ],
        occurrence_count=2,
        transcript_source="whisper",
    )
    result = adapt_filler_word_run_report_to_signals(report)

    assert result.signal_count > 0
    assert "filler_word_status" in result.metadata
    assert "occurrence_count" in result.metadata
    assert result.metadata["occurrence_count"] == 2
    assert result.metadata.get("transcript_source") == "whisper"


# ---------------------------------------------------------------------------
# 15. bad occurrence data does not crash
# ---------------------------------------------------------------------------

def test_bad_occurrence_data_does_not_crash():
    occs = [
        {},
        {"text": None, "confidence": "bad"},
        _make_occ_dict("gut", filler_type="hesitation", start=10.0, end=10.2, confidence=0.85),
    ]
    result = adapt_filler_words_to_signals(occs)
    assert result.signal_count >= 1
    # at least the good occurrence became a signal
    good_signals = [s for s in result.signals if s.get("signal_type") == "hesitation_filler"]
    assert len(good_signals) >= 1


# ---------------------------------------------------------------------------
# 16. signal output satisfies future-edit-logic contract
# ---------------------------------------------------------------------------

def test_signal_output_can_feed_future_edit_logic_contract():
    occ = _make_occ_dict("ähm", filler_type="hesitation", start=5.0, end=5.3, confidence=0.80)
    sig = filler_occurrence_to_signal(occ)

    required_keys = [
        "signal_type",
        "start_seconds",
        "end_seconds",
        "center_seconds",
        "recommended_start_seconds",
        "recommended_end_seconds",
        "signal_score",
        "priority",
        "remove_candidate",
        "reason",
        "source_occurrence",
    ]
    for key in required_keys:
        assert key in sig, f"Missing required key: {key}"

    assert sig["signal_type"] == "hesitation_filler"
    assert isinstance(sig["signal_score"], float)
    assert sig["priority"] in ("high", "medium", "low")
    assert isinstance(sig["remove_candidate"], bool)
    assert isinstance(sig["reason"], str)
    assert isinstance(sig["source_occurrence"], dict)


# ---------------------------------------------------------------------------
# 17. BOM and newline hygiene
# ---------------------------------------------------------------------------

def test_filler_word_signal_adapter_files_have_no_bom_and_end_with_newline():
    files = [
        _REPO_ROOT / "models" / "filler_word_signal.py",
        _REPO_ROOT / "core" / "filler_word_signal_adapter.py",
        _REPO_ROOT / "tests" / "test_filler_word_signal_adapter_smoke.py",
    ]
    for path in files:
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {path.name}"
        assert raw.endswith(b"\n"), f"Missing trailing newline in {path.name}"
