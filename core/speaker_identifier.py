from __future__ import annotations

import math
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Protocol

import numpy as np

from models.transcript_result import TranscriptResult, TranscriptSegment


class EmbeddingBackend(Protocol):
    def embed(self, audio_path: str | Path) -> np.ndarray:
        ...


class SpeakerIdentificationUnavailable(RuntimeError):
    """Raised when local speaker identification cannot be executed."""


@dataclass(frozen=True)
class SpeakerIdentificationSummary:
    strategy: str
    ali_segments: int
    friend_segments: int
    unknown_segments: int
    total_segments: int
    reference_audio_path: str | None = None
    warnings: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "strategy": self.strategy,
            "ali_segments": self.ali_segments,
            "friend_segments": self.friend_segments,
            "unknown_segments": self.unknown_segments,
            "total_segments": self.total_segments,
            "reference_audio_path": self.reference_audio_path,
            "warnings": list(self.warnings or []),
        }


class ResemblyzerEmbeddingBackend:
    """Local voice embedding backend. No cloud or HuggingFace token is used."""

    def __init__(self) -> None:
        try:
            from resemblyzer import VoiceEncoder, preprocess_wav
        except Exception as exc:  # pragma: no cover - depends on local package
            raise SpeakerIdentificationUnavailable(
                "resemblyzer is not available for local speaker embeddings"
            ) from exc

        self._preprocess_wav = preprocess_wav
        self._encoder = VoiceEncoder()

    def embed(self, audio_path: str | Path) -> np.ndarray:
        wav = self._preprocess_wav(Path(audio_path))
        if len(wav) == 0:
            raise SpeakerIdentificationUnavailable(f"empty audio: {audio_path}")
        return np.asarray(self._encoder.embed_utterance(wav), dtype=np.float32)


class SpeakerIdentifier:
    TRACK_TO_SPEAKER = {
        "mic": "ali",
        "discord": "friend",
    }

    def __init__(
        self,
        reference_audio_path: str | Path = "data/voice_references/ali_voice_reference.wav",
        embedding_backend: EmbeddingBackend | None = None,
        ali_similarity_threshold: float = 0.60,
        friend_similarity_threshold: float = 0.40,
    ) -> None:
        self.reference_audio_path = Path(reference_audio_path)
        self.embedding_backend = embedding_backend
        self.ali_similarity_threshold = float(ali_similarity_threshold)
        self.friend_similarity_threshold = float(friend_similarity_threshold)
        self.last_summary: SpeakerIdentificationSummary | None = None

    def identify_track_based(
        self,
        segments: dict[str, list[TranscriptSegment]],
    ) -> list[TranscriptSegment]:
        result: list[TranscriptSegment] = []

        for track_label, segments_list in segments.items():
            safe_track = _safe_track(track_label)
            if safe_track == "ingame":
                continue

            speaker = self.TRACK_TO_SPEAKER.get(safe_track, "unknown")
            for segment in segments_list:
                segment.audio_track = safe_track
                segment.speaker = speaker
                result.append(segment)

        result.sort(key=lambda segment: segment.start_seconds)
        self.last_summary = self._summary("track_based", result, warnings=[])
        return result

    def identify_transcript_results(
        self,
        transcript_results: dict[str, TranscriptResult],
        *,
        source_media_path: str | Path | None = None,
    ) -> TranscriptResult:
        if not transcript_results:
            raise ValueError("transcript_results must not be empty")

        normalized = {
            _safe_track(track_label): list(result.segments or [])
            for track_label, result in transcript_results.items()
        }

        has_track_separation = "mic" in normalized or "discord" in normalized
        if has_track_separation and len(normalized) > 1:
            segments = self.identify_track_based(normalized)
            strategy = "track_based"
        else:
            only_track, only_segments = next(iter(normalized.items()))
            for segment in only_segments:
                segment.audio_track = only_track
            segments = self.identify_single_track(
                only_segments,
                source_media_path=source_media_path,
            )
            strategy = self.last_summary.strategy if self.last_summary else "single_track"

        first_result = next(iter(transcript_results.values()))
        return TranscriptResult(
            source_path=first_result.source_path,
            language=first_result.language,
            segments=segments,
            full_text=" ".join(
                segment.text.strip() for segment in segments if segment.text.strip()
            ).strip(),
            engine=first_result.engine,
        )

    def identify_single_track(
        self,
        segments: list[TranscriptSegment],
        *,
        source_media_path: str | Path | None = None,
    ) -> list[TranscriptSegment]:
        sorted_segments = sorted(segments, key=lambda segment: segment.start_seconds)
        warnings: list[str] = []

        if source_media_path is None:
            for segment in sorted_segments:
                segment.speaker = "unknown"
            self.last_summary = self._summary(
                "single_track_unavailable",
                sorted_segments,
                warnings=["source_media_path_missing"],
            )
            return sorted_segments

        if not self.reference_audio_path.exists():
            self.extract_reference_sample(source_media_path, self.reference_audio_path)

        try:
            backend = self.embedding_backend or ResemblyzerEmbeddingBackend()
            reference_embedding = backend.embed(self.reference_audio_path)
        except Exception as exc:
            for segment in sorted_segments:
                segment.speaker = "unknown"
            self.last_summary = self._summary(
                "single_track_embedding_unavailable",
                sorted_segments,
                warnings=[str(exc)],
            )
            return sorted_segments

        with tempfile.TemporaryDirectory(prefix="zenith_speaker_segments_") as temp_dir:
            for index, segment in enumerate(sorted_segments):
                segment.audio_track = _safe_track(segment.audio_track)
                segment_path = Path(temp_dir) / f"segment_{index:04d}.wav"

                try:
                    self._extract_segment_audio(
                        source_media_path=source_media_path,
                        output_path=segment_path,
                        start_seconds=segment.start_seconds,
                        duration_seconds=segment.end_seconds - segment.start_seconds,
                    )
                    segment_embedding = backend.embed(segment_path)
                    similarity = cosine_similarity(reference_embedding, segment_embedding)
                    segment.speaker = self._speaker_from_similarity(similarity)
                except Exception as exc:
                    warnings.append(f"segment_{index}:{exc}")
                    segment.speaker = "unknown"

        self.last_summary = self._summary(
            "single_track_embedding",
            sorted_segments,
            warnings=warnings,
        )
        return sorted_segments

    def extract_reference_sample(
        self,
        source_media_path: str | Path,
        output_path: str | Path | None = None,
        *,
        start_seconds: float = 30.0,
        duration_seconds: float = 5.0,
    ) -> Path:
        target = Path(output_path) if output_path is not None else self.reference_audio_path
        target.parent.mkdir(parents=True, exist_ok=True)

        command = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-ss",
            str(float(start_seconds)),
            "-i",
            str(source_media_path),
            "-t",
            str(float(duration_seconds)),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(target),
        ]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        if completed.returncode != 0:
            message = (completed.stderr or completed.stdout or "").strip()
            raise SpeakerIdentificationUnavailable(
                f"failed to extract reference sample: {message}"
            )

        return target

    def _speaker_from_similarity(self, similarity: float) -> str:
        if similarity >= self.ali_similarity_threshold:
            return "ali"
        if similarity <= self.friend_similarity_threshold:
            return "friend"
        return "unknown"

    def _extract_segment_audio(
        self,
        *,
        source_media_path: str | Path,
        output_path: str | Path,
        start_seconds: float,
        duration_seconds: float,
    ) -> None:
        duration = max(0.1, float(duration_seconds))
        command = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-ss",
            str(max(0.0, float(start_seconds))),
            "-i",
            str(source_media_path),
            "-t",
            str(duration),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            str(output_path),
        ]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        if completed.returncode != 0:
            message = (completed.stderr or completed.stdout or "").strip()
            raise SpeakerIdentificationUnavailable(
                f"failed to extract segment audio: {message}"
            )

    def _summary(
        self,
        strategy: str,
        segments: Iterable[TranscriptSegment],
        *,
        warnings: list[str],
    ) -> SpeakerIdentificationSummary:
        items = list(segments)
        return SpeakerIdentificationSummary(
            strategy=strategy,
            ali_segments=sum(1 for segment in items if segment.speaker == "ali"),
            friend_segments=sum(1 for segment in items if segment.speaker == "friend"),
            unknown_segments=sum(
                1 for segment in items if segment.speaker not in {"ali", "friend"}
            ),
            total_segments=len(items),
            reference_audio_path=(
                str(self.reference_audio_path) if self.reference_audio_path.exists() else None
            ),
            warnings=warnings,
        )


def cosine_similarity(left: np.ndarray, right: np.ndarray) -> float:
    left_norm = float(np.linalg.norm(left))
    right_norm = float(np.linalg.norm(right))
    if left_norm <= 0.0 or right_norm <= 0.0:
        return 0.0

    value = float(np.dot(left, right) / (left_norm * right_norm))
    if math.isnan(value):
        return 0.0
    return max(-1.0, min(1.0, value))


def _safe_track(track_label: Any) -> str:
    clean = str(track_label or "").strip().lower()
    return clean or "unknown"
