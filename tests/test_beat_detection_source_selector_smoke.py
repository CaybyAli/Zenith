from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from core.beat_detection_source_selector import (
    extract_manifest_beat_audio_targets,
    is_wav_path,
    path_exists,
    select_beat_detection_source,
    select_beat_detection_source_for_job,
)
from models.beat_detection_source import BeatDetectionSourceSelection


def _touch(path: Path) -> Path:
    path.write_bytes(b"tiny")
    return path


def test_beat_detection_source_selection_roundtrip() -> None:
    selection = BeatDetectionSourceSelection(
        status="selected",
        selected_path="music.wav",
        selected_type="music_reference_audio",
        source_priority=["music_reference_audio", "analysis_audio", "original_wav"],
        checked_sources=[
            {
                "type": "music_reference_audio",
                "path": "music.wav",
                "exists": True,
                "is_wav": True,
                "usable": True,
                "reason": "selected_wav_source",
            }
        ],
        requires_extraction=False,
        require_existing_file=True,
        is_wav_source=True,
        source_exists=True,
        original_source_path="original.mp4",
        preprocessing_manifest_path="manifest.json",
        recommendation="analyze_selected_wav",
        warnings=["demo_warning"],
        errors=[],
        metadata={"kind": "roundtrip"},
    )

    loaded = BeatDetectionSourceSelection.from_dict(selection.to_dict())

    assert loaded.status == "selected"
    assert loaded.selected_path == "music.wav"
    assert loaded.selected_type == "music_reference_audio"
    assert loaded.source_priority == ["music_reference_audio", "analysis_audio", "original_wav"]
    assert loaded.checked_sources[0]["reason"] == "selected_wav_source"
    assert loaded.recommendation == "analyze_selected_wav"
    assert loaded.metadata["kind"] == "roundtrip"


def test_is_wav_path_and_path_exists(tmp_path: Path) -> None:
    wav_path = _touch(tmp_path / "Music.WAV")
    mp4_path = _touch(tmp_path / "video.mp4")

    assert is_wav_path(wav_path) is True
    assert is_wav_path(str(wav_path)) is True
    assert is_wav_path(mp4_path) is False
    assert is_wav_path(None) is False
    assert is_wav_path("") is False

    assert path_exists(wav_path) is True
    assert path_exists(tmp_path / "missing.wav") is False
    assert path_exists(None) is False
    assert path_exists("") is False


def test_extract_manifest_beat_audio_targets_from_dict() -> None:
    manifest = {
        "audio_extraction_plan": {
            "targets": [
                {
                    "target_type": "music_reference_audio",
                    "output_path": "preprocessed/music.wav",
                },
                {
                    "target_type": "analysis_audio",
                    "path": "preprocessed/analysis.wav",
                },
                {
                    "target_type": "voice_audio",
                    "output_path": "preprocessed/voice.wav",
                },
            ]
        }
    }

    targets = extract_manifest_beat_audio_targets(manifest)

    assert targets == {
        "music_reference_audio": "preprocessed/music.wav",
        "analysis_audio": "preprocessed/analysis.wav",
    }


def test_music_reference_audio_preferred_existing(tmp_path: Path) -> None:
    music_path = _touch(tmp_path / "music.wav")
    analysis_path = _touch(tmp_path / "analysis.wav")
    manifest = {
        "music_reference_audio_path": str(music_path),
        "analysis_audio_path": str(analysis_path),
    }

    selection = select_beat_detection_source(preprocessing_manifest=manifest)

    assert selection.status == "selected"
    assert selection.selected_type == "music_reference_audio"
    assert selection.selected_path == str(music_path)
    assert selection.recommendation == "analyze_selected_wav"
    assert selection.requires_extraction is False


def test_analysis_audio_fallback_existing(tmp_path: Path) -> None:
    analysis_path = _touch(tmp_path / "analysis.wav")
    manifest = {"analysis_audio_path": str(analysis_path)}

    selection = select_beat_detection_source(preprocessing_manifest=manifest)

    assert selection.status == "selected_fallback"
    assert selection.selected_type == "analysis_audio"
    assert selection.selected_path == str(analysis_path)
    assert selection.recommendation == "review_warning"


def test_analysis_audio_fallback_warns(tmp_path: Path) -> None:
    analysis_path = _touch(tmp_path / "analysis.wav")
    manifest = {"analysis_audio_path": str(analysis_path)}

    selection = select_beat_detection_source(preprocessing_manifest=manifest)

    assert "analysis_audio_used_for_beat_detection" in selection.warnings
    assert selection.errors == []


def test_missing_music_reference_audio_blocks(tmp_path: Path) -> None:
    missing_music_path = tmp_path / "missing_music.wav"
    analysis_path = _touch(tmp_path / "analysis.wav")
    manifest = {
        "music_reference_audio_path": str(missing_music_path),
        "analysis_audio_path": str(analysis_path),
    }

    selection = select_beat_detection_source(preprocessing_manifest=manifest)

    assert selection.status == "missing_preprocessed_audio"
    assert selection.selected_type == "planned_music_reference_audio"
    assert selection.selected_path == str(missing_music_path)
    assert selection.requires_extraction is True
    assert selection.recommendation == "generate_preprocessed_audio"


def test_original_wav_fallback_existing(tmp_path: Path) -> None:
    original_wav = _touch(tmp_path / "original.wav")

    selection = select_beat_detection_source(original_source_path=str(original_wav))

    assert selection.status == "selected_fallback"
    assert selection.selected_type == "original_wav"
    assert selection.selected_path == str(original_wav)
    assert "original_wav_used_for_beat_detection" in selection.warnings


def test_original_mp4_rejected_requires_extraction(tmp_path: Path) -> None:
    original_mp4 = _touch(tmp_path / "original.mp4")

    selection = select_beat_detection_source(original_source_path=str(original_mp4))

    assert selection.status == "skipped_unsupported_source"
    assert selection.selected_type == "unsupported_original_source"
    assert selection.selected_path == str(original_mp4)
    assert selection.requires_extraction is True
    assert selection.recommendation == "extract_audio_first"


def test_non_wav_music_reference_skipped_to_analysis(tmp_path: Path) -> None:
    music_mp3 = _touch(tmp_path / "music.mp3")
    analysis_wav = _touch(tmp_path / "analysis.wav")
    manifest = {
        "music_reference_audio_path": str(music_mp3),
        "analysis_audio_path": str(analysis_wav),
    }

    selection = select_beat_detection_source(preprocessing_manifest=manifest)

    assert selection.status == "selected_fallback"
    assert selection.selected_type == "analysis_audio"
    assert selection.selected_path == str(analysis_wav)

    music_check = selection.checked_sources[0]
    assert music_check["type"] == "music_reference_audio"
    assert music_check["reason"] == "non_wav_preprocessed_audio"
    assert music_check["usable"] is False


def test_unavailable_when_no_sources() -> None:
    selection = select_beat_detection_source()

    assert selection.status == "unavailable"
    assert selection.selected_type == "none"
    assert selection.selected_path is None
    assert selection.recommendation == "no_audio_source_available"
    assert "no_beat_detection_source_available" in selection.errors


def test_for_job_reads_preprocessing_manifest_dict(tmp_path: Path) -> None:
    music_path = _touch(tmp_path / "music.wav")
    job = SimpleNamespace(
        preprocessing_manifest={
            "music_reference_audio_path": str(music_path),
        }
    )

    selection = select_beat_detection_source_for_job(job)

    assert selection.status == "selected"
    assert selection.selected_type == "music_reference_audio"
    assert selection.selected_path == str(music_path)


def test_for_job_reads_manifest_path_json(tmp_path: Path) -> None:
    music_path = _touch(tmp_path / "music.wav")
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(
        json.dumps({"music_reference_audio_path": str(music_path)}),
        encoding="utf-8",
    )

    job = SimpleNamespace(preprocessing_manifest_path=str(manifest_path))

    selection = select_beat_detection_source_for_job(job)

    assert selection.status == "selected"
    assert selection.selected_type == "music_reference_audio"
    assert selection.selected_path == str(music_path)
    assert selection.preprocessing_manifest_path == str(manifest_path)


def test_for_job_original_source_fallback(tmp_path: Path) -> None:
    original_wav = _touch(tmp_path / "original.wav")
    job = SimpleNamespace(raw_video_path=str(original_wav))

    selection = select_beat_detection_source_for_job(job)

    assert selection.status == "selected_fallback"
    assert selection.selected_type == "original_wav"
    assert selection.selected_path == str(original_wav)


def test_empty_job_safe() -> None:
    job = SimpleNamespace()

    selection = select_beat_detection_source_for_job(job)

    assert selection.status == "unavailable"
    assert selection.selected_type == "none"
    assert "no_beat_detection_source_available" in selection.errors


def test_checked_sources_documented(tmp_path: Path) -> None:
    original_mp4 = _touch(tmp_path / "clip.mp4")

    selection = select_beat_detection_source(original_source_path=str(original_mp4))

    assert selection.checked_sources
    assert all("type" in item for item in selection.checked_sources)
    assert all("path" in item for item in selection.checked_sources)
    assert all("exists" in item for item in selection.checked_sources)
    assert all("is_wav" in item for item in selection.checked_sources)
    assert all("usable" in item for item in selection.checked_sources)
    assert all("reason" in item for item in selection.checked_sources)


def test_beat_detection_source_selector_files_have_no_bom_and_end_with_newline() -> None:
    paths = [
        Path("models/beat_detection_source.py"),
        Path("core/beat_detection_source_selector.py"),
        Path("tests/test_beat_detection_source_selector_smoke.py"),
    ]

    for path in paths:
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"{path} has BOM"
        assert data.endswith(b"\n"), f"{path} does not end with newline"
