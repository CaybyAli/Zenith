from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from models.dynamic_edit_plan import DynamicEditPlan
from models.edit_timeline import EditTimeline
from models.job import Job
from models.reframe_plan import ReframePlan
from models.timeline_segment import TimelineSegment
from models.zoom_instruction import ZoomInstruction
from shared.errors import ValidationError


class FinalRenderDriver:
    """
    Renders a final video by consuming all planning layers:
      - EditTimeline  : ordered segments with roles (hook/build/peak/bridge/payoff)
      - ReframePlan   : per-segment normalised crop windows {"x","y","width","height"}
      - DynamicEditPlan: zoom instructions mapped to segments
      - MusicApplyTimeline: delegated to MusicApplyProcessor after concat

    The output has the ACTUAL duration derived from the selected segments —
    not a hardcoded 60-second window.
    Video is encoded with h264_nvenc (RTX 4090 NVENC) + AAC audio.
    """

    _FFMPEG = r"D:\Tools\ffmpeg\bin\ffmpeg.exe"
    _FFPROBE = r"D:\Tools\ffmpeg\bin\ffprobe.exe"

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
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

    def _find_reframe_instruction(self, segment_id: str, reframe_plan: ReframePlan | None):
        if reframe_plan is None:
            return None
        for instr in reframe_plan.instructions:
            if instr.segment_id == segment_id:
                return instr
        return None

    def _find_zoom_instructions(
        self,
        segment: TimelineSegment,
        dynamic_edit_plan: DynamicEditPlan | None,
    ) -> list[ZoomInstruction]:
        if dynamic_edit_plan is None:
            return []
        return [
            z for z in dynamic_edit_plan.zoom_instructions
            if z.segment_id == segment.segment_id
        ]

    # ------------------------------------------------------------------ #
    #  Filter chain builder                                                #
    # ------------------------------------------------------------------ #

    def _build_filter_complex(
        self,
        segment: TimelineSegment,
        reframe_plan: ReframePlan | None,
        dynamic_edit_plan: DynamicEditPlan | None,
        src_w: int,
        src_h: int,
    ) -> tuple[str, str]:
        """
        Baut den filter_complex für 32:9 Source -> 16:9 Output.
        Layout: Gameplay als Hauptbild, Facecam als PiP oben links.
        Returns: (filter_complex_string, output_label)
        """
        instr = self._find_reframe_instruction(segment.segment_id, reframe_plan)
        layout_kind = instr.layout_kind if instr else "full_gameplay"

        # Sonderfall: Facecam soll Hauptbild sein (kein PiP)
        if layout_kind == "facecam_emphasis":
            fc = (
                "[0:v]crop=1920:1080:0:0,"
                "scale=1920:1080[out]"
            )
            return fc, "[out]"

        # Standardfall: Gameplay = Hauptbild, Facecam = PiP oben links
        PIP_W, PIP_H = 480, 270   # 25% der Breite
        PIP_X, PIP_Y = 32, 32     # Abstand zum oberen + linken Rand

        fc = (
            "[0:v]split=2[gp_src][fc_src];"
            "[gp_src]crop=1920:1080:1920:0,scale=1920:1080[gp];"
            f"[fc_src]crop=1920:1080:0:0,scale={PIP_W}:{PIP_H}[fc];"
            f"[gp][fc]overlay={PIP_X}:{PIP_Y}[out]"
        )
        return fc, "[out]"

    # ------------------------------------------------------------------ #
    #  FFmpeg operations                                                   #
    # ------------------------------------------------------------------ #

    def _extract_segment(
        self,
        source: Path,
        segment: TimelineSegment,
        filter_complex: str,
        out_label: str,
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
            "-filter_complex", filter_complex,
            "-map", out_label,
            "-map", "0:a?",
            "-pix_fmt", "yuv420p",
            "-c:v", "h264_nvenc",
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
            )

    def _concat_segments(self, seg_paths: list[Path], output_path: Path) -> None:
        if len(seg_paths) == 1:
            shutil.copy2(seg_paths[0], output_path)
            return

        list_file = output_path.parent / "concat_list.txt"
        with open(list_file, "w") as f:
            for p in seg_paths:
                f.write(f"file '{str(p.resolve())}'\n")

        cmd = [
            self._FFMPEG, "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(list_file.resolve()),
            "-c", "copy",
            str(output_path),
        ]
        result = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        list_file.unlink(missing_ok=True)
        if result.returncode != 0:
            raise ValidationError(f"Segment concat failed: {result.stderr[-800:]}")

    # ------------------------------------------------------------------ #
    #  Public API                                                          #
    # ------------------------------------------------------------------ #

    def render(
        self,
        job: Job,
        source_path: str | Path,
        edit_timeline: EditTimeline,
        reframe_plan: ReframePlan | None = None,
        dynamic_edit_plan: DynamicEditPlan | None = None,
        output_dir: str | Path = "output",
    ) -> str:
        """
        Render by consuming all planning layers.  Music is NOT applied here —
        it is left to MusicApplyProcessor in build_publish_artifacts so that
        the existing post-render audio pipeline is unchanged.

        Returns the path to the concatenated final video.
        """
        source = Path(source_path)
        if not source.exists():
            raise ValidationError(f"Source video not found: {source}")

        segments = sorted(
            edit_timeline.selected_segments,
            key=lambda s: s.start_time,
        )
        if not segments:
            raise ValidationError(
                f"EditTimeline {edit_timeline.timeline_id} has no selected segments"
            )

        out_dir = Path(output_dir)
        out_dir.mkdir(exist_ok=True)

        tmp_dir = out_dir / f"tmp_{job.job_id}"
        tmp_dir.mkdir(exist_ok=True)

        try:
            src_w, src_h = self._get_video_dimensions(source)

            seg_paths: list[Path] = []
            for i, seg in enumerate(segments):
                fc, label = self._build_filter_complex(
                    seg, reframe_plan, dynamic_edit_plan, src_w, src_h
                )
                tmp_path = tmp_dir / f"seg_{i:03d}_{seg.segment_role}.mp4"
                self._extract_segment(source, seg, fc, label, tmp_path)
                seg_paths.append(tmp_path)

            concat_path = out_dir / f"{job.job_id}_final.mp4"
            self._concat_segments(seg_paths, concat_path)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        total_duration = round(sum(s.duration for s in segments), 3)

        context = {
            "job_id": job.job_id,
            "render_driver": "FinalRenderDriver",
            "source_video": str(source),
            "timeline_id": edit_timeline.timeline_id,
            "timeline_score": edit_timeline.timeline_score,
            "segments_count": len(segments),
            "segments": [
                {
                    "segment_id": s.segment_id,
                    "role": s.segment_role,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "duration": s.duration,
                }
                for s in segments
            ],
            "total_duration_seconds": total_duration,
            "reframe_plan_used": reframe_plan is not None,
            "reframe_instructions_count": (
                len(reframe_plan.instructions) if reframe_plan is not None else 0
            ),
            "dynamic_edit_plan_used": dynamic_edit_plan is not None,
            "zoom_instructions_count": (
                len(dynamic_edit_plan.zoom_instructions)
                if dynamic_edit_plan is not None
                else 0
            ),
            "codec_video": "h264_nvenc",
            "codec_audio": "aac",
            "output_video_path": str(concat_path),
        }

        context_path = out_dir / f"{job.job_id}_final_render_driver_context.json"
        with open(context_path, "w", encoding="utf-8") as f:
            json.dump(context, f, indent=4, ensure_ascii=False)

        return str(concat_path)

    def render_from_json(
        self,
        job: Job,
        source_path: str | Path,
        export_path: str | Path,
        output_dir: str | Path = "output",
    ) -> str:
        """
        Standalone render: reads all planning JSON files from export_path
        (edit_timeline.json, reframe_plan.json, dynamic_edit_plan.json)
        and renders via NVENC.  Music is applied from music_apply_timeline.json
        when present, since this path is used outside the normal pipeline.
        """
        from core.dynamic_edit_plan_repository import DynamicEditPlanRepository
        from core.edit_timeline_repository import EditTimelineRepository
        from core.music_apply_timeline_repository import MusicApplyTimelineRepository
        from core.reframe_plan_repository import ReframePlanRepository

        edit_timeline = EditTimelineRepository().load_timeline(export_path)
        if edit_timeline is None:
            raise ValidationError(
                f"edit_timeline.json not found in {export_path}"
            )

        reframe_plan = ReframePlanRepository().load_plan(export_path)
        dynamic_edit_plan = DynamicEditPlanRepository().load_plan(export_path)
        music_apply_timeline = MusicApplyTimelineRepository().load_timeline(export_path)

        final_path = self.render(
            job=job,
            source_path=source_path,
            edit_timeline=edit_timeline,
            reframe_plan=reframe_plan,
            dynamic_edit_plan=dynamic_edit_plan,
            output_dir=output_dir,
        )

        if music_apply_timeline is not None:
            from core.music_apply_processor import MusicApplyProcessor
            music_result = MusicApplyProcessor().apply(
                rendered_video_path=final_path,
                music_application_plan=None,
                channel_type=job.channel_type.value,
                music_apply_timeline=music_apply_timeline,
            )
            if music_result.get("music_applied"):
                final_path = str(music_result["output_video_path"])

        return final_path
