from __future__ import annotations

import inspect

from core.energy_curve_builder import EnergyCurveBuilder
from models.edit_signal import EditSignal


JOB_ID = "job_energy_curve_required_smoke"


def _make_signal(
    *,
    signal_id: str,
    signal_type: str,
    start_time: float,
    end_time: float,
    strength: float,
    confidence: float,
) -> EditSignal:
    signature = inspect.signature(EditSignal)

    values = {
        "signal_id": signal_id,
        "job_id": JOB_ID,
        "signal_type": signal_type,
        "source": "energy_curve_required_smoke",
        "start_time": start_time,
        "end_time": end_time,
        "strength": strength,
        "confidence": confidence,
        "reason": "required energy curve smoke test",
        "notes": ["energy_curve_required_smoke"],
        "metadata": {"test": "test_energy_curve_smoke"},
    }

    kwargs = {}
    for name, parameter in signature.parameters.items():
        if name == "self":
            continue

        if name in values:
            kwargs[name] = values[name]
        elif parameter.default is inspect.Parameter.empty:
            kwargs[name] = "energy_curve_required_smoke"

    return EditSignal(**kwargs)


def test_energy_curve_smoke() -> None:
    signals = [
        _make_signal(
            signal_id="required_audio_peak",
            signal_type="audio_peak",
            start_time=2.0,
            end_time=7.0,
            strength=0.95,
            confidence=0.95,
        ),
        _make_signal(
            signal_id="required_motion_peak",
            signal_type="motion_peak",
            start_time=3.0,
            end_time=8.0,
            strength=0.95,
            confidence=0.95,
        ),
        _make_signal(
            signal_id="required_hook",
            signal_type="hook",
            start_time=4.0,
            end_time=9.0,
            strength=0.90,
            confidence=0.95,
        ),
        _make_signal(
            signal_id="required_highlight",
            signal_type="highlight",
            start_time=5.0,
            end_time=10.0,
            strength=0.95,
            confidence=0.95,
        ),
        _make_signal(
            signal_id="required_silence",
            signal_type="silence_zone",
            start_time=15.0,
            end_time=20.0,
            strength=1.0,
            confidence=0.95,
        ),
        _make_signal(
            signal_id="required_low_motion",
            signal_type="low_motion_zone",
            start_time=20.0,
            end_time=25.0,
            strength=0.95,
            confidence=0.90,
        ),
        _make_signal(
            signal_id="required_duration_context",
            signal_type="duration_context",
            start_time=0.0,
            end_time=30.0,
            strength=1.0,
            confidence=1.0,
        ),
    ]

    result = EnergyCurveBuilder().build(
        job_id=JOB_ID,
        edit_signals=signals,
        duration_seconds=30.0,
        window_seconds=5.0,
        max_peaks=3,
    )

    assert result.job_id == JOB_ID
    assert result.engine == "energy-curve-builder-v1"
    assert len(result.points) == 6
    assert len(result.peak_points) >= 1
    assert result.average_energy > 0.0
    assert result.max_energy >= 0.60

    source_ids = {
        source_signal_id
        for point in result.points
        for source_signal_id in point.source_signal_ids
    }

    assert "required_audio_peak" in source_ids
    assert "required_motion_peak" in source_ids
    assert "required_hook" in source_ids
    assert "required_highlight" in source_ids
    assert "required_silence" in source_ids
    assert "required_low_motion" in source_ids
    assert "required_duration_context" not in source_ids

    assert any("high_energy_window" in point.notes for point in result.points)

    print("ENERGY CURVE SMOKE TEST PASSED")
    print(f"points={len(result.points)}")
    print(f"peaks={len(result.peak_points)}")
    print(f"average_energy={result.average_energy}")
    print(f"max_energy={result.max_energy}")
    print(f"engine={result.engine}")


if __name__ == "__main__":
    test_energy_curve_smoke()
