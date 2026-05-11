from __future__ import annotations

import os
from typing import Any

import pytest

from models.energy_peak import EnergyPeak, EnergyPeakDetectionResult
from core.energy_peak_detector import (
    detect_energy_peaks,
    detect_energy_peak_at_index,
    extract_energy_items,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_items(energy_values: list[float]) -> list[dict[str, Any]]:
    items = []
    for i, e in enumerate(energy_values):
        t = i * 1.0
        items.append({
            "time_seconds": t,
            "start_seconds": t,
            "end_seconds": t + 1.0,
            "energy_score": e,
            "source_index": i,
            "is_silent": False,
            "source_item": {},
        })
    return items


def _make_timeline(energy_values: list[float]) -> list[dict[str, Any]]:
    result = []
    for i, e in enumerate(energy_values):
        t = i * 1.0
        result.append({
            "time_seconds": t,
            "start_seconds": t,
            "end_seconds": t + 1.0,
            "energy_score": e,
            "is_silent": False,
        })
    return result


# ---------------------------------------------------------------------------
# 1. EnergyPeak roundtrip
# ---------------------------------------------------------------------------

def test_energy_peak_roundtrip():
    peak = EnergyPeak(
        start_seconds=1.0,
        end_seconds=2.0,
        center_seconds=1.5,
        energy_score=0.9,
        peak_score=0.85,
        peak_type="combined",
        confidence=0.90,
        reason="combined_energy_peak",
        source_index=3,
        is_local_maximum=True,
        rise_delta=0.3,
        fall_delta=0.2,
        window_energy_before=0.6,
        window_energy_after=0.5,
        source_item={"orig": True},
        rules_applied=["threshold_peak", "local_maximum"],
        warnings=["w1"],
        errors=[],
        metadata={"extra": 42},
    )
    d = peak.to_dict()
    restored = EnergyPeak.from_dict(d)

    assert restored.start_seconds == 1.0
    assert restored.end_seconds == 2.0
    assert restored.center_seconds == 1.5
    assert restored.energy_score == 0.9
    assert restored.peak_score == 0.85
    assert restored.peak_type == "combined"
    assert restored.confidence == 0.90
    assert restored.reason == "combined_energy_peak"
    assert restored.source_index == 3
    assert restored.is_local_maximum is True
    assert restored.rise_delta == 0.3
    assert restored.fall_delta == 0.2
    assert restored.window_energy_before == 0.6
    assert restored.window_energy_after == 0.5
    assert restored.rules_applied == ["threshold_peak", "local_maximum"]
    assert restored.warnings == ["w1"]
    assert restored.metadata["extra"] == 42


# ---------------------------------------------------------------------------
# 2. EnergyPeakDetectionResult roundtrip
# ---------------------------------------------------------------------------

def test_energy_peak_detection_result_roundtrip():
    peak = EnergyPeak(
        start_seconds=0.5,
        end_seconds=1.5,
        center_seconds=1.0,
        energy_score=0.88,
        peak_score=0.80,
        peak_type="high_energy",
        confidence=0.80,
        reason="energy_above_peak_threshold",
    )
    result = EnergyPeakDetectionResult(
        status="ok",
        peaks=[peak],
        peak_count=1,
        high_energy_peak_count=1,
        local_max_peak_count=0,
        rise_peak_count=0,
        threshold_peak_count=1,
        peak_threshold=0.85,
        min_peak_distance_seconds=0.4,
        warnings=[],
        errors=[],
        metadata={"top_peak_score": 0.80},
    )
    d = result.to_dict()
    restored = EnergyPeakDetectionResult.from_dict(d)

    assert restored.status == "ok"
    assert restored.peak_count == 1
    assert len(restored.peaks) == 1
    assert restored.peaks[0].peak_type == "high_energy"
    assert restored.high_energy_peak_count == 1
    assert restored.peak_threshold == 0.85
    assert restored.metadata["top_peak_score"] == 0.80


# ---------------------------------------------------------------------------
# 3. extract_energy_items from context timeline (list[dict] with time_seconds)
# ---------------------------------------------------------------------------

def test_extract_energy_items_from_context_timeline():
    timeline = [
        {"time_seconds": 1.0, "start_seconds": 1.0, "end_seconds": 2.0, "energy_score": 0.5},
        {"time_seconds": 2.0, "start_seconds": 2.0, "end_seconds": 3.0, "energy_score": 0.9},
    ]
    items = extract_energy_items(timeline)
    assert len(items) == 2
    assert items[0]["time_seconds"] == 1.0
    assert items[0]["energy_score"] == 0.5
    assert items[1]["energy_score"] == 0.9


# ---------------------------------------------------------------------------
# 4. extract_energy_items from rms points dict (normalized_energy)
# ---------------------------------------------------------------------------

def test_extract_energy_items_from_rms_points_dict():
    data = {
        "points": [
            {
                "center_seconds": 0.5,
                "start_seconds": 0.0,
                "end_seconds": 1.0,
                "normalized_energy": 0.7,
                "rms": 0.3,
                "is_silent": False,
            },
        ]
    }
    items = extract_energy_items(data)
    assert len(items) == 1
    assert items[0]["energy_score"] == 0.7
    assert items[0]["time_seconds"] == 0.5


# ---------------------------------------------------------------------------
# 5. High energy threshold peak detected
# ---------------------------------------------------------------------------

def test_detect_high_energy_threshold_peak():
    timeline = _make_timeline([0.2, 0.4, 0.9, 0.3])
    result = detect_energy_peaks(timeline, peak_threshold=0.85)

    assert result.peak_count >= 1
    peak_energies = [p.energy_score for p in result.peaks]
    assert 0.9 in peak_energies

    matching = [p for p in result.peaks if p.energy_score == 0.9]
    assert len(matching) >= 1
    assert matching[0].peak_type in ("high_energy", "combined")
    assert "threshold_peak" in matching[0].rules_applied


# ---------------------------------------------------------------------------
# 6. Local maximum peak detected
# ---------------------------------------------------------------------------

def test_detect_local_maximum_peak():
    timeline = _make_timeline([0.2, 0.7, 0.3])
    result = detect_energy_peaks(timeline, peak_threshold=0.85)

    assert result.peak_count >= 1
    local_peaks = [p for p in result.peaks if "local_maximum" in p.rules_applied]
    assert len(local_peaks) >= 1
    assert local_peaks[0].energy_score == 0.7


# ---------------------------------------------------------------------------
# 7. Sudden rise peak detected
# ---------------------------------------------------------------------------

def test_detect_sudden_rise_peak():
    timeline = _make_timeline([0.1, 0.2, 0.55])
    result = detect_energy_peaks(
        timeline,
        peak_threshold=0.85,
        rise_threshold=0.25,
    )

    assert result.peak_count >= 1
    rise_peaks = [p for p in result.peaks if "sudden_rise" in p.rules_applied]
    assert len(rise_peaks) >= 1
    assert rise_peaks[0].energy_score == 0.55


# ---------------------------------------------------------------------------
# 8. Combined peak when multiple rules match
# ---------------------------------------------------------------------------

def test_combined_peak_when_multiple_rules_match():
    timeline = _make_timeline([0.2, 0.95, 0.3])
    result = detect_energy_peaks(timeline, peak_threshold=0.85)

    assert result.peak_count >= 1
    combined = [p for p in result.peaks if p.energy_score == 0.95]
    assert len(combined) >= 1
    assert combined[0].peak_type == "combined"
    assert "threshold_peak" in combined[0].rules_applied
    assert "local_maximum" in combined[0].rules_applied


# ---------------------------------------------------------------------------
# 9. Flat low energy produces no peak
# ---------------------------------------------------------------------------

def test_no_peak_for_flat_low_energy():
    timeline = _make_timeline([0.2, 0.21, 0.2])
    result = detect_energy_peaks(timeline, peak_threshold=0.85)

    assert result.peak_count == 0


# ---------------------------------------------------------------------------
# 10. min_peak_distance deduplicates close peaks
# ---------------------------------------------------------------------------

def test_min_peak_distance_deduplicates_close_peaks():
    timeline = [
        {"time_seconds": 1.0, "start_seconds": 1.0, "end_seconds": 1.1, "energy_score": 0.9, "is_silent": False},
        {"time_seconds": 1.1, "start_seconds": 1.1, "end_seconds": 1.2, "energy_score": 0.95, "is_silent": False},
        {"time_seconds": 2.0, "start_seconds": 2.0, "end_seconds": 2.1, "energy_score": 0.9, "is_silent": False},
    ]
    result = detect_energy_peaks(
        timeline,
        peak_threshold=0.85,
        min_peak_distance_seconds=0.4,
    )

    assert result.peak_count == 2
    peak_times = [p.center_seconds for p in result.peaks]
    assert 2.0 in peak_times
    # The cluster at 1.0/1.1 should keep only the stronger one (0.95)
    cluster = [p for p in result.peaks if p.center_seconds < 1.5]
    assert len(cluster) == 1
    assert cluster[0].energy_score == 0.95


# ---------------------------------------------------------------------------
# 11. max_peaks limits by score
# ---------------------------------------------------------------------------

def test_max_peaks_limits_by_score():
    timeline = _make_timeline([0.2, 0.9, 0.3, 0.95, 0.2, 0.88])
    result = detect_energy_peaks(
        timeline,
        peak_threshold=0.85,
        min_peak_distance_seconds=0.1,
        max_peaks=2,
    )

    assert result.peak_count == 2
    # Sorted chronologically after selection
    assert result.peaks[0].center_seconds <= result.peaks[1].center_seconds


# ---------------------------------------------------------------------------
# 12. Silent low energy item is not a peak
# ---------------------------------------------------------------------------

def test_silent_low_energy_is_not_peak():
    timeline = [
        {
            "time_seconds": 1.0,
            "start_seconds": 1.0,
            "end_seconds": 2.0,
            "energy_score": 0.4,
            "is_silent": True,
        }
    ]
    result = detect_energy_peaks(timeline, peak_threshold=0.85)
    assert result.peak_count == 0


# ---------------------------------------------------------------------------
# 13. Empty timeline is safe
# ---------------------------------------------------------------------------

def test_empty_timeline_safe():
    result = detect_energy_peaks([])
    assert result.status == "completed_with_warnings"
    assert "no_energy_items" in result.warnings
    assert result.peak_count == 0


# ---------------------------------------------------------------------------
# 14. Bad items do not crash
# ---------------------------------------------------------------------------

def test_bad_items_do_not_crash():
    timeline = [
        {},
        {"time_seconds": "bad", "energy_score": "bad"},
        {"time_seconds": 5.0, "start_seconds": 5.0, "end_seconds": 6.0, "energy_score": 0.9, "is_silent": False},
    ]
    result = detect_energy_peaks(timeline, peak_threshold=0.85)
    # Should not crash
    assert isinstance(result, EnergyPeakDetectionResult)
    # The valid high-energy item should be detected or at least not crash
    assert result.peak_count >= 0


# ---------------------------------------------------------------------------
# 15. Works with RMS Context Adapter output
# ---------------------------------------------------------------------------

def test_peak_detector_works_with_rms_context_adapter_output():
    from models.rms_energy import RmsEnergyPoint, RmsEnergyTimelineResult
    from core.rms_energy_context_adapter import adapt_rms_energy_timeline_to_context

    points = [
        RmsEnergyPoint(
            start_seconds=0.0,
            end_seconds=0.5,
            center_seconds=0.25,
            rms=0.1,
            normalized_energy=0.2,
            is_silent=False,
        ),
        RmsEnergyPoint(
            start_seconds=0.5,
            end_seconds=1.0,
            center_seconds=0.75,
            rms=0.8,
            normalized_energy=0.9,
            is_silent=False,
        ),
        RmsEnergyPoint(
            start_seconds=1.0,
            end_seconds=1.5,
            center_seconds=1.25,
            rms=0.1,
            normalized_energy=0.2,
            is_silent=False,
        ),
    ]
    timeline_result = RmsEnergyTimelineResult(
        status="ok",
        points=points,
        point_count=len(points),
    )

    adapter_result = adapt_rms_energy_timeline_to_context(timeline_result, peak_threshold=0.85)
    assert adapter_result.status == "ok"

    result = detect_energy_peaks(adapter_result, peak_threshold=0.85)
    assert result.peak_count >= 1
    peak_energies = [p.energy_score for p in result.peaks]
    assert any(e >= 0.85 for e in peak_energies)


# ---------------------------------------------------------------------------
# 16. Energy peak output feeds silence context builder
# ---------------------------------------------------------------------------

def test_energy_peak_can_feed_silence_context_builder():
    from core.silence_context_builder import build_silence_segment_context

    energy_timeline = [
        {
            "time_seconds": 0.5,
            "start_seconds": 0.0,
            "end_seconds": 1.0,
            "energy_score": 0.9,
            "is_peak": True,
            "is_silent": False,
        }
    ]

    silence_segment = {
        "start_seconds": 1.5,
        "end_seconds": 2.0,
        "duration_seconds": 0.5,
    }

    ctx = build_silence_segment_context(
        segment=silence_segment,
        energy_timeline=energy_timeline,
        context_window_seconds=1.0,
    )

    assert ctx.previous_energy_score is not None
    assert ctx.previous_energy_score >= 0.75
    assert ctx.is_after_high_energy is True


# ---------------------------------------------------------------------------
# 17. BOM and trailing newline hygiene
# ---------------------------------------------------------------------------

def test_energy_peak_detector_files_have_no_bom_and_end_with_newline():
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    files = [
        os.path.join(repo_root, "models", "energy_peak.py"),
        os.path.join(repo_root, "core", "energy_peak_detector.py"),
        os.path.join(repo_root, "tests", "test_energy_peak_detector_foundation_smoke.py"),
    ]
    for path in files:
        with open(path, "rb") as f:
            raw = f.read()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {path}"
        assert raw.endswith(b"\n"), f"No trailing newline in {path}"
