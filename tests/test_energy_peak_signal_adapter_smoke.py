from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any

import pytest

from core.energy_peak_signal_adapter import (
    adapt_energy_peak_run_report_to_signals,
    adapt_energy_peaks_to_signals,
    energy_peak_to_signal,
    extract_peak_dicts,
)
from models.energy_peak import EnergyPeak, EnergyPeakDetectionResult
from models.energy_peak_run import EnergyPeakRunReport
from models.energy_peak_signal import EnergyPeakSignalAdapterResult

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)


def _make_peak_dict(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "peak_type": "combined",
        "start_seconds": 9.0,
        "end_seconds": 11.0,
        "center_seconds": 10.0,
        "energy_score": 0.85,
        "peak_score": 0.9,
        "confidence": 0.88,
        "reason": "combined_energy_peak",
        "source_index": 0,
        "rules_applied": [],
        "warnings": [],
        "errors": [],
        "metadata": {},
    }
    base.update(overrides)
    return base


def _make_energy_peak(**overrides: Any) -> EnergyPeak:
    defaults: dict[str, Any] = dict(
        start_seconds=9.0,
        end_seconds=11.0,
        center_seconds=10.0,
        energy_score=0.85,
        peak_score=0.9,
        peak_type="combined",
        confidence=0.88,
        reason="combined_energy_peak",
        source_index=0,
    )
    defaults.update(overrides)
    return EnergyPeak(**defaults)


# ---------------------------------------------------------------------------
# 1. Roundtrip
# ---------------------------------------------------------------------------

def test_energy_peak_signal_adapter_result_roundtrip():
    original = EnergyPeakSignalAdapterResult(
        status="ok",
        signals=[{"signal_type": "energy_peak", "signal_score": 0.9}],
        signal_count=1,
        peak_count=1,
        high_priority_signal_count=1,
        signal_types={"energy_peak": 1},
        max_signal_score=0.9,
        avg_signal_score=0.9,
        recommendation="use_edit_signals",
        metadata={"test": True},
    )
    d = original.to_dict()
    restored = EnergyPeakSignalAdapterResult.from_dict(d)

    assert restored.status == "ok"
    assert restored.signal_count == 1
    assert restored.peak_count == 1
    assert restored.max_signal_score == pytest.approx(0.9)
    assert restored.signal_types == {"energy_peak": 1}
    assert restored.recommendation == "use_edit_signals"
    assert restored.metadata == {"test": True}


# ---------------------------------------------------------------------------
# 2. extract_peak_dicts — list of dicts
# ---------------------------------------------------------------------------

def test_extract_peak_dicts_from_list_of_dicts():
    peaks = [_make_peak_dict(), _make_peak_dict(peak_type="high_energy")]
    result = extract_peak_dicts(peaks)
    assert len(result) == 2
    assert result[0]["peak_type"] == "combined"
    assert result[1]["peak_type"] == "high_energy"


# ---------------------------------------------------------------------------
# 3. extract_peak_dicts — list of EnergyPeak objects
# ---------------------------------------------------------------------------

def test_extract_peak_dicts_from_energy_peak_objects():
    peaks = [_make_energy_peak(), _make_energy_peak(peak_type="sudden_rise")]
    result = extract_peak_dicts(peaks)
    assert len(result) == 2
    assert result[0]["peak_type"] == "combined"
    assert result[1]["peak_type"] == "sudden_rise"
    assert "energy_score" in result[0]


# ---------------------------------------------------------------------------
# 4. extract_peak_dicts — dict with "peaks" key
# ---------------------------------------------------------------------------

def test_extract_peak_dicts_from_run_report_dict():
    d = {"status": "ok", "peaks": [_make_peak_dict(), _make_peak_dict(peak_type="local_maximum")]}
    result = extract_peak_dicts(d)
    assert len(result) == 2


# ---------------------------------------------------------------------------
# 5. extract_peak_dicts — job-like SimpleNamespace with energy_peaks
# ---------------------------------------------------------------------------

def test_extract_peak_dicts_from_job_like_object():
    job = SimpleNamespace(energy_peaks=[_make_peak_dict(), _make_peak_dict(peak_type="sudden_rise")])
    result = extract_peak_dicts(job)
    assert len(result) == 2


# ---------------------------------------------------------------------------
# 6. energy_peak_to_signal — combined peak
# ---------------------------------------------------------------------------

def test_energy_peak_to_signal_combined_peak():
    peak = _make_peak_dict(peak_type="combined", center_seconds=10.0, peak_score=0.9)
    sig = energy_peak_to_signal(peak)

    assert sig["signal_type"] == "combined_energy_peak"
    assert sig["priority"] == "high"
    assert sig["recommended_start_seconds"] == pytest.approx(9.25)
    assert sig["recommended_end_seconds"] == pytest.approx(10.75)
    assert sig["signal_score"] == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# 7. energy_peak_to_signal — high_energy
# ---------------------------------------------------------------------------

def test_energy_peak_to_signal_high_energy_peak():
    peak = _make_peak_dict(peak_type="high_energy")
    sig = energy_peak_to_signal(peak)
    assert sig["signal_type"] == "high_energy_peak"


# ---------------------------------------------------------------------------
# 8. energy_peak_to_signal — local_maximum
# ---------------------------------------------------------------------------

def test_energy_peak_to_signal_local_maximum_peak():
    peak = _make_peak_dict(peak_type="local_maximum")
    sig = energy_peak_to_signal(peak)
    assert sig["signal_type"] == "local_maximum_peak"


# ---------------------------------------------------------------------------
# 9. energy_peak_to_signal — sudden_rise
# ---------------------------------------------------------------------------

def test_energy_peak_to_signal_sudden_rise_peak():
    peak = _make_peak_dict(peak_type="sudden_rise")
    sig = energy_peak_to_signal(peak)
    assert sig["signal_type"] == "sudden_rise_peak"


# ---------------------------------------------------------------------------
# 10. energy_peak_to_signal — center fallback
# ---------------------------------------------------------------------------

def test_energy_peak_to_signal_center_fallback():
    peak = _make_peak_dict(start_seconds=4.0, end_seconds=6.0)
    del peak["center_seconds"]
    sig = energy_peak_to_signal(peak)
    assert sig["center_seconds"] == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# 11. adapt_energy_peaks_to_signals — basic
# ---------------------------------------------------------------------------

def test_adapt_energy_peaks_to_signals_basic():
    peaks = [
        _make_peak_dict(peak_type="combined", center_seconds=5.0, peak_score=0.9),
        _make_peak_dict(peak_type="high_energy", center_seconds=10.0, peak_score=0.7),
        _make_peak_dict(peak_type="local_maximum", center_seconds=15.0, peak_score=0.6),
    ]
    result = adapt_energy_peaks_to_signals(peaks)

    assert result.signal_count == 3
    assert "combined_energy_peak" in result.signal_types
    assert "high_energy_peak" in result.signal_types
    assert "local_maximum_peak" in result.signal_types
    assert result.max_signal_score == pytest.approx(0.9)


# ---------------------------------------------------------------------------
# 12. adapt_energy_peaks_to_signals — max_signals
# ---------------------------------------------------------------------------

def test_adapt_energy_peaks_to_signals_max_signals():
    peaks = [
        _make_peak_dict(peak_type="combined", center_seconds=5.0, peak_score=0.9),
        _make_peak_dict(peak_type="high_energy", center_seconds=10.0, peak_score=0.7),
        _make_peak_dict(peak_type="local_maximum", center_seconds=15.0, peak_score=0.5),
    ]
    result = adapt_energy_peaks_to_signals(peaks, max_signals=2)

    assert result.signal_count == 2
    scores = [s["signal_score"] for s in result.signals]
    assert 0.9 in scores
    assert 0.7 in scores
    # Chronological order preserved after filtering
    assert result.signals[0]["center_seconds"] <= result.signals[1]["center_seconds"]


# ---------------------------------------------------------------------------
# 13. adapt_energy_peaks_to_signals — no peaks
# ---------------------------------------------------------------------------

def test_adapt_energy_peaks_to_signals_no_peaks():
    result = adapt_energy_peaks_to_signals([])
    assert result.status == "skipped_no_peaks"
    assert result.recommendation == "no_energy_peaks_available"
    assert result.signal_count == 0


# ---------------------------------------------------------------------------
# 14. adapt_energy_peak_run_report_to_signals
# ---------------------------------------------------------------------------

def test_adapt_energy_peak_run_report_to_signals():
    peaks = [_make_peak_dict(), _make_peak_dict(peak_type="high_energy", center_seconds=20.0)]
    report = EnergyPeakRunReport(
        status="ok",
        peaks=[p for p in peaks],
        peak_count=2,
        recommendation="use_energy_peaks",
    )
    result = adapt_energy_peak_run_report_to_signals(report)

    assert result.signal_count > 0
    assert "energy_peak_status" in result.metadata
    assert "peak_count" in result.metadata


# ---------------------------------------------------------------------------
# 15. Bad peak data does not crash
# ---------------------------------------------------------------------------

def test_bad_peak_data_does_not_crash():
    bad_peaks: list[Any] = [
        {},
        {"center_seconds": "bad", "peak_score": "bad"},
        _make_peak_dict(peak_type="combined", center_seconds=8.0, peak_score=0.88),
    ]
    result = adapt_energy_peaks_to_signals(bad_peaks)

    assert result.status in {"ok", "completed_with_warnings"}
    assert result.signal_count >= 1
    good_signals = [s for s in result.signals if s.get("signal_type") == "combined_energy_peak"]
    assert len(good_signals) >= 1


# ---------------------------------------------------------------------------
# 16. Signal output satisfies future edit-logic contract
# ---------------------------------------------------------------------------

def test_signal_output_can_feed_future_edit_logic_contract():
    peak = _make_peak_dict()
    sig = energy_peak_to_signal(peak)

    required_keys = {
        "signal_type",
        "start_seconds",
        "end_seconds",
        "center_seconds",
        "signal_score",
        "priority",
        "reason",
        "source_peak",
    }
    missing = required_keys - sig.keys()
    assert not missing, f"Missing keys in signal: {missing}"

    assert isinstance(sig["signal_type"], str)
    assert isinstance(sig["start_seconds"], float)
    assert isinstance(sig["end_seconds"], float)
    assert isinstance(sig["center_seconds"], float)
    assert isinstance(sig["signal_score"], float)
    assert sig["priority"] in {"high", "medium", "low"}
    assert isinstance(sig["reason"], str)
    assert isinstance(sig["source_peak"], dict)


# ---------------------------------------------------------------------------
# 17. BOM and trailing newline hygiene
# ---------------------------------------------------------------------------

def test_peak_signal_adapter_files_have_no_bom_and_end_with_newline():
    files = [
        os.path.join(_REPO_ROOT, "models", "energy_peak_signal.py"),
        os.path.join(_REPO_ROOT, "core", "energy_peak_signal_adapter.py"),
        os.path.join(_REPO_ROOT, "tests", "test_energy_peak_signal_adapter_smoke.py"),
    ]
    for path in files:
        with open(path, "rb") as f:
            raw = f.read()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {path}"
        assert raw.endswith(b"\n"), f"No trailing newline in {path}"
