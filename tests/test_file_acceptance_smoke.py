from __future__ import annotations

from pathlib import Path

from core.file_acceptance import validate_file_info, validate_file_path
from models.file_acceptance import FileAcceptanceResult
from models.file_info import FileInfo


def _good_file_info() -> FileInfo:
    return FileInfo(
        path="video.mp4",
        exists=True,
        extension=".mp4",
        size_bytes=12345,
        is_supported_format=True,
        duration_seconds=120.0,
        container_format="mov,mp4,m4a,3gp,3g2,mj2",
        video_stream_count=1,
        audio_stream_count=1,
        has_video=True,
        has_audio=True,
        width=1920,
        height=1080,
        fps=60.0,
        video_codecs=["h264"],
        audio_codecs=["aac"],
        raw_ffprobe={},
        probe_status="ok",
        probe_error=None,
    )


def test_file_acceptance_result_roundtrip() -> None:
    result = FileAcceptanceResult(
        accepted=True,
        status="accepted_with_warnings",
        severity="warning",
        reasons=["file_passed_acceptance_rules"],
        warnings=["very_long_file"],
        errors=[],
        file_path="video.mp4",
        extension=".mp4",
        profile_id="gaming_main",
        recommendation="accept_with_review",
        details={"duration_seconds": 18000.0},
    )

    data = result.to_dict()
    restored = FileAcceptanceResult.from_dict(data)

    assert restored.accepted is True
    assert restored.status == "accepted_with_warnings"
    assert restored.severity == "warning"
    assert restored.reasons == ["file_passed_acceptance_rules"]
    assert restored.warnings == ["very_long_file"]
    assert restored.errors == []
    assert restored.file_path == "video.mp4"
    assert restored.extension == ".mp4"
    assert restored.profile_id == "gaming_main"
    assert restored.recommendation == "accept_with_review"
    assert restored.details["duration_seconds"] == 18000.0


def test_good_file_info_is_accepted() -> None:
    result = validate_file_info(_good_file_info())

    assert result.accepted is True
    assert result.status == "accepted"
    assert result.severity == "ok"
    assert result.recommendation == "accept"
    assert result.errors == []
    assert result.warnings == []
    assert "file_passed_acceptance_rules" in result.reasons


def test_unsupported_extension_is_rejected() -> None:
    info = _good_file_info()
    info.path = "notes.txt"
    info.extension = ".txt"
    info.is_supported_format = False

    result = validate_file_info(info)

    assert result.accepted is False
    assert result.status == "rejected"
    assert result.severity == "error"
    assert "unsupported_extension" in result.errors


def test_missing_file_is_rejected() -> None:
    info = _good_file_info()
    info.exists = False
    info.probe_status = "missing"
    info.probe_error = "file_not_found"

    result = validate_file_info(info)

    assert result.accepted is False
    assert "file_missing" in result.errors


def test_probe_failed_is_rejected() -> None:
    info = _good_file_info()
    info.probe_status = "failed"
    info.probe_error = "ffprobe_failed"

    result = validate_file_info(info)

    assert result.accepted is False
    assert "probe_failed" in result.errors
    assert result.details["probe_error"] == "ffprobe_failed"


def test_no_video_is_rejected() -> None:
    info = _good_file_info()
    info.has_video = False
    info.video_stream_count = 0
    info.width = None
    info.height = None
    info.fps = None
    info.video_codecs = []

    result = validate_file_info(info)

    assert result.accepted is False
    assert "no_video_stream" in result.errors


def test_no_audio_is_warning_by_default() -> None:
    info = _good_file_info()
    info.has_audio = False
    info.audio_stream_count = 0
    info.audio_codecs = []

    result = validate_file_info(info)

    assert result.accepted is True
    assert result.status == "accepted_with_warnings"
    assert result.severity == "warning"
    assert result.recommendation == "accept_with_review"
    assert "no_audio_stream" in result.warnings
    assert "no_audio_stream" not in result.errors


def test_no_audio_is_rejected_when_profile_requires_audio() -> None:
    info = _good_file_info()
    info.has_audio = False
    info.audio_stream_count = 0
    info.audio_codecs = []

    profile = {"profile_id": "gaming_main", "require_audio": True}
    result = validate_file_info(info, profile=profile)

    assert result.accepted is False
    assert result.status == "rejected"
    assert result.profile_id == "gaming_main"
    assert "no_audio_stream" in result.errors
    assert "no_audio_stream" not in result.warnings


def test_invalid_duration_is_rejected() -> None:
    info = _good_file_info()
    info.duration_seconds = 0

    result = validate_file_info(info)

    assert result.accepted is False
    assert "invalid_duration" in result.errors


def test_very_long_file_gets_warning() -> None:
    info = _good_file_info()
    info.duration_seconds = 5 * 60 * 60

    result = validate_file_info(info)

    assert result.accepted is True
    assert result.status == "accepted_with_warnings"
    assert "very_long_file" in result.warnings


def test_validate_file_path_missing_file_does_not_crash(tmp_path: Path) -> None:
    missing_file = tmp_path / "missing.mp4"

    result = validate_file_path(missing_file)

    assert result.accepted is False
    assert result.status == "rejected"
    assert "file_missing" in result.errors


def test_file_acceptance_files_have_no_bom_and_end_with_newline() -> None:
    paths = [
        Path("models/file_acceptance.py"),
        Path("core/file_acceptance.py"),
        Path("tests/test_file_acceptance_smoke.py"),
    ]

    for path in paths:
        data = path.read_bytes()

        assert not data.startswith(b"\xef\xbb\xbf"), f"{path} has UTF-8 BOM"
        assert data.endswith(b"\n"), f"{path} must end with newline"
