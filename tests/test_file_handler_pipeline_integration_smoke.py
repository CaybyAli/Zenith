from __future__ import annotations

from pathlib import Path

import core.file_handler as file_handler
from models.file_info import FileInfo
from models.file_readability import FileReadabilityResult
from models.job import Job


def _good_file_info() -> FileInfo:
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


def _job_from_dict() -> Job:
    return Job.from_dict(
        {
            "job_id": "job_file_handler_test",
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


def test_file_handler_report_good_file_with_monkeypatch(monkeypatch) -> None:
    def fake_probe_file(path):
        return _good_file_info()

    def fake_readability(path, seconds=3.0):
        return _readable_result(str(path))

    monkeypatch.setattr(file_handler, "probe_file", fake_probe_file)
    monkeypatch.setattr(file_handler, "check_file_readability", fake_readability)

    report = file_handler.build_file_handler_report("video.mp4")

    assert report["accepted"] is True
    assert report["readable"] is True
    assert report["status"] == "accepted"
    assert report["recommendation"] == "accept"
    assert report["file_info"]["path"] == "video.mp4"
    assert report["file_acceptance"]["accepted"] is True
    assert report["stream_classification"]["stream_count"] == 2
    assert report["file_readability"]["readable"] is True


def test_file_handler_report_rejected_file_skips_readability(monkeypatch) -> None:
    rejected_info = _good_file_info()
    rejected_info.extension = ".txt"
    rejected_info.is_supported_format = False
    rejected_info.has_video = False
    rejected_info.video_stream_count = 0

    def fake_probe_file(path):
        return rejected_info

    def fake_readability(path, seconds=3.0):
        raise AssertionError("readability should not run for rejected files")

    monkeypatch.setattr(file_handler, "probe_file", fake_probe_file)
    monkeypatch.setattr(file_handler, "check_file_readability", fake_readability)

    report = file_handler.build_file_handler_report("notes.txt")

    assert report["accepted"] is False
    assert report["readable"] is False
    assert report["status"] == "rejected"
    assert "unsupported_extension" in report["errors"]
    assert "no_video_stream" in report["errors"]
    assert report["file_readability"] == {}


def test_apply_file_handler_report_to_job_sets_fields() -> None:
    job = _job_from_dict()
    report = {
        "file_info": {"path": "video.mp4"},
        "file_acceptance": {"accepted": True},
        "stream_classification": {"stream_count": 2},
        "file_readability": {"readable": True},
        "accepted": True,
        "readable": True,
        "needs_manual_review": False,
        "status": "accepted",
        "warnings": [],
        "errors": [],
        "recommendation": "accept",
    }

    file_handler.apply_file_handler_report_to_job(job, report)

    assert job.file_info["path"] == "video.mp4"
    assert job.file_acceptance["accepted"] is True
    assert job.stream_classification["stream_count"] == 2
    assert job.file_readability["readable"] is True
    assert job.file_handler_report["status"] == "accepted"


def test_job_to_dict_from_dict_preserves_file_handler_fields() -> None:
    job = _job_from_dict()
    job.file_info = {"path": "video.mp4"}
    job.file_acceptance = {"accepted": True}
    job.stream_classification = {"stream_count": 2}
    job.file_readability = {"readable": True}
    job.file_handler_report = {"status": "accepted"}

    data = job.to_dict()
    restored = Job.from_dict(data)

    assert restored.file_info == {"path": "video.mp4"}
    assert restored.file_acceptance == {"accepted": True}
    assert restored.stream_classification == {"stream_count": 2}
    assert restored.file_readability == {"readable": True}
    assert restored.file_handler_report == {"status": "accepted"}


def test_file_handler_files_have_no_bom_and_end_with_newline() -> None:
    paths = [
        Path("core/file_handler.py"),
        Path("tests/test_file_handler_pipeline_integration_smoke.py"),
    ]

    for path in paths:
        data = path.read_bytes()

        assert not data.startswith(b"\xef\xbb\xbf"), f"{path} has UTF-8 BOM"
        assert data.endswith(b"\n"), f"{path} must end with newline"
