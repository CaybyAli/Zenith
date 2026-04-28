"""
test_tiktok_uploader_smoke.py

Smoke-tests for TikTokUploader (core/tiktok_uploader.py) and the
TikTok branch in Publisher (core/publisher.py).

All network calls are mocked — no real API credentials required.

Tests:
  1. Successful upload flow (init → chunk PUT → status poll → video_id)
  2. Missing TIKTOK_ACCESS_TOKEN → ValidationError
  3. Video duration > 10 min → ValidationError
  4. Caption truncation at 150 chars
  5. Aspect ratio warning for non-9:16 video (no error, just a log)
  6. TikTok init API error → TikTokUploadError
  7. Status poll: PROCESSING → PUBLISH_COMPLETE → returns video_id
  8. Status poll timeout → TikTokUploadError
  9. Publisher routes tiktok backend → published PublishResult
 10. Publisher catches TikTokUploadError → failed PublishResult
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import unittest.mock as mock
from pathlib import Path
from types import SimpleNamespace

import pytest

from core.tiktok_uploader import (
    TikTokUploadError,
    TikTokUploader,
    _build_caption,
    _chunk_size_for,
)
from shared.errors import ValidationError


# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #

_FFMPEG = r"D:\Tools\ffmpeg\bin\ffmpeg.exe"


def _make_video(path: str, width: int = 608, height: int = 1080, duration: int = 3) -> None:
    """Tiny synthetic MP4 via ffmpeg lavfi."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    subprocess.run(
        [
            _FFMPEG, "-y",
            "-f", "lavfi", "-i",
            f"testsrc=size={width}x{height}:rate=10:duration={duration}",
            "-f", "lavfi", "-i",
            f"sine=frequency=440:sample_rate=44100:duration={duration}",
            "-c:v", "libx264", "-preset", "ultrafast",
            "-c:a", "aac",
            path,
        ],
        check=True,
        capture_output=True,
    )


def _fake_package(video_path: str, title: str = "Test Title", hashtags=None):
    return SimpleNamespace(
        video_path=video_path,
        title=title,
        hashtags=hashtags or ["ki", "trend", "viral"],
    )


def _mock_init_response(publish_id="pub_001", upload_url="https://upload.tiktok.example/v1"):
    body = {"data": {"publish_id": publish_id, "upload_url": upload_url}, "error": {"code": "ok"}}
    r = mock.MagicMock()
    r.json.return_value = body
    r.status_code = 200
    return r


def _mock_put_response(status_code=206):
    r = mock.MagicMock()
    r.status_code = status_code
    r.text = ""
    return r


def _mock_status_response(status="PUBLISH_COMPLETE", video_id="tt_video_123"):
    body = {
        "data": {
            "status": status,
            "publicaly_available_post_id": [video_id],
        },
        "error": {"code": "ok"},
    }
    r = mock.MagicMock()
    r.json.return_value = body
    r.status_code = 200
    return r


# ------------------------------------------------------------------ #
#  Unit tests — pure logic, no I/O                                     #
# ------------------------------------------------------------------ #

def test_build_caption_short():
    cap = _build_caption("Short Title", ["ki", "trend"])
    assert cap == "Short Title #ki #trend"
    assert len(cap) <= 150


def test_build_caption_truncates_to_150():
    long_title = "A" * 140
    tags = ["ki", "trend", "viral", "tech"]
    cap = _build_caption(long_title, tags)
    assert len(cap) <= 150


def test_build_caption_no_hashtags():
    cap = _build_caption("Just a title", [])
    assert cap == "Just a title"


def test_build_caption_adds_hash_prefix():
    cap = _build_caption("T", ["ki", "#trend"])
    assert "#ki" in cap
    assert "#trend" in cap
    # No double ##
    assert "##" not in cap


def test_chunk_size_small_file():
    small = 2 * 1024 * 1024  # 2 MB
    size = _chunk_size_for(small)
    assert size == 4 * 1024 * 1024  # clamped to 4 MB minimum


def test_chunk_size_large_file():
    large = 200 * 1024 * 1024  # 200 MB
    size = _chunk_size_for(large)
    assert size == 64 * 1024 * 1024  # capped at 64 MB


def test_chunk_size_mid_file():
    mid = 30 * 1024 * 1024  # 30 MB — within [4, 64]
    size = _chunk_size_for(mid)
    assert 4 * 1024 * 1024 <= size <= 64 * 1024 * 1024


# ------------------------------------------------------------------ #
#  Test 1 — successful upload flow                                     #
# ------------------------------------------------------------------ #

def test_successful_upload_flow():
    with tempfile.TemporaryDirectory() as tmp:
        video_path = os.path.join(tmp, "short.mp4")
        _make_video(video_path, width=608, height=1080, duration=3)

        pkg = _fake_package(video_path)

        with mock.patch.dict(os.environ, {"TIKTOK_ACCESS_TOKEN": "tok_test_123"}):
            with mock.patch("requests.post") as mock_post, \
                 mock.patch("requests.put") as mock_put:

                mock_post.side_effect = [
                    _mock_init_response(publish_id="pub_001"),
                    _mock_status_response(status="PUBLISH_COMPLETE", video_id="tt_xyz"),
                ]
                mock_put.return_value = _mock_put_response(status_code=200)

                video_id = TikTokUploader().upload(pkg)

    assert video_id == "tt_xyz"
    assert mock_post.call_count == 2  # init + status
    assert mock_put.call_count >= 1   # at least one chunk


# ------------------------------------------------------------------ #
#  Test 2 — missing token                                              #
# ------------------------------------------------------------------ #

def test_missing_token_raises():
    with tempfile.TemporaryDirectory() as tmp:
        video_path = os.path.join(tmp, "v.mp4")
        _make_video(video_path)
        pkg = _fake_package(video_path)

        env = {k: v for k, v in os.environ.items() if k != "TIKTOK_ACCESS_TOKEN"}
        with mock.patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValidationError, match="TIKTOK_ACCESS_TOKEN"):
                TikTokUploader().upload(pkg)


# ------------------------------------------------------------------ #
#  Test 3 — video too long                                             #
# ------------------------------------------------------------------ #

def test_video_too_long_raises():
    with tempfile.TemporaryDirectory() as tmp:
        video_path = os.path.join(tmp, "long.mp4")
        _make_video(video_path, duration=3)
        pkg = _fake_package(video_path)

        # Patch ffprobe to report 700 seconds
        with mock.patch.dict(os.environ, {"TIKTOK_ACCESS_TOKEN": "tok_test"}):
            with mock.patch("subprocess.run") as mock_run:
                mock_run.return_value = mock.MagicMock(
                    returncode=0, stdout="700.0\n", stderr=""
                )
                with pytest.raises(ValidationError, match="10-minute"):
                    TikTokUploader().upload(pkg)


# ------------------------------------------------------------------ #
#  Test 4 — caption truncation (functional, no I/O)                    #
# ------------------------------------------------------------------ #

def test_caption_150_char_limit():
    title = "B" * 200
    tags = ["x"]
    cap = _build_caption(title, tags)
    assert len(cap) == 150


# ------------------------------------------------------------------ #
#  Test 5 — non-9:16 aspect ratio logs a warning but does not raise    #
# ------------------------------------------------------------------ #

def test_non_vertical_ratio_warns_not_raises():
    with tempfile.TemporaryDirectory() as tmp:
        # Create a 16:9 video (landscape, not 9:16)
        video_path = os.path.join(tmp, "wide.mp4")
        _make_video(video_path, width=1920, height=1080, duration=3)
        pkg = _fake_package(video_path)

        with mock.patch.dict(os.environ, {"TIKTOK_ACCESS_TOKEN": "tok_test"}):
            with mock.patch("requests.post") as mock_post, \
                 mock.patch("requests.put") as mock_put:

                mock_post.side_effect = [
                    _mock_init_response(),
                    _mock_status_response(),
                ]
                mock_put.return_value = _mock_put_response(200)

                # Should NOT raise — only print a warning
                result = TikTokUploader().upload(pkg)

    assert result  # got back a video_id


# ------------------------------------------------------------------ #
#  Test 6 — TikTok init API error                                      #
# ------------------------------------------------------------------ #

def test_init_api_error_raises():
    with tempfile.TemporaryDirectory() as tmp:
        video_path = os.path.join(tmp, "v.mp4")
        _make_video(video_path)
        pkg = _fake_package(video_path)

        bad_response = mock.MagicMock()
        bad_response.json.return_value = {
            "error": {"code": "access_token_invalid", "message": "Invalid token", "log_id": "lg1"},
            "data": {},
        }
        bad_response.status_code = 401

        with mock.patch.dict(os.environ, {"TIKTOK_ACCESS_TOKEN": "bad_token"}):
            with mock.patch("requests.post", return_value=bad_response):
                with pytest.raises(TikTokUploadError, match="Invalid token"):
                    TikTokUploader().upload(pkg)


# ------------------------------------------------------------------ #
#  Test 7 — status poll: PROCESSING then PUBLISH_COMPLETE              #
# ------------------------------------------------------------------ #

def test_status_poll_processing_then_complete():
    with tempfile.TemporaryDirectory() as tmp:
        video_path = os.path.join(tmp, "v.mp4")
        _make_video(video_path)
        pkg = _fake_package(video_path)

        processing_resp = mock.MagicMock()
        processing_resp.json.return_value = {
            "data": {"status": "PROCESSING", "publicaly_available_post_id": []},
            "error": {"code": "ok"},
        }
        processing_resp.status_code = 200

        with mock.patch.dict(os.environ, {"TIKTOK_ACCESS_TOKEN": "tok_test"}):
            with mock.patch("requests.post") as mock_post, \
                 mock.patch("requests.put", return_value=_mock_put_response(200)):

                mock_post.side_effect = [
                    _mock_init_response(),        # call 1: init
                    processing_resp,              # call 2: first status poll
                    processing_resp,              # call 3: second status poll
                    _mock_status_response(        # call 4: COMPLETE
                        status="PUBLISH_COMPLETE", video_id="tt_final"
                    ),
                ]

                with mock.patch("time.sleep"):   # skip delays
                    video_id = TikTokUploader().upload(pkg)

    assert video_id == "tt_final"
    assert mock_post.call_count == 4


# ------------------------------------------------------------------ #
#  Test 8 — status poll timeout                                        #
# ------------------------------------------------------------------ #

def test_status_poll_timeout_raises():
    from core.tiktok_uploader import _STATUS_MAX_POLLS

    with tempfile.TemporaryDirectory() as tmp:
        video_path = os.path.join(tmp, "v.mp4")
        _make_video(video_path)
        pkg = _fake_package(video_path)

        processing_resp = mock.MagicMock()
        processing_resp.json.return_value = {
            "data": {"status": "PROCESSING", "publicaly_available_post_id": []},
            "error": {"code": "ok"},
        }
        processing_resp.status_code = 200

        # init + _STATUS_MAX_POLLS × PROCESSING
        side_effects = [_mock_init_response()] + [processing_resp] * _STATUS_MAX_POLLS

        with mock.patch.dict(os.environ, {"TIKTOK_ACCESS_TOKEN": "tok_test"}):
            with mock.patch("requests.post") as mock_post, \
                 mock.patch("requests.put", return_value=_mock_put_response(200)), \
                 mock.patch("time.sleep"):

                mock_post.side_effect = side_effects

                with pytest.raises(TikTokUploadError, match="timed out"):
                    TikTokUploader().upload(pkg)


# ------------------------------------------------------------------ #
#  Test 9 — Publisher routes tiktok backend → published               #
# ------------------------------------------------------------------ #

def _tiktok_package(job_id: str) -> "PublishPackage":
    from models.publish_package import PublishPackage
    from shared.enums import ChannelType, PlatformType, TargetFormat

    return PublishPackage(
        job_id=job_id,
        video_path="/fake/short.mp4",
        title="Test TikTok Video",
        description="desc",
        hashtags=["ki", "trend"],
        thumbnail_path=None,
        platform=PlatformType.TIKTOK,
        channel_type=ChannelType.FACELESS_TREND,
        target_format=TargetFormat.SHORT,
        requires_manual_approval=False,
        title_mode="standard",
        description_mode="standard",
        hashtags_mode="standard",
        subtitle_style="standard",
        packaging_profile="standard",
        length_profile="standard",
        preferred_aspect_ratio="9:16",
        thumbnail_required=False,
        uploader_backend="tiktok",
    )


def test_publisher_tiktok_backend_published():
    from core.publisher import Publisher
    from models.publish_decision import PublishDecision

    pkg = _tiktok_package("job_pub_tiktok_001")

    decision = PublishDecision(
        job_id=pkg.job_id,
        decision="autopublish_allowed",
        reason="test",
    )

    with mock.patch("core.tiktok_uploader.TikTokUploader.upload", return_value="tt_pub_id"):
        result = Publisher().publish(pkg, decision)

    assert result.publish_status == "published"
    assert result.platform_video_id == "tt_pub_id"
    assert result.backend_name == "tiktok"
    assert "tiktok.com" in (result.public_url or "")
    print(f"\n[PASS] test_publisher_tiktok_backend_published  url={result.public_url}")


# ------------------------------------------------------------------ #
#  Test 10 — Publisher catches TikTokUploadError → failed             #
# ------------------------------------------------------------------ #

def test_publisher_tiktok_upload_error_returns_failed():
    from core.publisher import Publisher
    from models.publish_decision import PublishDecision

    pkg = _tiktok_package("job_pub_tiktok_002")

    decision = PublishDecision(
        job_id=pkg.job_id,
        decision="autopublish_allowed",
        reason="test",
    )

    with mock.patch(
        "core.tiktok_uploader.TikTokUploader.upload",
        side_effect=TikTokUploadError("TikTok init failed: quota exceeded"),
    ):
        result = Publisher().publish(pkg, decision)

    assert result.publish_status == "failed"
    assert "quota exceeded" in (result.error_message or "")
    assert result.backend_name == "tiktok"
    print(f"\n[PASS] test_publisher_tiktok_upload_error_returns_failed  error={result.error_message}")


# ------------------------------------------------------------------ #
#  Entry point                                                         #
# ------------------------------------------------------------------ #

def main() -> None:
    test_build_caption_short()
    test_build_caption_truncates_to_150()
    test_build_caption_no_hashtags()
    test_build_caption_adds_hash_prefix()
    test_chunk_size_small_file()
    test_chunk_size_large_file()
    test_chunk_size_mid_file()

    test_successful_upload_flow()
    test_missing_token_raises()
    test_video_too_long_raises()
    test_caption_150_char_limit()
    test_non_vertical_ratio_warns_not_raises()
    test_init_api_error_raises()
    test_status_poll_processing_then_complete()
    test_status_poll_timeout_raises()
    test_publisher_tiktok_backend_published()
    test_publisher_tiktok_upload_error_returns_failed()

    print("\n=== ALL TIKTOK UPLOADER SMOKE TESTS PASSED ===")


if __name__ == "__main__":
    main()
