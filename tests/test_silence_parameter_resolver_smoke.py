from __future__ import annotations

import pathlib
from types import SimpleNamespace
from typing import Any

import pytest

from models.silence_detection_parameters import SilenceDetectionParameters
from core.silence_parameter_resolver import (
    resolve_silence_detection_parameters,
    DEFAULT_THRESHOLD_DB,
    DEFAULT_MIN_DURATION_SECONDS,
    DEFAULT_REQUIRE_EXISTING_AUDIO,
)

_REPO_ROOT = pathlib.Path(__file__).parent.parent


def _make_job(**kwargs: Any) -> SimpleNamespace:
    defaults = {
        "quality_mode": None,
        "profile_id": None,
        "profile_metadata": {},
        "silence_threshold_db": None,
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


class TestSilenceDetectionParametersRoundtrip:
    def test_silence_detection_parameters_roundtrip(self) -> None:
        original = SilenceDetectionParameters(
            threshold_db=-41.5,
            min_duration_seconds=0.35,
            require_existing_audio=False,
            source_priority=["overrides", "profile", "default"],
            profile_id="gaming_main",
            quality_mode="pro",
            resolved_from={"threshold_db": "overrides.threshold_db"},
            warnings=["test_warning"],
            errors=[],
            metadata={"extra": "data"},
        )
        data = original.to_dict()
        restored = SilenceDetectionParameters.from_dict(data)

        assert restored.threshold_db == -41.5
        assert restored.min_duration_seconds == 0.35
        assert restored.require_existing_audio is False
        assert restored.source_priority == ["overrides", "profile", "default"]
        assert restored.profile_id == "gaming_main"
        assert restored.quality_mode == "pro"
        assert restored.resolved_from == {"threshold_db": "overrides.threshold_db"}
        assert restored.warnings == ["test_warning"]
        assert restored.errors == []
        assert restored.metadata == {"extra": "data"}


class TestDefaultResolution:
    def test_defaults_are_used_without_profile_or_job(self) -> None:
        result = resolve_silence_detection_parameters()

        assert result.threshold_db == DEFAULT_THRESHOLD_DB
        assert result.min_duration_seconds == DEFAULT_MIN_DURATION_SECONDS
        assert result.require_existing_audio is DEFAULT_REQUIRE_EXISTING_AUDIO
        assert result.resolved_from.get("threshold_db") == "default"
        assert result.resolved_from.get("min_duration_seconds") == "default"
        assert result.resolved_from.get("require_existing_audio") == "default"
        assert result.errors == []


class TestProfileOverridesDefaults:
    def test_profile_audio_values_override_defaults(self) -> None:
        profile = {
            "profile_id": "gaming_main",
            "quality_mode": "pro",
            "audio": {
                "silence_threshold_db": -43,
                "min_silence_duration_ms": 350,
            },
        }
        result = resolve_silence_detection_parameters(profile=profile)

        assert result.threshold_db == -43.0
        assert result.min_duration_seconds == pytest.approx(0.35, abs=1e-9)
        assert result.profile_id == "gaming_main"
        assert "profile.audio.silence_threshold_db" in result.resolved_from.get("threshold_db", "")
        assert "ms" in result.resolved_from.get("min_duration_seconds", "")


class TestOverridesWinOverProfile:
    def test_overrides_win_over_profile(self) -> None:
        profile = {
            "audio": {"silence_threshold_db": -43},
        }
        overrides = {"threshold_db": -35.0}
        result = resolve_silence_detection_parameters(profile=profile, overrides=overrides)

        assert result.threshold_db == -35.0
        assert "overrides" in result.resolved_from.get("threshold_db", "")


class TestJobQualityModeDefaults:
    def test_job_quality_mode_sets_quality_defaults(self) -> None:
        job = _make_job(quality_mode="pro")
        result = resolve_silence_detection_parameters(job=job)

        assert result.threshold_db == -42.0
        assert result.min_duration_seconds == pytest.approx(0.35, abs=1e-9)
        assert "quality_mode.pro" in result.resolved_from.get("threshold_db", "")


class TestCinematicQualityModeDefaults:
    def test_cinematic_quality_mode_defaults_are_stricter(self) -> None:
        result = resolve_silence_detection_parameters(
            overrides={"quality_mode": "cinematic"}
        )

        assert result.threshold_db == -44.0
        assert result.min_duration_seconds == pytest.approx(0.3, abs=1e-9)


class TestInvalidThresholdFallback:
    def test_invalid_threshold_falls_back_with_warning(self) -> None:
        result = resolve_silence_detection_parameters(
            overrides={"threshold_db": -200.0}
        )

        assert len(result.warnings) > 0
        assert result.threshold_db in (-40.0, -38.0, -42.0, -44.0)

    def test_invalid_threshold_non_numeric_falls_back(self) -> None:
        result = resolve_silence_detection_parameters(
            overrides={"threshold_db": "not_a_number"}
        )
        assert result.threshold_db == DEFAULT_THRESHOLD_DB


class TestInvalidMinDurationFallback:
    def test_invalid_min_duration_falls_back_with_warning(self) -> None:
        result = resolve_silence_detection_parameters(
            overrides={"min_duration_seconds": 99.0}
        )

        assert len(result.warnings) > 0
        assert result.min_duration_seconds in (0.4, 0.5, 0.35, 0.3)


class TestMsDurationConversion:
    def test_ms_duration_is_converted_to_seconds(self) -> None:
        result = resolve_silence_detection_parameters(
            overrides={"min_duration_ms": 750}
        )

        assert result.min_duration_seconds == pytest.approx(0.75, abs=1e-9)

    def test_ms_350_converts_to_035(self) -> None:
        result = resolve_silence_detection_parameters(
            overrides={"min_silence_duration_ms": 350}
        )
        assert result.min_duration_seconds == pytest.approx(0.35, abs=1e-9)


class TestBoolLikeRequireExistingAudio:
    def test_bool_like_require_existing_audio_is_parsed_false(self) -> None:
        result = resolve_silence_detection_parameters(
            overrides={"require_existing_audio": "false"}
        )
        assert result.require_existing_audio is False

    def test_bool_like_require_existing_audio_no(self) -> None:
        result = resolve_silence_detection_parameters(
            overrides={"require_existing_audio": "no"}
        )
        assert result.require_existing_audio is False

    def test_bool_like_require_existing_audio_true(self) -> None:
        result = resolve_silence_detection_parameters(
            overrides={"require_existing_audio": "yes"}
        )
        assert result.require_existing_audio is True

    def test_bool_require_existing_audio_int_zero(self) -> None:
        result = resolve_silence_detection_parameters(
            overrides={"require_existing_audio": 0}
        )
        assert result.require_existing_audio is False


class TestJobProfileMetadata:
    def test_job_profile_metadata_can_supply_audio_values(self) -> None:
        job = _make_job(
            profile_metadata={
                "audio": {
                    "silence_threshold_db": -41,
                    "min_silence_duration_ms": 500,
                }
            }
        )
        result = resolve_silence_detection_parameters(job=job)

        assert result.threshold_db == -41.0
        assert result.min_duration_seconds == pytest.approx(0.5, abs=1e-9)


class TestResolverRobustness:
    def test_resolver_does_not_crash_on_bad_inputs(self) -> None:
        bad_profile: dict = {
            "audio": "not_a_dict",
            "silence_threshold_db": "oops",
            "silence_detection": None,
        }
        bad_job = _make_job(
            profile_metadata="not_a_dict",
            quality_mode=42,
        )
        bad_overrides: dict = {
            "threshold_db": [1, 2, 3],
            "min_duration_seconds": {"nested": True},
            "require_existing_audio": object(),
        }

        result = resolve_silence_detection_parameters(
            profile=bad_profile,
            job=bad_job,
            overrides=bad_overrides,
        )

        assert isinstance(result, SilenceDetectionParameters)
        assert isinstance(result.threshold_db, float)
        assert isinstance(result.min_duration_seconds, float)
        assert isinstance(result.require_existing_audio, bool)

    def test_resolver_does_not_crash_on_none_inputs(self) -> None:
        result = resolve_silence_detection_parameters(
            profile=None,
            job=None,
            overrides=None,
        )
        assert isinstance(result, SilenceDetectionParameters)
        assert result.errors == []


class TestFileHygiene:
    def _check_file(self, rel_path: str) -> None:
        path = _REPO_ROOT / rel_path
        raw = path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {rel_path}"
        assert raw.endswith(b"\n"), f"File does not end with newline: {rel_path}"

    def test_silence_parameter_resolver_files_have_no_bom_and_end_with_newline(self) -> None:
        self._check_file("models/silence_detection_parameters.py")
        self._check_file("core/silence_parameter_resolver.py")
        self._check_file("tests/test_silence_parameter_resolver_smoke.py")
