from __future__ import annotations

import os

import pytest

from models.job import Job
from models.energy_peak_run import EnergyPeakRunReport
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
_TEST_PATH = os.path.join(_THIS_DIR, "test_energy_peak_pipeline_integration_smoke.py")


def _make_job(**kwargs) -> Job:
    defaults = dict(
        job_id="test-energy-peak-pipeline-001",
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
# 1. Job roundtrip preserves energy peak fields
# ---------------------------------------------------------------------------

def test_job_roundtrip_preserves_energy_peak_fields():
    job = _make_job(
        energy_peak_report={"status": "ok"},
        energy_peak_status="ok",
        energy_peak_timeline_source="provided_energy_timeline",
        energy_peak_detection_result={"status": "ok", "peak_count": 3},
        energy_peaks=[
            {"peak_type": "combined", "energy_score": 0.95, "peak_score": 0.85},
            {"peak_type": "high_energy", "energy_score": 0.9, "peak_score": 0.75},
        ],
        energy_peak_count=2,
        energy_high_energy_peak_count=2,
        energy_local_max_peak_count=1,
        energy_rise_peak_count=0,
        energy_threshold_peak_count=2,
        energy_peak_threshold=0.85,
        energy_rise_threshold=0.25,
        energy_min_peak_distance_seconds=0.4,
        energy_max_peak_score=0.85,
        energy_avg_peak_score=0.8,
        energy_top_peak={"peak_type": "combined", "peak_score": 0.85},
        energy_peak_recommendation="use_energy_peaks",
    )

    d = job.to_dict()
    restored = Job.from_dict(d)

    assert restored.energy_peak_report == {"status": "ok"}
    assert restored.energy_peak_status == "ok"
    assert restored.energy_peak_timeline_source == "provided_energy_timeline"
    assert restored.energy_peak_detection_result == {"status": "ok", "peak_count": 3}
    assert len(restored.energy_peaks) == 2
    assert restored.energy_peak_count == 2
    assert restored.energy_high_energy_peak_count == 2
    assert restored.energy_local_max_peak_count == 1
    assert restored.energy_rise_peak_count == 0
    assert restored.energy_threshold_peak_count == 2
    assert restored.energy_peak_threshold == pytest.approx(0.85)
    assert restored.energy_rise_threshold == pytest.approx(0.25)
    assert restored.energy_min_peak_distance_seconds == pytest.approx(0.4)
    assert restored.energy_max_peak_score == pytest.approx(0.85)
    assert restored.energy_avg_peak_score == pytest.approx(0.8)
    assert restored.energy_top_peak["peak_type"] == "combined"
    assert restored.energy_peak_recommendation == "use_energy_peaks"


# ---------------------------------------------------------------------------
# 2. Old jobs without energy peak fields do not crash
# ---------------------------------------------------------------------------

def test_job_from_dict_without_energy_peak_fields_uses_defaults():
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
    assert job.energy_peak_report == {}
    assert job.energy_peak_status is None
    assert job.energy_peak_timeline_source is None
    assert job.energy_peak_detection_result == {}
    assert job.energy_peaks == []
    assert job.energy_peak_count == 0
    assert job.energy_high_energy_peak_count == 0
    assert job.energy_local_max_peak_count == 0
    assert job.energy_rise_peak_count == 0
    assert job.energy_threshold_peak_count == 0
    assert job.energy_peak_threshold == pytest.approx(0.85)
    assert job.energy_rise_threshold == pytest.approx(0.25)
    assert job.energy_min_peak_distance_seconds == pytest.approx(0.4)
    assert job.energy_max_peak_score == pytest.approx(0.0)
    assert job.energy_avg_peak_score == pytest.approx(0.0)
    assert job.energy_top_peak == {}
    assert job.energy_peak_recommendation is None


# ---------------------------------------------------------------------------
# 3. Pipeline source contains energy peak events
# ---------------------------------------------------------------------------

def test_gaming_pipeline_contains_energy_peak_events():
    src = _read_pipeline_source()
    for event in [
        "ENERGY_PEAK_DETECTION_STARTED",
        "ENERGY_PEAK_DETECTION_DONE",
        "ENERGY_PEAK_DETECTION_SKIPPED",
        "ENERGY_PEAK_DETECTION_FAILED",
    ]:
        assert event in src, f"Missing event in gaming_pipeline.py: {event}"


# ---------------------------------------------------------------------------
# 4. Pipeline imports run_energy_peak_detection_for_job
# ---------------------------------------------------------------------------

def test_gaming_pipeline_uses_energy_peak_runner_import():
    src = _read_pipeline_source()
    assert "from core.energy_peak_runner import run_energy_peak_detection_for_job" in src
    assert "run_energy_peak_detection_for_job(" in src


# ---------------------------------------------------------------------------
# 5. Pipeline order contract
# ---------------------------------------------------------------------------

def test_energy_peak_pipeline_order_contract():
    src = _read_pipeline_source()

    idx_rms_started = src.index("RMS_ENERGY_STARTED")
    idx_energy_peak_started = src.index("ENERGY_PEAK_DETECTION_STARTED")
    idx_silence_detection_started = src.index("SILENCE_DETECTION_STARTED")
    idx_silence_classification_started = src.index("SILENCE_CLASSIFICATION_STARTED")
    idx_state_analyzing = src.index("STATE_ANALYZING")

    # RMS_ENERGY_STARTED < ENERGY_PEAK_DETECTION_STARTED
    assert idx_rms_started < idx_energy_peak_started, \
        "RMS_ENERGY_STARTED must appear before ENERGY_PEAK_DETECTION_STARTED"

    # RMS_ENERGY_CONTEXT_ADAPTED or RMS_ENERGY_CONTEXT_SKIPPED < ENERGY_PEAK_DETECTION_STARTED
    idx_context_adapted = src.find("RMS_ENERGY_CONTEXT_ADAPTED")
    idx_context_skipped = src.find("RMS_ENERGY_CONTEXT_SKIPPED")
    idx_context_event = min(
        x for x in [idx_context_adapted, idx_context_skipped] if x >= 0
    )
    assert idx_context_event < idx_energy_peak_started, \
        "RMS context event must appear before ENERGY_PEAK_DETECTION_STARTED"

    # ENERGY_PEAK_DETECTION_STARTED < SILENCE_DETECTION_STARTED
    assert idx_energy_peak_started < idx_silence_detection_started, \
        "ENERGY_PEAK_DETECTION_STARTED must appear before SILENCE_DETECTION_STARTED"

    # ENERGY_PEAK_DETECTION_STARTED < SILENCE_CLASSIFICATION_STARTED
    assert idx_energy_peak_started < idx_silence_classification_started, \
        "ENERGY_PEAK_DETECTION_STARTED must appear before SILENCE_CLASSIFICATION_STARTED"

    # ENERGY_PEAK_DETECTION_STARTED < STATE_ANALYZING
    assert idx_energy_peak_started < idx_state_analyzing, \
        "ENERGY_PEAK_DETECTION_STARTED must appear before STATE_ANALYZING"


# ---------------------------------------------------------------------------
# 6. Pipeline source sets the job fields
# ---------------------------------------------------------------------------

def test_energy_peak_pipeline_sets_job_fields_in_source():
    src = _read_pipeline_source()
    for assignment in [
        "job.energy_peak_report =",
        "job.energy_peak_status =",
        "job.energy_peaks =",
        "job.energy_peak_count =",
        "job.energy_top_peak =",
    ]:
        assert assignment in src, f"Missing assignment in gaming_pipeline.py: {assignment}"


# ---------------------------------------------------------------------------
# 7. Pipeline does not directly call detect_energy_peaks
# ---------------------------------------------------------------------------

def test_energy_peak_pipeline_does_not_directly_detect_from_rms():
    src = _read_pipeline_source()
    assert "run_energy_peak_detection_for_job(" in src, \
        "gaming_pipeline.py must use run_energy_peak_detection_for_job"
    assert "detect_energy_peaks(" not in src, \
        "gaming_pipeline.py must not call detect_energy_peaks directly — use the runner"


# ---------------------------------------------------------------------------
# 8. BOM and trailing newline hygiene
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


# ---------------------------------------------------------------------------
# 9. Pipeline-like energy peak report sets expected job fields
# ---------------------------------------------------------------------------

def test_pipeline_like_energy_peak_report_sets_expected_job_fields():
    job = _make_job()

    report = EnergyPeakRunReport(
        status="ok",
        energy_timeline_source="provided_energy_timeline",
        peaks=[
            {"peak_type": "combined", "energy_score": 0.95, "peak_score": 0.9},
        ],
        peak_count=1,
        high_energy_peak_count=1,
        local_max_peak_count=1,
        rise_peak_count=0,
        threshold_peak_count=1,
        peak_threshold=0.85,
        rise_threshold=0.25,
        min_peak_distance_seconds=0.4,
        max_peak_score=0.9,
        avg_peak_score=0.9,
        top_peak={"peak_type": "combined", "energy_score": 0.95, "peak_score": 0.9},
        recommendation="use_energy_peaks",
        peak_detection_result={"status": "ok", "peak_count": 1},
    )

    # Replicate what pipeline does
    job.energy_peak_report = report.to_dict()
    job.energy_peak_status = report.status
    job.energy_peak_timeline_source = report.energy_timeline_source
    job.energy_peak_detection_result = dict(report.peak_detection_result or {})
    job.energy_peaks = list(report.peaks or [])
    job.energy_peak_count = int(report.peak_count or 0)
    job.energy_high_energy_peak_count = int(report.high_energy_peak_count or 0)
    job.energy_local_max_peak_count = int(report.local_max_peak_count or 0)
    job.energy_rise_peak_count = int(report.rise_peak_count or 0)
    job.energy_threshold_peak_count = int(report.threshold_peak_count or 0)
    job.energy_peak_threshold = float(report.peak_threshold or 0.85)
    job.energy_rise_threshold = float(report.rise_threshold or 0.25)
    job.energy_min_peak_distance_seconds = float(report.min_peak_distance_seconds or 0.4)
    job.energy_max_peak_score = float(report.max_peak_score or 0.0)
    job.energy_avg_peak_score = float(report.avg_peak_score or 0.0)
    job.energy_top_peak = dict(report.top_peak or {})
    job.energy_peak_recommendation = report.recommendation

    assert job.energy_peak_status == "ok"
    assert job.energy_peak_timeline_source == "provided_energy_timeline"
    assert job.energy_peak_count == 1
    assert job.energy_high_energy_peak_count == 1
    assert job.energy_max_peak_score == pytest.approx(0.9)
    assert job.energy_top_peak["peak_type"] == "combined"
    assert job.energy_peak_recommendation == "use_energy_peaks"

    # Roundtrip persists
    restored = Job.from_dict(job.to_dict())
    assert restored.energy_peak_status == "ok"
    assert restored.energy_peak_count == 1
    assert restored.energy_top_peak["peak_type"] == "combined"
