from __future__ import annotations

from core.transcript_processor import TranscriptProcessor


def test_faster_whisper_runtime_prefers_cuda_when_available(monkeypatch) -> None:
    monkeypatch.delenv("ZENITH_FASTER_WHISPER_DEVICE", raising=False)
    monkeypatch.delenv("ZENITH_FASTER_WHISPER_COMPUTE_TYPE", raising=False)
    monkeypatch.setenv("ZENITH_FASTER_WHISPER_AUTO_CUDA", "1")
    monkeypatch.setattr(
        TranscriptProcessor,
        "_should_prefer_cuda_runtime",
        lambda self: True,
    )

    candidates = TranscriptProcessor()._faster_whisper_runtime_candidates()

    assert candidates == [("cuda", "float16"), ("cpu", "int8")]


def test_faster_whisper_runtime_honors_explicit_env(monkeypatch) -> None:
    monkeypatch.setenv("ZENITH_FASTER_WHISPER_DEVICE", "cpu")
    monkeypatch.setenv("ZENITH_FASTER_WHISPER_COMPUTE_TYPE", "int8")

    candidates = TranscriptProcessor()._faster_whisper_runtime_candidates()

    assert candidates == [("cpu", "int8")]


def test_faster_whisper_auto_cuda_can_be_disabled(monkeypatch) -> None:
    monkeypatch.delenv("ZENITH_FASTER_WHISPER_DEVICE", raising=False)
    monkeypatch.delenv("ZENITH_FASTER_WHISPER_COMPUTE_TYPE", raising=False)
    monkeypatch.setenv("ZENITH_FASTER_WHISPER_AUTO_CUDA", "0")

    candidates = TranscriptProcessor()._faster_whisper_runtime_candidates()

    assert candidates == [("cpu", "int8")]
