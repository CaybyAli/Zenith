import os
from pathlib import Path
from typing import Any, Iterable, Optional

from models.transcript_result import TranscriptResult, TranscriptSegment


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

        model = WhisperModel(self.model_name)
        raw_segments, info = model.transcribe(source_path, vad_filter=True)

        segments = self._sanitize_segments(
            {
                "start": segment.start,
                "end": segment.end,
                "text": segment.text,
                "confidence": None,
            }
            for segment in raw_segments
        )

        if not segments:
            raise TranscriptUnavailableError("faster-whisper returned no valid segments")

        return TranscriptResult(
            source_path=source_path,
            language=getattr(info, "language", None),
            segments=segments,
            full_text=self._build_full_text(segments),
            engine="faster-whisper",
        )

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
            else:
                start = getattr(item, "start", None)
                end = getattr(item, "end", None)
                text = getattr(item, "text", None)
                confidence = getattr(item, "confidence", None)

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

            sanitized.append(
                TranscriptSegment(
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                    text=clean_text,
                    confidence=confidence if isinstance(confidence, float) else None,
                )
            )

        sanitized.sort(key=lambda segment: segment.start_seconds)
        return sanitized

    def _build_full_text(self, segments: list[TranscriptSegment]) -> str:
        return " ".join(segment.text.strip() for segment in segments if segment.text.strip()).strip()