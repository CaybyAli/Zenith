from __future__ import annotations

from pathlib import Path

import pytest

from core.audio_stream_inspector import AudioStreamInspector


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAIR_001_RAW = PROJECT_ROOT / "learning_corpus" / "pairs" / "pair_001" / "raw.mp4"


def test_inventory_from_standard_multitrack_payload_labels_roles() -> None:
    payload = {
        "format": {"duration": "12.5"},
        "streams": [
            {"index": 0, "codec_type": "video", "codec_name": "h264"},
            {
                "index": 1,
                "codec_type": "audio",
                "codec_name": "aac",
                "channels": 1,
                "sample_rate": "48000",
                "duration": "12.4",
            },
            {
                "index": 2,
                "codec_type": "audio",
                "codec_name": "aac",
                "channels": 2,
                "sample_rate": "48000",
            },
            {
                "index": 3,
                "codec_type": "audio",
                "codec_name": "aac",
                "channels": 2,
                "sample_rate": "48000",
            },
        ],
    }

    inventory = AudioStreamInspector()._inventory_from_ffprobe_payload(payload)

    assert inventory.is_multi_track is True
    assert inventory.has_mic_track is True
    assert inventory.has_discord_track is True
    assert inventory.has_ingame_track is True
    assert [stream.index for stream in inventory.streams] == [1, 2, 3]
    assert [stream.label for stream in inventory.streams] == [
        "mic",
        "discord",
        "ingame",
    ]
    assert inventory.streams[0].duration_seconds == 12.4
    assert inventory.streams[1].duration_seconds == 12.5


def test_single_track_payload_is_unknown_fallback_not_mic() -> None:
    payload = {
        "format": {"duration": "5.0"},
        "streams": [
            {
                "index": 1,
                "codec_type": "audio",
                "codec_name": "aac",
                "channels": 2,
                "sample_rate": "48000",
            }
        ],
    }

    inventory = AudioStreamInspector()._inventory_from_ffprobe_payload(payload)

    assert inventory.is_multi_track is False
    assert inventory.has_mic_track is False
    assert inventory.has_discord_track is False
    assert inventory.has_ingame_track is False
    assert len(inventory.streams) == 1
    assert inventory.streams[0].label == "unknown"
    assert inventory.streams[0].index == 1


def test_pair_001_current_raw_is_phase_4_8_multitrack() -> None:
    if not PAIR_001_RAW.exists():
        pytest.skip("pair_001 raw.mp4 not available in this checkout")

    inventory = AudioStreamInspector().inspect(str(PAIR_001_RAW))

    assert len(inventory.streams) >= 2
    assert inventory.is_multi_track is True
    assert inventory.has_mic_track is True
    assert inventory.streams[0].label == "mic"
    assert all(stream.index >= 0 for stream in inventory.streams)
    assert all(stream.channels >= 1 for stream in inventory.streams)
    assert all(stream.sample_rate > 0 for stream in inventory.streams)


def test_inventory_to_dict_contains_track_flags() -> None:
    inventory = AudioStreamInspector()._inventory_from_ffprobe_payload(
        {
            "streams": [
                {
                    "index": 1,
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "channels": 1,
                    "sample_rate": "48000",
                },
                {
                    "index": 2,
                    "codec_type": "audio",
                    "codec_name": "aac",
                    "channels": 2,
                    "sample_rate": "48000",
                },
            ]
        }
    )

    data = inventory.to_dict()

    assert data["is_multi_track"] is True
    assert data["has_mic_track"] is True
    assert data["has_discord_track"] is True
    assert data["streams"][0]["label"] == "mic"
