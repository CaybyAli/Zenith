from __future__ import annotations

import subprocess
from pathlib import Path

from core.file_readability import (
    TAIL_LIMIT,
    check_file_readability,
)
from models.file_readability import FileReadabilityResult


def _write_bytes(path: Path, size: int) -> None:
    path.write_bytes(b"x" * size)


def test_file_readability_result_roundtrip() -> None:
    result = FileReadabilityResult(
        readable=True,
        status="readable_with_warnings",
        severity="warning",
        file_path="video.mp4",
        checked_seconds=3.0,
        ffmpeg_returncode=0,
        stdout_tail="ok",
        stderr_tail="",
        warnings=["suspiciously_small_file"],
        errors=[],
        recommendation="accept_with_review",
        details={"size_bytes": 512},
    )

    data = result.to_dict()
    restored = FileReadabilityResult.from_dict(data)

    assert restored.readable is True
    assert restored.status == "readable_with_warnings"
    assert restored.severity == "warning"
    assert restored.file_path == "video.mp4"
    assert restored.checked_seconds == 3.0
    assert restored.ffmpeg_returncode == 0
    assert restored.stdout_tail == "ok"
    assert restored.warnings == ["suspiciously_small_file"]
    assert restored.errors == []
    assert restored.recommendation == "accept_with_review"
    assert restored.details["size_bytes"] == 512


def test_missing_file_is_unreadable(tmp_path: Path) -> None:
    missing_file = tmp_path / "missing.mp4"

    result = check_file_readability(missing_file)

    assert result.readable is False
    assert result.status == "unreadable"
    assert result.severity == "error"
    assert "file_missing" in result.errors
    assert result.recommendation == "reject"


def test_empty_file_is_unreadable(tmp_path: Path) -> None:
    file_path = tmp_path / "empty.mp4"
    file_path.write_bytes(b"")

    result = check_file_readability(file_path)

    assert result.readable is False
    assert result.status == "unreadable"
    assert "empty_file" in result.errors
    assert result.recommendation == "reject"


def test_suspiciously_small_file_success_has_warning(
    tmp_path: Path,
    monkeypatch,
) -> None:
    file_path = tmp_path / "small.mp4"
    _write_bytes(file_path, 512)

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_file_readability(file_path, ffmpeg_path="fake_ffmpeg")

    assert result.readable is True
    assert result.status == "readable_with_warnings"
    assert result.severity == "warning"
    assert "suspiciously_small_file" in result.warnings
    assert result.recommendation == "accept_with_review"


def test_ffmpeg_success_is_readable(tmp_path: Path, monkeypatch) -> None:
    file_path = tmp_path / "normal.mp4"
    _write_bytes(file_path, 2048)

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="decoded ok",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_file_readability(file_path, seconds=3.0, ffmpeg_path="fake_ffmpeg")

    assert result.readable is True
    assert result.status == "readable"
    assert result.severity == "ok"
    assert result.ffmpeg_returncode == 0
    assert result.stdout_tail == "decoded ok"
    assert result.recommendation == "accept"


def test_ffmpeg_failure_is_unreadable(tmp_path: Path, monkeypatch) -> None:
    file_path = tmp_path / "broken.mp4"
    _write_bytes(file_path, 2048)

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr="Invalid data found",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_file_readability(file_path, ffmpeg_path="fake_ffmpeg")

    assert result.readable is False
    assert result.status == "unreadable"
    assert result.severity == "error"
    assert result.ffmpeg_returncode == 1
    assert "ffmpeg_decode_failed" in result.errors
    assert "Invalid data found" in result.stderr_tail
    assert result.recommendation == "reject"


def test_ffmpeg_exception_is_failed(tmp_path: Path, monkeypatch) -> None:
    file_path = tmp_path / "exception.mp4"
    _write_bytes(file_path, 2048)

    def fake_run(*args, **kwargs):
        raise RuntimeError("ffmpeg exploded")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_file_readability(file_path, ffmpeg_path="fake_ffmpeg")

    assert result.readable is False
    assert result.status == "failed"
    assert result.severity == "error"
    assert "readability_check_failed" in result.errors
    assert "ffmpeg exploded" in result.stderr_tail
    assert result.recommendation == "manual_review"


def test_tail_limits_long_stderr(tmp_path: Path, monkeypatch) -> None:
    file_path = tmp_path / "long_error.mp4"
    _write_bytes(file_path, 2048)

    long_stderr = "x" * (TAIL_LIMIT + 500)

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr=long_stderr,
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = check_file_readability(file_path, ffmpeg_path="fake_ffmpeg")

    assert result.readable is False
    assert result.stderr_tail is not None
    assert len(result.stderr_tail) <= TAIL_LIMIT
    assert result.stderr_tail == long_stderr[-TAIL_LIMIT:]


def test_file_readability_files_have_no_bom_and_end_with_newline() -> None:
    paths = [
        Path("models/file_readability.py"),
        Path("core/file_readability.py"),
        Path("tests/test_file_readability_smoke.py"),
    ]

    for path in paths:
        data = path.read_bytes()

        assert not data.startswith(b"\xef\xbb\xbf"), f"{path} has UTF-8 BOM"
        assert data.endswith(b"\n"), f"{path} must end with newline"
