from __future__ import annotations

from pathlib import Path

from core.unified_edit_signal_registry import (
    DEFAULT_DEDUP_CENTER_TOLERANCE_SECONDS,
    SOURCE_AUDIO_NORMALIZATION,
    SOURCE_BEAT_DETECTION,
    SOURCE_ENERGY_PEAK,
    SOURCE_FILLER_WORD,
    SOURCE_SILENCE_CLASSIFICATION,
    apply_unified_edit_signal_result_to_job,
    build_unified_edit_signal_result,
    run_unified_edit_signal_registry_for_job,
)
from models.job import Job
from models.unified_edit_signal_result import UnifiedEditSignalResult
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)


def _make_job() -> Job:
    return Job(
        job_id="job_phase3c_registry_001",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="input.mp4",
    )


def _energy_peak_report_with_one_peak(center: float = 10.0) -> dict:
    return {
        "status": "ok",
        "peak_count": 1,
        "peaks": [
            {
                "peak_type": "high_energy",
                "start_seconds": center - 0.5,
                "end_seconds": center + 0.5,
                "center_seconds": center,
                "energy_score": 0.9,
                "peak_score": 0.9,
                "confidence": 0.85,
                "reason": "test_peak",
                "rules_applied": ["high_energy"],
            }
        ],
        "recommendation": "use_peaks",
    }


def _filler_report_with_one_filler(center: float = 5.0) -> dict:
    return {
        "status": "ok",
        "occurrence_count": 1,
        "occurrences": [
            {
                "text": "äh",
                "normalized_text": "äh",
                "filler_type": "hesitation",
                "language": "de",
                "start_seconds": center - 0.1,
                "end_seconds": center + 0.1,
                "center_seconds": center,
                "duration_seconds": 0.2,
                "confidence": 0.8,
                "remove_candidate": True,
                "reason": "hesitation_filler",
            }
        ],
        "recommendation": "use_filler_word_analysis",
    }


def _beat_report_with_two_beats(times: tuple[float, ...] = (1.0, 2.0)) -> dict:
    return {
        "status": "ok",
        "beat_count": len(times),
        "estimated_bpm": 120.0,
        "beats": [
            {
                "time_seconds": t,
                "strength": 0.9,
                "confidence": 0.85,
                "is_downbeat_candidate": (i == 0),
            }
            for i, t in enumerate(times)
        ],
        "beat_detection_result": {
            "beats": [
                {
                    "time_seconds": t,
                    "strength": 0.9,
                    "confidence": 0.85,
                    "is_downbeat_candidate": (i == 0),
                }
                for i, t in enumerate(times)
            ],
        },
        "recommendation": "use_beats",
    }


def _audio_normalization_report_too_quiet() -> dict:
    return {
        "status": "completed_with_warnings",
        "level_status": "too_quiet",
        "normalization_needed": True,
        "recommended_gain_db": 6.0,
        "limited_gain_db": 6.0,
        "target_rms_dbfs": -18.0,
        "target_peak_dbfs": -1.0,
        "reason": "audio_too_quiet",
    }


def test_empty_job_does_not_crash_and_yields_skipped() -> None:
    job = _make_job()

    result = build_unified_edit_signal_result(job=job)

    assert isinstance(result, UnifiedEditSignalResult)
    assert result.status == "skipped_no_signals"
    assert result.signal_count == 0
    assert result.signals == []
    assert result.recommendation == "no_edit_signals_available"


def test_registry_collects_energy_peak_signals() -> None:
    job = _make_job()
    job.energy_peak_report = _energy_peak_report_with_one_peak(center=12.0)

    result = build_unified_edit_signal_result(job=job)

    assert result.signal_count >= 1
    assert SOURCE_ENERGY_PEAK in result.source_counts
    assert any(s["source"] == SOURCE_ENERGY_PEAK for s in result.signals)


def test_registry_collects_filler_word_signals() -> None:
    job = _make_job()
    job.filler_word_report = _filler_report_with_one_filler(center=7.0)

    result = build_unified_edit_signal_result(job=job)

    assert result.signal_count >= 1
    assert SOURCE_FILLER_WORD in result.source_counts
    assert any(s["source"] == SOURCE_FILLER_WORD for s in result.signals)


def test_registry_collects_audio_normalization_signals() -> None:
    job = _make_job()
    job.audio_normalization_report = _audio_normalization_report_too_quiet()

    result = build_unified_edit_signal_result(job=job)

    assert result.signal_count >= 1
    assert SOURCE_AUDIO_NORMALIZATION in result.source_counts
    assert any(s["source"] == SOURCE_AUDIO_NORMALIZATION for s in result.signals)


def test_registry_collects_beat_detection_signals() -> None:
    job = _make_job()
    job.beat_detection_report = _beat_report_with_two_beats((4.0, 5.0))

    result = build_unified_edit_signal_result(job=job)

    assert result.signal_count >= 2
    assert SOURCE_BEAT_DETECTION in result.source_counts
    assert any(s["source"] == SOURCE_BEAT_DETECTION for s in result.signals)


def test_registry_collects_silence_classification_signals() -> None:
    job = _make_job()
    job.silence_classifications = [
        {
            "start_seconds": 3.0,
            "end_seconds": 3.6,
            "duration_seconds": 0.6,
            "classification": "silence_remove",
            "remove_candidate": True,
            "confidence": 0.8,
            "reason": "long_silence",
        }
    ]

    result = build_unified_edit_signal_result(job=job)

    assert SOURCE_SILENCE_CLASSIFICATION in result.source_counts
    assert any(
        s["source"] == SOURCE_SILENCE_CLASSIFICATION
        and s["signal_type"] == "silence_remove_candidate"
        for s in result.signals
    )


def test_registry_deduplicates_near_duplicate_signals() -> None:
    job = _make_job()
    job.beat_detection_report = {
        "status": "ok",
        "beat_count": 3,
        "estimated_bpm": 120.0,
        "beats": [
            {
                "time_seconds": 5.00,
                "strength": 0.8,
                "confidence": 0.8,
                "is_downbeat_candidate": False,
            },
            {
                "time_seconds": 5.05,
                "strength": 0.9,
                "confidence": 0.9,
                "is_downbeat_candidate": False,
            },
            {
                "time_seconds": 5.50,
                "strength": 0.85,
                "confidence": 0.85,
                "is_downbeat_candidate": False,
            },
        ],
        "beat_detection_result": {
            "beats": [
                {
                    "time_seconds": 5.00,
                    "strength": 0.8,
                    "confidence": 0.8,
                    "is_downbeat_candidate": False,
                },
                {
                    "time_seconds": 5.05,
                    "strength": 0.9,
                    "confidence": 0.9,
                    "is_downbeat_candidate": False,
                },
                {
                    "time_seconds": 5.50,
                    "strength": 0.85,
                    "confidence": 0.85,
                    "is_downbeat_candidate": False,
                },
            ],
        },
    }

    result = build_unified_edit_signal_result(
        job=job,
        dedup_tolerance_seconds=DEFAULT_DEDUP_CENTER_TOLERANCE_SECONDS,
    )

    assert result.duplicate_count >= 1
    centers = [s.get("center_seconds") for s in result.signals if s["source"] == SOURCE_BEAT_DETECTION]
    assert len(centers) == 2

    winner = next(
        s
        for s in result.signals
        if s["source"] == SOURCE_BEAT_DETECTION and abs((s.get("center_seconds") or 0.0) - 5.025) < 0.2
    )
    assert int(winner["metadata"].get("duplicate_count") or 0) >= 1
    assert winner["metadata"].get("merged_sources")


def test_registry_sorts_signals_chronologically() -> None:
    job = _make_job()
    job.beat_detection_report = _beat_report_with_two_beats((2.0, 1.0))
    job.filler_word_report = _filler_report_with_one_filler(center=3.0)
    job.energy_peak_report = _energy_peak_report_with_one_peak(center=10.0)

    result = build_unified_edit_signal_result(job=job)
    centers = [s.get("center_seconds") for s in result.signals if s.get("center_seconds") is not None]
    assert centers == sorted(centers)


def test_registry_combines_multiple_sources() -> None:
    job = _make_job()
    job.energy_peak_report = _energy_peak_report_with_one_peak(center=10.0)
    job.filler_word_report = _filler_report_with_one_filler(center=5.0)
    job.beat_detection_report = _beat_report_with_two_beats((1.0, 2.0))
    job.audio_normalization_report = _audio_normalization_report_too_quiet()

    result = build_unified_edit_signal_result(job=job)

    assert result.status in {"ok", "completed_with_warnings"}
    assert result.signal_count >= 5
    assert SOURCE_ENERGY_PEAK in result.source_counts
    assert SOURCE_FILLER_WORD in result.source_counts
    assert SOURCE_BEAT_DETECTION in result.source_counts
    assert SOURCE_AUDIO_NORMALIZATION in result.source_counts
    assert result.max_signal_score > 0.0
    assert result.avg_signal_score > 0.0


def test_apply_result_to_job_sets_fields_and_roundtrips() -> None:
    job = _make_job()
    job.filler_word_report = _filler_report_with_one_filler(center=2.0)
    job.energy_peak_report = _energy_peak_report_with_one_peak(center=8.0)

    result = run_unified_edit_signal_registry_for_job(job=job)

    assert job.unified_edit_signal_status == result.status
    assert job.unified_edit_signal_count == result.signal_count
    assert job.unified_edit_signals == result.signals
    assert job.unified_edit_signal_summary["signal_count"] == result.signal_count
    assert job.unified_edit_signal_recommendation == result.recommendation

    restored = Job.from_dict(job.to_dict())
    assert restored.unified_edit_signal_status == job.unified_edit_signal_status
    assert restored.unified_edit_signal_count == job.unified_edit_signal_count
    assert restored.unified_edit_signals == job.unified_edit_signals
    assert restored.unified_edit_signal_summary == job.unified_edit_signal_summary
    assert (
        restored.unified_edit_signal_recommendation
        == job.unified_edit_signal_recommendation
    )


def test_old_job_dict_loads_without_unified_signal_fields() -> None:
    legacy_data = {
        "job_id": "legacy_job_001",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "short",
        "target_platforms": ["youtube"],
        "status": "routed",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
    }

    restored = Job.from_dict(legacy_data)

    assert restored.unified_edit_signal_report == {}
    assert restored.unified_edit_signal_status is None
    assert restored.unified_edit_signals == []
    assert restored.unified_edit_signal_count == 0
    assert restored.unified_edit_signal_summary == {}
    assert restored.unified_edit_signal_recommendation is None


def test_registry_handles_failing_adapter_safely(monkeypatch) -> None:
    job = _make_job()
    job.energy_peak_report = _energy_peak_report_with_one_peak(center=12.0)
    job.filler_word_report = _filler_report_with_one_filler(center=3.0)

    import core.unified_edit_signal_registry as registry_module

    def _boom(_report):
        raise RuntimeError("simulated adapter failure")

    monkeypatch.setattr(
        registry_module,
        "adapt_filler_word_run_report_to_signals",
        _boom,
    )

    result = build_unified_edit_signal_result(job=job)

    assert any("filler_word_adapter_failed" in err for err in result.errors)
    assert SOURCE_ENERGY_PEAK in result.source_counts
    assert result.signal_count >= 1


def test_signal_format_matches_specified_fields() -> None:
    job = _make_job()
    job.filler_word_report = _filler_report_with_one_filler(center=4.0)

    result = build_unified_edit_signal_result(job=job)

    assert result.signals
    signal = result.signals[0]

    required_fields = {
        "signal_id",
        "signal_type",
        "source",
        "start_seconds",
        "end_seconds",
        "center_seconds",
        "duration_seconds",
        "signal_score",
        "priority",
        "action_hint",
        "reason",
        "confidence",
        "metadata",
    }
    missing = required_fields - set(signal.keys())
    assert not missing, f"signal missing fields: {missing}"


def test_phase3c_registry_files_have_no_bom_and_end_with_newline() -> None:
    files = [
        Path("core/unified_edit_signal_registry.py"),
        Path("models/unified_edit_signal_result.py"),
        Path("tests/test_phase3c_unified_edit_signal_registry_smoke.py"),
    ]

    for file_path in files:
        content = file_path.read_bytes()

        assert not content.startswith(b"\xef\xbb\xbf"), f"{file_path} has UTF-8 BOM"
        assert content.endswith(b"\n"), f"{file_path} must end with newline"
