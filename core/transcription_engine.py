from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Callable, Iterable

from models.transcript_result import TranscriptResult, TranscriptSegment


class TranscriptUnavailableError(RuntimeError):
    pass


SegmentSanitizer = Callable[[Iterable[Any], str], list[TranscriptSegment]]
RuntimeCandidates = Callable[[], list[tuple[str, str]]]


VALID_TRANSCRIPTION_ENGINES: tuple[str, ...] = ("whisperx", "faster_whisper")
DEFAULT_TRANSCRIPTION_ENGINE = "whisperx"


def normalize_transcription_engine_name(value: str | None) -> str:
    clean = str(value or DEFAULT_TRANSCRIPTION_ENGINE).strip().lower().replace("-", "_")
    if clean in VALID_TRANSCRIPTION_ENGINES:
        return clean
    allowed = ", ".join(VALID_TRANSCRIPTION_ENGINES)
    raise ValueError(f"Unsupported transcription_engine={value!r}; allowed: {allowed}")


def _build_full_text(segments: list[TranscriptSegment]) -> str:
    return " ".join(
        segment.text.strip()
        for segment in segments
        if str(getattr(segment, "text", "") or "").strip()
    ).strip()


class TranscriptionEngine(ABC):
    name: str

    @abstractmethod
    def transcribe(
        self,
        source_path: str,
        *,
        result_source_path: str | None = None,
        audio_track: str = "mic",
        sanitize_segments: SegmentSanitizer,
    ) -> TranscriptResult:
        raise NotImplementedError


class WhisperXEngine(TranscriptionEngine):
    name = "whisperx"

    def __init__(
        self,
        model_name: str,
        *,
        python_path: str | Path | None = None,
        bridge_path: str | Path | None = None,
        timeout_seconds: int | None = None,
    ) -> None:
        self.model_name = model_name
        self.python_path = Path(python_path) if python_path is not None else self._default_python_path()
        self.bridge_path = Path(bridge_path) if bridge_path is not None else self._default_bridge_path()
        self.timeout_seconds = int(
            timeout_seconds
            if timeout_seconds is not None
            else os.getenv("ZENITH_WHISPERX_TIMEOUT_SECONDS", "7200")
        )

    def transcribe(
        self,
        source_path: str,
        *,
        result_source_path: str | None = None,
        audio_track: str = "mic",
        sanitize_segments: SegmentSanitizer,
    ) -> TranscriptResult:
        self._ensure_available()

        with tempfile.TemporaryDirectory(prefix="zenith_whisperx_") as temp_dir:
            report_path = Path(temp_dir) / "whisperx_report.json"
            command = [
                str(self.python_path),
                str(self.bridge_path),
                "--input",
                str(source_path),
                "--output",
                str(report_path),
                "--model",
                self.model_name,
            ]

            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=False,
                timeout=self.timeout_seconds,
            )

            if completed.returncode != 0:
                message = (completed.stderr or completed.stdout or "").strip()
                raise TranscriptUnavailableError(
                    "whisperx failed via bridge subprocess: " + (message or f"returncode={completed.returncode}")
                )

            if not report_path.exists():
                raise TranscriptUnavailableError(
                    f"whisperx bridge did not create report: {report_path}"
                )

            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
            except Exception as exc:
                raise TranscriptUnavailableError(f"whisperx bridge report unreadable: {exc}") from exc

        status = str(report.get("status") or "").strip().lower()
        if status != "ok":
            error = report.get("error") or report.get("message") or "unknown whisperx bridge error"
            raise TranscriptUnavailableError(f"whisperx bridge status={status or 'missing'}: {error}")

        raw_segments = list(report.get("segments") or [])
        segments = sanitize_segments(raw_segments, audio_track)
        if not segments:
            raise TranscriptUnavailableError("whisperx returned no valid segments")

        return TranscriptResult(
            source_path=result_source_path or source_path,
            language=report.get("language"),
            segments=segments,
            full_text=_build_full_text(segments),
            engine=self.name,
        )

    def _ensure_available(self) -> None:
        if os.getenv("ZENITH_WHISPERX_DISABLE", "0").strip().lower() in {"1", "true", "yes", "on"}:
            raise TranscriptUnavailableError("whisperx unavailable: disabled by ZENITH_WHISPERX_DISABLE")

        if not self.python_path.exists():
            raise TranscriptUnavailableError(f"whisperx unavailable: python not found: {self.python_path}")

        if not self.bridge_path.exists():
            raise TranscriptUnavailableError(f"whisperx unavailable: bridge not found: {self.bridge_path}")

    @staticmethod
    def _default_python_path() -> Path:
        configured = os.getenv("ZENITH_WHISPERX_PYTHON")
        if configured:
            return Path(configured)

        root = Path(__file__).resolve().parents[1]
        if os.name == "nt":
            return root / ".venv_whisperx_p5_2" / "Scripts" / "python.exe"
        return root / ".venv_whisperx_p5_2" / "bin" / "python"

    @staticmethod
    def _default_bridge_path() -> Path:
        configured = os.getenv("ZENITH_WHISPERX_BRIDGE")
        if configured:
            return Path(configured)
        return Path(__file__).resolve().with_name("whisperx_bridge_transcribe.py")


class FasterWhisperEngine(TranscriptionEngine):
    name = "faster_whisper"

    def __init__(
        self,
        model_name: str,
        *,
        runtime_candidates: RuntimeCandidates | None = None,
    ) -> None:
        self.model_name = model_name
        self.runtime_candidates = runtime_candidates or default_faster_whisper_runtime_candidates

    def transcribe(
        self,
        source_path: str,
        *,
        result_source_path: str | None = None,
        audio_track: str = "mic",
        sanitize_segments: SegmentSanitizer,
    ) -> TranscriptResult:
        from faster_whisper import WhisperModel

        errors: list[str] = []

        for device, compute_type in self.runtime_candidates():
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

                segments = sanitize_segments(
                    (
                        {
                            "start": segment.start,
                            "end": segment.end,
                            "text": segment.text,
                            "confidence": None,
                            "words": getattr(segment, "words", None),
                        }
                        for segment in raw_segments
                    ),
                    audio_track,
                )

                if not segments:
                    raise TranscriptUnavailableError("faster-whisper returned no valid segments")

                return TranscriptResult(
                    source_path=result_source_path or source_path,
                    language=getattr(info, "language", None),
                    segments=segments,
                    full_text=_build_full_text(segments),
                    engine="faster-whisper",
                )
            except Exception as exc:
                errors.append(f"{device}/{compute_type}: {exc}")

        raise TranscriptUnavailableError(
            "faster-whisper failed for all runtimes: " + "; ".join(errors)
        )


def should_prefer_cuda_runtime() -> bool:
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


def default_faster_whisper_runtime_candidates() -> list[tuple[str, str]]:
    configured_device = os.getenv("ZENITH_FASTER_WHISPER_DEVICE")
    configured_compute_type = os.getenv("ZENITH_FASTER_WHISPER_COMPUTE_TYPE")
    if configured_device or configured_compute_type:
        device = configured_device or "cpu"
        compute_type = configured_compute_type or (
            "float16" if device.lower() == "cuda" else "int8"
        )
        return [(device, compute_type)]

    candidates: list[tuple[str, str]] = []
    if should_prefer_cuda_runtime():
        candidates.append(("cuda", "float16"))

    candidates.append(("cpu", "int8"))
    return candidates


def create_transcription_engine(
    engine_name: str | None,
    *,
    model_name: str,
) -> TranscriptionEngine:
    normalized = normalize_transcription_engine_name(engine_name)
    if normalized == "whisperx":
        return WhisperXEngine(model_name=model_name)
    if normalized == "faster_whisper":
        return FasterWhisperEngine(model_name=model_name)
    raise AssertionError(f"Unhandled transcription engine: {normalized}")
