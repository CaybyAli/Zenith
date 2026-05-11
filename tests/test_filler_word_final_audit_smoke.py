from __future__ import annotations

import inspect
import types
from types import SimpleNamespace
from typing import Any

import pytest

from models.filler_word import FillerWordDetectionResult, FillerWordOccurrence
from models.filler_word_run import FillerWordRunReport
from models.filler_word_signal import FillerWordSignalAdapterResult
from core.filler_word_detector import (
    detect_filler_words,
    extract_word_items,
    get_default_filler_lexicon,
    normalize_token,
)
from core.filler_word_runner import (
    build_filler_word_run_report,
    extract_transcript_source_from_job,
    run_filler_word_detection_for_job,
)
from core.filler_word_signal_adapter import (
    adapt_filler_word_run_report_to_signals,
    adapt_filler_words_to_signals,
)


# ---------------------------------------------------------------------------
# Test 1 — Model roundtrips
# ---------------------------------------------------------------------------

def test_2b10_models_roundtrip():
    occ = FillerWordOccurrence(
        text="ähm",
        normalized_text="ähm",
        filler_type="hesitation",
        language="de",
        start_seconds=1.0,
        end_seconds=1.5,
        center_seconds=1.25,
        duration_seconds=0.5,
        confidence=0.75,
        remove_candidate=True,
        reason="lexicon_match",
        source_segment_index=0,
        source_word_index=2,
        source_item={"raw": "Ähm"},
        warnings=[],
        errors=[],
        metadata={"extra": 1},
    )
    occ2 = FillerWordOccurrence.from_dict(occ.to_dict())
    assert occ2.text == "ähm"
    assert occ2.filler_type == "hesitation"
    assert occ2.language == "de"
    assert occ2.start_seconds == 1.0
    assert occ2.center_seconds == 1.25
    assert occ2.metadata == {"extra": 1}

    det = FillerWordDetectionResult(
        status="ok",
        occurrences=[occ],
        occurrence_count=1,
        remove_candidate_count=1,
        counts_by_filler_type={"hesitation": 1},
        counts_by_language={"de": 1},
        total_filler_duration_seconds=0.5,
    )
    det2 = FillerWordDetectionResult.from_dict(det.to_dict())
    assert det2.status == "ok"
    assert det2.occurrence_count == 1
    assert len(det2.occurrences) == 1
    assert det2.occurrences[0].filler_type == "hesitation"

    report = FillerWordRunReport(
        status="ok",
        occurrence_count=1,
        remove_candidate_count=1,
        counts_by_filler_type={"hesitation": 1},
        counts_by_language={"de": 1},
        transcript_word_count=10,
        filler_rate=0.1,
        recommendation="use_filler_word_analysis",
    )
    report2 = FillerWordRunReport.from_dict(report.to_dict())
    assert report2.status == "ok"
    assert report2.occurrence_count == 1
    assert report2.filler_rate == 0.1

    sig_result = FillerWordSignalAdapterResult(
        status="ok",
        signals=[{"signal_type": "hesitation_filler"}],
        signal_count=1,
        occurrence_count=1,
        recommendation="use_filler_edit_signals",
    )
    sig_result2 = FillerWordSignalAdapterResult.from_dict(sig_result.to_dict())
    assert sig_result2.status == "ok"
    assert sig_result2.signal_count == 1
    assert sig_result2.signals[0]["signal_type"] == "hesitation_filler"


# ---------------------------------------------------------------------------
# Test 2 — Normalization + lexicon contract
# ---------------------------------------------------------------------------

def test_2b10_detector_normalization_and_lexicon_contract():
    assert normalize_token("Ähm,") == "ähm"
    assert normalize_token(" UM! ") == "um"
    assert normalize_token("şey...") == "şey"
    assert normalize_token("") == ""
    assert normalize_token(None) == ""
    assert normalize_token(42) == "42"

    lex = get_default_filler_lexicon()
    required = ["ähm", "um", "you know", "i mean", "şey", "yani"]
    for word in required:
        assert word in lex, f"Missing from lexicon: {word!r}"

    assert lex["ähm"]["language"] == "de"
    assert lex["um"]["language"] == "en"
    assert lex["şey"]["language"] == "tr"
    assert lex["you know"]["filler_type"] == "phrase_filler"
    assert lex["i mean"]["filler_type"] == "phrase_filler"
    assert lex["yani"]["language"] == "tr"


# ---------------------------------------------------------------------------
# Test 3 — Core detection contract
# ---------------------------------------------------------------------------

def test_2b10_detector_core_detection_contract():
    def _detect(words: list[str]) -> FillerWordDetectionResult:
        return detect_filler_words(words)

    # German hesitation
    r = _detect(["ähm", "das", "war"])
    types_found = {o.filler_type for o in r.occurrences}
    langs_found = {o.language for o in r.occurrences}
    assert "hesitation" in types_found
    assert "de" in langs_found

    # English hesitation
    r = _detect(["um", "that", "was"])
    types_found = {o.filler_type for o in r.occurrences}
    assert "hesitation" in types_found
    langs = {o.language for o in r.occurrences}
    assert "en" in langs

    # Turkish hesitation
    r = _detect(["şey", "çok", "iyi"])
    types_found = {o.filler_type for o in r.occurrences}
    assert "hesitation" in types_found
    langs = {o.language for o in r.occurrences}
    assert "tr" in langs

    # Phrase filler: "you know"
    r = _detect(["you", "know", "this"])
    types_found = {o.filler_type for o in r.occurrences}
    assert "phrase_filler" in types_found

    # Phrase filler: "i mean"
    r = _detect(["i", "mean", "this"])
    types_found = {o.filler_type for o in r.occurrences}
    assert "phrase_filler" in types_found

    # repeated_word (no timing → gap check skipped → should detect)
    r = _detect(["ich", "ich", "glaube"])
    types_found = {o.filler_type for o in r.occurrences}
    assert "repeated_word" in types_found

    # Large repeat gap should suppress repeated_word
    word_items = [
        {"text": "ja", "normalized_text": "ja", "start_seconds": 0.0, "end_seconds": 0.3,
         "center_seconds": 0.15, "source_segment_index": None, "source_word_index": 0, "source_item": {}},
        {"text": "ja", "normalized_text": "ja", "start_seconds": 5.0, "end_seconds": 5.3,
         "center_seconds": 5.15, "source_segment_index": None, "source_word_index": 1, "source_item": {}},
    ]
    r2 = detect_filler_words(word_items)
    repeat_occs = [o for o in r2.occurrences if o.filler_type == "repeated_word"]
    assert len(repeat_occs) == 0, "Large gap should suppress repeated_word"


# ---------------------------------------------------------------------------
# Test 4 — Word extraction contract
# ---------------------------------------------------------------------------

def test_2b10_word_extraction_contract():
    # list[str]
    items = extract_word_items(["ähm", "das", "war"])
    assert len(items) == 3
    assert items[0]["text"] == "ähm"
    assert items[0]["start_seconds"] is None

    # list[dict] with word/start/end
    word_dicts = [
        {"word": "ähm", "start": 0.0, "end": 0.3},
        {"word": "das", "start": 0.4, "end": 0.7},
    ]
    items2 = extract_word_items(word_dicts)
    assert len(items2) == 2
    assert items2[0]["start_seconds"] == 0.0
    assert items2[0]["center_seconds"] == pytest.approx(0.15)

    # dict with "words"
    items3 = extract_word_items({"words": ["hallo", "welt"]})
    assert len(items3) == 2

    # dict with "segments"
    seg_data = {
        "segments": [
            {"text": "ähm das war", "start": 0.0, "end": 3.0}
        ]
    }
    items4 = extract_word_items(seg_data)
    assert len(items4) == 3
    assert items4[0]["start_seconds"] is not None
    assert items4[0]["end_seconds"] is not None

    # None → safe
    assert extract_word_items(None) == []
    # Empty list → safe
    assert extract_word_items([]) == []
    # Broken items don't crash (mixed list with non-str, non-dict first item falls
    # into the object path; the contract only guarantees no crash)
    items5 = extract_word_items([None, 42, {"word": "ok"}])
    assert isinstance(items5, list)


# ---------------------------------------------------------------------------
# Test 5 — Runner contract
# ---------------------------------------------------------------------------

def test_2b10_runner_contract():
    # provided transcript with fillers → occurrence_count > 0
    rpt = build_filler_word_run_report(
        transcript_data=["ähm", "ich", "ich", "meine"],
        transcript_source="test",
    )
    assert rpt.occurrence_count > 0
    assert rpt.transcript_word_count > 0
    assert rpt.status in {"ok", "completed_with_warnings"}

    # no transcript → skipped_no_transcript
    rpt2 = build_filler_word_run_report(transcript_data=None)
    assert rpt2.status == "skipped_no_transcript"

    # empty transcript → safe skipped
    rpt3 = build_filler_word_run_report(transcript_data=[])
    assert rpt3.status == "skipped_no_transcript"

    # no fillers → no_fillers_detected
    rpt4 = build_filler_word_run_report(transcript_data=["hallo", "welt", "foo"])
    assert "no_fillers_detected" in rpt4.warnings or rpt4.recommendation == "no_fillers_detected"

    # segment data → word_count > 0 + occurrence_count > 0
    seg_data = {"segments": [{"text": "ähm das war super", "start": 0.0, "end": 4.0}]}
    rpt5 = build_filler_word_run_report(transcript_data=seg_data, transcript_source="segments")
    assert rpt5.transcript_word_count > 0
    assert rpt5.occurrence_count > 0

    # max_occurrences limit
    rpt6 = build_filler_word_run_report(
        transcript_data=["ähm", "um", "ähm", "um", "ähm"],
        max_occurrences=2,
    )
    assert rpt6.occurrence_count <= 2

    # preview is small
    rpt7 = build_filler_word_run_report(transcript_data=["ähm"])
    preview = rpt7.transcript_data_preview
    assert isinstance(preview, dict)


# ---------------------------------------------------------------------------
# Test 6 — Job runner source fallback contract
# ---------------------------------------------------------------------------

def test_2b10_job_runner_source_fallback_contract():
    # transcript_data wins over speech_segments
    job = SimpleNamespace(
        transcript_data=["ähm", "ich", "ich"],
        speech_segments=["other", "data"],
        metadata={},
    )
    data, src = extract_transcript_source_from_job(job)
    assert data == ["ähm", "ich", "ich"]
    assert "transcript_data" in src

    # speech_segments fallback
    job2 = SimpleNamespace(
        transcript_data=None,
        speech_segments=["ähm", "hallo"],
        metadata={},
    )
    data2, src2 = extract_transcript_source_from_job(job2)
    assert data2 == ["ähm", "hallo"]
    assert "speech_segments" in src2

    # metadata["transcript"] fallback
    job3 = SimpleNamespace(
        transcript_data=None,
        speech_segments=None,
        metadata={"transcript": ["um", "yeah"]},
    )
    data3, src3 = extract_transcript_source_from_job(job3)
    assert data3 == ["um", "yeah"]

    # provided transcript_data overrides job
    job4 = SimpleNamespace(transcript_data=["ähm"], metadata={})
    rpt = run_filler_word_detection_for_job(job4, transcript_data=["um", "you", "know"])
    assert rpt.transcript_source == "provided_transcript_data"

    # empty job → no crash
    job5 = SimpleNamespace()
    rpt5 = run_filler_word_detection_for_job(job5)
    assert rpt5.status == "skipped_no_transcript"

    # broken job fields → no crash
    job6 = SimpleNamespace(transcript_data=object(), metadata="bad")
    rpt6 = run_filler_word_detection_for_job(job6)
    assert rpt6 is not None


# ---------------------------------------------------------------------------
# Test 7 — Signal adapter contract
# ---------------------------------------------------------------------------

def test_2b10_signal_adapter_contract():
    def _make_occ(filler_type: str, **kwargs) -> dict[str, Any]:
        base = {
            "text": filler_type,
            "normalized_text": filler_type,
            "filler_type": filler_type,
            "language": "de",
            "start_seconds": 1.0,
            "end_seconds": 1.5,
            "center_seconds": 1.25,
            "duration_seconds": 0.5,
            "confidence": 0.75,
            "remove_candidate": True,
            "reason": "test",
        }
        base.update(kwargs)
        return base

    # hesitation → hesitation_filler
    r = adapt_filler_words_to_signals([_make_occ("hesitation")])
    assert r.signals[0]["signal_type"] == "hesitation_filler"

    # discourse_marker → discourse_marker_filler
    r = adapt_filler_words_to_signals([_make_occ("discourse_marker")])
    assert r.signals[0]["signal_type"] == "discourse_marker_filler"

    # phrase_filler → phrase_filler
    r = adapt_filler_words_to_signals([_make_occ("phrase_filler")])
    assert r.signals[0]["signal_type"] == "phrase_filler"

    # repeated_word → repeated_word_filler
    r = adapt_filler_words_to_signals([_make_occ("repeated_word")])
    assert r.signals[0]["signal_type"] == "repeated_word_filler"

    # center-only fallback (no start/end)
    occ_no_se = {
        "text": "ähm", "normalized_text": "ähm", "filler_type": "hesitation",
        "language": "de", "start_seconds": None, "end_seconds": None,
        "center_seconds": 2.0, "confidence": 0.75, "remove_candidate": True, "reason": "",
    }
    r2 = adapt_filler_words_to_signals([occ_no_se])
    sig = r2.signals[0]
    assert sig["recommended_start_seconds"] is not None
    assert sig["recommended_end_seconds"] is not None

    # recommended windows present
    r3 = adapt_filler_words_to_signals([_make_occ("hesitation")])
    sig3 = r3.signals[0]
    assert "recommended_start_seconds" in sig3
    assert "recommended_end_seconds" in sig3

    # signal_score and priority
    assert "signal_score" in sig3
    assert "priority" in sig3
    assert sig3["priority"] in {"high", "medium", "low"}

    # max_signals limit
    occs = [_make_occ("hesitation", center_seconds=float(i)) for i in range(5)]
    r4 = adapt_filler_words_to_signals(occs, max_signals=3)
    assert r4.signal_count == 3

    # no occurrences → safe
    r5 = adapt_filler_words_to_signals([])
    assert r5.status == "skipped_no_fillers"

    # bad occurrence data → safe
    r6 = adapt_filler_words_to_signals([None, {}, "broken"])
    assert r6 is not None


# ---------------------------------------------------------------------------
# Test 8 — Integrated flow: transcript → filler → signal
# ---------------------------------------------------------------------------

def test_2b10_integrated_flow_transcript_to_filler_to_signal():
    words = ["ähm", "ich", "ich", "meine", "you", "know", "wow"]

    det = detect_filler_words(words)
    assert det.occurrence_count > 0

    found_types = {o.filler_type for o in det.occurrences}
    assert "repeated_word" in found_types, "Should detect 'ich ich' as repeated_word"
    assert "phrase_filler" in found_types, "Should detect 'you know' as phrase_filler"

    report = build_filler_word_run_report(transcript_data=words, transcript_source="test")
    assert report.occurrence_count > 0

    sig_result = adapt_filler_word_run_report_to_signals(report)
    assert sig_result.signal_count > 0

    # All signals are future-edit-compatible
    for sig in sig_result.signals:
        assert "signal_type" in sig
        assert "signal_score" in sig
        assert "priority" in sig
        assert "remove_candidate" in sig
        assert "reason" in sig
        assert "source_occurrence" in sig
        assert "recommended_start_seconds" in sig
        assert "recommended_end_seconds" in sig
        # Timing keys must be present (values may be None for plain-string transcripts)
        assert "start_seconds" in sig
        assert "center_seconds" in sig


# ---------------------------------------------------------------------------
# Test 9 — Job and pipeline contract
# ---------------------------------------------------------------------------

def test_2b10_job_and_pipeline_contract():
    from models.job import Job
    from shared.enums import (
        AutopublishClass, ChannelType, JobStatus, JobType,
        Mode, TargetFormat, ValidatorStatus,
    )

    j = Job(
        job_id="audit-test-001",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.LONGFORM,
        target_platforms=["youtube"],
        status=JobStatus.CREATED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="inbox/gaming_main/test.mp4",
    )
    j.filler_word_report = {"status": "skipped_no_transcript", "occurrence_count": 0}
    j.filler_word_status = "skipped_no_transcript"
    j.filler_word_transcript_source = None
    j.filler_word_detection_result = {}
    j.filler_word_occurrences = []
    j.filler_word_occurrence_count = 0
    j.filler_word_remove_candidate_count = 0
    j.filler_word_counts_by_type = {}
    j.filler_word_counts_by_language = {}
    j.filler_word_total_duration_seconds = 0.0
    j.filler_word_transcript_word_count = 0
    j.filler_word_rate = 0.0
    j.filler_word_recommendation = "no_transcript_available"

    d = j.to_dict()
    j2 = Job.from_dict(d)
    assert j2.filler_word_status == "skipped_no_transcript"
    assert j2.filler_word_occurrence_count == 0
    assert j2.filler_word_recommendation == "no_transcript_available"
    assert isinstance(j2.filler_word_counts_by_type, dict)
    assert isinstance(j2.filler_word_occurrences, list)

    # Check gaming_pipeline.py imports run_filler_word_detection_for_job
    import core.gaming_pipeline as gp
    src = inspect.getsource(gp)

    assert "run_filler_word_detection_for_job" in src
    assert "detect_filler_words" not in [
        line.split("import")[-1].strip()
        for line in src.splitlines()
        if line.strip().startswith("from core.filler_word_detector import") or
           line.strip().startswith("import core.filler_word_detector")
    ], "gaming_pipeline must not import detect_filler_words directly"

    assert "extract_word_items" not in [
        line.split("import")[-1].strip()
        for line in src.splitlines()
        if line.strip().startswith("from core.filler_word_detector import") or
           line.strip().startswith("import core.filler_word_detector")
    ], "gaming_pipeline must not import extract_word_items directly"

    # Decision event names present
    for event in [
        "FILLER_WORD_DETECTION_STARTED",
        "FILLER_WORD_DETECTION_DONE",
        "FILLER_WORD_DETECTION_COMPLETED_WITH_WARNINGS",
        "FILLER_WORD_DETECTION_SKIPPED",
        "FILLER_WORD_DETECTION_FAILED",
    ]:
        assert event in src, f"Missing event in gaming_pipeline: {event}"

    # Checkpoint present
    assert "filler_word_detection_done" in src

    # Job assignment lines present
    for assignment in [
        "job.filler_word_report =",
        "job.filler_word_status =",
        "job.filler_word_occurrences =",
        "job.filler_word_occurrence_count =",
        "job.filler_word_rate =",
    ]:
        assert assignment in src, f"Missing assignment in gaming_pipeline: {assignment}"

    # Event ordering: ENERGY_PEAK < SILENCE_CLASSIFICATION < FILLER_WORD < STATE_ANALYZING
    idx_energy = src.index("ENERGY_PEAK_DETECTION_STARTED")
    idx_silence = src.index("SILENCE_CLASSIFICATION_STARTED")
    idx_filler = src.index("FILLER_WORD_DETECTION_STARTED")
    idx_analyzing = src.index("STATE_ANALYZING")

    assert idx_energy < idx_filler, "ENERGY_PEAK_DETECTION_STARTED must come before FILLER_WORD_DETECTION_STARTED"
    assert idx_silence < idx_filler, "SILENCE_CLASSIFICATION_STARTED must come before FILLER_WORD_DETECTION_STARTED"
    assert idx_filler < idx_analyzing, "FILLER_WORD_DETECTION_STARTED must come before STATE_ANALYZING"


# ---------------------------------------------------------------------------
# Test 10 — BOM and trailing newline hygiene
# ---------------------------------------------------------------------------

def test_2b10_files_have_no_bom_and_end_with_newline():
    import pathlib

    files_to_check = [
        "models/filler_word.py",
        "core/filler_word_detector.py",
        "models/filler_word_run.py",
        "core/filler_word_runner.py",
        "models/filler_word_signal.py",
        "core/filler_word_signal_adapter.py",
        "tests/test_filler_word_detector_foundation_smoke.py",
        "tests/test_filler_word_runner_smoke.py",
        "tests/test_filler_word_pipeline_integration_smoke.py",
        "tests/test_filler_word_signal_adapter_smoke.py",
        "tests/test_filler_word_final_audit_smoke.py",
        "core/gaming_pipeline.py",
        "models/job.py",
    ]

    repo_root = pathlib.Path(__file__).parent.parent
    bom_violations: list[str] = []
    newline_violations: list[str] = []

    for rel_path in files_to_check:
        p = repo_root / rel_path
        assert p.exists(), f"Expected file not found: {rel_path}"
        raw = p.read_bytes()

        if raw.startswith(b"\xef\xbb\xbf"):
            bom_violations.append(rel_path)
            fixed = raw[3:]
            p.write_bytes(fixed)

        content = p.read_bytes()
        if not content.endswith(b"\n"):
            newline_violations.append(rel_path)
            p.write_bytes(content + b"\n")

    assert bom_violations == [], f"BOM found and removed in: {bom_violations}"
    assert newline_violations == [], f"Missing trailing newline fixed in: {newline_violations}"
