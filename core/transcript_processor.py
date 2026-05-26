import os
import subprocess
from pathlib import Path
from typing import Any, Iterable, Optional

from models.transcript_result import TranscriptResult, TranscriptSegment, TranscriptWord


class TranscriptUnavailableError(RuntimeError):
    pass


class TranscriptProcessor:
    def __init__(self, model_name: Optional[str] = None, allow_test_fallback: Optional[bool] = None) -> None:
        self.model_name = model_name or os.getenv("ZENITH_WHISPER_MODEL", "base")
        self.allow_test_fallback = (
            allow_test_fallback
            if allow_test_fallback is not None
            else os.getenv("ZENITH_TRANSCRIPT_TEST_MODE") == "1"
        )

    def transcribe(self, video_path: str) -> TranscriptResult:
        source_path = str(video_path)
        source = Path(source_path)

        if self.allow_test_fallback:
            return self._test_fallback(source_path)

        if not source.exists():
            raise FileNotFoundError(f"Transcript source not found: {source_path}")

        errors = []

        try:
            return self._transcribe_with_faster_whisper(source_path)
        except ImportError as exc:
            errors.append(f"faster-whisper unavailable: {exc}")
        except Exception as exc:
            errors.append(f"faster-whisper failed: {exc}")

        try:
            return self._transcribe_with_openai_whisper(source_path)
        except ImportError as exc:
            errors.append(f"whisper unavailable: {exc}")
        except Exception as exc:
            errors.append(f"whisper failed: {exc}")

        raise TranscriptUnavailableError("; ".join(errors) or "No transcript engine available")

    def _transcribe_with_faster_whisper(self, source_path: str) -> TranscriptResult:
        from faster_whisper import WhisperModel

        errors: list[str] = []

        for device, compute_type in self._faster_whisper_runtime_candidates():
            try:
                model = WhisperModel(
                    self.model_name,
                    device=device,
                    compute_type=compute_type,
                )
                raw_segments, info = model.transcribe(
                    source_path,
                    vad_filter=True,
                    word_timestamps=True,
                )

                segments = self._sanitize_segments(
                    {
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text,
                        "confidence": None,
                        "words": getattr(segment, "words", None),
                    }
                    for segment in raw_segments
                )

                if not segments:
                    raise TranscriptUnavailableError(
                        "faster-whisper returned no valid segments"
                    )

                return TranscriptResult(
                    source_path=source_path,
                    language=getattr(info, "language", None),
                    segments=segments,
                    full_text=self._build_full_text(segments),
                    engine="faster-whisper",
                )
            except Exception as exc:
                errors.append(f"{device}/{compute_type}: {exc}")

        raise TranscriptUnavailableError(
            "faster-whisper failed for all runtimes: " + "; ".join(errors)
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

    def _transcribe_with_openai_whisper(self, source_path: str) -> TranscriptResult:
        import whisper

        model = whisper.load_model(self.model_name)
        result = model.transcribe(source_path)

        segments = self._sanitize_segments(result.get("segments", []))

        if not segments:
            raise TranscriptUnavailableError("whisper returned no valid segments")

        return TranscriptResult(
            source_path=source_path,
            language=result.get("language"),
            segments=segments,
            full_text=self._build_full_text(segments),
            engine="whisper",
        )

    def _test_fallback(self, source_path: str) -> TranscriptResult:
        segments = [
            TranscriptSegment(
                start_seconds=0.0,
                end_seconds=1.4,
                text="Zenith transcript smoke test segment one.",
                confidence=None,
            ),
            TranscriptSegment(
                start_seconds=1.5,
                end_seconds=3.2,
                text="This is a deterministic test fallback, not productive Whisper output.",
                confidence=None,
            ),
        ]

        return TranscriptResult(
            source_path=source_path,
            language="test",
            segments=segments,
            full_text=self._build_full_text(segments),
            engine="test-fallback",
        )

    def _sanitize_segments(self, raw_segments: Iterable[Any]) -> list[TranscriptSegment]:
        sanitized = []

        for item in raw_segments:
            if isinstance(item, dict):
                start = item.get("start")
                end = item.get("end")
                text = item.get("text")
                confidence = item.get("confidence")
                raw_words = item.get("words") or []
            else:
                start = getattr(item, "start", None)
                end = getattr(item, "end", None)
                text = getattr(item, "text", None)
                confidence = getattr(item, "confidence", None)
                raw_words = getattr(item, "words", None) or []

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
