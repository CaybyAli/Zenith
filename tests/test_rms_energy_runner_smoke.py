from __future__ import annotations

import os
import struct
import wave
from types import SimpleNamespace
from typing import Any

import pytest

from models.rms_energy_run import RmsEnergyRunReport
from models.rms_energy import RmsEnergyTimelineResult
import core.rms_energy_runner as runner_module
from core.rms_energy_runner import build_rms_energy_run_report, run_rms_energy_for_job

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)


def _write_wav(path: str, duration_seconds: float = 0.3, sample_rate: int = 8000) -> None:
    n_frames = int(sample_rate * duration_seconds)
    amplitude = 4000
    data = struct.pack(f"<{n_frames}h", *([amplitude] * n_frames))
    with wave.open(path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(data)


# ── 1. roundtrip ─────────────────────────────────────────────────────────────

def test_rms_energy_run_report_roundtrip():
    report = RmsEnergyRunReport(
        status="ok",
        selected_path="/tmp/analysis.wav",
        selected_type="analysis_audio",
        timeline_status="ok",
        point_count=30,
        duration_seconds=0.3,
        sample_rate=8000,
        channels=1,
        frame_ms=10.0,
        hop_ms=5.0,
        min_rms=0.1,
        max_rms=0.9,
        avg_rms=0.5,
        min_normalized_energy=0.0,
        max_normalized_energy=1.0,
        avg_normalized_energy=0.5,
        warnings=["some_warning"],
        errors=[],
        recommendation="use_energy_timeline",
        metadata={"run": 1},
    )
    d = report.to_dict()
    restored = RmsEnergyRunReport.from_dict(d)
    assert restored.status == "ok"
    assert restored.selected_path == "/tmp/analysis.wav"
    assert restored.selected_type == "analysis_audio"
    assert restored.timeline_status == "ok"
    assert restored.point_count == 30
    assert restored.sample_rate == 8000
    assert restored.channels == 1
    assert restored.frame_ms == 10.0
    assert restored.hop_ms == 5.0
    assert restored.recommendation == "use_energy_timeline"
    assert restored.metadata == {"run": 1}
    assert restored.warnings == ["some_warning"]
    # None round-trip
    report_none = RmsEnergyRunReport(status="failed", sample_rate=None, channels=None, timeline_status=None)
    d2 = report_none.to_dict()
    r2 = RmsEnergyRunReport.from_dict(d2)
    assert r2.sample_rate is None
    assert r2.channels is None
    assert r2.timeline_status is None


# ── 2. analysis WAV selected and analyzed ────────────────────────────────────

def test_runner_selects_existing_analysis_wav_and_analyzes(tmp_path):
    wav = tmp_path / "analysis.wav"
    _write_wav(str(wav))
    manifest = {"analysis_audio_path": str(wav)}
    result = build_rms_energy_run_report(preprocessing_manifest=manifest)
    assert result.status == "ok"
    assert result.selected_type == "analysis_audio"
    assert result.point_count > 0
    assert result.timeline_status == "ok"
    assert result.recommendation == "use_energy_timeline"


# ── 3. speech WAV fallback ────────────────────────────────────────────────────

def test_runner_uses_speech_wav_fallback(tmp_path):
    speech = tmp_path / "speech.wav"
    _write_wav(str(speech))
    manifest = {
        "analysis_audio_path": str(tmp_path / "analysis.wav"),  # missing
        "speech_audio_path": str(speech),
    }
    result = build_rms_energy_run_report(preprocessing_manifest=manifest)
    assert result.status == "ok"
    assert result.selected_type == "speech_audio"


# ── 4. missing preprocessed audio blocks ─────────────────────────────────────

def test_runner_blocks_missing_preprocessed_audio(tmp_path):
    manifest = {"analysis_audio_path": str(tmp_path / "analysis.wav")}
    result = build_rms_energy_run_report(
        preprocessing_manifest=manifest,
        require_existing_file=True,
    )
    assert result.status == "blocked_missing_preprocessed_audio"
    assert result.recommendation == "generate_preprocessed_audio"
    assert result.point_count == 0


# ── 5. planned audio blocked when require_existing_file=False ─────────────────

def test_runner_blocks_planned_audio_when_require_existing_false(tmp_path):
    manifest = {"analysis_audio_path": str(tmp_path / "analysis.wav")}
    result = build_rms_energy_run_report(
        preprocessing_manifest=manifest,
        require_existing_file=False,
    )
    assert result.status == "blocked_missing_preprocessed_audio"
    assert result.selected_type == "planned_analysis_audio"
    assert result.point_count == 0


# ── 6. original MP4 skipped ───────────────────────────────────────────────────

def test_runner_skips_original_mp4(tmp_path):
    vid = tmp_path / "video.mp4"
    vid.write_bytes(b"\x00" * 16)
    result = build_rms_energy_run_report(
        fallback_source_path=str(vid),
        allow_original_wav_fallback=True,
    )
    assert result.status in ("skipped_unsupported_source", "failed")
    assert result.recommendation == "extract_audio_first"
    assert result.point_count == 0


# ── 7. original WAV fallback ──────────────────────────────────────────────────

def test_runner_accepts_original_wav_fallback(tmp_path):
    orig = tmp_path / "original.wav"
    _write_wav(str(orig))
    result = build_rms_energy_run_report(
        fallback_source_path=str(orig),
        allow_original_wav_fallback=True,
    )
    assert result.status == "ok"
    assert result.selected_type == "original_wav"
    assert "original_wav_used_for_rms_energy" in result.warnings


# ── 8. bad WAV fails safely ───────────────────────────────────────────────────

def test_runner_handles_bad_wav_as_failed(tmp_path):
    bad = tmp_path / "bad.wav"
    bad.write_text("this is not a wav file", encoding="utf-8")
    manifest = {"analysis_audio_path": str(bad)}
    result = build_rms_energy_run_report(preprocessing_manifest=manifest)
    assert result.status == "failed"
    assert any("wav_read_failed" in e for e in result.errors)


# ── 9. unavailable when no sources ───────────────────────────────────────────

def test_runner_unavailable_no_sources():
    result = build_rms_energy_run_report()
    assert result.status == "failed"
    assert result.recommendation == "no_audio_source_available"


# ── 10. job wrapper reads manifest ───────────────────────────────────────────

def test_run_rms_energy_for_job_reads_manifest(tmp_path):
    wav = tmp_path / "analysis.wav"
    _write_wav(str(wav))
    job = SimpleNamespace(
        preprocessing_manifest={"analysis_audio_path": str(wav)},
    )
    result = run_rms_energy_for_job(job)
    assert result.status == "ok"
    assert result.selected_type == "analysis_audio"


# ── 11. empty job safe ────────────────────────────────────────────────────────

def test_run_rms_energy_for_empty_job_safe():
    job = SimpleNamespace()
    result = run_rms_energy_for_job(job)
    assert result.status == "failed"
    # must not raise


# ── 12. frame and hop settings propagated ────────────────────────────────────

def test_runner_respects_frame_and_hop_settings(tmp_path):
    wav = tmp_path / "analysis.wav"
    _write_wav(str(wav), duration_seconds=1.0, sample_rate=16000)
    manifest = {"analysis_audio_path": str(wav)}
    result = build_rms_energy_run_report(
        preprocessing_manifest=manifest,
        frame_ms=100.0,
        hop_ms=100.0,
    )
    assert result.status == "ok"
    assert result.frame_ms == 100.0
    assert result.hop_ms == 100.0
    assert result.energy_timeline_result.get("frame_ms") == 100.0
    assert result.energy_timeline_result.get("hop_ms") == 100.0


# ── 13. analyzer NOT called for MP4 ──────────────────────────────────────────

def test_runner_does_not_call_analyzer_for_mp4_with_monkeypatch(tmp_path, monkeypatch):
    call_count: list[int] = [0]

    def fake_analyzer(path: str, **kwargs: Any) -> RmsEnergyTimelineResult:
        call_count[0] += 1
        return RmsEnergyTimelineResult(status="ok", source_path=path)

    monkeypatch.setattr(runner_module, "analyze_wav_rms_energy", fake_analyzer)

    vid = tmp_path / "video.mp4"
    vid.write_bytes(b"\x00" * 16)
    build_rms_energy_run_report(
        fallback_source_path=str(vid),
        allow_original_wav_fallback=True,
    )
    assert call_count[0] == 0


# ── 14. analyzer IS called for WAV ───────────────────────────────────────────

def test_runner_calls_analyzer_for_selected_wav_with_monkeypatch(tmp_path, monkeypatch):
    call_count: list[int] = [0]

    def fake_analyzer(path: str, **kwargs: Any) -> RmsEnergyTimelineResult:
        call_count[0] += 1
        frame_ms = kwargs.get("frame_ms", 10.0)
        hop_ms = kwargs.get("hop_ms", 5.0)
        return RmsEnergyTimelineResult(
            status="ok",
            source_path=path,
            sample_rate=8000,
            channels=1,
            duration_seconds=0.3,
            frame_ms=frame_ms,
            hop_ms=hop_ms,
            points=[],
            point_count=0,
        )

    monkeypatch.setattr(runner_module, "analyze_wav_rms_energy", fake_analyzer)

    wav = tmp_path / "analysis.wav"
    wav.write_bytes(b"placeholder")  # content irrelevant with fake analyzer
    # Selector checks existence; write a placeholder so exists=True
    manifest = {"analysis_audio_path": str(wav)}
    result = build_rms_energy_run_report(preprocessing_manifest=manifest)

    assert call_count[0] == 1
    assert result.selected_type == "analysis_audio"
    assert result.status == "ok"


# ── 15. BOM and newline hygiene ───────────────────────────────────────────────

def test_rms_energy_runner_files_have_no_bom_and_end_with_newline():
    files = [
        os.path.join(_REPO_ROOT, "models", "rms_energy_run.py"),
        os.path.join(_REPO_ROOT, "core", "rms_energy_runner.py"),
        os.path.join(_REPO_ROOT, "tests", "test_rms_energy_runner_smoke.py"),
    ]
    for path in files:
        raw = open(path, "rb").read()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {path}"
        assert raw.endswith(b"\n"), f"Missing trailing newline in {path}"
