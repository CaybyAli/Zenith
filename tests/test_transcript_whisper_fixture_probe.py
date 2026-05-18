from __future__ import annotations

from pathlib import Path
import re

import pytest

from core.transcript_processor import TranscriptProcessor, TranscriptUnavailableError


FIXTURE_AUDIO_PATH = Path(__file__).resolve().parent / "fixtures" / "whisper_probe.wav"


@pytest.mark.real_whisper
def test_whisper_transcribes_bundled_sapi_fixture(monkeypatch) -> None:
    if not FIXTURE_AUDIO_PATH.exists():
        pytest.skip(f"Whisper fixture missing: {FIXTURE_AUDIO_PATH}")

    monkeypatch.delenv("ZENITH_TRANSCRIPT_TEST_MODE", raising=False)
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")

    try:
        result = TranscriptProcessor().transcribe(str(FIXTURE_AUDIO_PATH))
    except (TranscriptUnavailableError, ImportError, RuntimeError, OSError) as exc:
        pytest.skip(f"Real Whisper fixture unavailable in this environment: {exc}")

    assert result.segments
    assert result.engine in {"faster-whisper", "whisper"}

    text = re.sub(r"[^a-z ]+", " ", (result.full_text or "").lower())
    assert "fox" in text
    assert "dog" in text

    first_segment = result.segments[0]
    assert first_segment.end_seconds > first_segment.start_seconds
    assert first_segment.text.strip()
