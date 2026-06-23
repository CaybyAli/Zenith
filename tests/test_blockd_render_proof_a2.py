from __future__ import annotations

import importlib.util
from pathlib import Path


def _load_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "blockd_render_proof_a2.py"
    spec = importlib.util.spec_from_file_location("blockd_render_proof_a2", path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_filtered_candidates_and_cluster_are_artifact_driven():
    module = _load_module()
    report = {
        "candidates": [
            {
                "candidate_index": 0,
                "start": 10.0,
                "end": 10.8,
                "zoom_start": 10.1,
                "zoom_end": 10.7,
                "zoom_mode": "instant",
                "is_real_reaction": True,
                "confidence": 0.91,
                "friend_text": "A",
            },
            {
                "candidate_index": 1,
                "start": 11.0,
                "end": 11.6,
                "zoom_start": 11.0,
                "zoom_end": 11.5,
                "zoom_mode": "smooth",
                "is_real_reaction": True,
                "confidence": 0.87,
                "friend_text": "B",
            },
            {
                "candidate_index": 2,
                "start": 30.0,
                "end": 31.0,
                "zoom_start": 30.1,
                "zoom_end": 30.9,
                "zoom_mode": "smooth",
                "is_real_reaction": True,
                "confidence": 0.79,
                "friend_text": "below floor",
            },
            {
                "candidate_index": 3,
                "start": 50.0,
                "end": 50.5,
                "zoom_start": 50.0,
                "zoom_end": 50.4,
                "zoom_mode": "instant",
                "is_real_reaction": False,
                "confidence": 0.99,
                "friend_text": "not real",
            },
        ]
    }

    filtered, below_floor, counters = module._filtered_candidates(report)
    cluster = module._densest_cluster(filtered)
    planned = module._planned_cut_segments(cluster["picks"])

    assert [row["candidate_index"] for row in filtered] == [0, 1]
    assert [row["candidate_index"] for row in below_floor] == [2]
    assert counters["excluded_not_real_reaction"] == 1
    assert counters["excluded_real_below_confidence_floor"] == 1
    assert cluster["size"] == 2
    assert cluster["window_start"] == 6.0
    assert cluster["window_end"] == 15.6
    assert planned == [
        {
            "candidate_index": 0,
            "gameplay_crop_start": 10.1,
            "gameplay_crop_end": 10.7,
            "zoom_mode": "instant",
            "confidence": 0.91,
            "friend_text": "A",
        },
        {
            "candidate_index": 1,
            "gameplay_crop_start": 11.0,
            "gameplay_crop_end": 11.5,
            "zoom_mode": "smooth",
            "confidence": 0.87,
            "friend_text": "B",
        },
    ]


def test_pair_006_track_truth_maps_to_expected_raw_streams():
    module = _load_module()

    roles = module._resolve_pair_audio_roles("pair_006")

    assert roles == {
        "ali": {
            "track_name": "a0",
            "audio_index": 0,
            "global_stream_spec": "0:1",
            "audio_selector": "0:a:0",
        },
        "discord": {
            "track_name": "a1",
            "audio_index": 1,
            "global_stream_spec": "0:2",
            "audio_selector": "0:a:1",
        },
        "game": {
            "track_name": "a2",
            "audio_index": 2,
            "global_stream_spec": "0:3",
            "audio_selector": "0:a:2",
        },
    }


def test_select_dual_speaker_window_uses_full_render_window_when_both_speakers_are_present():
    module = _load_module()

    def point(timestamp: float, rms_dbfs: float, speaker: str):
        return module.VoiceIntensityPoint(
            timestamp=timestamp,
            intensity=0,
            lufs=rms_dbfs - 5.0,
            rms_dbfs=rms_dbfs,
            speaker=speaker,
        )

    ali_points = [
        point(10.0, -20.0, "ali"),
        point(11.0, -19.5, "ali"),
        point(12.0, -80.0, "ali"),
        point(13.0, -18.0, "ali"),
    ]
    discord_points = [
        point(10.0, -70.0, "discord"),
        point(11.0, -21.0, "discord"),
        point(12.0, -22.0, "discord"),
        point(13.0, -20.0, "discord"),
    ]

    selected = module._select_dual_speaker_window(
        ali_points,
        discord_points,
        render_window_start=10.0,
        render_window_end=14.0,
    )

    assert selected["start"] == 10.0
    assert selected["end"] == 14.0
    assert selected["duration_seconds"] == 4.0
    assert selected["ali_active_seconds"] == 3.0
    assert selected["discord_active_seconds"] == 3.0
    assert selected["window_origin"] == "full_render_window"


def test_longest_active_window_reports_contiguous_speech_run():
    module = _load_module()

    def point(timestamp: float, rms_dbfs: float, speaker: str):
        return module.VoiceIntensityPoint(
            timestamp=timestamp,
            intensity=0,
            lufs=rms_dbfs - 5.0,
            rms_dbfs=rms_dbfs,
            speaker=speaker,
        )

    ali_points = [
        point(20.0, -80.0, "ali"),
        point(21.0, -20.0, "ali"),
        point(22.0, -19.0, "ali"),
        point(23.0, -80.0, "ali"),
        point(24.0, -21.0, "ali"),
        point(25.0, -20.5, "ali"),
    ]

    selected = module._longest_active_window(ali_points, speaker="ali")

    assert selected["start"] == 21.0
    assert selected["end"] == 23.0
    assert selected["duration_seconds"] == 2.0
    assert selected["active_seconds"] == 2.0
    assert selected["speaker"] == "ali"
