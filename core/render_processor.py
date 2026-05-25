from __future__ import annotations

import json
import subprocess
from pathlib import Path

from models.edit_decision import EditDecision
from models.job import Job
from models.music_application_plan import MusicApplicationPlan
from core.ffmpeg_helper import get_ffmpeg_path, get_ffprobe_path
from core.ffmpeg_capability_resolver import resolve_ffmpeg_capabilities
from shared.errors import ValidationError

_ENCODER_CACHE: dict[tuple[str, str], str] = {}


def _resolve_encoder(ffmpeg_path: str, ffprobe_path: str) -> str:
    cache_key = (str(ffmpeg_path), str(ffprobe_path))
    if cache_key in _ENCODER_CACHE:
        return _ENCODER_CACHE[cache_key]

    try:
        report = resolve_ffmpeg_capabilities(
            {
                "job_id": "render_processor",
                "ffmpeg_path_hint": str(ffmpeg_path),
                "ffprobe_path_hint": str(ffprobe_path),
                "ffmpeg_resolver_allow_tool_probe": True,
            }
        )
        encoder = "h264_nvenc" if bool(getattr(report, "has_nvenc", False)) else "libx264"
    except Exception:
        encoder = "libx264"

    _ENCODER_CACHE[cache_key] = encoder
    return encoder


# DEPRECATED - Phase 2: superseded by FinalRenderDriver for gaming_main longform rendering.
class RenderProcessor:
    def _parse_segment(self, segment_text: str) -> tuple[float, float | None]:
        segment_text = segment_text.strip()

        if " - " not in segment_text:
            raise ValidationError(f"Invalid segment format: {segment_text}")

        start_raw, end_raw = segment_text.split(" - ", 1)
        start_raw = start_raw.strip().replace("s", "")
        end_raw = end_raw.strip().replace("s", "")

        start_time = float(start_raw)
        end_time = None if end_raw.lower() == "end" else float(end_raw)

        return start_time, end_time

    def _resolve_render_window(
        self,
        edit_decision: EditDecision,
        final_edit_package: dict | None = None,
    ) -> tuple[float, float | None, bool, str]:
        if not edit_decision.selected_segments:
            raise ValidationError("No selected segments for render")

        fallback_start, fallback_end = self._parse_segment(
            edit_decision.selected_segments[0]
        )

        render_start = fallback_start
        render_end = fallback_end
        used_final_edit_package = False
        render_strategy = "legacy_trim"

        if isinstance(final_edit_package, dict):
            timeline_start_time = final_edit_package.get("timeline_start_time")
            timeline_end_time = final_edit_package.get("timeline_end_time")

            if (
                isinstance(timeline_start_time, (int, float))
                and isinstance(timeline_end_time, (int, float))
                and float(timeline_end_time) > float(timeline_start_time)
            ):
                render_start = round(float(timeline_start_time), 3)
                render_end = round(float(timeline_end_time), 3)
                used_final_edit_package = True
                render_strategy = str(
                    final_edit_package.get(
                        "render_strategy",
                        "integrated_timeline_window",
                    )
                )

        return render_start, render_end, used_final_edit_package, render_strategy

    def _instruction_overlaps_window(
        self,
        *,
        instruction_start: float,
        instruction_end: float,
        render_start: float,
        render_end: float | None,
    ) -> bool:
        if render_end is None:
            return instruction_end > render_start

        return instruction_end > render_start and instruction_start < render_end

    def _build_music_application_context(
        self,
        *,
        music_application_plan: MusicApplicationPlan | None,
        render_start: float,
        render_end: float | None,
    ) -> dict[str, object]:
        if music_application_plan is None:
            return {
                "music_application_plan_used": False,
                "music_application_instruction_count": 0,
                "applied_music_instruction_count": 0,
                "music_application_asset_ids": [],
                "render_audio_strategy": "no_music_application",
            }

        overlapping_instructions = [
            instruction
            for instruction in music_application_plan.instructions
            if self._instruction_overlaps_window(
                instruction_start=float(instruction.start_time),
                instruction_end=float(instruction.end_time),
                render_start=render_start,
                render_end=render_end,
            )
        ]

        return {
            "music_application_plan_used": True,
            "music_application_plan_id": music_application_plan.plan_id,
            "music_application_channel_type": music_application_plan.channel_type,
            "music_application_instruction_count": len(music_application_plan.instructions),
            "applied_music_instruction_count": len(overlapping_instructions),
            "music_application_asset_ids": [
                instruction.asset_id for instruction in overlapping_instructions
            ],
            "music_application_score": music_application_plan.application_score,
            "render_audio_strategy": (
                "music_application_attached"
                if overlapping_instructions
                else "music_application_available_but_outside_window"
            ),
        }

    def render(
        self,
        job: Job,
        edit_decision: EditDecision,
        final_edit_package: dict | None = None,
        music_application_plan: MusicApplicationPlan | None = None,
    ) -> str:
        if not job.raw_video_path:
            raise ValidationError("No video to render")

        source = Path(job.raw_video_path)

        if not source.exists():
            raise ValidationError(f"Source file not found: {source}")

        render_start, render_end, used_final_edit_package, render_strategy = (
            self._resolve_render_window(
                edit_decision=edit_decision,
                final_edit_package=final_edit_package,
            )
        )

        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)

        output_path = output_dir / f"{job.job_id}_final.mp4"
        context_path = output_dir / f"{job.job_id}_final_render_context.json"

        ffmpeg_path = get_ffmpeg_path()
        ffprobe_path = get_ffprobe_path()
        video_encoder = _resolve_encoder(ffmpeg_path, ffprobe_path)
        if video_encoder == "h264_nvenc":
            video_encoder_args = ["-c:v", video_encoder, "-pix_fmt", "yuv420p"]
        else:
            video_encoder_args = ["-c:v", video_encoder]

        ffmpeg_cmd = [
            ffmpeg_path,
            "-y",
            "-ss",
            str(render_start),
            "-hwaccel",
            "cuda",
            "-hwaccel_output_format",
            "cuda",
            "-i",
            str(source),
        ]

        if render_end is not None:
            render_duration = round(render_end - render_start, 3)

            if render_duration <= 0:
                raise ValidationError(
                    f"Invalid render window: start={render_start}, end={render_end}"
                )

            ffmpeg_cmd.extend(["-t", str(render_duration)])

        if video_encoder != "h264_nvenc":
            ffmpeg_cmd.extend(["-vf", "hwdownload,format=nv12"])

        ffmpeg_cmd.extend(
            [
                *video_encoder_args,
                "-c:a",
                "aac",
                str(output_path),
            ]
        )

        result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

        if result.returncode != 0:
            raise ValidationError(f"Render failed: {result.stderr}")

        context_payload = {
            "job_id": job.job_id,
            "used_final_edit_package": used_final_edit_package,
            "render_strategy": render_strategy,
            "render_start_time": render_start,
            "render_end_time": render_end if render_end is not None else "end",
        }

        if isinstance(final_edit_package, dict):
            context_payload.update(
                {
                    "timeline_id": final_edit_package.get("timeline_id"),
                    "selected_segments": int(final_edit_package.get("selected_segments", 0) or 0),
                    "reframe_instructions": int(final_edit_package.get("reframe_instructions", 0) or 0),
                    "reaction_moments": int(final_edit_package.get("reaction_moments", 0) or 0),
                    "zoom_instructions": int(final_edit_package.get("zoom_instructions", 0) or 0),
                    "audio_cues": int(final_edit_package.get("audio_cues", 0) or 0),
                    "audio_mix_instructions": int(final_edit_package.get("audio_mix_instructions", 0) or 0),
                    "integration_score": float(final_edit_package.get("integration_score", 0.0) or 0.0),
                    "primary_focus_kind": final_edit_package.get("primary_focus_kind"),
                }
            )

        context_payload.update(
            self._build_music_application_context(
                music_application_plan=music_application_plan,
                render_start=render_start,
                render_end=render_end,
            )
        )

        with open(context_path, "w", encoding="utf-8") as f:
            json.dump(context_payload, f, indent=4, ensure_ascii=False)

        return str(output_path)
