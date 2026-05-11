from __future__ import annotations

from typing import Any

from models.silence_detection_parameters import SilenceDetectionParameters

DEFAULT_THRESHOLD_DB: float = -40.0
DEFAULT_MIN_DURATION_SECONDS: float = 0.4
DEFAULT_REQUIRE_EXISTING_AUDIO: bool = True

_QUALITY_MODE_DEFAULTS: dict[str, dict[str, float]] = {
    "fast": {"threshold_db": -38.0, "min_duration_seconds": 0.5},
    "balanced": {"threshold_db": -40.0, "min_duration_seconds": 0.4},
    "pro": {"threshold_db": -42.0, "min_duration_seconds": 0.35},
    "cinematic": {"threshold_db": -44.0, "min_duration_seconds": 0.3},
}

_THRESHOLD_RANGE = (-80.0, -5.0)
_DURATION_RANGE = (0.05, 10.0)


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _coerce_bool(value: Any) -> bool | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in ("true", "yes", "1"):
            return True
        if normalized in ("false", "no", "0"):
            return False
        return None
    return None


def _extract_nested_value(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
        if current is None:
            return None
    return current


def _resolve_quality_mode(
    overrides: dict[str, Any] | None,
    job: Any,
    profile: dict[str, Any] | None,
) -> tuple[str | None, str]:
    if overrides:
        val = overrides.get("quality_mode")
        if val:
            return str(val).strip().lower(), "overrides.quality_mode"

    if job is not None:
        val = getattr(job, "quality_mode", None)
        if val:
            return str(val).strip().lower(), "job.quality_mode"

    if profile:
        val = profile.get("quality_mode")
        if val:
            return str(val).strip().lower(), "profile.quality_mode"

    return None, "none"


def _resolve_threshold_db(
    overrides: dict[str, Any] | None,
    job: Any,
    profile: dict[str, Any] | None,
    quality_mode: str | None,
    warnings: list[str],
) -> tuple[float, str]:
    override_keys = ["threshold_db", "silence_threshold_db", "silence_detection_threshold_db"]
    if overrides:
        for key in override_keys:
            raw = overrides.get(key)
            if raw is not None:
                val = _coerce_float(raw)
                if val is not None:
                    if _THRESHOLD_RANGE[0] <= val <= _THRESHOLD_RANGE[1]:
                        return val, f"overrides.{key}"
                    warnings.append(
                        f"threshold_db {val} out of range {_THRESHOLD_RANGE}, falling back"
                    )

    if job is not None:
        raw = getattr(job, "silence_threshold_db", None)
        if raw is not None:
            val = _coerce_float(raw)
            if val is not None:
                if _THRESHOLD_RANGE[0] <= val <= _THRESHOLD_RANGE[1]:
                    return val, "job.silence_threshold_db"
                warnings.append(
                    f"threshold_db {val} out of range {_THRESHOLD_RANGE}, falling back"
                )

        pm = getattr(job, "profile_metadata", None) or {}
        for path, source_name in [
            (["silence_threshold_db"], "job.profile_metadata.silence_threshold_db"),
            (["audio", "silence_threshold_db"], "job.profile_metadata.audio.silence_threshold_db"),
        ]:
            raw = _extract_nested_value(pm, *path)
            if raw is not None:
                val = _coerce_float(raw)
                if val is not None:
                    if _THRESHOLD_RANGE[0] <= val <= _THRESHOLD_RANGE[1]:
                        return val, source_name
                    warnings.append(
                        f"threshold_db {val} out of range {_THRESHOLD_RANGE}, falling back"
                    )

    if profile:
        for path, source_name in [
            (["audio", "silence_threshold_db"], "profile.audio.silence_threshold_db"),
            (["silence_detection", "threshold_db"], "profile.silence_detection.threshold_db"),
            (["silence", "threshold_db"], "profile.silence.threshold_db"),
            (["silence_threshold_db"], "profile.silence_threshold_db"),
        ]:
            raw = _extract_nested_value(profile, *path)
            if raw is not None:
                val = _coerce_float(raw)
                if val is not None:
                    if _THRESHOLD_RANGE[0] <= val <= _THRESHOLD_RANGE[1]:
                        return val, source_name
                    warnings.append(
                        f"threshold_db {val} out of range {_THRESHOLD_RANGE}, falling back"
                    )

    if quality_mode and quality_mode in _QUALITY_MODE_DEFAULTS:
        return _QUALITY_MODE_DEFAULTS[quality_mode]["threshold_db"], f"quality_mode.{quality_mode}"

    return DEFAULT_THRESHOLD_DB, "default"


def _resolve_min_duration_seconds(
    overrides: dict[str, Any] | None,
    job: Any,
    profile: dict[str, Any] | None,
    quality_mode: str | None,
    warnings: list[str],
) -> tuple[float, str]:
    def _check_seconds(raw: Any, source: str) -> tuple[float, str] | None:
        val = _coerce_float(raw)
        if val is None:
            return None
        if _DURATION_RANGE[0] <= val <= _DURATION_RANGE[1]:
            return val, source
        warnings.append(
            f"min_duration_seconds {val} out of range {_DURATION_RANGE}, falling back"
        )
        return None

    def _check_ms(raw: Any, source: str) -> tuple[float, str] | None:
        val = _coerce_float(raw)
        if val is None:
            return None
        converted = val / 1000.0
        if _DURATION_RANGE[0] <= converted <= _DURATION_RANGE[1]:
            return converted, source
        warnings.append(
            f"min_duration_ms {val} converts to {converted}s, out of range {_DURATION_RANGE}, falling back"
        )
        return None

    seconds_keys = ["min_duration_seconds", "min_silence_duration_seconds", "silence_min_duration_seconds"]
    ms_keys = ["min_duration_ms", "min_silence_duration_ms", "min_silence_duration_milliseconds"]

    if overrides:
        for key in seconds_keys:
            raw = overrides.get(key)
            if raw is not None:
                result = _check_seconds(raw, f"overrides.{key}")
                if result:
                    return result
        for key in ms_keys:
            raw = overrides.get(key)
            if raw is not None:
                result = _check_ms(raw, f"overrides.{key}(ms)")
                if result:
                    return result

    if job is not None:
        pm = getattr(job, "profile_metadata", None) or {}
        for path, source_name in [
            (["min_silence_duration_seconds"], "job.profile_metadata.min_silence_duration_seconds"),
            (["audio", "min_silence_duration_ms"], "job.profile_metadata.audio.min_silence_duration_ms(ms)"),
            (["audio", "min_silence_duration_seconds"], "job.profile_metadata.audio.min_silence_duration_seconds"),
        ]:
            raw = _extract_nested_value(pm, *path)
            if raw is not None:
                if "ms" in source_name:
                    result = _check_ms(raw, source_name)
                else:
                    result = _check_seconds(raw, source_name)
                if result:
                    return result

    if profile:
        profile_audio = profile.get("audio") or {}
        for key in ms_keys:
            raw = profile_audio.get(key)
            if raw is not None:
                result = _check_ms(raw, f"profile.audio.{key}(ms)")
                if result:
                    return result
        for key in seconds_keys:
            raw = profile_audio.get(key)
            if raw is not None:
                result = _check_seconds(raw, f"profile.audio.{key}")
                if result:
                    return result

        for path, source_name, is_ms in [
            (["silence_detection", "min_duration_seconds"], "profile.silence_detection.min_duration_seconds", False),
            (["silence_detection", "min_duration_ms"], "profile.silence_detection.min_duration_ms(ms)", True),
            (["silence", "min_duration_seconds"], "profile.silence.min_duration_seconds", False),
            (["silence", "min_duration_ms"], "profile.silence.min_duration_ms(ms)", True),
        ]:
            raw = _extract_nested_value(profile, *path)
            if raw is not None:
                result = _check_ms(raw, source_name) if is_ms else _check_seconds(raw, source_name)
                if result:
                    return result

    if quality_mode and quality_mode in _QUALITY_MODE_DEFAULTS:
        return _QUALITY_MODE_DEFAULTS[quality_mode]["min_duration_seconds"], f"quality_mode.{quality_mode}"

    return DEFAULT_MIN_DURATION_SECONDS, "default"


def _resolve_require_existing_audio(
    overrides: dict[str, Any] | None,
    job: Any,
    profile: dict[str, Any] | None,
    warnings: list[str],
) -> tuple[bool, str]:
    search_keys = [
        "require_existing_audio",
        "silence_require_existing_audio",
    ]

    if overrides:
        for key in search_keys:
            raw = overrides.get(key)
            if raw is not None:
                val = _coerce_bool(raw)
                if val is not None:
                    return val, f"overrides.{key}"
                warnings.append(f"require_existing_audio override '{raw}' not parseable, falling back")

    if profile:
        for path, source_name in [
            (["audio", "require_existing_audio"], "profile.audio.require_existing_audio"),
            (["silence_detection", "require_existing_audio"], "profile.silence_detection.require_existing_audio"),
            (["require_existing_audio"], "profile.require_existing_audio"),
        ]:
            raw = _extract_nested_value(profile, *path)
            if raw is not None:
                val = _coerce_bool(raw)
                if val is not None:
                    return val, source_name
                warnings.append(f"require_existing_audio '{raw}' not parseable, falling back")

    return DEFAULT_REQUIRE_EXISTING_AUDIO, "default"


def _resolve_profile_id(
    profile: dict[str, Any] | None,
    job: Any,
) -> str | None:
    if profile:
        val = profile.get("profile_id") or profile.get("profile_name")
        if val:
            return str(val)
    if job is not None:
        val = getattr(job, "profile_id", None)
        if val:
            return str(val)
    return None


def resolve_silence_detection_parameters(
    profile: dict[str, Any] | None = None,
    job: Any | None = None,
    overrides: dict[str, Any] | None = None,
) -> SilenceDetectionParameters:
    warnings: list[str] = []
    errors: list[str] = []
    resolved_from: dict[str, str] = {}

    try:
        quality_mode, qm_source = _resolve_quality_mode(overrides, job, profile)
        resolved_from["quality_mode"] = qm_source

        threshold_db, threshold_source = _resolve_threshold_db(
            overrides, job, profile, quality_mode, warnings
        )
        resolved_from["threshold_db"] = threshold_source

        min_duration_seconds, duration_source = _resolve_min_duration_seconds(
            overrides, job, profile, quality_mode, warnings
        )
        resolved_from["min_duration_seconds"] = duration_source

        require_existing_audio, req_source = _resolve_require_existing_audio(
            overrides, job, profile, warnings
        )
        resolved_from["require_existing_audio"] = req_source

        profile_id = _resolve_profile_id(profile, job)

        source_priority: list[str] = []
        if overrides:
            source_priority.append("overrides")
        if job is not None:
            source_priority.append("job")
        if profile:
            source_priority.append("profile")
        if quality_mode:
            source_priority.append(f"quality_mode.{quality_mode}")
        source_priority.append("default")

        return SilenceDetectionParameters(
            threshold_db=threshold_db,
            min_duration_seconds=min_duration_seconds,
            require_existing_audio=require_existing_audio,
            source_priority=source_priority,
            profile_id=profile_id,
            quality_mode=quality_mode,
            resolved_from=resolved_from,
            warnings=warnings,
            errors=errors,
        )

    except Exception as exc:
        errors.append(f"resolver_exception: {exc}")
        return SilenceDetectionParameters(
            threshold_db=DEFAULT_THRESHOLD_DB,
            min_duration_seconds=DEFAULT_MIN_DURATION_SECONDS,
            require_existing_audio=DEFAULT_REQUIRE_EXISTING_AUDIO,
            source_priority=["default"],
            resolved_from={"threshold_db": "default", "min_duration_seconds": "default",
                           "require_existing_audio": "default"},
            warnings=warnings,
            errors=errors,
        )
