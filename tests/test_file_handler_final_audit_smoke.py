from __future__ import annotations

import subprocess
from pathlib import Path

import core.file_handler as file_handler
from core.file_acceptance import validate_file_info
from core.file_probe import parse_ffprobe_json
from core.file_readability import check_file_readability
from core.stream_classifier import classify_file_streams
from models.file_info import FileInfo
from models.file_readability import FileReadabilityResult
from models.job import Job


EXPECTED_FILE_HANDLER_EVENTS = {
    "FILE_PROBED",
    "FILE_ACCEPTANCE_CHECKED",
    "STREAMS_CLASSIFIED",
    "FILE_READABILITY_CHECKED",
    "FILE_HANDLER_PASSED",
    "FILE_REJECTED",
    "FILE_UNREADABLE",
    "FILE_HANDLER_SKIPPED",
}


def _job_from_dict() -> Job:
    return Job.from_dict(
        {
            "job_id": "job_file_handler_final_audit",
            "job_type": "gaming",
            "channel_type": "gaming_main",
            "target_format": "longform",
            "target_platforms": ["youtube"],
            "status": "created",
            "mode": "normal",
            "autopublish_class": "manual_only",
            "confidence_score": 0.0,
            "validator_status": "not_validated",
            "raw_video_path": "video.mp4",
        }
    )


def _base_good_file_info() -> FileInfo:
    return FileInfo(
        path="video.mp4",
        exists=True,
        extension=".mp4",
        size_bytes=4096,
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
        raw_ffprobe={
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
                    "tags": {"title": "Microphone"},
                },
            ]
        },
        probe_status="ok",
        probe_error=None,
    )


def _readable_result(path: str = "video.mp4") -> FileReadabilityResult:
    return FileReadabilityResult(
        readable=True,
        status="readable",
        severity="ok",
        file_path=path,
        checked_seconds=3.0,
        ffmpeg_returncode=0,
        stdout_tail="",
        stderr_tail="",
        warnings=[],
        errors=[],
        recommendation="accept",
        details={"size_bytes": 4096},
    )


def test_file_probe_acceptance_streams_and_readability_foundation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    fake_ffprobe = {
        "format": {
            "duration": "123.456",
            "format_name": "mov,mp4,m4a,3gp,3g2,mj2",
        },
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
        ],
    }

    file_info = parse_ffprobe_json("example.mp4", fake_ffprobe)
    file_info.exists = True
    file_info.size_bytes = 4096

    assert file_info.duration_seconds == 123.456
    assert file_info.video_stream_count == 1
    assert file_info.audio_stream_count == 2
    assert file_info.fps == 59.94

    acceptance = validate_file_info(file_info)
    assert acceptance.accepted is True
    assert acceptance.status == "accepted"

    stream_result = classify_file_streams(file_info)
    assert stream_result.primary_video_stream["role"] == "video_primary"
    assert len(stream_result.voice_audio_candidates) == 1
    assert len(stream_result.game_audio_candidates) == 1
    assert stream_result.needs_manual_review is False

    video_file = tmp_path / "readable.mp4"
    video_file.write_bytes(b"x" * 4096)

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=0,
            stdout="ok",
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)

    readability = check_file_readability(video_file, ffmpeg_path="fake_ffmpeg")
    assert readability.readable is True
    assert readability.status == "readable"
    assert readability.recommendation == "accept"


def test_file_acceptance_rejects_bad_inputs() -> None:
    unsupported = _base_good_file_info()
    unsupported.path = "notes.txt"
    unsupported.extension = ".txt"
    unsupported.is_supported_format = False

    unsupported_result = validate_file_info(unsupported)
    assert unsupported_result.accepted is False
    assert "unsupported_extension" in unsupported_result.errors

    no_video = _base_good_file_info()
    no_video.has_video = False
    no_video.video_stream_count = 0
    no_video.width = None
    no_video.height = None
    no_video.fps = None

    no_video_result = validate_file_info(no_video)
    assert no_video_result.accepted is False
    assert "no_video_stream" in no_video_result.errors

    no_audio = _base_good_file_info()
    no_audio.has_audio = False
    no_audio.audio_stream_count = 0

    no_audio_default = validate_file_info(no_audio)
    assert no_audio_default.accepted is True
    assert no_audio_default.status == "accepted_with_warnings"
    assert "no_audio_stream" in no_audio_default.warnings

    no_audio_required = validate_file_info(
        no_audio,
        profile={"profile_id": "gaming_main", "require_audio": True},
    )
    assert no_audio_required.accepted is False
    assert "no_audio_stream" in no_audio_required.errors


def test_file_readability_failure_modes(tmp_path: Path, monkeypatch) -> None:
    missing = check_file_readability(tmp_path / "missing.mp4")
    assert missing.readable is False
    assert "file_missing" in missing.errors

    empty_file = tmp_path / "empty.mp4"
    empty_file.write_bytes(b"")

    empty = check_file_readability(empty_file)
    assert empty.readable is False
    assert "empty_file" in empty.errors

    broken_file = tmp_path / "broken.mp4"
    broken_file.write_bytes(b"x" * 4096)

    def fake_failure(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args,
            returncode=1,
            stdout="",
            stderr="Invalid data found",
        )

    monkeypatch.setattr(subprocess, "run", fake_failure)

    failed = check_file_readability(broken_file, ffmpeg_path="fake_ffmpeg")
    assert failed.readable is False
    assert failed.status == "unreadable"
    assert "ffmpeg_decode_failed" in failed.errors
    assert "Invalid data found" in failed.stderr_tail

    def fake_exception(*args, **kwargs):
        raise RuntimeError("ffmpeg exploded")

    monkeypatch.setattr(subprocess, "run", fake_exception)

    exception_result = check_file_readability(broken_file, ffmpeg_path="fake_ffmpeg")
    assert exception_result.readable is False
    assert exception_result.status == "failed"
    assert "readability_check_failed" in exception_result.errors


def test_file_handler_report_and_job_roundtrip(monkeypatch) -> None:
    def fake_probe_file(path):
        return _base_good_file_info()

    def fake_readability(path, seconds=3.0):
        return _readable_result(str(path))

    monkeypatch.setattr(file_handler, "probe_file", fake_probe_file)
    monkeypatch.setattr(file_handler, "check_file_readability", fake_readability)

    report = file_handler.build_file_handler_report("video.mp4")

    assert report["accepted"] is True
    assert report["readable"] is True
    assert report["status"] == "accepted"
    assert report["recommendation"] == "accept"
    assert "file_info" in report
    assert "file_acceptance" in report
    assert "stream_classification" in report
    assert "file_readability" in report

    job = _job_from_dict()
    file_handler.apply_file_handler_report_to_job(job, report)

    restored = Job.from_dict(job.to_dict())

    assert restored.file_info["path"] == "video.mp4"
    assert restored.file_acceptance["accepted"] is True
    assert restored.stream_classification["stream_count"] == 2
    assert restored.file_readability["readable"] is True
    assert restored.file_handler_report["status"] == "accepted"

    gaming_pipeline_text = Path("core/gaming_pipeline.py").read_text(encoding="utf-8")
    for event_name in EXPECTED_FILE_HANDLER_EVENTS:
        assert event_name in gaming_pipeline_text


def test_file_handler_files_have_no_bom_and_end_with_newline() -> None:
    paths = [
        Path("models/file_info.py"),
        Path("core/file_probe.py"),
        Path("models/file_acceptance.py"),
        Path("core/file_acceptance.py"),
        Path("models/stream_info.py"),
        Path("core/stream_classifier.py"),
        Path("models/file_readability.py"),
        Path("core/file_readability.py"),
        Path("core/file_handler.py"),
        Path("tests/test_file_info_ffprobe_foundation_smoke.py"),
        Path("tests/test_file_acceptance_smoke.py"),
        Path("tests/test_stream_classifier_smoke.py"),
        Path("tests/test_file_readability_smoke.py"),
        Path("tests/test_file_handler_pipeline_integration_smoke.py"),
        Path("tests/test_file_handler_final_audit_smoke.py"),
    ]

    for path in paths:
        data = path.read_bytes()

        assert not data.startswith(b"\xef\xbb\xbf"), f"{path} has UTF-8 BOM"
        assert data.endswith(b"\n"), f"{path} must end with newline"
