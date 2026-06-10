from __future__ import annotations

from pathlib import Path

import pytest

from core.music_content_type_policy import (
    CATEGORY_FUNNY_GAMING_BACKGROUND,
    CATEGORY_VLOG_BACKGROUND,
    CONTENT_TYPE_GAMING_MAIN,
    CONTENT_TYPE_UNCUT,
    CONTENT_TYPE_VLOG_MAIN,
    choose_default_preview_category_for_content_type,
)
from scripts import controlled_music_preview_render as preview

_Q_TOKEN = "qw" + "en"


def _q_flag(name: str) -> str:
    return f"{_Q_TOKEN}_{name}"


def _repo_fixture(tmp_path: Path) -> Path:
    input_path = tmp_path / preview.CONFIRMED_INPUT_VIDEO
    input_path.parent.mkdir(parents=True, exist_ok=True)
    input_path.write_bytes(b"video")
    new_input_path = tmp_path / preview.SELECTED_NEW_INPUT_VIDEO
    new_input_path.parent.mkdir(parents=True, exist_ok=True)
    new_input_path.write_bytes(b"new video")

    music_dir = tmp_path / preview.MAIN_MUSIC_ROOT / CATEGORY_FUNNY_GAMING_BACKGROUND
    music_dir.mkdir(parents=True, exist_ok=True)
    (music_dir / "b_second.mp3").write_bytes(b"music")
    (music_dir / "a_first.mp3").write_bytes(b"music")
    (tmp_path / preview.MAIN_MUSIC_ROOT / "hype").mkdir(parents=True, exist_ok=True)
    (tmp_path / preview.MAIN_MUSIC_ROOT / "hype" / "a_hype.mp3").write_bytes(b"music")
    vlog_dir = tmp_path / preview.MAIN_MUSIC_ROOT / CATEGORY_VLOG_BACKGROUND
    vlog_dir.mkdir(parents=True, exist_ok=True)
    (vlog_dir / "a_vlog.mp3").write_bytes(b"music")
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
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.EXPECTED_OUTPUT_ROOT,
    )

    assert manifest["status"] == "dry_run"
    assert manifest["dry_run"] is True
    assert manifest["owner_execute_required"] is True
    assert not list((repo_root / preview.EXPECTED_OUTPUT_ROOT).rglob("*.mp4"))


def test_dry_run_reports_intro_offset_policy(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.CONFIRMED_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.EXPECTED_OUTPUT_ROOT,
    )
    assert manifest["intro_offset_policy_used"] is True


def test_dry_run_reports_demo_quiet_intro_trim_without_boost(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.CONFIRMED_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.EXPECTED_OUTPUT_ROOT,
    )
    assert manifest["quiet_intro_detected"] is True
    assert manifest["music_start_offset_sec"] == 30.0
    assert manifest["intro_trim_used"] is True
    assert manifest["intro_boost_used"] is False
    assert manifest["intro_boost_gain_db"] == 0.0


def test_dry_run_reports_lower_low_speech_gains(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.CONFIRMED_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.EXPECTED_OUTPUT_ROOT,
    )
    assert manifest["low_speech_base_music_gain_db"] == -27.0
    assert manifest["low_speech_ducking_gain_db"] == -32.0
    assert manifest["low_speech_max_music_gain_db"] == -25.0
    assert manifest["low_speech_volume_reduced_total_db"] == 10.0


def test_script_never_auto_boosts_intro(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.CONFIRMED_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.EXPECTED_OUTPUT_ROOT,
    )
    assert manifest["intro_boost_used"] is False


def test_only_confirmed_input_is_allowed(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    with pytest.raises(preview.ControlledMusicPreviewError, match="input_not_in_allowed_controlled_preview_inputs"):
        preview.run(
            repo_root=repo_root,
            input_video="reports/other.mp4",
            channel_type="main",
            content_type=CONTENT_TYPE_GAMING_MAIN,
            output_root=preview.EXPECTED_OUTPUT_ROOT,
        )


def test_selected_new_clip_is_allowed(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.SELECTED_NEW_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP9_OUTPUT_ROOT,
    )

    assert manifest["status"] == "dry_run"
    assert manifest["input_video_path"] == preview.SELECTED_NEW_INPUT_VIDEO.as_posix()
    assert manifest["input_video_path"] != preview.CONFIRMED_INPUT_VIDEO.as_posix()
    assert manifest["content_type"] == CONTENT_TYPE_GAMING_MAIN
    assert manifest["music_category"] == CATEGORY_FUNNY_GAMING_BACKGROUND
    assert manifest["vlog_background_blocked_for_gaming_main"] is True
    assert manifest["music_start_offset_sec"] == 30.0
    assert manifest["intro_boost_used"] is False
    assert manifest["low_speech_base_music_gain_db"] == -27.0
    assert manifest["low_speech_ducking_gain_db"] == -32.0
    assert manifest["low_speech_max_music_gain_db"] == -25.0
    assert manifest["owner_execute_required"] is True
    assert not list((repo_root / preview.STEP9_OUTPUT_ROOT).rglob("*.mp4"))


def test_disallowed_controlled_preview_inputs_are_blocked(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    blocked_inputs = (
        "learning_corpus/pairs/pair_001/raw.mp4",
        "local_assets/music/main_account/funny_gaming_background/test.mp3",
        "video_configs/something.mp4",
        "reports/controlled_music_preview_run/irgendwas.mp4",
    )

    for blocked_input in blocked_inputs:
        with pytest.raises(
            preview.ControlledMusicPreviewError,
            match="input_not_in_allowed_controlled_preview_inputs",
        ):
            preview.run(
                repo_root=repo_root,
                input_video=blocked_input,
                channel_type="main",
                content_type=CONTENT_TYPE_GAMING_MAIN,
                output_root=preview.EXPECTED_OUTPUT_ROOT,
            )


def test_only_main_channel_is_allowed_and_uncut_is_blocked(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    with pytest.raises(preview.ControlledMusicPreviewError):
        preview.run(
            repo_root=repo_root,
            input_video=preview.CONFIRMED_INPUT_VIDEO,
            channel_type="uncut",
            content_type=CONTENT_TYPE_GAMING_MAIN,
            output_root=preview.EXPECTED_OUTPUT_ROOT,
        )


def test_output_scope_is_enforced(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    preview.run(
        repo_root=repo_root,
        input_video=preview.CONFIRMED_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.EXPECTED_OUTPUT_ROOT,
    )

    for blocked in ("video_configs", "learning_corpus", "local_assets/music"):
        with pytest.raises(preview.ControlledMusicPreviewError):
            preview.run(
                repo_root=repo_root,
                input_video=preview.CONFIRMED_INPUT_VIDEO,
                channel_type="main",
                content_type=CONTENT_TYPE_GAMING_MAIN,
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


def test_rocket_league_k7_preview_uses_gaming_main(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.CONFIRMED_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.EXPECTED_OUTPUT_ROOT,
    )
    assert manifest["content_type"] == CONTENT_TYPE_GAMING_MAIN


def test_controlled_preview_does_not_choose_vlog_background_for_gaming_main(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    selected, category = preview.select_music_file(repo_root, CONTENT_TYPE_GAMING_MAIN)
    assert selected.name == "a_first.mp3"
    assert category == CATEGORY_FUNNY_GAMING_BACKGROUND
    assert category != CATEGORY_VLOG_BACKGROUND
    assert "vlog_background" not in selected.parts


def test_gaming_main_default_category_is_funny_gaming_background():
    assert (
        choose_default_preview_category_for_content_type(CONTENT_TYPE_GAMING_MAIN)
        == CATEGORY_FUNNY_GAMING_BACKGROUND
    )


def test_no_fallback_from_gaming_main_to_vlog_background(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    funny_dir = repo_root / preview.MAIN_MUSIC_ROOT / CATEGORY_FUNNY_GAMING_BACKGROUND
    for path in funny_dir.glob("*.mp3"):
        path.rename(path.with_suffix(".disabled"))
    with pytest.raises(preview.ControlledMusicPreviewError):
        preview.select_music_file(repo_root, CONTENT_TYPE_GAMING_MAIN)


def test_vlog_content_cannot_choose_gaming_category_for_confirmed_input(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    with pytest.raises(preview.ControlledMusicPreviewError):
        preview.select_music_file(repo_root, CONTENT_TYPE_VLOG_MAIN)


def test_uncut_content_remains_blocked(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    with pytest.raises(preview.ControlledMusicPreviewError):
        preview.select_music_file(repo_root, CONTENT_TYPE_UNCUT)


def test_first_fix_test_uses_only_funny_gaming_background(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    selected, category = preview.select_music_file(repo_root, CONTENT_TYPE_GAMING_MAIN)
    assert selected.name == "a_first.mp3"
    assert category == CATEGORY_FUNNY_GAMING_BACKGROUND
    assert "hype" not in selected.parts
    assert "fail" not in selected.parts
    assert CATEGORY_VLOG_BACKGROUND not in selected.parts


def test_no_shell_true_is_used():
    text = Path("scripts/controlled_music_preview_render.py").read_text(encoding="utf-8")
    assert "shell" + "=True" not in text


def test_ffmpeg_command_with_intro_offset_is_complete(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    input_video = repo_root / preview.CONFIRMED_INPUT_VIDEO
    music_path, _category = preview.select_music_file(repo_root, CONTENT_TYPE_GAMING_MAIN)
    output_path = repo_root / preview.EXPECTED_OUTPUT_ROOT / "run_test" / preview.OUTPUT_FILENAME

    command = preview.build_ffmpeg_command(
        input_video,
        music_path,
        output_path,
        music_start_offset_sec=30.0,
    )

    assert "-stream_loop" in command
    assert "-1" in command
    assert "-ss" in command
    assert "30.000" in command
    assert command.count("-i") == 2
    assert str(music_path) in command
    assert "-filter_complex" in command
    assert "-map" in command
    assert command[-1] == str(output_path)


def test_ffmpeg_command_without_output_is_rejected(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    input_video = repo_root / preview.CONFIRMED_INPUT_VIDEO
    music_path, _category = preview.select_music_file(repo_root, CONTENT_TYPE_GAMING_MAIN)

    with pytest.raises(preview.ControlledMusicPreviewError):
        preview.validate_ffmpeg_command(
            ["ffmpeg", "-hide_banner", "-i", str(input_video), "-i", str(music_path)],
            music_file=music_path,
            output_video=Path(""),
        )


def test_ffmpeg_command_without_music_input_is_rejected(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    output_path = repo_root / preview.EXPECTED_OUTPUT_ROOT / "run_test" / preview.OUTPUT_FILENAME

    with pytest.raises(preview.ControlledMusicPreviewError):
        preview.validate_ffmpeg_command(
            ["ffmpeg", "-hide_banner", "-i", str(repo_root / preview.CONFIRMED_INPUT_VIDEO), str(output_path)],
            music_file=repo_root / preview.MAIN_MUSIC_ROOT / CATEGORY_FUNNY_GAMING_BACKGROUND / "missing.mp3",
            output_video=output_path,
        )


def test_ffmpeg_command_must_not_end_after_stream_loop(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    music_path, _category = preview.select_music_file(repo_root, CONTENT_TYPE_GAMING_MAIN)
    output_path = repo_root / preview.EXPECTED_OUTPUT_ROOT / "run_test" / preview.OUTPUT_FILENAME

    with pytest.raises(preview.ControlledMusicPreviewError):
        preview.validate_ffmpeg_command(
            ["ffmpeg", "-hide_banner", "-y", "-i", "input.mp4", "-stream_loop", "-1"],
            music_file=music_path,
            output_video=output_path,
        )


def test_execute_path_uses_complete_ffmpeg_builder(tmp_path, monkeypatch):
    repo_root = _repo_fixture(tmp_path)
    captured = {}

    class Completed:
        returncode = 0
        stdout = "ok"
        stderr = ""

    def fake_run(command, **kwargs):
        captured["command"] = command
        captured["kwargs"] = kwargs
        return Completed()

    monkeypatch.setattr(preview.subprocess, "run", fake_run)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.CONFIRMED_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.EXPECTED_OUTPUT_ROOT,
        execute_owner_go=True,
    )

    command = captured["command"]
    assert manifest["status"] == "ok"
    assert command[0] == "ffmpeg"
    assert command[-1].endswith(preview.OUTPUT_FILENAME)
    assert "-ss" in command
    assert "30.000" in command
    assert str(repo_root / preview.MAIN_MUSIC_ROOT / CATEGORY_FUNNY_GAMING_BACKGROUND / "a_first.mp3") in command
    assert "-filter_complex" in command
    assert command.count("-map") >= 2
    assert captured["kwargs"]["capture_output"] is True
    assert captured["kwargs"]["text"] is True


def test_no_upload_model_or_runtime_learning_flags(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.CONFIRMED_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.EXPECTED_OUTPUT_ROOT,
    )
    assert manifest["upload_started"] is False
    assert manifest["runtime_learning_started"] is False
    assert manifest[_q_flag("used")] is False
    assert manifest[_q_flag("autocut_used")] is False
    assert manifest["ingest_used"] is False


def test_no_delete_functions_are_used():
    text = Path("scripts/controlled_music_preview_render.py").read_text(encoding="utf-8")
    forbidden = (
        "os." + "remove",
        "un" + "link",
        "rm" + "tree",
        "Remove" + "-Item",
    )
    for token in forbidden:
        assert token not in text


def test_manifest_safety_flags(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.CONFIRMED_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.EXPECTED_OUTPUT_ROOT,
    )
    assert manifest["upload_started"] is False
    assert manifest["runtime_learning_started"] is False
    assert manifest[_q_flag("used")] is False
    assert manifest[_q_flag("autocut_used")] is False
    assert manifest["production_files_modified"] is False
    assert manifest["final_render_used"] is False
    assert manifest["owner_review_required"] is True
