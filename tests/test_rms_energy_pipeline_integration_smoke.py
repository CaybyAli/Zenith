from __future__ import annotations

import os

import pytest

from models.job import Job
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


def _make_job(**kwargs) -> Job:
    defaults = dict(
        job_id="test-rms-pipeline-001",
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


def _read_job_source() -> str:
    with open(_JOB_MODEL_PATH, encoding="utf-8") as f:
        return f.read()


# ── 1. Job roundtrip preserves all RMS energy fields ─────────────────────────

def test_job_roundtrip_preserves_rms_energy_fields():
    job = _make_job(
        rms_energy_status="ok",
        rms_energy_selected_path="/tmp/analysis.wav",
        rms_energy_selected_type="analysis_audio",
        rms_energy_timeline_status="ok",
        rms_energy_point_count=42,
        rms_energy_duration_seconds=10.5,
        rms_energy_sample_rate=44100,
        rms_energy_channels=1,
        rms_energy_frame_ms=10.0,
        rms_energy_hop_ms=5.0,
        rms_energy_min_rms=0.01,
        rms_energy_max_rms=0.9,
        rms_energy_avg_rms=0.4,
        rms_energy_min_normalized_energy=0.05,
        rms_energy_max_normalized_energy=0.95,
        rms_energy_avg_normalized_energy=0.5,
        rms_energy_report={"status": "ok"},
        rms_energy_source_selection={"status": "ok"},
        rms_energy_timeline_result={"status": "ok", "points": []},
        rms_energy_context_status="ok",
        rms_energy_context_point_count=10,
        rms_energy_context_peak_count=3,
        rms_energy_context_silent_count=1,
        rms_energy_context_adapter={"status": "ok"},
        rms_energy_context_timeline=[{"time_seconds": 0.5, "energy_score": 0.7}],
    )

    d = job.to_dict()
    restored = Job.from_dict(d)

    assert restored.rms_energy_status == "ok"
    assert restored.rms_energy_selected_path == "/tmp/analysis.wav"
    assert restored.rms_energy_selected_type == "analysis_audio"
    assert restored.rms_energy_timeline_status == "ok"
    assert restored.rms_energy_point_count == 42
    assert restored.rms_energy_duration_seconds == pytest.approx(10.5)
    assert restored.rms_energy_sample_rate == 44100
    assert restored.rms_energy_channels == 1
    assert restored.rms_energy_frame_ms == pytest.approx(10.0)
    assert restored.rms_energy_hop_ms == pytest.approx(5.0)
    assert restored.rms_energy_min_rms == pytest.approx(0.01)
    assert restored.rms_energy_max_rms == pytest.approx(0.9)
    assert restored.rms_energy_avg_rms == pytest.approx(0.4)
    assert restored.rms_energy_min_normalized_energy == pytest.approx(0.05)
    assert restored.rms_energy_max_normalized_energy == pytest.approx(0.95)
    assert restored.rms_energy_avg_normalized_energy == pytest.approx(0.5)
    assert restored.rms_energy_report == {"status": "ok"}
    assert restored.rms_energy_source_selection == {"status": "ok"}
    assert "status" in restored.rms_energy_timeline_result
    assert restored.rms_energy_context_status == "ok"
    assert restored.rms_energy_context_point_count == 10
    assert restored.rms_energy_context_peak_count == 3
    assert restored.rms_energy_context_silent_count == 1
    assert restored.rms_energy_context_adapter == {"status": "ok"}
    assert len(restored.rms_energy_context_timeline) == 1


# ── 2. Existing jobs without RMS fields do not crash ─────────────────────────

def test_job_from_dict_without_rms_fields_uses_defaults():
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
    assert job.rms_energy_status is None
    assert job.rms_energy_point_count == 0
    assert job.rms_energy_report == {}
    assert job.rms_energy_context_timeline == []
    assert job.rms_energy_context_status is None


# ── 3. Pipeline source contains all required RMS event types ─────────────────

def test_gaming_pipeline_contains_rms_energy_events():
    src = _read_pipeline_source()
    for event in [
        "RMS_ENERGY_STARTED",
        "RMS_ENERGY_SOURCE_SELECTED",
        "RMS_ENERGY_DONE",
        "RMS_ENERGY_BLOCKED",
        "RMS_ENERGY_SKIPPED",
        "RMS_ENERGY_FAILED",
        "RMS_ENERGY_CONTEXT_ADAPTED",
        "RMS_ENERGY_CONTEXT_SKIPPED",
    ]:
        assert event in src, f"Missing event in gaming_pipeline.py: {event}"


# ── 4. Pipeline imports run_rms_energy_for_job ────────────────────────────────

def test_gaming_pipeline_uses_rms_energy_runner_import():
    src = _read_pipeline_source()
    assert "from core.rms_energy_runner import run_rms_energy_for_job" in src
    assert "run_rms_energy_for_job(" in src


# ── 5. Pipeline imports adapt_rms_energy_run_report_to_context ────────────────

def test_gaming_pipeline_uses_context_adapter_import():
    src = _read_pipeline_source()
    assert "from core.rms_energy_context_adapter import adapt_rms_energy_run_report_to_context" in src
    assert "adapt_rms_energy_run_report_to_context(" in src


# ── 6. RMS pipeline order contract ───────────────────────────────────────────

def test_rms_pipeline_order_contract():
    src = _read_pipeline_source()

    idx_preprocessing_ready = src.index("PREPROCESSING_READY")
    idx_rms_started = src.index("RMS_ENERGY_STARTED")
    idx_silence_detection_started = src.index("SILENCE_DETECTION_STARTED")
    idx_silence_classification_started = src.index("SILENCE_CLASSIFICATION_STARTED")

    # PREPROCESSING_READY < RMS_ENERGY_STARTED
    assert idx_preprocessing_ready < idx_rms_started, \
        "PREPROCESSING_READY must appear before RMS_ENERGY_STARTED"

    # RMS_ENERGY_STARTED < SILENCE_DETECTION_STARTED
    assert idx_rms_started < idx_silence_detection_started, \
        "RMS_ENERGY_STARTED must appear before SILENCE_DETECTION_STARTED"

    # RMS_ENERGY_STARTED < SILENCE_CLASSIFICATION_STARTED
    assert idx_rms_started < idx_silence_classification_started, \
        "RMS_ENERGY_STARTED must appear before SILENCE_CLASSIFICATION_STARTED"

    # RMS_ENERGY_CONTEXT_ADAPTED or RMS_ENERGY_CONTEXT_SKIPPED < SILENCE_CLASSIFICATION_STARTED
    idx_context_adapted = src.find("RMS_ENERGY_CONTEXT_ADAPTED")
    idx_context_skipped = src.find("RMS_ENERGY_CONTEXT_SKIPPED")
    idx_context_event = min(
        x for x in [idx_context_adapted, idx_context_skipped] if x >= 0
    )
    assert idx_context_event < idx_silence_classification_started, \
        "RMS_ENERGY_CONTEXT_ADAPTED/SKIPPED must appear before SILENCE_CLASSIFICATION_STARTED"


# ── 7. Pipeline does not directly call analyze_wav_rms_energy ─────────────────

def test_rms_pipeline_does_not_directly_analyze_mp4():
    src = _read_pipeline_source()
    assert "analyze_wav_rms_energy" not in src, \
        "gaming_pipeline.py must not call analyze_wav_rms_energy directly — use run_rms_energy_for_job"
    assert "run_rms_energy_for_job(" in src, \
        "gaming_pipeline.py must use run_rms_energy_for_job"


# ── 8. Silence classifier receives RMS energy timeline hook ───────────────────

def test_silence_classifier_receives_rms_energy_timeline_hook():
    src = _read_pipeline_source()
    assert "rms_energy_context_timeline" in src, \
        "gaming_pipeline.py must reference rms_energy_context_timeline"
    assert "run_silence_classifier_for_job(" in src
    # The energy_timeline kwarg must appear near the classifier call
    classifier_call_idx = src.index("run_silence_classifier_for_job(")
    snippet = src[classifier_call_idx:classifier_call_idx + 400]
    assert "energy_timeline" in snippet, \
        "run_silence_classifier_for_job must be called with energy_timeline="


# ── 9. BOM and newline hygiene ────────────────────────────────────────────────

def test_pipeline_integration_files_have_no_bom_and_end_with_newline():
    files = [
        _JOB_MODEL_PATH,
        _PIPELINE_PATH,
        os.path.join(_THIS_DIR, "test_rms_energy_pipeline_integration_smoke.py"),
    ]
    for path in files:
        with open(path, "rb") as f:
            raw = f.read()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {path}"
        assert raw.endswith(b"\n"), f"Missing trailing newline in {path}"
