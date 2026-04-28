"""
core/tiktok_uploader.py

TikTok Content Posting API v2 — server-side direct-post uploader.

Authentication
--------------
Set the environment variable TIKTOK_ACCESS_TOKEN before calling upload().
Optionally TIKTOK_CLIENT_KEY for future OAuth refresh flows.

API flow (per TikTok docs)
--------------------------
  1. POST /v2/post/publish/video/init/
       → publish_id  +  upload_url
  2. PUT  {upload_url}  (chunked, Content-Range)
       → 206 per chunk, 200 on final chunk
  3. POST /v2/post/publish/status/fetch/   (poll until PUBLISH_COMPLETE)
       → publicaly_available_post_id  (note: TikTok's own typo)

Platform constraints
--------------------
  • Caption: max 150 characters (title + hashtags combined)
  • Video:   max 10 minutes (600 s)
  • Format:  9:16 strongly preferred; we log a warning for other ratios
  • Chunks:  4 MB minimum, 64 MB maximum; single chunk for small files
"""
from __future__ import annotations

import math
import os
import subprocess
import time
from pathlib import Path

import requests

from shared.errors import ValidationError, ZenithError


# ------------------------------------------------------------------ #
#  Custom error                                                        #
# ------------------------------------------------------------------ #

class TikTokUploadError(ZenithError):
    """Raised when the TikTok API returns a non-ok error code."""


# ------------------------------------------------------------------ #
#  Constants                                                           #
# ------------------------------------------------------------------ #

_API_BASE          = "https://open.tiktokapis.com/v2"
_INIT_URL          = f"{_API_BASE}/post/publish/video/init/"
_STATUS_URL        = f"{_API_BASE}/post/publish/status/fetch/"
_MAX_CAPTION_LEN   = 150
_MAX_DURATION_SEC  = 600           # 10 minutes
_MIN_CHUNK_BYTES   = 4  * 1024 * 1024   #  4 MB
_MAX_CHUNK_BYTES   = 64 * 1024 * 1024   # 64 MB
_STATUS_POLL_DELAY = 5.0           # seconds between status polls
_STATUS_MAX_POLLS  = 60            # 60 × 5 s = 5 min timeout
_FFPROBE           = r"D:\Tools\ffmpeg\bin\ffprobe.exe"


# ------------------------------------------------------------------ #
#  Helpers                                                             #
# ------------------------------------------------------------------ #

def _get_video_duration(video_path: Path) -> float:
    """Return video duration in seconds via ffprobe."""
    cmd = [
        _FFPROBE, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0 or not result.stdout.strip():
        raise ValidationError(f"ffprobe could not read duration: {video_path}")
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise ValidationError(f"ffprobe returned non-numeric duration: {result.stdout!r}") from exc


def _get_video_dimensions(video_path: Path) -> tuple[int, int]:
    """Return (width, height) via ffprobe."""
    cmd = [
        _FFPROBE, "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0",
        str(video_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0 and result.stdout.strip():
        parts = result.stdout.strip().split(",")
        if len(parts) >= 2:
            try:
                return int(parts[0]), int(parts[1])
            except ValueError:
                pass
    return 0, 0


def _build_caption(title: str, hashtags: list[str]) -> str:
    """
    Combine title + hashtags into a TikTok caption ≤ 150 characters.
    Hashtags are normalised (leading # added if missing).
    """
    tags = [f"#{t.lstrip('#')}" for t in hashtags if t.strip()]
    tag_str = " ".join(tags)

    if tag_str:
        candidate = f"{title} {tag_str}"
        if len(candidate) <= _MAX_CAPTION_LEN:
            return candidate
        # Truncate title to make room for tags
        room = _MAX_CAPTION_LEN - len(tag_str) - 1
        if room >= 5:
            return f"{title[:room].rstrip()} {tag_str}"
        # No room for tags — just truncate the whole thing
        return candidate[:_MAX_CAPTION_LEN]

    return title[:_MAX_CAPTION_LEN]


def _chunk_size_for(video_size: int) -> int:
    """Choose a chunk size within [4 MB, 64 MB] that fits the file cleanly."""
    if video_size <= _MAX_CHUNK_BYTES:
        return max(_MIN_CHUNK_BYTES, video_size)
    return _MAX_CHUNK_BYTES


# ------------------------------------------------------------------ #
#  Uploader                                                            #
# ------------------------------------------------------------------ #

class TikTokUploader:
    """
    Uploads a video to TikTok via the Content Posting API v2.

    Usage
    -----
    uploader = TikTokUploader()        # reads token from env
    video_id = uploader.upload(package)
    """

    def __init__(
        self,
        access_token: str | None = None,
        client_key: str | None = None,
    ) -> None:
        self.access_token = (
            access_token or os.environ.get("TIKTOK_ACCESS_TOKEN", "")
        ).strip()
        self.client_key = (
            client_key or os.environ.get("TIKTOK_CLIENT_KEY", "")
        ).strip()

    # ---------------------------------------------------------------- #
    #  Internal helpers                                                  #
    # ---------------------------------------------------------------- #

    def _require_token(self) -> None:
        if not self.access_token:
            raise ValidationError(
                "TIKTOK_ACCESS_TOKEN is not set. "
                "Export the token before calling TikTokUploader."
            )

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json; charset=UTF-8",
        }

    # ---------------------------------------------------------------- #
    #  Step 1 – initialise upload                                        #
    # ---------------------------------------------------------------- #

    def _init_upload(
        self,
        *,
        caption: str,
        video_size: int,
        chunk_size: int,
        chunk_count: int,
    ) -> dict[str, str]:
        """
        Call /v2/post/publish/video/init/ and return
        {"publish_id": ..., "upload_url": ...}.
        """
        payload = {
            "post_info": {
                "title": caption,
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
                "video_cover_timestamp_ms": 1000,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": video_size,
                "chunk_size": chunk_size,
                "total_chunk_count": chunk_count,
            },
        }

        resp = requests.post(
            _INIT_URL,
            headers=self._auth_headers(),
            json=payload,
            timeout=30,
        )

        body = resp.json()
        err = body.get("error", {})
        if err.get("code", "ok") != "ok":
            raise TikTokUploadError(
                f"TikTok init failed (HTTP {resp.status_code}): "
                f"{err.get('message', 'unknown error')} "
                f"[log_id={err.get('log_id', '')}]"
            )

        data = body.get("data", {})
        if not data.get("publish_id") or not data.get("upload_url"):
            raise TikTokUploadError(
                f"TikTok init response missing publish_id or upload_url: {body}"
            )

        return {
            "publish_id": str(data["publish_id"]),
            "upload_url": str(data["upload_url"]),
        }

    # ---------------------------------------------------------------- #
    #  Step 2 – chunked PUT upload                                       #
    # ---------------------------------------------------------------- #

    def _upload_chunks(
        self,
        upload_url: str,
        video_path: Path,
        chunk_size: int,
    ) -> None:
        """
        Upload the video file to TikTok's pre-signed URL in chunks.
        TikTok expects Content-Range: bytes {start}-{end}/{total}.
        """
        total = video_path.stat().st_size
        offset = 0

        with open(video_path, "rb") as fh:
            chunk_index = 0
            while offset < total:
                chunk = fh.read(chunk_size)
                if not chunk:
                    break

                end = offset + len(chunk) - 1
                headers = {
                    "Content-Range": f"bytes {offset}-{end}/{total}",
                    "Content-Length": str(len(chunk)),
                    "Content-Type": "video/mp4",
                }

                resp = requests.put(
                    upload_url,
                    headers=headers,
                    data=chunk,
                    timeout=300,
                )

                # TikTok returns 206 for intermediate chunks, 200 for the last
                if resp.status_code not in (200, 201, 206):
                    raise TikTokUploadError(
                        f"TikTok chunk {chunk_index} upload failed: "
                        f"HTTP {resp.status_code} — {resp.text[:200]}"
                    )

                offset += len(chunk)
                chunk_index += 1

                print(
                    f"[TikTokUploader] Chunk {chunk_index} uploaded "
                    f"({offset}/{total} bytes, {int(offset / total * 100)} %)"
                )

    # ---------------------------------------------------------------- #
    #  Step 3 – poll publish status                                      #
    # ---------------------------------------------------------------- #

    def _poll_status(self, publish_id: str) -> str:
        """
        Poll /v2/post/publish/status/fetch/ until PUBLISH_COMPLETE.
        Returns the TikTok video ID (from publicaly_available_post_id).
        Raises TikTokUploadError on FAILED or timeout.
        """
        for attempt in range(_STATUS_MAX_POLLS):
            resp = requests.post(
                _STATUS_URL,
                headers=self._auth_headers(),
                json={"publish_id": publish_id},
                timeout=30,
            )
            body = resp.json()
            err = body.get("error", {})
            if err.get("code", "ok") != "ok":
                raise TikTokUploadError(
                    f"TikTok status check failed: {err.get('message', 'unknown')} "
                    f"[log_id={err.get('log_id', '')}]"
                )

            data = body.get("data", {})
            status = data.get("status", "")

            if status == "PUBLISH_COMPLETE":
                # Note: TikTok spells this field with a typo ("publicaly")
                ids = data.get("publicaly_available_post_id", [])
                video_id = ids[0] if ids else publish_id
                print(
                    f"[TikTokUploader] Published successfully. "
                    f"video_id={video_id}  publish_id={publish_id}"
                )
                return str(video_id)

            if status == "FAILED":
                fail_reason = data.get("fail_reason", "unknown")
                raise TikTokUploadError(
                    f"TikTok publish failed: {fail_reason}  publish_id={publish_id}"
                )

            print(
                f"[TikTokUploader] Status={status!r} (attempt {attempt + 1}/"
                f"{_STATUS_MAX_POLLS}) — waiting {_STATUS_POLL_DELAY:.0f} s …"
            )
            time.sleep(_STATUS_POLL_DELAY)

        raise TikTokUploadError(
            f"TikTok publish timed out after "
            f"{_STATUS_MAX_POLLS * _STATUS_POLL_DELAY:.0f} s  "
            f"publish_id={publish_id}"
        )

    # ---------------------------------------------------------------- #
    #  Pre-flight validation                                             #
    # ---------------------------------------------------------------- #

    def _validate(self, video_path: Path) -> None:
        if not video_path.exists():
            raise ValidationError(f"TikTok upload: video file not found: {video_path}")

        duration = _get_video_duration(video_path)
        if duration > _MAX_DURATION_SEC:
            raise ValidationError(
                f"TikTok upload: video is {duration:.1f} s, "
                f"exceeds the 10-minute limit ({_MAX_DURATION_SEC} s). "
                f"Use a shorter clip or a Shorts segment."
            )

        w, h = _get_video_dimensions(video_path)
        if w > 0 and h > 0:
            ratio = w / h
            # 9:16 ≈ 0.5625 — allow ±10 % tolerance
            if not (0.50 <= ratio <= 0.62):
                print(
                    f"[TikTokUploader] WARNING: video aspect ratio is {w}×{h} "
                    f"({ratio:.3f}), which is not 9:16. "
                    "TikTok recommends vertical (9:16) for best reach. "
                    "Consider using a vertical_reframe_engine output."
                )

    # ---------------------------------------------------------------- #
    #  Public API                                                        #
    # ---------------------------------------------------------------- #

    def upload(self, package) -> str:
        """
        Upload *package.video_path* to TikTok and return the TikTok video ID.

        *package* must expose:
          .video_path    str | Path
          .title         str
          .hashtags      list[str]

        Raises
        ------
        ValidationError       on missing token, missing file, or duration > 10 min
        TikTokUploadError     on API errors during init, upload, or status polling
        """
        self._require_token()

        video_path = Path(package.video_path)
        self._validate(video_path)

        caption = _build_caption(package.title, list(package.hashtags))

        video_size = video_path.stat().st_size
        chunk_size = _chunk_size_for(video_size)
        chunk_count = math.ceil(video_size / chunk_size)

        print(
            f"[TikTokUploader] Starting upload: {video_path.name}  "
            f"size={video_size} B  chunks={chunk_count}  "
            f"caption={caption!r}"
        )

        init = self._init_upload(
            caption=caption,
            video_size=video_size,
            chunk_size=chunk_size,
            chunk_count=chunk_count,
        )
        publish_id = init["publish_id"]
        upload_url = init["upload_url"]

        print(f"[TikTokUploader] Init OK. publish_id={publish_id}")

        self._upload_chunks(upload_url, video_path, chunk_size)

        print(f"[TikTokUploader] Upload complete. Polling status …")
        return self._poll_status(publish_id)
