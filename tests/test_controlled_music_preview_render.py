from __future__ import annotations

from pathlib import Path

import pytest

from scripts import controlled_music_preview_render as preview


def _repo_fixture(tmp_path: Path) -> Path:
    input_path = tmp_path / preview.CONFIRMED_INPUT_VIDEO
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_bytes(b"video")

    music_dir = tmp_path / preview.MAIN_MUSIC_ROOT / preview.MUSIC_CATEGORY
    music_dir.mkdir(parents=True, exist_ok=True)
    (music_dir / "b_second.mp3").write_bytes(b"music")
    (music_dir / "a_first.mp3").write_bytes(b"music")
    (tmp_path / preview.MAIN_MUSIC_ROOT / "hype").mkdir(parents=True, exist_ok=True)
    (tmp_path / preview.MAIN_MUSIC_ROOT / "hype" / "a_hype.mp3").write_bytes(b"music")
    return tmp_path


def test_default_is_dry_run_and_starts_no_render(tmp_path, monkeypatch):
    repo_root = _repo_fixture(tmp_path)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("ffmpeg must not start in dry-run")

    monkeypatch.setattr(preview.subprocess, "run", fail_if_called)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.CONFIRMED_INPUT_VIDEO,
        channel_type="main",
        output_root=preview.EXPECTED_OUTPUT_ROOT,
    )

    assert manifest["status"] == "dry_run"
    assert manifest["dry_run"] is True
    assert manifest["owner_execute_required"] is True
    assert not list((repo_root / preview.EXPECTED_OUTPUT_ROOT).rglob("*.mp4"))


def test_only_confirmed_input_is_allowed(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    with pytest.raises(preview.ControlledMusicPreviewError):
        preview.run(
            repo_root=repo_root,
            input_video="reports/other.mp4",
            channel_type="main",
            output_root=preview.EXPECTED_OUTPUT_ROOT,
        )


def test_only_main_channel_is_allowed_and_uncut_is_blocked(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    with pytest.raises(preview.ControlledMusicPreviewError):
        preview.run(
            repo_root=repo_root,
            input_video=preview.CONFIRMED_INPUT_VIDEO,
            channel_type="uncut",
            output_root=preview.EXPECTED_OUTPUT_ROOT,
        )


def test_output_scope_is_enforced(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    preview.run(
        repo_root=repo_root,
        input_video=preview.CONFIRMED_INPUT_VIDEO,
        channel_type="main",
        output_root=preview.EXPECTED_OUTPUT_ROOT,
    )

    for blocked in ("video_configs", "learning_corpus", "local_assets/music"):
        with pytest.raises(preview.ControlledMusicPreviewError):
            preview.run(
                repo_root=repo_root,
                input_video=preview.CONFIRMED_INPUT_VIDEO,
                channel_type="main",
                output_root=blocked,
            )


def test_music_source_must_be_under_main_account(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    with pytest.raises(preview.ControlledMusicPreviewError):
        preview._assert_music_source_allowed(repo_root, repo_root / "reports/music.mp3")


def test_uncut_music_source_is_blocked(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    uncut_music = repo_root / "local_assets/music/uncut/song.mp3"
    uncut_music.parent.mkdir(parents=True, exist_ok=True)
    uncut_music.write_bytes(b"music")
    with pytest.raises(preview.ControlledMusicPreviewError):
        preview._assert_music_source_allowed(repo_root, uncut_music)


def test_first_test_uses_only_vlog_background(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    selected = preview.select_music_file(repo_root)
    assert selected.name == "a_first.mp3"
    assert preview.MUSIC_CATEGORY == "vlog_background"
    assert "hype" not in selected.parts
    assert "fail" not in selected.parts
    assert "funny_gaming_background" not in selected.parts


def test_no_shell_true_is_used():
    text = Path("scripts/controlled_music_preview_render.py").read_text(encoding="utf-8")
    assert "shell=True" not in text


def test_no_upload_qwen_or_runtime_learning_flags(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.CONFIRMED_INPUT_VIDEO,
        channel_type="main",
        output_root=preview.EXPECTED_OUTPUT_ROOT,
    )
    assert manifest["upload_started"] is False
    assert manifest["runtime_learning_started"] is False
    assert manifest["qwen_used"] is False
    assert manifest["qwen_autocut_used"] is False
    assert manifest["ingest_used"] is False


def test_no_delete_functions_are_used():
    text = Path("scripts/controlled_music_preview_render.py").read_text(encoding="utf-8")
    for token in ("os.remove", "unlink", "rmtree", "Remove-Item"):
        assert token not in text


def test_manifest_safety_flags(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.CONFIRMED_INPUT_VIDEO,
        channel_type="main",
        output_root=preview.EXPECTED_OUTPUT_ROOT,
    )
    assert manifest["upload_started"] is False
    assert manifest["runtime_learning_started"] is False
    assert manifest["qwen_used"] is False
    assert manifest["qwen_autocut_used"] is False
    assert manifest["production_files_modified"] is False
    assert manifest["final_render_used"] is False
    assert manifest["owner_review_required"] is True
