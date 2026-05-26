from __future__ import annotations


class PowerProfile:
    OFF = "off"
    ECO = "eco"
    BALANCED = "balanced"
    PERFORMANCE = "performance"
    FULL_POWER = "full_power"

    DEFAULT = "balanced"
    ALL = ["off", "eco", "balanced", "performance", "full_power"]

    @staticmethod
    def normalize(value: str) -> str:
        """Unbekannter Wert → 'balanced'. Nie crashen."""
        try:
            clean = str(value or "").strip().lower()
        except Exception:
            clean = PowerProfile.DEFAULT

        if clean in PowerProfile.ALL:
            return clean

        return PowerProfile.DEFAULT

    @staticmethod
    def resolve_worker_count(power_profile: str) -> int:
        """
        off/eco → 1
        balanced → 2
        performance → 4
        full_power → 8
        Unbekannt → 2 (balanced Fallback)
        """
        profile = PowerProfile.normalize(power_profile)

        if profile == PowerProfile.OFF:
            return 1
        if profile == PowerProfile.ECO:
            return 1
        if profile == PowerProfile.BALANCED:
            return 2
        if profile == PowerProfile.PERFORMANCE:
            return 4
        if profile == PowerProfile.FULL_POWER:
            return 8

        return 2

    @staticmethod
    def resolve_analysis_worker_count(power_profile: str) -> int:
        return min(4, PowerProfile.resolve_worker_count(power_profile))

    @staticmethod
    def resolve_visual_analysis_frame_sample_rate(
        power_profile: str,
        stage: str,
    ) -> float:
        profile = PowerProfile.normalize(power_profile)
        stage_key = str(stage or "").strip().lower()

        defaults = {
            "motion": 2.0,
            "face_reaction": 2.0,
            "screen_content": 2.0,
            "stutter": 10.0,
        }

        if profile == PowerProfile.PERFORMANCE:
            return {
                "motion": 0.5,
                "face_reaction": 0.5,
                "screen_content": 0.5,
                "stutter": 2.0,
            }.get(stage_key, defaults.get(stage_key, 2.0))

        if profile == PowerProfile.ECO:
            return {
                "motion": 0.25,
                "face_reaction": 0.25,
                "screen_content": 0.25,
                "stutter": 1.0,
            }.get(stage_key, defaults.get(stage_key, 2.0))

        return defaults.get(stage_key, 2.0)

    @staticmethod
    def resolve_scene_change_timeout_seconds(power_profile: str) -> float:
        profile = PowerProfile.normalize(power_profile)
        if profile == PowerProfile.PERFORMANCE:
            return 30.0
        if profile == PowerProfile.ECO:
            return 15.0
        return 120.0

    @staticmethod
    def resolve_model_tier(power_profile: str) -> str:
        """
        off        → "shadow_only"
        eco        → "smallest_available"
        balanced   → "default"
        performance → "preferred"
        full_power → "largest_available"
        Unbekannt  → "default"
        """
        profile = PowerProfile.normalize(power_profile)

        if profile == PowerProfile.OFF:
            return "shadow_only"
        if profile == PowerProfile.ECO:
            return "smallest_available"
        if profile == PowerProfile.BALANCED:
            return "default"
        if profile == PowerProfile.PERFORMANCE:
            return "preferred"
        if profile == PowerProfile.FULL_POWER:
            return "largest_available"

        return "default"

    @staticmethod
    def resolve_render_config(power_profile: str) -> dict:
        """
        Gibt immer dict mit keys: threads (int), nvenc_preset (str)
        off        → threads=1,  nvenc_preset="p1"
        eco        → threads=2,  nvenc_preset="p2"
        balanced   → threads=0,  nvenc_preset="p4"
        performance → threads=0, nvenc_preset="p7"
        full_power → threads=0,  nvenc_preset="p7"
        Unbekannt  → balanced Fallback
        """
        profile = PowerProfile.normalize(power_profile)

        if profile == PowerProfile.OFF:
            return {"threads": 1, "nvenc_preset": "p1"}
        if profile == PowerProfile.ECO:
            return {"threads": 2, "nvenc_preset": "p2"}
        if profile == PowerProfile.BALANCED:
            return {"threads": 0, "nvenc_preset": "p4"}
        if profile == PowerProfile.PERFORMANCE:
            return {"threads": 0, "nvenc_preset": "p7"}
        if profile == PowerProfile.FULL_POWER:
            return {"threads": 0, "nvenc_preset": "p7"}

        return {"threads": 0, "nvenc_preset": "p4"}
