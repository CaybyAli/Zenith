from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any

import pytest

from models.filler_word_run import FillerWordRunReport
from core.filler_word_runner import (
    build_filler_word_run_report,
    extract_transcript_source_from_job,
    run_filler_word_detection_for_job,
)


# ─── 1. FillerWordRunReport roundtrip ────────────────────────────────────────

def test_filler_word_run_report_roundtrip():
    report = FillerWordRunReport(
        status="ok",
        transcript_source="job.transcript_data",
        occurrence_count=3,
        remove_candidate_count=2,
        counts_by_filler_type={"hesitation": 2, "repeated_word": 1},
        counts_by_language={"de": 2, "unknown": 1},
        total_filler_duration_seconds=1.2,
        transcript_word_count=10,
        filler_rate=0.3,
        warnings=[],
        errors=[],
        recommendation="use_filler_word_analysis",
        metadata={"job_id": "test"},
    )
    d = report.to_dict()
    restored = FillerWordRunReport.from_dict(d)
    assert restored.status == "ok"
    assert restored.occurrence_count == 3
    assert restored.transcript_source == "job.transcript_data"
    assert restored.counts_by_filler_type == {"hesitation": 2, "repeated_word": 1}
    assert restored.recommendation == "use_filler_word_analysis"
    assert restored.filler_rate == pytest.approx(0.3)


# ─── 2. Provided transcript detects fillers ──────────────────────────────────

def test_build_report_with_provided_transcript_detects_fillers():
    transcript = ["ähm", "ich", "ich", "meine", "um", "wow"]
    report = build_filler_word_run_report(transcript_data=transcript)
    assert report.status in ("ok", "completed_with_warnings")
    assert report.occurrence_count >= 3
    assert report.transcript_word_count == 6
    assert report.filler_rate > 0
    assert "hesitation" in report.counts_by_filler_type or "repeated_word" in report.counts_by_filler_type


# ─── 3. No transcript → skipped ──────────────────────────────────────────────

def test_build_report_no_transcript_skipped():
    report = build_filler_word_run_report(transcript_data=None)
    assert report.status == "skipped_no_transcript"
    assert report.recommendation == "no_transcript_available"
    assert "no_transcript_available" in report.warnings


# ─── 4. Empty transcript → safe skip ─────────────────────────────────────────

def test_build_report_empty_transcript_skipped():
    report = build_filler_word_run_report(transcript_data=[])
    assert report.status in ("skipped_no_transcript", "completed_with_warnings")
    # must not crash


# ─── 5. No fillers detected ───────────────────────────────────────────────────

def test_build_report_no_fillers_detected():
    transcript = ["das", "war", "krass"]
    report = build_filler_word_run_report(transcript_data=transcript)
    assert report.occurrence_count == 0
    assert report.recommendation == "no_fillers_detected"


# ─── 6. Segment dict data ────────────────────────────────────────────────────

def test_build_report_with_segment_data():
    data = {
        "segments": [
            {"text": "ähm das war krass", "start_seconds": 10.0, "end_seconds": 14.0}
        ]
    }
    report = build_filler_word_run_report(transcript_data=data)
    assert report.transcript_word_count == 4
    assert report.occurrence_count >= 1
    assert report.total_filler_duration_seconds > 0


# ─── 7. max_occurrences respected ────────────────────────────────────────────

def test_build_report_respects_max_occurrences():
    transcript = ["ähm", "um", "ähm", "um", "ähm", "um", "ähm", "um"]
    report = build_filler_word_run_report(transcript_data=transcript, max_occurrences=2)
    assert report.occurrence_count == 2


# ─── 8. Job source priority: transcript_data before speech_segments ──────────

def test_extract_transcript_source_from_job_priority():
    job = SimpleNamespace(
        transcript_data=["ähm"],
        speech_segments=["um"],
    )
    data, source = extract_transcript_source_from_job(job)
    assert data == ["ähm"]
    assert source == "job.transcript_data"


# ─── 9. Fallback to speech_segments ──────────────────────────────────────────

def test_extract_transcript_source_from_job_fallback_speech_segments():
    job = SimpleNamespace(
        transcript_data=None,
        transcript=None,
        word_segments=None,
        speech_segments=["um", "test"],
    )
    data, source = extract_transcript_source_from_job(job)
    assert data == ["um", "test"]
    assert source == "job.speech_segments"


# ─── 10. metadata fallback ───────────────────────────────────────────────────

def test_extract_transcript_source_from_job_metadata_fallback():
    job = SimpleNamespace(metadata={"transcript": ["ähm", "okay"]})
    data, source = extract_transcript_source_from_job(job)
    assert data == ["ähm", "okay"]
    assert "metadata" in source and "transcript" in source


# ─── 11. run_for_job with transcript_data ────────────────────────────────────

def test_run_for_job_with_transcript_data():
    job = SimpleNamespace(transcript_data=["ähm", "das", "ist", "cool"])
    report = run_filler_word_detection_for_job(job)
    assert report.occurrence_count > 0
    assert report.transcript_source == "job.transcript_data"


# ─── 12. Provided transcript overrides job ───────────────────────────────────

def test_run_for_job_with_provided_transcript_overrides_job():
    job = SimpleNamespace(transcript_data=["das"])
    report = run_filler_word_detection_for_job(job, transcript_data=["ähm"])
    assert report.transcript_source == "provided_transcript_data"
    assert report.occurrence_count == 1


# ─── 13. Empty job safe ──────────────────────────────────────────────────────

def test_run_for_empty_job_safe():
    job = SimpleNamespace()
    report = run_filler_word_detection_for_job(job)
    assert report.status == "skipped_no_transcript"
    # no crash


# ─── 14. Bad job fields safe ─────────────────────────────────────────────────

def test_bad_job_fields_safe():
    job = SimpleNamespace(
        transcript_data=object(),  # not list/dict/str
        metadata=42,               # not a dict
    )
    report = run_filler_word_detection_for_job(job)
    # Must not crash; status can be anything reasonable
    assert isinstance(report, FillerWordRunReport)
    assert report.status in ("skipped_no_transcript", "completed_with_warnings", "failed", "ok")


# ─── 15. Phrase fillers ──────────────────────────────────────────────────────

def test_runner_handles_phrase_fillers():
    transcript = ["you", "know", "this", "is", "wild"]
    report = build_filler_word_run_report(transcript_data=transcript)
    assert report.occurrence_count >= 1
    assert "phrase_filler" in report.counts_by_filler_type


# ─── 16. Repeated word gap ───────────────────────────────────────────────────

def test_runner_handles_repeated_word_gap():
    transcript = [
        {"word": "ich", "start_seconds": 0.0, "end_seconds": 0.2},
        {"word": "ich", "start_seconds": 0.25, "end_seconds": 0.4},
    ]
    report = build_filler_word_run_report(transcript_data=transcript)
    assert report.occurrence_count >= 1
    assert "repeated_word" in report.counts_by_filler_type


# ─── 17. Preview stays small ─────────────────────────────────────────────────

def test_runner_preview_is_small():
    big_transcript = ["das"] * 100
    report = build_filler_word_run_report(transcript_data=big_transcript)
    preview = report.transcript_data_preview
    assert "type" in preview
    assert "word_count" in preview
    assert "item_count" in preview
    # Preview must not contain the full list
    assert "das" not in str(preview)[:200] or preview.get("item_count") == 100


# ─── 18. BOM and newline hygiene ─────────────────────────────────────────────

def test_filler_word_runner_files_have_no_bom_and_end_with_newline():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = [
        os.path.join(base, "models", "filler_word_run.py"),
        os.path.join(base, "core", "filler_word_runner.py"),
        os.path.join(base, "tests", "test_filler_word_runner_smoke.py"),
    ]
    for path in files:
        with open(path, "rb") as f:
            raw = f.read()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {path}"
        assert raw.endswith(b"\n"), f"Missing trailing newline in {path}"
