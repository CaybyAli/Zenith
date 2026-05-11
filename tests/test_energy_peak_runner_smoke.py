from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any

import pytest

from models.energy_peak_run import EnergyPeakRunReport
from core.energy_peak_runner import (
    build_energy_peak_run_report,
    run_energy_peak_detection_for_job,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_timeline(energy_values: list[float]) -> list[dict[str, Any]]:
    result = []
    for i, e in enumerate(energy_values):
        t = float(i)
        result.append({
            "time_seconds": t,
            "start_seconds": t,
            "end_seconds": t + 1.0,
            "energy_score": e,
            "is_silent": False,
        })
    return result


def _rms_run_report_dict(normalized_energies: list[float]) -> dict[str, Any]:
    points = []
    for i, ne in enumerate(normalized_energies):
        t = float(i) * 0.5
        points.append({
            "start_seconds": t,
            "end_seconds": t + 0.5,
            "center_seconds": t + 0.25,
            "normalized_energy": ne,
            "rms": ne * 0.5,
            "is_silent": False,
        })
    return {
        "status": "ok",
        "energy_timeline_result": {
            "status": "ok",
            "points": points,
        },
    }


# ---------------------------------------------------------------------------
# 1. EnergyPeakRunReport roundtrip
# ---------------------------------------------------------------------------

def test_energy_peak_run_report_roundtrip():
    report = EnergyPeakRunReport(
        status="ok",
        energy_timeline_source="provided_energy_timeline",
        energy_timeline=[{"time_seconds": 1.0, "energy_score": 0.9}],
        peaks=[{"peak_type": "combined", "peak_score": 0.85}],
        peak_count=1,
        high_energy_peak_count=1,
        local_max_peak_count=1,
        rise_peak_count=0,
        threshold_peak_count=1,
        peak_threshold=0.85,
        rise_threshold=0.25,
        min_peak_distance_seconds=0.4,
        max_peak_score=0.85,
        avg_peak_score=0.85,
        top_peak={"peak_type": "combined"},
        rms_context_adapter_result={"status": "ok"},
        warnings=[],
        errors=[],
        recommendation="use_energy_peaks",
        metadata={"extra": 1},
    )
    d = report.to_dict()
    restored = EnergyPeakRunReport.from_dict(d)

    assert restored.status == "ok"
    assert restored.energy_timeline_source == "provided_energy_timeline"
    assert restored.peak_count == 1
    assert restored.high_energy_peak_count == 1
    assert restored.peak_threshold == 0.85
    assert restored.recommendation == "use_energy_peaks"
    assert restored.top_peak["peak_type"] == "combined"
    assert restored.metadata["extra"] == 1


# ---------------------------------------------------------------------------
# 2. Runner uses provided energy_timeline
# ---------------------------------------------------------------------------

def test_runner_uses_provided_energy_timeline():
    timeline = _make_timeline([0.2, 0.9, 0.3])
    report = build_energy_peak_run_report(energy_timeline=timeline, peak_threshold=0.85)

    assert report.status == "ok"
    assert report.energy_timeline_source == "provided_energy_timeline"
    assert report.peak_count >= 1
    assert report.top_peak != {}
    assert report.recommendation == "use_energy_peaks"


# ---------------------------------------------------------------------------
# 3. Runner adapts rms_run_report to energy_timeline
# ---------------------------------------------------------------------------

def test_runner_adapts_rms_run_report_to_energy_timeline():
    rms_report = _rms_run_report_dict([0.2, 0.9, 0.3])
    report = build_energy_peak_run_report(rms_run_report=rms_report, peak_threshold=0.85)

    assert report.energy_timeline_source == "rms_run_report_adapter"
    assert report.peak_count >= 1
    assert report.rms_context_adapter_result != {}


# ---------------------------------------------------------------------------
# 4. Runner skips when no energy_timeline provided
# ---------------------------------------------------------------------------

def test_runner_skips_when_no_energy_timeline():
    report = build_energy_peak_run_report()

    assert report.status == "skipped_no_energy_timeline"
    assert report.recommendation == "no_energy_timeline_available"
    assert "no_energy_timeline_available" in report.warnings


# ---------------------------------------------------------------------------
# 5. Runner handles empty energy_timeline
# ---------------------------------------------------------------------------

def test_runner_handles_empty_energy_timeline():
    report = build_energy_peak_run_report(energy_timeline=[])

    assert report.status in ("skipped_no_energy_timeline", "completed_with_warnings")
    all_messages = report.warnings + report.errors
    assert any(
        m in all_messages
        for m in ("empty_energy_timeline", "no_energy_peaks_detected", "no_energy_items")
    )


# ---------------------------------------------------------------------------
# 6. Runner detects no peaks for flat low energy
# ---------------------------------------------------------------------------

def test_runner_detects_no_peaks_for_flat_low_energy():
    timeline = _make_timeline([0.2, 0.21, 0.2])
    report = build_energy_peak_run_report(energy_timeline=timeline, peak_threshold=0.85)

    assert report.peak_count == 0
    assert report.recommendation == "no_peaks_detected"


# ---------------------------------------------------------------------------
# 7. Runner detects combined peak
# ---------------------------------------------------------------------------

def test_runner_detects_combined_peak():
    timeline = _make_timeline([0.2, 0.95, 0.3])
    report = build_energy_peak_run_report(energy_timeline=timeline, peak_threshold=0.85)

    assert report.peak_count >= 1
    top = report.top_peak
    assert top != {}
    rules = top.get("rules_applied", [])
    assert "threshold_peak" in rules or top.get("peak_type") == "combined"


# ---------------------------------------------------------------------------
# 8. Runner respects max_peaks
# ---------------------------------------------------------------------------

def test_runner_respects_max_peaks():
    # 3 separate peaks far enough apart
    timeline = [
        {"time_seconds": 0.0, "start_seconds": 0.0, "end_seconds": 1.0, "energy_score": 0.9, "is_silent": False},
        {"time_seconds": 2.0, "start_seconds": 2.0, "end_seconds": 3.0, "energy_score": 0.91, "is_silent": False},
        {"time_seconds": 4.0, "start_seconds": 4.0, "end_seconds": 5.0, "energy_score": 0.92, "is_silent": False},
    ]
    report = build_energy_peak_run_report(
        energy_timeline=timeline,
        peak_threshold=0.85,
        min_peak_distance_seconds=0.4,
        max_peaks=2,
    )

    assert report.peak_count == 2


# ---------------------------------------------------------------------------
# 9. Runner respects thresholds
# ---------------------------------------------------------------------------

def test_runner_respects_thresholds():
    # Single item: no neighbours, so only threshold_peak can fire
    timeline = [
        {"time_seconds": 1.0, "start_seconds": 1.0, "end_seconds": 2.0, "energy_score": 0.75, "is_silent": False}
    ]

    report_low = build_energy_peak_run_report(energy_timeline=timeline, peak_threshold=0.7)
    report_high = build_energy_peak_run_report(energy_timeline=timeline, peak_threshold=0.9)

    assert report_low.peak_count >= 1
    assert report_high.peak_count == 0


# ---------------------------------------------------------------------------
# 10. run_for_job reads rms_energy_context_timeline
# ---------------------------------------------------------------------------

def test_run_for_job_reads_rms_energy_context_timeline():
    ctx_timeline = _make_timeline([0.2, 0.9, 0.3])
    job = SimpleNamespace(rms_energy_context_timeline=ctx_timeline)

    report = run_energy_peak_detection_for_job(job, peak_threshold=0.85)

    assert report.peak_count >= 1


# ---------------------------------------------------------------------------
# 11. run_for_job falls back to rms_energy_report when context missing
# ---------------------------------------------------------------------------

def test_run_for_job_reads_rms_energy_report_when_context_missing():
    rms_report = _rms_run_report_dict([0.2, 0.9, 0.3])
    job = SimpleNamespace(
        rms_energy_context_timeline=[],
        rms_energy_report=rms_report,
    )

    report = run_energy_peak_detection_for_job(job, peak_threshold=0.85)

    assert report.peak_count >= 1
    assert report.energy_timeline_source == "rms_run_report_adapter"


# ---------------------------------------------------------------------------
# 12. run_for_job reads rms_energy_context_adapter dict
# ---------------------------------------------------------------------------

def test_run_for_job_reads_rms_energy_context_adapter_dict():
    ctx_timeline = _make_timeline([0.2, 0.9, 0.3])
    job = SimpleNamespace(
        rms_energy_context_timeline=[],
        rms_energy_context_adapter={"energy_timeline": ctx_timeline},
    )

    report = run_energy_peak_detection_for_job(job, peak_threshold=0.85)

    assert report.peak_count >= 1


# ---------------------------------------------------------------------------
# 13. Empty job does not crash
# ---------------------------------------------------------------------------

def test_run_for_empty_job_safe():
    job = SimpleNamespace()

    report = run_energy_peak_detection_for_job(job)

    assert isinstance(report, EnergyPeakRunReport)
    assert report.status in ("skipped_no_energy_timeline", "failed", "completed_with_warnings")


# ---------------------------------------------------------------------------
# 14. Bad energy timeline items do not crash
# ---------------------------------------------------------------------------

def test_runner_bad_energy_timeline_safe():
    timeline = [
        {},
        {"time_seconds": "bad", "energy_score": "bad"},
        {"time_seconds": 5.0, "start_seconds": 5.0, "end_seconds": 6.0, "energy_score": 0.9, "is_silent": False},
    ]

    report = build_energy_peak_run_report(energy_timeline=timeline, peak_threshold=0.85)

    assert isinstance(report, EnergyPeakRunReport)
    assert not report.errors or all("runner_failed" not in e for e in report.errors)


# ---------------------------------------------------------------------------
# 15. Runner output feeds silence context builder
# ---------------------------------------------------------------------------

def test_peak_runner_output_can_feed_silence_context_builder():
    from core.silence_context_builder import build_silence_segment_context

    timeline = _make_timeline([0.2, 0.9, 0.3])
    report = build_energy_peak_run_report(energy_timeline=timeline, peak_threshold=0.85)

    assert report.peak_count >= 1

    top = report.top_peak
    assert top != {}

    energy_for_silence = [{
        "time_seconds": top.get("center_seconds", top.get("start_seconds", 0.0)),
        "start_seconds": top.get("start_seconds", 0.0),
        "end_seconds": top.get("end_seconds", 1.0),
        "energy_score": top.get("energy_score", 0.9),
        "is_peak": True,
        "is_silent": False,
    }]

    silence_segment = {
        "start_seconds": top.get("end_seconds", 1.0) + 0.5,
        "end_seconds": top.get("end_seconds", 1.0) + 1.5,
        "duration_seconds": 1.0,
    }

    ctx = build_silence_segment_context(
        segment=silence_segment,
        energy_timeline=energy_for_silence,
        context_window_seconds=2.0,
    )

    assert ctx.previous_energy_score is not None
    assert ctx.previous_energy_score >= 0.75
    assert ctx.is_after_high_energy is True


# ---------------------------------------------------------------------------
# 16. BOM and trailing newline hygiene
# ---------------------------------------------------------------------------

def test_energy_peak_runner_files_have_no_bom_and_end_with_newline():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = [
        os.path.join(repo_root, "models", "energy_peak_run.py"),
        os.path.join(repo_root, "core", "energy_peak_runner.py"),
        os.path.join(repo_root, "tests", "test_energy_peak_runner_smoke.py"),
    ]
    for path in files:
        with open(path, "rb") as f:
            raw = f.read()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {path}"
        assert raw.endswith(b"\n"), f"No trailing newline in {path}"
