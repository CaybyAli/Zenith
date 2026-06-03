from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import pytest

from core.audio_stream_inspector import AudioStream, AudioStreamInventory
from core.job_store import compact_job_dict_for_persistence
from core.power_profile import PowerProfile
from core.transcript_processor import TranscriptProcessor
from core.transcription_engine import (
    DEFAULT_TRANSCRIPTION_ENGINE,
    FasterWhisperEngine,
    TranscriptUnavailableError,
    TranscriptionEngine,
)
from models.job import Job
from models.transcript_result import TranscriptResult, TranscriptSegment


class FakeSingleTrackInspector:
    def inspect(self, video_path: str) -> AudioStreamInventory:
        return AudioStreamInventory(
            streams=[AudioStream(1, 1, 48000, "aac", 1.0, "mic")],
            is_multi_track=False,
            has_mic_track=True,
            has_discord_track=False,
            has_ingame_track=False,
        )


class FakeEngine(TranscriptionEngine):
    name = "fake_engine"

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def transcribe(
        self,
        source_path: str,
        *,
        result_source_path: str | None = None,
        audio_track: str = "mic",
        sanitize_segments,
    ) -> TranscriptResult:
        self.calls.append((source_path, audio_track))
        segment = TranscriptSegment(
            start_seconds=0.0,
            end_seconds=1.0,
            text="engine smoke",
            audio_track=audio_track,
        )
        return TranscriptResult(
            source_path=result_source_path or source_path,
            language="en",
            segments=[segment],
            full_text="engine smoke",
            engine=self.name,
        )


def test_power_profile_transcription_engine_default_and_validation() -> None:
    assert PowerProfile.transcription_engine == "whisperx"
    assert PowerProfile.normalize_transcription_engine(None) == "whisperx"
    assert PowerProfile.normalize_transcription_engine("faster-whisper") == "faster_whisper"

    with pytest.raises(ValueError, match="Unsupported transcription_engine"):
        PowerProfile.normalize_transcription_engine("silent_fallback")



def test_job_model_has_persisted_transcription_engine_field() -> None:
    field_names = {field.name for field in fields(Job)}
    assert "transcription_engine" in field_names


def test_job_persistence_always_contains_transcription_engine() -> None:
    compact = compact_job_dict_for_persistence(
        {
            "job_id": "job_p5_g1",
            "status": "created",
        }
    )

    assert compact["transcription_engine"] == DEFAULT_TRANSCRIPTION_ENGINE


def test_whisperx_unavailable_does_not_call_faster_whisper(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "sample.wav"
    source.write_bytes(b"not real audio, availability fails before decoding")
    monkeypatch.setenv("ZENITH_WHISPERX_DISABLE", "1")

    def forbidden_faster_whisper(self, *args, **kwargs):  # pragma: no cover - must not run
        raise AssertionError("faster_whisper was called as a silent fallback")

    monkeypatch.setattr(FasterWhisperEngine, "transcribe", forbidden_faster_whisper)

    processor = TranscriptProcessor(
        allow_test_fallback=False,
        transcription_engine="whisperx",
        audio_stream_inspector=FakeSingleTrackInspector(),
    )

    with pytest.raises(TranscriptUnavailableError, match="whisperx unavailable"):
        processor.transcribe(str(source))

    assert processor.transcription_engine_name == "whisperx"


def test_transcribe_and_all_streams_use_selected_engine(tmp_path: Path) -> None:
    source = tmp_path / "sample.wav"
    source.write_bytes(b"placeholder")
    fake_engine = FakeEngine()
    processor = TranscriptProcessor(
        allow_test_fallback=False,
        transcription_engine=fake_engine,
        audio_stream_inspector=FakeSingleTrackInspector(),
    )

    single = processor.transcribe(str(source))
    all_streams = processor.transcribe_all_streams(str(source))

    assert single.engine == "fake_engine"
    assert all_streams["mic"].engine == "fake_engine"
    assert fake_engine.calls == [(str(source), "mic"), (str(source), "mic")]
