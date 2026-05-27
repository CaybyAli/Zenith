from __future__ import annotations

from pathlib import Path

import pytest

from core.audio_stream_inspector import AudioStream, AudioStreamInventory
from core.transcript_processor import TranscriptProcessor
from models.transcript_result import TranscriptResult


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAIR_001_RAW = PROJECT_ROOT / "learning_corpus" / "pairs" / "pair_001" / "raw.mp4"


class FakeMultiTrackInspector:
    def inspect(self, video_path: str) -> AudioStreamInventory:
        return AudioStreamInventory(
            streams=[
                AudioStream(1, 1, 48000, "aac", 10.0, "mic"),
                AudioStream(2, 2, 48000, "aac", 10.0, "discord"),
                AudioStream(3, 2, 48000, "aac", 10.0, "ingame"),
            ],
            is_multi_track=True,
            has_mic_track=True,
            has_discord_track=True,
            has_ingame_track=True,
        )


class FakeDuplicateLabelInspector:
    def inspect(self, video_path: str) -> AudioStreamInventory:
        return AudioStreamInventory(
            streams=[
                AudioStream(1, 2, 48000, "aac", 10.0, "unknown"),
                AudioStream(2, 2, 48000, "aac", 10.0, "unknown"),
            ],
            is_multi_track=True,
            has_mic_track=False,
            has_discord_track=False,
            has_ingame_track=False,
        )


def test_transcript_segment_to_dict_includes_audio_track() -> None:
    result = TranscriptProcessor(allow_test_fallback=True).transcribe("placeholder.mp4")

    assert result.segments
    assert result.segments[0].audio_track == "mic"
    assert result.segments[0].speaker == "unknown"
    assert result.segments[0].to_dict()["audio_track"] == "mic"
    assert result.segments[0].to_dict()["speaker"] == "unknown"


def test_transcribe_all_streams_returns_one_result_per_label() -> None:
    processor = TranscriptProcessor(
        allow_test_fallback=True,
        audio_stream_inspector=FakeMultiTrackInspector(),
    )

    results = processor.transcribe_all_streams("placeholder.mp4")

    assert set(results) == {"mic", "discord", "ingame"}
    assert all(isinstance(result, TranscriptResult) for result in results.values())
    assert {
        result.segments[0].audio_track for result in results.values() if result.segments
    } == {"mic", "discord", "ingame"}


def test_transcribe_all_streams_disambiguates_duplicate_labels() -> None:
    processor = TranscriptProcessor(
        allow_test_fallback=True,
        audio_stream_inspector=FakeDuplicateLabelInspector(),
    )

    results = processor.transcribe_all_streams("placeholder.mp4")

    assert list(results) == ["unknown", "unknown_2"]
    assert results["unknown"].segments[0].audio_track == "unknown"
    assert results["unknown_2"].segments[0].audio_track == "unknown_2"


def test_sanitize_segments_accepts_audio_track_from_raw_segment() -> None:
    processor = TranscriptProcessor(allow_test_fallback=True)

    segments = processor._sanitize_segments(
        [
            {
                "start": 0.0,
                "end": 1.0,
                "text": "Hallo",
                "audio_track": "discord",
            }
        ],
        audio_track="mic",
    )

    assert len(segments) == 1
    assert segments[0].audio_track == "discord"


def test_pair_001_transcribe_all_streams_uses_phase_4_8_multitrack() -> None:
    if not PAIR_001_RAW.exists():
        pytest.skip("pair_001 raw.mp4 not available in this checkout")

    processor = TranscriptProcessor(allow_test_fallback=True)

    results = processor.transcribe_all_streams(str(PAIR_001_RAW))

    assert len(results) >= 2
    assert "mic" in results
    assert all(result.engine == "test-fallback" for result in results.values())
    assert all(result.segments for result in results.values())
    assert {result.segments[0].audio_track for result in results.values()} == set(results)
