from __future__ import annotations

from typing import Any


ALLOWED_DEBUG_MODES = {"off", "normal", "verbose", "trace"}


def _normalize_debug_mode(value: Any) -> str:
    if value is None:
        return "off"

    raw = str(value).strip().lower()

    if raw in {"false", "0", "no", "none", ""}:
        return "off"

    if raw in {"true", "1", "yes", "on"}:
        return "normal"

    if raw not in ALLOWED_DEBUG_MODES:
        return "off"

    return raw


def get_debug_mode(job=None, profile=None, services=None) -> str:
    services = services or {}
    profile = profile or {}

    if isinstance(services, dict) and "debug_mode" in services:
        return _normalize_debug_mode(services.get("debug_mode"))

    if job is not None and hasattr(job, "debug_mode"):
        return _normalize_debug_mode(getattr(job, "debug_mode"))

    if isinstance(profile, dict) and "debug_mode" in profile:
        return _normalize_debug_mode(profile.get("debug_mode"))

    return "off"


def is_debug_enabled(job=None, profile=None, services=None) -> bool:
    return get_debug_mode(job=job, profile=profile, services=services) in {
        "normal",
        "verbose",
        "trace",
    }


def is_verbose_enabled(job=None, profile=None, services=None) -> bool:
    return get_debug_mode(job=job, profile=profile, services=services) in {
        "verbose",
        "trace",
    }


def is_trace_enabled(job=None, profile=None, services=None) -> bool:
    return get_debug_mode(job=job, profile=profile, services=services) == "trace"


def build_debug_context(job=None, profile=None, services=None) -> dict[str, Any]:
    mode = get_debug_mode(job=job, profile=profile, services=services)

    return {
        "debug_mode": mode,
        "debug_enabled": mode in {"normal", "verbose", "trace"},
        "verbose_enabled": mode in {"verbose", "trace"},
        "trace_enabled": mode == "trace",
        "job_id": getattr(job, "job_id", None) if job is not None else None,
        "profile_id": (
            profile.get("profile_id")
            if isinstance(profile, dict)
            else getattr(job, "profile_id", None)
        ),
        "quality_mode": (
            profile.get("quality_mode")
            if isinstance(profile, dict)
            else getattr(job, "quality_mode", None)
        ),
    }
