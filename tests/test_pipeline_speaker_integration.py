from __future__ import annotations

from pathlib import Path

import pytest

from core.speaker_identifier import SpeakerIdentifier
from core.transcript_processor import TranscriptProcessor


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PAIR_001_RAW = PROJECT_ROOT / "learning_corpus" / "pairs" / "pair_001" / "raw.mp4"


def test_pair_001_transcript_streams_receive_speaker_labels() -> None:
    if not PAIR_001_RAW.exists():
        pytest.skip("pair_001 raw.mp4 not available in this checkout")

    streams = TranscriptProcessor(allow_test_fallback=True).transcribe_all_streams(
        str(PAIR_001_RAW)
    )

    identifier = SpeakerIdentifier()
    result = identifier.identify_transcript_results(streams)

    assert result.segments
    assert all(segment.speaker in {"ali", "friend", "unknown"} for segment in result.segments)
    assert all(segment.audio_track for segment in result.segments)
    assert result.engine == "test-fallback"
    assert identifier.last_summary is not None
    assert identifier.last_summary.strategy == "single_track_unavailable"
