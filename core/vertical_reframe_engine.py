from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path

from shared.errors import ValidationError


# ------------------------------------------------------------------ #
#  Crop configurations for different focus regions                    #
#  All values normalised to source frame (0.0–1.0).                  #
#  The crop produces a 9:16 slice:                                    #
#    crop_w ≈ src_h × (9/16)  →  scaled to 1080×1920.               #
# ------------------------------------------------------------------ #

_CROP_CONFIGS: dict[str, dict[str, float]] = {
    # Facecam usually occupies the left third of a gaming layout
    "facecam": {"x": 0.025, "y": 0.0, "width": 0.317, "height": 1.0},
    # Action zone is typically centre-right
    "gameplay": {"x": 0.342, "y": 0.0, "width": 0.317, "height": 1.0},
    # Balanced / safe centre crop
    "balanced": {"x": 0.342, "y": 0.0, "width": 0.317, "height": 1.0},
    # Default centre
    "center": {"x": 0.342, "y": 0.0, "width": 0.317, "height": 1.0},
}

_FOCUS_KINDS = frozenset(_CROP_CONFIGS)


class VerticalReframeEngine:
    """
    Converts a 16:9 video segment to 9:16 (1080×1920) for Shorts / Reels.

    Smart crop strategy:
      - "facecam"  → left portion (facecam zone)
      - "gameplay" → centre/right (action zone)
      - "balanced" / "center" → dead centre
      - "auto"     → detects via per-frame brightness split (falls back to centre)

    Subtitle overlay:
      - Looks for a .srt file co-located with the source.
      - Also accepts a Whisper-output JSON (*_whisper.json / *_transcript.json)
        and converts it to a temp SRT on the fly.
      - No subtitle present → renders cleanly without error.

    Encoding: h264_nvenc -preset p4 -cq 23  (RTX NVENC).
    Output:   1080×1920 MP4.
    """

    OUTPUT_W = 1080
    OUTPUT_H = 1920
    _FFMPEG = r"D:\Tools\ffmpeg\bin\ffmpeg.exe"
    _FFPROBE = r"D:\Tools\ffmpeg\bin\ffprobe.exe"

    # ------------------------------------------------------------------ #
    #  Internals – dimensions                                              #
    # ------------------------------------------------------------------ #

    def _get_video_dimensions(self, source: Path) -> tuple[int, int]:
        cmd = [
            self._FFPROBE,
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=p=0",
            str(source),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split(",")
            if len(parts) >= 2:
                try:
                    return int(parts[0]), int(parts[1])
                except ValueError:
                    pass
        return 1920, 1080

    # ------------------------------------------------------------------ #
    #  Internals – focus detection                                         #
    # ------------------------------------------------------------------ #

    def _detect_focus_kind(self, source: Path, start_time: float) -> str:
        """
        Extract one frame at start_time and compare mean brightness of the
        left third vs the right third.  If they differ meaningfully we are
        looking at a facecam-on-left layout.  Otherwise fall back to centre.
        """
        try:
            with tempfile.TemporaryDirectory() as tmp:
                frame_path = Path(tmp) / "probe_frame.png"
                cmd = [
                    self._FFMPEG, "-y",
                    "-ss", str(round(start_time, 3)),
                    "-i", str(source),
                    "-frames:v", "1",
                    "-vf", "scale=96:54",   # thumbnail scale — fast
                    str(frame_path),
                ]
                r = subprocess.run(cmd, capture_output=True, text=True)
                if r.returncode != 0 or not frame_path.exists():
                    return "center"

                # Read raw pixels via ffprobe rawvideo pipe
                pipe_cmd = [
                    self._FFMPEG, "-y",
                    "-i", str(frame_path),
                    "-f", "rawvideo",
                    "-pix_fmt", "gray",
                    "pipe:1",
                ]
                pr = subprocess.run(pipe_cmd, capture_output=True)
                if pr.returncode != 0 or len(pr.stdout) < 96 * 54:
                    return "center"

                pixels = pr.stdout
                width, height = 96, 54
                third = width // 3

                left_sum = sum(pixels[r * width: r * width + third] for r in range(height))
                right_sum = sum(pixels[r * width + (width - third): r * width + width] for r in range(height))

                left_mean = left_sum / (third * height)
                right_mean = right_sum / (third * height)

                # A meaningful brightness difference → different content in each zone
                if abs(left_mean - right_mean) > 18:
                    return "facecam"
                return "center"
        except Exception:
            return "center"

    # ------------------------------------------------------------------ #
    #  Internals – crop filter                                             #
    # ------------------------------------------------------------------ #

    def _build_crop_filter(self, src_w: int, src_h: int, focus_kind: str) -> str:
        cfg = _CROP_CONFIGS.get(focus_kind, _CROP_CONFIGS["center"])

        x = round(src_w * cfg["x"])
        y = round(src_h * cfg["y"])
        w = round(src_w * cfg["width"])
        h = round(src_h * cfg["height"])

        # Even dimensions required by h264
        w = max(2, w - (w % 2))
        h = max(2, h - (h % 2))

        # Clamp to frame bounds
        x = max(0, min(x, src_w - w))
        y = max(0, min(y, src_h - h))

        return f"crop={w}:{h}:{x}:{y},scale={self.OUTPUT_W}:{self.OUTPUT_H}"

    # ------------------------------------------------------------------ #
    #  Internals – subtitle handling                                       #
    # ------------------------------------------------------------------ #

    def _find_subtitle_source(self, source: Path) -> Path | None:
        """Return the first subtitle file found alongside the source."""
        stem = source.stem
        parent = source.parent
        for candidate in [
            parent / f"{stem}.srt",
            parent / f"{stem}.vtt",
            parent / f"{stem}_whisper.json",
            parent / f"{stem}_transcript.json",
        ]:
            if candidate.exists():
                return candidate
        return None

    @staticmethod
    def _seconds_to_srt_timestamp(t: float) -> str:
        t = max(0.0, t)
        h = int(t // 3600)
        m = int((t % 3600) // 60)
        s = int(t % 60)
        ms = int(round((t % 1) * 1000))
        return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

    def _whisper_json_to_srt(
        self,
        json_path: Path,
        start_offset: float,
        duration: float,
        tmp_dir: Path,
    ) -> Path | None:
        try:
            with open(json_path, encoding="utf-8") as f:
                data = json.load(f)
            segments = data.get("segments", [])
        except Exception:
            return None

        end_offset = start_offset + duration
        srt_lines: list[str] = []
        idx = 1

        for seg in segments:
            s = float(seg.get("start", 0.0))
            e = float(seg.get("end", 0.0))
            text = str(seg.get("text", "")).strip()

            if not text or e <= start_offset or s >= end_offset:
                continue

            # Shift timestamps relative to the extracted segment
            s_rel = max(0.0, s - start_offset)
            e_rel = min(duration, e - start_offset)
            if e_rel <= s_rel:
                continue

            srt_lines += [
                str(idx),
                f"{self._seconds_to_srt_timestamp(s_rel)} --> {self._seconds_to_srt_timestamp(e_rel)}",
                text,
                "",
            ]
            idx += 1

        if not srt_lines:
            return None

        out = tmp_dir / "subtitles.srt"
        out.write_text("\n".join(srt_lines), encoding="utf-8")
        return out

    def _srt_trim_and_shift(
        self,
        srt_path: Path,
        start_offset: float,
        duration: float,
        tmp_dir: Path,
    ) -> Path | None:
        """Read an existing SRT, keep only lines within the segment and shift timestamps."""
        try:
            raw = srt_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None

        end_offset = start_offset + duration

        # Minimal SRT parser
        _TS_RE = re.compile(
            r"(\d+:\d+:\d+[,\.]\d+)\s*-->\s*(\d+:\d+:\d+[,\.]\d+)"
        )

        def _ts_to_sec(ts: str) -> float:
            ts = ts.replace(",", ".")
            parts = ts.split(":")
            h, m, rest = int(parts[0]), int(parts[1]), float(parts[2])
            return h * 3600 + m * 60 + rest

        blocks = raw.strip().split("\n\n")
        out_blocks: list[str] = []
        new_idx = 1

        for block in blocks:
            lines = block.strip().splitlines()
            ts_line = next((l for l in lines if "-->" in l), None)
            if ts_line is None:
                continue
            m = _TS_RE.search(ts_line)
            if not m:
                continue

            s = _ts_to_sec(m.group(1))
            e = _ts_to_sec(m.group(2))

            if e <= start_offset or s >= end_offset:
                continue

            s_rel = max(0.0, s - start_offset)
            e_rel = min(duration, e - start_offset)
            if e_rel <= s_rel:
                continue

            text_lines = [l for l in lines if "-->" not in l and not l.strip().isdigit()]
            text = "\n".join(text_lines).strip()
            if not text:
                continue

            out_blocks.append(
                f"{new_idx}\n"
                f"{self._seconds_to_srt_timestamp(s_rel)} --> {self._seconds_to_srt_timestamp(e_rel)}\n"
                f"{text}"
            )
            new_idx += 1

        if not out_blocks:
            return None

        out = tmp_dir / "subtitles.srt"
        out.write_text("\n\n".join(out_blocks), encoding="utf-8")
        return out

    def _prepare_subtitle(
        self,
        subtitle_source: Path | None,
        start_time: float,
        duration: float,
        tmp_dir: Path,
    ) -> Path | None:
        if subtitle_source is None:
            return None

        if subtitle_source.suffix.lower() in (".json",):
            return self._whisper_json_to_srt(
                subtitle_source, start_time, duration, tmp_dir
            )

        if subtitle_source.suffix.lower() in (".srt", ".vtt"):
            return self._srt_trim_and_shift(
                subtitle_source, start_time, duration, tmp_dir
            )

        return None

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def reframe(
        self,
        source_path: str | Path,
        start_time: float,
        duration: float,
        output_path: str | Path,
        *,
        focus_kind: str = "auto",
        subtitle_path: str | Path | None = "auto",
    ) -> str:
        """
        Reframe a segment of *source_path* to 9:16 (1080×1920) and write to
        *output_path*.

        Parameters
        ----------
        source_path:
            Source 16:9 video.
        start_time:
            Segment start in seconds (absolute, within source).
        duration:
            Segment length in seconds.
        output_path:
            Destination MP4.
        focus_kind:
            "facecam" | "gameplay" | "balanced" | "center" | "auto".
            "auto" tries brightness-based detection, falls back to "center".
        subtitle_path:
            Explicit path to a .srt / .vtt / _whisper.json file.
            Pass "auto" (default) to search next to *source_path*.
            Pass None to disable subtitles entirely.

        Returns
        -------
        str  path to the rendered output file.
        """
        source = Path(source_path)
        if not source.exists():
            raise ValidationError(f"Source video not found: {source}")

        if duration <= 0:
            raise ValidationError(f"Duration must be positive, got {duration}")

        resolved_focus = focus_kind
        if resolved_focus == "auto":
            resolved_focus = self._detect_focus_kind(source, start_time)

        if resolved_focus not in _FOCUS_KINDS:
            resolved_focus = "center"

        src_w, src_h = self._get_video_dimensions(source)
        crop_filter = self._build_crop_filter(src_w, src_h, resolved_focus)

        with tempfile.TemporaryDirectory() as tmp_str:
            tmp_dir = Path(tmp_str)

            # --- Subtitle resolution ---
            sub_file: Path | None = None
            if subtitle_path == "auto":
                sub_file = self._prepare_subtitle(
                    self._find_subtitle_source(source),
                    start_time,
                    duration,
                    tmp_dir,
                )
            elif subtitle_path is not None:
                sub_file = self._prepare_subtitle(
                    Path(subtitle_path),
                    start_time,
                    duration,
                    tmp_dir,
                )
            # subtitle_path is None → sub_file stays None, no overlay

            # --- Build vf chain ---
            vf_parts = [crop_filter]
            if sub_file is not None:
                # Escape backslashes and colons for FFmpeg filter syntax
                srt_escaped = str(sub_file).replace("\\", "/").replace(":", "\\:")
                vf_parts.append(
                    f"subtitles='{srt_escaped}'"
                    ":force_style='FontSize=14,PrimaryColour=&H00FFFFFF,"
                    "OutlineColour=&H00000000,Outline=1,Shadow=0,"
                    "Alignment=2,MarginV=20'"
                )

            vf = ",".join(vf_parts)

            # --- FFmpeg command ---
            cmd = [
                self._FFMPEG, "-y",
                "-ss", str(round(start_time, 3)),
                "-t", str(round(duration, 3)),
                "-i", str(source),
                "-vf", vf,
                "-c:v", "h264_nvenc",
                "-preset", "p4",
                "-cq", "23",
                "-c:a", "aac",
                "-b:a", "192k",
                str(output_path),
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise ValidationError(
                f"Vertical reframe failed "
                f"[focus={resolved_focus} sub={'yes' if sub_file else 'no'}]: "
                f"{result.stderr[-800:]}"
            )

        return str(output_path)
