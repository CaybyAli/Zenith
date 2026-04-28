# patch_render_driver_v2.py
from pathlib import Path

file = Path(r"D:\Zenith\core\final_render_driver.py")
content = file.read_text(encoding="utf-8")

# ── PATCH 1: 32:9 → 16:9 mit Facecam PIP ──────────────────────────────────
old_extract = '''    def _extract_segment(
        self,
        source: Path,
        segment: TimelineSegment,
        vf: str,
        temp_path: Path,
    ) -> None:
        duration = round(segment.duration, 3)
        if duration <= 0:
            raise ValidationError(
                f"Segment {segment.segment_id} ({segment.segment_role}) "
                f"has non-positive duration: {duration}s"
            )


        cmd = [
            self._FFMPEG, "-y",
            "-ss", str(round(segment.start_time, 3)),
            "-t", str(duration),
            "-i", str(source),
            "-vf", vf,
            "-pix_fmt", "yuv420p", "-c:v", "h264_nvenc",
            "-preset", "p4",
            "-cq", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-reset_timestamps", "1",
            str(temp_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise ValidationError(
                f"Segment extract failed [{segment.segment_role} "
                f"{segment.start_time:.1f}s-{segment.end_time:.1f}s]: "
                f"{result.stderr[-800:]}"
            )'''

new_extract = '''    def _is_ultrawide(self, w: int, h: int) -> bool:
        """True wenn Quelle breiter als 16:9 ist (z.B. 32:9 OBS-Split-Recording)."""
        return h > 0 and (w / h) > 2.0

    def _extract_segment(
        self,
        source: Path,
        segment: TimelineSegment,
        vf: str,
        temp_path: Path,
        src_w: int = 1920,
        src_h: int = 1080,
    ) -> None:
        duration = round(segment.duration, 3)
        if duration <= 0:
            raise ValidationError(
                f"Segment {segment.segment_id} ({segment.segment_role}) "
                f"has non-positive duration: {duration}s"
            )

        if self._is_ultrawide(src_w, src_h):
            # 32:9 Quelle: linke Hälfte = Facecam, rechte Hälfte = Game
            half_w = src_w // 2
            # Facecam als PIP: 25% Breite, unten-links mit 10px Rand
            cam_w = 480
            cam_h = 270
            filter_complex = (
                f"[0:v]crop={half_w}:{src_h}:{half_w}:0,scale=1920:1080{(',' + vf) if vf and 'scale' not in vf else ''}[game];"
                f"[0:v]crop={half_w}:{src_h}:0:0,scale={cam_w}:{cam_h}[cam];"
                f"[game][cam]overlay=10:H-h-10[v]"
            )
            cmd = [
                self._FFMPEG, "-y",
                "-ss", str(round(segment.start_time, 3)),
                "-t", str(duration),
                "-i", str(source),
                "-filter_complex", filter_complex,
                "-map", "[v]",
                "-map", "0:a",
                "-pix_fmt", "yuv420p", "-c:v", "h264_nvenc",
                "-preset", "p4",
                "-cq", "23",
                "-c:a", "aac",
                "-b:a", "192k",
                "-reset_timestamps", "1",
                str(temp_path),
            ]
        else:
            cmd = [
                self._FFMPEG, "-y",
                "-ss", str(round(segment.start_time, 3)),
                "-t", str(duration),
                "-i", str(source),
                "-vf", vf,
                "-pix_fmt", "yuv420p", "-c:v", "h264_nvenc",
                "-preset", "p4",
                "-cq", "23",
                "-c:a", "aac",
                "-b:a", "192k",
                "-reset_timestamps", "1",
                str(temp_path),
            ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise ValidationError(
                f"Segment extract failed [{segment.segment_role} "
                f"{segment.start_time:.1f}s-{segment.end_time:.1f}s]: "
                f"{result.stderr[-800:]}"
            )'''

# ── PATCH 2: Clip-Deduplizierung ───────────────────────────────────────────
old_segments = '''        segments = sorted(
            edit_timeline.selected_segments,
            key=lambda s: s.start_time,
        )
        if not segments:
            raise ValidationError(
                f"EditTimeline {edit_timeline.timeline_id} has no selected segments"
            )'''

new_segments = '''        raw_segments = sorted(
            edit_timeline.selected_segments,
            key=lambda s: s.start_time,
        )
        if not raw_segments:
            raise ValidationError(
                f"EditTimeline {edit_timeline.timeline_id} has no selected segments"
            )

        # Deduplizierung: Segmente mit überlappenden Zeitbereichen überspringen
        segments: list = []
        for seg in raw_segments:
            overlap = any(
                not (seg.end_time <= used.start_time or seg.start_time >= used.end_time)
                for used in segments
            )
            if not overlap:
                segments.append(seg)'''

# ── PATCH 3: src_w/src_h an _extract_segment weitergeben ──────────────────
old_call = '''                self._extract_segment(source, seg, vf, tmp_path)'''
new_call  = '''                self._extract_segment(source, seg, vf, tmp_path, src_w=src_w, src_h=src_h)'''

applied = []

if old_extract in content:
    content = content.replace(old_extract, new_extract)
    applied.append("PATCH 1 (32:9 PIP Layout)")
else:
    print("PATCH 1 NICHT GEFUNDEN - prüfe manuell")

if old_segments in content:
    content = content.replace(old_segments, new_segments)
    applied.append("PATCH 2 (Clip-Deduplizierung)")
else:
    print("PATCH 2 NICHT GEFUNDEN - prüfe manuell")

if old_call in content:
    content = content.replace(old_call, new_call)
    applied.append("PATCH 3 (src_w/src_h Weitergabe)")
else:
    print("PATCH 3 NICHT GEFUNDEN - prüfe manuell")

file.write_text(content, encoding="utf-8")
print("Angewendete Patches:", ", ".join(applied))