from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


DEFAULT_CAPTION_POWER_PROFILE = "final"
DEFAULT_CAPTION_HIGHLIGHT_TIMING_NUDGE_SECONDS = -0.15

DEFAULT_CAPTION_WHISPER_MODELS: dict[str, str] = {
    "fast": "base",
    "debug": "base",
    "medium": "medium",
    "quality": "large-v3",
    "final": "large-v3",
    "max_quality": "large-v3",
}


@dataclass(frozen=True)
class CaptionWhisperModelResolution:
    power_profile: str
    model_name: str
    config_path: str | None
    source: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "power_profile": self.power_profile,
            "model_name": self.model_name,
            "config_path": self.config_path,
            "source": self.source,
        }


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError(f"Caption transcription config must be an object: {path}")
    return dict(data)


def _load_caption_transcription_config(config_dir: str | Path = "video_configs") -> tuple[dict[str, Any], Path | None]:
    path = Path(config_dir) / "caption_transcription.json"
    if not path.exists():
        return {}, None
    return _read_json(path), path


def _normalise_profile(value: object) -> str:
    text = str(value or "").strip().lower().replace("-", "_")

    aliases = {
        "fast": "fast",
        "debug": "debug",
        "base": "fast",
        "medium": "medium",
        "quality": "quality",
        "final": "final",
        "real": "final",
        "render": "final",
        "large": "final",
        "large_v3": "final",
        "large-v3": "final",
        "max": "max_quality",
        "max_quality": "max_quality",
    }

    return aliases.get(text, text or DEFAULT_CAPTION_POWER_PROFILE)


def _model_map_from_config(config: Mapping[str, Any]) -> dict[str, str]:
    model_map = dict(DEFAULT_CAPTION_WHISPER_MODELS)

    raw = config.get("caption_whisper_models")
    if isinstance(raw, Mapping):
        for key, value in raw.items():
            key_text = _normalise_profile(key)
            value_text = str(value or "").strip()
            if key_text and value_text:
                model_map[key_text] = value_text

    return model_map


def resolve_caption_whisper_model(
    *,
    source_video_path: str | Path | None = None,
    config_dir: str | Path = "video_configs",
    power_profile: str | None = None,
) -> CaptionWhisperModelResolution:
    direct_model = str(os.getenv("ZENITH_CAPTION_WHISPER_MODEL") or "").strip()
    if direct_model:
        profile = _normalise_profile(power_profile or os.getenv("ZENITH_CAPTION_POWER_PROFILE") or "direct")
        return CaptionWhisperModelResolution(
            power_profile=profile,
            model_name=direct_model,
            config_path=None,
            source="env:ZENITH_CAPTION_WHISPER_MODEL",
        )

    config, config_path = _load_caption_transcription_config(config_dir)
    model_map = _model_map_from_config(config)

    profile = _normalise_profile(
        power_profile
        or os.getenv("ZENITH_CAPTION_POWER_PROFILE")
        or config.get("caption_power_profile")
        or DEFAULT_CAPTION_POWER_PROFILE
    )

    model_name = model_map.get(profile)
    if not model_name:
        raise ValueError(
            f"Unknown caption power profile {profile!r}. "
            f"Known profiles: {sorted(model_map)}"
        )

    return CaptionWhisperModelResolution(
        power_profile=profile,
        model_name=model_name,
        config_path=str(config_path) if config_path else None,
        source="config:caption_transcription",
    )


def resolve_caption_highlight_timing_nudge_seconds(
    *,
    config_dir: str | Path = "video_configs",
) -> float:
    direct = str(os.getenv("ZENITH_CAPTION_HIGHLIGHT_TIMING_NUDGE_SECONDS") or "").strip()
    if direct:
        return float(direct)

    config, _config_path = _load_caption_transcription_config(config_dir)
    raw = config.get(
        "caption_highlight_timing_nudge_seconds",
        DEFAULT_CAPTION_HIGHLIGHT_TIMING_NUDGE_SECONDS,
    )
    return float(raw)
