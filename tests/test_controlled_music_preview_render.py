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
    assert manifest["owner_adobe_reference_gain_range_db"] == [-40.0, -35.0]
    assert manifest["owner_music_target_gain_db"] == -38.0
    assert manifest["ffmpeg_music_volume_gain_db"] == -38.0
    assert manifest["ffmpeg_music_volume_linear"] == pytest.approx(0.0126, abs=0.0001)
    assert manifest["ffmpeg_music_volume_source"] == "owner_adobe_reference_gain_db"
    assert manifest["adaptive_track_gain_enabled"] is True
    assert manifest["track_gain_strategy"] == "relative_track_loudness_with_owner_range_clamp"
    assert manifest["track_gain_reference"] == "median_selected_track_mean_volume_db"
    assert manifest["all_final_gains_between_minus_40_and_minus_35"] is True
    assert manifest["all_tracks_same_gain"] is False
    assert manifest["manifest_gains_applied_to_ffmpeg_command"] is True
    assert manifest["speech_aware_ducking_confirmed"] is False
    assert manifest["sidechaincompress_used"] is True
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

    assert "-stream_loop" in command
    assert "-1" in command
    assert "-ss" in command
    assert "30.000" in command
    assert command.count("-i") == 2
    assert str(music_path) in command
    assert "-filter_complex" in command
    assert "-map" in command
    assert command[-1] == str(output_path)
    filter_complex = command[command.index("-filter_complex") + 1]
    assert "volume=0.08" not in filter_complex
    assert "volume=-38.0dB" in filter_complex
    assert "volume=-27.0dB" not in filter_complex
    assert "sidechaincompress" in filter_complex


def test_db_to_linear_converts_planned_preview_gain():
    assert preview.db_to_linear(-38.0) == pytest.approx(0.0126, abs=0.0001)


def test_ffmpeg_music_volume_manifest_fields_match_owner_adobe_reference_gain(tmp_path):
    repo_root = _repo_fixture(tmp_path)
    manifest = preview.run(
        repo_root=repo_root,
        input_video=preview.VISUAL_PROPER_RUN_INPUT_VIDEO,
        channel_type="main",
        content_type=CONTENT_TYPE_GAMING_MAIN,
        output_root=preview.STEP13_OUTPUT_ROOT,
    )

    assert manifest["owner_adobe_reference_gain_range_db"] == [-40.0, -35.0]
    assert manifest["owner_music_target_gain_db"] == -38.0
    assert manifest["ffmpeg_music_volume_gain_db"] == -38.0
    assert manifest["ffmpeg_music_volume_linear"] == pytest.approx(0.0126, abs=0.0001)
    assert manifest["ffmpeg_music_volume_source"] == "owner_adobe_reference_gain_db"
    assert manifest["adaptive_track_gain_enabled"] is True
    assert manifest["track_gain_strategy"] == "relative_track_loudness_with_owner_range_clamp"
    assert manifest["track_gain_reference"] == "median_selected_track_mean_volume_db"
    assert manifest["all_final_gains_between_minus_40_and_minus_35"] is True
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
        music_volume_gain_db=-38.0,
    )

    filter_complex = command[command.index("-filter_complex") + 1]
    assert "volume=-38.0dB" in filter_complex
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
    assert "volume=-40.0dB" in command
    assert "volume=-39.5dB" in command
    assert "volume=-36.5dB" in command
    assert "volume=-35.0dB" in command
    assert "volume=0.08" not in command
    assert "volume=-27.0dB" not in command
    assert "concat=n=" in command
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
    assert plan["owner_adobe_reference_gain_range_db"] == [-40.0, -35.0]
    assert plan["owner_music_target_gain_db"] == -38.0
    assert plan["track_gain_strategy"] == "relative_track_loudness_with_owner_range_clamp"
    assert plan["track_gain_reference"] == "median_selected_track_mean_volume_db"
    assert plan["reference_track_mean_volume_db"] == -21.5
    assert plan["ffmpeg_music_volume_gain_db_by_track"] == [-40.0, -39.5, -36.5, -35.0]
    assert plan["all_final_gains_between_minus_40_and_minus_35"] is True
    assert plan["all_tracks_same_gain"] is False
    assert plan["selected_music_tracks"][0]["mean_volume_db"] == -18.0
    assert plan["selected_music_tracks"][0]["final_gain_db"] == -40.0
    assert plan["selected_music_tracks"][-1]["mean_volume_db"] == -28.0
    assert plan["selected_music_tracks"][-1]["final_gain_db"] == -35.0


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
    assert manifest["ffmpeg_music_volume_gain_db_by_track"] == [-40.0, -39.5, -36.5, -35.0]
    assert len(set(manifest["ffmpeg_music_volume_gain_db_by_track"])) > 1
    assert "volume=-40.0dB" in command
    assert "volume=-39.5dB" in command
    assert "volume=-36.5dB" in command
    assert "volume=-35.0dB" in command
    assert "volume=0.08" not in command
    assert "volume=-27.0dB" not in command
    assert "-stream_loop" not in command
    assert "concat=n=4" in command

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
