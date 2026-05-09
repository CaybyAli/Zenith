"""
ProfileManager — lädt, validiert und verwaltet Editing-Profile aus JSON-Dateien.
"""

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = {
    "profile_id",
    "channel_type",
    "display_name",
    "quality_mode",
    "cut_aggressiveness",
    "music_enabled",
    "source_aspect_ratio",
    "target_format",
    "reframing_mode",
    "camera_zoom_enabled",
    "camera_zoom_mode",
    "camera_zoom_trigger",
    "camera_zoom_strength",
    "grading_strength",
    "min_clip_duration",
    "max_clip_duration",
    "version",
}

DEFAULT_FALLBACK_QUALITY = "balanced"


class ProfileLoadError(Exception):
    """Wird geworfen wenn ein Profil nicht geladen werden kann."""
    pass


class ProfileManager:
    """Verwaltet Editing-Profile aus dem profiles/ Ordner."""

    def __init__(self, profiles_dir: Optional[Path] = None):
        if profiles_dir is None:
            profiles_dir = Path(__file__).parent.parent / "profiles"
        self.profiles_dir = Path(profiles_dir)

    def load_profile(self, profile_id: str) -> dict:
        """
        Lädt ein Profil anhand seiner ID.
        Fallback auf quality_mode=balanced wenn Profil nicht gefunden.
        """
        profile_path = self.profiles_dir / f"{profile_id}.json"

        if not profile_path.exists():
            logger.warning(
                "PROFILE_NOT_FOUND profile=%s — using balanced fallback",
                profile_id,
            )
            return self._make_fallback_profile(profile_id)

        try:
            with open(profile_path, encoding="utf-8-sig") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ProfileLoadError(
                f"Profil '{profile_id}' enthält ungültiges JSON: {e}"
            ) from e

        self.validate_profile(data)

        logger.info(
            "PROFILE_LOADED profile=%s source=profiles/%s.json",
            profile_id,
            profile_id,
        )
        return data

    def list_profiles(self) -> list[str]:
        """Gibt alle verfügbaren Profil-IDs zurück."""
        return sorted(
            p.stem for p in self.profiles_dir.glob("*.json")
        )

    def validate_profile(self, data: dict) -> None:
        """
        Prüft ob alle Pflichtfelder vorhanden sind.
        Wirft ValueError wenn ein Feld fehlt.
        """
        missing = REQUIRED_FIELDS - data.keys()
        if missing:
            raise ValueError(
                f"Profil ungültig — fehlende Felder: {sorted(missing)}"
            )

    def _make_fallback_profile(self, profile_id: str) -> dict:
        """Erstellt ein minimales Fallback-Profil mit balanced-Defaults."""
        return {
            "profile_id": profile_id,
            "channel_type": profile_id,
            "display_name": f"Fallback ({profile_id})",
            "quality_mode": DEFAULT_FALLBACK_QUALITY,
            "cut_aggressiveness": 0.5,
            "dead_time_removal_strength": 0.7,
            "speech_protection_strength": 0.9,
            "music_enabled": False,
            "source_aspect_ratio": "16:9",
            "target_format": "16:9",
            "reframing_mode": "none",
            "gameplay_zoom_enabled": False,
            "gameplay_zoom_mode": None,
            "camera_zoom_enabled": False,
            "camera_zoom_mode": "selective",
            "camera_zoom_trigger": [],
            "camera_zoom_strength": 0.1,
            "grading_strength": 0.2,
            "min_clip_duration": 2.0,
            "max_clip_duration": 45.0,
            "version": "1.0.0",
            "_is_fallback": True,
        }
