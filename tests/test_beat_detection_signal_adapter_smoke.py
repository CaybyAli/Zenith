from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from core.beat_detection_signal_adapter import (
    REQUIRED_SIGNAL_FIELDS,
    adapt_beat_detection_run_report_to_signals,
    adapt_beats_to_signals,
    beat_to_signal,
    extract_beat_dicts,
)
from models.beat_detection import BeatDetectionResult, BeatPoint
from models.beat_detection_run import BeatDetectionRunReport
from models.beat_detection_signal import BeatDetectionSignalAdapterResult


def _beat(
    time_seconds: float = 1.0,
    strength: float = 0.8,
    confidence: float = 0.7,
    is_downbeat_candidate: bool = False,
) -> dict:
    return {
        "time_seconds": time_seconds,
        "strength": strength,
        "confidence": confidence,
        "energy": 2.0,
        "is_downbeat_candidate": is_downbeat_candidate,
        "reason": "test_beat",
    }


def test_beat_detection_signal_adapter_result_roundtrip() -> None:
    result = BeatDetectionSignalAdapterResult(
        status="ok",
        signals=[
            {
                "signal_type": "beat_strong_sync_point",
                "signal_score": 0.9,
                "priority": "high",
            }
        ],
        signal_count=1,
        high_priority_signal_count=1,
        signal_types={"beat_strong_sync_point": 1},
        max_signal_score=0.9,
        avg_signal_score=0.9,
        beat_count=1,
        estimated_bpm=120.0,
        warnings=["demo_warning"],
        errors=[],
        recommendation="use_beat_edit_signals",
        metadata={"kind": "roundtrip"},
    )

    loaded = BeatDetectionSignalAdapterResult.from_dict(result.to_dict())

    assert loaded.status == "ok"
    assert loaded.signal_count == 1
    assert loaded.high_priority_signal_count == 1
    assert loaded.signal_types["beat_strong_sync_point"] == 1
    assert loaded.max_signal_score == 0.9
    assert loaded.avg_signal_score == 0.9
    assert loaded.beat_count == 1
    assert loaded.estimated_bpm == 120.0
    assert loaded.recommendation == "use_beat_edit_signals"
    assert loaded.metadata["kind"] == "roundtrip"


def test_extract_from_list_of_dict_beats() -> None:
    beats = [_beat(0.5), _beat(1.0)]

    extracted = extract_beat_dicts(beats)

    assert len(extracted) == 2
    assert extracted[0]["time_seconds"] == 0.5


def test_extract_from_beat_point_objects() -> None:
    beats = [
        BeatPoint(time_seconds=0.5, strength=0.8, confidence=0.7),
        BeatPoint(time_seconds=1.0, strength=0.6, confidence=0.6),
    ]

    extracted = extract_beat_dicts(beats)

    assert len(extracted) == 2
    assert extracted[0]["time_seconds"] == 0.5
    assert extracted[0]["strength"] == 0.8


def test_extract_from_beat_detection_run_report_object() -> None:
    report = BeatDetectionRunReport(
        status="ok",
        beats=[_beat(0.25), _beat(0.75)],
        beat_count=2,
        estimated_bpm=120.0,
    )

    extracted = extract_beat_dicts(report)

    assert len(extracted) == 2
    assert extracted[1]["time_seconds"] == 0.75


def test_extract_from_dict_with_beat_detection_result() -> None:
    source = {
        "beat_detection_result": {
            "beats": [_beat(0.5), _beat(1.5)],
        }
    }

    extracted = extract_beat_dicts(source)

    assert len(extracted) == 2
    assert extracted[0]["time_seconds"] == 0.5


def test_extract_from_job_like_object() -> None:
    job = SimpleNamespace(
        beat_detection_result=BeatDetectionResult(
            status="ok",
            beats=[
                BeatPoint(time_seconds=0.5, strength=0.9, confidence=0.8),
                BeatPoint(time_seconds=1.0, strength=0.7, confidence=0.6),
            ],
            beat_count=2,
        )
    )

    extracted = extract_beat_dicts(job)

    assert len(extracted) == 2
    assert extracted[0]["time_seconds"] == 0.5


def test_beat_to_signal_strong_beat() -> None:
    signal = beat_to_signal(
        _beat(time_seconds=1.0, strength=0.85, confidence=0.4),
        source_index=0,
        beat_count=1,
        estimated_bpm=120.0,
    )

    assert signal is not None
    assert signal["signal_type"] == "beat_strong_sync_point"
    assert signal["priority"] == "high"
    assert signal["signal_score"] == 0.85
    assert signal["center_seconds"] == 1.0
    assert signal["estimated_bpm"] == 120.0


def test_beat_to_signal_medium_beat() -> None:
    signal = beat_to_signal(
        _beat(time_seconds=1.0, strength=0.55, confidence=0.4),
        source_index=0,
        beat_count=1,
    )

    assert signal is not None
    assert signal["signal_type"] == "beat_sync_point"
    assert signal["priority"] == "medium"


def test_beat_to_signal_soft_beat() -> None:
    signal = beat_to_signal(
        _beat(time_seconds=1.0, strength=0.2, confidence=0.3),
        source_index=0,
        beat_count=1,
    )

    assert signal is not None
    assert signal["signal_type"] == "beat_soft_sync_point"
    assert signal["priority"] == "low"


def test_beat_to_signal_downbeat_candidate() -> None:
    signal = beat_to_signal(
        _beat(
            time_seconds=1.0,
            strength=0.4,
            confidence=0.4,
            is_downbeat_candidate=True,
        ),
        source_index=0,
        beat_count=1,
    )

    assert signal is not None
    assert signal["signal_type"] == "beat_downbeat_candidate"
    assert signal["priority"] == "high"
    assert signal["signal_score"] >= 0.9


def test_beat_to_signal_invalid_beat_safe() -> None:
    assert beat_to_signal({"strength": 0.9}) is None
    assert beat_to_signal({"time_seconds": "broken"}) is None
    assert beat_to_signal({"time_seconds": -1.0}) is None
    assert beat_to_signal(None) is None


def test_adapt_beats_to_signals_basic() -> None:
    result = adapt_beats_to_signals(
        [_beat(0.5, 0.9, 0.8), _beat(1.0, 0.6, 0.5)],
        estimated_bpm=120.0,
    )

    assert result.status == "ok"
    assert result.signal_count == 2
    assert result.beat_count == 2
    assert result.high_priority_signal_count == 1
    assert result.signal_types["beat_strong_sync_point"] == 1
    assert result.signal_types["beat_sync_point"] == 1
    assert result.recommendation == "use_beat_edit_signals"


def test_adapt_beats_to_signals_max_signals_keeps_strongest() -> None:
    beats = [
        _beat(0.5, 0.2, 0.2),
        _beat(1.0, 0.95, 0.9),
        _beat(1.5, 0.6, 0.6),
    ]

    result = adapt_beats_to_signals(beats, max_signals=2)

    assert result.signal_count == 2
    assert [signal["center_seconds"] for signal in result.signals] == [1.0, 1.5]
    assert result.max_signal_score == 0.95


def test_adapt_beat_detection_run_report_to_signals_basic() -> None:
    report = BeatDetectionRunReport(
        status="ok",
        selected_type="music_reference_audio",
        selected_path="music.wav",
        beats=[_beat(0.5, 0.9, 0.8), _beat(1.0, 0.6, 0.6)],
        beat_count=2,
        estimated_bpm=120.0,
    )

    result = adapt_beat_detection_run_report_to_signals(report)

    assert result.status == "ok"
    assert result.signal_count == 2
    assert result.beat_count == 2
    assert result.estimated_bpm == 120.0
    assert result.metadata["beat_detection_status"] == "ok"
    assert result.metadata["selected_type"] == "music_reference_audio"
    assert result.metadata["selected_path"] == "music.wav"


def test_no_beats_safe() -> None:
    result = adapt_beats_to_signals([])

    assert result.status == "skipped_no_beats"
    assert result.signal_count == 0
    assert result.recommendation == "no_beats_available"
    assert "no_beats_available" in result.warnings


def test_bad_data_safe() -> None:
    result = adapt_beats_to_signals([{"strength": 0.8}, {"time_seconds": "bad"}])

    assert result.status in {"skipped_no_beats", "completed_with_warnings"}
    assert result.signal_count == 0
    assert result.errors == []


def test_future_edit_compatible_output_required_fields() -> None:
    signal = beat_to_signal(
        _beat(time_seconds=2.0, strength=0.9, confidence=0.8),
        source_index=3,
        beat_count=10,
        estimated_bpm=128.0,
        metadata={"channel": "gaming_main"},
    )

    assert signal is not None

    for field in REQUIRED_SIGNAL_FIELDS:
        assert field in signal

    assert signal["source"] == "beat_detection_signal_adapter"
    assert signal["start_seconds"] >= 0.0
    assert signal["end_seconds"] > signal["start_seconds"]
    assert signal["beat_index"] == 3
    assert signal["beat_count"] == 10
    assert signal["source_beat"]["time_seconds"] == 2.0
    assert signal["metadata"]["channel"] == "gaming_main"


def test_beat_detection_signal_adapter_files_have_no_bom_and_end_with_newline() -> None:
    paths = [
        Path("models/beat_detection_signal.py"),
        Path("core/beat_detection_signal_adapter.py"),
        Path("tests/test_beat_detection_signal_adapter_smoke.py"),
    ]

    for path in paths:
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert data.endswith(b"\n"), f"{path} does not end with newline"
