from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from models.silence_audio_source import SilenceAudioSourceSelection
from core.silence_audio_source_selector import (
    select_silence_audio_source,
    select_silence_audio_source_for_job,
)


# ---------------------------------------------------------------------------
# Model round-trip
# ---------------------------------------------------------------------------

def test_silence_audio_source_selection_roundtrip() -> None:
    sel = SilenceAudioSourceSelection(
        selected_path="/audio/analysis.wav",
        source_type="analysis_audio",
        status="selected",
        exists=True,
        checked_paths=["/audio/analysis.wav"],
        preferred_order=["analysis_audio", "speech_audio"],
        warnings=["some_warning"],
        errors=[],
        recommendation="use_selected",
        metadata={"key": "val"},
    )
    d = sel.to_dict()
    restored = SilenceAudioSourceSelection.from_dict(d)
    assert restored.selected_path == sel.selected_path
    assert restored.source_type == sel.source_type
    assert restored.status == sel.status
    assert restored.exists == sel.exists
    assert restored.checked_paths == sel.checked_paths
    assert restored.preferred_order == sel.preferred_order
    assert restored.warnings == sel.warnings
    assert restored.errors == sel.errors
    assert restored.recommendation == sel.recommendation
    assert restored.metadata == sel.metadata


# ---------------------------------------------------------------------------
# Source priority tests
# ---------------------------------------------------------------------------

def test_selects_existing_analysis_audio_first(tmp_path: Path) -> None:
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    analysis = audio_dir / "analysis.wav"
    analysis.write_bytes(b"")
    speech = audio_dir / "speech.wav"
    speech.write_bytes(b"")

    manifest = {
        "analysis_audio_path": str(analysis),
        "speech_audio_path": str(speech),
        "music_audio_path": "",
    }

    result = select_silence_audio_source(preprocessing_manifest=manifest)
    assert result.selected_path == str(analysis)
    assert result.source_type == "analysis_audio"
    assert result.status == "selected"
    assert result.exists is True
    assert result.recommendation == "use_selected"


def test_selects_existing_speech_audio_when_analysis_missing(tmp_path: Path) -> None:
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    speech = audio_dir / "speech.wav"
    speech.write_bytes(b"")

    manifest = {
        "analysis_audio_path": str(tmp_path / "audio" / "analysis_missing.wav"),
        "speech_audio_path": str(speech),
        "music_audio_path": "",
    }

    result = select_silence_audio_source(preprocessing_manifest=manifest)
    assert result.selected_path == str(speech)
    assert result.source_type == "speech_audio"
    assert result.status in ("selected", "selected_fallback")
    assert result.exists is True


def test_uses_original_source_as_fallback_when_preprocessed_missing(tmp_path: Path) -> None:
    original = tmp_path / "video.mp4"
    original.write_bytes(b"")

    manifest = {
        "analysis_audio_path": str(tmp_path / "missing_analysis.wav"),
        "speech_audio_path": str(tmp_path / "missing_speech.wav"),
        "music_audio_path": "",
    }

    result = select_silence_audio_source(
        preprocessing_manifest=manifest,
        fallback_source_path=str(original),
    )
    assert result.source_type == "original_source"
    assert result.status == "selected_fallback"
    assert result.exists is True
    assert "original_source_used_for_silence_detection" in result.warnings


def test_require_existing_false_selects_planned_analysis_audio(tmp_path: Path) -> None:
    planned = str(tmp_path / "audio" / "analysis.wav")

    manifest = {
        "analysis_audio_path": planned,
        "speech_audio_path": "",
        "music_audio_path": "",
    }

    result = select_silence_audio_source(
        preprocessing_manifest=manifest,
        require_existing_file=False,
    )
    assert result.selected_path == planned
    assert result.source_type == "analysis_audio"
    assert result.status == "missing_preprocessed_audio"
    assert result.recommendation == "extract_audio_first"
    assert result.exists is False


def test_no_audio_source_available_returns_unavailable() -> None:
    result = select_silence_audio_source(
        preprocessing_manifest=None,
        fallback_source_path=None,
    )
    assert result.selected_path is None
    assert result.status == "unavailable"
    assert "no_silence_audio_source_available" in result.errors
    assert result.recommendation == "reject_or_retry"


def test_music_reference_audio_gets_warning_if_used(tmp_path: Path) -> None:
    music = tmp_path / "music.wav"
    music.write_bytes(b"")

    manifest = {
        "analysis_audio_path": str(tmp_path / "missing_analysis.wav"),
        "speech_audio_path": str(tmp_path / "missing_speech.wav"),
        "music_audio_path": str(music),
    }

    result = select_silence_audio_source(preprocessing_manifest=manifest)
    assert result.source_type == "music_reference_audio"
    assert "music_reference_audio_used_for_silence_detection" in result.warnings
    assert result.exists is True


# ---------------------------------------------------------------------------
# Job-based selection
# ---------------------------------------------------------------------------

def test_select_silence_audio_source_for_job_uses_job_manifest(tmp_path: Path) -> None:
    audio_dir = tmp_path / "audio"
    audio_dir.mkdir()
    analysis = audio_dir / "analysis.wav"
    analysis.write_bytes(b"")

    manifest: dict[str, Any] = {
        "analysis_audio_path": str(analysis),
        "speech_audio_path": "",
        "music_audio_path": "",
    }

    job = SimpleNamespace(
        preprocessing_manifest=manifest,
        raw_video_path=None,
    )

    result = select_silence_audio_source_for_job(job)
    assert result.source_type == "analysis_audio"
    assert result.selected_path == str(analysis)
    assert result.status == "selected"


def test_select_silence_audio_source_for_job_falls_back_to_raw_video(tmp_path: Path) -> None:
    raw_video = tmp_path / "video.mp4"
    raw_video.write_bytes(b"")

    job = SimpleNamespace(
        preprocessing_manifest={},
        raw_video_path=str(raw_video),
    )

    result = select_silence_audio_source_for_job(job)
    assert result.source_type == "original_source"
    assert result.status == "selected_fallback"
    assert result.exists is True
    assert "original_source_used_for_silence_detection" in result.warnings


# ---------------------------------------------------------------------------
# BOM / Newline hygiene
# ---------------------------------------------------------------------------

def test_silence_audio_source_selector_files_have_no_bom_and_end_with_newline() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    files = [
        repo_root / "models" / "silence_audio_source.py",
        repo_root / "core" / "silence_audio_source_selector.py",
        repo_root / "tests" / "test_silence_audio_source_selector_smoke.py",
    ]
    for fpath in files:
        raw = fpath.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {fpath}"
        assert raw.endswith(b"\n"), f"Missing trailing newline in {fpath}"
