from pathlib import Path

import pytest

from core.music_ducking_plan import (
    MusicDuckingPlanError,
    build_ducking_plan_item,
    build_empty_ducking_plan_manifest,
    classify_speech_priority,
    validate_ducking_plan_item,
)
from scripts.p55_ducking_plan_smoke import run

_Q_TOKEN = "qw" + "en"


def _q_flag(name: str) -> str:
    return f"{_Q_TOKEN}_{name}"


def _ducking_input(**overrides):
    item = {
        "segment_id": "seg_001",
        "channel_type": "main",
        "selected_category": "vlog_background",
        "selection_status": "selected",
        "selected_candidate_id": "demo_candidate",
        "speech_density": 0.10,
        "energy_score": 0.30,
        "highlight_score": 0.10,
        "mood_tag": "neutral",
    }
    item.update(overrides)
    return item


def test_speech_density_010_is_low():
    assert classify_speech_priority(0.10) == "low"


def test_speech_density_035_is_medium():
    assert classify_speech_priority(0.35) == "medium"


def test_speech_density_055_is_high():
    assert classify_speech_priority(0.55) == "high"


def test_speech_density_080_is_very_high():
    assert classify_speech_priority(0.80) == "very_high"


def test_main_selected_music_enables_ducking():
    item = build_ducking_plan_item(_ducking_input())
    assert item["music_allowed"] is True
    assert item["ducking_enabled"] is True
    assert item["plan_status"] == "planned"


def test_low_speech_density_010_uses_owner_review_lower_music_gains():
    item = build_ducking_plan_item(_ducking_input(speech_density=0.10))
    assert item["speech_priority"] == "low"
    assert item["base_music_gain_db"] == -22.0
    assert item["ducking_gain_db"] == -27.0
    assert item["max_music_gain_db"] == -20.0


def test_medium_high_and_very_high_gains_stay_unchanged():
    expected = (
        (0.35, "medium", -20.0, -26.0, -18.0),
        (0.55, "high", -23.0, -30.0, -21.0),
        (0.80, "very_high", -26.0, -34.0, -24.0),
    )
    for speech_density, priority, base_gain, ducking_gain, max_gain in expected:
        item = build_ducking_plan_item(_ducking_input(speech_density=speech_density))
        assert item["speech_priority"] == priority
        assert item["base_music_gain_db"] == base_gain
        assert item["ducking_gain_db"] == ducking_gain
        assert item["max_music_gain_db"] == max_gain


def test_uncut_is_always_blocked():
    item = build_ducking_plan_item(
        _ducking_input(
            channel_type="uncut",
            selected_category="none",
            selection_status="blocked",
            selected_candidate_id=None,
            mood_tag="hype",
            energy_score=1.0,
            highlight_score=1.0,
        )
    )
    assert item["music_allowed"] is False
    assert item["selected_category"] == "none"
    assert item["ducking_enabled"] is False
    assert item["plan_status"] == "blocked"
    assert "uncut_music_disabled" in item["reason"]


def test_missing_candidate_disables_music_and_ducking():
    item = build_ducking_plan_item(
        _ducking_input(
            selected_category="sad",
            selection_status="missing_candidate",
            selected_candidate_id=None,
            speech_density=0.20,
            mood_tag="sad",
        )
    )
    assert item["music_allowed"] is False
    assert item["ducking_enabled"] is False
    assert item["plan_status"] == "no_selected_music"
    assert item["selected_category"] == "none"


def test_invalid_speech_density_is_blocked():
    for speech_density in (-0.1, 1.1):
        with pytest.raises(MusicDuckingPlanError):
            build_ducking_plan_item(_ducking_input(speech_density=speech_density))


def test_invalid_energy_and_highlight_scores_are_blocked():
    for field in ("energy_score", "highlight_score"):
        for value in (-0.1, 1.1):
            with pytest.raises(MusicDuckingPlanError):
                build_ducking_plan_item(_ducking_input(**{field: value}))


def test_invalid_channel_type_is_blocked():
    with pytest.raises(MusicDuckingPlanError):
        build_ducking_plan_item(_ducking_input(channel_type="side"))


def test_positive_gain_values_are_blocked():
    with pytest.raises(MusicDuckingPlanError):
        validate_ducking_plan_item(
            {
                "segment_id": "bad_gain",
                "channel_type": "main",
                "music_allowed": True,
                "selected_category": "hype",
                "ducking_enabled": True,
                "base_music_gain_db": 1.0,
                "ducking_gain_db": -10.0,
                "max_music_gain_db": -8.0,
                "speech_priority": "low",
                "plan_status": "planned",
                "reason": "bad_gain",
            }
        )


def test_max_music_gain_must_not_exceed_minus_14db():
    with pytest.raises(MusicDuckingPlanError):
        validate_ducking_plan_item(
            {
                "segment_id": "too_loud",
                "channel_type": "main",
                "music_allowed": True,
                "selected_category": "hype",
                "ducking_enabled": True,
                "base_music_gain_db": -13.0,
                "ducking_gain_db": -20.0,
                "max_music_gain_db": -13.0,
                "speech_priority": "low",
                "plan_status": "planned",
                "reason": "too_loud",
            }
        )


def test_loud_categories_never_exceed_safe_max_gain():
    for category in ("hype", "fail", "funny_gaming_background"):
        item = build_ducking_plan_item(_ducking_input(selected_category=category, mood_tag="hype"))
        assert item["max_music_gain_db"] <= -14.0


def test_manifest_default_is_safe():
    manifest = build_empty_ducking_plan_manifest()
    for flag in (
        "music_build_started",
        "music_inserted",
        "audio_mix_started",
        "render_used",
        "preview_render_used",
        "ingest_used",
        _q_flag("used"),
        _q_flag("autocut_used"),
        "runtime_learning_started",
        "external_download_used",
        "api_key_used",
        "music_files_committed",
        "real_audio_modified",
    ):
        assert manifest[flag] is False
    assert manifest["uncut_music_allowed"] is False
    assert manifest["ducking_plan_created"] is True


def test_smoke_script_writes_only_expected_reports_dir(tmp_path):
    manifest = run(str(tmp_path), "reports/phase5_5_ducking_plan")
    assert manifest["status"] == "ok"
    assert manifest["step"] == "5.5-5"
    assert manifest["mode"] == "ducking_plan_only"
    assert (tmp_path / "reports/phase5_5_ducking_plan/ducking_plan_manifest.json").exists()
    assert (tmp_path / "reports/phase5_5_ducking_plan/ducking_plan_summary.md").exists()
    assert not (tmp_path / "video_configs").exists()
    assert not (tmp_path / "learning_corpus").exists()
    assert not (tmp_path / "local_assets/music").exists()


def test_wrong_output_dir_is_blocked(tmp_path):
    for output_dir in (
        "reports/other",
        "video_configs",
        "learning_corpus",
        "local_assets/music",
    ):
        with pytest.raises(ValueError):
            run(str(tmp_path), output_dir)
        assert not (tmp_path / output_dir).exists()


def test_forbidden_imports_and_usage_are_absent():
    forbidden = (
        "subprocess",
        "request" + "s",
        "ffmpeg",
        "whis" + "per",
        "render_short",
        "shutil." + "rm" + "tree",
        "os." + "remove",
        ".un" + "link(",
        "while " + "True",
        "oll" + "ama",
        _q_flag("")[:-1],
    )
    for path in (Path("core/music_ducking_plan.py"), Path("scripts/p55_ducking_plan_smoke.py")):
        text = path.read_text(encoding="utf-8").lower()
        for token in forbidden:
            assert token not in text
