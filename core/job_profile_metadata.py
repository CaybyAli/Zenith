from __future__ import annotations

import json
from typing import Any


PROFILE_METADATA_KEYS = (
    "profile_id",
    "quality_mode",
    "profile_version",
    "profile_snapshot_path",
    "profile_source",
    "cut_aggressiveness",
    "source_aspect_ratio",
    "target_format",
    "reframing_mode",
    "music_enabled",
    "camera_zoom_enabled",
    "gameplay_zoom_enabled",
)


def build_profile_metadata(
    profile: dict[str, Any] | None,
    profile_snapshot_path: str | None,
) -> dict[str, Any]:
    profile = dict(profile or {})

    metadata = {
        "profile_id": profile.get("profile_id"),
        "quality_mode": profile.get("quality_mode"),
        "profile_version": profile.get("version") or profile.get("profile_version"),
        "profile_snapshot_path": (
            str(profile_snapshot_path)
            if profile_snapshot_path is not None
            else None
        ),
        "profile_source": "json_profile_manager",
        "cut_aggressiveness": profile.get("cut_aggressiveness"),
        "source_aspect_ratio": profile.get("source_aspect_ratio"),
        "target_format": profile.get("target_format"),
        "reframing_mode": profile.get("reframing_mode"),
        "music_enabled": profile.get("music_enabled"),
        "camera_zoom_enabled": profile.get("camera_zoom_enabled"),
        "gameplay_zoom_enabled": profile.get("gameplay_zoom_enabled"),
    }

    json.dumps(metadata)

    return metadata


def apply_profile_metadata_to_job(
    job: Any,
    profile: dict[str, Any] | None,
    profile_snapshot_path: str | None,
) -> dict[str, Any]:
    metadata = build_profile_metadata(
        profile=profile,
        profile_snapshot_path=profile_snapshot_path,
    )

    job.profile_id = metadata["profile_id"]
    job.quality_mode = metadata["quality_mode"]
    job.profile_version = metadata["profile_version"]
    job.profile_snapshot_path = metadata["profile_snapshot_path"]
    job.profile_source = metadata["profile_source"]
    job.profile_metadata = metadata

    return metadata
