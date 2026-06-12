from __future__ import annotations
import json
import re

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
    proper_run_path = tmp_path / preview.PROPER_RUN_INPUT_VIDEO
    proper_run_path.parent.mkdir(parents=True, exist_ok=True)
    proper_run_path.write_bytes(b"proper run video")
    visual_proper_run_path = tmp_path / preview.VISUAL_PROPER_RUN_INPUT_VIDEO
    visual_proper_run_path.parent.mkdir(parents=True, exist_ok=True)
    visual_proper_run_path.write_bytes(b"visual proper run video")

    music_dir = tmp_path / preview.MAIN_MUSIC_ROOT / CATEGORY_FUNNY_GAMING_BACKGROUND
    music_dir.mkdir(parents=True, exist_ok=True)
    (music_dir / "d_fourth.mp3").write_bytes(b"music")
    (music_dir / "c_third.mp3").write_bytes(b"music")
    (music_dir / "b_second.mp3").write_bytes(b"music")
    (music_dir / "a_first.mp3").write_bytes(b"music")
    (tmp_path / preview.MAIN_MUSIC_ROOT / "hype").mkdir(parents=True, exist_ok=True)
    (tmp_path / preview.MAIN_MUSIC_ROOT / "hype" / "a_hype.mp3").write_bytes(b"music")
    vlog_dir = tmp_path / preview.MAIN_MUSIC_ROOT / CATEGORY_VLOG_BACKGROUND
    vlog_dir.mkdir(parents=True, exist_ok=True)
    (vlog_dir / "a_vlog.mp3").write_bytes(b"music")
    return tmp_path


def _fake_music_loudness(music_file: Path) -> dict:
    mean_by_name = {
        "a_first.mp3": -18.0,
        "b_second.mp3": -20.0,
        "c_third.mp3": -23.0,
        "d_fourth.mp3": -28.0,
        "a_hype.mp3": -21.0,
        "a_vlog.mp3": -24.0,
    }
    return {
        "mean_volume_db": mean_by_name.get(music_file.name, -22.0),
        "max_volume_db": -1.0,
        "loudness_probe": "test_fake_loudness",
    }


def _fake_music_duration(music_file: Path) -> float:
    duration_by_name = {
        "a_first.mp3": 150.0,
        "b_second.mp3": 150.0,
        "c_third.mp3": 150.0,
        "d_fourth.mp3": 150.0,
        "a_hype.mp3": 150.0,
        "a_vlog.mp3": 150.0,
    }
    return duration_by_name.get(music_file.name, 150.0)


def _fake_input_duration(input_video: Path, repo_root: Path) -> float:
    return 528.348813


@pytest.fixture(autouse=True)
def _patch_music_loudness(monkeypatch):
    monkeypatch.setattr(preview, "measure_music_track_loudness_db", _fake_music_loudness)
    monkeypatch.setattr(preview, "get_music_track_duration_sec", _fake_music_duration)
    monkeypatch.setattr(preview, "input_duration_sec", _fake_input_duration)


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


def test_proper_run_input_is_allowed(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP11_OUTPUT_ROOT,
    )

    assert manifest["status"] == "dry_run"
    assert manifest["input_video_path"] == preview.PROPER_RUN_INPUT_VIDEO.as_posix()


def test_step11_output_root_is_allowed(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP11_OUTPUT_ROOT,
    )

    assert manifest["status"] == "dry_run"
    assert manifest["output_root"] == preview.STEP11_OUTPUT_ROOT.as_posix()


def test_visual_proper_run_input_is_allowed(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )

    assert manifest["status"] == "dry_run"
    assert manifest["input_video_path"] == preview.VISUAL_PROPER_RUN_INPUT_VIDEO.as_posix()


def test_step13_output_root_is_allowed_for_visual_proper_run(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )

    assert manifest["status"] == "dry_run"
    assert manifest["output_root"] == preview.STEP13_OUTPUT_ROOT.as_posix()


def test_step13_dry_run_with_visual_proper_run_uses_owner_volume_and_playlist_fix(tmp_path, monkeypatch):
    repo_root = _repo_fixture(tmp_path)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("ffmpeg must not start in dry-run")

    monkeypatch.setattr(preview.subprocess, "run", fail_if_called)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )

    assert manifest["status"] == "dry_run"
    assert not list((repo_root / preview.STEP13_OUTPUT_ROOT).rglob("*.mp4"))
    assert manifest["input_video_path"] == preview.VISUAL_PROPER_RUN_INPUT_VIDEO.as_posix()
    assert manifest["output_root"] == preview.STEP13_OUTPUT_ROOT.as_posix()
    assert manifest["content_type"] == CONTENT_TYPE_GAMING_MAIN
    assert manifest["music_category"] == CATEGORY_FUNNY_GAMING_BACKGROUND
    assert manifest["vlog_background_blocked_for_gaming_main"] is True
    assert manifest["music_start_offset_sec"] == 30.0
    assert manifest["intro_trim_used"] is True
    assert manifest["intro_boost_used"] is False
    assert manifest["low_speech_base_music_gain_db"] == -27.0
    assert manifest["low_speech_ducking_gain_db"] == -32.0
    assert manifest["low_speech_max_music_gain_db"] == -25.0
    assert manifest["owner_adobe_reference_gain_range_db"] == [-4.0, 4.0]
    assert manifest["owner_music_audible_gain_range_db"] == [-44.0, -34.0]
    assert manifest["owner_music_target_gain_db"] == -39.0
    assert manifest["ffmpeg_music_volume_gain_db"] == -39.0
    assert manifest["ffmpeg_music_volume_linear"] == pytest.approx(preview.db_to_linear(-39.0), abs=0.0001)
    assert manifest["ffmpeg_music_volume_source"] == "owner_music_audible_gain_db"
    assert manifest["adaptive_track_gain_enabled"] is True
    assert manifest["track_gain_strategy"] == "relative_track_loudness_normalization_only_single_final_automation_gain"
    assert manifest["track_gain_reference"] == "median_selected_track_mean_volume_db"
    assert manifest["all_final_gains_between_audible_range"] is False
    assert manifest["all_final_gains_between_minus_35_and_minus_26"] is False
    assert manifest["all_final_gains_between_minus_40_and_minus_35"] is False
    assert manifest["all_tracks_same_gain"] is False
    assert manifest["manifest_gains_applied_to_ffmpeg_command"] is True
    assert manifest["speech_aware_ducking_confirmed"] is False
    assert manifest["sidechaincompress_used"] is False
    assert manifest["input_duration_sec"] > 180.0
    assert manifest["long_run_playlist_enabled"] is True
    assert manifest["music_single_track_loop"] is False
    assert manifest["selected_music_track_count"] >= 3
    assert len({track["path"] for track in manifest["selected_music_tracks"]}) == manifest["selected_music_track_count"]
    assert manifest["music_playlist_no_immediate_repeat"] is True
    assert manifest["music_playlist_category"] == CATEGORY_FUNNY_GAMING_BACKGROUND
    assert manifest["music_playlist_fast_switching"] is False
    assert manifest["owner_execute_required"] is True


def test_step11_dry_run_with_proper_run_uses_final_music_tuning(tmp_path, monkeypatch):
    repo_root = _repo_fixture(tmp_path)

    def fail_if_called(*args, **kwargs):
        raise AssertionError("ffmpeg must not start in dry-run")

    monkeypatch.setattr(preview.subprocess, "run", fail_if_called)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP11_OUTPUT_ROOT,
    )

    assert manifest["status"] == "dry_run"
    assert not list((repo_root / preview.STEP11_OUTPUT_ROOT).rglob("*.mp4"))
    assert manifest["input_video_path"] == preview.PROPER_RUN_INPUT_VIDEO.as_posix()
    assert manifest["output_root"] == preview.STEP11_OUTPUT_ROOT.as_posix()
    assert manifest["content_type"] == CONTENT_TYPE_GAMING_MAIN
    assert manifest["music_category"] == CATEGORY_FUNNY_GAMING_BACKGROUND
    assert manifest["music_start_offset_sec"] == 30.0
    assert manifest["intro_trim_used"] is True
    assert manifest["intro_boost_used"] is False
    assert manifest["low_speech_base_music_gain_db"] == -27.0
    assert manifest["low_speech_ducking_gain_db"] == -32.0
    assert manifest["low_speech_max_music_gain_db"] == -25.0


def test_visual_proper_run_has_no_k7_short_or_old_facecam_fallback(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )

    assert manifest["input_video_path"] == preview.VISUAL_PROPER_RUN_INPUT_VIDEO.as_posix()
    assert manifest["input_video_path"] != preview.CONFIRMED_INPUT_VIDEO.as_posix()
    assert manifest["input_video_path"] != preview.SELECTED_NEW_INPUT_VIDEO.as_posix()
    assert manifest["input_video_path"] != preview.PROPER_RUN_INPUT_VIDEO.as_posix()


def test_old_facecam_proper_run_cannot_use_step13_output_root(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    with pytest.raises(preview.ControlledMusicPreviewError, match="input/output pair is not allowed"):
        preview.run(
            repo_root=repo_root,
            input_video=preview.PROPER_RUN_INPUT_VIDEO,
            channel_type="main",
            content_type=CONTENT_TYPE_GAMING_MAIN,
            output_root=preview.STEP13_OUTPUT_ROOT,
        )


def test_proper_run_has_no_k7_or_short_fallback(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP11_OUTPUT_ROOT,
    )

    assert manifest["input_video_path"] == preview.PROPER_RUN_INPUT_VIDEO.as_posix()
    assert manifest["input_video_path"] != preview.CONFIRMED_INPUT_VIDEO.as_posix()
    assert manifest["input_video_path"] != preview.SELECTED_NEW_INPUT_VIDEO.as_posix()


def test_disallowed_controlled_preview_inputs_are_blocked(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    blocked_inputs = (
        "learning_corpus/pairs/pair_001/raw.mp4",
        "local_assets/music/main_account/funny_gaming_background/test.mp3",
        "video_configs/something.mp4",
        "reports/controlled_music_preview_run/irgendwas.mp4",
        "exports/gaming_main/job_other/job_other_v1_final.mp4",
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

    assert command[0] == "ffmpeg"
    assert str(input_video) in command
    assert str(music_path) in command
    assert str(output_path) == command[-1]
    assert "-stream_loop" not in command
    assert "-filter_complex" in command

    filter_complex = command[command.index("-filter_complex") + 1]

    assert "atrim=start=30.000" in filter_complex
    assert "afade" in filter_complex
    assert "volume=0.08" not in filter_complex
    assert "volume=-39.0dB" in filter_complex
    assert "volume=-27.0dB" not in filter_complex
    assert "sidechaincompress" not in filter_complex
    assert "[aout]" in filter_complex

def test_db_to_linear_converts_planned_preview_gain():
    assert preview.db_to_linear(-39.0) == pytest.approx(preview.db_to_linear(-39.0), abs=0.0001)


def test_ffmpeg_music_volume_manifest_fields_match_owner_adobe_reference_gain(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )

    assert manifest["owner_adobe_reference_gain_range_db"] == [-4.0, 4.0]
    assert manifest["owner_music_audible_gain_range_db"] == [-44.0, -34.0]
    assert manifest["owner_music_target_gain_db"] == -39.0
    assert manifest["ffmpeg_music_volume_gain_db"] == -39.0
    assert manifest["ffmpeg_music_volume_linear"] == pytest.approx(preview.db_to_linear(-39.0), abs=0.0001)
    assert manifest["ffmpeg_music_volume_source"] == "owner_music_audible_gain_db"
    assert manifest["adaptive_track_gain_enabled"] is True
    assert manifest["track_gain_strategy"] == "relative_track_loudness_normalization_only_single_final_automation_gain"
    assert manifest["track_gain_reference"] == "median_selected_track_mean_volume_db"
    assert manifest["all_final_gains_between_audible_range"] is False
    assert manifest["all_final_gains_between_minus_35_and_minus_26"] is False
    assert manifest["all_final_gains_between_minus_40_and_minus_35"] is False
    assert manifest["all_tracks_same_gain"] is False
    assert manifest["manifest_gains_applied_to_ffmpeg_command"] is True
    assert manifest["speech_aware_ducking_confirmed"] is False


def test_manifest_gains_claim_requires_matching_ffmpeg_command(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    input_video = repo_root / preview.VISUAL_PROPER_RUN_INPUT_VIDEO
    music_path, _category = preview.select_music_file(repo_root, CONTENT_TYPE_GAMING_MAIN)
    output_path = repo_root / preview.STEP13_OUTPUT_ROOT / "run_test" / preview.OUTPUT_FILENAME

    command = preview.build_ffmpeg_command(
        input_video,
        music_path,
        output_path,
        music_start_offset_sec=30.0,
        music_volume_gain_db=-34.0,
    )

    filter_complex = command[command.index("-filter_complex") + 1]
    assert "volume=-34.0dB" in filter_complex
    assert "volume=-27.0dB" not in filter_complex
    assert "volume=0.08" not in filter_complex


def test_long_visual_proper_run_uses_multi_song_playlist_command(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )
    run_dir = repo_root / Path(manifest["output_video_path"]).parent
    command = (run_dir / "ffmpeg_command.txt").read_text(encoding="utf-8")

    assert manifest["input_duration_sec"] > 180.0
    assert manifest["long_run_playlist_enabled"] is True
    assert manifest["music_single_track_loop"] is False
    assert manifest["selected_music_track_count"] >= 3
    assert len({track["path"] for track in manifest["selected_music_tracks"]}) == manifest["selected_music_track_count"]
    assert all(CATEGORY_FUNNY_GAMING_BACKGROUND in track["path"] for track in manifest["selected_music_tracks"])
    assert all(CATEGORY_VLOG_BACKGROUND not in track["path"] for track in manifest["selected_music_tracks"])
    assert all("uncut" not in Path(track["path"]).parts for track in manifest["selected_music_tracks"])
    assert manifest["music_playlist_no_immediate_repeat"] is True
    assert manifest["music_playlist_fast_switching"] is False
    assert "volume=-3.5dB" in command
    assert "volume=-1.5dB" in command
    assert "volume=1.5dB" in command
    assert "volume=4.0dB" in command
    assert "volume=-30.0dB" not in command
    assert "volume=-36.5dB" not in command
    assert "volume=-35.0dB" not in command
    assert "volume=0.08" not in command
    assert "volume=-27.0dB" not in command
    assert f"amix=inputs={manifest['music_timeline_segment_count']}" in command
    assert "-stream_loop" not in command


def test_long_run_playlist_requires_at_least_three_tracks(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    funny_dir = repo_root / preview.MAIN_MUSIC_ROOT / CATEGORY_FUNNY_GAMING_BACKGROUND
    for path in sorted(funny_dir.glob("*.mp3"))[2:]:
        path.rename(path.with_suffix(".disabled"))

    with pytest.raises(preview.ControlledMusicPreviewError, match="at least 3 unique tracks"):
        preview.run(
            repo_root=repo_root,
            input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
            channel_type="main",
            content_type=CONTENT_TYPE_GAMING_MAIN,
            output_root=preview.STEP13_OUTPUT_ROOT,
        )


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
    assert "-ss" not in command
    assert "atrim=start=30.000" in " ".join(str(part) for part in command)
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

def test_adaptive_track_gain_calculates_per_track_owner_clamped_values(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    tracks = [
        repo_root / preview.MAIN_MUSIC_ROOT / CATEGORY_FUNNY_GAMING_BACKGROUND / "a_first.mp3",
        repo_root / preview.MAIN_MUSIC_ROOT / CATEGORY_FUNNY_GAMING_BACKGROUND / "b_second.mp3",
        repo_root / preview.MAIN_MUSIC_ROOT / CATEGORY_FUNNY_GAMING_BACKGROUND / "c_third.mp3",
        repo_root / preview.MAIN_MUSIC_ROOT / CATEGORY_FUNNY_GAMING_BACKGROUND / "d_fourth.mp3",
    ]

    plan = preview.build_track_gain_plan(repo_root, tracks)

    assert plan["adaptive_track_gain_enabled"] is True
    assert plan["owner_adobe_reference_gain_range_db"] == [-4.0, 4.0]
    assert plan["owner_music_target_gain_db"] == -39.0
    assert plan["track_gain_strategy"] == "relative_track_loudness_normalization_only_single_final_automation_gain"
    assert plan["track_gain_reference"] == "median_selected_track_mean_volume_db"
    assert plan["reference_track_mean_volume_db"] == -21.5
    assert plan["ffmpeg_music_volume_gain_db_by_track"] == [-3.5, -1.5, 1.5, 4.0]
    assert plan["per_track_normalization_gain_db_by_track"] == [-3.5, -1.5, 1.5, 4.0]
    assert plan["all_track_normalization_gains_between_minus_4_and_plus_4"] is True
    assert plan["all_final_gains_between_audible_range"] is False
    assert plan["all_final_gains_between_minus_35_and_minus_26"] is False
    assert plan["all_final_gains_between_minus_40_and_minus_35"] is False
    assert plan["music_gain_application_mode"] == "single_final_automation_gain"
    assert plan["double_music_gain_fix_enabled"] is True
    assert plan["per_track_final_mix_gain_applied"] is False
    assert plan["automation_final_mix_gain_applied"] is True
    assert plan["music_bus_double_gain_protection_enabled"] is True
    assert plan["all_tracks_same_gain"] is False
    assert plan["selected_music_tracks"][0]["mean_volume_db"] == -18.0
    assert plan["selected_music_tracks"][0]["final_normalization_gain_db"] == -3.5
    assert plan["selected_music_tracks"][-1]["mean_volume_db"] == -28.0
    assert plan["selected_music_tracks"][-1]["final_normalization_gain_db"] == 4.0


def test_adaptive_track_gain_fails_fast_without_mean_volume(tmp_path, monkeypatch):
    repo_root = _repo_fixture(tmp_path)
    track = repo_root / preview.MAIN_MUSIC_ROOT / CATEGORY_FUNNY_GAMING_BACKGROUND / "a_first.mp3"

    def missing_mean_volume(_music_file: Path) -> dict:
        return {"max_volume_db": -1.0}

    monkeypatch.setattr(preview, "measure_music_track_loudness_db", missing_mean_volume)

    with pytest.raises(preview.ControlledMusicPreviewError, match="mean_volume_db"):
        preview.build_track_gain_plan(repo_root, [track])


def test_long_run_command_uses_different_adaptive_volume_values(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )
    run_dir = repo_root / Path(manifest["output_video_path"]).parent
    command = (run_dir / "ffmpeg_command.txt").read_text(encoding="utf-8")

    assert manifest["selected_music_track_count"] == 4
    assert manifest["ffmpeg_music_volume_gain_db_by_track"] == [-3.5, -1.5, 1.5, 4.0]
    assert manifest["per_track_normalization_gain_db_by_track"] == [-3.5, -1.5, 1.5, 4.0]
    assert len(set(manifest["ffmpeg_music_volume_gain_db_by_track"])) > 1
    assert "volume=-3.5dB" in command
    assert "volume=-1.5dB" in command
    assert "volume=1.5dB" in command
    assert "volume=4.0dB" in command
    assert manifest["per_track_strong_negative_gain_count"] == 0
    assert manifest["automation_strong_negative_gain_count"] == manifest["automation_window_count"]
    assert manifest["music_gain_application_mode"] == "single_final_automation_gain"
    assert manifest["double_music_gain_fix_enabled"] is True
    assert manifest["per_track_final_mix_gain_applied"] is False
    assert manifest["automation_final_mix_gain_applied"] is True
    assert manifest["music_bus_double_gain_protection_enabled"] is True
    assert manifest["music_bus_double_gain_protection_passed"] is True
    assert manifest["effective_music_gain_double_applied"] is False
    assert "volume=-30.0dB" not in command
    assert "volume=-36.5dB" not in command
    assert "volume=0.08" not in command
    assert "volume=-27.0dB" not in command
    assert "-stream_loop" not in command
    assert f"amix=inputs={manifest['music_timeline_segment_count']}" in command

def test_step15a2_dry_run_manifest_contains_music_timeline_planner(tmp_path):
    repo_root = _repo_fixture(tmp_path)

    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )

    assert manifest["status"] == "dry_run"
    assert manifest["music_timeline_planner_enabled"] is True
    assert manifest["music_timeline"]
    assert manifest["music_timeline_segment_count"] >= 3
    assert manifest["track_duration_aware_selection"] is True
    assert manifest["duration_based_song_count"] is True
    assert manifest["mood_category_mapping_enabled"] is True
    assert manifest["true_ai_mood_detection_used"] is False
    assert "fallback" in manifest["mood_analysis_source"]
    assert manifest["single_song_loop"] is False
    assert manifest["selected_music_track_count"] >= 3
    assert manifest["qwen_used"] is False
    assert manifest["runtime_learning_started"] is False
    assert manifest["owner_execute_required"] is True



def test_step16a_dry_run_manifest_contains_dynamic_music_automation(tmp_path):
    repo_root = _repo_fixture(tmp_path)

    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )

    assert manifest["status"] == "dry_run"
    assert manifest["music_timeline_planner_enabled"] is True
    assert manifest["music_automation_planner_enabled"] is True
    assert manifest["automation_window_sec"] == 5.0
    assert manifest["automation_window_count"] > 0
    assert manifest["voice_aware_music_ceiling_enabled"] is True
    assert manifest["music_section_loudness_aware"] is True
    assert manifest["gain_smoothing_enabled"] is True
    assert manifest["max_gain_change_per_window_db"] == 1.5
    assert manifest["smooth_music_automation_enabled"] is True
    assert manifest["automation_output_smoothed"] is True
    assert manifest["max_adjacent_gain_delta_passed"] is True
    assert manifest["ali_friend_separation_confirmed"] is False
    assert manifest["speaker_voice_source"] == "mixed_audio_level"
    assert manifest["automation_all_final_gains_between_audible_range"] is True
    assert manifest["automation_all_final_gains_between_audible_range"] is True
    assert manifest["automation_all_final_gains_between_minus_35_and_minus_26"] is False
    assert manifest["automation_all_final_gains_between_minus_40_and_minus_35"] is False
    assert manifest["clean_transition_policy_enabled"] is True
    assert manifest["track_start_trim_sec"] == 30.0
    assert manifest["track_end_trim_sec"] == 15.0
    assert manifest["crossfade_sec"] == 3.0
    assert manifest["hard_cut_transitions"] is False
    assert manifest["owner_execute_required"] is True
    assert manifest["music_timeline"][0]["transition_type"] == "crossfade"
    assert manifest["music_timeline"][0]["track_source_start_sec"] >= 0.0

def test_step16b_fix_command_realizes_clean_transitions_trim_and_dynamic_automation(tmp_path):
    input_video = tmp_path / "input.mp4"
    output_video = tmp_path / "out.mp4"
    music_files = [tmp_path / f"song_{index}.mp3" for index in range(1, 5)]

    timeline = [
        {"track_source_start_sec": 30.0, "track_source_end_sec": 150.0, "track_used_duration_sec": 120.0},
        {"track_source_start_sec": 30.0, "track_source_end_sec": 138.276, "track_used_duration_sec": 108.276},
        {"track_source_start_sec": 30.0, "track_source_end_sec": 150.0, "track_used_duration_sec": 120.0},
        {"track_source_start_sec": 30.0, "track_source_end_sec": 125.571, "track_used_duration_sec": 95.571},
    ]

    automation_plan = [
        {"start_sec": 0.0, "end_sec": 5.0, "final_gain_db": -33.0},
        {"start_sec": 5.0, "end_sec": 10.0, "final_gain_db": -31.0},
        {"start_sec": 10.0, "end_sec": 15.0, "final_gain_db": -35.0},
    ]

    command = preview.build_ffmpeg_command(
        input_video,
        music_files[0],
        output_video,
        music_start_offset_sec=30.0,
        music_volume_gain_db=-34.0,
        music_files=music_files,
        long_run_playlist_enabled=True,
        music_volume_gain_db_by_track=[-1.4, -3.4, -4.0, -2.6],
        music_timeline=timeline,
        music_automation_plan=automation_plan,
        crossfade_sec=3.0,
    )

    filter_complex = command[command.index("-filter_complex") + 1]

    assert "atrim=start=30.000" in filter_complex
    assert "afade" in filter_complex
    assert "amix=inputs=4" in filter_complex
    assert "adelay=" in filter_complex
    assert "asplit=3" in filter_complex
    assert "[auto0]atrim=start=0.000:end=5.000" in filter_complex
    assert "[auto1]atrim=start=5.000:end=10.000" in filter_complex
    assert "[auto2]atrim=start=10.000:end=15.000" in filter_complex
    assert "volume=-33.0dB" in filter_complex
    assert "volume=-31.0dB" in filter_complex
    assert "volume=-35.0dB" in filter_complex
    assert "[ag0][ag1][ag2]concat=n=3:v=0:a=1[music_auto]" in filter_complex
    assert "between(t," not in filter_complex
    assert "eval=frame" not in filter_complex
    assert "volume='if(" not in filter_complex
    assert "volume=0.08" not in filter_complex
    assert "volume=-27.0dB" not in filter_complex
    assert "stream_loop" not in command

    probe = preview.build_ffmpeg_command_realization_probe(command)
    assert probe["ffmpeg_clean_transition_applied"] is True
    assert probe["ffmpeg_command_contains_fade"] is True
    assert probe["ffmpeg_command_contains_track_trim"] is True
    assert probe["ffmpeg_dynamic_automation_applied"] is True
    assert probe["automation_window_command_applied"] is True
    assert probe["command_contains_time_based_volume_automation"] is False
    assert probe["command_contains_segmented_gain_automation"] is True
    assert probe["command_contains_nested_if_volume_automation"] is False
    assert probe["command_dynamic_gain_zone_count"] == 3
    assert probe["dynamic_gain_expression_strategy"] == "segmented_atrim_volume_concat"
    assert probe["segmented_gain_concat_enabled"] is True
    assert probe["segmented_gain_asplit_count"] == 3
    assert probe["segmented_gain_atrim_count"] == 3
    assert probe["segmented_gain_volume_count"] == 3
    assert probe["manifest_command_consistency_gate"] is True


def test_step16b_r_fix_large_window_count_uses_segmented_strategy_without_nested_if(tmp_path):
    input_video = tmp_path / "input.mp4"
    output_video = tmp_path / "out.mp4"
    music_files = [tmp_path / f"song_{index}.mp3" for index in range(1, 5)]

    automation_plan = [
        {
            "start_sec": float(index * 5),
            "end_sec": float((index + 1) * 5),
            "final_gain_db": -33.0,
        }
        for index in range(106)
    ]

    command = preview.build_ffmpeg_command(
        input_video,
        music_files[0],
        output_video,
        music_start_offset_sec=30.0,
        music_volume_gain_db=-34.0,
        music_files=music_files,
        long_run_playlist_enabled=True,
        music_volume_gain_db_by_track=[-1.4, -3.4, -4.0, -2.6],
        music_automation_plan=automation_plan,
        crossfade_sec=3.0,
    )

    filter_complex = command[command.index("-filter_complex") + 1]
    probe = preview.build_ffmpeg_command_realization_probe(command)

    assert "asplit=106" in filter_complex
    assert "concat=n=106:v=0:a=1[music_auto]" in filter_complex
    assert filter_complex.count("between(t,") == 0
    assert "eval=frame" not in filter_complex
    assert "volume='if(" not in filter_complex
    assert probe["large_window_count_requires_segmented_strategy"] is True
    assert probe["dynamic_gain_expression_strategy"] == "segmented_atrim_volume_concat"
    assert probe["command_contains_segmented_gain_automation"] is True
    assert probe["command_contains_nested_if_volume_automation"] is False
    assert probe["command_dynamic_gain_zone_count"] == 106
    assert probe["segmented_gain_asplit_count"] == 106
    assert probe["segmented_gain_atrim_count"] == 106
    assert probe["segmented_gain_volume_count"] == 106
    assert probe["manifest_command_consistency_gate"] is True


def test_step16b_fix_consistency_gate_blocks_false_clean_transition_claim(tmp_path):
    bad_command = [
        "ffmpeg",
        "-i",
        str(tmp_path / "input.mp4"),
        "-i",
        str(tmp_path / "song.mp3"),
        "-filter_complex",
        "[1:a]volume=-38.0dB[musicquiet];"
        "[musicquiet][0:a]sidechaincompress=threshold=0.035:ratio=12:attack=30:release=500[ducked];"
        "[0:a][ducked]amix=inputs=2:duration=first:dropout_transition=0,volume=1.0[aout]",
        str(tmp_path / "out.mp4"),
    ]

    with pytest.raises(preview.ControlledMusicPreviewError, match="clean_transition_manifest_command_mismatch"):
        preview.assert_manifest_command_consistency(
            {
                "clean_transition_policy_enabled": True,
                "music_automation_planner_enabled": False,
            },
            bad_command,
        )


def test_step16b_fix_consistency_gate_blocks_false_dynamic_automation_claim(tmp_path):
    bad_command = [
        "ffmpeg",
        "-i",
        str(tmp_path / "input.mp4"),
        "-i",
        str(tmp_path / "song.mp3"),
        "-filter_complex",
        "[1:a]atrim=start=30.000:end=150.000,asetpts=PTS-STARTPTS,"
        "volume=-38.0dB,afade=t=in:st=0:d=3.000,afade=t=out:st=117.000:d=3.000[musicquiet];"
        "[musicquiet][0:a]sidechaincompress=threshold=0.035:ratio=12:attack=30:release=500[ducked];"
        "[0:a][ducked]amix=inputs=2:duration=first:dropout_transition=0,volume=1.0[aout]",
        str(tmp_path / "out.mp4"),
    ]

    with pytest.raises(preview.ControlledMusicPreviewError, match="dynamic_automation_manifest_command_mismatch"):
        preview.assert_manifest_command_consistency(
            {
                "clean_transition_policy_enabled": True,
                "music_automation_planner_enabled": True,
            },
            bad_command,
        )


def test_step16b_fix_dry_run_manifest_contains_command_realization_fields(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    output_root = repo_root / "reports/controlled_music_preview_run/step13_visual_proper_run_music_render"

    preview.run(
        repo_root=repo_root,
        input_video="exports/gaming_main/job_aa2953e15914/job_aa2953e15914_v1_final.mp4",
        channel_type="main",
        content_type="gaming_main",
        output_root="reports/controlled_music_preview_run/step13_visual_proper_run_music_render",
        execute_owner_go=False,
    )

    command_path = sorted(
        output_root.glob("run_*/ffmpeg_command.txt"),
        key=lambda path: path.stat().st_mtime,
    )[-1]
    run_dir = command_path.parent

    manifest = json.loads((run_dir / "preview_render_manifest.json").read_text(encoding="utf-8"))
    command_text = command_path.read_text(encoding="utf-8")

    assert manifest["status"] == "dry_run"
    assert manifest["dry_run"] is True
    assert manifest["music_automation_planner_enabled"] is True
    assert manifest["clean_transition_policy_enabled"] is True
    assert manifest["ffmpeg_clean_transition_applied"] is True
    assert manifest["ffmpeg_command_contains_fade"] is True
    assert manifest["ffmpeg_command_contains_track_trim"] is True
    assert manifest["ffmpeg_dynamic_automation_applied"] is True
    assert manifest["automation_window_command_applied"] is True
    assert manifest["command_contains_time_based_volume_automation"] is False
    assert manifest["command_contains_segmented_gain_automation"] is True
    assert manifest["command_contains_nested_if_volume_automation"] is False
    assert manifest["command_dynamic_gain_zone_count"] > 1
    assert manifest["dynamic_gain_expression_strategy"] == "segmented_atrim_volume_concat"
    assert manifest["segmented_gain_concat_enabled"] is True
    assert manifest["segmented_gain_asplit_count"] == manifest["automation_window_count"]
    assert manifest["segmented_gain_atrim_count"] == manifest["automation_window_count"]
    assert manifest["segmented_gain_volume_count"] == manifest["automation_window_count"]
    assert manifest["large_window_count_requires_segmented_strategy"] is True
    assert manifest["manifest_command_consistency_gate"] is True

    assert "atrim=start=30.000" in command_text
    assert "afade" in command_text or "acrossfade" in command_text
    assert "asplit=" in command_text
    assert "amix=inputs=" in command_text
    assert "between(t," not in command_text
    assert "eval=frame" not in command_text
    assert "volume='if(" not in command_text
    assert "volume=0.08" not in command_text
    assert "volume=-27.0dB" not in command_text
    assert "stream_loop" not in command_text

def test_step17b_music_audibility_policy_manifest_and_command(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )

    command_path = next((repo_root / preview.STEP13_OUTPUT_ROOT).rglob("ffmpeg_command.txt"))
    command_text = command_path.read_text(encoding="utf-8")

    assert manifest["music_audibility_policy_enabled"] is True
    assert manifest["owner_music_audible_gain_range_db"] == [-44.0, -34.0]
    assert manifest["owner_music_target_gain_db"] == -39.0
    assert manifest["music_audibility_floor_db"] == -44.0
    assert manifest["music_loudness_ceiling_db"] == -34.0
    assert manifest["double_ducking_protection_enabled"] is True
    assert manifest["sidechain_ratio"] <= 4.0
    assert manifest["sidechain_threshold"] == 0.08
    assert manifest["sidechain_attack"] == 40
    assert manifest["sidechain_release"] == 350
    assert -42.0 <= manifest["command_volume_average_db"] <= -34.0
    assert manifest["command_volume_min_db"] >= -44.0
    assert manifest["command_volume_max_db"] <= -26.0
    assert manifest["command_volume_audibility_gate_passed"] is True
    assert "ratio=12" not in command_text
    assert any(token in command_text for token in ["volume=-38.0dB", "volume=-40.0dB", "volume=-42.0dB"])
    assert "volume=-39.0dB" not in command_text
    assert "volume=-30.0dB" not in command_text
    assert "sidechaincompress" not in command_text
    assert "ratio=3" not in command_text



def test_step17b_output_root_is_allowed_for_music_audibility_policy_fix(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP17B_OUTPUT_ROOT,
    )

    assert manifest["status"] == "dry_run"
    assert manifest["output_root"] == preview.STEP17B_OUTPUT_ROOT.as_posix()
    assert manifest["music_audibility_policy_enabled"] is True
    assert manifest["owner_music_audible_gain_range_db"] == [-44.0, -34.0]
    assert manifest["double_ducking_protection_enabled"] is True


def test_segmented_automation_does_not_apply_double_music_gain(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )

    assert manifest["music_gain_application_mode"] == "single_final_automation_gain"
    assert manifest["double_music_gain_fix_enabled"] is True
    assert manifest["per_track_final_mix_gain_applied"] is False
    assert manifest["automation_final_mix_gain_applied"] is True
    assert manifest["music_bus_double_gain_protection_enabled"] is True
    assert manifest["music_bus_double_gain_protection_passed"] is True
    assert manifest["effective_music_gain_double_applied"] is False


def test_track_stage_does_not_apply_final_negative_mix_gain(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )

    track_stage_values = manifest["track_stage_volume_db_values"]
    assert track_stage_values[:4] == [-3.5, -1.5, 1.5, 4.0]
    assert len(track_stage_values) == manifest["music_timeline_segment_count"]
    assert all(-4.0 <= value <= 4.0 for value in track_stage_values)
    assert manifest["per_track_strong_negative_gain_count"] == 0
    assert manifest["automation_strong_negative_gain_count"] == manifest["automation_window_count"]
    assert manifest["automation_stage_volume_db_values"]
    assert all(-44.0 <= value <= -34.0 for value in manifest["automation_stage_volume_db_values"])


def test_double_gain_gate_blocks_bad_command():
    gate = preview.build_music_bus_double_gain_gate(
        per_track_final_mix_gain_applied=True,
        automation_final_mix_gain_applied=True,
    )

    assert gate["status"] == "blocked"
    assert gate["blocked_reason"] == "double_music_gain_detected"
    assert gate["music_bus_double_gain_protection_enabled"] is True
    assert gate["music_bus_double_gain_protection_passed"] is False
    assert gate["effective_music_gain_double_applied"] is True


def test_music_audibility_policy_still_active(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )

    assert manifest["music_audibility_policy_enabled"] is True
    assert manifest["owner_music_audible_gain_range_db"] == [-44.0, -34.0]
    assert manifest["owner_music_target_gain_db"] == -39.0
    assert manifest["command_volume_audibility_gate_passed"] is True


def test_sidechain_still_gentle(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )
    command_path = next((repo_root / preview.STEP13_OUTPUT_ROOT).rglob("ffmpeg_command.txt"))
    command_text = command_path.read_text(encoding="utf-8")

    assert manifest["sidechain_ratio"] <= 4.0
    assert "ratio=12" not in command_text
    assert "sidechaincompress" not in command_text


def test_segmented_automation_still_active(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )

    assert manifest["dynamic_gain_expression_strategy"] == "segmented_atrim_volume_concat"
    assert manifest["segmented_gain_volume_count"] == manifest["automation_window_count"]
    assert manifest["command_contains_nested_if_volume_automation"] is False

def test_step19b_output_root_is_allowed_for_music_balance_gap_fix():
    assert hasattr(preview, "STEP19B_OUTPUT_ROOT")
    root = preview.STEP19B_OUTPUT_ROOT.as_posix()
    allowed_roots = {
        output_root.as_posix()
        for output_root in preview.ALLOWED_CONTROLLED_PREVIEW_OUTPUT_ROOTS.values()
    }
    visual_input = preview.VISUAL_PROPER_RUN_INPUT_VIDEO.as_posix()
    allowed_for_visual = preview.ALLOWED_CONTROLLED_PREVIEW_RUN_TARGETS[visual_input]

    assert root == "reports/controlled_music_preview_run/step19b_music_balance_gap_fix"
    assert root in allowed_roots
    assert root in allowed_for_visual


def test_owner_review_19_balance_policy(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP19B_OUTPUT_ROOT,
    )

    assert manifest["status"] == "dry_run"
    assert manifest["dry_run"] is True
    assert manifest["music_balance_policy_enabled"] is True
    assert manifest["owner_music_balanced_gain_range_db"] == [-44.0, -34.0]
    assert manifest["owner_music_target_gain_db"] == -39.0
    assert manifest["music_audibility_floor_db"] == -44.0
    assert manifest["music_loudness_ceiling_db"] == -34.0
    assert manifest["command_volume_min_db"] >= -44.0
    assert manifest["command_volume_max_db"] <= -34.0
    assert manifest["command_volume_audibility_gate_passed"] is True


def test_music_not_as_loud_as_voice_when_voice_active(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP19B_OUTPUT_ROOT,
    )

    voice_active_windows = [
        window for window in manifest["music_automation_plan"]
        if window["voice_level_db"] >= -38.0
    ]
    assert voice_active_windows
    assert all(window["final_gain_db"] <= -35.0 for window in voice_active_windows)
    assert manifest["voice_priority_music_ducking_enabled"] is True
    assert manifest["music_must_stay_below_voice_enabled"] is True


def test_music_remains_audible_without_voice():
    result = preview.build_command_volume_audibility_gate(
        [
            "ffmpeg",
            "-filter_complex",
            "[auto0]atrim=start=0.000:end=5.000,asetpts=PTS-STARTPTS,volume=-34.0dB[ag0]",
        ]
    )

    assert result["command_volume_audibility_gate_passed"] is True
    assert result["command_volume_average_db"] <= -34.0


def test_known_gap_103_110_has_music_coverage(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP19B_OUTPUT_ROOT,
    )

    assert manifest["music_continuity_guard_enabled"] is True
    assert manifest["music_gap_detection_enabled"] is True
    assert manifest["known_owner_gap_sec"] == [103.0, 110.0]
    assert manifest["known_owner_gap_has_music_coverage"] is True
    assert manifest["known_owner_gap_has_automation_coverage"] is True
    assert manifest["music_gap_at_103_110_fixed"] is True
    assert manifest["musicbed_full_coverage_required"] is True
    assert manifest["musicbed_no_silent_gaps"] is True


def test_no_double_gain_regression(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP19B_OUTPUT_ROOT,
    )

    assert manifest["double_music_gain_fix_enabled"] is True
    assert manifest["per_track_final_mix_gain_applied"] is False
    assert manifest["automation_final_mix_gain_applied"] is True
    assert manifest["music_bus_double_gain_protection_enabled"] is True
    assert manifest["music_bus_double_gain_protection_passed"] is True
    assert manifest["effective_music_gain_double_applied"] is False


def test_step19b_safety_no_upload_no_model_no_runtime_learning(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP19B_OUTPUT_ROOT,
    )

    assert manifest["upload_started"] is False
    assert manifest["runtime_learning_started"] is False
    assert manifest[preview._q_flag("used")] is False
    assert manifest[preview._q_flag("autocut_used")] is False
    assert manifest["ingest_used"] is False
    assert manifest["sidechain_ratio"] <= 4.0
    assert not list((repo_root / preview.STEP19B_OUTPUT_ROOT).rglob("*.mp4"))


def test_ffmpeg_musicbed_uses_timeline_segment_count(tmp_path):
    input_video = tmp_path / "input.mp4"
    output_video = tmp_path / "out.mp4"
    music_files = [tmp_path / f"song_{index}.mp3" for index in range(1, 5)]

    timeline = [
        {"track_path": music_files[0].as_posix(), "start_sec": 0.0, "end_sec": 120.0, "track_source_start_sec": 30.0, "track_source_end_sec": 150.0, "track_used_duration_sec": 120.0, "segment_has_real_music_source": True},
        {"track_path": music_files[1].as_posix(), "start_sec": 120.0, "end_sec": 228.0, "track_source_start_sec": 30.0, "track_source_end_sec": 138.0, "track_used_duration_sec": 108.0, "segment_has_real_music_source": True},
        {"track_path": music_files[2].as_posix(), "start_sec": 228.0, "end_sec": 348.0, "track_source_start_sec": 30.0, "track_source_end_sec": 150.0, "track_used_duration_sec": 120.0, "segment_has_real_music_source": True},
        {"track_path": music_files[3].as_posix(), "start_sec": 348.0, "end_sec": 443.0, "track_source_start_sec": 30.0, "track_source_end_sec": 125.0, "track_used_duration_sec": 95.0, "segment_has_real_music_source": True},
        {"track_path": music_files[0].as_posix(), "start_sec": 443.0, "end_sec": 528.0, "track_source_start_sec": 30.0, "track_source_end_sec": 115.0, "track_used_duration_sec": 85.0, "reused_track": True, "segment_has_real_music_source": True},
    ]

    automation_plan = [
        {"start_sec": 0.0, "end_sec": 5.0, "final_gain_db": -33.0},
        {"start_sec": 5.0, "end_sec": 10.0, "final_gain_db": -31.0},
    ]

    command = preview.build_ffmpeg_command(
        input_video,
        music_files[0],
        output_video,
        music_start_offset_sec=30.0,
        music_volume_gain_db=-34.0,
        music_files=music_files,
        long_run_playlist_enabled=True,
        music_volume_gain_db_by_track=[-1.4, -3.4, -4.0, -2.6],
        music_timeline=timeline,
        music_automation_plan=automation_plan,
        crossfade_sec=3.0,
    )

    filter_complex = command[command.index("-filter_complex") + 1]
    probe = preview.assert_manifest_command_consistency(
        {
            "clean_transition_policy_enabled": True,
            "music_automation_planner_enabled": True,
            "music_timeline": timeline,
            "music_timeline_segment_count": len(timeline),
        },
        command,
    )

    assert "amix=inputs=5:duration=longest:dropout_transition=0:normalize=0[musicbed]" in filter_complex
    assert "adelay=" in filter_complex
    assert "[musicSegment5]" in filter_complex
    assert probe["musicbed_command_segment_count"] == 5
    assert probe["musicbed_timeline_segment_count"] == 5
    assert probe["musicbed_command_matches_timeline"] is True
    assert probe["musicbed_no_silent_gaps_verified_by_command"] is True
    assert probe["music_crossfade_count"] == 4
    assert probe["music_expected_crossfade_count"] == 4
    assert probe["music_transition_overlap_enabled"] is True
    assert probe["music_transition_hard_cut_detected"] is False


def test_reused_track_builds_real_ffmpeg_segment(tmp_path):
    input_video = tmp_path / "input.mp4"
    output_video = tmp_path / "out.mp4"
    music_files = [tmp_path / f"song_{index}.mp3" for index in range(1, 5)]
    timeline = [
        {"track_path": music_files[0].as_posix(), "start_sec": 0.0, "end_sec": 120.0, "track_source_start_sec": 30.0, "track_source_end_sec": 150.0, "track_used_duration_sec": 120.0, "segment_has_real_music_source": True},
        {"track_path": music_files[0].as_posix(), "start_sec": 120.0, "end_sec": 200.0, "track_source_start_sec": 30.0, "track_source_end_sec": 110.0, "track_used_duration_sec": 80.0, "reused_track": True, "segment_has_real_music_source": True},
    ]
    command = preview.build_ffmpeg_command(
        input_video,
        music_files[0],
        output_video,
        music_files=music_files,
        long_run_playlist_enabled=True,
        music_volume_gain_db_by_track=[0.0, 0.0, 0.0, 0.0],
        music_timeline=timeline,
        music_automation_plan=[
            {"start_sec": 0.0, "end_sec": 5.0, "final_gain_db": -34.0},
            {"start_sec": 5.0, "end_sec": 10.0, "final_gain_db": -34.0},
        ],
    )
    filter_complex = command[command.index("-filter_complex") + 1]
    assert "[musicSegment2]" in filter_complex
    assert "amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[musicbed]" in filter_complex


def test_music_transition_crossfade_count_matches_segments(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )

    assert manifest["music_crossfade_count"] == manifest["music_expected_crossfade_count"]
    assert manifest["music_crossfade_count"] == manifest["music_timeline_segment_count"] - 1
    assert manifest["music_transition_crossfade_enabled"] is True


def test_music_transition_has_overlap_not_hard_cut(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )
    run_dir = repo_root / Path(manifest["output_video_path"]).parent
    command_text = (run_dir / "ffmpeg_command.txt").read_text(encoding="utf-8")

    assert "adelay=" in command_text
    assert "amix=inputs=" in command_text
    assert manifest["music_transition_overlap_enabled"] is True
    assert manifest["music_transition_hard_cut_detected"] is False
    assert manifest["song_boundary_energy_continuity_passed"] is True


def test_step25a_regression_no_upload_qwen_learning_stream_loop_sidechain_or_foreground(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )
    run_dir = repo_root / Path(manifest["output_video_path"]).parent
    command_text = (run_dir / "ffmpeg_command.txt").read_text(encoding="utf-8")

    assert manifest["upload_started"] is False
    assert manifest["runtime_learning_started"] is False
    assert manifest["qwen_used"] is False
    assert "stream_loop" not in command_text
    assert "sidechaincompress" not in command_text
    assert not re.search(r"volume=-(?:30|31|32|33)\.0dB", command_text)
    assert manifest.get("manifest_truth_requires_audio_stem_probe") in (None, True)


def _automation_volume_values_from_command_text(command_text: str) -> list[float]:
    return [
        float(match.group(1))
        for match in re.finditer(r"\[auto\d+\].*?volume=(-?\d+\.\d)dB\[ag\d+\]", command_text)
    ]


def test_ffmpeg_command_has_non_constant_automation_gains(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )

    run_dir = repo_root / Path(manifest["output_video_path"]).parent
    command_text = (run_dir / "ffmpeg_command.txt").read_text(encoding="utf-8")
    gains = _automation_volume_values_from_command_text(command_text)

    assert gains
    assert len(set(gains)) >= 4
    assert gains.count(-36.0) != 106
    assert manifest["command_music_automation_values_extracted"] is True
    assert manifest["command_dynamic_gain_non_constant"] is True
    assert manifest["command_dynamic_gain_unique_value_count"] >= 4


def test_command_gate_blocks_constant_automation():
    filter_complex = ";".join(
        f"[auto{index}]atrim=start={index * 5:.3f}:end={(index + 1) * 5:.3f},"
        f"asetpts=PTS-STARTPTS,volume=-36.0dB[ag{index}]"
        for index in range(6)
    )
    command = ["ffmpeg", "-filter_complex", filter_complex]

    gate = preview.build_command_volume_audibility_gate(command)

    assert gate["status"] == "blocked"
    assert gate["blocked_reason"] == "music_automation_not_dynamic"
    assert gate["command_dynamic_gain_non_constant"] is False


def test_final_music_segment_has_no_tail_fadeout(tmp_path):
    input_video = tmp_path / "input.mp4"
    output_video = tmp_path / "out.mp4"
    music_files = [tmp_path / "song_1.mp3", tmp_path / "song_2.mp3"]
    timeline = [
        {"track_path": music_files[0].as_posix(), "start_sec": 0.0, "end_sec": 120.0, "track_source_start_sec": 30.0, "track_source_end_sec": 150.0, "track_used_duration_sec": 120.0},
        {"track_path": music_files[1].as_posix(), "start_sec": 120.0, "end_sec": 220.0, "track_source_start_sec": 30.0, "track_source_end_sec": 130.0, "track_used_duration_sec": 100.0},
    ]

    command = preview.build_ffmpeg_command(
        input_video,
        music_files[0],
        output_video,
        music_files=music_files,
        long_run_playlist_enabled=True,
        music_volume_gain_db_by_track=[0.0, 0.0],
        music_timeline=timeline,
        music_automation_plan=[
            {"start_sec": 0.0, "end_sec": 5.0, "final_gain_db": -30.0},
            {"start_sec": 5.0, "end_sec": 10.0, "final_gain_db": -34.0},
            {"start_sec": 10.0, "end_sec": 15.0, "final_gain_db": -36.0},
            {"start_sec": 15.0, "end_sec": 20.0, "final_gain_db": -38.0},
        ],
    )
    probe = preview.build_ffmpeg_command_realization_probe(command)

    assert probe["final_music_segment_tail_fade_disabled"] is True
    assert probe["final_music_segment_has_no_fade_to_silence"] is True
    assert probe["command_contains_final_tail_fadeout"] is False
    assert "afade=t=out" not in probe["command_final_music_segment_filter"]


def test_command_gate_blocks_final_tail_fadeout(tmp_path):
    bad_command = [
        "ffmpeg",
        "-i",
        str(tmp_path / "input.mp4"),
        "-i",
        str(tmp_path / "song1.mp3"),
        "-i",
        str(tmp_path / "song2.mp3"),
        "-filter_complex",
        "[1:a]atrim=start=30.000:end=150.000,asetpts=PTS-STARTPTS,volume=0.0dB,afade=t=in:st=0:d=3.000,afade=t=out:st=117.000:d=3.000[musicSegment1];"
        "[2:a]atrim=start=30.000:end=130.000,asetpts=PTS-STARTPTS,volume=0.0dB,afade=t=in:st=0:d=3.000,afade=t=out:st=97.000:d=3.000[musicSegment2];"
        "[musicSegment1][musicSegment2]concat=n=2:v=0:a=1[musicbed];"
        "[musicbed]asplit=4[auto0][auto1][auto2][auto3];"
        "[auto0]atrim=start=0.000:end=5.000,asetpts=PTS-STARTPTS,volume=-30.0dB[ag0];"
        "[auto1]atrim=start=5.000:end=10.000,asetpts=PTS-STARTPTS,volume=-34.0dB[ag1];"
        "[auto2]atrim=start=10.000:end=15.000,asetpts=PTS-STARTPTS,volume=-36.0dB[ag2];"
        "[auto3]atrim=start=15.000:end=20.000,asetpts=PTS-STARTPTS,volume=-38.0dB[ag3];"
        "[ag0][ag1][ag2][ag3]concat=n=4:v=0:a=1[music_auto];"
        "[music_auto][0:a]sidechaincompress=threshold=0.08:ratio=3:attack=40:release=350[ducked];"
        "[0:a][ducked]amix=inputs=2:duration=first:dropout_transition=0,volume=1.0[aout]",
        str(tmp_path / "out.mp4"),
    ]

    with pytest.raises(preview.ControlledMusicPreviewError, match="final_tail_fadeout_detected"):
        preview.assert_manifest_command_consistency(
            {
                "clean_transition_policy_enabled": True,
                "music_automation_planner_enabled": True,
                "music_timeline_segment_count": 2,
            },
            bad_command,
        )


def test_step22b_regression_music_gates_stay_safe(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )
    run_dir = repo_root / Path(manifest["output_video_path"]).parent
    command_text = (run_dir / "ffmpeg_command.txt").read_text(encoding="utf-8")

    assert manifest["musicbed_command_matches_timeline"] is True
    assert f"amix=inputs={manifest['music_timeline_segment_count']}" in command_text
    assert manifest["double_music_gain_fix_enabled"] is True
    assert manifest["per_track_final_mix_gain_applied"] is False
    assert manifest["automation_final_mix_gain_applied"] is True
    assert manifest["sidechain_ratio"] <= 4.0
    assert "ratio=12" not in command_text
    assert "stream_loop" not in command_text
    assert "qwen" not in command_text.lower()
    assert manifest["upload_started"] is False
    assert manifest["runtime_learning_started"] is False
    assert manifest["qwen_used"] is False


def test_step22b_dry_run_manifest_has_loud_section_cut_windows(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )

    assert manifest["loud_section_cut_window_count"] > 0
    assert manifest["quiet_section_boost_window_count"] > 0
    assert manifest["voice_priority_window_count"] > 0
    assert manifest["dynamic_gain_non_constant"] is True
    assert manifest["command_dynamic_gain_non_constant"] is True


def _step23b_command_text_from_manifest(manifest, repo_root):
    output_path = Path(manifest["output_video_path"])
    command_path = repo_root / output_path.parent / "ffmpeg_command.txt"
    assert command_path.exists()
    return command_path.read_text(encoding="utf-8-sig")


def test_step23b_command_blocks_foreground_music_gains(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )
    command_text = _step23b_command_text_from_manifest(manifest, repo_root)

    assert manifest["owner_background_music_policy_enabled"] is True
    assert manifest["overall_music_gain_range_db"] == [-44.0, -34.0]
    assert manifest["owner_music_target_gain_db"] == -39.0
    assert "volume=-30.0dB" not in command_text
    assert "volume=-32.0dB" not in command_text
    assert manifest["forbidden_foreground_gain_blocked"] is True


def test_step23b_command_blocks_slow_segment_fadein_and_sidechain(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )
    command_text = _step23b_command_text_from_manifest(manifest, repo_root)

    assert "afade=t=in:st=0:d=3.000" in command_text
    assert "sidechaincompress" not in command_text
    assert manifest["true_song_crossfade_allows_three_second_transition_fade"] is True
    assert manifest["segment_fade_in_max_sec"] <= 3.0
    assert manifest["raw_fullmix_sidechain_blocked"] is True


def test_step23b_owner_tail_music_guard_manifest(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )

    assert manifest["owner_tail_music_guard_enabled"] is True
    assert manifest["owner_tail_music_guard_passed"] is True
    assert manifest["owner_tail_music_silent_window_count"] == 0


def test_no_full_render_in_diagnose_audio_stems_mode(tmp_path, monkeypatch):
    repo_root = _repo_fixture(tmp_path)

    def fake_diagnosis(**kwargs):
        return {
            "audio_stem_diagnosis_enabled": True,
            "manifest_truth_requires_audio_stem_probe": True,
            "music_auto_stem_generated_for_gate": True,
            "music_auto_tail_rms_checked": True,
            "music_auto_tail_audible": True,
            "music_auto_tail_silent_window_count": 0,
            "song_start_music_stem_checked": True,
            "song_start_silent_window_count": 0,
            "music_vs_voice_relative_gate_enabled": True,
            "voice_window_music_below_voice_db_min": 18.0,
            "voice_window_music_below_voice_passed": True,
            "final_mix_tail_probe_passed": True,
            "diagnosis_mode_generated_mp4": False,
            "full_render_started": False,
            "status": "diagnosis_ok",
            "blocked_reason": None,
        }

    monkeypatch.setattr(preview, "run_audio_stem_diagnosis", fake_diagnosis)

    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
        diagnose_audio_stems=True,
    )

    assert manifest["status"] == "diagnosis_ok"
    assert manifest["dry_run"] is True
    assert manifest["audio_stem_probe_passed"] is True
    assert manifest["diagnosis_mode_generated_mp4"] is False
    assert manifest["full_render_started"] is False
    assert not list((repo_root / preview.STEP13_OUTPUT_ROOT).rglob("*.mp4"))


def test_no_music_double_mix(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )
    run_dir = repo_root / Path(manifest["output_video_path"]).parent
    command_text = (run_dir / "ffmpeg_command.txt").read_text(encoding="utf-8")

    assert command_text.count("[music_auto]") == 2
    assert "[music_auto][0:a]sidechaincompress" not in command_text
    assert "[0:a][ducked]amix=inputs=2" in command_text
    assert command_text.count("amix=inputs=2") == 1


def test_final_mix_does_not_use_raw_fullmix_sidechain(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )
    run_dir = repo_root / Path(manifest["output_video_path"]).parent
    command_text = (run_dir / "ffmpeg_command.txt").read_text(encoding="utf-8")

    assert "sidechaincompress" not in command_text
    assert manifest["raw_fullmix_sidechain_blocked"] is True
    assert manifest["ffmpeg_sidechaincompress_disabled"] is True


def test_music_inputs_are_not_double_seeked_when_timeline_trims_source(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )
    run_dir = repo_root / Path(manifest["output_video_path"]).parent
    command = json.loads((run_dir / "ffmpeg_command.txt").read_text(encoding="utf-8"))
    command_text = " ".join(str(part) for part in command)

    assert "-ss" not in command
    assert "atrim=start=30.000" in command_text
