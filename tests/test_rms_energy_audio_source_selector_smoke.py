from __future__ import annotations

import os
from types import SimpleNamespace

import pytest

from models.rms_energy_audio_source import RmsEnergyAudioSourceSelection
from core.rms_energy_audio_source_selector import (
    select_rms_energy_audio_source,
    select_rms_energy_audio_source_for_job,
)

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)


# ── 1. roundtrip ─────────────────────────────────────────────────────────────

def test_rms_energy_audio_source_selection_roundtrip():
    sel = RmsEnergyAudioSourceSelection(
        status="selected",
        selected_path="/tmp/analysis.wav",
        selected_type="analysis_audio",
        exists=True,
        is_wav=True,
        source_priority=["analysis_audio", "speech_audio"],
        checked_sources=[{"source_type": "analysis_audio", "path": "/tmp/analysis.wav",
                           "exists": True, "is_wav": True, "accepted": True, "reason": "ok"}],
        allow_original_wav_fallback=True,
        requires_extraction=False,
        warnings=[],
        errors=[],
        recommendation="analyze_wav",
        metadata={"extra": 1},
    )
    d = sel.to_dict()
    restored = RmsEnergyAudioSourceSelection.from_dict(d)
    assert restored.status == "selected"
    assert restored.selected_path == "/tmp/analysis.wav"
    assert restored.selected_type == "analysis_audio"
    assert restored.exists is True
    assert restored.is_wav is True
    assert restored.source_priority == ["analysis_audio", "speech_audio"]
    assert len(restored.checked_sources) == 1
    assert restored.recommendation == "analyze_wav"
    assert restored.metadata == {"extra": 1}


# ── 2. analysis_audio WAV preferred ──────────────────────────────────────────

def test_selects_existing_analysis_audio_wav_first(tmp_path):
    wav = tmp_path / "analysis.wav"
    wav.write_bytes(b"RIFF" + b"\x00" * 36)
    manifest = {"analysis_audio_path": str(wav)}
    result = select_rms_energy_audio_source(preprocessing_manifest=manifest)
    assert result.status == "selected"
    assert result.selected_type == "analysis_audio"
    assert result.exists is True
    assert result.is_wav is True
    assert result.recommendation == "analyze_wav"


# ── 3. speech_audio fallback ──────────────────────────────────────────────────

def test_selects_speech_audio_when_analysis_missing(tmp_path):
    speech = tmp_path / "speech.wav"
    speech.write_bytes(b"RIFF" + b"\x00" * 36)
    manifest = {
        "analysis_audio_path": str(tmp_path / "analysis.wav"),  # does not exist
        "speech_audio_path": str(speech),
    }
    result = select_rms_energy_audio_source(preprocessing_manifest=manifest)
    assert result.status == "selected"
    assert result.selected_type == "speech_audio"
    assert result.exists is True
    assert result.is_wav is True


# ── 4. music_reference warning fallback ──────────────────────────────────────

def test_music_reference_is_warning_fallback(tmp_path):
    music = tmp_path / "music.wav"
    music.write_bytes(b"RIFF" + b"\x00" * 36)
    manifest = {"music_reference_audio_path": str(music)}
    result = select_rms_energy_audio_source(preprocessing_manifest=manifest)
    assert result.status == "selected_fallback"
    assert result.selected_type == "music_reference_audio"
    assert "music_reference_audio_used_for_rms_energy" in result.warnings


# ── 5. planned analysis audio require_existing_file=False ────────────────────

def test_planned_analysis_audio_when_require_existing_false(tmp_path):
    planned = tmp_path / "analysis.wav"  # intentionally not created
    manifest = {"analysis_audio_path": str(planned)}
    result = select_rms_energy_audio_source(
        preprocessing_manifest=manifest,
        require_existing_file=False,
    )
    assert result.status == "missing_preprocessed_audio"
    assert result.selected_type == "planned_analysis_audio"
    assert result.requires_extraction is True
    assert result.recommendation == "generate_preprocessed_audio"


# ── 6. missing preprocessed audio require_existing_file=True ─────────────────

def test_missing_preprocessed_audio_when_require_existing_true(tmp_path):
    manifest = {"analysis_audio_path": str(tmp_path / "analysis.wav")}
    result = select_rms_energy_audio_source(
        preprocessing_manifest=manifest,
        require_existing_file=True,
    )
    assert result.status == "missing_preprocessed_audio"
    assert result.requires_extraction is True


# ── 7. original WAV fallback ──────────────────────────────────────────────────

def test_original_wav_fallback_allowed(tmp_path):
    orig = tmp_path / "original.wav"
    orig.write_bytes(b"RIFF" + b"\x00" * 36)
    result = select_rms_energy_audio_source(
        fallback_source_path=str(orig),
        allow_original_wav_fallback=True,
    )
    assert result.status == "selected_fallback"
    assert result.selected_type == "original_wav"
    assert "original_wav_used_for_rms_energy" in result.warnings


# ── 8. original MP4 rejected ──────────────────────────────────────────────────

def test_original_mp4_is_not_selected_for_wav_analyzer(tmp_path):
    vid = tmp_path / "video.mp4"
    vid.write_bytes(b"\x00" * 8)
    result = select_rms_energy_audio_source(
        fallback_source_path=str(vid),
        allow_original_wav_fallback=True,
    )
    assert result.selected_path is None or result.selected_type != "original_wav"
    assert result.requires_extraction is True
    all_warnings_errors = result.warnings + result.errors
    assert any("original_source_not_wav" in w for w in all_warnings_errors)
    assert result.recommendation == "extract_audio_first"
    assert result.status in ("unsupported_original_source", "unavailable")


# ── 9. non-WAV preprocessed target skipped ───────────────────────────────────

def test_non_wav_preprocessed_target_is_skipped(tmp_path):
    speech = tmp_path / "speech.wav"
    speech.write_bytes(b"RIFF" + b"\x00" * 36)
    manifest = {
        "analysis_audio_path": str(tmp_path / "analysis.m4a"),  # non-WAV
        "speech_audio_path": str(speech),
    }
    result = select_rms_energy_audio_source(preprocessing_manifest=manifest)
    assert result.selected_type == "speech_audio"
    analysis_entry = next(
        (s for s in result.checked_sources if s.get("source_type") == "analysis_audio"),
        None,
    )
    assert analysis_entry is not None
    assert analysis_entry["accepted"] is False


# ── 10. audio_extraction_plan targets ────────────────────────────────────────

def test_reads_audio_extraction_plan_targets(tmp_path):
    wav = tmp_path / "analysis_plan.wav"
    wav.write_bytes(b"RIFF" + b"\x00" * 36)
    manifest = {
        "audio_extraction_plan": {
            "targets": [
                {
                    "target_type": "analysis_audio",
                    "output_path": str(wav),
                }
            ]
        }
    }
    result = select_rms_energy_audio_source(preprocessing_manifest=manifest)
    assert result.status == "selected"
    assert result.selected_type == "analysis_audio"
    assert result.is_wav is True


# ── 11. unavailable when no sources ──────────────────────────────────────────

def test_unavailable_when_no_sources():
    result = select_rms_energy_audio_source()
    assert result.status == "unavailable"
    assert "no_rms_energy_audio_source_available" in result.errors


# ── 12. job wrapper reads manifest and raw_video_path ─────────────────────────

def test_job_wrapper_reads_manifest_and_raw_path(tmp_path):
    speech = tmp_path / "speech.wav"
    speech.write_bytes(b"RIFF" + b"\x00" * 36)
    job = SimpleNamespace(
        preprocessing_manifest={"speech_audio_path": str(speech)},
        raw_video_path=str(tmp_path / "video.mp4"),
    )
    result = select_rms_energy_audio_source_for_job(job)
    assert result.selected_type == "speech_audio"


# ── 13. empty job safe ────────────────────────────────────────────────────────

def test_empty_job_safe():
    job = SimpleNamespace()
    result = select_rms_energy_audio_source_for_job(job)
    assert result.status == "unavailable"
    # must not raise


# ── 14. checked_sources records all candidates ───────────────────────────────

def test_checked_sources_records_all_candidates(tmp_path):
    speech = tmp_path / "speech.wav"
    speech.write_bytes(b"RIFF" + b"\x00" * 36)
    manifest = {
        "analysis_audio_path": str(tmp_path / "analysis.wav"),  # missing
        "speech_audio_path": str(speech),
    }
    result = select_rms_energy_audio_source(preprocessing_manifest=manifest)
    assert len(result.checked_sources) >= 2
    analysis_entry = next(
        (s for s in result.checked_sources if s.get("source_type") == "analysis_audio"),
        None,
    )
    assert analysis_entry is not None
    assert analysis_entry["accepted"] is False
    speech_entry = next(
        (s for s in result.checked_sources if s.get("source_type") == "speech_audio"),
        None,
    )
    assert speech_entry is not None
    assert speech_entry["accepted"] is True


# ── 15. BOM and newline hygiene ───────────────────────────────────────────────

def test_rms_energy_audio_source_selector_files_have_no_bom_and_end_with_newline():
    files = [
        os.path.join(_REPO_ROOT, "models", "rms_energy_audio_source.py"),
        os.path.join(_REPO_ROOT, "core", "rms_energy_audio_source_selector.py"),
        os.path.join(_REPO_ROOT, "tests", "test_rms_energy_audio_source_selector_smoke.py"),
    ]
    for path in files:
        raw = open(path, "rb").read()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {path}"
        assert raw.endswith(b"\n"), f"Missing trailing newline in {path}"
