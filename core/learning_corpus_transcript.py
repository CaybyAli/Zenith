from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

from core.power_profile import PowerProfile


@dataclass(frozen=True)
class TranscriptResult:
    """Stable transcript payload used by style_fingerprint.json."""

    language: str
    segments_count: int
    first_10s_text: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WhisperRuntimeConfig:
    """Runtime settings for the local faster-whisper wrapper."""

    model_name_or_path: str
    device: str
    compute_type: str
    power_profile: str


class SupportsTranscribe(Protocol):
    def transcribe(self, media_path: str, **kwargs: Any) -> Any:
        ...


class FasterWhisperUnavailable(RuntimeError):
    """Raised when transcript extraction is requested without faster-whisper."""


_DEFAULT_MODEL_BY_TIER = {
    "shadow_only": "tiny",
    "smallest_available": "tiny",
    "default": "small",
    "preferred": "medium",
    "largest_available": "large-v3",
}


def resolve_whisper_runtime_config(
    *,
    power_profile: str | None = None,
    model_name_or_path: str | None = None,
    device: str | None = None,
    compute_type: str | None = None,
) -> WhisperRuntimeConfig:
    """
    Resolve deterministic local faster-whisper settings.

    Explicit arguments win, then environment variables, then the project
    PowerProfile tier. No cloud endpoint is used.
    """

    normalized_profile = PowerProfile.normalize(power_profile or PowerProfile.DEFAULT)
    model_tier = PowerProfile.resolve_model_tier(normalized_profile)

    resolved_model = (
        model_name_or_path
        or os.environ.get("ZENITH_FASTER_WHISPER_MODEL")
        or os.environ.get("ZENITH_WHISPER_MODEL")
        or _DEFAULT_MODEL_BY_TIER.get(model_tier, _DEFAULT_MODEL_BY_TIER["default"])
    )
    resolved_device = device or os.environ.get("ZENITH_FASTER_WHISPER_DEVICE") or "auto"
    resolved_compute_type = (
        compute_type or os.environ.get("ZENITH_FASTER_WHISPER_COMPUTE_TYPE") or "auto"
    )

    return WhisperRuntimeConfig(
        model_name_or_path=str(resolved_model),
        device=str(resolved_device),
        compute_type=str(resolved_compute_type),
        power_profile=normalized_profile,
    )


def build_faster_whisper_model(config: WhisperRuntimeConfig) -> SupportsTranscribe:
    """Create a local faster-whisper model lazily."""

    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception as exc:  # pragma: no cover - exercised only without dependency
        raise FasterWhisperUnavailable(
            "faster-whisper is not available. Install the local package or pass "
            "a test/dummy transcriber into extract_transcript()."
        ) from exc

    return WhisperModel(
        config.model_name_or_path,
        device=config.device,
        compute_type=config.compute_type,
    )


def extract_transcript(
    media_path: str | Path,
    *,
    transcriber: SupportsTranscribe | None = None,
    power_profile: str | None = None,
    model_name_or_path: str | None = None,
    device: str | None = None,
    compute_type: str | None = None,
    first_seconds: float = 10.0,
) -> dict[str, Any]:
    """
    Extract the passive transcript fingerprint for one media input.

    faster-whisper auto-detects language because language is deliberately not
    forced. The output schema is intentionally small and stable:
    language, segments_count, first_10s_text.
    """

    path = Path(media_path)
    if not path.exists():
        raise FileNotFoundError(f"Transcript input does not exist: {path}")
    if first_seconds <= 0:
        raise ValueError("first_seconds must be greater than zero")

    config = resolve_whisper_runtime_config(
        power_profile=power_profile,
        model_name_or_path=model_name_or_path,
        device=device,
        compute_type=compute_type,
    )
    active_transcriber = transcriber or build_faster_whisper_model(config)

    segments_iterable, info = active_transcriber.transcribe(
        str(path),
        language=None,
        vad_filter=False,
        word_timestamps=False,
    )

    segments_count = 0
    first_text_parts: list[str] = []
    for segment in segments_iterable:
        segments_count += 1
        start = _segment_float(segment, "start", default=0.0)
        if start < first_seconds:
            text = _segment_text(segment)
            if text:
                first_text_parts.append(text)

    language = _info_language(info)
    result = TranscriptResult(
        language=language,
        segments_count=segments_count,
        first_10s_text=_normalize_text(" ".join(first_text_parts)),
    )
    return result.to_dict()


def _info_language(info: Any) -> str:
    if isinstance(info, dict):
        value = info.get("language")
    else:
        value = getattr(info, "language", None)

    clean = str(value or "unknown").strip().lower()
    return clean or "unknown"


def _segment_text(segment: Any) -> str:
    if isinstance(segment, dict):
        value = segment.get("text", "")
    else:
        value = getattr(segment, "text", "")
    return _normalize_text(str(value or ""))


def _segment_float(segment: Any, key: str, *, default: float) -> float:
    if isinstance(segment, dict):
        raw_value = segment.get(key, default)
    else:
        raw_value = getattr(segment, key, default)

    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return default


def _normalize_text(value: str) -> str:
    return " ".join(value.replace("\r", " ").replace("\n", " ").split())
