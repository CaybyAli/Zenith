from __future__ import annotations

from pathlib import Path

import pytest

from core.file_probe import (
    is_supported_video_extension,
    parse_ffprobe_json,
    probe_file,
)
from models.file_info import FileInfo


def test_file_info_to_dict_from_dict_roundtrip() -> None:
    info = FileInfo(
        path="video.mp4",
        exists=True,
        extension=".mp4",
        size_bytes=12345,
        is_supported_format=True,
        duration_seconds=123.456,
        container_format="mov,mp4,m4a,3gp,3g2,mj2",
        video_stream_count=1,
        audio_stream_count=2,
        has_video=True,
        has_audio=True,
        width=1920,
        height=1080,
        fps=59.94,
        video_codecs=["h264"],
        audio_codecs=["aac", "opus"],
        raw_ffprobe={"format": {"duration": "123.456"}},
        probe_status="ok",
        probe_error=None,
    )

    data = info.to_dict()
    restored = FileInfo.from_dict(data)

    assert restored.path == "video.mp4"
    assert restored.exists is True
    assert restored.extension == ".mp4"
    assert restored.duration_seconds == 123.456
    assert restored.width == 1920
    assert restored.height == 1080
    assert restored.fps == 59.94
    assert restored.video_stream_count == 1
    assert restored.audio_stream_count == 2
    assert restored.video_codecs == ["h264"]
    assert restored.audio_codecs == ["aac", "opus"]


def test_supported_video_extensions() -> None:
    assert is_supported_video_extension("video.mp4") is True
    assert is_supported_video_extension("video.mkv") is True
    assert is_supported_video_extension("video.mov") is True
    assert is_supported_video_extension("video.avi") is True
    assert is_supported_video_extension("video.webm") is True
    assert is_supported_video_extension("video.flv") is True

    assert is_supported_video_extension("notes.txt") is False
    assert is_supported_video_extension("image.jpg") is False


def test_parse_ffprobe_json_video_and_audio_streams() -> None:
    fake_ffprobe_json = {
        "format": {
            "duration": "123.456",
            "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
        },
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
                "r_frame_rate": "60000/1001",
            },
            {
                "codec_type": "audio",
                "codec_name": "aac",
            },
            {
                "codec_type": "audio",
                "codec_name": "opus",
            },
        ],
    }

    info = parse_ffprobe_json("example.mp4", fake_ffprobe_json)

    assert info.duration_seconds == pytest.approx(123.456)
    assert info.container_format == "mov,mp4,m4a,3gp,3g2,mj2"
    assert info.video_stream_count == 1
    assert info.audio_stream_count == 2
    assert info.has_video is True
    assert info.has_audio is True
    assert info.width == 1920
    assert info.height == 1080
    assert info.fps == pytest.approx(59.94, abs=0.001)
    assert info.video_codecs == ["h264"]
    assert "aac" in info.audio_codecs
    assert "opus" in info.audio_codecs
    assert info.probe_status == "parsed"


def test_probe_missing_file_returns_missing_status(tmp_path: Path) -> None:
    missing_file = tmp_path / "missing_video.mp4"

    info = probe_file(missing_file)

    assert info.exists is False
    assert info.extension == ".mp4"
    assert info.is_supported_format is True
    assert info.probe_status == "missing"
    assert info.probe_error == "file_not_found"


def test_parse_empty_ffprobe_json_does_not_crash() -> None:
    info = parse_ffprobe_json("empty.mp4", {})

    assert info.video_stream_count == 0
    assert info.audio_stream_count == 0
    assert info.has_video is False
    assert info.has_audio is False
    assert info.width is None
    assert info.height is None
    assert info.fps is None
    assert info.video_codecs == []
    assert info.audio_codecs == []
    assert info.probe_status == "parsed"


def test_parse_broken_ffprobe_json_does_not_crash() -> None:
    info = parse_ffprobe_json("broken.mp4", {"format": [], "streams": "bad"})

    assert info.video_stream_count == 0
    assert info.audio_stream_count == 0
    assert info.has_video is False
    assert info.has_audio is False
    assert info.probe_status == "parsed"


def test_file_probe_files_have_no_bom_and_end_with_newline() -> None:
    paths = [
        Path("models/file_info.py"),
        Path("core/file_probe.py"),
        Path("tests/test_file_info_ffprobe_foundation_smoke.py"),
    ]

    for path in paths:
        data = path.read_bytes()

        assert not data.startswith(b"\xef\xbb\xbf"), f"{path} has UTF-8 BOM"
        assert data.endswith(b"\n"), f"{path} must end with newline"
