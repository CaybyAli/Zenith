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
from core.ffmpeg_helper import get_ffmpeg_path, get_ffprobe_path
from shared.errors import ValidationError

from typing import Literal

ZoomSize = Literal["tiny", "small", "medium", "large"]

class ZoomTimelineBuilder:
    """Baut eine kontinuierliche Timeline fuer smooth zoom transitions."""
    
    def __init__(self, segment_duration: float):
        self.segment_duration = segment_duration
        self.events: list[dict] = []  # {"time": float, "size": ZoomSize}
    
    def add_peak(self, rel_start: float, rel_end: float, size: ZoomSize) -> None:
        """Fuege einen Peak hinzu (relative Zeit im Segment)."""
        # Start-Event: Zoom beginnt
        self.events.append({"time": rel_start, "size": size, "type": "start"})
        # End-Event: Zoom endet
        self.events.append({"time": rel_end, "size": "tiny", "type": "end"})
    
    def build_timeline(self, transition_duration: float = 0.4) -> list[dict]:
        """
        Baut Timeline mit smooth transitions.
        
        Returns: [{"time": 0.0, "size": "tiny", "target": "large", "transition_end": 0.4}, ...]
        """
        if not self.events:
            # Ganzes Segment = tiny
            return [{"time": 0.0, "size": "tiny", "target": "tiny", "transition_end": 0.0}]
        
        # Sortiere Events nach Zeit
        sorted_events = sorted(self.events, key=lambda e: e["time"])
        
        timeline = []
        current_size: ZoomSize = "tiny"
        
        for event in sorted_events:
            target_size = event["size"]
            
            # Nur wenn sich Groesse aendert
            if target_size != current_size:
                timeline.append({
                    "time": event["time"],
                    "size": current_size,
                    "target": target_size,
                    "transition_end": event["time"] + transition_duration
                })
                current_size = target_size
        
        # Falls Timeline leer, fuege Default hinzu
        if not timeline:
            timeline.append({"time": 0.0, "size": "tiny", "target": "tiny", "transition_end": 0.0})
        
        return timeline

def ease_in_out_cubic(t: float) -> float:
    """
    Cubic ease-in-out function (smooth acceleration/deceleration).
    
    Args:
        t: Progress 0.0 to 1.0
    Returns:
        Eased value 0.0 to 1.0
    """
    if t < 0.5:
        return 4 * t * t * t
    else:
        p = 2 * t - 2
        return 1 + p * p * p / 2
def generate_zoom_expression(timeline: list[dict], segment_duration: float) -> str:
    """
    Generiert FFmpeg zoompan Expression fuer smooth transitions.
    
    Timeline Format:
    [
      {"time": 0.0, "size": "tiny", "target": "large", "transition_end": 0.4},
      {"time": 2.5, "size": "large", "target": "tiny", "transition_end": 2.9},
      ...
    ]
    
    Returns: FFmpeg Expression String fuer width/height
    """
    # Groessen
    sizes = {
        "tiny": (480, 270),
        "small": (540, 304),
        "medium": (660, 371),
        "large": (800, 450),
    }
    
    # Baue IF-ELSE Chain fuer WIDTH
    width_expr_parts = []
    height_expr_parts = []
    
    for i, event in enumerate(timeline):
        t_start = event["time"]
        t_end = event["transition_end"]
        from_size = event["size"]
        to_size = event["target"]
        
        from_w, from_h = sizes[from_size]
        to_w, to_h = sizes[to_size]
        
        if t_start == t_end:
            # Keine Transition, instant
            continue
        
        duration = t_end - t_start
        
        # Cubic ease-in-out in FFmpeg Expression
        # t_norm = (t - t_start) / duration
        # eased = if(t_norm<0.5, 4*t_norm^3, 1+(2*t_norm-2)^3/2)
        # value = from + (to - from) * eased
        
        t_norm_expr = f"((t-{t_start})/{duration})"
        cubic_expr = f"if(lt({t_norm_expr},0.5), 4*pow({t_norm_expr},3), 1+pow(2*{t_norm_expr}-2,3)/2)"
        
        width_transition = f"{from_w}+({to_w}-{from_w})*({cubic_expr})"
        height_transition = f"{from_h}+({to_h}-{from_h})*({cubic_expr})"
        
        # IF between(t, start, end)
        width_expr_parts.append(f"if(between(t,{t_start},{t_end}),{width_transition}")
        height_expr_parts.append(f"if(between(t,{t_start},{t_end}),{height_transition}")
    
    # Default = last target size
    if timeline:
        default_w, default_h = sizes[timeline[-1]["target"]]
    else:
        default_w, default_h = sizes["tiny"]
    
    # Baue Expression zusammen
    if width_expr_parts:
        # Nested if-else: if(cond1, val1, if(cond2, val2, default))
        width_expr = width_expr_parts[0]
        for part in width_expr_parts[1:]:
            width_expr = width_expr + "," + part
        width_expr = width_expr + "," + str(default_w) + ")" * len(width_expr_parts)
        
        height_expr = height_expr_parts[0]
        for part in height_expr_parts[1:]:
            height_expr = height_expr + "," + part
        height_expr = height_expr + "," + str(default_h) + ")" * len(height_expr_parts)
    else:
        width_expr = str(default_w)
        height_expr = str(default_h)
    
    return width_expr, height_expr


def interpolate_size(from_size: ZoomSize, to_size: ZoomSize, progress: float) -> tuple[int, int]:
    """
    Interpoliert zwischen zwei PiP-Groessen mit ease-in-out.
    
    Args:
        from_size: Start-Groesse
        to_size: Ziel-Groesse
        progress: 0.0 (start) bis 1.0 (end)
    Returns:
        (width, height) fuer aktuellen Progress
    """
    # Groessen-Definition
    sizes = {
        "tiny": (480, 270),
        "small": (540, 304),
        "medium": (660, 371),
        "large": (800, 450),
    }
    
    from_w, from_h = sizes[from_size]
    to_w, to_h = sizes[to_size]
    
    # Ease-in-out anwenden
    eased = ease_in_out_cubic(progress)
    
    # Interpolieren
    current_w = int(from_w + (to_w - from_w) * eased)
    current_h = int(from_h + (to_h - from_h) * eased)
    
    return current_w, current_h

class FinalRenderDriver:
    """
    Renders a final video by consuming all planning layers:
      - EditTimeline  : ordered segments with roles (hook/build/peak/bridge/payoff)
      - ReframePlan   : per-segment normalised crop windows {"x","y","width","height"}
      - DynamicEditPlan: zoom instructions mapped to segments
      - MusicApplyTimeline: delegated to MusicApplyProcessor after concat

    The output has the ACTUAL duration derived from the selected segments --
    not a hardcoded 60-second window.
    Video is encoded with h264_nvenc (RTX 4090 NVENC) + AAC audio.
    """

    _FFMPEG = get_ffmpeg_path()
    _FFPROBE = get_ffprobe_path()

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
        audio_peaks: list[dict],
        src_w: int,
        src_h: int,
    ) -> tuple[str, str]:

        """
        Baut den filter_complex fuer 32:9 Source -> 16:9 Output.
        Layout: Gameplay als Hauptbild, Facecam als PiP oben links.
        ZOOM: PiP vergroessert sich bei lustigen Momenten (3 Stufen)!
        Returns: (filter_complex_string, output_label)
        """
        instr = self._find_reframe_instruction(segment.segment_id, reframe_plan)
        layout_kind = instr.layout_kind if instr else "full_gameplay"

        print(f"[DEBUG] Segment {segment.segment_id[:8]} ({segment.segment_role}): layout_kind='{layout_kind}'")

        if src_w >= 3000:  # 32:9 Format
            if layout_kind == "facecam_emphasis":
                print(f"[DEBUG] -> Rendering FACECAM ONLY (left half)")
                fc = (
                    f"[0:v]crop={src_w//2}:1080:0:0,"
                    "scale=1920:1080[out]"
                )
                return fc, "[out]"
            
# ZOOM-FEATURE: Finde Zoom-Momente fuer dieses Segment
            zoom_instructions = self._find_zoom_instructions(segment, dynamic_edit_plan)
            
            # Basis-Groessen - 4 STUFEN fuer feinere Kontrolle (ANGEPASST: groesser)
            PIP_TINY_W, PIP_TINY_H = 480, 270       # Sehr klein
            PIP_SMALL_W, PIP_SMALL_H = 540, 304     # Normal
            PIP_MEDIUM_W, PIP_MEDIUM_H = 600, 338   # Laut reden (kleiner)
            PIP_LARGE_W, PIP_LARGE_H = 720, 405     # Schreien (kleiner)

            PIP_X, PIP_Y = 20, 100
            crop_offset = int((src_w / 1920) * 28)
            
            if not zoom_instructions:
                # Keine Zooms -> immer kleine Groesse
                print(f"[DEBUG] -> Rendering GAMEPLAY + Facecam PiP (SMALL: {PIP_SMALL_W}x{PIP_SMALL_H})")
                fc = (
                    "[0:v]split=2[gp_src][fc_src];"
                    f"[gp_src]crop={src_w//2}:1080:{src_w//2}:0,scale=1920:1080[gp];"
                    f"[fc_src]crop={src_w//2 - crop_offset}:1068:0:2,scale={PIP_SMALL_W}:{PIP_SMALL_H}[fc];"
                    f"[gp][fc]overlay={PIP_X}:{PIP_Y}[out]"
                )
                return fc, "[out]"

            # MIT ZOOMS: INSTANT switching zwischen 4 Stufen
            seg_start = segment.start_time
            
            enable_large = []
            enable_medium = []
            enable_small = []
            
            for peak in audio_peaks:
                duration = peak["end"] - peak["start"]
                
                if duration < 0.8:
                    print(f"[DEBUG]     -> [-] Skipped (too short: {duration:.1f}s, {peak['peak_db']:.1f}dB)")
                    continue

                rel_start = max(0.0, peak["start"] - seg_start)
                rel_end = max(rel_start + 0.05, peak["end"] - seg_start)
                
                # 4-STUFEN-SYSTEM
                if peak["peak_db"] > -13.0:
                    enable_large.append(f"between(t,{rel_start:.1f},{rel_end:.1f})")
                    print(f"[DEBUG]     -> [RED] LARGE zoom {rel_start:.1f}s-{rel_end:.1f}s ({peak['peak_db']:.1f}dB, {duration:.1f}s)")
                elif peak["peak_db"] > -16.5:
                    enable_medium.append(f"between(t,{rel_start:.1f},{rel_end:.1f})")
                    print(f"[DEBUG]     -> [YEL] MEDIUM zoom {rel_start:.1f}s-{rel_end:.1f}s ({peak['peak_db']:.1f}dB, {duration:.1f}s)")
                elif peak["peak_db"] > -18.5:
                    enable_small.append(f"between(t,{rel_start:.1f},{rel_end:.1f})")
                    print(f"[DEBUG]     -> [GRN] SMALL zoom {rel_start:.1f}s-{rel_end:.1f}s ({peak['peak_db']:.1f}dB, {duration:.1f}s)")
                else:
                    print(f"[DEBUG]     -> [-] TINY (quiet: {peak['peak_db']:.1f}dB)")
            
            if not enable_large and not enable_medium and not enable_small:
                print(f"[DEBUG] -> Found {len(zoom_instructions)} zoom(s), but all low intensity")
                print(f"[DEBUG] -> Rendering GAMEPLAY + Facecam PiP (SMALL: {PIP_SMALL_W}x{PIP_SMALL_H})")
                fc = (
                    "[0:v]split=2[gp_src][fc_src];"
                    f"[gp_src]crop={src_w//2}:1080:{src_w//2}:0,scale=1920:1080[gp];"
                    f"[fc_src]crop={src_w//2 - crop_offset}:1068:0:2,scale={PIP_SMALL_W}:{PIP_SMALL_H}[fc];"
                    f"[gp][fc]overlay={PIP_X}:{PIP_Y}[out]"
                )
                return fc, "[out]"
            
            enable_large_str = "+".join(enable_large) if enable_large else "0"
            enable_medium_str = "+".join(enable_medium) if enable_medium else "0"
            enable_small_str = "+".join(enable_small) if enable_small else "0"
            
            print(f"[DEBUG] -> [CUT] 4-STUFEN AUDIO-REACTIVE ZOOM:")
            print(f"[DEBUG]    LARGE={len(enable_large)} | MEDIUM={len(enable_medium)} | SMALL={len(enable_small)}")
            
            # Vier PiP-Groessen, INSTANT switching mit enable-Conditions
            fc = (
                "[0:v]split=5[gp_src][fc_tiny_src][fc_small_src][fc_medium_src][fc_large_src];"
                f"[gp_src]crop={src_w//2}:1080:{src_w//2}:0,scale=1920:1080[gp];"
                
                # TINY PiP (default - leise Momente)
                f"[fc_tiny_src]crop={src_w//2 - crop_offset}:1068:0:2,scale={PIP_TINY_W}:{PIP_TINY_H}[fc_tiny];"
                
                # SMALL PiP (normal reden)
                f"[fc_small_src]crop={src_w//2 - crop_offset}:1068:0:2,scale={PIP_SMALL_W}:{PIP_SMALL_H}[fc_small];"
                
                # MEDIUM PiP (laut/aufgeregt)
                f"[fc_medium_src]crop={src_w//2 - crop_offset}:1068:0:2,scale={PIP_MEDIUM_W}:{PIP_MEDIUM_H}[fc_medium];"
                
                # LARGE PiP (schreien)
                f"[fc_large_src]crop={src_w//2 - crop_offset}:1068:0:2,scale={PIP_LARGE_W}:{PIP_LARGE_H}[fc_large];"
                
                # Overlays: TINY (default), dann SMALL, MEDIUM, LARGE (Prioritaet steigend)
                f"[gp][fc_tiny]overlay={PIP_X}:{PIP_Y}:enable='not(({enable_small_str})+({enable_medium_str})+({enable_large_str}))':shortest=1[tmp1];"
                f"[tmp1][fc_small]overlay={PIP_X}:{PIP_Y}:enable='{enable_small_str}':shortest=1[tmp2];"
                f"[tmp2][fc_medium]overlay={PIP_X}:{PIP_Y}:enable='{enable_medium_str}':shortest=1[tmp3];"
                f"[tmp3][fc_large]overlay={PIP_X}:{PIP_Y}:enable='{enable_large_str}':shortest=1[out]"
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

        from core.audio_peak_detector import AudioPeakDetector

        """
        Render by consuming all planning layers.  Music is NOT applied here --
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
            total_segments = len(segments)

            print(f"\n{'='*60}")
            print(f"[CUT] RENDERING GESTARTET: {total_segments} Segmente")
            print(f"{'='*60}\n")

            for i, seg in enumerate(segments):
                # AUDIO-PEAK DETECTION fuer reactive zoom
                audio_peaks = AudioPeakDetector().detect_peaks(
                    video_path=source_path,
                    segment_start=seg.start_time,
                    segment_duration=seg.duration,
                    threshold_db=-20.0,
                    min_duration=0.5,
                )
                
                if audio_peaks:
                    print(f"[DEBUG] [AUDIO] Found {len(audio_peaks)} audio peaks in segment:")
                    for idx, peak in enumerate(audio_peaks, 1):
                        duration = peak['end'] - peak['start']
                        print(f"[DEBUG]   Peak {idx}: {peak['start']:.1f}s-{peak['end']:.1f}s ({duration:.1f}s duration, {peak['peak_db']:.1f}dB)")
                else:
                    print(f"[DEBUG] [MUTE] No audio peaks detected (segment too quiet)")
                
                # Fortschritt berechnen
                current_segment = i + 1
                progress_percent = int((current_segment / total_segments) * 100)
                
                print(f"[SEG] SEGMENT {current_segment}/{total_segments} ({progress_percent}%) - {seg.segment_role.upper()}")
                print(f"   [TIME] {seg.start_time:.1f}s -> {seg.end_time:.1f}s ({seg.duration:.1f}s)")
                
                fc, label = self._build_filter_complex(
                    seg, reframe_plan, dynamic_edit_plan, audio_peaks, src_w, src_h
                )
                tmp_path = tmp_dir / f"seg_{i:03d}_{seg.segment_role}.mp4"
                
                self._extract_segment(source, seg, fc, label, tmp_path)
                seg_paths.append(tmp_path)
                
                print(f"   [OK] Segment fertig!\n")
                print(f"{'='*60}")
                print(f"[DONE] ALLE SEGMENTE GERENDERT - Jetzt zusammenfuegen...")
                print(f"{'='*60}\n")

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
