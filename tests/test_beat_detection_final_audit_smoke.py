from __future__ import annotations

import json
import struct
import wave
from pathlib import Path
from types import SimpleNamespace

import core.beat_detection_runner as runner_module
from core.beat_detection_runner import (
    build_beat_detection_run_report,
    run_beat_detection_for_job,
)
from core.beat_detection_signal_adapter import (
    REQUIRED_SIGNAL_FIELDS,
    adapt_beat_detection_run_report_to_signals,
    adapt_beats_to_signals,
    beat_to_signal,
    extract_beat_dicts,
)
from core.beat_detection_source_selector import (
    select_beat_detection_source,
    select_beat_detection_source_for_job,
)
from core.beat_detector import (
    analyze_wav_beats,
    build_energy_envelope,
    calculate_frame_energy,
    detect_beat_candidates,
    detect_beats_from_samples,
    estimate_bpm_from_beats,
    filter_beats_by_min_distance,
)
from models.beat_detection import BeatDetectionResult, BeatPoint
from models.beat_detection_run import BeatDetectionRunReport
from models.beat_detection_signal import BeatDetectionSignalAdapterResult
from models.beat_detection_source import BeatDetectionSourceSelection
from models.job import Job


def _pulse_samples(
    sample_rate: int = 1000,
    duration_seconds: float = 2.0,
    pulse_times: list[float] | None = None,
    pulse_width_samples: int = 8,
) -> list[float]:
    pulse_times = pulse_times or [0.25, 0.75, 1.25, 1.75]
    sample_count = int(sample_rate * duration_seconds)
    samples = [0.02 for _ in range(sample_count)]

    for pulse_time in pulse_times:
        start = int(pulse_time * sample_rate)
        for offset in range(pulse_width_samples):
            index = start + offset
            if 0 <= index < len(samples):
                samples[index] = 1.0

    return samples


def _flat_samples(sample_rate: int = 1000, duration_seconds: float = 2.0) -> list[float]:
    return [0.1 for _ in range(int(sample_rate * duration_seconds))]


def _write_wav_16bit(
    path: Path,
    samples: list[float],
    sample_rate: int = 1000,
    channels: int = 1,
) -> Path:
    with wave.open(str(path), "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        frames = bytearray()
        for sample in samples:
            value = int(max(-1.0, min(1.0, sample)) * 32767)
            for _ in range(channels):
                frames.extend(struct.pack("<h", value))

        wav_file.writeframes(bytes(frames))

    return path


def _touch(path: Path) -> Path:
    path.write_bytes(b"tiny")
    return path


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
        "reason": "audit_beat",
    }


def _job_payload() -> dict:
    return {
        "job_id": "job_beat_final_audit",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "longform",
        "target_platforms": ["youtube"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
        "pipeline_type": "gaming_pipeline",
        "raw_video_path": "input/demo.mp4",
    }


def _pipeline_source() -> str:
    return Path("core/gaming_pipeline.py").read_text(encoding="utf-8")


def _beat_detection_pipeline_block() -> str:
    source = _pipeline_source()
    start = source.index('phase="beat_detection"')
    end = source.index('event_type="STATE_ANALYZING"', start)
    return source[start:end]


def test_2b12_models_roundtrip() -> None:
    beat = BeatPoint(
        time_seconds=1.25,
        strength=0.9,
        confidence=0.8,
        energy=2.0,
        local_energy=2.0,
        average_energy=0.5,
        source_index=3,
        is_downbeat_candidate=True,
        bpm_context=120.0,
        reason="audit",
        warnings=["w"],
        errors=[],
        metadata={"k": "v"},
    )
    beat_loaded = BeatPoint.from_dict(beat.to_dict())
    assert beat_loaded.time_seconds == 1.25
    assert beat_loaded.is_downbeat_candidate is True
    assert beat_loaded.metadata["k"] == "v"

    detection = BeatDetectionResult(
        status="ok",
        input_path="music.wav",
        beats=[beat],
        beat_count=1,
        estimated_bpm=120.0,
        average_beat_interval_seconds=0.5,
        duration_seconds=2.0,
        sample_rate=1000,
        channels=1,
        energy_frame_count=20,
        warnings=["demo"],
        errors=[],
    )
    detection_loaded = BeatDetectionResult.from_dict(detection.to_dict())
    assert detection_loaded.status == "ok"
    assert detection_loaded.beat_count == 1
    assert detection_loaded.beats[0].time_seconds == 1.25

    selection = BeatDetectionSourceSelection(
        status="selected",
        selected_path="music.wav",
        selected_type="music_reference_audio",
        source_priority=["music_reference_audio", "analysis_audio", "original_wav"],
        checked_sources=[{"type": "music_reference_audio", "usable": True}],
        recommendation="analyze_selected_wav",
        metadata={"audit": True},
    )
    selection_loaded = BeatDetectionSourceSelection.from_dict(selection.to_dict())
    assert selection_loaded.status == "selected"
    assert selection_loaded.selected_type == "music_reference_audio"

    run_report = BeatDetectionRunReport(
        status="ok",
        source_selection=selection.to_dict(),
        selected_path="music.wav",
        selected_type="music_reference_audio",
        beat_detection_result=detection.to_dict(),
        beats=[beat.to_dict()],
        beat_count=1,
        estimated_bpm=120.0,
        recommendation="use_beat_timeline",
    )
    run_loaded = BeatDetectionRunReport.from_dict(run_report.to_dict())
    assert run_loaded.status == "ok"
    assert run_loaded.beat_count == 1
    assert run_loaded.selected_type == "music_reference_audio"

    signal_result = BeatDetectionSignalAdapterResult(
        status="ok",
        signals=[{"signal_type": "beat_strong_sync_point", "signal_score": 0.9}],
        signal_count=1,
        high_priority_signal_count=1,
        signal_types={"beat_strong_sync_point": 1},
        max_signal_score=0.9,
        avg_signal_score=0.9,
        beat_count=1,
        estimated_bpm=120.0,
        recommendation="use_beat_edit_signals",
    )
    signal_loaded = BeatDetectionSignalAdapterResult.from_dict(signal_result.to_dict())
    assert signal_loaded.status == "ok"
    assert signal_loaded.signal_count == 1
    assert signal_loaded.signal_types["beat_strong_sync_point"] == 1


def test_2b12_detector_contract() -> None:
    assert calculate_frame_energy([1, -1, 1, -1]) == 1.0
    assert calculate_frame_energy([]) == 0.0

    envelope = build_energy_envelope(_pulse_samples(), sample_rate=1000)
    assert len(envelope) > 1
    assert build_energy_envelope([0.2], sample_rate=1000)

    manual_envelope = [
        {"index": 0, "center_seconds": 0.0, "start_seconds": 0.0, "end_seconds": 0.1, "energy": 0.1},
        {"index": 1, "center_seconds": 0.5, "start_seconds": 0.4, "end_seconds": 0.6, "energy": 5.0},
        {"index": 2, "center_seconds": 1.0, "start_seconds": 0.9, "end_seconds": 1.1, "energy": 0.1},
    ]
    candidates = detect_beat_candidates(manual_envelope, peak_threshold=1.35)
    assert len(candidates) == 1
    assert candidates[0].time_seconds == 0.5

    flat_envelope = [
        {"index": index, "center_seconds": index * 0.5, "start_seconds": 0.0, "end_seconds": 0.1, "energy": 1.0}
        for index in range(6)
    ]
    assert detect_beat_candidates(flat_envelope, peak_threshold=1.35) == []

    close_beats = [
        BeatPoint(time_seconds=1.00, strength=0.4),
        BeatPoint(time_seconds=1.10, strength=0.9),
        BeatPoint(time_seconds=2.00, strength=0.6),
    ]
    filtered = filter_beats_by_min_distance(close_beats, min_beat_distance_seconds=0.25)
    assert len(filtered) == 2
    assert filtered[0].time_seconds == 1.10

    regular_beats = [
        BeatPoint(time_seconds=0.0),
        BeatPoint(time_seconds=0.5),
        BeatPoint(time_seconds=1.0),
    ]
    assert estimate_bpm_from_beats(regular_beats) == 120.0
    assert estimate_bpm_from_beats([BeatPoint(time_seconds=0.0)]) is None

    pulse_result = detect_beats_from_samples(_pulse_samples(), sample_rate=1000)
    assert pulse_result.status in {"ok", "completed_with_warnings"}
    assert pulse_result.beat_count >= 3

    empty_result = detect_beats_from_samples([], sample_rate=1000)
    assert empty_result.status in {"completed_with_warnings", "failed"}
    assert empty_result.beat_count == 0

    silent_result = detect_beats_from_samples([0.0] * 1000, sample_rate=1000)
    assert silent_result.status in {"completed_with_warnings", "ok"}
    assert silent_result.beat_count == 0


def test_2b12_wav_analyzer_contract(tmp_path: Path) -> None:
    mono_wav = _write_wav_16bit(tmp_path / "mono.wav", _pulse_samples(), channels=1)
    stereo_wav = _write_wav_16bit(tmp_path / "stereo.wav", _pulse_samples(), channels=2)
    flat_wav = _write_wav_16bit(tmp_path / "flat.wav", _flat_samples(), channels=1)

    mono_result = analyze_wav_beats(mono_wav)
    stereo_result = analyze_wav_beats(stereo_wav)
    flat_result = analyze_wav_beats(flat_wav)

    assert mono_result.status in {"ok", "completed_with_warnings"}
    assert mono_result.channels == 1
    assert mono_result.beat_count >= 3

    assert stereo_result.status in {"ok", "completed_with_warnings"}
    assert stereo_result.channels == 2
    assert stereo_result.beat_count >= 3

    assert flat_result.status in {"ok", "completed_with_warnings"}
    assert flat_result.beat_count == 0

    missing_result = analyze_wav_beats(tmp_path / "missing.wav")
    assert missing_result.status == "failed"
    assert "wav_file_missing" in missing_result.errors

    bad_wav = tmp_path / "bad.wav"
    bad_wav.write_text("not wav", encoding="utf-8")
    bad_result = analyze_wav_beats(bad_wav)
    assert bad_result.status == "failed"
    assert "wav_read_failed" in bad_result.errors


def test_2b12_source_selector_contract(tmp_path: Path) -> None:
    music_wav = _write_wav_16bit(tmp_path / "music.wav", _pulse_samples())
    analysis_wav = _write_wav_16bit(tmp_path / "analysis.wav", _pulse_samples())
    original_wav = _write_wav_16bit(tmp_path / "original.wav", _pulse_samples())
    original_mp4 = _touch(tmp_path / "clip.mp4")
    non_wav_music = _touch(tmp_path / "music.mp3")

    selected = select_beat_detection_source(
        preprocessing_manifest={
            "music_reference_audio_path": str(music_wav),
            "analysis_audio_path": str(analysis_wav),
        }
    )
    assert selected.status == "selected"
    assert selected.selected_type == "music_reference_audio"
    assert selected.checked_sources

    fallback = select_beat_detection_source(
        preprocessing_manifest={"analysis_audio_path": str(analysis_wav)}
    )
    assert fallback.status == "selected_fallback"
    assert fallback.selected_type == "analysis_audio"
    assert "analysis_audio_used_for_beat_detection" in fallback.warnings

    missing = select_beat_detection_source(
        preprocessing_manifest={
            "music_reference_audio_path": str(tmp_path / "missing_music.wav"),
            "analysis_audio_path": str(analysis_wav),
        }
    )
    assert missing.status == "missing_preprocessed_audio"
    assert missing.selected_type == "planned_music_reference_audio"
    assert missing.recommendation == "generate_preprocessed_audio"

    original = select_beat_detection_source(original_source_path=str(original_wav))
    assert original.status == "selected_fallback"
    assert original.selected_type == "original_wav"

    unsupported = select_beat_detection_source(original_source_path=str(original_mp4))
    assert unsupported.status == "skipped_unsupported_source"
    assert unsupported.selected_type == "unsupported_original_source"
    assert unsupported.recommendation == "extract_audio_first"

    non_wav_skip = select_beat_detection_source(
        preprocessing_manifest={
            "music_reference_audio_path": str(non_wav_music),
            "analysis_audio_path": str(analysis_wav),
        }
    )
    assert non_wav_skip.selected_type == "analysis_audio"

    empty_job_selection = select_beat_detection_source_for_job(SimpleNamespace())
    assert empty_job_selection.status == "unavailable"
    assert empty_job_selection.selected_type == "none"
    assert empty_job_selection.checked_sources


def test_2b12_runner_contract(tmp_path: Path, monkeypatch) -> None:
    music_wav = _write_wav_16bit(tmp_path / "music.wav", _pulse_samples())
    analysis_wav = _write_wav_16bit(tmp_path / "analysis.wav", _pulse_samples())
    original_wav = _write_wav_16bit(tmp_path / "original.wav", _pulse_samples())
    original_mp4 = _touch(tmp_path / "clip.mp4")

    music_report = build_beat_detection_run_report(
        preprocessing_manifest={"music_reference_audio_path": str(music_wav)}
    )
    assert music_report.status in {"ok", "completed_with_warnings"}
    assert music_report.selected_type == "music_reference_audio"
    assert music_report.beat_count >= 3

    analysis_report = build_beat_detection_run_report(
        preprocessing_manifest={"analysis_audio_path": str(analysis_wav)}
    )
    assert analysis_report.status in {"ok", "completed_with_warnings"}
    assert analysis_report.selected_type == "analysis_audio"

    missing_report = build_beat_detection_run_report(
        preprocessing_manifest={"music_reference_audio_path": str(tmp_path / "missing.wav")}
    )
    assert missing_report.status == "blocked_missing_preprocessed_audio"
    assert missing_report.recommendation == "generate_preprocessed_audio"

    mp4_report = build_beat_detection_run_report(original_source_path=str(original_mp4))
    assert mp4_report.status == "skipped_unsupported_source"
    assert mp4_report.recommendation == "extract_audio_first"

    original_report = build_beat_detection_run_report(original_source_path=str(original_wav))
    assert original_report.status in {"ok", "completed_with_warnings"}
    assert original_report.selected_type == "original_wav"

    bad_wav = tmp_path / "bad.wav"
    bad_wav.write_text("bad wav", encoding="utf-8")
    bad_report = build_beat_detection_run_report(
        preprocessing_manifest={"music_reference_audio_path": str(bad_wav)}
    )
    assert bad_report.status == "failed"
    assert "wav_read_failed" in bad_report.errors

    flat_wav = _write_wav_16bit(tmp_path / "flat.wav", _flat_samples())
    flat_report = build_beat_detection_run_report(
        preprocessing_manifest={"music_reference_audio_path": str(flat_wav)}
    )
    assert flat_report.beat_count == 0
    assert flat_report.recommendation == "no_beats_detected"

    empty_job_report = run_beat_detection_for_job(SimpleNamespace())
    assert empty_job_report.status == "skipped_no_audio_source"

    provided_selection = BeatDetectionSourceSelection(
        status="selected",
        selected_path=str(music_wav),
        selected_type="music_reference_audio",
        recommendation="analyze_selected_wav",
    )
    provided_report = build_beat_detection_run_report(source_selection=provided_selection)
    assert provided_report.selected_type == "music_reference_audio"
    assert provided_report.beat_count >= 3

    calls = {"count": 0}

    def fake_analyze_wav_beats(*args, **kwargs):
        calls["count"] += 1
        return BeatDetectionResult(status="ok", beats=[BeatPoint(time_seconds=0.5, strength=0.9)], beat_count=1)

    monkeypatch.setattr(runner_module, "analyze_wav_beats", fake_analyze_wav_beats)
    build_beat_detection_run_report(original_source_path=str(original_mp4))
    assert calls["count"] == 0

    build_beat_detection_run_report(
        preprocessing_manifest={"music_reference_audio_path": str(music_wav)}
    )
    assert calls["count"] == 1


def test_2b12_signal_adapter_contract() -> None:
    strong = beat_to_signal(_beat(1.0, 0.9, 0.7), source_index=0, beat_count=4, estimated_bpm=120.0)
    medium = beat_to_signal(_beat(2.0, 0.6, 0.4), source_index=1, beat_count=4)
    soft = beat_to_signal(_beat(3.0, 0.2, 0.3), source_index=2, beat_count=4)
    downbeat = beat_to_signal(_beat(4.0, 0.4, 0.4, True), source_index=3, beat_count=4)

    assert strong is not None and strong["signal_type"] == "beat_strong_sync_point"
    assert medium is not None and medium["signal_type"] == "beat_sync_point"
    assert soft is not None and soft["signal_type"] == "beat_soft_sync_point"
    assert downbeat is not None and downbeat["signal_type"] == "beat_downbeat_candidate"

    for field in REQUIRED_SIGNAL_FIELDS:
        assert field in strong

    beat_points = [
        BeatPoint(time_seconds=0.5, strength=0.8, confidence=0.7),
        BeatPoint(time_seconds=1.0, strength=0.6, confidence=0.6),
    ]
    run_report = BeatDetectionRunReport(status="ok", beats=[_beat(0.5), _beat(1.0)], beat_count=2)
    dict_source = {"beat_detection_result": {"beats": [_beat(0.25), _beat(0.75)]}}
    job_like = SimpleNamespace(beat_detection_beats=[_beat(2.0), _beat(2.5)])

    assert len(extract_beat_dicts([_beat(0.5), _beat(1.0)])) == 2
    assert len(extract_beat_dicts(beat_points)) == 2
    assert len(extract_beat_dicts(run_report)) == 2
    assert len(extract_beat_dicts(dict_source)) == 2
    assert len(extract_beat_dicts(job_like)) == 2

    max_result = adapt_beats_to_signals(
        [_beat(0.5, 0.2, 0.2), _beat(1.0, 0.95, 0.9), _beat(1.5, 0.6, 0.6)],
        max_signals=2,
    )
    assert max_result.signal_count == 2
    assert [signal["center_seconds"] for signal in max_result.signals] == [1.0, 1.5]

    assert beat_to_signal({"strength": 0.9}) is None
    assert beat_to_signal({"time_seconds": "broken"}) is None

    no_beats = adapt_beats_to_signals([])
    assert no_beats.status == "skipped_no_beats"
    assert no_beats.recommendation == "no_beats_available"


def test_2b12_integrated_flow_wav_to_runner_to_signal(tmp_path: Path) -> None:
    music_wav = _write_wav_16bit(tmp_path / "music_reference.wav", _pulse_samples())
    job = SimpleNamespace(
        preprocessing_manifest={
            "music_reference_audio_path": str(music_wav),
        }
    )

    report = run_beat_detection_for_job(job)
    signals = adapt_beat_detection_run_report_to_signals(report)

    assert report.status in {"ok", "completed_with_warnings"}
    assert report.selected_type == "music_reference_audio"
    assert report.beat_count > 0
    assert report.recommendation == "use_beat_timeline"

    assert signals.status in {"ok", "completed_with_warnings"}
    assert signals.signal_count >= 1
    assert signals.recommendation in {"use_beat_edit_signals", "review_warnings"}

    first_signal = signals.signals[0]
    for field in REQUIRED_SIGNAL_FIELDS:
        assert field in first_signal


def test_2b12_job_roundtrip_contract() -> None:
    payload = _job_payload()
    payload.update(
        {
            "beat_detection_report": {"status": "ok"},
            "beat_detection_status": "ok",
            "beat_detection_selected_path": "preprocessed/music.wav",
            "beat_detection_selected_type": "music_reference_audio",
            "beat_detection_source_selection": {"status": "selected"},
            "beat_detection_result": {"status": "ok"},
            "beat_detection_beats": [{"time_seconds": 0.5, "strength": 0.9}],
            "beat_detection_beat_count": 1,
            "beat_detection_estimated_bpm": 120.0,
            "beat_detection_average_beat_interval_seconds": 0.5,
            "beat_detection_duration_seconds": 2.0,
            "beat_detection_sample_rate": 1000,
            "beat_detection_channels": 1,
            "beat_detection_energy_frame_count": 12,
            "beat_detection_peak_threshold": 1.35,
            "beat_detection_min_beat_distance_seconds": 0.25,
            "beat_detection_max_beat_strength": 0.9,
            "beat_detection_avg_beat_strength": 0.9,
            "beat_detection_top_beat": {"time_seconds": 0.5, "strength": 0.9},
            "beat_detection_recommendation": "use_beat_timeline",
        }
    )

    job = Job.from_dict(payload)
    data = job.to_dict()

    for field in [
        "beat_detection_report",
        "beat_detection_status",
        "beat_detection_selected_path",
        "beat_detection_selected_type",
        "beat_detection_source_selection",
        "beat_detection_result",
        "beat_detection_beats",
        "beat_detection_beat_count",
        "beat_detection_estimated_bpm",
        "beat_detection_average_beat_interval_seconds",
        "beat_detection_duration_seconds",
        "beat_detection_sample_rate",
        "beat_detection_channels",
        "beat_detection_energy_frame_count",
        "beat_detection_peak_threshold",
        "beat_detection_min_beat_distance_seconds",
        "beat_detection_max_beat_strength",
        "beat_detection_avg_beat_strength",
        "beat_detection_top_beat",
        "beat_detection_recommendation",
    ]:
        assert field in data

    assert data["beat_detection_status"] == "ok"
    assert data["beat_detection_beat_count"] == 1
    assert data["beat_detection_estimated_bpm"] == 120.0

    old_job = Job.from_dict(_job_payload())
    assert old_job.beat_detection_report == {}
    assert old_job.beat_detection_status is None
    assert old_job.beat_detection_beats == []


def test_2b12_pipeline_source_contract() -> None:
    source = _pipeline_source()
    beat_block = _beat_detection_pipeline_block()

    required = [
        "from core.beat_detection_runner import run_beat_detection_for_job",
        "BEAT_DETECTION_STARTED",
        "BEAT_DETECTION_DONE",
        "BEAT_DETECTION_COMPLETED_WITH_WARNINGS",
        "BEAT_DETECTION_BLOCKED",
        "BEAT_DETECTION_SKIPPED",
        "BEAT_DETECTION_FAILED",
        "beat_detection_done",
        "run_beat_detection_for_job(",
        "job.beat_detection_report =",
        "job.beat_detection_status =",
        "job.beat_detection_selected_path =",
        "job.beat_detection_selected_type =",
        "job.beat_detection_beat_count =",
        "job.beat_detection_estimated_bpm =",
        "job.beat_detection_recommendation =",
    ]

    for marker in required:
        assert marker in source

    assert "analyze_wav_beats(" not in source
    assert "select_beat_detection_source(" not in source
    assert "select_beat_detection_source_for_job(" not in source
    assert "ffmpeg" not in beat_block.lower()
    assert "loudnorm" not in beat_block.lower()


def test_2b12_pipeline_order_and_file_hygiene() -> None:
    source = _pipeline_source()

    assert source.index("PREPROCESSING_READY") < source.index("BEAT_DETECTION_STARTED")
    assert source.index("ENERGY_PEAK_DETECTION_STARTED") < source.index("BEAT_DETECTION_STARTED")
    assert source.index("AUDIO_NORMALIZATION_STARTED") < source.index("BEAT_DETECTION_STARTED")
    assert source.index("BEAT_DETECTION_STARTED") < source.index("STATE_ANALYZING")
    assert "beat_detection_done" in source

    paths = [
        Path("models/beat_detection.py"),
        Path("core/beat_detector.py"),
        Path("models/beat_detection_source.py"),
        Path("core/beat_detection_source_selector.py"),
        Path("models/beat_detection_run.py"),
        Path("core/beat_detection_runner.py"),
        Path("models/beat_detection_signal.py"),
        Path("core/beat_detection_signal_adapter.py"),
        Path("models/job.py"),
        Path("core/gaming_pipeline.py"),
        Path("tests/test_beat_detection_foundation_smoke.py"),
        Path("tests/test_beat_detection_source_selector_smoke.py"),
        Path("tests/test_beat_detection_runner_smoke.py"),
        Path("tests/test_beat_detection_signal_adapter_smoke.py"),
        Path("tests/test_beat_detection_pipeline_integration_smoke.py"),
        Path("tests/test_beat_detection_final_audit_smoke.py"),
    ]

    for path in paths:
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert data.endswith(b"\n"), f"{path} does not end with newline"
