from __future__ import annotations

from pathlib import Path

from core.stream_classifier import (
    classify_file_streams,
    extract_stream_infos_from_ffprobe,
)
from models.file_info import FileInfo
from models.stream_info import StreamClassificationResult, StreamInfo


def _file_info_with_raw(raw_ffprobe: dict) -> FileInfo:
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
        fps=59.94,
        video_codecs=["h264"],
        audio_codecs=["aac"],
        raw_ffprobe=raw_ffprobe,
        probe_status="ok",
        probe_error=None,
    )


def test_stream_info_roundtrip() -> None:
    stream = StreamInfo(
        index=1,
        codec_type="audio",
        codec_name="aac",
        channels=2,
        sample_rate=48000,
        duration_seconds=120.0,
        language="eng",
        title="Microphone",
        handler_name="SoundHandler",
        tags={"title": "Microphone"},
        role="audio_candidate_voice",
        confidence=0.85,
        reasons=["matched_voice_keyword"],
    )

    data = stream.to_dict()
    restored = StreamInfo.from_dict(data)

    assert restored.index == 1
    assert restored.codec_type == "audio"
    assert restored.codec_name == "aac"
    assert restored.channels == 2
    assert restored.sample_rate == 48000
    assert restored.title == "Microphone"
    assert restored.role == "audio_candidate_voice"
    assert restored.confidence == 0.85
    assert restored.reasons == ["matched_voice_keyword"]


def test_stream_classification_result_roundtrip() -> None:
    result = StreamClassificationResult(
        file_path="video.mp4",
        stream_count=2,
        video_streams=[{"index": 0, "role": "video_primary"}],
        audio_streams=[{"index": 1, "role": "audio_candidate_voice"}],
        primary_video_stream={"index": 0, "role": "video_primary"},
        primary_audio_stream=None,
        voice_audio_candidates=[{"index": 1, "role": "audio_candidate_voice"}],
        warnings=[],
        needs_manual_review=False,
    )

    data = result.to_dict()
    restored = StreamClassificationResult.from_dict(data)

    assert restored.file_path == "video.mp4"
    assert restored.stream_count == 2
    assert restored.primary_video_stream["role"] == "video_primary"
    assert len(restored.voice_audio_candidates) == 1
    assert restored.needs_manual_review is False


def test_video_primary_and_audio_roles_are_classified() -> None:
    raw_ffprobe = {
        "streams": [
            {
                "index": 0,
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
                "r_frame_rate": "60000/1001",
            },
            {
                "index": 1,
                "codec_type": "audio",
                "codec_name": "aac",
                "tags": {"title": "Microphone"},
            },
            {
                "index": 2,
                "codec_type": "audio",
                "codec_name": "aac",
                "tags": {"title": "Desktop Audio"},
            },
            {
                "index": 3,
                "codec_type": "audio",
                "codec_name": "opus",
                "tags": {"title": "Discord"},
            },
        ]
    }

    extracted = extract_stream_infos_from_ffprobe(raw_ffprobe)
    result = classify_file_streams(_file_info_with_raw(raw_ffprobe))

    assert len(extracted) == 4
    assert result.stream_count == 4
    assert result.primary_video_stream["role"] == "video_primary"
    assert result.primary_video_stream["fps"] == 59.94
    assert len(result.voice_audio_candidates) == 1
    assert len(result.game_audio_candidates) == 1
    assert len(result.discord_audio_candidates) == 1
    assert result.voice_audio_candidates[0]["role"] == "audio_candidate_voice"
    assert result.game_audio_candidates[0]["role"] == "audio_candidate_game"
    assert result.discord_audio_candidates[0]["role"] == "audio_candidate_discord"
    assert result.needs_manual_review is False


def test_music_audio_candidate_is_classified() -> None:
    raw_ffprobe = {
        "streams": [
            {
                "index": 0,
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
                "r_frame_rate": "30/1",
            },
            {
                "index": 1,
                "codec_type": "audio",
                "codec_name": "aac",
                "tags": {"title": "Music Browser Alerts"},
            },
        ]
    }

    result = classify_file_streams(_file_info_with_raw(raw_ffprobe))

    assert len(result.music_audio_candidates) == 1
    assert result.music_audio_candidates[0]["role"] == "audio_candidate_music"
    assert result.music_audio_candidates[0]["confidence"] == 0.85


def test_unknown_audio_streams_trigger_manual_review() -> None:
    raw_ffprobe = {
        "streams": [
            {
                "index": 0,
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
                "r_frame_rate": "60/1",
            },
            {
                "index": 1,
                "codec_type": "audio",
                "codec_name": "aac",
            },
            {
                "index": 2,
                "codec_type": "audio",
                "codec_name": "aac",
            },
        ]
    }

    result = classify_file_streams(_file_info_with_raw(raw_ffprobe))

    assert result.needs_manual_review is True
    assert "multiple_audio_streams_without_voice_candidate" in result.warnings
    assert "unknown_audio_streams_present" in result.warnings
    assert len(result.unknown_audio_streams) == 1


def test_empty_ffprobe_does_not_crash() -> None:
    result = classify_file_streams(_file_info_with_raw({}))

    assert result.stream_count == 0
    assert result.video_streams == []
    assert result.audio_streams == []
    assert result.needs_manual_review is True
    assert "no_streams_found" in result.warnings
    assert "no_video_stream" in result.warnings


def test_file_with_no_video_triggers_warning() -> None:
    raw_ffprobe = {
        "streams": [
            {
                "index": 1,
                "codec_type": "audio",
                "codec_name": "aac",
                "tags": {"title": "Microphone"},
            },
        ]
    }

    result = classify_file_streams(_file_info_with_raw(raw_ffprobe))

    assert result.stream_count == 1
    assert result.primary_video_stream is None
    assert "no_video_stream" in result.warnings
    assert result.needs_manual_review is True


def test_stream_classifier_files_have_no_bom_and_end_with_newline() -> None:
    paths = [
        Path("models/stream_info.py"),
        Path("core/stream_classifier.py"),
        Path("tests/test_stream_classifier_smoke.py"),
    ]

    for path in paths:
        data = path.read_bytes()

        assert not data.startswith(b"\xef\xbb\xbf"), f"{path} has UTF-8 BOM"
        assert data.endswith(b"\n"), f"{path} must end with newline"
