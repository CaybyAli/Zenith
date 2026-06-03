from __future__ import annotations

import json

from core.caption_transcription_config import resolve_caption_whisper_model


def test_caption_model_default_final_uses_large_v3(tmp_path, monkeypatch):
    config_dir = tmp_path / "video_configs"
    config_dir.mkdir()
    (config_dir / "caption_transcription.json").write_text(
        json.dumps(
            {
                "caption_power_profile": "final",
                "caption_whisper_models": {
                    "fast": "base",
                    "debug": "base",
                    "medium": "medium",
                    "quality": "large-v3",
                    "final": "large-v3",
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.delenv("ZENITH_CAPTION_WHISPER_MODEL", raising=False)
    monkeypatch.delenv("ZENITH_CAPTION_POWER_PROFILE", raising=False)

    resolved = resolve_caption_whisper_model(config_dir=config_dir)

    assert resolved.power_profile == "final"
    assert resolved.model_name == "large-v3"
    assert resolved.source == "config:caption_transcription"


def test_caption_model_fast_debug_uses_base(tmp_path, monkeypatch):
    config_dir = tmp_path / "video_configs"
    config_dir.mkdir()
    (config_dir / "caption_transcription.json").write_text(
        json.dumps(
            {
                "caption_power_profile": "final",
                "caption_whisper_models": {
                    "fast": "base",
                    "debug": "base",
                    "medium": "medium",
                    "final": "large-v3",
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setenv("ZENITH_CAPTION_POWER_PROFILE", "debug")
    monkeypatch.delenv("ZENITH_CAPTION_WHISPER_MODEL", raising=False)

    resolved = resolve_caption_whisper_model(config_dir=config_dir)

    assert resolved.power_profile == "debug"
    assert resolved.model_name == "base"


def test_caption_model_medium_profile_is_available(tmp_path, monkeypatch):
    config_dir = tmp_path / "video_configs"
    config_dir.mkdir()
    (config_dir / "caption_transcription.json").write_text(
        json.dumps(
            {
                "caption_power_profile": "medium",
                "caption_whisper_models": {
                    "fast": "base",
                    "medium": "medium",
                    "final": "large-v3",
                },
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.delenv("ZENITH_CAPTION_WHISPER_MODEL", raising=False)
    monkeypatch.delenv("ZENITH_CAPTION_POWER_PROFILE", raising=False)

    resolved = resolve_caption_whisper_model(config_dir=config_dir)

    assert resolved.power_profile == "medium"
    assert resolved.model_name == "medium"


def test_caption_direct_model_env_override_wins(tmp_path, monkeypatch):
    config_dir = tmp_path / "video_configs"
    config_dir.mkdir()
    (config_dir / "caption_transcription.json").write_text(
        json.dumps({"caption_power_profile": "final"}),
        encoding="utf-8",
    )

    monkeypatch.setenv("ZENITH_CAPTION_WHISPER_MODEL", "medium")
    monkeypatch.setenv("ZENITH_CAPTION_POWER_PROFILE", "final")

    resolved = resolve_caption_whisper_model(config_dir=config_dir)

    assert resolved.model_name == "medium"
    assert resolved.source == "env:ZENITH_CAPTION_WHISPER_MODEL"
