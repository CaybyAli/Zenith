from pathlib import Path

import pytest

from core.music_contracts import (
    ALLOWED_CATEGORIES,
    ALLOWED_LICENSE_STATUS,
    MusicContractError,
    build_empty_music_contract_manifest,
    validate_music_contract_manifest,
    validate_music_item,
    validate_music_path,
)
from scripts.p55_music_contracts_smoke import run


def _item(**overrides):
    item = {
        "file_path": "local_assets/music/main_account/intro/test.mp3",
        "category": "intro",
        "source": "owner_local",
        "owner_approved": True,
        "license_status": "owner_approved",
        "intended_use": "intro",
        "channel_type": "main",
    }
    item.update(overrides)
    return item


def test_allowed_categories_are_accepted(tmp_path):
    for category in ALLOWED_CATEGORIES:
        assert validate_music_item(_item(category=category), tmp_path)["category"] == category


def test_official_main_account_categories_are_exact():
    assert ALLOWED_CATEGORIES == (
        "intro",
        "outro",
        "vlog_background",
        "funny_gaming_background",
        "fail",
        "hype",
        "sad",
    )


def test_none_category_is_blocked_for_real_music_items(tmp_path):
    with pytest.raises(MusicContractError):
        validate_music_item(_item(category="none"), tmp_path)


def test_main_channel_type_is_accepted(tmp_path):
    result = validate_music_item(_item(channel_type="main", category="hype"), tmp_path)
    assert result["channel_type"] == "main"
    assert result["category"] == "hype"


def test_uncut_channel_type_is_blocked_for_music_items(tmp_path):
    with pytest.raises(MusicContractError):
        validate_music_item(_item(channel_type="uncut"), tmp_path)


def test_wrong_channel_type_is_blocked_for_music_items(tmp_path):
    with pytest.raises(MusicContractError):
        validate_music_item(_item(channel_type="shorts"), tmp_path)


def test_wrong_categories_are_blocked(tmp_path):
    for category in (
        "random",
        "song",
        "beat",
        "suspense",
        "calm",
        "victory",
        "emotional",
        "background",
        "peak",
        "funny",
    ):
        with pytest.raises(MusicContractError):
            validate_music_item(_item(category=category), tmp_path)


def test_allowed_roots_are_accepted(tmp_path):
    paths = (
        "local_assets/music/main_account/intro/test.mp3",
        "assets/audio/gaming_main/music/main_intro_bed.mp3",
        "assets/music/intro/test.m4a",
    )
    for path in paths:
        assert validate_music_path(tmp_path, path) == path


def test_paths_outside_allowed_roots_are_blocked(tmp_path):
    for path in (
        "video_configs/test.mp3",
        "learning_corpus/test.mp3",
        "local_assets/music/uncut/test.mp3",
        "../secret.mp3",
        r"C:\Users\Ali\Music\test.mp3",
    ):
        with pytest.raises(MusicContractError):
            validate_music_path(tmp_path, path)


def test_license_without_owner_approval_is_blocked(tmp_path):
    with pytest.raises(MusicContractError):
        validate_music_item(_item(owner_approved=False), tmp_path)
    with pytest.raises(MusicContractError):
        validate_music_item(_item(license_status="unknown"), tmp_path)


def test_allowed_license_statuses_are_accepted(tmp_path):
    for license_status in ALLOWED_LICENSE_STATUS:
        assert (
            validate_music_item(_item(license_status=license_status), tmp_path)["license_status"]
            == license_status
        )


def test_manifest_default_is_safe(tmp_path):
    manifest = validate_music_contract_manifest(build_empty_music_contract_manifest(tmp_path))
    for flag in (
        "music_build_started",
        "music_inserted",
        "render_used",
        "ingest_used",
        "qwen_autocut_used",
        "runtime_learning_started",
        "external_download_used",
        "api_key_used",
        "music_files_committed",
    ):
        assert manifest[flag] is False


def test_smoke_script_writes_only_expected_reports_dir(tmp_path):
    manifest = run(str(tmp_path), "reports/phase5_5_music_contracts")
    assert manifest["status"] == "ok"
    assert (tmp_path / "reports/phase5_5_music_contracts/music_contracts_manifest.json").exists()
    assert (tmp_path / "reports/phase5_5_music_contracts/music_contracts_summary.md").exists()


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
    )
    for path in (Path("core/music_contracts.py"), Path("scripts/p55_music_contracts_smoke.py")):
        text = path.read_text(encoding="utf-8")
        for token in forbidden:
            assert token not in text
