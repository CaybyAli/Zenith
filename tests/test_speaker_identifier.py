from __future__ import annotations

from pathlib import Path

import numpy as np

from core.audio_track_mapping_config import AudioTrackRole
from core.speaker_identifier import SpeakerIdentifier, cosine_similarity
from models.transcript_result import TranscriptResult, TranscriptSegment


class FakeEmbeddingBackend:
    def embed(self, audio_path: str | Path) -> np.ndarray:
        name = Path(audio_path).name
        if "0001" in name:
            return np.asarray([0.0, 1.0], dtype=np.float32)
        return np.asarray([1.0, 0.0], dtype=np.float32)


class NoopExtractionSpeakerIdentifier(SpeakerIdentifier):
    def _extract_segment_audio(self, **kwargs) -> None:
        return None


def _segment(start: float, end: float, text: str = "test") -> TranscriptSegment:
    return TranscriptSegment(start_seconds=start, end_seconds=end, text=text)


def test_track_based_identification_labels_mic_and_discord() -> None:
    identifier = SpeakerIdentifier()

    result = identifier.identify_track_based(
        {
            "mic": [_segment(0.0, 1.0, "ali")],
            "discord": [_segment(2.0, 3.0, "friend")],
            "ingame": [_segment(4.0, 5.0, "announcer")],
        }
    )

    assert [(segment.audio_track, segment.speaker) for segment in result] == [
        ("mic", "ali"),
        ("discord", "friend"),
    ]
    assert identifier.last_summary is not None
    assert identifier.last_summary.strategy == "track_based"
    assert identifier.last_summary.ali_segments == 1
    assert identifier.last_summary.friend_segments == 1


def test_hybrid_result_uses_track_based_when_tracks_are_separated() -> None:
    identifier = SpeakerIdentifier()
    mic = TranscriptResult("raw.mp4", "de", [_segment(0.0, 1.0)], "ali", "test")
    discord = TranscriptResult("raw.mp4", "de", [_segment(1.0, 2.0)], "friend", "test")

    result = identifier.identify_transcript_results(
        {"mic": mic, "discord": discord},
        source_media_path="raw.mp4",
    )

    assert result.engine == "test"
    assert [segment.speaker for segment in result.segments] == ["ali", "friend"]


def test_track_based_identification_uses_supplied_role_speaker() -> None:
    identifier = SpeakerIdentifier()

    result = identifier.identify_track_based(
        {
            "mic": [_segment(0.0, 1.0, "ali")],
            "unknown": [_segment(1.0, 2.0, "friend")],
        },
        track_roles=[
            AudioTrackRole("owner", "mic", "ali", 0, True),
            AudioTrackRole("friend", "unknown", "friend", 1, True),
        ],
    )

    assert [(segment.audio_track, segment.speaker) for segment in result] == [
        ("mic", "ali"),
        ("unknown", "friend"),
    ]
    assert identifier.last_summary is not None
    assert identifier.last_summary.friend_segments == 1


def test_single_track_embedding_labels_similarity_bands(tmp_path) -> None:
    reference = tmp_path / "ali_voice_reference.wav"
    reference.write_bytes(b"placeholder")
    identifier = NoopExtractionSpeakerIdentifier(
        reference_audio_path=reference,
        embedding_backend=FakeEmbeddingBackend(),
        ali_similarity_threshold=0.75,
        friend_similarity_threshold=0.25,
    )
    segments = [_segment(0.0, 1.0), _segment(1.0, 2.0)]

    result = identifier.identify_single_track(
        segments,
        source_media_path="raw.mp4",
    )

    assert [segment.speaker for segment in result] == ["ali", "friend"]
    assert identifier.last_summary is not None
    assert identifier.last_summary.strategy == "single_track_embedding"


def test_single_track_without_source_marks_unknown() -> None:
    identifier = SpeakerIdentifier()

    result = identifier.identify_single_track([_segment(0.0, 1.0)])

    assert result[0].speaker == "unknown"
    assert identifier.last_summary is not None
    assert identifier.last_summary.strategy == "single_track_unavailable"


def test_cosine_similarity_handles_zero_vectors() -> None:
    assert cosine_similarity(np.asarray([0.0, 0.0]), np.asarray([1.0, 0.0])) == 0.0
    assert cosine_similarity(np.asarray([1.0, 0.0]), np.asarray([1.0, 0.0])) == 1.0
