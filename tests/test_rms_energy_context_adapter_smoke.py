from __future__ import annotations

import os
from typing import Any

import pytest

from models.rms_energy import RmsEnergyPoint, RmsEnergyTimelineResult
from models.rms_energy_run import RmsEnergyRunReport
from models.rms_energy_context_adapter import RmsEnergyContextAdapterResult
from core.rms_energy_context_adapter import (
    adapt_rms_energy_run_report_to_context,
    adapt_rms_energy_timeline_to_context,
    convert_rms_point_to_energy_context_item,
)
from core.silence_context_builder import build_silence_segment_context
from core.adaptive_silence_classifier import classify_silence_segment

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)


def _make_point_obj(
    start: float = 0.0,
    end: float = 1.0,
    center: float | None = None,
    rms: float = 0.4,
    normalized_energy: float = 0.5,
    dbfs: float | None = -20.0,
    is_silent: bool = False,
) -> RmsEnergyPoint:
    return RmsEnergyPoint(
        start_seconds=start,
        end_seconds=end,
        center_seconds=center if center is not None else (start + end) / 2.0,
        rms=rms,
        normalized_energy=normalized_energy,
        dbfs=dbfs,
        is_silent=is_silent,
    )


def _make_timeline_result(points: list[RmsEnergyPoint]) -> RmsEnergyTimelineResult:
    return RmsEnergyTimelineResult(
        status="ok",
        points=points,
        point_count=len(points),
    )


def _make_run_report(timeline_result: RmsEnergyTimelineResult) -> RmsEnergyRunReport:
    return RmsEnergyRunReport(
        status="ok",
        selected_path="/tmp/audio.wav",
        selected_type="analysis_audio",
        energy_timeline_result=timeline_result.to_dict(),
        point_count=timeline_result.point_count,
    )


# ── 1. roundtrip ─────────────────────────────────────────────────────────────

def test_rms_energy_context_adapter_result_roundtrip():
    result = RmsEnergyContextAdapterResult(
        status="ok",
        energy_timeline=[{"time_seconds": 1.0, "energy_score": 0.7, "is_peak": False}],
        point_count=1,
        peak_count=0,
        silent_count=0,
        peak_threshold=0.85,
        min_energy_score=0.7,
        max_energy_score=0.7,
        avg_energy_score=0.7,
    )
    d = result.to_dict()
    restored = RmsEnergyContextAdapterResult.from_dict(d)
    assert restored.status == "ok"
    assert restored.point_count == 1
    assert restored.peak_threshold == 0.85
    assert len(restored.energy_timeline) == 1
    assert restored.energy_timeline[0]["energy_score"] == pytest.approx(0.7)


# ── 2. convert RmsEnergyPoint object ─────────────────────────────────────────

def test_convert_rms_point_object_to_context_item():
    point = _make_point_obj(start=1.0, end=2.0, center=1.5, normalized_energy=0.9, is_silent=False)
    item = convert_rms_point_to_energy_context_item(point, peak_threshold=0.85)
    assert item["time_seconds"] == pytest.approx(1.5)
    assert item["energy_score"] == pytest.approx(0.9)
    assert item["is_peak"] is True
    assert item["is_silent"] is False
    assert item["source"] == "rms_energy_timeline"


# ── 3. convert dict point ─────────────────────────────────────────────────────

def test_convert_rms_point_dict_to_context_item():
    point = {
        "start_seconds": 1.0,
        "end_seconds": 2.0,
        "center_seconds": 1.5,
        "rms": 0.4,
        "normalized_energy": 0.9,
        "dbfs": -10.0,
        "is_silent": False,
    }
    item = convert_rms_point_to_energy_context_item(point, peak_threshold=0.85)
    assert item["time_seconds"] == pytest.approx(1.5)
    assert item["energy_score"] == pytest.approx(0.9)
    assert item["is_peak"] is True


# ── 4. center fallback ────────────────────────────────────────────────────────

def test_convert_point_uses_center_fallback():
    point = {
        "start_seconds": 2.0,
        "end_seconds": 4.0,
        "rms": 0.3,
        "normalized_energy": 0.5,
    }
    item = convert_rms_point_to_energy_context_item(point)
    assert item["time_seconds"] == pytest.approx(3.0)


# ── 5. adapt timeline result object ──────────────────────────────────────────

def test_adapt_timeline_result_object_to_context():
    points = [
        _make_point_obj(start=0.0, end=1.0, normalized_energy=0.5),
        _make_point_obj(start=1.0, end=2.0, normalized_energy=0.7),
        _make_point_obj(start=2.0, end=3.0, normalized_energy=0.9),
    ]
    timeline = _make_timeline_result(points)
    result = adapt_rms_energy_timeline_to_context(timeline)
    assert result.status == "ok"
    assert result.point_count == 3
    assert len(result.energy_timeline) == 3


# ── 6. adapt timeline dict ────────────────────────────────────────────────────

def test_adapt_timeline_result_dict_to_context():
    points = [
        _make_point_obj(start=0.0, end=1.0, normalized_energy=0.5),
        _make_point_obj(start=1.0, end=2.0, normalized_energy=0.6),
    ]
    timeline = _make_timeline_result(points)
    result = adapt_rms_energy_timeline_to_context(timeline.to_dict())
    assert result.point_count == 2


# ── 7. adapt list directly ────────────────────────────────────────────────────

def test_adapt_timeline_list_directly():
    raw_points = [
        {"start_seconds": 0.0, "end_seconds": 1.0, "center_seconds": 0.5, "normalized_energy": 0.4, "rms": 0.2},
        {"start_seconds": 1.0, "end_seconds": 2.0, "center_seconds": 1.5, "normalized_energy": 0.6, "rms": 0.3},
        {"start_seconds": 2.0, "end_seconds": 3.0, "center_seconds": 2.5, "normalized_energy": 0.8, "rms": 0.4},
    ]
    result = adapt_rms_energy_timeline_to_context(raw_points)
    assert result.point_count == 3


# ── 8. peak threshold ─────────────────────────────────────────────────────────

def test_peak_threshold_marks_peaks():
    points = [
        _make_point_obj(start=0.0, end=1.0, normalized_energy=0.4),
        _make_point_obj(start=1.0, end=2.0, normalized_energy=0.9),
    ]
    timeline = _make_timeline_result(points)
    result = adapt_rms_energy_timeline_to_context(timeline, peak_threshold=0.85)
    assert result.peak_count == 1


# ── 9. silent filter ──────────────────────────────────────────────────────────

def test_include_silent_points_false_filters_silent():
    points = [
        _make_point_obj(start=0.0, end=1.0, normalized_energy=0.1, is_silent=True),
        _make_point_obj(start=1.0, end=2.0, normalized_energy=0.8, is_silent=False),
    ]
    timeline = _make_timeline_result(points)
    result = adapt_rms_energy_timeline_to_context(timeline, include_silent_points=False)
    assert result.point_count == 1
    assert result.silent_count == 0


# ── 10. empty timeline safe ───────────────────────────────────────────────────

def test_empty_timeline_is_safe():
    timeline = _make_timeline_result([])
    result = adapt_rms_energy_timeline_to_context(timeline)
    assert result.status in ("ok", "completed_with_warnings")
    assert result.point_count == 0
    assert "no_rms_energy_points" in result.warnings


# ── 11. bad points safe ───────────────────────────────────────────────────────

def test_bad_points_do_not_crash():
    raw_points: list[Any] = [
        {},
        {"center_seconds": "bad", "normalized_energy": "bad"},
    ]
    result = adapt_rms_energy_timeline_to_context(raw_points)
    assert result is not None
    assert result.point_count >= 0


# ── 12. adapt run report object ───────────────────────────────────────────────

def test_adapt_run_report_object_to_context():
    points = [
        _make_point_obj(start=0.0, end=1.0, normalized_energy=0.7),
        _make_point_obj(start=1.0, end=2.0, normalized_energy=0.9),
    ]
    timeline = _make_timeline_result(points)
    report = _make_run_report(timeline)
    result = adapt_rms_energy_run_report_to_context(report)
    assert result.point_count > 0
    assert "source_status" in result.metadata
    assert "selected_type" in result.metadata


# ── 13. adapt run report dict ─────────────────────────────────────────────────

def test_adapt_run_report_dict_to_context():
    points = [
        _make_point_obj(start=0.0, end=1.0, normalized_energy=0.6),
        _make_point_obj(start=1.0, end=2.0, normalized_energy=0.8),
    ]
    timeline = _make_timeline_result(points)
    report = _make_run_report(timeline)
    result = adapt_rms_energy_run_report_to_context(report.to_dict())
    assert result.point_count > 0


# ── 14. missing timeline → failed ────────────────────────────────────────────

def test_missing_run_report_energy_timeline_failed():
    report = RmsEnergyRunReport(
        status="ok",
        energy_timeline_result={},
    )
    result = adapt_rms_energy_run_report_to_context(report)
    assert result.status == "failed"
    assert "missing_energy_timeline_result" in result.errors


# ── 15. integration with silence context builder ──────────────────────────────

def test_adapter_energy_timeline_works_with_silence_context_builder():
    point = _make_point_obj(start=9.0, end=10.0, center=9.5, normalized_energy=0.9, is_silent=False)
    timeline = _make_timeline_result([point])
    adapter_result = adapt_rms_energy_timeline_to_context(timeline)

    segment = {"start_seconds": 10.0, "end_seconds": 11.0, "duration_seconds": 1.0}
    ctx = build_silence_segment_context(segment, energy_timeline=adapter_result.energy_timeline)

    assert ctx.previous_energy_score == pytest.approx(0.9)
    assert ctx.is_after_high_energy is True


# ── 16. integration with adaptive classifier ──────────────────────────────────

def test_adapter_energy_timeline_works_with_adaptive_classifier():
    point = _make_point_obj(start=0.0, end=1.0, center=0.5, normalized_energy=0.9, is_silent=False)
    timeline = _make_timeline_result([point])
    adapter_result = adapt_rms_energy_timeline_to_context(timeline)

    segment = {"start_seconds": 1.0, "end_seconds": 2.2, "duration_seconds": 1.2}
    ctx = build_silence_segment_context(segment, energy_timeline=adapter_result.energy_timeline)
    classification = classify_silence_segment(segment, context=ctx.to_dict())

    assert classification.classification == "dramatic_pause"
    assert classification.remove_candidate is False


# ── 17. BOM and newline hygiene ───────────────────────────────────────────────

def test_rms_energy_context_adapter_files_have_no_bom_and_end_with_newline():
    files = [
        os.path.join(_REPO_ROOT, "models", "rms_energy_context_adapter.py"),
        os.path.join(_REPO_ROOT, "core", "rms_energy_context_adapter.py"),
        os.path.join(_REPO_ROOT, "tests", "test_rms_energy_context_adapter_smoke.py"),
    ]
    for path in files:
        with open(path, "rb") as f:
            raw = f.read()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {path}"
        assert raw.endswith(b"\n"), f"Missing trailing newline in {path}"
