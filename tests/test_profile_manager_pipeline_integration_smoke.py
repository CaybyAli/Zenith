"""
Smoke-Test für ProfileManager Pipeline Integration — 2B-01-B
"""

import json
from pathlib import Path
from types import SimpleNamespace

from core.gaming_pipeline import (
    _load_json_profile_for_job,
    _write_profile_snapshot,
    resolve_track_roles,
)


REQUIRED_SNAPSHOT_FIELDS = {
    "job_id",
    "profile_id",
    "channel_type",
    "quality_mode",
    "cut_aggressiveness",
    "source_aspect_ratio",
    "target_format",
    "reframing_mode",
    "music_enabled",
    "camera_zoom_enabled",
    "gameplay_zoom_enabled",
    "profile_version",
}


def _fake_job(job_id="job_profile_pipeline_smoke", channel_type="gaming_main"):
    return SimpleNamespace(
        job_id=job_id,
        channel_type=SimpleNamespace(value=channel_type),
    )


def test_pipeline_loads_gaming_main_json_profile():
    job = _fake_job(channel_type="gaming_main")

    profile = _load_json_profile_for_job(job)

    assert profile["profile_id"] == "gaming_main"
    assert profile["quality_mode"] == "pro"
    assert profile["cut_aggressiveness"] == 0.85
    assert profile["music_enabled"] is True


def test_pipeline_profile_has_gaming_main_format_values():
    job = _fake_job(channel_type="gaming_main")

    profile = _load_json_profile_for_job(job)

    assert profile["source_aspect_ratio"] == "32:9"
    assert profile["target_format"] == "16:9"
    assert profile["reframing_mode"] == "intelligent_crop"
    assert profile["camera_zoom_enabled"] is True
    assert profile["gameplay_zoom_enabled"] is True


def test_pipeline_writes_profile_snapshot_payload(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    job = _fake_job(
        job_id="job_profile_snapshot_smoke",
        channel_type="gaming_main",
    )
    profile = _load_json_profile_for_job(job)

    snapshot_path = _write_profile_snapshot(job, profile)
    snapshot_file = Path(snapshot_path)

    assert snapshot_file.exists()

    payload = json.loads(snapshot_file.read_text(encoding="utf-8"))

    assert REQUIRED_SNAPSHOT_FIELDS.issubset(payload.keys())
    assert payload["job_id"] == "job_profile_snapshot_smoke"
    assert payload["profile_id"] == "gaming_main"
    assert payload["channel_type"] == "gaming_main"
    assert payload["quality_mode"] == "pro"
    assert payload["cut_aggressiveness"] == 0.85
    assert payload["source_aspect_ratio"] == "32:9"
    assert payload["target_format"] == "16:9"
    assert payload["reframing_mode"] == "intelligent_crop"
    assert payload["music_enabled"] is True
    assert payload["camera_zoom_enabled"] is True
    assert payload["gameplay_zoom_enabled"] is True
    assert payload["profile_version"] == "1.0.0"


def test_pipeline_profile_fallback_does_not_crash(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    job = _fake_job(
        job_id="job_profile_fallback_smoke",
        channel_type="unknown_profile_xyz",
    )

    profile = _load_json_profile_for_job(job)
    snapshot_path = _write_profile_snapshot(job, profile)

    assert profile["profile_id"] == "unknown_profile_xyz"
    assert profile["quality_mode"] == "balanced"
    assert profile["_is_fallback"] is True
    assert Path(snapshot_path).exists()


def test_resolve_track_roles_prefers_profile_audio_tracks():
    profile = {
        "audio_tracks": [
            {
                "role": "owner",
                "audio_track": "mic",
                "speaker": "ali",
                "ffmpeg_audio_index": "0:a:0",
                "transcribe_for_captions": True,
            },
            {
                "role": "friend",
                "audio_track": "discord",
                "speaker": "friend",
                "ffmpeg_audio_index": "0:a:1",
                "transcribe_for_captions": True,
            },
        ],
    }

    roles = resolve_track_roles("inbox/gaming_main/raw.mp4", profile)

    assert roles is not None
    assert [(role.role, role.audio_track, role.speaker) for role in roles] == [
        ("owner", "mic", "ali"),
        ("friend", "discord", "friend"),
    ]
    assert [role.ffmpeg_audio_index for role in roles] == [0, 1]


def test_resolve_track_roles_uses_pair_truth_only_for_learning_corpus_pairs():
    roles = resolve_track_roles(
        "learning_corpus/pairs/pair_009/raw.mp4",
        {},
    )

    assert roles is not None
    assert [(role.ffmpeg_audio_index, role.role, role.audio_track, role.speaker) for role in roles] == [
        (0, "owner", "mic", "ali"),
        (1, "friend", "discord", "friend"),
        (2, "game", "ingame", "unknown"),
        (3, "still", "silent", "unknown"),
    ]
    assert [role.transcribe_for_captions for role in roles] == [True, True, False, False]
