from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from core.ffmpeg_helper import get_ffmpeg_path
from models.file_readability import FileReadabilityResult


MIN_SUSPICIOUS_FILE_SIZE_BYTES = 1024
DEFAULT_CHECK_SECONDS = 3.0
TAIL_LIMIT = 2000


def _tail(text: str | None, limit: int = TAIL_LIMIT) -> str | None:
    if text is None:
        return None

    text = str(text)
    if len(text) <= limit:
        return text

    return text[-limit:]


def check_file_size_basic(path: str | Path) -> tuple[list[str], list[str], dict[str, Any]]:
    file_path = Path(path)
    warnings: list[str] = []
    errors: list[str] = []
    details: dict[str, Any] = {
        "exists": file_path.exists(),
        "size_bytes": None,
    }

    if not file_path.exists():
        errors.append("file_missing")
        return warnings, errors, details

    size = file_path.stat().st_size
    details["size_bytes"] = size

    if size == 0:
        errors.append("empty_file")
    elif size < MIN_SUSPICIOUS_FILE_SIZE_BYTES:
        warnings.append("suspiciously_small_file")

    return warnings, errors, details


def run_ffmpeg_readability_check(
    path: str | Path,
    seconds: float = DEFAULT_CHECK_SECONDS,
    ffmpeg_path: str | None = None,
) -> subprocess.CompletedProcess[str]:
    resolved_ffmpeg_path = ffmpeg_path or get_ffmpeg_path()

    command = [
        resolved_ffmpeg_path,
        "-v",
        "error",
        "-t",
        str(seconds),
        "-i",
        str(path),
        "-f",
        "null",
        "-",
    ]

    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        check=False,
    )


def check_file_readability(
    path: str | Path,
    seconds: float = DEFAULT_CHECK_SECONDS,
    ffmpeg_path: str | None = None,
) -> FileReadabilityResult:
    file_path = Path(path)
    warnings, errors, details = check_file_size_basic(file_path)

    if errors:
        return FileReadabilityResult(
            readable=False,
            status="unreadable",
            severity="error",
            file_path=str(file_path),
            checked_seconds=0.0,
            ffmpeg_returncode=None,
            stdout_tail=None,
            stderr_tail=None,
            warnings=warnings,
            errors=errors,
            recommendation="reject",
            details=details,
        )

    try:
        result = run_ffmpeg_readability_check(
            path=file_path,
            seconds=seconds,
            ffmpeg_path=ffmpeg_path,
        )

        details["ffmpeg_command_checked_seconds"] = seconds

        if result.returncode == 0:
            status = "readable_with_warnings" if warnings else "readable"
            severity = "warning" if warnings else "ok"
            recommendation = "accept_with_review" if warnings else "accept"

            return FileReadabilityResult(
                readable=True,
                status=status,
                severity=severity,
                file_path=str(file_path),
                checked_seconds=seconds,
                ffmpeg_returncode=result.returncode,
                stdout_tail=_tail(result.stdout),
                stderr_tail=_tail(result.stderr),
                warnings=warnings,
                errors=[],
                recommendation=recommendation,
                details=details,
            )

        errors.append("ffmpeg_decode_failed")

        return FileReadabilityResult(
            readable=False,
            status="unreadable",
            severity="error",
            file_path=str(file_path),
            checked_seconds=seconds,
            ffmpeg_returncode=result.returncode,
            stdout_tail=_tail(result.stdout),
            stderr_tail=_tail(result.stderr),
            warnings=warnings,
            errors=errors,
            recommendation="reject",
            details=details,
        )

    except Exception as exc:
        errors.append("readability_check_failed")
        details["exception"] = str(exc)

        return FileReadabilityResult(
            readable=False,
            status="failed",
            severity="error",
            file_path=str(file_path),
            checked_seconds=seconds,
            ffmpeg_returncode=None,
            stdout_tail=None,
            stderr_tail=_tail(str(exc)),
            warnings=warnings,
            errors=errors,
            recommendation="manual_review",
            details=details,
        )
