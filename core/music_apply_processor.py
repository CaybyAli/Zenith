from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

from core.music_apply_timeline_resolver import MusicApplyTimelineResolver
from models.music_application_plan import MusicApplicationPlan
from models.music_apply_timeline import MusicApplyTimeline
from shared.errors import ValidationError


class MusicApplyProcessor:
    def _build_resolver_job(self, *, job_id: str, channel_type: str):
        return SimpleNamespace(
            job_id=job_id,
            channel_type=SimpleNamespace(value=channel_type),
        )

    def _resolve_timeline_fallback(
        self,
        *,
        music_application_plan: MusicApplicationPlan | None,
        channel_type: str,
    ) -> MusicApplyTimeline | None:
        if music_application_plan is None:
            return None

        resolver_job = self._build_resolver_job(
            job_id=music_application_plan.job_id,
            channel_type=channel_type,
        )

        return MusicApplyTimelineResolver().build(
            job=resolver_job,
            music_application_plan=music_application_plan,
        )

    def _split_available_segments(
        self,
        timeline: MusicApplyTimeline | None,
    ) -> tuple[list, list]:
        if timeline is None:
            return [], []

        available_segments = []
        missing_segments = []

        for segment in timeline.segments:
            music_path = Path(segment.source_file_path)
            if music_path.exists():
                available_segments.append(segment)
            else:
                missing_segments.append(segment)

        return available_segments, missing_segments

    def _build_filter_complex(self, segments: list) -> str:
        filter_parts: list[str] = []
        mix_inputs: list[str] = ["[0:a]"]

        for index, segment in enumerate(segments, start=1):
            duration = round(
                max(0.1, float(segment.music_offset_end) - float(segment.music_offset_start)),
                3,
            )
            delay_ms = max(0, int(round(float(segment.video_start_time) * 1000)))
            music_level = max(0.0, min(1.0, float(segment.music_level)))
            fade_in = max(0.0, min(float(segment.fade_in_seconds), duration))
            fade_out = max(0.0, min(float(segment.fade_out_seconds), duration))
            fade_out_start = max(0.0, duration - fade_out)

            chain = [
                f"[{index}:a]atrim=start={round(float(segment.music_offset_start), 3)}:end={round(float(segment.music_offset_end), 3)}",
                "asetpts=PTS-STARTPTS",
            ]

            if fade_in > 0:
                chain.append(f"afade=t=in:st=0:d={round(fade_in, 3)}")

            if fade_out > 0:
                chain.append(
                    f"afade=t=out:st={round(fade_out_start, 3)}:d={round(fade_out, 3)}"
                )

            chain.append(f"volume={round(music_level, 3)}")
            chain.append(f"adelay={delay_ms}|{delay_ms}")

            label = f"music_{index}"
            filter_parts.append(",".join(chain) + f"[{label}]")
            mix_inputs.append(f"[{label}]")

        mix_part = (
            "".join(mix_inputs)
            + f"amix=inputs={len(mix_inputs)}:duration=first:dropout_transition=0[mixed]"
        )

        return ";".join(filter_parts + [mix_part])

    def apply(
        self,
        *,
        rendered_video_path: str,
        music_application_plan: MusicApplicationPlan | None,
        channel_type: str,
        music_apply_timeline: MusicApplyTimeline | None = None,
    ) -> dict[str, object]:
        video_path = Path(rendered_video_path)

        if not video_path.exists():
            raise ValidationError(f"Rendered video not found: {rendered_video_path}")

        context_path = video_path.with_name(f"{video_path.stem}_music_apply_context.json")

        if channel_type != "gaming_main":
            payload = {
                "music_applied": False,
                "reason": "channel_not_enabled",
                "output_video_path": str(video_path),
                "music_apply_timeline_used": False,
                "music_apply_segment_count": 0,
                "applied_music_segment_count": 0,
                "music_application_asset_ids": [],
            }
            with open(context_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4, ensure_ascii=False)
            return payload

        timeline = music_apply_timeline
        timeline_source = "pipeline"

        if timeline is None:
            timeline = self._resolve_timeline_fallback(
                music_application_plan=music_application_plan,
                channel_type=channel_type,
            )
            timeline_source = "processor_fallback"

        if timeline is None:
            payload = {
                "music_applied": False,
                "reason": "no_music_timeline",
                "output_video_path": str(video_path),
                "music_apply_timeline_used": False,
                "music_apply_timeline_source": timeline_source,
                "music_apply_segment_count": 0,
                "applied_music_segment_count": 0,
                "music_application_asset_ids": [],
            }
            with open(context_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4, ensure_ascii=False)
            return payload

        available_segments, missing_segments = self._split_available_segments(timeline)

        if not available_segments:
            payload = {
                "music_applied": False,
                "reason": "no_available_music_files",
                "output_video_path": str(video_path),
                "music_apply_timeline_used": True,
                "music_apply_timeline_source": timeline_source,
                "music_apply_timeline_id": timeline.timeline_id,
                "requested_music_segment_count": len(timeline.segments),
                "music_apply_segment_count": len(timeline.segments),
                "applied_music_segment_count": 0,
                "missing_music_segment_count": len(missing_segments),
                "partial_apply_used": False,
                "music_application_asset_ids": [],
                "missing_music_asset_ids": [segment.asset_id for segment in missing_segments],
            }
            with open(context_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=4, ensure_ascii=False)
            return payload

        output_path = video_path.with_name(f"{video_path.stem}_music_applied.mp4")

        ffmpeg_cmd = [
            r"D:\Tools\ffmpeg\bin\ffmpeg.exe",
            "-y",
            "-i",
            str(video_path),
        ]

        for segment in available_segments:
            ffmpeg_cmd.extend(["-i", str(segment.source_file_path)])

        ffmpeg_cmd.extend(
    [
        "-filter_complex",
        self._build_filter_complex(available_segments),
        "-map",
        "0:v",
        "-map",
        "[mixed]",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
        str(output_path),
    ]
)

        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise ValidationError(f"Music apply failed: {result.stderr}")

        partial_apply_used = len(missing_segments) > 0

        payload = {
            "music_applied": True,
            "reason": (
                "partial_timeline_segments_applied"
                if partial_apply_used
                else "timeline_segments_applied"
            ),
            "output_video_path": str(output_path),
            "music_apply_timeline_used": True,
            "music_apply_timeline_source": timeline_source,
            "music_apply_timeline_id": timeline.timeline_id,
            "requested_music_segment_count": len(timeline.segments),
            "music_apply_segment_count": len(timeline.segments),
            "applied_music_segment_count": len(available_segments),
            "missing_music_segment_count": len(missing_segments),
            "partial_apply_used": partial_apply_used,
            "music_application_asset_ids": [
                segment.asset_id for segment in available_segments
            ],
            "missing_music_asset_ids": [
                segment.asset_id for segment in missing_segments
            ],
            "timeline_score": timeline.timeline_score,
        }

        with open(context_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=4, ensure_ascii=False)

        return payload