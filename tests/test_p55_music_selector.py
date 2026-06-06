from pathlib import Path

import pytest

from core.music_selector import (
    MusicSelectorError,
    build_empty_music_selector_manifest,
    select_music_for_mapping,
    validate_music_candidate,
)
from scripts.p55_music_selector_smoke import run


def _candidate(**overrides):
    candidate = {
        "candidate_id": "main_intro",
        "file_path": "local_assets/music/main_account/intro/demo_intro.mp3",
        "channel_type": "main",
        "category": "intro",
        "source": "demo",
        "owner_approved": True,
        "license_status": "owner_approved",
        "intended_use": "main account",
        "mood_tags": ["intro"],
        "priority": 10,
    }
    candidate.update(overrides)
    return candidate


def _mapping(**overrides):
    mapping = {
        "segment_id": "seg_001",
        "channel_type": "main",
        "requested_category": "intro",
        "mood_tag": "intro",
        "energy_level": "medium",
        "ducking_required": False,
    }
    mapping.update(overrides)
    return mapping


def test_main_request_selects_intro_candidate(tmp_path):
    result = select_music_for_mapping(_mapping(), [_candidate()], str(tmp_path))
    assert result["selection_status"] == "selected"
    assert result["selected_candidate_id"] == "main_intro"
    assert result["selected_category"] == "intro"


def test_main_request_selects_funny_candidate(tmp_path):
    result = select_music_for_mapping(
        _mapping(requested_category="funny", mood_tag="funny"),
        [_candidate(candidate_id="main_funny", category="funny", mood_tags=["funny"])],
        str(tmp_path),
    )
    assert result["selection_status"] == "selected"
    assert result["selected_candidate_id"] == "main_funny"


def test_main_request_selects_peak_candidate(tmp_path):
    result = select_music_for_mapping(
        _mapping(requested_category="peak", mood_tag="hype", energy_level="peak"),
        [_candidate(candidate_id="main_peak", category="peak", mood_tags=["peak"], priority=30)],
        str(tmp_path),
    )
    assert result["selection_status"] == "selected"
    assert result["selected_candidate_id"] == "main_peak"


def test_uncut_request_is_always_blocked(tmp_path):
    result = select_music_for_mapping(
        _mapping(channel_type="uncut", requested_category="peak", mood_tag="hype", energy_level="peak"),
        [_candidate(category="peak")],
        str(tmp_path),
    )
    assert result["music_allowed"] is False
    assert result["selected_candidate_id"] is None
    assert result["selected_file_path"] is None
    assert result["selected_category"] == "none"
    assert result["selection_status"] == "blocked"
    assert "uncut_music_disabled" in result["reason"]


def test_uncut_candidate_is_blocked_even_with_owner_approval(tmp_path):
    with pytest.raises(MusicSelectorError):
        validate_music_candidate(
            _candidate(
                candidate_id="bad_uncut",
                channel_type="uncut",
                category="peak",
                file_path="local_assets/music/uncut/bad_uncut.mp3",
                owner_approved=True,
            ),
            str(tmp_path),
        )


def test_owner_approval_false_is_blocked(tmp_path):
    with pytest.raises(MusicSelectorError):
        validate_music_candidate(_candidate(owner_approved=False), str(tmp_path))


def test_unknown_license_status_is_blocked(tmp_path):
    with pytest.raises(MusicSelectorError):
        validate_music_candidate(_candidate(license_status="unknown"), str(tmp_path))


def test_none_category_is_blocked_for_real_candidates(tmp_path):
    with pytest.raises(MusicSelectorError):
        validate_music_candidate(_candidate(category="none"), str(tmp_path))


def test_candidate_outside_allowed_roots_is_blocked(tmp_path):
    for file_path in (
        r"C:\Users\Ali\Music\test.mp3",
        "../secret.mp3",
        "video_configs/test.mp3",
        "learning_corpus/test.mp3",
    ):
        with pytest.raises(MusicSelectorError):
            validate_music_candidate(_candidate(file_path=file_path), str(tmp_path))


def test_missing_requested_category_has_no_fallback(tmp_path):
    result = select_music_for_mapping(
        _mapping(requested_category="suspense", mood_tag="suspense"),
        [_candidate(category="intro")],
        str(tmp_path),
    )
    assert result["selection_status"] == "missing_candidate"
    assert result["selected_candidate_id"] is None
    assert result["selected_file_path"] is None
    assert result["selected_category"] == "none"


def test_highest_priority_wins(tmp_path):
    result = select_music_for_mapping(
        _mapping(),
        [
            _candidate(candidate_id="low", priority=1),
            _candidate(candidate_id="high", priority=20),
        ],
        str(tmp_path),
    )
    assert result["selected_candidate_id"] == "high"


def test_priority_tie_sorts_by_candidate_id(tmp_path):
    result = select_music_for_mapping(
        _mapping(),
        [
            _candidate(candidate_id="b_candidate", priority=10),
            _candidate(candidate_id="a_candidate", priority=10),
        ],
        str(tmp_path),
    )
    assert result["selected_candidate_id"] == "a_candidate"


def test_manifest_default_is_safe():
    manifest = build_empty_music_selector_manifest()
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
    assert manifest["metadata_only"] is True
    assert manifest["reads_music_files"] is False


def test_smoke_script_writes_only_expected_reports_dir(tmp_path):
    manifest = run(str(tmp_path), "reports/phase5_5_music_selector")
    assert manifest["status"] == "ok"
    assert manifest["step"] == "5.5-4"
    assert (tmp_path / "reports/phase5_5_music_selector/music_selector_manifest.json").exists()
    assert (tmp_path / "reports/phase5_5_music_selector/music_selector_summary.md").exists()


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
    for path in (Path("core/music_selector.py"), Path("scripts/p55_music_selector_smoke.py")):
        text = path.read_text(encoding="utf-8").lower()
        for token in forbidden:
            assert token not in text
