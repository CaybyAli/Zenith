from pathlib import Path

import pytest

from core.music_energy_mapping import (
    MusicEnergyMappingError,
    build_empty_energy_mapping_manifest,
    classify_energy_level,
    map_segment_to_music,
    validate_energy_segment,
)
from scripts.p55_energy_to_music_mapping_smoke import run


def _segment(**overrides):
    segment = {
        "segment_id": "seg_001",
        "start_sec": 0.0,
        "end_sec": 10.0,
        "segment_role": "gameplay",
        "energy_score": 0.40,
        "highlight_score": 0.10,
        "speech_density": 0.10,
        "mood_tag": "neutral",
        "channel_type": "main",
    }
    segment.update(overrides)
    return segment


def test_energy_level_classification():
    assert classify_energy_level(0.10) == "low"
    assert classify_energy_level(0.40) == "medium"
    assert classify_energy_level(0.70) == "high"
    assert classify_energy_level(0.90) == "peak"


def test_intro_role_maps_to_intro():
    assert map_segment_to_music(_segment(segment_role="intro"))["music_category"] == "intro"
    assert map_segment_to_music(_segment(segment_role="intro"))["music_allowed"] is True


def test_outro_role_maps_to_outro():
    assert map_segment_to_music(_segment(segment_role="outro"))["music_category"] == "outro"


def test_highlight_role_maps_to_hype():
    assert map_segment_to_music(_segment(segment_role="highlight"))["music_category"] == "hype"


def test_gameplay_without_highlight_maps_to_vlog_background():
    low = map_segment_to_music(_segment(energy_score=0.20, highlight_score=0.10))
    medium = map_segment_to_music(_segment(energy_score=0.50, highlight_score=0.20))
    assert low["music_category"] == "vlog_background"
    assert medium["music_category"] == "vlog_background"


def test_high_energy_or_high_highlight_maps_to_hype():
    assert map_segment_to_music(_segment(energy_score=0.80))["music_category"] == "hype"
    assert map_segment_to_music(_segment(highlight_score=0.75))["music_category"] == "hype"


def test_speech_density_sets_ducking_flag():
    assert map_segment_to_music(_segment(speech_density=0.35))["ducking_required"] is True
    assert map_segment_to_music(_segment(speech_density=0.34))["ducking_required"] is False


def test_invalid_scores_are_blocked():
    for field in ("energy_score", "highlight_score", "speech_density"):
        for value in (-0.1, 1.1):
            with pytest.raises(MusicEnergyMappingError):
                validate_energy_segment(_segment(**{field: value}))


def test_negative_or_wrong_times_are_blocked():
    with pytest.raises(MusicEnergyMappingError):
        validate_energy_segment(_segment(start_sec=-0.1))
    with pytest.raises(MusicEnergyMappingError):
        validate_energy_segment(_segment(start_sec=10.0, end_sec=10.0))
    with pytest.raises(MusicEnergyMappingError):
        validate_energy_segment(_segment(start_sec=11.0, end_sec=10.0))


def test_wrong_roles_and_moods_are_blocked():
    for role in ("song", "beat", "random"):
        with pytest.raises(MusicEnergyMappingError):
            validate_energy_segment(_segment(segment_role=role))
    for mood in ("angry", "unknown", "victory", "emotional", "background", "peak", "tense"):
        with pytest.raises(MusicEnergyMappingError):
            validate_energy_segment(_segment(mood_tag=mood))


def test_main_channel_type_can_map_music():
    mapped = map_segment_to_music(_segment(channel_type="main", mood_tag="funny"))
    assert mapped["music_allowed"] is True
    assert mapped["music_category"] == "funny_gaming_background"


def test_uncut_channel_type_disables_music():
    mapped = map_segment_to_music(
        _segment(
            channel_type="uncut",
            segment_role="highlight",
            energy_score=1.0,
            highlight_score=1.0,
            mood_tag="hype",
            speech_density=0.80,
        )
    )
    assert mapped["music_allowed"] is False
    assert mapped["music_category"] == "none"
    assert mapped["ducking_required"] is False
    assert mapped["reason"] == "uncut_music_disabled"


def test_uncut_ignores_mood_energy_and_highlight():
    for mood in ("funny", "hype"):
        mapped = map_segment_to_music(
            _segment(channel_type="uncut", mood_tag=mood, energy_score=1.0, highlight_score=1.0)
        )
        assert mapped["music_allowed"] is False
        assert mapped["music_category"] == "none"


def test_main_mood_specific_mapping():
    expected = {
        "funny": "funny_gaming_background",
        "suspense": "hype",
        "fail": "fail",
        "sad": "sad",
        "calm": "vlog_background",
        "neutral": "vlog_background",
        "hype": "hype",
    }
    for mood, category in expected.items():
        assert map_segment_to_music(_segment(mood_tag=mood))["music_category"] == category


def test_main_highlight_or_high_energy_maps_to_hype():
    assert map_segment_to_music(_segment(segment_role="highlight"))["music_category"] == "hype"
    assert map_segment_to_music(_segment(energy_score=0.90, mood_tag="hype"))["music_category"] == "hype"


def test_wrong_channel_type_is_blocked():
    with pytest.raises(MusicEnergyMappingError):
        validate_energy_segment(_segment(channel_type="side"))


def test_manifest_default_is_safe():
    manifest = build_empty_energy_mapping_manifest()
    for flag in (
        "music_build_started",
        "music_inserted",
        "render_used",
        "preview_render_used",
        "ingest_used",
        "qwen_used",
        "qwen_autocut_used",
        "runtime_learning_started",
        "external_download_used",
        "api_key_used",
        "music_files_committed",
    ):
        assert manifest[flag] is False
    assert manifest["main_account_music_allowed"] is True
    assert manifest["uncut_music_allowed"] is False
    assert manifest["uncut_music_category"] == "none"
    assert manifest["channel_rules_enforced"] is True


def test_smoke_script_writes_only_expected_reports_dir(tmp_path):
    manifest = run(str(tmp_path), "reports/phase5_5_energy_to_music_mapping")
    assert manifest["status"] == "ok"
    assert (tmp_path / "reports/phase5_5_energy_to_music_mapping/energy_to_music_mapping_manifest.json").exists()
    assert (tmp_path / "reports/phase5_5_energy_to_music_mapping/energy_to_music_mapping_summary.md").exists()


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
        "requests",
        "ffmpeg",
        "whisper",
        "render_short",
        "shutil.rmtree",
        "os.remove",
        ".unlink(",
        "while True",
        "ollama",
        "qwen",
    )
    for path in (Path("core/music_energy_mapping.py"), Path("scripts/p55_energy_to_music_mapping_smoke.py")):
        text = path.read_text(encoding="utf-8").lower()
        for token in forbidden:
            assert token not in text
