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
    "dead_time_removal_strength",
    "speech_protection_strength",
    "story_context_weight",
    "gameplay_context_weight",
    "reaction_context_weight",
    "music_enabled",
    "dynamic_zoom_allowed",
    "facecam_emphasis_allowed",
    "gameplay_focus_allowed",
    "fixed_facecam_mode",
    "subtitles_default",
    "review_strictness",
    "requires_human_approval",
    "source_aspect_ratio",
    "target_format",
    "reframing_mode",
    "gameplay_zoom_enabled",
    "gameplay_zoom_mode",
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

ALLOWED_QUALITY_MODES = {"fast", "balanced", "pro", "cinematic"}
ALLOWED_ASPECT_RATIOS = {"16:9", "32:9", "9:16", "1:1"}
ALLOWED_REFRAMING_MODES = {"none", "intelligent_crop", "center_crop", "vertical_reframe"}
ALLOWED_ZOOM_MODES = {"aggressive", "selective", "none", None}

RATIO_0_TO_1_FIELDS = (
    "cut_aggressiveness",
    "dead_time_removal_strength",
    "speech_protection_strength",
    "story_context_weight",
    "gameplay_context_weight",
    "reaction_context_weight",
    "camera_zoom_strength",
    "grading_strength",
)

POSITIVE_DURATION_FIELDS = (
    "min_clip_duration",
    "max_clip_duration",
)

BOOLEAN_FIELDS = (
    "music_enabled",
    "dynamic_zoom_allowed",
    "facecam_emphasis_allowed",
    "gameplay_focus_allowed",
    "fixed_facecam_mode",
    "subtitles_default",
    "requires_human_approval",
    "gameplay_zoom_enabled",
    "camera_zoom_enabled",
)


class ProfileLoadError(Exception):
    """Wird geworfen wenn ein Profil nicht geladen werden kann."""
    pass

class ProfileValidationError(ValueError):
    """Wird geworfen wenn ein Profil ungültige Werte enthält."""
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
        Prüft ob alle Pflichtfelder und Werte im fertigen Profil gültig sind.
        Wichtig: Diese Prüfung passiert nach dem Merge.
        """
        missing = REQUIRED_FIELDS - data.keys()
        if missing:
            raise ProfileValidationError(
                f"Profil ungültig — fehlende Felder: {sorted(missing)}"
            )

        self._require_choice(data, "quality_mode", ALLOWED_QUALITY_MODES)
        self._require_choice(data, "source_aspect_ratio", ALLOWED_ASPECT_RATIOS)
        self._require_choice(data, "target_format", ALLOWED_ASPECT_RATIOS)
        self._require_choice(data, "reframing_mode", ALLOWED_REFRAMING_MODES)
        self._require_choice(data, "camera_zoom_mode", ALLOWED_ZOOM_MODES)
        self._require_choice(data, "gameplay_zoom_mode", ALLOWED_ZOOM_MODES)

        for key in BOOLEAN_FIELDS:
            self._require_bool(data, key)

        for key in RATIO_0_TO_1_FIELDS:
            self._require_range_0_to_1(data, key)

        for key in POSITIVE_DURATION_FIELDS:
            self._require_positive_number(data, key)

        self._require_list(data, "camera_zoom_trigger")
        self._require_non_empty_string(data, "version")
        self._validate_duration_order(data)

    def _require_choice(self, data: dict, key: str, allowed: set) -> None:
        value = data.get(key)
        if value not in allowed:
            raise ProfileValidationError(
                f"Profil ungültig — {key} muss einer von {sorted(allowed, key=str)} sein."
            )

    def _require_bool(self, data: dict, key: str) -> None:
        if not isinstance(data.get(key), bool):
            raise ProfileValidationError(
                f"Profil ungültig — {key} muss true oder false sein."
            )

    def _require_number(self, data: dict, key: str) -> float:
        value = data.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ProfileValidationError(
                f"Profil ungültig — {key} muss eine Zahl sein."
            )
        return float(value)

    def _require_range_0_to_1(self, data: dict, key: str) -> None:
        value = self._require_number(data, key)
        if value < 0.0 or value > 1.0:
            raise ProfileValidationError(
                f"Profil ungültig — {key} muss zwischen 0.0 und 1.0 liegen."
            )

    def _require_positive_number(self, data: dict, key: str) -> None:
        value = self._require_number(data, key)
        if value <= 0.0:
            raise ProfileValidationError(
                f"Profil ungültig — {key} muss größer als 0 sein."
            )

    def _require_non_empty_string(self, data: dict, key: str) -> None:
        value = data.get(key)
        if not isinstance(value, str) or not value.strip():
            raise ProfileValidationError(
                f"Profil ungültig — {key} muss ein nicht-leerer String sein."
            )

    def _require_list(self, data: dict, key: str) -> None:
        if not isinstance(data.get(key), list):
            raise ProfileValidationError(
                f"Profil ungültig — {key} muss eine Liste sein."
            )

    def _validate_duration_order(self, data: dict) -> None:
        min_duration = self._require_number(data, "min_clip_duration")
        max_duration = self._require_number(data, "max_clip_duration")

        if min_duration > max_duration:
            raise ProfileValidationError(
                "Profil ungültig — min_clip_duration darf nicht größer als max_clip_duration sein."
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
