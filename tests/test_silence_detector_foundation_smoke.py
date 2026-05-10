from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from models.silence_detection import SilenceDetectionResult, SilenceSegment
from core.silence_detector import (
    build_silencedetect_command,
    detect_silence,
    parse_silencedetect_output,
)


# ---------------------------------------------------------------------------
# Model round-trips
# ---------------------------------------------------------------------------

def test_silence_segment_roundtrip() -> None:
    seg = SilenceSegment(
        start_seconds=1.5,
        end_seconds=2.1,
        duration_seconds=0.6,
        threshold_db=-40.0,
        warnings=["test_warning"],
        metadata={"key": "value"},
    )
    d = seg.to_dict()
    restored = SilenceSegment.from_dict(d)
    assert restored.start_seconds == seg.start_seconds
    assert restored.end_seconds == seg.end_seconds
    assert restored.duration_seconds == seg.duration_seconds
    assert restored.threshold_db == seg.threshold_db
    assert restored.warnings == seg.warnings
    assert restored.metadata == seg.metadata
    assert restored.source == seg.source
    assert restored.classification == seg.classification
    assert restored.remove_candidate == seg.remove_candidate
    assert restored.confidence == seg.confidence


def test_silence_detection_result_roundtrip() -> None:
    seg = SilenceSegment(start_seconds=1.0, end_seconds=2.0, duration_seconds=1.0)
    result = SilenceDetectionResult(
        source_path="/fake/audio.wav",
        status="ok",
        segments=[seg],
        segment_count=1,
        total_silence_seconds=1.0,
        warnings=["w1"],
        errors=[],
        command_preview=["ffmpeg", "-i", "/fake/audio.wav"],
        metadata={"extra": "data"},
    )
    d = result.to_dict()
    restored = SilenceDetectionResult.from_dict(d)
    assert restored.source_path == result.source_path
    assert restored.status == result.status
    assert restored.engine == result.engine
    assert restored.segment_count == result.segment_count
    assert restored.total_silence_seconds == result.total_silence_seconds
    assert len(restored.segments) == 1
    assert restored.segments[0].start_seconds == 1.0
    assert restored.warnings == ["w1"]
    assert restored.errors == []
    assert restored.metadata == {"extra": "data"}


# ---------------------------------------------------------------------------
# Command builder
# ---------------------------------------------------------------------------

def test_build_silencedetect_command_contains_expected_parts() -> None:
    cmd = build_silencedetect_command(
        source_path="/fake/audio.wav",
        threshold_db=-40.0,
        min_duration_seconds=0.4,
        ffmpeg_path="ffmpeg",
    )
    joined = " ".join(cmd)
    assert "ffmpeg" in cmd[0]
    assert "-af" in cmd
    assert "silencedetect" in joined
    assert "noise=-40.0dB" in joined
    assert "d=0.4" in joined
    assert "/fake/audio.wav" in cmd


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

FAKE_OUTPUT_TWO_SEGMENTS = """\
ffmpeg version 6.0
[silencedetect @ abc] silence_start: 1.500
[silencedetect @ abc] silence_end: 2.100 | silence_duration: 0.600
[silencedetect @ abc] silence_start: 5.000
[silencedetect @ abc] silence_end: 6.250 | silence_duration: 1.250
"""


def test_parse_silencedetect_output_parses_segments() -> None:
    result = parse_silencedetect_output(
        source_path="/fake/audio.wav",
        output=FAKE_OUTPUT_TWO_SEGMENTS,
        threshold_db=-40.0,
        min_duration_seconds=0.4,
        command_preview=["ffmpeg"],
    )
    assert result.status == "ok"
    assert result.segment_count == 2
    assert abs(result.total_silence_seconds - 1.85) < 0.001
    assert result.segments[0].start_seconds == 1.5
    assert result.segments[0].end_seconds == 2.1
    assert result.segments[0].duration_seconds == 0.6
    assert result.segments[1].start_seconds == 5.0
    assert result.segments[1].end_seconds == 6.25
    assert result.segments[1].duration_seconds == 1.25


def test_parse_empty_output_returns_ok_with_zero_segments() -> None:
    result = parse_silencedetect_output(
        source_path="/fake/audio.wav",
        output="",
        threshold_db=-40.0,
        min_duration_seconds=0.4,
        command_preview=["ffmpeg"],
    )
    assert result.status == "ok"
    assert result.segment_count == 0
    assert result.total_silence_seconds == 0.0
    assert result.errors == []


def test_parse_orphan_end_adds_warning_not_crash() -> None:
    orphan_output = "[silencedetect @ abc] silence_end: 3.000 | silence_duration: 0.500\n"
    result = parse_silencedetect_output(
        source_path="/fake/audio.wav",
        output=orphan_output,
        threshold_db=-40.0,
        min_duration_seconds=0.4,
        command_preview=["ffmpeg"],
    )
    assert result.status == "ok"
    assert any("orphan_silence_end" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# detect_silence monkeypatch tests
# ---------------------------------------------------------------------------

FAKE_FFMPEG_SUCCESS_OUTPUT = """\
[silencedetect @ abc] silence_start: 2.000
[silencedetect @ abc] silence_end: 3.500 | silence_duration: 1.500
"""


def test_detect_silence_success_with_monkeypatch(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_proc = MagicMock()
    fake_proc.returncode = 0
    fake_proc.stdout = FAKE_FFMPEG_SUCCESS_OUTPUT

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake_proc)

    result = detect_silence(
        source_path="/fake/audio.wav",
        ffmpeg_path="ffmpeg",
    )
    assert result.status == "ok"
    assert result.segment_count > 0


def test_detect_silence_failure_with_monkeypatch(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_proc = MagicMock()
    fake_proc.returncode = 1
    fake_proc.stdout = "ffmpeg error: something went wrong"

    monkeypatch.setattr(subprocess, "run", lambda *a, **kw: fake_proc)

    result = detect_silence(
        source_path="/fake/audio.wav",
        ffmpeg_path="ffmpeg",
    )
    assert result.status == "failed"
    assert "ffmpeg_silencedetect_failed" in result.errors


def test_detect_silence_exception_with_monkeypatch(monkeypatch: pytest.MonkeyPatch) -> None:
    def raise_error(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("subprocess boom")

    monkeypatch.setattr(subprocess, "run", raise_error)

    result = detect_silence(
        source_path="/fake/audio.wav",
        ffmpeg_path="ffmpeg",
    )
    assert result.status == "failed"
    assert "silence_detection_failed" in result.errors


# ---------------------------------------------------------------------------
# BOM / Newline hygiene
# ---------------------------------------------------------------------------

def test_silence_detector_files_have_no_bom_and_end_with_newline() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    files = [
        repo_root / "models" / "silence_detection.py",
        repo_root / "core" / "silence_detector.py",
        repo_root / "tests" / "test_silence_detector_foundation_smoke.py",
    ]
    for fpath in files:
        raw = fpath.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf"), f"BOM found in {fpath}"
        assert raw.endswith(b"\n"), f"Missing trailing newline in {fpath}"
