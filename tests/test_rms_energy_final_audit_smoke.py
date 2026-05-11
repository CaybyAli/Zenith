from __future__ import annotations

import inspect
import math
import os
import struct
import wave
from dataclasses import dataclass
from typing import Any

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


def _make_job(**kwargs) -> Job:
    defaults = dict(
        job_id="audit-test-001",
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


# ---------------------------------------------------------------------------
# Test 1 — Model roundtrip
# ---------------------------------------------------------------------------

def test_2b08_models_roundtrip():
    from models.rms_energy import RmsEnergyPoint, RmsEnergyTimelineResult
    from models.rms_energy_audio_source import RmsEnergyAudioSourceSelection
    from models.rms_energy_run import RmsEnergyRunReport
    from models.rms_energy_context_adapter import RmsEnergyContextAdapterResult

    # RmsEnergyPoint
    pt = RmsEnergyPoint(
        start_seconds=0.0, end_seconds=0.01, center_seconds=0.005,
        rms=0.5, normalized_energy=0.7, dbfs=-6.0, sample_count=160, is_silent=False,
    )
    pt2 = RmsEnergyPoint.from_dict(pt.to_dict())
    assert pt2.rms == pt.rms
    assert pt2.normalized_energy == pt.normalized_energy
    assert pt2.dbfs == pt.dbfs
    assert pt2.sample_count == pt.sample_count
    assert pt2.is_silent is False

    # RmsEnergyTimelineResult
    tr = RmsEnergyTimelineResult(
        status="ok", source_path="/tmp/a.wav", sample_rate=16000, channels=1,
        duration_seconds=1.0, frame_ms=10.0, hop_ms=5.0,
        points=[pt], point_count=1,
        min_rms=0.5, max_rms=0.5, avg_rms=0.5,
        min_normalized_energy=0.7, max_normalized_energy=0.7, avg_normalized_energy=0.7,
    )
    tr2 = RmsEnergyTimelineResult.from_dict(tr.to_dict())
    assert tr2.status == "ok"
    assert tr2.sample_rate == 16000
    assert tr2.point_count == 1
    assert len(tr2.points) == 1
    assert tr2.points[0].rms == 0.5

    # RmsEnergyAudioSourceSelection
    sel = RmsEnergyAudioSourceSelection(
        status="selected", selected_path="/tmp/a.wav", selected_type="analysis_audio",
        exists=True, is_wav=True, requires_extraction=False, recommendation="analyze_wav",
    )
    sel2 = RmsEnergyAudioSourceSelection.from_dict(sel.to_dict())
    assert sel2.status == "selected"
    assert sel2.selected_path == "/tmp/a.wav"
    assert sel2.is_wav is True
    assert sel2.exists is True

    # RmsEnergyRunReport
    rr = RmsEnergyRunReport(
        status="ok", selected_path="/tmp/a.wav", selected_type="analysis_audio",
        timeline_status="ok", point_count=10, duration_seconds=0.5,
        sample_rate=16000, channels=1, frame_ms=10.0, hop_ms=5.0,
        min_rms=0.1, max_rms=0.9, avg_rms=0.5,
        min_normalized_energy=0.0, max_normalized_energy=1.0, avg_normalized_energy=0.5,
    )
    rr2 = RmsEnergyRunReport.from_dict(rr.to_dict())
    assert rr2.status == "ok"
    assert rr2.sample_rate == 16000
    assert rr2.point_count == 10
    assert rr2.timeline_status == "ok"

    # RmsEnergyContextAdapterResult
    ca = RmsEnergyContextAdapterResult(
        status="ok", point_count=3, peak_count=1, silent_count=0,
        peak_threshold=0.85,
        energy_timeline=[{"time_seconds": 0.5, "energy_score": 0.9, "is_peak": True}],
    )
    ca2 = RmsEnergyContextAdapterResult.from_dict(ca.to_dict())
    assert ca2.status == "ok"
    assert ca2.point_count == 3
    assert ca2.peak_count == 1
    assert len(ca2.energy_timeline) == 1


# ---------------------------------------------------------------------------
# Test 2 — RMS Analyzer core math contract
# ---------------------------------------------------------------------------

def test_2b08_rms_analyzer_core_math_contract():
    from core.rms_energy_analyzer import calculate_rms, normalize_values, dbfs_from_rms

    rms_val = calculate_rms([1.0, -1.0, 1.0, -1.0])
    assert abs(rms_val - 1.0) < 1e-9

    assert calculate_rms([0.0, 0.0]) == 0.0
    assert calculate_rms([]) == 0.0

    normed = normalize_values([0.0, 0.5, 1.0])
    assert normed == [0.0, 0.5, 1.0]

    assert normed == pytest.approx([0.0, 0.5, 1.0])

    assert dbfs_from_rms(1.0) == pytest.approx(0.0, abs=1e-9)
    assert dbfs_from_rms(0.5) == pytest.approx(-6.0206, abs=0.01)
    assert dbfs_from_rms(0.0) is None
    assert dbfs_from_rms(-1.0) is None


# ---------------------------------------------------------------------------
# Test 3 — Timeline and WAV contract
# ---------------------------------------------------------------------------

def _write_wav_to_path(path: str, sample_rate: int = 16000, duration_s: float = 0.2) -> None:
    n_frames = int(sample_rate * duration_s)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        data = struct.pack(f"<{n_frames}h", *[int(3000 * math.sin(2 * math.pi * 440 * i / sample_rate)) for i in range(n_frames)])
        wf.writeframes(data)


def test_2b08_timeline_and_wav_contract(tmp_path):
    from core.rms_energy_analyzer import (
        analyze_wav_rms_energy,
        build_rms_energy_timeline_from_samples,
    )

    wav_path = str(tmp_path / "test.wav")
    _write_wav_to_path(wav_path, sample_rate=16000, duration_s=0.2)

    result = analyze_wav_rms_energy(wav_path)
    assert result.status == "ok"
    assert result.point_count > 0
    assert result.sample_rate == 16000
    assert result.channels == 1

    # build_rms_energy_timeline_from_samples with normal samples
    samples = [math.sin(2 * math.pi * 440 * i / 16000) for i in range(1600)]
    tl = build_rms_energy_timeline_from_samples(samples=samples, sample_rate=16000)
    assert tl.status == "ok"
    assert len(tl.points) > 0

    # short samples do not crash
    short_tl = build_rms_energy_timeline_from_samples(samples=[0.1], sample_rate=16000)
    assert short_tl.status in ("ok", "completed_with_warnings")

    # empty samples are safe
    empty_tl = build_rms_energy_timeline_from_samples(samples=[], sample_rate=16000)
    assert empty_tl.status in ("ok", "completed_with_warnings")

    # invalid sample_rate fails safely
    bad_tl = build_rms_energy_timeline_from_samples(samples=[0.1, 0.2], sample_rate=-1)
    assert bad_tl.status == "failed"
    assert any("invalid_sample_rate" in e for e in bad_tl.errors)

    # missing WAV fails safely
    missing = analyze_wav_rms_energy(str(tmp_path / "nonexistent.wav"))
    assert missing.status == "failed"


# ---------------------------------------------------------------------------
# Test 4 — Source selector contract
# ---------------------------------------------------------------------------

def test_2b08_source_selector_contract(tmp_path):
    from core.rms_energy_audio_source_selector import select_rms_energy_audio_source

    # analysis_audio WAV is preferred when it exists
    wav = tmp_path / "analysis.wav"
    _write_wav_to_path(str(wav))
    sel = select_rms_energy_audio_source(
        preprocessing_manifest={"analysis_audio_path": str(wav)},
        require_existing_file=True,
    )
    assert sel.status == "selected"
    assert sel.selected_type == "analysis_audio"

    # speech_audio fallback when analysis_audio is missing
    speech_wav = tmp_path / "speech.wav"
    _write_wav_to_path(str(speech_wav))
    sel2 = select_rms_energy_audio_source(
        preprocessing_manifest={
            "analysis_audio_path": str(tmp_path / "missing.wav"),
            "speech_audio_path": str(speech_wav),
        },
        require_existing_file=True,
    )
    assert sel2.status == "selected"
    assert sel2.selected_type == "speech_audio"

    # music_reference_audio is selected_fallback with warning
    music_wav = tmp_path / "music.wav"
    _write_wav_to_path(str(music_wav))
    sel3 = select_rms_energy_audio_source(
        preprocessing_manifest={"music_reference_audio_path": str(music_wav)},
        require_existing_file=True,
    )
    assert sel3.status == "selected_fallback"
    assert sel3.selected_type == "music_reference_audio"
    assert any("music_reference_audio" in w for w in sel3.warnings)

    # planned analysis_audio path that doesn't exist → missing_preprocessed_audio
    sel4 = select_rms_energy_audio_source(
        preprocessing_manifest={"analysis_audio_path": str(tmp_path / "not_yet.wav")},
        require_existing_file=True,
    )
    assert sel4.status == "missing_preprocessed_audio"
    assert sel4.selected_type in ("planned_analysis_audio", "planned_speech_audio")

    # original WAV fallback works
    orig_wav = tmp_path / "original.wav"
    _write_wav_to_path(str(orig_wav))
    sel5 = select_rms_energy_audio_source(
        preprocessing_manifest=None,
        fallback_source_path=str(orig_wav),
        require_existing_file=True,
        allow_original_wav_fallback=True,
    )
    assert sel5.status == "selected_fallback"
    assert sel5.selected_type == "original_wav"

    # original MP4 is NOT selected and requires extraction
    sel6 = select_rms_energy_audio_source(
        preprocessing_manifest=None,
        fallback_source_path=str(tmp_path / "video.mp4"),
        require_existing_file=False,
        allow_original_wav_fallback=True,
    )
    assert sel6.status == "unsupported_original_source"
    assert sel6.recommendation == "extract_audio_first"

    # audio_extraction_plan targets are read
    plan_path = str(tmp_path / "planned_analysis.wav")
    sel7 = select_rms_energy_audio_source(
        preprocessing_manifest={
            "audio_extraction_plan": {
                "targets": [
                    {"target_type": "analysis_audio", "output_path": plan_path},
                ]
            }
        },
        require_existing_file=True,
    )
    assert sel7.status == "missing_preprocessed_audio"
    assert sel7.selected_path == plan_path


# ---------------------------------------------------------------------------
# Test 5 — Runner contract
# ---------------------------------------------------------------------------

def test_2b08_runner_contract(tmp_path):
    from core.rms_energy_runner import build_rms_energy_run_report, run_rms_energy_for_job

    # analysis.wav present → status ok
    wav = tmp_path / "analysis.wav"
    _write_wav_to_path(str(wav), duration_s=0.2)
    report = build_rms_energy_run_report(
        preprocessing_manifest={"analysis_audio_path": str(wav)},
        require_existing_file=True,
    )
    assert report.status == "ok"
    assert report.point_count > 0

    # missing analysis.wav → blocked_missing_preprocessed_audio
    report2 = build_rms_energy_run_report(
        preprocessing_manifest={"analysis_audio_path": str(tmp_path / "missing.wav")},
        require_existing_file=True,
    )
    assert report2.status == "blocked_missing_preprocessed_audio"

    # original MP4 → skipped_unsupported_source or recommendation extract_audio_first
    report3 = build_rms_energy_run_report(
        preprocessing_manifest=None,
        fallback_source_path=str(tmp_path / "video.mp4"),
        require_existing_file=False,
        allow_original_wav_fallback=True,
    )
    assert report3.status == "skipped_unsupported_source" or report3.recommendation == "extract_audio_first"

    # bad wav → failed
    bad_wav = tmp_path / "bad.wav"
    bad_wav.write_bytes(b"not a wav file at all")
    report4 = build_rms_energy_run_report(
        preprocessing_manifest={"analysis_audio_path": str(bad_wav)},
        require_existing_file=True,
    )
    assert report4.status == "failed"
    assert any("wav_read_failed" in e for e in report4.errors)

    # run_rms_energy_for_job reads preprocessing_manifest from job
    @dataclass
    class FakeJob:
        preprocessing_manifest: dict[str, Any]
        raw_video_path: str | None = None

    good_job = FakeJob(preprocessing_manifest={"analysis_audio_path": str(wav)})
    report5 = run_rms_energy_for_job(good_job)
    assert report5.status == "ok"

    # empty job does not crash
    @dataclass
    class EmptyJob:
        pass

    report6 = run_rms_energy_for_job(EmptyJob())
    assert report6.status in ("failed", "blocked_missing_preprocessed_audio", "skipped_unsupported_source", "unavailable")


# ---------------------------------------------------------------------------
# Test 6 — Context adapter contract
# ---------------------------------------------------------------------------

def test_2b08_context_adapter_contract():
    from models.rms_energy import RmsEnergyPoint, RmsEnergyTimelineResult
    from core.rms_energy_context_adapter import (
        adapt_rms_energy_timeline_to_context,
        adapt_rms_energy_run_report_to_context,
    )

    pt = RmsEnergyPoint(
        start_seconds=0.0, end_seconds=0.01, center_seconds=0.005,
        rms=0.8, normalized_energy=0.9, is_silent=False,
    )
    tl = RmsEnergyTimelineResult(
        status="ok", sample_rate=16000, channels=1, duration_seconds=0.01,
        points=[pt], point_count=1,
        min_normalized_energy=0.9, max_normalized_energy=0.9, avg_normalized_energy=0.9,
    )

    # RmsEnergyTimelineResult → energy_timeline
    ctx = adapt_rms_energy_timeline_to_context(tl, peak_threshold=0.85)
    assert ctx.status == "ok"
    assert len(ctx.energy_timeline) == 1

    item = ctx.energy_timeline[0]
    # normalized_energy becomes energy_score
    assert item["energy_score"] == pt.normalized_energy
    # center_seconds becomes time_seconds
    assert item["time_seconds"] == pt.center_seconds
    # peak_threshold marks peak
    assert item["is_peak"] is True  # 0.9 >= 0.85

    # silent filtering works
    silent_pt = RmsEnergyPoint(
        start_seconds=0.1, end_seconds=0.11, center_seconds=0.105,
        rms=0.0001, normalized_energy=0.0, is_silent=True,
    )
    tl2 = RmsEnergyTimelineResult(
        status="ok", sample_rate=16000, channels=1, duration_seconds=0.2,
        points=[pt, silent_pt], point_count=2,
    )
    ctx2 = adapt_rms_energy_timeline_to_context(tl2, include_silent_points=False)
    assert all(not item["is_silent"] for item in ctx2.energy_timeline)

    # RunReport → Context works
    from core.rms_energy_runner import build_rms_energy_run_report
    import tempfile, struct, math, wave as _wave

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        tmp_path = f.name
    try:
        _write_wav_to_path_local(tmp_path)
        rr = build_rms_energy_run_report(
            preprocessing_manifest={"analysis_audio_path": tmp_path},
            require_existing_file=True,
        )
        ctx3 = adapt_rms_energy_run_report_to_context(rr)
        assert ctx3.status in ("ok", "completed_with_warnings", "failed")
    finally:
        os.unlink(tmp_path)

    # missing timeline fails safely
    bad_rr = {"status": "ok", "energy_timeline_result": None, "point_count": 0}
    ctx4 = adapt_rms_energy_run_report_to_context(bad_rr)
    assert ctx4.status == "failed"
    assert any("missing_energy_timeline_result" in e for e in ctx4.errors)


def _write_wav_to_path_local(path: str, sample_rate: int = 16000, duration_s: float = 0.1) -> None:
    n_frames = int(sample_rate * duration_s)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        data = struct.pack(f"<{n_frames}h", *[int(3000 * math.sin(2 * math.pi * 440 * i / sample_rate)) for i in range(n_frames)])
        wf.writeframes(data)


# ---------------------------------------------------------------------------
# Test 7 — Integrated flow: RMS → Silence Classifier
# ---------------------------------------------------------------------------

def test_2b08_integrated_flow_rms_to_silence_classifier():
    from models.rms_energy import RmsEnergyPoint, RmsEnergyTimelineResult
    from core.rms_energy_context_adapter import adapt_rms_energy_timeline_to_context
    from core.silence_context_builder import build_silence_segment_context
    from core.adaptive_silence_classifier import classify_silence_segment

    # Build RMS point just before the silence segment (center at 9.5s)
    pt = RmsEnergyPoint(
        start_seconds=9.4, end_seconds=9.6, center_seconds=9.5,
        rms=0.8, normalized_energy=0.9, is_silent=False,
    )
    tl = RmsEnergyTimelineResult(
        status="ok", sample_rate=16000, channels=1, duration_seconds=12.0,
        points=[pt], point_count=1,
        min_normalized_energy=0.9, max_normalized_energy=0.9, avg_normalized_energy=0.9,
    )

    adapter_result = adapt_rms_energy_timeline_to_context(tl, peak_threshold=0.85)
    energy_timeline = adapter_result.energy_timeline

    # Silence segment: 10.0 – 11.2 (duration 1.2s)
    @dataclass
    class Seg:
        start_seconds: float = 10.0
        end_seconds: float = 11.2
        duration_seconds: float = 1.2

    seg = Seg()
    silence_ctx = build_silence_segment_context(
        segment=seg,
        energy_timeline=energy_timeline,
    )

    assert silence_ctx.previous_energy_score == pytest.approx(0.9, abs=1e-6)
    assert silence_ctx.is_after_high_energy is True

    ctx_dict = {
        "previous_energy_score": silence_ctx.previous_energy_score,
        "is_after_high_energy": silence_ctx.is_after_high_energy,
        "is_before_high_energy": silence_ctx.is_before_high_energy,
    }

    classification = classify_silence_segment(
        segment=seg,
        context=ctx_dict,
    )

    assert classification.classification == "dramatic_pause"
    assert classification.remove_candidate is False


# ---------------------------------------------------------------------------
# Test 8 — Job and pipeline contract
# ---------------------------------------------------------------------------

def test_2b08_job_and_pipeline_contract():
    # All RMS fields survive roundtrip
    j = _make_job()
    j.rms_energy_report = {"status": "ok"}
    j.rms_energy_status = "ok"
    j.rms_energy_source_selection = {"selected_type": "analysis_audio"}
    j.rms_energy_timeline_result = {"point_count": 5}
    j.rms_energy_selected_path = "/tmp/analysis.wav"
    j.rms_energy_selected_type = "analysis_audio"
    j.rms_energy_timeline_status = "ok"
    j.rms_energy_point_count = 5
    j.rms_energy_duration_seconds = 1.23
    j.rms_energy_sample_rate = 16000
    j.rms_energy_channels = 1
    j.rms_energy_frame_ms = 10.0
    j.rms_energy_hop_ms = 5.0
    j.rms_energy_min_rms = 0.1
    j.rms_energy_max_rms = 0.9
    j.rms_energy_avg_rms = 0.5
    j.rms_energy_min_normalized_energy = 0.0
    j.rms_energy_max_normalized_energy = 1.0
    j.rms_energy_avg_normalized_energy = 0.5
    j.rms_energy_context_adapter = {"status": "ok"}
    j.rms_energy_context_timeline = [{"time_seconds": 0.5, "energy_score": 0.9}]
    j.rms_energy_context_status = "ok"
    j.rms_energy_context_point_count = 1
    j.rms_energy_context_peak_count = 1
    j.rms_energy_context_silent_count = 0

    d = j.to_dict()
    j2 = Job.from_dict(d)

    assert j2.rms_energy_status == "ok"
    assert j2.rms_energy_selected_path == "/tmp/analysis.wav"
    assert j2.rms_energy_selected_type == "analysis_audio"
    assert j2.rms_energy_timeline_status == "ok"
    assert j2.rms_energy_point_count == 5
    assert j2.rms_energy_duration_seconds == pytest.approx(1.23)
    assert j2.rms_energy_sample_rate == 16000
    assert j2.rms_energy_channels == 1
    assert j2.rms_energy_frame_ms == 10.0
    assert j2.rms_energy_hop_ms == 5.0
    assert j2.rms_energy_min_rms == pytest.approx(0.1)
    assert j2.rms_energy_max_rms == pytest.approx(0.9)
    assert j2.rms_energy_avg_rms == pytest.approx(0.5)
    assert j2.rms_energy_min_normalized_energy == 0.0
    assert j2.rms_energy_max_normalized_energy == pytest.approx(1.0)
    assert j2.rms_energy_avg_normalized_energy == pytest.approx(0.5)
    assert j2.rms_energy_context_status == "ok"
    assert j2.rms_energy_context_point_count == 1
    assert j2.rms_energy_context_peak_count == 1
    assert j2.rms_energy_context_silent_count == 0

    # gaming_pipeline.py source contract
    pipeline_src = open("core/gaming_pipeline.py").read()

    assert "run_rms_energy_for_job" in pipeline_src
    assert "adapt_rms_energy_run_report_to_context" in pipeline_src
    assert "RMS_ENERGY_STARTED" in pipeline_src
    assert "RMS_ENERGY_SOURCE_SELECTED" in pipeline_src
    assert "RMS_ENERGY_DONE" in pipeline_src or "RMS_ENERGY_COMPLETED" in pipeline_src
    assert "RMS_ENERGY_BLOCKED" in pipeline_src
    assert "RMS_ENERGY_SKIPPED" in pipeline_src
    assert "RMS_ENERGY_FAILED" in pipeline_src
    assert "RMS_ENERGY_CONTEXT_ADAPTED" in pipeline_src
    assert "RMS_ENERGY_CONTEXT_SKIPPED" in pipeline_src
    assert "run_silence_classifier_for_job" in pipeline_src
    assert "energy_timeline" in pipeline_src
    # gaming_pipeline.py must NOT directly import analyze_wav_rms_energy
    assert "analyze_wav_rms_energy" not in pipeline_src

    # Ordering: PREPROCESSING_READY before RMS_ENERGY_STARTED
    idx_prep = pipeline_src.index("PREPROCESSING_READY")
    idx_rms_start = pipeline_src.index("RMS_ENERGY_STARTED")
    assert idx_prep < idx_rms_start

    # RMS_ENERGY_STARTED before SILENCE_DETECTION_STARTED
    idx_silence_det = pipeline_src.index("SILENCE_DETECTION_STARTED")
    assert idx_rms_start < idx_silence_det

    # RMS_ENERGY_CONTEXT_ADAPTED before SILENCE_CLASSIFICATION_STARTED
    idx_ctx = min(
        pipeline_src.index("RMS_ENERGY_CONTEXT_ADAPTED"),
        pipeline_src.index("RMS_ENERGY_CONTEXT_SKIPPED"),
    )
    idx_classif = pipeline_src.index("SILENCE_CLASSIFICATION_STARTED")
    assert idx_ctx < idx_classif


# ---------------------------------------------------------------------------
# Test 9 — Files: no BOM, end with newline
# ---------------------------------------------------------------------------

_AUDIT_FILES = [
    "models/rms_energy.py",
    "core/rms_energy_analyzer.py",
    "models/rms_energy_audio_source.py",
    "core/rms_energy_audio_source_selector.py",
    "models/rms_energy_run.py",
    "core/rms_energy_runner.py",
    "models/rms_energy_context_adapter.py",
    "core/rms_energy_context_adapter.py",
    "tests/test_rms_energy_timeline_foundation_smoke.py",
    "tests/test_rms_energy_audio_source_selector_smoke.py",
    "tests/test_rms_energy_runner_smoke.py",
    "tests/test_rms_energy_context_adapter_smoke.py",
    "tests/test_rms_energy_pipeline_integration_smoke.py",
    "tests/test_rms_energy_final_audit_smoke.py",
    "core/gaming_pipeline.py",
    "models/job.py",
]


def test_2b08_files_have_no_bom_and_end_with_newline():
    missing = []
    bom_files = []
    no_newline_files = []

    for rel_path in _AUDIT_FILES:
        if not os.path.exists(rel_path):
            missing.append(rel_path)
            continue
        raw = open(rel_path, "rb").read()
        if raw.startswith(b"\xef\xbb\xbf"):
            bom_files.append(rel_path)
        if not raw.endswith(b"\n"):
            no_newline_files.append(rel_path)

    assert missing == [], f"Missing audit files: {missing}"
    assert bom_files == [], f"Files with BOM: {bom_files}"
    assert no_newline_files == [], f"Files not ending with newline: {no_newline_files}"
