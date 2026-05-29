import os
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

from core.audio_stream_inspector import (
    AudioStream,
    AudioStreamInspectionError,
    AudioStreamInspector,
)
from core.transcription_engine import (
    DEFAULT_TRANSCRIPTION_ENGINE,
    FasterWhisperEngine,
    TranscriptUnavailableError,
    TranscriptionEngine,
    create_transcription_engine,
    normalize_transcription_engine_name,
)
from models.transcript_result import TranscriptResult, TranscriptSegment, TranscriptWord


class TranscriptProcessor:
    def __init__(
        self,
        model_name: Optional[str] = None,
        allow_test_fallback: Optional[bool] = None,
        audio_stream_inspector: AudioStreamInspector | None = None,
        transcription_engine: str | TranscriptionEngine | None = None,
    ) -> None:
        self.model_name = model_name or os.getenv("ZENITH_WHISPER_MODEL", "base")
        self.allow_test_fallback = (
            allow_test_fallback
            if allow_test_fallback is not None
            else os.getenv("ZENITH_TRANSCRIPT_TEST_MODE") == "1"
        )
        self.audio_stream_inspector = audio_stream_inspector or AudioStreamInspector()

        if isinstance(transcription_engine, TranscriptionEngine):
            self.transcription_engine_name = transcription_engine.name
            self.transcription_engine = transcription_engine
        else:
            configured_engine = (
                transcription_engine
                or os.getenv("ZENITH_TRANSCRIPTION_ENGINE")
                or DEFAULT_TRANSCRIPTION_ENGINE
            )
            self.transcription_engine_name = normalize_transcription_engine_name(configured_engine)
            self.transcription_engine = create_transcription_engine(
                self.transcription_engine_name,
                model_name=self.model_name,
            )

    def transcribe(self, video_path: str, audio_stream_index: int = 1) -> TranscriptResult:
        source_path = str(video_path)
        source = Path(source_path)

        if self.allow_test_fallback:
            return self._test_fallback(source_path)

        if not source.exists():
            raise FileNotFoundError(f"Transcript source not found: {source_path}")

        with self._selected_audio_source(source_path, audio_stream_index) as selected:
            return self.transcription_engine.transcribe(
                selected.source_path,
                result_source_path=source_path,
                audio_track=selected.audio_track,
                sanitize_segments=self._sanitize_segments,
            )

    def transcribe_all_streams(self, video_path: str) -> dict[str, TranscriptResult]:
        source_path = str(video_path)
        source = Path(source_path)

        if not source.exists() and not self.allow_test_fallback:
            raise FileNotFoundError(f"Transcript source not found: {source_path}")

        try:
            inventory = self.audio_stream_inspector.inspect(source_path)
        except (AudioStreamInspectionError, FileNotFoundError):
            if not self.allow_test_fallback:
                raise
            return {"mic": self._test_fallback(source_path, audio_track="mic")}
        if not inventory.streams:
            raise TranscriptUnavailableError("No audio streams available for transcription")

        results: dict[str, TranscriptResult] = {}
        for stream in inventory.streams:
            label = self._unique_track_label(stream.label, results)
            if self.allow_test_fallback:
                results[label] = self._test_fallback(source_path, audio_track=label)
                continue

            result = self.transcribe(source_path, audio_stream_index=stream.index)
            self._stamp_audio_track(result, label)
            results[label] = result

        return results

    def _transcribe_with_faster_whisper(
        self,
        source_path: str,
        *,
        result_source_path: str | None = None,
        audio_track: str = "mic",
    ) -> TranscriptResult:
        engine = FasterWhisperEngine(
            model_name=self.model_name,
            runtime_candidates=self._faster_whisper_runtime_candidates,
        )
        return engine.transcribe(
            source_path,
            result_source_path=result_source_path,
            audio_track=audio_track,
            sanitize_segments=self._sanitize_segments,
        )

    def _faster_whisper_runtime_candidates(self) -> list[tuple[str, str]]:
        configured_device = os.getenv("ZENITH_FASTER_WHISPER_DEVICE")
        configured_compute_type = os.getenv("ZENITH_FASTER_WHISPER_COMPUTE_TYPE")
        if configured_device or configured_compute_type:
            device = configured_device or "cpu"
            compute_type = configured_compute_type or (
                "float16" if device.lower() == "cuda" else "int8"
            )
            return [(device, compute_type)]

        candidates: list[tuple[str, str]] = []
        if self._should_prefer_cuda_runtime():
            candidates.append(("cuda", "float16"))

        candidates.append(("cpu", "int8"))
        return candidates

    def _should_prefer_cuda_runtime(self) -> bool:
        if os.getenv("ZENITH_FASTER_WHISPER_AUTO_CUDA", "0").strip().lower() in {
            "0",
            "false",
            "no",
            "off",
        }:
            return False
        try:
            probe = subprocess.run(
                ["nvidia-smi", "-L"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return False

        return probe.returncode == 0 and bool(probe.stdout.strip())

    def _test_fallback(self, source_path: str, audio_track: str = "mic") -> TranscriptResult:
        segments = [
            TranscriptSegment(
                start_seconds=0.0,
                end_seconds=1.4,
                text="Zenith transcript smoke test segment one.",
                confidence=None,
                audio_track=audio_track,
                speaker="unknown",
            ),
            TranscriptSegment(
                start_seconds=1.5,
                end_seconds=3.2,
                text="This is a deterministic test fallback, not productive Whisper output.",
                confidence=None,
                audio_track=audio_track,
                speaker="unknown",
            ),
        ]

        return TranscriptResult(
            source_path=source_path,
            language="test",
            segments=segments,
            full_text=self._build_full_text(segments),
            engine="test-fallback",
        )

    def _sanitize_segments(
        self,
        raw_segments: Iterable[Any],
        audio_track: str = "mic",
    ) -> list[TranscriptSegment]:
        sanitized = []
        for item in raw_segments:
            if isinstance(item, dict):
                start = item.get("start")
                end = item.get("end")
                text = item.get("text")
                confidence = item.get("confidence")
                raw_words = item.get("words") or []
                item_audio_track = item.get("audio_track")
                item_speaker = item.get("speaker")
            else:
                start = getattr(item, "start", None)
                end = getattr(item, "end", None)
                text = getattr(item, "text", None)
                confidence = getattr(item, "confidence", None)
                raw_words = getattr(item, "words", None) or []
                item_audio_track = getattr(item, "audio_track", None)
                item_speaker = getattr(item, "speaker", None)

            try:
                start_seconds = max(0.0, float(start))
                end_seconds = max(0.0, float(end))
            except (TypeError, ValueError):
                continue

            clean_text = str(text or "").strip()

            if not clean_text:
                continue

            if end_seconds <= start_seconds:
                continue

            words = self._sanitize_words(raw_words)

            sanitized.append(
                TranscriptSegment(
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                    text=clean_text,
                    confidence=confidence if isinstance(confidence, float) else None,
                    words=words,
                    audio_track=self._safe_audio_track(item_audio_track, audio_track),
                    speaker=self._safe_speaker(item_speaker),
                )
            )

        sanitized.sort(key=lambda segment: segment.start_seconds)
        return sanitized

    def _sanitize_words(self, raw_words: Iterable[Any]) -> list[TranscriptWord]:
        words: list[TranscriptWord] = []

        for item in raw_words or []:
            if isinstance(item, dict):
                start = item.get("start")
                end = item.get("end")
                text = item.get("word", item.get("text"))
                probability = item.get("probability")
            else:
                start = getattr(item, "start", None)
                end = getattr(item, "end", None)
                text = getattr(item, "word", None) or getattr(item, "text", None)
                probability = getattr(item, "probability", None)

            try:
                start_seconds = max(0.0, float(start))
                end_seconds = max(0.0, float(end))
            except (TypeError, ValueError):
                continue

            clean_text = str(text or "").strip()
            if not clean_text:
                continue

            if end_seconds <= start_seconds:
                continue

            try:
                safe_probability = float(probability) if probability is not None else None
            except (TypeError, ValueError):
                safe_probability = None

            words.append(
                TranscriptWord(
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                    text=clean_text,
                    probability=safe_probability,
                )
            )

        words.sort(key=lambda word: word.start_seconds)
        return words

    def _build_full_text(self, segments: list[TranscriptSegment]) -> str:
        return " ".join(segment.text.strip() for segment in segments if segment.text.strip()).strip()

    @contextmanager
    def _selected_audio_source(
        self,
        source_path: str,
        audio_stream_index: int,
    ) -> Iterator["_SelectedAudioSource"]:
        try:
            inventory = self.audio_stream_inspector.inspect(source_path)
        except (AudioStreamInspectionError, FileNotFoundError):
            yield _SelectedAudioSource(source_path=source_path, audio_track="mic")
            return

        if not inventory.streams:
            raise TranscriptUnavailableError("No audio streams available for transcription")

        selected_stream = self._resolve_audio_stream(
            inventory.streams,
            audio_stream_index=audio_stream_index,
        )

        if len(inventory.streams) == 1:
            yield _SelectedAudioSource(source_path=source_path, audio_track="mic")
            return

        audio_track = self._safe_audio_track(selected_stream.label, "unknown")
        with tempfile.TemporaryDirectory(prefix="zenith_audio_stream_") as temp_dir:
            extracted_path = str(Path(temp_dir) / f"stream_{selected_stream.index}.wav")
            self._extract_audio_stream(
                source_path=source_path,
                stream_index=selected_stream.index,
                output_path=extracted_path,
            )
            yield _SelectedAudioSource(
                source_path=extracted_path,
                audio_track=audio_track,
            )

    def _resolve_audio_stream(
        self,
        streams: list[AudioStream],
        *,
        audio_stream_index: int,
    ) -> AudioStream:
        for stream in streams:
            if stream.index == audio_stream_index:
                return stream

        if len(streams) == 1:
            return streams[0]

        if 0 <= audio_stream_index < len(streams):
            return streams[audio_stream_index]

        available = ", ".join(str(stream.index) for stream in streams)
        raise TranscriptUnavailableError(
            f"Audio stream {audio_stream_index} not found; available streams: {available}"
        )

    def _extract_audio_stream(
        self,
        *,
        source_path: str,
        stream_index: int,
        output_path: str,
    ) -> None:
        command = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            source_path,
            "-map",
            f"0:{stream_index}",
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            output_path,
        ]
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
            timeout=120,
        )
        if completed.returncode != 0:
            message = (completed.stderr or completed.stdout or "").strip()
            raise TranscriptUnavailableError(
                f"Failed to extract audio stream {stream_index}: {message}"
            )

    def _unique_track_label(
        self,
        label: str,
        existing_results: dict[str, TranscriptResult],
    ) -> str:
        safe_label = self._safe_audio_track(label, "unknown")
        if safe_label not in existing_results:
            return safe_label

        suffix = 2
        while f"{safe_label}_{suffix}" in existing_results:
            suffix += 1
        return f"{safe_label}_{suffix}"

    def _stamp_audio_track(self, result: TranscriptResult, audio_track: str) -> None:
        safe_track = self._safe_audio_track(audio_track, "unknown")
        for segment in result.segments or []:
            segment.audio_track = safe_track

    def _safe_audio_track(self, value: Any, default: str) -> str:
        clean = str(value or "").strip().lower()
        if clean in {"mic", "discord", "ingame", "unknown"}:
            return clean
        if clean:
            return clean
        return default

    def _safe_speaker(self, value: Any) -> str:
        clean = str(value or "").strip().lower()
        if clean in {"ali", "friend", "unknown"}:
            return clean
        return "unknown"


class _SelectedAudioSource:
    def __init__(self, source_path: str, audio_track: str) -> None:
        self.source_path = source_path
        self.audio_track = audio_track
