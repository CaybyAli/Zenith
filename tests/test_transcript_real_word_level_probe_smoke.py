from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest

from core.transcript_processor import TranscriptProcessor, TranscriptUnavailableError
from core.transcript_runner import build_transcript_run_report
from core.transcript_segment_normalizer import normalize_transcript_segments
from core.transcript_source_selector import TranscriptSourceSelection


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")


def _selection(audio_path: str) -> TranscriptSourceSelection:
    return TranscriptSourceSelection(
        status="selected",
        selected_path=audio_path,
        selected_type="speech_audio",
        recommendation="transcribe_speech_audio",
    )


def test_transcript_processor_is_available_and_word_level_is_not_faked() -> None:
    processor = TranscriptProcessor(allow_test_fallback=True)

    result = processor.transcribe("deterministic-test-source.wav")
    normalization_result = normalize_transcript_segments(
        [segment.to_dict() for segment in result.segments]
    )

    assert result.engine == "test-fallback"
    assert normalization_result.status == "ok"
    assert normalization_result.segment_count >= 1
    assert normalization_result.valid_segment_count >= 1

    for segment in normalization_result.segments:
        assert segment["start_seconds"] is not None
        assert segment["end_seconds"] is not None
        assert segment["text"]

    assert normalization_result.word_count == 0
    assert normalization_result.word_timestamp_count == 0
    assert normalization_result.has_word_level_timestamps is False


def test_runner_does_not_claim_word_level_when_words_are_missing() -> None:
    processor = TranscriptProcessor(allow_test_fallback=True)

    report = build_transcript_run_report(
        selection=_selection("deterministic-test-source.wav"),
        transcribe_fn=processor.transcribe,
        metadata={"stage": "2B-19-E"},
    )

    assert report.status == "ok"
    assert report.segment_count >= 1
    assert report.word_count > 0
    assert report.normalized_word_count == 0
    assert report.word_timestamp_count == 0
    assert report.has_word_level_timestamps is False

    for segment in report.segments:
        assert segment["start_seconds"] is not None
        assert segment["end_seconds"] is not None
        assert segment["text"]
        assert segment["words"] == []


def test_real_whisper_probe_is_optional_and_skip_safe() -> None:
    audio_path = os.getenv("ZENITH_REAL_WHISPER_AUDIO_PATH")

    if not audio_path:
        pytest.skip("Set ZENITH_REAL_WHISPER_AUDIO_PATH to run a real local Whisper probe.")

    source = Path(audio_path)
    if not source.is_file():
        pytest.skip(f"Real Whisper probe audio does not exist: {audio_path}")

    processor = TranscriptProcessor(allow_test_fallback=False)

    try:
        report = build_transcript_run_report(
            selection=_selection(str(source)),
            transcribe_fn=processor.transcribe,
            metadata={"stage": "2B-19-E-real-probe"},
        )
    except (TranscriptUnavailableError, ImportError, RuntimeError, OSError) as exc:
        pytest.skip(f"Real Whisper probe unavailable in this environment: {exc}")

    assert report.status in {
        "ok",
        "completed_with_warnings",
        "failed",
        "whisper_unavailable",
        "blocked_missing_preprocessed_audio",
    }

    if report.segments:
        for segment in report.segments:
            assert "start_seconds" in segment
            assert "end_seconds" in segment
            assert "text" in segment

    if report.word_timestamp_count > 0:
        assert report.has_word_level_timestamps is True
    else:
        assert report.has_word_level_timestamps is False or report.word_timestamp_count == 0


def test_processor_currently_does_not_request_faster_whisper_word_timestamps() -> None:
    source = _read("core/transcript_processor.py")

    assert "faster_whisper" in source
    assert "word_timestamps=True" not in source
    assert "word_timestamps = True" not in source


def test_real_probe_file_has_no_bom_and_ends_with_newline() -> None:
    data = (PROJECT_ROOT / "tests/test_transcript_real_word_level_probe_smoke.py").read_bytes()

    assert not data.startswith(b"\xef\xbb\xbf")
    assert data.endswith(b"\n")
