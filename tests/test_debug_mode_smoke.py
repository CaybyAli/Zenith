from __future__ import annotations

from types import SimpleNamespace

from core.debug_mode import (
    build_debug_context,
    get_debug_mode,
    is_debug_enabled,
    is_trace_enabled,
    is_verbose_enabled,
)
from models.job import Job


def test_default_debug_mode_is_off():
    assert get_debug_mode() == "off"
    assert is_debug_enabled() is False
    assert is_verbose_enabled() is False
    assert is_trace_enabled() is False


def test_services_debug_mode_overrides_job_and_profile():
    job = SimpleNamespace(debug_mode="off")
    profile = {"debug_mode": "trace"}

    assert get_debug_mode(
        job=job,
        profile=profile,
        services={"debug_mode": "verbose"},
    ) == "verbose"


def test_job_debug_mode_is_used_when_services_missing():
    job = SimpleNamespace(debug_mode="trace")

    assert get_debug_mode(job=job, profile={"debug_mode": "normal"}) == "trace"


def test_profile_debug_mode_is_used_when_job_missing():
    assert get_debug_mode(profile={"debug_mode": "normal"}) == "normal"


def test_true_false_values_are_normalized():
    assert get_debug_mode(services={"debug_mode": True}) == "normal"
    assert get_debug_mode(services={"debug_mode": "true"}) == "normal"
    assert get_debug_mode(services={"debug_mode": 1}) == "normal"

    assert get_debug_mode(services={"debug_mode": False}) == "off"
    assert get_debug_mode(services={"debug_mode": "false"}) == "off"
    assert get_debug_mode(services={"debug_mode": 0}) == "off"


def test_verbose_enables_debug_and_verbose_but_not_trace():
    services = {"debug_mode": "verbose"}

    assert is_debug_enabled(services=services) is True
    assert is_verbose_enabled(services=services) is True
    assert is_trace_enabled(services=services) is False


def test_trace_enables_all_debug_flags():
    services = {"debug_mode": "trace"}

    assert is_debug_enabled(services=services) is True
    assert is_verbose_enabled(services=services) is True
    assert is_trace_enabled(services=services) is True


def test_invalid_debug_mode_falls_back_to_off():
    assert get_debug_mode(services={"debug_mode": "banana"}) == "off"


def test_build_debug_context_contains_job_profile_and_quality():
    job = SimpleNamespace(
        job_id="job_debug_smoke",
        profile_id="fallback_profile",
        quality_mode="balanced",
    )
    profile = {
        "profile_id": "gaming_main",
        "quality_mode": "pro",
        "debug_mode": "trace",
    }

    context = build_debug_context(job=job, profile=profile)

    assert context["debug_mode"] == "trace"
    assert context["debug_enabled"] is True
    assert context["verbose_enabled"] is True
    assert context["trace_enabled"] is True
    assert context["job_id"] == "job_debug_smoke"
    assert context["profile_id"] == "gaming_main"
    assert context["quality_mode"] == "pro"


def test_job_to_dict_from_dict_preserves_debug_fields():
    data = {
        "job_id": "job_model_debug_fields",
        "job_type": "gaming",
        "channel_type": "gaming_main",
        "target_format": "longform",
        "target_platforms": ["youtube"],
        "status": "created",
        "mode": "normal",
        "autopublish_class": "manual_only",
        "confidence_score": 0.0,
        "validator_status": "not_validated",
        "debug_mode": "verbose",
        "debug_context": {
            "debug_mode": "verbose",
            "debug_enabled": True,
            "verbose_enabled": True,
            "trace_enabled": False,
        },
    }

    job = Job.from_dict(data)
    as_dict = job.to_dict()

    assert as_dict["debug_mode"] == "verbose"
    assert as_dict["debug_context"]["debug_mode"] == "verbose"
    assert as_dict["debug_context"]["debug_enabled"] is True
    assert as_dict["debug_context"]["verbose_enabled"] is True
    assert as_dict["debug_context"]["trace_enabled"] is False
