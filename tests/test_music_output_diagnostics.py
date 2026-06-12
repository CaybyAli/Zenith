from __future__ import annotations

from core.music_output_diagnostics import (
    apply_audio_stem_truth_gate,
    build_audio_stem_truth_gate,
    transition_probe_windows,
)


def _base_manifest() -> dict:
    return {
        "status": "dry_run",
        "musicbed_full_coverage_required": True,
        "musicbed_full_coverage_confirmed": True,
        "musicbed_no_silent_gaps": True,
        "musicbed_command_matches_timeline": True,
        "tail_music_coverage_passed": True,
        "musicbed_gap_count": 0,
    }


def _audible(start: float = 471.0, end: float = 481.0, level: float = -52.0) -> dict:
    return {"start_sec": start, "end_sec": end, "mean_volume_db": level, "max_volume_db": -12.0}


def test_audio_stem_probe_required_for_manifest_truth():
    gate = {
        "audio_stem_diagnosis_enabled": True,
        "manifest_truth_requires_audio_stem_probe": True,
        "music_auto_stem_generated_for_gate": False,
        "music_auto_tail_audible": False,
        "music_auto_tail_silent_window_count": 1,
        "song_start_music_stem_checked": False,
        "song_start_silent_window_count": 1,
        "voice_window_music_below_voice_passed": False,
        "final_mix_tail_probe_passed": False,
        "status": "blocked",
        "blocked_reason": "audio_stem_probe_missing",
    }

    manifest = apply_audio_stem_truth_gate(_base_manifest(), gate)

    assert manifest["status"] == "blocked"
    assert manifest["blocked_reason"] == "audio_stem_probe_missing"
    assert manifest["musicbed_no_silent_gaps"] is False
    assert manifest["musicbed_full_coverage_confirmed"] is False
    assert manifest["musicbed_no_silent_gaps_verified_by_audio_stem"] is False


def test_tail_guard_uses_music_auto_stem_not_only_timeline(tmp_path):
    stem = tmp_path / "music_auto_after_gain.mka"
    stem.write_bytes(b"stem")

    gate = build_audio_stem_truth_gate(
        music_auto_stem_path=stem,
        music_auto_stem_duration_sec=470.0,
        expected_duration_sec=528.0,
        tail_window_stats=[_audible()],
        song_start_window_stats=[_audible(0.0, 10.0)],
        voice_music_relative_stats=[{"music_below_voice_db": 22.0}],
        final_mix_tail_stats=[_audible()],
    )
    manifest = apply_audio_stem_truth_gate(_base_manifest(), gate)

    assert manifest["status"] == "blocked"
    assert manifest["blocked_reason"] == "music_auto_shorter_than_video"
    assert manifest["music_auto_tail_audible"] is False
    assert manifest["music_auto_tail_silent_window_count"] == 1
    assert manifest["musicbed_no_silent_gaps"] is False


def test_tail_music_duration_still_matches_video(tmp_path):
    stem = tmp_path / "music_auto_after_gain.mka"
    stem.write_bytes(b"stem")

    gate = build_audio_stem_truth_gate(
        music_auto_stem_path=stem,
        music_auto_stem_duration_sec=527.3,
        expected_duration_sec=528.0,
        tail_window_stats=[_audible()],
        song_start_window_stats=[_audible(0.0, 10.0)],
        transition_window_stats=[_audible(117.0, 123.0)],
        voice_music_relative_stats=[{"music_below_voice_db": 22.0}],
        final_mix_tail_stats=[_audible()],
    )

    assert gate["status"] == "diagnosis_ok"
    assert gate["music_auto_duration_sec"] >= gate["video_duration_sec"] - 1.0


def test_transition_energy_does_not_drop_to_silence(tmp_path):
    stem = tmp_path / "music_auto_after_gain.mka"
    stem.write_bytes(b"stem")

    gate = build_audio_stem_truth_gate(
        music_auto_stem_path=stem,
        music_auto_stem_duration_sec=528.0,
        expected_duration_sec=528.0,
        tail_window_stats=[_audible()],
        song_start_window_stats=[_audible(0.0, 10.0)],
        transition_window_stats=[_audible(117.0, 123.0, -52.0)],
        voice_music_relative_stats=[{"music_below_voice_db": 22.0}],
        final_mix_tail_stats=[_audible()],
    )

    assert gate["transition_crossfade_stem_probe_passed"] is True
    assert gate["transition_energy_drop_count"] == 0


def test_transition_probe_windows_cover_overlap():
    windows = transition_probe_windows(
        [
            {"start_sec": 0.0, "end_sec": 120.0, "crossfade_out_sec": 3.0},
            {"start_sec": 120.0, "end_sec": 240.0, "crossfade_in_sec": 3.0},
        ],
        240.0,
    )

    assert windows == [{"transition_index": 1, "start_sec": 117.0, "end_sec": 123.0, "crossfade_in_sec": 3.0}]


def test_song_start_guard_blocks_silent_segment_start(tmp_path):
    stem = tmp_path / "music_auto_after_gain.mka"
    stem.write_bytes(b"stem")

    gate = build_audio_stem_truth_gate(
        music_auto_stem_path=stem,
        music_auto_stem_duration_sec=528.0,
        expected_duration_sec=528.0,
        tail_window_stats=[_audible()],
        song_start_window_stats=[{"start_sec": 120.0, "end_sec": 130.0, "mean_volume_db": None}],
        voice_music_relative_stats=[{"music_below_voice_db": 22.0}],
        final_mix_tail_stats=[_audible()],
    )

    assert gate["status"] == "blocked"
    assert gate["blocked_reason"] == "song_start_music_not_audible"
    assert gate["song_start_silent_window_count"] == 1


def test_music_vs_voice_relative_gate_blocks_foreground_music(tmp_path):
    stem = tmp_path / "music_auto_after_gain.mka"
    stem.write_bytes(b"stem")

    foreground = build_audio_stem_truth_gate(
        music_auto_stem_path=stem,
        music_auto_stem_duration_sec=528.0,
        expected_duration_sec=528.0,
        tail_window_stats=[_audible()],
        song_start_window_stats=[_audible(0.0, 10.0)],
        voice_music_relative_stats=[{"music_below_voice_db": 10.0}],
        final_mix_tail_stats=[_audible()],
    )
    background = build_audio_stem_truth_gate(
        music_auto_stem_path=stem,
        music_auto_stem_duration_sec=528.0,
        expected_duration_sec=528.0,
        tail_window_stats=[_audible()],
        song_start_window_stats=[_audible(0.0, 10.0)],
        voice_music_relative_stats=[{"music_below_voice_db": 18.0}, {"music_below_voice_db": 24.0}],
        final_mix_tail_stats=[_audible()],
    )

    assert foreground["status"] == "blocked"
    assert foreground["blocked_reason"] == "music_too_close_to_voice"
    assert foreground["voice_window_music_below_voice_passed"] is False
    assert background["status"] == "diagnosis_ok"
    assert background["voice_window_music_below_voice_passed"] is True
