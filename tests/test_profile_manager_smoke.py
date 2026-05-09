"""
Smoke-Tests für ProfileManager — 2B-01-A
"""

import json
import pytest
from pathlib import Path

from core.profile_manager import ProfileManager, ProfileLoadError


PROFILES_DIR = Path(__file__).parent.parent / "profiles"
ALL_PROFILE_IDS = [
    "gaming_main",
    "vlog_main",
    "gaming_uncut",
    "reaction_uncut",
    "vlog_uncut",
]


# ── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture
def manager():
    return ProfileManager(profiles_dir=PROFILES_DIR)


# ── list_profiles ────────────────────────────────────────────────────────────

def test_list_profiles_returns_all_five(manager):
    result = manager.list_profiles()
    assert sorted(result) == sorted(ALL_PROFILE_IDS)


def test_list_profiles_returns_list(manager):
    assert isinstance(manager.list_profiles(), list)


# ── load_profile ─────────────────────────────────────────────────────────────

@pytest.mark.parametrize("profile_id", ALL_PROFILE_IDS)
def test_load_profile_returns_dict(manager, profile_id):
    profile = manager.load_profile(profile_id)
    assert isinstance(profile, dict)


@pytest.mark.parametrize("profile_id", ALL_PROFILE_IDS)
def test_load_profile_id_matches(manager, profile_id):
    profile = manager.load_profile(profile_id)
    assert profile["profile_id"] == profile_id


@pytest.mark.parametrize("profile_id", ALL_PROFILE_IDS)
def test_load_profile_has_version(manager, profile_id):
    profile = manager.load_profile(profile_id)
    assert profile["version"] == "1.0.0"


@pytest.mark.parametrize("profile_id", ALL_PROFILE_IDS)
def test_load_profile_has_quality_mode(manager, profile_id):
    profile = manager.load_profile(profile_id)
    assert profile["quality_mode"] in {"fast", "balanced", "pro", "cinematic"}


@pytest.mark.parametrize("profile_id", ALL_PROFILE_IDS)
def test_load_profile_cut_aggressiveness_range(manager, profile_id):
    profile = manager.load_profile(profile_id)
    assert 0.0 <= profile["cut_aggressiveness"] <= 1.0


# ── validate_profile ─────────────────────────────────────────────────────────

def test_validate_profile_passes_for_valid_data(manager):
    profile = manager.load_profile("gaming_main")
    manager.validate_profile(profile)  # kein Fehler erwartet


def test_validate_profile_raises_on_missing_field(manager):
    bad_profile = {"profile_id": "test"}  # fast alle Felder fehlen
    with pytest.raises(ValueError, match="fehlende Felder"):
        manager.validate_profile(bad_profile)


def test_validate_profile_raises_on_empty_dict(manager):
    with pytest.raises(ValueError, match="fehlende Felder"):
        manager.validate_profile({})


# ── Fallback ─────────────────────────────────────────────────────────────────

def test_fallback_on_unknown_profile(manager):
    profile = manager.load_profile("unknown_profile_xyz")
    assert profile["quality_mode"] == "balanced"
    assert profile["_is_fallback"] is True


def test_fallback_preserves_profile_id(manager):
    profile = manager.load_profile("does_not_exist")
    assert profile["profile_id"] == "does_not_exist"


# ── Fehlerbehandlung ──────────────────────────────────────────────────────────

def test_broken_json_raises_profile_load_error(manager, tmp_path):
    broken = tmp_path / "broken.json"
    broken.write_text("{ this is not valid json }", encoding="utf-8")
    bad_manager = ProfileManager(profiles_dir=tmp_path)
    with pytest.raises(ProfileLoadError, match="ungültiges JSON"):
        bad_manager.load_profile("broken")


# ── Spezifische Profilwerte ───────────────────────────────────────────────────

def test_gaming_main_quality_is_pro(manager):
    profile = manager.load_profile("gaming_main")
    assert profile["quality_mode"] == "pro"


def test_gaming_main_music_enabled(manager):
    profile = manager.load_profile("gaming_main")
    assert profile["music_enabled"] is True


def test_reaction_uncut_lowest_cut_aggressiveness(manager):
    profiles = [manager.load_profile(p) for p in ALL_PROFILE_IDS]
    reaction = manager.load_profile("reaction_uncut")
    assert all(
        reaction["cut_aggressiveness"] <= p["cut_aggressiveness"]
        for p in profiles
    )


def test_gaming_uncut_music_disabled(manager):
    profile = manager.load_profile("gaming_uncut")
    assert profile["music_enabled"] is False


def test_vlog_main_reframing_none(manager):
    profile = manager.load_profile("vlog_main")
    assert profile["reframing_mode"] == "none"


def test_gaming_main_reframing_intelligent_crop(manager):
    profile = manager.load_profile("gaming_main")
    assert profile["reframing_mode"] == "intelligent_crop"
