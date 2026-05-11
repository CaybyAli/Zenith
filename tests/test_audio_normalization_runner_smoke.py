from __future__ import annotations

import json
import os
import struct
import wave
from types import SimpleNamespace

import pytest

from models.audio_normalization import AudioNormalizationResult
from models.audio_normalization_run import AudioNormalizationRunReport
from models.audio_normalization_source import AudioNormalizationSourceSelection
from core.audio_normalization_runner import (
    build_audio_normalization_run_report,
    run_audio_normalization_for_job,
)

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)


def _write_wav(path, samples_float, sample_rate=44100, channels=1):
    """Write a 16-bit PCM WAV file from float samples in [-1.0, 1.0]."""
    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        ints = [max(-32768, min(32767, int(s * 32767))) for s in samples_float]
        wf.writeframes(struct.pack(f"<{len(ints)}h", *ints))


def _normal_samples(n=200):
    """Samples with amplitude ~0.2 → RMS ~-17 dBFS (normal range)."""
    return [0.2 if i % 2 == 0 else -0.2 for i in range(n)]


def _quiet_samples(n=200):
    """Samples with amplitude ~0.001 → RMS ~-60 dBFS (too_quiet)."""
    return [0.001 if i % 2 == 0 else -0.001 for i in range(n)]


def _clipped_samples(n=200):
    """Samples at amplitude 1.0 → after int16 round-trip ~0.9999 ≥ 0.999 threshold."""
    return [1.0 if i % 2 == 0 else -1.0 for i in range(n)]


# ── 1. roundtrip ──────────────────────────────────────────────────────────────

def test_audio_normalization_run_report_roundtrip():
    report = AudioNormalizationRunReport(
        status="ok",
        selected_path="/tmp/analysis.wav",
        selected_type="analysis_audio",
        normalization_result={"status": "ok"},
        level_status="normal",
        normalization_needed=False,
        recommendation="no_normalization_needed",
        target_rms_dbfs=-18.0,
        target_peak_dbfs=-1.0,
        recommended_gain_db=0.5,
        limited_gain_db=0.5,
        gain_limited_by_peak=False,
        would_clip_after_gain=False,
        peak_dbfs=-3.0,
        rms_dbfs=-18.0,
        peak_amplitude=0.7,
        rms=0.126,
        clipping_sample_count=0,
        clipping_ratio=0.0,
        sample_count=1000,
        duration_seconds=0.02,
        sample_rate=44100,
        channels=1,
        warnings=[],
        errors=[],
        metadata={"job_id": "test"},
    )
    d = report.to_dict()
    restored = AudioNormalizationRunReport.from_dict(d)
    assert restored.status == "ok"
    assert restored.selected_path == "/tmp/analysis.wav"
    assert restored.selected_type == "analysis_audio"
    assert restored.level_status == "normal"
    assert restored.normalization_needed is False
    assert restored.recommendation == "no_normalization_needed"
    assert restored.sample_count == 1000
    assert restored.peak_dbfs == -3.0
    assert restored.rms_dbfs == -18.0
    assert restored.sample_rate == 44100
    assert restored.channels == 1
    assert restored.metadata == {"job_id": "test"}
    assert restored.normalization_result == {"status": "ok"}


# ── 2. analyze existing analysis WAV ─────────────────────────────────────────

def test_runner_analyzes_existing_analysis_wav(tmp_path):
    wav = tmp_path / "analysis.wav"
    _write_wav(wav, _normal_samples())
    manifest = {"analysis_audio_path": str(wav)}
    result = build_audio_normalization_run_report(preprocessing_manifest=manifest)
    assert result.status in ("ok", "completed_with_warnings")
    assert result.selected_type == "analysis_audio"
    assert result.selected_path == str(wav)
    assert result.sample_count > 0
    assert result.normalization_result != {}
    assert result.recommendation


# ── 3. speech WAV fallback ────────────────────────────────────────────────────

def test_runner_analyzes_existing_speech_wav_fallback(tmp_path):
    wav = tmp_path / "speech.wav"
    _write_wav(wav, _normal_samples())
    manifest = {"speech_audio_path": str(wav)}
    result = build_audio_normalization_run_report(preprocessing_manifest=manifest)
    assert result.status in ("ok", "completed_with_warnings")
    assert result.selected_type == "speech_audio"
    assert result.sample_count > 0


# ── 4. missing preprocessed audio blocks ─────────────────────────────────────

def test_runner_blocks_missing_preprocessed_audio(tmp_path):
    manifest = {"analysis_audio_path": str(tmp_path / "analysis.wav")}
    result = build_audio_normalization_run_report(preprocessing_manifest=manifest)
    assert result.status == "blocked_missing_preprocessed_audio"
    assert result.selected_type == "planned_analysis_audio"
    assert result.recommendation == "generate_preprocessed_audio"
    assert result.normalization_result == {}
    assert result.sample_count == 0


# ── 5. original MP4 skipped ───────────────────────────────────────────────────

def test_runner_skips_original_mp4(tmp_path):
    mp4 = tmp_path / "video.mp4"
    mp4.write_bytes(b"\x00" * 8)
    result = build_audio_normalization_run_report(original_source_path=str(mp4))
    assert result.status == "skipped_unsupported_source"
    assert result.recommendation == "extract_audio_first"
    assert result.sample_count == 0
    assert result.normalization_result == {}


# ── 6. original WAV fallback ──────────────────────────────────────────────────

def test_runner_original_wav_fallback(tmp_path):
    wav = tmp_path / "original.wav"
    _write_wav(wav, _normal_samples())
    result = build_audio_normalization_run_report(original_source_path=str(wav))
    assert result.selected_type == "original_wav"
    assert result.status in ("ok", "completed_with_warnings")
    assert "original_wav_used_for_normalization" in result.warnings


# ── 7. no audio source safe ───────────────────────────────────────────────────

def test_runner_no_audio_source_safe():
    result = build_audio_normalization_run_report()
    assert result.status == "skipped_no_audio_source"
    assert result.recommendation == "no_audio_source_available"
    assert result.sample_count == 0


# ── 8. bad WAV fails safely ───────────────────────────────────────────────────

def test_runner_bad_wav_failed(tmp_path):
    bad_wav = tmp_path / "analysis.wav"
    bad_wav.write_bytes(b"this is definitely not a wav file and will fail parsing")
    manifest = {"analysis_audio_path": str(bad_wav)}
    result = build_audio_normalization_run_report(preprocessing_manifest=manifest)
    assert result.status == "failed"
    assert any("wav_read_failed" in e for e in result.errors)
    assert result.selected_type == "analysis_audio"


# ── 9. too_quiet audio plan ───────────────────────────────────────────────────

def test_runner_too_quiet_audio_plan(tmp_path):
    wav = tmp_path / "quiet.wav"
    _write_wav(wav, _quiet_samples())
    manifest = {"analysis_audio_path": str(wav)}
    result = build_audio_normalization_run_report(preprocessing_manifest=manifest)
    assert result.status in ("ok", "completed_with_warnings")
    assert result.sample_count > 0
    assert isinstance(result.normalization_needed, bool)
    if result.level_status == "too_quiet":
        assert result.recommended_gain_db >= 0


# ── 10. clipped audio plan ────────────────────────────────────────────────────

def test_runner_clipped_audio_plan(tmp_path):
    wav = tmp_path / "clipped.wav"
    _write_wav(wav, _clipped_samples())
    manifest = {"analysis_audio_path": str(wav)}
    result = build_audio_normalization_run_report(preprocessing_manifest=manifest)
    assert result.clipping_sample_count > 0
    assert result.level_status == "clipped" or result.status == "completed_with_warnings"
    assert result.recommendation in ("fix_clipping", "review_warnings", "use_normalization_plan")


# ── 11. for_job reads manifest dict ──────────────────────────────────────────

def test_run_for_job_reads_manifest_dict(tmp_path):
    wav = tmp_path / "analysis.wav"
    _write_wav(wav, _normal_samples())
    job = SimpleNamespace(
        preprocessing_manifest={
            "audio_extraction_plan": {
                "targets": [
                    {"target_type": "analysis_audio", "output_path": str(wav)}
                ]
            }
        }
    )
    result = run_audio_normalization_for_job(job)
    assert result.selected_type == "analysis_audio"
    assert result.sample_count > 0


# ── 12. for_job reads manifest path JSON ─────────────────────────────────────

def test_run_for_job_reads_manifest_path_json(tmp_path):
    wav = tmp_path / "analysis.wav"
    _write_wav(wav, _normal_samples())
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(
        json.dumps({"analysis_audio_path": str(wav)}), encoding="utf-8"
    )
    job = SimpleNamespace(preprocessing_manifest_path=str(manifest_file))
    result = run_audio_normalization_for_job(job)
    assert result.selected_type == "analysis_audio"
    assert result.sample_count > 0


# ── 13. for_job original WAV fallback ────────────────────────────────────────

def test_run_for_job_original_wav_fallback(tmp_path):
    wav = tmp_path / "original.wav"
    _write_wav(wav, _normal_samples())
    job = SimpleNamespace(raw_video_path=str(wav))
    result = run_audio_normalization_for_job(job)
    assert result.selected_type == "original_wav"
    assert result.status in ("ok", "completed_with_warnings")


# ── 14. empty job safe ────────────────────────────────────────────────────────

def test_run_for_empty_job_safe():
    job = SimpleNamespace()
    result = run_audio_normalization_for_job(job)
    assert result.status in ("skipped_no_audio_source", "skipped_unsupported_source")


# ── 15. provided source_selection is used ────────────────────────────────────

def test_runner_uses_provided_source_selection(tmp_path):
    wav = tmp_path / "analysis.wav"
    _write_wav(wav, _normal_samples())
    sel = AudioNormalizationSourceSelection(
        status="selected",
        selected_path=str(wav),
        selected_type="analysis_audio",
        is_wav_source=True,
        source_exists=True,
        recommendation="analyze_selected_wav",
    )
    result = build_audio_normalization_run_report(source_selection=sel)
    assert result.selected_path == str(wav)
    assert result.selected_type == "analysis_audio"
    assert result.sample_count > 0


# ── 16. MP4 does not call analyzer ───────────────────────────────────────────

def test_runner_does_not_analyze_mp4_monkeypatch(tmp_path, monkeypatch):
    call_count = {"n": 0}

    def mock_analyzer(*args, **kwargs):
        call_count["n"] += 1
        return AudioNormalizationResult(status="ok")

    monkeypatch.setattr(
        "core.audio_normalization_runner.analyze_wav_audio_normalization",
        mock_analyzer,
    )

    mp4 = tmp_path / "video.mp4"
    mp4.write_bytes(b"\x00" * 8)
    build_audio_normalization_run_report(original_source_path=str(mp4))
    assert call_count["n"] == 0


# ── 17. WAV calls analyzer exactly once ──────────────────────────────────────

def test_runner_analyzes_wav_monkeypatch(tmp_path, monkeypatch):
    call_count = {"n": 0}

    def mock_analyzer(*args, **kwargs):
        call_count["n"] += 1
        return AudioNormalizationResult(
            status="ok",
            recommendation="no_normalization_needed",
        )

    monkeypatch.setattr(
        "core.audio_normalization_runner.analyze_wav_audio_normalization",
        mock_analyzer,
    )

    wav = tmp_path / "analysis.wav"
    wav.write_bytes(b"placeholder")  # content doesn't matter — mock replaces analyzer
    manifest = {"analysis_audio_path": str(wav)}
    build_audio_normalization_run_report(preprocessing_manifest=manifest)
    assert call_count["n"] == 1


# ── 18. BOM and newline hygiene ───────────────────────────────────────────────

def test_audio_normalization_runner_files_have_no_bom_and_end_with_newline():
    files = [
        os.path.join(_REPO_ROOT, "models", "audio_normalization_run.py"),
        os.path.join(_REPO_ROOT, "core", "audio_normalization_runner.py"),
        os.path.join(_REPO_ROOT, "tests", "test_audio_normalization_runner_smoke.py"),
    ]
    for path in files:
        raw = open(path, "rb").read()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {path}"
        assert raw.endswith(b"\n"), f"Missing trailing newline in {path}"
