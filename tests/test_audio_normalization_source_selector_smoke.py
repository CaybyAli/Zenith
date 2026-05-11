from __future__ import annotations

import json
import os
from types import SimpleNamespace

import pytest

from models.audio_normalization_source import AudioNormalizationSourceSelection
from core.audio_normalization_source_selector import (
    is_wav_path,
    path_exists,
    extract_manifest_audio_targets,
    select_audio_normalization_source,
    select_audio_normalization_source_for_job,
)

_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_THIS_DIR)


# ── 1. roundtrip ──────────────────────────────────────────────────────────────

def test_audio_normalization_source_selection_roundtrip():
    sel = AudioNormalizationSourceSelection(
        status="selected",
        selected_path="/tmp/analysis.wav",
        selected_type="analysis_audio",
        source_priority=["analysis_audio", "speech_audio", "music_reference_audio", "original_wav"],
        checked_sources=[{
            "type": "analysis_audio",
            "path": "/tmp/analysis.wav",
            "exists": True,
            "is_wav": True,
            "usable": True,
            "reason": "ok",
        }],
        requires_extraction=False,
        require_existing_file=True,
        is_wav_source=True,
        source_exists=True,
        original_source_path="/tmp/original.mp4",
        preprocessing_manifest_path="/tmp/manifest.json",
        recommendation="analyze_selected_wav",
        warnings=[],
        errors=[],
        metadata={"job_id": "abc123"},
    )
    d = sel.to_dict()
    restored = AudioNormalizationSourceSelection.from_dict(d)
    assert restored.status == "selected"
    assert restored.selected_path == "/tmp/analysis.wav"
    assert restored.selected_type == "analysis_audio"
    assert restored.is_wav_source is True
    assert restored.source_exists is True
    assert restored.requires_extraction is False
    assert restored.require_existing_file is True
    assert restored.original_source_path == "/tmp/original.mp4"
    assert restored.preprocessing_manifest_path == "/tmp/manifest.json"
    assert restored.recommendation == "analyze_selected_wav"
    assert restored.source_priority == ["analysis_audio", "speech_audio", "music_reference_audio", "original_wav"]
    assert len(restored.checked_sources) == 1
    assert restored.metadata == {"job_id": "abc123"}


# ── 2. is_wav_path ────────────────────────────────────────────────────────────

def test_is_wav_path():
    assert is_wav_path("test.wav") is True
    assert is_wav_path("TEST.WAV") is True
    assert is_wav_path("analysis.WAV") is True
    assert is_wav_path("test.mp4") is False
    assert is_wav_path("test.m4a") is False
    assert is_wav_path("test.mkv") is False
    assert is_wav_path(None) is False
    assert is_wav_path("") is False
    assert is_wav_path(42) is False


# ── 3. extract_manifest_audio_targets from dict ───────────────────────────────

def test_extract_manifest_audio_targets_from_dict():
    manifest = {
        "audio_extraction_plan": {
            "targets": [
                {"target_type": "analysis_audio", "output_path": "/audio/analysis.wav"},
                {"target_type": "speech_audio", "output_path": "/audio/speech.wav"},
                {"target_type": "music_reference_audio", "output_path": "/audio/music.wav"},
            ]
        }
    }
    result = extract_manifest_audio_targets(manifest)
    assert result.get("analysis_audio") == "/audio/analysis.wav"
    assert result.get("speech_audio") == "/audio/speech.wav"
    assert result.get("music_reference_audio") == "/audio/music.wav"


# ── 4. analysis_audio preferred when existing ─────────────────────────────────

def test_select_analysis_audio_preferred_existing(tmp_path):
    wav = tmp_path / "analysis.wav"
    wav.write_bytes(b"RIFF" + b"\x00" * 36)
    manifest = {"analysis_audio_path": str(wav)}
    result = select_audio_normalization_source(preprocessing_manifest=manifest)
    assert result.status == "selected"
    assert result.selected_type == "analysis_audio"
    assert result.selected_path == str(wav)
    assert result.is_wav_source is True
    assert result.source_exists is True
    assert result.recommendation == "analyze_selected_wav"


# ── 5. speech_audio fallback when analysis absent ─────────────────────────────

def test_select_speech_audio_fallback_existing(tmp_path):
    wav = tmp_path / "speech.wav"
    wav.write_bytes(b"RIFF" + b"\x00" * 36)
    manifest = {"speech_audio_path": str(wav)}
    result = select_audio_normalization_source(preprocessing_manifest=manifest)
    assert result.status == "selected"
    assert result.selected_type == "speech_audio"
    assert result.selected_path == str(wav)
    assert result.is_wav_source is True


# ── 6. music_reference fallback warns ────────────────────────────────────────

def test_music_reference_audio_fallback_warns(tmp_path):
    wav = tmp_path / "music_ref.wav"
    wav.write_bytes(b"RIFF" + b"\x00" * 36)
    manifest = {"music_reference_audio_path": str(wav)}
    result = select_audio_normalization_source(preprocessing_manifest=manifest)
    assert result.status == "selected_fallback"
    assert result.selected_type == "music_reference_audio"
    assert "music_reference_audio_used_for_normalization" in result.warnings
    assert result.is_wav_source is True


# ── 7. missing analysis_audio blocks for preprocessing ───────────────────────

def test_missing_analysis_audio_blocks_for_preprocessing(tmp_path):
    planned = tmp_path / "analysis.wav"  # intentionally not created
    manifest = {"analysis_audio_path": str(planned)}
    result = select_audio_normalization_source(preprocessing_manifest=manifest)
    assert result.status == "missing_preprocessed_audio"
    assert result.selected_type == "planned_analysis_audio"
    assert result.selected_path == str(planned)
    assert result.requires_extraction is True
    assert result.recommendation == "generate_preprocessed_audio"


# ── 8. original WAV fallback existing ────────────────────────────────────────

def test_original_wav_fallback_existing(tmp_path):
    wav = tmp_path / "original.wav"
    wav.write_bytes(b"RIFF" + b"\x00" * 36)
    result = select_audio_normalization_source(original_source_path=str(wav))
    assert result.status == "selected_fallback"
    assert result.selected_type == "original_wav"
    assert result.selected_path == str(wav)
    assert "original_wav_used_for_normalization" in result.warnings
    assert result.is_wav_source is True


# ── 9. original MP4 rejected, requires extraction ────────────────────────────

def test_original_mp4_rejected_requires_extraction(tmp_path):
    mp4 = tmp_path / "video.mp4"
    mp4.write_bytes(b"\x00" * 8)
    result = select_audio_normalization_source(original_source_path=str(mp4))
    assert result.status == "skipped_unsupported_source"
    assert result.selected_type == "unsupported_original_source"
    assert result.selected_path == str(mp4)
    assert result.requires_extraction is True
    assert result.recommendation == "extract_audio_first"


# ── 10. non-WAV preprocessed audio skipped ───────────────────────────────────

def test_non_wav_preprocessed_audio_skipped(tmp_path):
    speech = tmp_path / "speech.wav"
    speech.write_bytes(b"RIFF" + b"\x00" * 36)
    manifest = {
        "analysis_audio_path": str(tmp_path / "analysis.m4a"),
        "speech_audio_path": str(speech),
    }
    result = select_audio_normalization_source(preprocessing_manifest=manifest)
    assert result.selected_type == "speech_audio"
    analysis_entry = next(
        (s for s in result.checked_sources if s.get("type") == "analysis_audio"),
        None,
    )
    assert analysis_entry is not None
    assert analysis_entry["usable"] is False
    assert analysis_entry["reason"] == "non_wav_preprocessed_audio"


# ── 11. unavailable when no sources ──────────────────────────────────────────

def test_unavailable_when_no_sources():
    result = select_audio_normalization_source()
    assert result.status == "unavailable"
    assert "no_audio_normalization_source_available" in result.errors
    assert result.recommendation == "no_audio_source_available"


# ── 12. for_job reads preprocessing_manifest dict ────────────────────────────

def test_for_job_reads_preprocessing_manifest_dict(tmp_path):
    analysis = tmp_path / "analysis.wav"
    analysis.write_bytes(b"RIFF" + b"\x00" * 36)
    job = SimpleNamespace(
        preprocessing_manifest={
            "audio_extraction_plan": {
                "targets": [
                    {"target_type": "analysis_audio", "output_path": str(analysis)}
                ]
            }
        }
    )
    result = select_audio_normalization_source_for_job(job)
    assert result.status == "selected"
    assert result.selected_type == "analysis_audio"
    assert result.selected_path == str(analysis)


# ── 13. for_job reads manifest_path JSON ─────────────────────────────────────

def test_for_job_reads_manifest_path_json(tmp_path):
    analysis = tmp_path / "analysis.wav"
    analysis.write_bytes(b"RIFF" + b"\x00" * 36)
    manifest_data = {"analysis_audio_path": str(analysis)}
    manifest_file = tmp_path / "manifest.json"
    manifest_file.write_text(json.dumps(manifest_data), encoding="utf-8")
    job = SimpleNamespace(preprocessing_manifest_path=str(manifest_file))
    result = select_audio_normalization_source_for_job(job)
    assert result.status == "selected"
    assert result.selected_type == "analysis_audio"
    assert result.preprocessing_manifest_path == str(manifest_file)


# ── 14. for_job original source fallback ─────────────────────────────────────

def test_for_job_original_source_fallback(tmp_path):
    wav = tmp_path / "original.wav"
    wav.write_bytes(b"RIFF" + b"\x00" * 36)
    job = SimpleNamespace(raw_video_path=str(wav))
    result = select_audio_normalization_source_for_job(job)
    assert result.status == "selected_fallback"
    assert result.selected_type == "original_wav"
    assert "original_wav_used_for_normalization" in result.warnings


# ── 15. empty job safe ────────────────────────────────────────────────────────

def test_empty_job_safe():
    job = SimpleNamespace()
    result = select_audio_normalization_source_for_job(job)
    assert result.status in ("unavailable", "skipped_unsupported_source")
    # must not raise


# ── 16. checked_sources documents all candidates ─────────────────────────────

def test_checked_sources_are_documented(tmp_path):
    music = tmp_path / "music_ref.wav"
    music.write_bytes(b"RIFF" + b"\x00" * 36)
    manifest = {
        "analysis_audio_path": str(tmp_path / "analysis.m4a"),
        "speech_audio_path": str(tmp_path / "speech.m4a"),
        "music_reference_audio_path": str(music),
    }
    result = select_audio_normalization_source(preprocessing_manifest=manifest)
    assert len(result.checked_sources) >= 3
    types_found = {s["type"] for s in result.checked_sources}
    assert "analysis_audio" in types_found
    assert "speech_audio" in types_found
    assert "music_reference_audio" in types_found


# ── 17. BOM and newline hygiene ───────────────────────────────────────────────

def test_audio_normalization_source_selector_files_have_no_bom_and_end_with_newline():
    files = [
        os.path.join(_REPO_ROOT, "models", "audio_normalization_source.py"),
        os.path.join(_REPO_ROOT, "core", "audio_normalization_source_selector.py"),
        os.path.join(_REPO_ROOT, "tests", "test_audio_normalization_source_selector_smoke.py"),
    ]
    for path in files:
        raw = open(path, "rb").read()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {path}"
        assert raw.endswith(b"\n"), f"Missing trailing newline in {path}"
