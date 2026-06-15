from __future__ import annotations

import os
from pathlib import Path

import pytest


pytestmark = pytest.mark.real_whisper

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "whisper_probe.wav"


def _resolve_model_name() -> str:
    return os.getenv("ZENITH_WHISPER_MODEL", "large-v3")


def _resolve_device() -> str:
    return os.getenv("ZENITH_FASTER_WHISPER_DEVICE", "cpu")


def _resolve_compute_type() -> str:
    return os.getenv("ZENITH_FASTER_WHISPER_COMPUTE_TYPE", "int8")


def test_p3_1_whisper_probe_real_inference(monkeypatch) -> None:
    """P3-1: real faster-whisper inference on whisper_probe.wav, no stubs."""

    faster_whisper = pytest.importorskip(
        "faster_whisper",
        reason="faster-whisper not installed",
    )

    monkeypatch.delenv("ZENITH_TRANSCRIPT_TEST_MODE", raising=False)
    monkeypatch.setenv("HF_HUB_OFFLINE", "1")
    monkeypatch.setenv("TRANSFORMERS_OFFLINE", "1")

    assert FIXTURE_PATH.exists(), f"Fixture not found: {FIXTURE_PATH}"

    model = faster_whisper.WhisperModel(
        _resolve_model_name(),
        device=_resolve_device(),
        compute_type=_resolve_compute_type(),
    )

    segments_iter, info = model.transcribe(str(FIXTURE_PATH), beam_size=5, vad_filter=True)
    segments = list(segments_iter)

    assert info.duration > 0
    assert info.language is not None
    assert segments

    full_text = " ".join(segment.text.strip() for segment in segments).strip().lower()

    assert "fox" in full_text
    assert "dog" in full_text

    print()
    print(f"model={_resolve_model_name()}")
    print(f"device={_resolve_device()}")
    print(f"compute_type={_resolve_compute_type()}")
    print(f"language={info.language}")
    print(f"duration={info.duration}")
    print(f"segments={len(segments)}")
    print(f"text={full_text}")
