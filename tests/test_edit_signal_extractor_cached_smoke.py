from __future__ import annotations

from types import SimpleNamespace

from core.edit_signal_extractor import EditSignalExtractor
from models.analysis_result import AnalysisResult


def _analysis(job_id: str, duration_seconds: float) -> AnalysisResult:
    return AnalysisResult(
        job_id=job_id,
        duration_seconds=duration_seconds,
        file_size_bytes=1234,
        usable_for_shorts=True,
        usable_for_longform=True,
        analysis_confidence=0.9,
        notes=[],
    )


def test_extract_uses_cached_audio_and_motion_without_moviepy(tmp_path, monkeypatch) -> None:
    raw_video = tmp_path / "raw.mp4"
    raw_video.write_bytes(b"placeholder")

    job = SimpleNamespace(
        job_id="job_cached_edit_signals",
        raw_video_path=str(raw_video),
        rms_energy_context_timeline=[
            {
                "start_seconds": 0.0,
                "end_seconds": 0.5,
                "energy_score": 0.9,
                "is_silent": False,
            },
            {
                "start_seconds": 1.0,
                "end_seconds": 1.5,
                "energy_score": 0.02,
                "is_silent": True,
            },
        ],
        motion_analysis_segments=[
            {
                "start_seconds": 0.0,
                "end_seconds": 1.0,
                "avg_motion_score": 0.72,
                "max_motion_score": 0.8,
                "classification": "high_motion",
            },
            {
                "start_seconds": 1.0,
                "end_seconds": 2.0,
                "avg_motion_score": 0.02,
                "max_motion_score": 0.03,
                "classification": "low_motion",
            },
        ],
    )

    extractor = EditSignalExtractor()
    monkeypatch.setattr(
        extractor,
        "_extract_audio_energy_signals",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("moviepy audio fallback used")),
    )
    monkeypatch.setattr(
        extractor,
        "_extract_video_activity_signals",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("moviepy video fallback used")),
    )

    signals = extractor.extract(job, _analysis(job.job_id, 2.0))
    signal_types = {signal.signal_type for signal in signals}

    assert "duration_context" in signal_types
    assert "audio_peak" in signal_types
    assert "silence_zone" in signal_types
    assert "motion_peak" in signal_types
    assert "low_motion_zone" in signal_types
    assert any(signal.source == "edit_signal_extractor.cached_audio" for signal in signals)
    assert any(signal.source == "edit_signal_extractor.cached_video" for signal in signals)


def test_cached_audio_points_are_bucketed_to_seconds() -> None:
    job = SimpleNamespace(
        job_id="job_cached_audio_buckets",
        rms_energy_context_timeline=[
            {
                "start_seconds": index * 0.01,
                "end_seconds": (index * 0.01) + 0.01,
                "energy_score": 0.8 if index < 100 else 0.2,
                "is_silent": False,
            }
            for index in range(300)
        ],
    )

    signals = EditSignalExtractor()._extract_cached_audio_energy_signals(
        job=job,
        duration_seconds=3.0,
    )

    assert 1 <= len(signals) <= 3
    assert {signal.start_time for signal in signals} == {0.0, 1.0, 2.0}
    assert all(signal.metadata["point_count"] >= 1 for signal in signals)


def test_cached_audio_mixed_silent_bucket_stays_activity() -> None:
    job = SimpleNamespace(
        job_id="job_cached_audio_mixed_silence",
        rms_energy_context_timeline=[
            {
                "start_seconds": index * 0.01,
                "end_seconds": (index * 0.01) + 0.01,
                "energy_score": 0.25,
                "is_silent": index < 70,
            }
            for index in range(100)
        ],
    )

    signals = EditSignalExtractor()._extract_cached_audio_energy_signals(
        job=job,
        duration_seconds=1.0,
    )

    assert len(signals) == 1
    assert signals[0].signal_type == "audio_activity"
    assert signals[0].metadata["silent_ratio"] == 0.7


def test_cached_visual_energy_segments_are_video_fallback_source() -> None:
    job = SimpleNamespace(
        job_id="job_cached_visual_energy",
        motion_analysis_segments=[],
        visual_energy_segments=[
            {
                "start_seconds": 2.0,
                "end_seconds": 4.0,
                "avg_visual_energy_score": 0.65,
                "max_visual_energy_score": 0.8,
                "classification": "peak_visual_energy",
            }
        ],
    )

    signals = EditSignalExtractor()._extract_cached_video_activity_signals(
        job=job,
        duration_seconds=5.0,
    )

    assert len(signals) == 1
    assert signals[0].signal_type == "motion_peak"
    assert signals[0].metadata["cache_source"] == "visual_energy_segments"
