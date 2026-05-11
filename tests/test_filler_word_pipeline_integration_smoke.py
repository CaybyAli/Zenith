from __future__ import annotations

import os

import pytest

from models.job import Job
from models.filler_word_run import FillerWordRunReport
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
_PIPELINE_PATH = os.path.join(_REPO_ROOT, "core", "gaming_pipeline.py")
_JOB_MODEL_PATH = os.path.join(_REPO_ROOT, "models", "job.py")
_TEST_PATH = os.path.join(_THIS_DIR, "test_filler_word_pipeline_integration_smoke.py")


def _make_job(**kwargs) -> Job:
    defaults = dict(
        job_id="test-filler-word-pipeline-001",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
    )
    defaults.update(kwargs)
    return Job(**defaults)


def _read_pipeline_source() -> str:
    with open(_PIPELINE_PATH, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# 1. Job roundtrip preserves filler word fields
# ---------------------------------------------------------------------------

def test_job_roundtrip_preserves_filler_word_fields():
    job = _make_job(
        filler_word_report={"status": "ok"},
        filler_word_status="ok",
        filler_word_transcript_source="job.transcript_data",
        filler_word_detection_result={"status": "ok", "occurrence_count": 3},
        filler_word_occurrences=[
            {"text": "ähm", "filler_type": "hesitation", "language": "de"},
            {"text": "um", "filler_type": "hesitation", "language": "en"},
            {"text": "ich ich", "filler_type": "repeated_word", "language": "de"},
        ],
        filler_word_occurrence_count=3,
        filler_word_remove_candidate_count=3,
        filler_word_counts_by_type={"hesitation": 2, "repeated_word": 1},
        filler_word_counts_by_language={"de": 2, "en": 1},
        filler_word_total_duration_seconds=1.4,
        filler_word_transcript_word_count=12,
        filler_word_rate=0.25,
        filler_word_recommendation="use_filler_word_analysis",
    )

    d = job.to_dict()
    restored = Job.from_dict(d)

    assert restored.filler_word_report == {"status": "ok"}
    assert restored.filler_word_status == "ok"
    assert restored.filler_word_transcript_source == "job.transcript_data"
    assert restored.filler_word_detection_result == {"status": "ok", "occurrence_count": 3}
    assert len(restored.filler_word_occurrences) == 3
    assert restored.filler_word_occurrence_count == 3
    assert restored.filler_word_remove_candidate_count == 3
    assert restored.filler_word_counts_by_type == {"hesitation": 2, "repeated_word": 1}
    assert restored.filler_word_counts_by_language == {"de": 2, "en": 1}
    assert restored.filler_word_total_duration_seconds == pytest.approx(1.4)
    assert restored.filler_word_transcript_word_count == 12
    assert restored.filler_word_rate == pytest.approx(0.25)
    assert restored.filler_word_recommendation == "use_filler_word_analysis"


# ---------------------------------------------------------------------------
# 2. Old jobs without filler word fields do not crash
# ---------------------------------------------------------------------------

def test_job_from_dict_without_filler_word_fields_uses_defaults():
    minimal = {
        "job_id": "test-old-job",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "short",
        "target_platforms": [],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
    }
    job = Job.from_dict(minimal)
    assert job.filler_word_report == {}
    assert job.filler_word_status is None
    assert job.filler_word_transcript_source is None
    assert job.filler_word_detection_result == {}
    assert job.filler_word_occurrences == []
    assert job.filler_word_occurrence_count == 0
    assert job.filler_word_remove_candidate_count == 0
    assert job.filler_word_counts_by_type == {}
    assert job.filler_word_counts_by_language == {}
    assert job.filler_word_total_duration_seconds == pytest.approx(0.0)
    assert job.filler_word_transcript_word_count == 0
    assert job.filler_word_rate == pytest.approx(0.0)
    assert job.filler_word_recommendation is None


# ---------------------------------------------------------------------------
# 3. Pipeline source contains filler word events
# ---------------------------------------------------------------------------

def test_gaming_pipeline_contains_filler_word_events():
    src = _read_pipeline_source()
    for event in [
        "FILLER_WORD_DETECTION_STARTED",
        "FILLER_WORD_DETECTION_DONE",
        "FILLER_WORD_DETECTION_SKIPPED",
        "FILLER_WORD_DETECTION_FAILED",
    ]:
        assert event in src, f"Missing event in gaming_pipeline.py: {event}"


# ---------------------------------------------------------------------------
# 4. Pipeline imports run_filler_word_detection_for_job
# ---------------------------------------------------------------------------

def test_gaming_pipeline_uses_filler_word_runner_import():
    src = _read_pipeline_source()
    assert "from core.filler_word_runner import run_filler_word_detection_for_job" in src
    assert "run_filler_word_detection_for_job(" in src


# ---------------------------------------------------------------------------
# 5. Pipeline order contract
# ---------------------------------------------------------------------------

def test_filler_word_pipeline_order_contract():
    src = _read_pipeline_source()

    idx_energy_peak_started = src.index("ENERGY_PEAK_DETECTION_STARTED")
    idx_silence_detection_started = src.index("SILENCE_DETECTION_STARTED")
    idx_silence_classification_started = src.index("SILENCE_CLASSIFICATION_STARTED")
    idx_filler_started = src.index("FILLER_WORD_DETECTION_STARTED")
    idx_state_analyzing = src.index("STATE_ANALYZING")

    assert idx_silence_classification_started < idx_filler_started, \
        "SILENCE_CLASSIFICATION_STARTED must appear before FILLER_WORD_DETECTION_STARTED"

    assert idx_silence_detection_started < idx_filler_started, \
        "SILENCE_DETECTION_STARTED must appear before FILLER_WORD_DETECTION_STARTED"

    assert idx_energy_peak_started < idx_filler_started, \
        "ENERGY_PEAK_DETECTION_STARTED must appear before FILLER_WORD_DETECTION_STARTED"

    assert idx_filler_started < idx_state_analyzing, \
        "FILLER_WORD_DETECTION_STARTED must appear before STATE_ANALYZING"


# ---------------------------------------------------------------------------
# 6. Pipeline source sets the job fields
# ---------------------------------------------------------------------------

def test_filler_word_pipeline_sets_job_fields_in_source():
    src = _read_pipeline_source()
    for assignment in [
        "job.filler_word_report =",
        "job.filler_word_status =",
        "job.filler_word_occurrences =",
        "job.filler_word_occurrence_count =",
        "job.filler_word_rate =",
        "job.filler_word_recommendation =",
    ]:
        assert assignment in src, f"Missing assignment in gaming_pipeline.py: {assignment}"


# ---------------------------------------------------------------------------
# 7. Pipeline uses the runner, not the detector directly
# ---------------------------------------------------------------------------

def test_filler_word_pipeline_does_not_run_detector_directly():
    src = _read_pipeline_source()
    assert "run_filler_word_detection_for_job(" in src, \
        "gaming_pipeline.py must use run_filler_word_detection_for_job"
    assert "detect_filler_words(" not in src, \
        "gaming_pipeline.py must not call detect_filler_words directly — use the runner"
    assert "extract_word_items(" not in src, \
        "gaming_pipeline.py must not call extract_word_items directly — use the runner"


# ---------------------------------------------------------------------------
# 8. Pipeline-like filler word report sets expected job fields
# ---------------------------------------------------------------------------

def test_pipeline_like_filler_word_report_sets_expected_job_fields():
    job = _make_job()

    report = FillerWordRunReport(
        status="ok",
        transcript_source="job.transcript_data",
        detection_result={"status": "ok", "occurrence_count": 2},
        occurrences=[
            {"text": "ähm", "filler_type": "hesitation", "language": "de"},
            {"text": "um", "filler_type": "hesitation", "language": "en"},
        ],
        occurrence_count=2,
        remove_candidate_count=2,
        counts_by_filler_type={"hesitation": 2},
        counts_by_language={"de": 1, "en": 1},
        total_filler_duration_seconds=0.8,
        transcript_word_count=10,
        filler_rate=0.2,
        recommendation="use_filler_word_analysis",
    )

    # Replicate what pipeline does
    job.filler_word_report = report.to_dict()
    job.filler_word_status = report.status
    job.filler_word_transcript_source = report.transcript_source
    job.filler_word_detection_result = dict(report.detection_result or {})
    job.filler_word_occurrences = list(report.occurrences or [])
    job.filler_word_occurrence_count = int(report.occurrence_count or 0)
    job.filler_word_remove_candidate_count = int(report.remove_candidate_count or 0)
    job.filler_word_counts_by_type = dict(report.counts_by_filler_type or {})
    job.filler_word_counts_by_language = dict(report.counts_by_language or {})
    job.filler_word_total_duration_seconds = float(report.total_filler_duration_seconds or 0.0)
    job.filler_word_transcript_word_count = int(report.transcript_word_count or 0)
    job.filler_word_rate = float(report.filler_rate or 0.0)
    job.filler_word_recommendation = report.recommendation

    assert job.filler_word_status == "ok"
    assert job.filler_word_transcript_source == "job.transcript_data"
    assert job.filler_word_occurrence_count == 2
    assert job.filler_word_remove_candidate_count == 2
    assert job.filler_word_counts_by_type == {"hesitation": 2}
    assert job.filler_word_counts_by_language == {"de": 1, "en": 1}
    assert job.filler_word_total_duration_seconds == pytest.approx(0.8)
    assert job.filler_word_transcript_word_count == 10
    assert job.filler_word_rate == pytest.approx(0.2)
    assert job.filler_word_recommendation == "use_filler_word_analysis"

    # Roundtrip persists
    restored = Job.from_dict(job.to_dict())
    assert restored.filler_word_status == "ok"
    assert restored.filler_word_occurrence_count == 2
    assert restored.filler_word_counts_by_type == {"hesitation": 2}
    assert restored.filler_word_recommendation == "use_filler_word_analysis"


# ---------------------------------------------------------------------------
# 9. BOM and trailing newline hygiene
# ---------------------------------------------------------------------------

def test_pipeline_integration_files_have_no_bom_and_end_with_newline():
    files = [
        _JOB_MODEL_PATH,
        _PIPELINE_PATH,
        _TEST_PATH,
    ]
    for path in files:
        with open(path, "rb") as f:
            raw = f.read()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {path}"
        assert raw.endswith(b"\n"), f"Missing trailing newline in {path}"
