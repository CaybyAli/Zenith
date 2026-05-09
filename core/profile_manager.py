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

DEFAULT_PROFILE_ID = "default"


class ProfileLoadError(Exception):
    """Wird geworfen wenn ein Profil nicht geladen werden kann."""
    pass


class ProfileManager:
    """Verwaltet Editing-Profile aus dem profiles/ Ordner."""

    def __init__(self, profiles_dir: Optional[Path] = None):
        if profiles_dir is None:
            profiles_dir = Path(__file__).parent.parent / "profiles"
        self.profiles_dir = Path(profiles_dir)

    def load_default_profile(self) -> dict:
        """
        Lädt profiles/default.json.
        Wenn default.json fehlt, ist das ein echter Fehler.
        """
        default_path = self.profiles_dir / f"{DEFAULT_PROFILE_ID}.json"

        if not default_path.exists():
            raise ProfileLoadError(
                f"Default-Profil fehlt: {default_path}"
            )

        data = self._load_json_file(DEFAULT_PROFILE_ID)
        self.validate_profile(data)
        return data

    def load_profile(self, profile_id: str) -> dict:
        """
        Lädt ein Profil anhand seiner ID.

        Neu:
        default.json wird zuerst geladen.
        Danach wird das spezifische Profil darübergelegt.
        Spezifische Werte gewinnen.
        """
        profile_id = str(profile_id or DEFAULT_PROFILE_ID)

        if profile_id == DEFAULT_PROFILE_ID:
            return self.load_default_profile()

        default_profile = self.load_default_profile()
        profile_path = self.profiles_dir / f"{profile_id}.json"

        if not profile_path.exists():
            logger.warning(
                "PROFILE_NOT_FOUND profile=%s — using default fallback",
                profile_id,
            )
            fallback = self._make_fallback_profile(profile_id, default_profile)
            self.validate_profile(fallback)
            return fallback

        specific_profile = self._load_json_file(profile_id)

        merged = self._merge_profiles(
            default_profile=default_profile,
            specific_profile=specific_profile,
            requested_profile_id=profile_id,
        )

        self.validate_profile(merged)

        logger.info(
            "PROFILE_LOADED profile=%s source=profiles/%s.json inherited_from=profiles/default.json",
            profile_id,
            profile_id,
        )
        return merged

    def list_profiles(self) -> list[str]:
        """
        Gibt alle echten Channel-Profile zurück.
        default.json wird absichtlich nicht mitgezählt.
        """
        return sorted(
            p.stem
            for p in self.profiles_dir.glob("*.json")
            if p.stem != DEFAULT_PROFILE_ID
        )

    def validate_profile(self, data: dict) -> None:
        """
        Prüft ob alle Pflichtfelder im fertigen Profil vorhanden sind.
        Wichtig: Diese Prüfung passiert nach dem Merge.
        """
        missing = REQUIRED_FIELDS - data.keys()
        if missing:
            raise ValueError(
                f"Profil ungültig — fehlende Felder: {sorted(missing)}"
            )

    def _load_json_file(self, profile_id: str) -> dict:
        profile_path = self.profiles_dir / f"{profile_id}.json"

        try:
            with open(profile_path, encoding="utf-8-sig") as f:
                data = json.load(f)
        except json.JSONDecodeError as e:
            raise ProfileLoadError(
                f"Profil '{profile_id}' enthält ungültiges JSON: {e}"
            ) from e
        except OSError as e:
            raise ProfileLoadError(
                f"Profil '{profile_id}' konnte nicht gelesen werden: {e}"
            ) from e

        if not isinstance(data, dict):
            raise ProfileLoadError(
                f"Profil '{profile_id}' muss ein JSON-Objekt sein."
            )

        return data

    def _merge_profiles(
        self,
        default_profile: dict,
        specific_profile: dict,
        requested_profile_id: str,
    ) -> dict:
        merged = dict(default_profile)
        merged.update(specific_profile)

        merged["profile_id"] = specific_profile.get(
            "profile_id",
            requested_profile_id,
        )
        merged["channel_type"] = specific_profile.get(
            "channel_type",
            requested_profile_id,
        )

        merged.pop("_is_fallback", None)
        return merged

    def _make_fallback_profile(
        self,
        profile_id: str,
        default_profile: dict | None = None,
    ) -> dict:
        """
        Erstellt ein Fallback-Profil aus default.json.
        profile_id bleibt das angefragte Profil.
        """
        if default_profile is None:
            default_profile = self.load_default_profile()

        fallback = dict(default_profile)
        fallback.update({
            "profile_id": profile_id,
            "channel_type": profile_id,
            "display_name": f"Fallback ({profile_id})",
            "_is_fallback": True,
        })
        return fallback