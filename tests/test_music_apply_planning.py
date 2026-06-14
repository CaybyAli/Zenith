from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.music_apply_planning import (
    DEFAULT_MUSIC_ASSETS_DIR,
    build_and_save_music_apply_timeline,
    calculate_music_level_gain_db,
)
from core.music_apply_timeline_repository import MusicApplyTimelineRepository


def _note_float(notes: list[str], prefix: str) -> float:
    for note in notes:
        if note.startswith(prefix):
            return float(note.split("=", 1)[1])
    raise AssertionError(f"missing note prefix: {prefix}")


def test_music_apply_planning_integration_writes_real_asset_timeline(tmp_path):
    assert DEFAULT_MUSIC_ASSETS_DIR.exists()

    result = build_and_save_music_apply_timeline(
        export_path=tmp_path,
        video_duration_sec=528.0,
        job_id="job_music_apply_planning_integration",
        channel_type="gaming_main",
        content_type="gaming_main",
        music_enabled=True,
        music_assets_dir=DEFAULT_MUSIC_ASSETS_DIR,
    )

    timeline_path = tmp_path / "music_apply_timeline.json"
    assert result.status == "created"
    assert result.timeline_path == str(timeline_path)
    assert result.segment_count >= 1
    assert timeline_path.exists()

    payload = json.loads(timeline_path.read_text(encoding="utf-8"))
    assert payload["timeline_id"] == "music_apply_timeline_job_music_apply_planning_integration"
    assert payload["job_id"] == "job_music_apply_planning_integration"
    assert payload["channel_type"] == "gaming_main"
    assert len(payload["segments"]) >= 1
    assert payload["segments"][0]["video_start_time"] == pytest.approx(0.0, abs=0.001)
    assert payload["segments"][-1]["video_end_time"] == pytest.approx(528.0, abs=0.01)

    for segment in payload["segments"]:
        source_path = Path(segment["source_file_path"])
        assert source_path.exists()
        assert segment["video_start_time"] < segment["video_end_time"]
        assert segment["music_offset_start"] < segment["music_offset_end"]
        assert isinstance(segment["music_level"], (int, float))
        assert segment["voice_priority"] is True
        assert segment["ducking_required"] is True
        assert segment["fade_in_seconds"] >= 0.0
        assert segment["fade_out_seconds"] >= 0.0
        assert segment["music_level"] == pytest.approx(
            _note_float(segment["notes"], "per_song_gain_db="),
            abs=0.001,
        )

    assert any(abs(float(segment["music_level"])) > 0.001 for segment in payload["segments"])

    loaded = MusicApplyTimelineRepository().load_timeline(tmp_path)
    assert loaded is not None
    assert len(loaded.segments) == len(payload["segments"])

    print("MUSIC_APPLY_TIMELINE_JSON_BEGIN")
    print(json.dumps(payload, indent=4, ensure_ascii=False))
    print("MUSIC_APPLY_TIMELINE_JSON_END")


def test_music_apply_planning_gate_skips_uncut_and_music_disabled(tmp_path):
    disabled_export = tmp_path / "disabled"
    disabled_result = build_and_save_music_apply_timeline(
        export_path=disabled_export,
        video_duration_sec=528.0,
        job_id="job_music_disabled",
        channel_type="gaming_main",
        content_type="gaming_main",
        music_enabled=False,
    )

    uncut_export = tmp_path / "uncut"
    uncut_result = build_and_save_music_apply_timeline(
        export_path=uncut_export,
        video_duration_sec=528.0,
        job_id="job_music_uncut",
        channel_type="gaming_main",
        content_type="gaming_uncut",
        music_enabled=True,
    )

    assert disabled_result.status == "skipped"
    assert disabled_result.reason == "music_disabled"
    assert not (disabled_export / "music_apply_timeline.json").exists()
    assert uncut_result.status == "skipped"
    assert uncut_result.reason == "content_type_uncut"
    assert not (uncut_export / "music_apply_timeline.json").exists()


def test_music_apply_gain_calculation_targets_minus_17_short_term_p95():
    assert calculate_music_level_gain_db(-20.25) == pytest.approx(3.25)
    assert calculate_music_level_gain_db(-17.0) == pytest.approx(0.0)
    assert calculate_music_level_gain_db(-14.5) == pytest.approx(-2.5)
