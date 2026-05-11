from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any

import pytest

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)
_PIPELINE_PATH = os.path.join(_REPO_ROOT, "core", "gaming_pipeline.py")


def _make_timeline(energy_values: list[float], spacing: float = 1.0) -> list[dict[str, Any]]:
    result = []
    for i, e in enumerate(energy_values):
        t = i * spacing
        result.append({
            "time_seconds": t,
            "start_seconds": t,
            "end_seconds": t + spacing,
            "energy_score": e,
            "is_silent": False,
        })
    return result


def _read_pipeline_source() -> str:
    with open(_PIPELINE_PATH, encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Test 1: Model roundtrips
# ---------------------------------------------------------------------------

def test_2b09_models_roundtrip():
    from models.energy_peak import EnergyPeak, EnergyPeakDetectionResult
    from models.energy_peak_run import EnergyPeakRunReport
    from models.energy_peak_signal import EnergyPeakSignalAdapterResult

    # EnergyPeak
    peak = EnergyPeak(
        start_seconds=1.0, end_seconds=2.0, center_seconds=1.5,
        energy_score=0.95, peak_score=0.88, peak_type="combined",
        confidence=0.90, reason="combined_energy_peak",
        source_index=3, is_local_maximum=True,
        rise_delta=0.45, fall_delta=0.30,
        window_energy_before=0.50, window_energy_after=0.65,
        source_item={"raw": True},
        rules_applied=["threshold_peak", "local_maximum"],
        warnings=[], errors=[], metadata={"x": 1},
    )
    d = peak.to_dict()
    p2 = EnergyPeak.from_dict(d)
    assert p2.start_seconds == peak.start_seconds
    assert p2.end_seconds == peak.end_seconds
    assert p2.peak_type == "combined"
    assert p2.rules_applied == ["threshold_peak", "local_maximum"]
    assert p2.is_local_maximum is True
    assert p2.source_index == 3
    assert p2.window_energy_before == pytest.approx(0.50)
    assert p2.rise_delta == pytest.approx(0.45)

    # EnergyPeakDetectionResult
    det = EnergyPeakDetectionResult(
        status="ok", peaks=[peak], peak_count=1,
        high_energy_peak_count=1, local_max_peak_count=1,
        rise_peak_count=0, threshold_peak_count=1,
        peak_threshold=0.85, min_peak_distance_seconds=0.4,
    )
    d2 = det.to_dict()
    det2 = EnergyPeakDetectionResult.from_dict(d2)
    assert det2.status == "ok"
    assert det2.peak_count == 1
    assert len(det2.peaks) == 1
    assert det2.peaks[0].peak_type == "combined"
    assert det2.peak_threshold == pytest.approx(0.85)
    assert det2.high_energy_peak_count == 1
    assert det2.local_max_peak_count == 1

    # EnergyPeakRunReport
    report = EnergyPeakRunReport(
        status="ok",
        energy_timeline_source="provided_energy_timeline",
        peaks=[peak.to_dict()],
        peak_count=1,
        high_energy_peak_count=1,
        local_max_peak_count=1,
        rise_peak_count=0,
        threshold_peak_count=1,
        peak_threshold=0.85,
        rise_threshold=0.25,
        min_peak_distance_seconds=0.4,
        max_peak_score=0.88,
        avg_peak_score=0.88,
        top_peak=peak.to_dict(),
        recommendation="use_energy_peaks",
    )
    rd = report.to_dict()
    r2 = EnergyPeakRunReport.from_dict(rd)
    assert r2.status == "ok"
    assert r2.energy_timeline_source == "provided_energy_timeline"
    assert r2.peak_count == 1
    assert len(r2.peaks) == 1
    assert r2.max_peak_score == pytest.approx(0.88)
    assert r2.rise_threshold == pytest.approx(0.25)
    assert r2.recommendation == "use_energy_peaks"

    # EnergyPeakSignalAdapterResult
    sig_res = EnergyPeakSignalAdapterResult(
        status="ok",
        signals=[{"signal_type": "combined_energy_peak", "signal_score": 0.88}],
        signal_count=1,
        peak_count=1,
        high_priority_signal_count=1,
        signal_types={"combined_energy_peak": 1},
        max_signal_score=0.88,
        avg_signal_score=0.88,
        recommendation="use_edit_signals",
    )
    sd = sig_res.to_dict()
    s2 = EnergyPeakSignalAdapterResult.from_dict(sd)
    assert s2.status == "ok"
    assert s2.signal_count == 1
    assert s2.signal_types == {"combined_energy_peak": 1}
    assert s2.max_signal_score == pytest.approx(0.88)
    assert s2.recommendation == "use_edit_signals"


# ---------------------------------------------------------------------------
# Test 2: Detector core rules contract
# ---------------------------------------------------------------------------

def test_2b09_detector_core_rules_contract():
    from core.energy_peak_detector import detect_energy_peaks

    # High energy: e=0.9 >= 0.85 threshold → threshold_peak in rules
    result = detect_energy_peaks(_make_timeline([0.2, 0.4, 0.9, 0.3]))
    assert result.peak_count > 0
    high_peak = next(p for p in result.peaks if p.energy_score >= 0.85)
    assert "threshold_peak" in high_peak.rules_applied

    # Local maximum (pure): [0.55, 0.60, 0.55] — rise=0.05 < 0.25, no threshold
    result = detect_energy_peaks(_make_timeline([0.55, 0.60, 0.55]))
    assert result.peak_count > 0
    lm_peak = result.peaks[0]
    assert lm_peak.is_local_maximum is True
    assert "local_maximum" in lm_peak.rules_applied
    assert lm_peak.peak_type == "local_maximum"

    # Sudden rise (pure): [0.1, 0.2, 0.55, 0.6] — index 2: rise=0.35>=0.25, but NOT local max (next=0.6>0.55)
    result = detect_energy_peaks(_make_timeline([0.1, 0.2, 0.55, 0.6]))
    assert result.peak_count > 0
    rise_peak = next(p for p in result.peaks if "sudden_rise" in p.rules_applied)
    assert rise_peak is not None
    assert rise_peak.peak_type == "sudden_rise"

    # Combined: [0.2, 0.95, 0.3] — threshold + local_max + sudden_rise → combined
    result = detect_energy_peaks(_make_timeline([0.2, 0.95, 0.3]))
    assert result.peak_count > 0
    combined_peak = result.peaks[0]
    assert combined_peak.peak_type == "combined"
    assert len(combined_peak.rules_applied) >= 2

    # Flat low energy → no peaks
    result = detect_energy_peaks(_make_timeline([0.2, 0.21, 0.2]))
    assert result.peak_count == 0

    # is_silent=True + energy=0.4 (below threshold) → no peak
    silent_item = [{
        "time_seconds": 0.0, "start_seconds": 0.0, "end_seconds": 1.0,
        "energy_score": 0.4, "is_silent": True,
    }]
    result = detect_energy_peaks(silent_item)
    assert result.peak_count == 0


# ---------------------------------------------------------------------------
# Test 3: Deduplicate and max_peaks contract
# ---------------------------------------------------------------------------

def test_2b09_detector_dedupe_and_limits_contract():
    from core.energy_peak_detector import detect_energy_peaks

    # Two peaks close together (t=0.0 and t=0.2, distance 0.2 < 0.4)
    # Third peak far away (t=5.0) — must survive
    close_timeline = [
        {"time_seconds": 0.0, "start_seconds": 0.0, "end_seconds": 0.5, "energy_score": 0.9, "is_silent": False},
        {"time_seconds": 0.2, "start_seconds": 0.2, "end_seconds": 0.7, "energy_score": 0.95, "is_silent": False},
        {"time_seconds": 5.0, "start_seconds": 5.0, "end_seconds": 5.5, "energy_score": 0.88, "is_silent": False},
    ]
    result = detect_energy_peaks(close_timeline, min_peak_distance_seconds=0.4)
    assert result.peak_count == 2
    centers = [p.center_seconds for p in result.peaks]
    assert any(abs(c - 5.0) < 0.1 for c in centers), "Far peak must survive deduplication"
    # Chronological order
    assert result.peaks == sorted(result.peaks, key=lambda p: p.center_seconds)

    # max_peaks=2 from 3 peaks: weakest (t=4.0) excluded, result re-sorted chronologically
    three_timeline = [
        {"time_seconds": 0.0, "start_seconds": 0.0, "end_seconds": 1.0, "energy_score": 0.9, "is_silent": False},
        {"time_seconds": 2.0, "start_seconds": 2.0, "end_seconds": 3.0, "energy_score": 0.95, "is_silent": False},
        {"time_seconds": 4.0, "start_seconds": 4.0, "end_seconds": 5.0, "energy_score": 0.88, "is_silent": False},
    ]
    result = detect_energy_peaks(three_timeline, min_peak_distance_seconds=0.4, max_peaks=2)
    assert result.peak_count == 2
    assert result.peaks == sorted(result.peaks, key=lambda p: p.center_seconds)
    # The weakest peak at t=4 is excluded (scores: t=0→0.585, t=2→0.6745, t=4→0.572)
    peak_centers = [p.center_seconds for p in result.peaks]
    assert not any(abs(c - 4.0) < 0.1 for c in peak_centers), "Weakest peak must be excluded by max_peaks"


# ---------------------------------------------------------------------------
# Test 4: Runner contract
# ---------------------------------------------------------------------------

def test_2b09_runner_contract():
    from core.energy_peak_runner import build_energy_peak_run_report

    # With provided energy_timeline → peak detected
    tl = _make_timeline([0.2, 0.95, 0.3])
    report = build_energy_peak_run_report(energy_timeline=tl)
    assert report.status in ("ok", "completed_with_warnings")
    assert report.peak_count > 0
    assert report.energy_timeline_source == "provided_energy_timeline"

    # With rms_run_report → uses rms_run_report_adapter
    rms_dict = {
        "status": "ok",
        "energy_timeline_result": {
            "status": "ok",
            "points": [
                {"start_seconds": 0.0, "end_seconds": 1.0, "center_seconds": 0.5,
                 "normalized_energy": 0.2, "rms": 0.1, "is_silent": False},
                {"start_seconds": 1.0, "end_seconds": 2.0, "center_seconds": 1.5,
                 "normalized_energy": 0.95, "rms": 0.8, "is_silent": False},
                {"start_seconds": 2.0, "end_seconds": 3.0, "center_seconds": 2.5,
                 "normalized_energy": 0.3, "rms": 0.2, "is_silent": False},
            ],
        },
    }
    report = build_energy_peak_run_report(rms_run_report=rms_dict)
    assert report.energy_timeline_source == "rms_run_report_adapter"
    assert report.peak_count > 0

    # No timeline provided → skipped
    report = build_energy_peak_run_report()
    assert report.status == "skipped_no_energy_timeline"
    assert "no_energy_timeline_available" in report.recommendation

    # Empty energy_timeline → skipped safely
    report = build_energy_peak_run_report(energy_timeline=[])
    assert report.status == "skipped_no_energy_timeline"

    # Flat low energy → no_peaks_detected
    flat = _make_timeline([0.2, 0.21, 0.2])
    report = build_energy_peak_run_report(energy_timeline=flat)
    assert report.status in ("completed_with_warnings",)
    assert report.recommendation == "no_peaks_detected"

    # Bad timeline (garbage dict) → no crash
    report = build_energy_peak_run_report(energy_timeline={"garbage": True})
    assert report is not None
    assert report.status in ("skipped_no_energy_timeline", "completed_with_warnings", "ok", "failed")


# ---------------------------------------------------------------------------
# Test 5: Job runner fallback contract
# ---------------------------------------------------------------------------

def test_2b09_job_runner_fallback_contract():
    from core.energy_peak_runner import run_energy_peak_detection_for_job

    good_tl = _make_timeline([0.2, 0.95, 0.3])

    # job.rms_energy_context_timeline is read
    job1 = SimpleNamespace(rms_energy_context_timeline=good_tl)
    r1 = run_energy_peak_detection_for_job(job1)
    assert r1.peak_count > 0
    assert r1.energy_timeline_source == "provided_energy_timeline"

    # job.energy_timeline is read when rms_energy_context_timeline is absent/None
    job2 = SimpleNamespace(rms_energy_context_timeline=None, energy_timeline=good_tl)
    r2 = run_energy_peak_detection_for_job(job2)
    assert r2.peak_count > 0

    # job.rms_energy_context_adapter["energy_timeline"] is read
    job3 = SimpleNamespace(
        rms_energy_context_timeline=None,
        energy_timeline=None,
        rms_energy_context_adapter={"energy_timeline": good_tl},
    )
    r3 = run_energy_peak_detection_for_job(job3)
    assert r3.peak_count > 0

    # job.rms_energy_report as fallback
    rms_rr = {
        "status": "ok",
        "energy_timeline_result": {
            "status": "ok",
            "points": [
                {"start_seconds": 0.0, "end_seconds": 1.0, "center_seconds": 0.5,
                 "normalized_energy": 0.95, "rms": 0.8, "is_silent": False},
            ],
        },
    }
    job4 = SimpleNamespace(
        rms_energy_context_timeline=None,
        energy_timeline=None,
        rms_energy_context_adapter=None,
        rms_energy_report=rms_rr,
    )
    r4 = run_energy_peak_detection_for_job(job4)
    assert r4.energy_timeline_source == "rms_run_report_adapter"
    assert r4.peak_count > 0

    # Empty job → skipped, no crash
    r5 = run_energy_peak_detection_for_job(SimpleNamespace())
    assert r5 is not None
    assert r5.status == "skipped_no_energy_timeline"


# ---------------------------------------------------------------------------
# Test 6: Signal adapter contract
# ---------------------------------------------------------------------------

def test_2b09_signal_adapter_contract():
    from core.energy_peak_signal_adapter import (
        adapt_energy_peaks_to_signals,
        energy_peak_to_signal,
    )

    def _peak(peak_type: str, energy: float = 0.9, score: float = 0.85, confidence: float = 0.88) -> dict[str, Any]:
        return {
            "peak_type": peak_type,
            "start_seconds": 9.0,
            "end_seconds": 11.0,
            "center_seconds": 10.0,
            "energy_score": energy,
            "peak_score": score,
            "confidence": confidence,
            "reason": f"{peak_type}_reason",
            "source_index": 0,
            "rules_applied": [],
            "metadata": {},
        }

    # combined → combined_energy_peak
    assert energy_peak_to_signal(_peak("combined"))["signal_type"] == "combined_energy_peak"

    # high_energy → high_energy_peak
    assert energy_peak_to_signal(_peak("high_energy"))["signal_type"] == "high_energy_peak"

    # local_maximum → local_maximum_peak
    assert energy_peak_to_signal(_peak("local_maximum", energy=0.65, score=0.60))["signal_type"] == "local_maximum_peak"

    # sudden_rise → sudden_rise_peak
    assert energy_peak_to_signal(_peak("sudden_rise", energy=0.65, score=0.60))["signal_type"] == "sudden_rise_peak"

    # center fallback: no center_seconds → (start+end)/2
    peak_no_center: dict[str, Any] = {
        "peak_type": "high_energy",
        "start_seconds": 4.0,
        "end_seconds": 6.0,
        "energy_score": 0.9,
        "peak_score": 0.88,
        "confidence": 0.80,
        "reason": "test",
        "source_index": 0,
        "rules_applied": [],
        "metadata": {},
    }
    sig = energy_peak_to_signal(peak_no_center)
    assert sig["center_seconds"] == pytest.approx(5.0)

    # recommended_start/end_seconds are built around center
    sig = energy_peak_to_signal(_peak("combined"))
    assert "recommended_start_seconds" in sig
    assert "recommended_end_seconds" in sig
    assert sig["recommended_start_seconds"] < sig["center_seconds"]
    assert sig["recommended_end_seconds"] > sig["center_seconds"]

    # priority: high when score >= 0.80
    sig_high = energy_peak_to_signal(_peak("combined", score=0.85, confidence=0.90))
    assert sig_high["priority"] == "high"

    # priority: low when score < 0.55
    sig_low = energy_peak_to_signal(_peak("sudden_rise", energy=0.52, score=0.50, confidence=0.70))
    assert sig_low["priority"] == "low"

    # max_signals limits output
    many_peaks = [_peak("combined", energy=0.9 + i * 0.01, score=0.85 + i * 0.01) for i in range(5)]
    result = adapt_energy_peaks_to_signals(many_peaks, max_signals=2)
    assert result.signal_count == 2

    # No peaks → safe skipped result
    result = adapt_energy_peaks_to_signals([])
    assert result.status == "skipped_no_peaks"
    assert result.signal_count == 0

    # Bad / None peak data → no crash
    result = adapt_energy_peaks_to_signals([None, {}, {"peak_type": "combined", "energy_score": "bad"}])
    assert result is not None


# ---------------------------------------------------------------------------
# Test 7: Integrated flow RMS → peak → signal → silence context
# ---------------------------------------------------------------------------

def test_2b09_integrated_flow_rms_to_peak_to_signal_to_silence_context():
    from models.rms_energy import RmsEnergyPoint, RmsEnergyTimelineResult
    from core.rms_energy_context_adapter import adapt_rms_energy_timeline_to_context
    from core.energy_peak_detector import detect_energy_peaks
    from core.energy_peak_runner import build_energy_peak_run_report
    from core.energy_peak_signal_adapter import adapt_energy_peak_run_report_to_signals
    from core.silence_context_builder import build_silence_segment_context

    # RMS timeline: low → high (0.95) → low
    points = [
        RmsEnergyPoint(start_seconds=0.0, end_seconds=1.0, center_seconds=0.5,
                       rms=0.1, normalized_energy=0.2, dbfs=-20.0, sample_count=100, is_silent=False),
        RmsEnergyPoint(start_seconds=1.0, end_seconds=2.0, center_seconds=1.5,
                       rms=0.8, normalized_energy=0.95, dbfs=-3.0, sample_count=100, is_silent=False),
        RmsEnergyPoint(start_seconds=2.0, end_seconds=3.0, center_seconds=2.5,
                       rms=0.15, normalized_energy=0.3, dbfs=-18.0, sample_count=100, is_silent=False),
    ]
    rms_timeline = RmsEnergyTimelineResult(
        status="ok", points=points, point_count=3,
        min_rms=0.1, max_rms=0.8, avg_rms=0.35,
        min_normalized_energy=0.2, max_normalized_energy=0.95, avg_normalized_energy=0.48,
    )

    # Adapt RMS → context energy_timeline
    ctx = adapt_rms_energy_timeline_to_context(rms_timeline)
    assert ctx.status in ("ok", "completed_with_warnings")
    assert len(ctx.energy_timeline) == 3

    # Detect peaks
    det = detect_energy_peaks(ctx.energy_timeline)
    assert det.peak_count > 0
    high_peak = max(det.peaks, key=lambda p: p.energy_score)
    assert high_peak.energy_score == pytest.approx(0.95, abs=0.01)

    # Build run report
    report = build_energy_peak_run_report(energy_timeline=ctx.energy_timeline)
    assert report.peak_count > 0
    assert report.status in ("ok", "completed_with_warnings")

    # Adapt to edit signals
    signals_result = adapt_energy_peak_run_report_to_signals(report)
    assert signals_result.signal_count > 0
    sig = signals_result.signals[0]
    # Future-edit-compatible fields present
    assert "signal_type" in sig
    assert "recommended_start_seconds" in sig
    assert "recommended_end_seconds" in sig
    assert "priority" in sig
    assert "signal_score" in sig

    # Build silence context for segment AFTER the high-energy peak
    # Silence at t=2.2–2.8; prev window [1.2, 2.2] contains peak at t=1.5 (energy=0.95)
    silence_seg = {"start_seconds": 2.2, "end_seconds": 2.8, "duration_seconds": 0.6}
    silence_ctx = build_silence_segment_context(
        segment=silence_seg,
        energy_timeline=ctx.energy_timeline,
    )
    assert silence_ctx.previous_energy_score is not None
    assert silence_ctx.is_after_high_energy is True


# ---------------------------------------------------------------------------
# Test 8: Job and pipeline contract
# ---------------------------------------------------------------------------

def test_2b09_job_and_pipeline_contract():
    from models.job import Job
    from shared.enums import (
        AutopublishClass, ChannelType, JobStatus, JobType, Mode, TargetFormat, ValidatorStatus,
    )

    job = Job(
        job_id="audit-ep-001",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        energy_peak_report={"status": "ok", "peak_count": 2},
        energy_peak_status="ok",
        energy_peak_timeline_source="provided_energy_timeline",
        energy_peak_detection_result={"status": "ok", "peak_count": 2},
        energy_peaks=[{"peak_type": "combined", "energy_score": 0.95}],
        energy_peak_count=2,
        energy_high_energy_peak_count=2,
        energy_local_max_peak_count=1,
        energy_rise_peak_count=1,
        energy_threshold_peak_count=2,
        energy_peak_threshold=0.85,
        energy_rise_threshold=0.25,
        energy_min_peak_distance_seconds=0.4,
        energy_max_peak_score=0.92,
        energy_avg_peak_score=0.87,
        energy_top_peak={"peak_type": "combined", "peak_score": 0.92},
        energy_peak_recommendation="use_energy_peaks",
    )
    d = job.to_dict()
    j2 = Job.from_dict(d)

    assert j2.energy_peak_report == {"status": "ok", "peak_count": 2}
    assert j2.energy_peak_status == "ok"
    assert j2.energy_peak_timeline_source == "provided_energy_timeline"
    assert j2.energy_peak_detection_result == {"status": "ok", "peak_count": 2}
    assert len(j2.energy_peaks) == 1
    assert j2.energy_peak_count == 2
    assert j2.energy_high_energy_peak_count == 2
    assert j2.energy_local_max_peak_count == 1
    assert j2.energy_rise_peak_count == 1
    assert j2.energy_threshold_peak_count == 2
    assert j2.energy_peak_threshold == pytest.approx(0.85)
    assert j2.energy_rise_threshold == pytest.approx(0.25)
    assert j2.energy_min_peak_distance_seconds == pytest.approx(0.4)
    assert j2.energy_max_peak_score == pytest.approx(0.92)
    assert j2.energy_avg_peak_score == pytest.approx(0.87)
    assert j2.energy_top_peak["peak_type"] == "combined"
    assert j2.energy_peak_recommendation == "use_energy_peaks"

    # Pipeline source contract
    src = _read_pipeline_source()

    assert "from core.energy_peak_runner import run_energy_peak_detection_for_job" in src
    assert "ENERGY_PEAK_DETECTION_STARTED" in src
    assert "ENERGY_PEAK_DETECTION_DONE" in src
    assert "ENERGY_PEAK_DETECTION_SKIPPED" in src
    assert "ENERGY_PEAK_DETECTION_FAILED" in src
    assert "energy_peak_detection_done" in src
    # Pipeline must NOT import detect_energy_peaks directly
    assert "from core.energy_peak_detector import detect_energy_peaks" not in src
    assert "job.energy_peak_report =" in src
    assert "job.energy_peak_status =" in src
    assert "job.energy_peaks =" in src
    assert "job.energy_peak_count =" in src
    assert "job.energy_top_peak =" in src

    # Ordering invariants
    rms_start_pos = src.index("RMS_ENERGY_STARTED")
    ep_start_pos = src.index("ENERGY_PEAK_DETECTION_STARTED")
    rms_ctx_adapted_pos = src.index("RMS_ENERGY_CONTEXT_ADAPTED")
    rms_ctx_skipped_pos = src.index("RMS_ENERGY_CONTEXT_SKIPPED")
    silence_start_pos = src.index("SILENCE_DETECTION_STARTED")
    state_pos = src.index("STATE_ANALYZING")

    assert rms_start_pos < ep_start_pos, "RMS_ENERGY_STARTED must precede ENERGY_PEAK_DETECTION_STARTED"
    assert min(rms_ctx_adapted_pos, rms_ctx_skipped_pos) < ep_start_pos, \
        "RMS context must be handled before ENERGY_PEAK_DETECTION_STARTED"
    assert ep_start_pos < silence_start_pos, "Energy peak must precede silence detection"
    assert ep_start_pos < state_pos, "Energy peak must precede STATE_ANALYZING"


# ---------------------------------------------------------------------------
# Test 9: Pipeline expected skip state contract
# ---------------------------------------------------------------------------

def test_2b09_pipeline_expected_skip_state_contract():
    from core.energy_peak_runner import run_energy_peak_detection_for_job

    # Bare SimpleNamespace (no timeline attributes) → skipped, no crash
    report = run_energy_peak_detection_for_job(SimpleNamespace())
    assert report is not None
    assert report.status == "skipped_no_energy_timeline"
    assert "no_energy_timeline_available" in report.recommendation
    assert report.peak_count == 0

    # Job with all timeline attributes explicitly None → same outcome
    job = SimpleNamespace(
        rms_energy_context_timeline=None,
        energy_timeline=None,
        rms_energy_context_adapter=None,
        rms_energy_report=None,
    )
    report = run_energy_peak_detection_for_job(job)
    assert report.status == "skipped_no_energy_timeline"
    assert report.peak_count == 0


# ---------------------------------------------------------------------------
# Test 10: No BOM and trailing newline for all 2B-09 files
# ---------------------------------------------------------------------------

def test_2b09_files_have_no_bom_and_end_with_newline():
    files_to_check = [
        os.path.join(_REPO_ROOT, "models", "energy_peak.py"),
        os.path.join(_REPO_ROOT, "core", "energy_peak_detector.py"),
        os.path.join(_REPO_ROOT, "models", "energy_peak_run.py"),
        os.path.join(_REPO_ROOT, "core", "energy_peak_runner.py"),
        os.path.join(_REPO_ROOT, "models", "energy_peak_signal.py"),
        os.path.join(_REPO_ROOT, "core", "energy_peak_signal_adapter.py"),
        os.path.join(_REPO_ROOT, "tests", "test_energy_peak_detector_foundation_smoke.py"),
        os.path.join(_REPO_ROOT, "tests", "test_energy_peak_runner_smoke.py"),
        os.path.join(_REPO_ROOT, "tests", "test_energy_peak_pipeline_integration_smoke.py"),
        os.path.join(_REPO_ROOT, "tests", "test_energy_peak_signal_adapter_smoke.py"),
        os.path.join(_REPO_ROOT, "tests", "test_energy_peak_final_audit_smoke.py"),
        os.path.join(_REPO_ROOT, "core", "gaming_pipeline.py"),
        os.path.join(_REPO_ROOT, "models", "job.py"),
    ]

    BOM = b"\xef\xbb\xbf"
    bom_files: list[str] = []
    no_newline_files: list[str] = []

    for path in files_to_check:
        assert os.path.isfile(path), f"Missing file: {path}"
        with open(path, "rb") as f:
            content = f.read()
        if content.startswith(BOM):
            bom_files.append(os.path.basename(path))
        if content and not content.endswith(b"\n"):
            no_newline_files.append(os.path.basename(path))

    assert not bom_files, f"UTF-8 BOM found in: {bom_files}"
    assert not no_newline_files, f"No trailing newline in: {no_newline_files}"
