from __future__ import annotations

import math
import wave
from pathlib import Path
from types import SimpleNamespace

from core.audio_normalization_analyzer import (
    analyze_audio_samples,
    build_normalization_result_from_stats,
    calculate_rms,
    clamp_gain_to_peak_headroom,
    dbfs_from_amplitude,
)
from core.audio_normalization_runner import (
    build_audio_normalization_run_report,
    run_audio_normalization_for_job,
)
from core.audio_normalization_signal_adapter import (
    adapt_audio_normalization_run_report_to_signals,
    audio_normalization_plan_to_signal,
)
from core.audio_normalization_source_selector import (
    select_audio_normalization_source,
    select_audio_normalization_source_for_job,
)
from models.audio_normalization import AudioLevelStats, AudioNormalizationResult
from models.audio_normalization_run import AudioNormalizationRunReport
from models.audio_normalization_signal import AudioNormalizationSignalAdapterResult
from models.audio_normalization_source import AudioNormalizationSourceSelection
from models.job import Job
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PIPELINE_FILE = REPO_ROOT / "core" / "gaming_pipeline.py"

AUDIO_NORMALIZATION_JOB_FIELDS = [
    "audio_normalization_report",
    "audio_normalization_status",
    "audio_normalization_selected_path",
    "audio_normalization_selected_type",
    "audio_normalization_source_selection",
    "audio_normalization_result",
    "audio_normalization_level_status",
    "audio_normalization_needed",
    "audio_normalization_recommendation",
    "audio_normalization_target_rms_dbfs",
    "audio_normalization_target_peak_dbfs",
    "audio_normalization_recommended_gain_db",
    "audio_normalization_limited_gain_db",
    "audio_normalization_gain_limited_by_peak",
    "audio_normalization_would_clip_after_gain",
    "audio_normalization_peak_dbfs",
    "audio_normalization_rms_dbfs",
    "audio_normalization_peak_amplitude",
    "audio_normalization_rms",
    "audio_normalization_clipping_sample_count",
    "audio_normalization_clipping_ratio",
    "audio_normalization_sample_count",
    "audio_normalization_duration_seconds",
    "audio_normalization_sample_rate",
    "audio_normalization_channels",
]

REQUIRED_SIGNAL_FIELDS = {
    "signal_type",
    "source",
    "level_status",
    "recommended_gain_db",
    "limited_gain_db",
    "target_rms_dbfs",
    "target_peak_dbfs",
    "normalization_needed",
    "signal_score",
    "priority",
    "reason",
    "source_plan",
    "metadata",
}

HYGIENE_FILES = [
    "models/audio_normalization.py",
    "core/audio_normalization_analyzer.py",
    "models/audio_normalization_source.py",
    "core/audio_normalization_source_selector.py",
    "models/audio_normalization_run.py",
    "core/audio_normalization_runner.py",
    "models/audio_normalization_signal.py",
    "core/audio_normalization_signal_adapter.py",
    "models/job.py",
    "core/gaming_pipeline.py",
    "tests/test_audio_normalization_foundation_smoke.py",
    "tests/test_audio_normalization_source_selector_smoke.py",
    "tests/test_audio_normalization_runner_smoke.py",
    "tests/test_audio_normalization_signal_adapter_smoke.py",
    "tests/test_audio_normalization_pipeline_integration_smoke.py",
    "tests/test_audio_normalization_final_audit_smoke.py",
]


def _write_wav(path: Path, samples: list[float], sample_rate: int = 8000) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)

        frames = bytearray()
        for sample in samples:
            clipped = max(-1.0, min(1.0, float(sample)))
            value = int(clipped * 32767)
            frames.extend(value.to_bytes(2, byteorder="little", signed=True))

        wav.writeframes(bytes(frames))

    return path


def _make_job(**overrides) -> Job:
    data = {
        "job_id": "job_audio_normalization_final_audit",
        "job_type": JobType.GAMING,
        "channel_type": ChannelType.GAMING_MAIN,
        "target_format": TargetFormat.LONGFORM,
        "target_platforms": ["youtube"],
        "status": JobStatus.ROUTED,
        "mode": Mode.NORMAL,
        "autopublish_class": AutopublishClass.MANUAL_ONLY,
        "confidence_score": 0.0,
        "validator_status": ValidatorStatus.NOT_VALIDATED,
        "raw_video_path": "tests/fixtures/input.mp4",
        "profile_id": "gaming_main",
        "quality_mode": "pro",
    }
    data.update(overrides)
    return Job(**data)


def _base_plan(**overrides) -> dict:
    plan = {
        "level_status": "too_quiet",
        "normalization_needed": True,
        "recommended_gain_db": 4.0,
        "limited_gain_db": 3.0,
        "target_rms_dbfs": -18.0,
        "target_peak_dbfs": -1.0,
        "reason": "final audit plan",
    }
    plan.update(overrides)
    return plan


def _pipeline_source() -> str:
    return PIPELINE_FILE.read_text(encoding="utf-8")


def _audio_normalization_block() -> str:
    source = _pipeline_source()
    start = source.index("# ── Audio Normalization (2B-11-E)")
    end = source.index("# ── End Audio Normalization")
    return source[start:end]


def test_2b11_models_roundtrip():
    stats = AudioLevelStats(
        peak_amplitude=0.8,
        rms=0.2,
        peak_dbfs=-1.9,
        rms_dbfs=-13.9,
        headroom_db=1.9,
        dynamic_range_db=12.0,
        clipping_sample_count=2,
        clipping_ratio=0.1,
        sample_count=20,
        duration_seconds=0.0025,
        sample_rate=8000,
        channels=1,
        warnings=["warn"],
        errors=[],
        metadata={"stage": "2B-11-F"},
    )
    restored_stats = AudioLevelStats.from_dict(stats.to_dict())
    assert restored_stats.peak_amplitude == 0.8
    assert restored_stats.sample_rate == 8000

    result = AudioNormalizationResult(
        status="ok",
        input_path="analysis.wav",
        level_status="too_quiet",
        stats=stats,
        recommended_gain_db=4.0,
        limited_gain_db=3.0,
        normalization_needed=True,
        recommendation="apply_gain",
    )
    restored_result = AudioNormalizationResult.from_dict(result.to_dict())
    assert restored_result.status == "ok"
    assert restored_result.stats.sample_count == 20
    assert restored_result.normalization_needed is True

    selection = AudioNormalizationSourceSelection(
        status="selected",
        selected_path="analysis.wav",
        selected_type="analysis_audio",
        checked_sources=[{"type": "analysis_audio", "usable": True}],
        is_wav_source=True,
        source_exists=True,
    )
    restored_selection = AudioNormalizationSourceSelection.from_dict(selection.to_dict())
    assert restored_selection.status == "selected"
    assert restored_selection.selected_type == "analysis_audio"

    report = AudioNormalizationRunReport(
        status="ok",
        source_selection=selection.to_dict(),
        selected_path="analysis.wav",
        selected_type="analysis_audio",
        normalization_result=result.to_dict(),
        level_status="too_quiet",
        normalization_needed=True,
        recommended_gain_db=4.0,
        limited_gain_db=3.0,
        sample_count=20,
        sample_rate=8000,
        channels=1,
    )
    restored_report = AudioNormalizationRunReport.from_dict(report.to_dict())
    assert restored_report.status == "ok"
    assert restored_report.selected_type == "analysis_audio"
    assert restored_report.sample_count == 20

    adapter_result = AudioNormalizationSignalAdapterResult(
        status="ok",
        signals=[{"signal_type": "audio_normalization_plan", "signal_score": 0.7}],
        signal_count=1,
        signal_types={"audio_normalization_plan": 1},
        recommendation="use_audio_edit_signals",
    )
    restored_adapter = AudioNormalizationSignalAdapterResult.from_dict(adapter_result.to_dict())
    assert restored_adapter.status == "ok"
    assert restored_adapter.signal_count == 1


def test_2b11_analyzer_contract():
    assert calculate_rms([1, -1, 1, -1]) == 1.0
    assert dbfs_from_amplitude(1.0) == 0.0
    assert math.isclose(dbfs_from_amplitude(0.5), -6.0206, abs_tol=0.01)
    assert dbfs_from_amplitude(0.0) is None

    limited_gain, limited = clamp_gain_to_peak_headroom(
        recommended_gain_db=10.0,
        peak_dbfs=-3.0,
        target_peak_dbfs=-1.0,
    )
    assert limited_gain == 2.0
    assert limited is True

    clipped_stats = analyze_audio_samples([1.0, -1.0, 0.5, -0.5], sample_rate=8000, channels=1)
    assert clipped_stats.clipping_sample_count >= 2
    assert "clipping_detected" in clipped_stats.warnings

    quiet_stats = analyze_audio_samples([0.01, -0.01] * 20, sample_rate=8000, channels=1)
    quiet_result = build_normalization_result_from_stats(quiet_stats)
    assert quiet_result.level_status == "too_quiet"
    assert quiet_result.normalization_needed is True

    silent_stats = analyze_audio_samples([0.0, 0.0, 0.0], sample_rate=8000, channels=1)
    silent_result = build_normalization_result_from_stats(silent_stats)
    assert silent_result.level_status == "silent"
    assert silent_result.recommendation == "audio_silent"

    empty_stats = analyze_audio_samples([None, "bad"], sample_rate=-1, channels=0)
    empty_result = build_normalization_result_from_stats(empty_stats)
    assert empty_stats.sample_count == 0
    assert empty_result.status == "completed_with_warnings"
    assert "no_samples" in empty_result.warnings


def test_2b11_source_selector_contract(tmp_path):
    analysis_wav = _write_wav(tmp_path / "analysis.wav", [0.2, -0.2] * 20)
    speech_wav = _write_wav(tmp_path / "speech.wav", [0.1, -0.1] * 20)
    music_wav = _write_wav(tmp_path / "music.wav", [0.05, -0.05] * 20)
    original_wav = _write_wav(tmp_path / "original.wav", [0.3, -0.3] * 20)
    original_mp4 = tmp_path / "original.mp4"
    original_mp4.write_bytes(b"fake mp4")

    selected = select_audio_normalization_source(
        preprocessing_manifest={
            "analysis_audio_path": str(analysis_wav),
            "speech_audio_path": str(speech_wav),
        },
        original_source_path=str(original_mp4),
    )
    assert selected.status == "selected"
    assert selected.selected_type == "analysis_audio"
    assert selected.checked_sources

    speech_fallback = select_audio_normalization_source(
        preprocessing_manifest={"speech_audio_path": str(speech_wav)},
    )
    assert speech_fallback.status == "selected"
    assert speech_fallback.selected_type == "speech_audio"

    music_fallback = select_audio_normalization_source(
        preprocessing_manifest={"music_reference_audio_path": str(music_wav)},
    )
    assert music_fallback.status == "selected_fallback"
    assert music_fallback.selected_type == "music_reference_audio"
    assert "music_reference_audio_used_for_normalization" in music_fallback.warnings

    missing = select_audio_normalization_source(
        preprocessing_manifest={"analysis_audio_path": str(tmp_path / "missing_analysis.wav")},
    )
    assert missing.status == "missing_preprocessed_audio"
    assert missing.selected_type == "planned_analysis_audio"

    original_wav_fallback = select_audio_normalization_source(
        preprocessing_manifest={},
        original_source_path=str(original_wav),
    )
    assert original_wav_fallback.status == "selected_fallback"
    assert original_wav_fallback.selected_type == "original_wav"

    original_mp4_result = select_audio_normalization_source(
        preprocessing_manifest={},
        original_source_path=str(original_mp4),
    )
    assert original_mp4_result.status == "skipped_unsupported_source"
    assert original_mp4_result.recommendation == "extract_audio_first"

    empty_job_result = select_audio_normalization_source_for_job(SimpleNamespace())
    assert empty_job_result.status == "unavailable"
    assert empty_job_result.errors


def test_2b11_runner_contract(tmp_path, monkeypatch):
    analysis_wav = _write_wav(tmp_path / "analysis.wav", [0.01, -0.01] * 80)
    speech_wav = _write_wav(tmp_path / "speech.wav", [0.02, -0.02] * 80)
    original_wav = _write_wav(tmp_path / "original.wav", [0.03, -0.03] * 80)
    original_mp4 = tmp_path / "original.mp4"
    original_mp4.write_bytes(b"fake mp4")
    bad_wav = tmp_path / "bad.wav"
    bad_wav.write_bytes(b"not a real wav")

    analysis_report = run_audio_normalization_for_job(
        SimpleNamespace(
            preprocessing_manifest={"analysis_audio_path": str(analysis_wav)},
            raw_video_path=str(original_mp4),
        )
    )
    assert analysis_report.status in {"ok", "completed_with_warnings"}
    assert analysis_report.selected_type == "analysis_audio"
    assert analysis_report.sample_count > 0

    speech_report = run_audio_normalization_for_job(
        SimpleNamespace(preprocessing_manifest={"speech_audio_path": str(speech_wav)})
    )
    assert speech_report.status in {"ok", "completed_with_warnings"}
    assert speech_report.selected_type == "speech_audio"

    missing_report = run_audio_normalization_for_job(
        SimpleNamespace(preprocessing_manifest={"analysis_audio_path": str(tmp_path / "missing.wav")})
    )
    assert missing_report.status == "blocked_missing_preprocessed_audio"

    mp4_report = run_audio_normalization_for_job(
        SimpleNamespace(preprocessing_manifest={}, raw_video_path=str(original_mp4))
    )
    assert mp4_report.status == "skipped_unsupported_source"
    assert mp4_report.recommendation == "extract_audio_first"

    original_wav_report = run_audio_normalization_for_job(
        SimpleNamespace(preprocessing_manifest={}, raw_video_path=str(original_wav))
    )
    assert original_wav_report.status in {"ok", "completed_with_warnings"}
    assert original_wav_report.selected_type == "original_wav"

    bad_report = build_audio_normalization_run_report(
        source_selection={
            "status": "selected",
            "selected_path": str(bad_wav),
            "selected_type": "analysis_audio",
            "warnings": [],
            "errors": [],
        }
    )
    assert bad_report.status == "failed"
    assert any("wav_read_failed" in error for error in bad_report.errors)

    empty_job_report = run_audio_normalization_for_job(SimpleNamespace())
    assert empty_job_report.status == "skipped_no_audio_source"

    provided_report = run_audio_normalization_for_job(
        SimpleNamespace(),
        source_selection={
            "status": "selected",
            "selected_path": str(analysis_wav),
            "selected_type": "analysis_audio",
            "warnings": [],
            "errors": [],
        },
    )
    assert provided_report.status in {"ok", "completed_with_warnings"}
    assert provided_report.selected_type == "analysis_audio"

    calls = {"count": 0}

    def fake_analyzer(*args, **kwargs):
        calls["count"] += 1
        return AudioNormalizationResult(
            status="ok",
            level_status="normal",
            stats=AudioLevelStats(sample_count=10, sample_rate=8000, channels=1),
            recommendation="no_normalization_needed",
        )

    monkeypatch.setattr(
        "core.audio_normalization_runner.analyze_wav_audio_normalization",
        fake_analyzer,
    )

    build_audio_normalization_run_report(
        source_selection={
            "status": "skipped_unsupported_source",
            "selected_path": str(original_mp4),
            "selected_type": "unsupported_original_source",
            "warnings": [],
            "errors": [],
        }
    )
    assert calls["count"] == 0

    build_audio_normalization_run_report(
        source_selection={
            "status": "selected",
            "selected_path": str(analysis_wav),
            "selected_type": "analysis_audio",
            "warnings": [],
            "errors": [],
        }
    )
    assert calls["count"] == 1


def test_2b11_signal_adapter_contract():
    expected = {
        "too_quiet": "audio_gain_boost_recommended",
        "too_loud": "audio_gain_reduce_recommended",
        "clipped": "audio_clipping_warning",
        "silent": "audio_silent_warning",
    }

    for level_status, signal_type in expected.items():
        signal = audio_normalization_plan_to_signal(_base_plan(level_status=level_status))
        assert signal is not None
        assert signal["signal_type"] == signal_type
        assert REQUIRED_SIGNAL_FIELDS.issubset(signal.keys())

    no_needed = audio_normalization_plan_to_signal(
        _base_plan(level_status="normal", normalization_needed=False, recommended_gain_db=0.0)
    )
    assert no_needed is not None
    assert no_needed["signal_type"] == "audio_no_normalization_needed"

    plan_signal = audio_normalization_plan_to_signal(
        _base_plan(level_status="normal", normalization_needed=True)
    )
    assert plan_signal is not None
    assert plan_signal["signal_type"] == "audio_normalization_plan"

    bad = adapt_audio_normalization_run_report_to_signals({"bad": object()})
    assert bad.status in {"skipped_no_normalization_plan", "failed"}
    assert isinstance(bad.to_dict(), dict)

    result = adapt_audio_normalization_run_report_to_signals(
        AudioNormalizationRunReport(
            status="ok",
            normalization_result=_base_plan(level_status="too_quiet"),
            level_status="too_quiet",
            normalization_needed=True,
            recommended_gain_db=4.0,
            limited_gain_db=3.0,
        )
    )
    assert result.status == "ok"
    assert result.signal_count >= 1
    assert result.signals[0]["metadata"]["future_edit_compatible"] is True


def test_2b11_integrated_flow_wav_to_runner_to_signal(tmp_path):
    analysis_wav = _write_wav(tmp_path / "analysis.wav", [0.01, -0.01] * 100)
    job = SimpleNamespace(
        preprocessing_manifest={"analysis_audio_path": str(analysis_wav)},
        raw_video_path=str(tmp_path / "source.mp4"),
    )

    report = run_audio_normalization_for_job(job)

    assert report.status in {"ok", "completed_with_warnings"}
    assert report.selected_type == "analysis_audio"
    assert report.sample_count > 0

    adapter_result = adapt_audio_normalization_run_report_to_signals(report)

    assert adapter_result.status in {"ok", "completed_with_warnings", "skipped_no_normalization_plan"}
    assert isinstance(adapter_result.to_dict(), dict)

    if adapter_result.signals:
        first_signal = adapter_result.signals[0]
        assert REQUIRED_SIGNAL_FIELDS.issubset(first_signal.keys())
        assert first_signal["metadata"]["future_edit_compatible"] is True


def test_2b11_job_roundtrip_contract():
    job = _make_job()

    job.audio_normalization_report = {"status": "ok"}
    job.audio_normalization_status = "ok"
    job.audio_normalization_selected_path = "preprocessed/job/audio/analysis.wav"
    job.audio_normalization_selected_type = "analysis_audio"
    job.audio_normalization_source_selection = {"status": "selected"}
    job.audio_normalization_result = {"level_status": "too_quiet"}
    job.audio_normalization_level_status = "too_quiet"
    job.audio_normalization_needed = True
    job.audio_normalization_recommendation = "use_normalization_plan"
    job.audio_normalization_target_rms_dbfs = -18.0
    job.audio_normalization_target_peak_dbfs = -1.0
    job.audio_normalization_recommended_gain_db = 4.5
    job.audio_normalization_limited_gain_db = 3.0
    job.audio_normalization_gain_limited_by_peak = True
    job.audio_normalization_would_clip_after_gain = False
    job.audio_normalization_peak_dbfs = -2.0
    job.audio_normalization_rms_dbfs = -24.5
    job.audio_normalization_peak_amplitude = 0.79
    job.audio_normalization_rms = 0.05
    job.audio_normalization_clipping_sample_count = 12
    job.audio_normalization_clipping_ratio = 0.01
    job.audio_normalization_sample_count = 44100
    job.audio_normalization_duration_seconds = 1.0
    job.audio_normalization_sample_rate = 44100
    job.audio_normalization_channels = 2

    payload = job.to_dict()
    restored = Job.from_dict(payload)

    for field_name in AUDIO_NORMALIZATION_JOB_FIELDS:
        assert field_name in payload

    assert restored.audio_normalization_status == "ok"
    assert restored.audio_normalization_selected_type == "analysis_audio"
    assert restored.audio_normalization_recommended_gain_db == 4.5
    assert restored.audio_normalization_clipping_sample_count == 12

    old_job = Job.from_dict(
        {
            "job_id": "old_job_without_audio_normalization",
            "job_type": "gaming",
            "channel_type": "gaming_main",
            "target_format": "longform",
            "target_platforms": ["youtube"],
            "status": "routed",
            "mode": "normal",
            "autopublish_class": "manual_only",
            "confidence_score": 0.0,
            "validator_status": "not_validated",
        }
    )
    assert old_job.audio_normalization_report == {}
    assert old_job.audio_normalization_status is None
    assert old_job.audio_normalization_needed is False


def test_2b11_pipeline_source_contract():
    source = _pipeline_source()
    audio_block = _audio_normalization_block()

    must_contain = [
        "from core.audio_normalization_runner import run_audio_normalization_for_job",
        "AUDIO_NORMALIZATION_STARTED",
        "AUDIO_NORMALIZATION_DONE",
        "AUDIO_NORMALIZATION_COMPLETED_WITH_WARNINGS",
        "AUDIO_NORMALIZATION_BLOCKED",
        "AUDIO_NORMALIZATION_SKIPPED",
        "AUDIO_NORMALIZATION_FAILED",
        "audio_normalization_done",
        "run_audio_normalization_for_job(",
        "job.audio_normalization_report =",
        "job.audio_normalization_status =",
        "job.audio_normalization_selected_path =",
        "job.audio_normalization_selected_type =",
        "job.audio_normalization_recommended_gain_db =",
        "job.audio_normalization_clipping_sample_count =",
    ]

    for text in must_contain:
        assert text in source

    low_level_calls = [
        "analyze_wav_audio_normalization(",
        "select_audio_normalization_source(",
        "select_audio_normalization_source_for_job(",
        "loudnorm",
    ]
    for text in low_level_calls:
        assert text not in source

    assert "ffmpeg" not in audio_block.lower()
    assert "loudnorm" not in audio_block.lower()


def test_2b11_pipeline_order_contract():
    source = _pipeline_source()

    filler_index = source.index("FILLER_WORD_DETECTION_STARTED")
    energy_peak_index = source.index("ENERGY_PEAK_DETECTION_STARTED")
    audio_start_index = source.index("AUDIO_NORMALIZATION_STARTED")
    analyzing_index = source.index("STATE_ANALYZING")

    preprocessing_candidates = [
        source.find("PREPROCESSING_READY"),
        source.find("PREPROCESSING_WORKSPACE_READY"),
    ]
    preprocessing_index = min(index for index in preprocessing_candidates if index >= 0)

    assert preprocessing_index < audio_start_index
    assert energy_peak_index < audio_start_index
    assert filler_index < audio_start_index
    assert audio_start_index < analyzing_index
    assert "step_name=\"audio_normalization_done\"" in source


def test_2b11_files_have_no_bom_and_end_with_newline():
    for relative_path in HYGIENE_FILES:
        path = REPO_ROOT / relative_path
        content = path.read_bytes()

        assert not content.startswith(b"\xef\xbb\xbf"), f"BOM found in {relative_path}"
        assert content.endswith(b"\n"), f"Missing trailing newline in {relative_path}"
