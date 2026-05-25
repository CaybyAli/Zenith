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
from core.ffmpeg_capability_resolver import resolve_ffmpeg_capabilities
from core.power_profile import PowerProfile
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
    Video is encoded with resolved H.264 encoder: h264_nvenc when available, otherwise libx264 + AAC audio.
    """

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _ffmpeg(self) -> str:
        """Resolve FFmpeg lazily, only when a real render command is built."""
        return get_ffmpeg_path()

    def _ffprobe(self) -> str:
        """Resolve FFprobe lazily, only when media probing is required."""
        return get_ffprobe_path()


    def _get_video_dimensions(self, source: Path) -> tuple[int, int]:
        cmd = [
            self._ffprobe(),
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
                    f"[0:v]hwdownload,format=nv12,crop={src_w//2}:1080:0:0,"
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
                    "[0:v]hwdownload,format=nv12,split=2[gp_src][fc_src];"
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
                    "[0:v]hwdownload,format=nv12,split=2[gp_src][fc_src];"
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
                "[0:v]hwdownload,format=nv12,split=5[gp_src][fc_tiny_src][fc_small_src][fc_medium_src][fc_large_src];"
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
            

        # Standard 16:9 / non-32:9 source fallback.
        # The method promises tuple[str, str], so never fall through to None.
        crop_window = getattr(instr, "crop_window", None) if instr else None
        if crop_window:
            crop_x = int(float(crop_window.get("x", 0.0)) * src_w)
            crop_y = int(float(crop_window.get("y", 0.0)) * src_h)
            crop_w = int(float(crop_window.get("width", 1.0)) * src_w)
            crop_h = int(float(crop_window.get("height", 1.0)) * src_h)

            crop_x = max(0, min(crop_x, src_w - 2))
            crop_y = max(0, min(crop_y, src_h - 2))
            crop_w = max(2, min(crop_w, src_w - crop_x))
            crop_h = max(2, min(crop_h, src_h - crop_y))

            if crop_w % 2:
                crop_w -= 1
            if crop_h % 2:
                crop_h -= 1

            print(
                f"[DEBUG] -> Rendering STANDARD 16:9 crop "
                f"{crop_w}x{crop_h}+{crop_x}+{crop_y} -> 1920x1080"
            )
            fc = (
                f"[0:v]hwdownload,format=nv12,crop={crop_w}:{crop_h}:{crop_x}:{crop_y},"
                "scale=1920:1080:force_original_aspect_ratio=decrease,"
                "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
                "setsar=1[out]"
            )
            return fc, "[out]"

        print(f"[DEBUG] -> Rendering STANDARD 16:9 source -> 1920x1080")
        fc = (
            "[0:v]hwdownload,format=nv12,scale=1920:1080:force_original_aspect_ratio=decrease,"
            "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
            "setsar=1[out]"
        )
        return fc, "[out]"


    # ------------------------------------------------------------------ #
    #  Censor SFX overlay helpers                                          #
    # ------------------------------------------------------------------ #

    def _load_censor_sfx_manifest(self) -> dict:
        manifest_path = Path("assets/sfx/censor/censor_sfx_manifest.json")
        if not manifest_path.exists():
            return {
                "default": "quack",
                "options": {},
                "warnings": [f"missing_manifest:{manifest_path}"],
            }

        with open(manifest_path, encoding="utf-8") as f:
            data = json.load(f)

        if not isinstance(data, dict):
            return {
                "default": "quack",
                "options": {},
                "warnings": ["invalid_censor_sfx_manifest"],
            }

        return data

    def _get_censor_sfx_path(
        self,
        replacement_sfx: str | None,
        manifest: dict,
    ) -> tuple[str, Path | None]:
        options = manifest.get("options")
        if not isinstance(options, dict):
            options = {}

        default_name = str(manifest.get("default") or "quack")
        requested_name = str(replacement_sfx or "").strip()
        sfx_name = requested_name if requested_name in options else default_name

        option = options.get(sfx_name)
        if not isinstance(option, dict):
            option = options.get(default_name)
            sfx_name = default_name

        if not isinstance(option, dict):
            return sfx_name, None

        raw_path = option.get("path")
        if not raw_path:
            return sfx_name, None

        return sfx_name, Path(str(raw_path))

    def _extract_censor_matches(self, job: Job) -> list[dict]:
        raw_matches = getattr(job, "profanity_censor_matches", None)

        if not raw_matches:
            report = getattr(job, "profanity_censor_report", None)
            if isinstance(report, dict):
                raw_matches = report.get("matches")

        if not isinstance(raw_matches, list):
            return []

        matches: list[dict] = []
        for item in raw_matches:
            if isinstance(item, dict):
                matches.append(dict(item))
                continue

            to_dict = getattr(item, "to_dict", None)
            if callable(to_dict):
                converted = to_dict()
                if isinstance(converted, dict):
                    matches.append(dict(converted))

        return matches

    def _safe_float_or_none(self, value) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _resolve_match_interval(self, match: dict) -> tuple[float, float] | None:
        start = self._safe_float_or_none(match.get("start_seconds"))
        end = self._safe_float_or_none(match.get("end_seconds"))
        center = self._safe_float_or_none(match.get("center_seconds"))
        duration = self._safe_float_or_none(match.get("duration_seconds"))

        if start is not None and end is not None and end > start:
            return start, end

        if start is not None and duration is not None and duration > 0:
            return start, start + duration

        if center is not None and duration is not None and duration > 0:
            half = duration / 2.0
            return max(0.0, center - half), center + half

        if center is not None:
            return max(0.0, center - 0.25), center + 0.25

        return None

    def _segment_duration_seconds(self, segment: TimelineSegment) -> float:
        duration = getattr(segment, "duration", None)
        if callable(duration):
            duration = duration()
        if duration is not None:
            try:
                return max(0.0, float(duration))
            except (TypeError, ValueError):
                pass
        return max(0.0, float(segment.end_time) - float(segment.start_time))

    def _build_segment_offset_table(self, segments: list[TimelineSegment]) -> list[dict]:
        table: list[dict] = []
        final_offset = 0.0

        for segment in segments:
            duration = self._segment_duration_seconds(segment)
            table.append(
                {
                    "segment": segment,
                    "source_start": float(segment.start_time),
                    "source_end": float(segment.end_time),
                    "final_start": final_offset,
                    "final_end": final_offset + duration,
                    "duration": duration,
                }
            )
            final_offset += duration

        return table

    def _max_censor_sfx_duration(self, sfx_name: str) -> float:
        if sfx_name == "beep":
            return 0.75
        return 1.00

    def _build_censor_sfx_events(
        self,
        job: Job,
        segments: list[TimelineSegment],
    ) -> list[dict]:
        manifest = self._load_censor_sfx_manifest()
        matches = self._extract_censor_matches(job)
        if not matches:
            return []

        offset_table = self._build_segment_offset_table(segments)
        events: list[dict] = []

        for match_index, match in enumerate(matches):
            if not bool(match.get("censor_required", False)):
                continue

            interval = self._resolve_match_interval(match)
            if interval is None:
                continue

            match_start, match_end = interval
            replacement_sfx = match.get("replacement_sfx")
            sfx_name, sfx_path = self._get_censor_sfx_path(replacement_sfx, manifest)

            if sfx_path is None or not sfx_path.exists():
                continue

            for row in offset_table:
                segment = row["segment"]
                kept_start = max(match_start, row["source_start"])
                kept_end = min(match_end, row["source_end"])

                if kept_end <= kept_start:
                    continue

                kept_duration = kept_end - kept_start
                if kept_duration < 0.05:
                    continue

                final_start = row["final_start"] + (kept_start - row["source_start"])
                final_duration = min(
                    kept_duration,
                    self._max_censor_sfx_duration(sfx_name),
                )

                events.append(
                    {
                        "event_id": f"censor_sfx_{match_index:03d}_{len(events):03d}",
                        "match_id": str(match.get("match_id") or f"match_{match_index}"),
                        "source_segment_id": str(segment.segment_id),
                        "replacement_sfx": sfx_name,
                        "asset_path": str(sfx_path),
                        "source_start_seconds": round(kept_start, 3),
                        "source_end_seconds": round(kept_end, 3),
                        "final_start_seconds": round(final_start, 3),
                        "duration_seconds": round(final_duration, 3),
                        "timing_source": str(match.get("timing_source") or "unknown"),
                    }
                )

        return events

    def _has_audio_stream(self, video_path: Path) -> bool:
        cmd = [
            self._ffprobe(),
            "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=index",
            "-of", "csv=p=0",
            str(video_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0 and bool(result.stdout.strip())

    def _apply_censor_sfx_overlay(
        self,
        video_path: Path,
        events: list[dict],
        expected_duration_seconds: float,
    ) -> dict:
        if not events:
            return {
                "applied": False,
                "applied_count": 0,
                "candidate_count": 0,
                "warnings": [],
            }

        valid_events = [
            event
            for event in events
            if Path(str(event.get("asset_path") or "")).exists()
            and float(event.get("duration_seconds") or 0.0) > 0.0
        ]

        if not valid_events:
            return {
                "applied": False,
                "applied_count": 0,
                "candidate_count": len(events),
                "warnings": ["no_valid_censor_sfx_events"],
            }

        has_audio = self._has_audio_stream(video_path)
        filter_parts: list[str] = []

        if has_audio:
            filter_parts.append(
                "[0:a]aresample=48000,"
                "aformat=sample_fmts=fltp:channel_layouts=stereo[maina]"
            )
            warnings: list[str] = []
        else:
            filter_parts.append(
                f"anullsrc=r=48000:cl=stereo:d={expected_duration_seconds:.3f}[maina]"
            )
            warnings = ["source_had_no_audio_stream_used_anullsrc"]

        cmd = [self._ffmpeg(), "-y", "-i", str(video_path)]
        for event in valid_events:
            cmd.extend(["-i", str(event["asset_path"])])

        for index, event in enumerate(valid_events):
            delay_ms = max(0, int(round(float(event["final_start_seconds"]) * 1000)))
            duration = max(0.01, float(event["duration_seconds"]))
            input_index = index + 1

            filter_parts.append(
                f"[{input_index}:a]"
                f"atrim=0:{duration:.3f},"
                "asetpts=PTS-STARTPTS,"
                "aresample=48000,"
                "aformat=sample_fmts=fltp:channel_layouts=stereo,"
                f"adelay={delay_ms}|{delay_ms}"
                f"[sfx{index}]"
            )

        mix_inputs = "[maina]" + "".join(
            f"[sfx{index}]" for index in range(len(valid_events))
        )
        filter_parts.append(
            f"{mix_inputs}"
            f"amix=inputs={len(valid_events) + 1}:normalize=0:duration=first[aout]"
        )

        tmp_path = video_path.with_name(f"{video_path.stem}_censor_sfx_tmp{video_path.suffix}")

        cmd.extend(
            [
                "-filter_complex",
                ";".join(filter_parts),
                "-map", "0:v:0",
                "-map", "[aout]",
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", "192k",
                "-movflags", "+faststart",
                str(tmp_path),
            ]
        )

        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            tmp_path.unlink(missing_ok=True)
            raise ValidationError(
                "Censor SFX overlay failed: "
                f"{result.stderr[-1200:]}"
            )

        shutil.move(str(tmp_path), str(video_path))

        return {
            "applied": True,
            "applied_count": len(valid_events),
            "candidate_count": len(events),
            "warnings": warnings,
            "events": valid_events,
        }


    # ------------------------------------------------------------------ #
    #  Video encoder resolution                                             #
    # ------------------------------------------------------------------ #

    _ENCODER_RUNTIME_PROBE_CACHE: dict[str, bool] = {}

    def _probe_video_encoder_runtime(self, encoder_name: str) -> bool:
        """Verify that an encoder can actually start, not just that FFmpeg lists it."""
        clean_encoder = str(encoder_name or "").strip()
        if not clean_encoder:
            return False

        if clean_encoder in self._ENCODER_RUNTIME_PROBE_CACHE:
            return self._ENCODER_RUNTIME_PROBE_CACHE[clean_encoder]

        cmd = [
            self._ffmpeg(),
            "-y",
            "-f", "lavfi",
            "-i", "color=c=black:s=16x16:r=1:d=0.1",
            "-frames:v", "1",
            "-an",
            "-c:v", clean_encoder,
            "-f", "null",
            "-",
        ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        ok = result.returncode == 0
        self._ENCODER_RUNTIME_PROBE_CACHE[clean_encoder] = ok
        return ok

    def _resolve_video_encoder(self, job: Job | None) -> dict:
        """Resolve FinalRenderDriver video encoder with NVENC -> libx264 fallback."""
        _render_cfg = PowerProfile.resolve_render_config(
            getattr(job, "power_profile", PowerProfile.DEFAULT)
        )
        _thread_args = (
            ["-threads", str(int(_render_cfg["threads"]))]
            if int(_render_cfg["threads"]) > 0
            else []
        )
        probe_job = {
            "job_id": getattr(job, "job_id", "unknown") if job is not None else "unknown",
            "ffmpeg_path_hint": self._ffmpeg(),
            "ffprobe_path_hint": self._ffprobe(),
            "ffmpeg_resolver_allow_tool_probe": True,
        }

        try:
            report = resolve_ffmpeg_capabilities(probe_job)
        except Exception as exc:
            return {
                "codec": "libx264",
                "mode": "cpu_fallback",
                "ffmpeg_args": [*_thread_args, "-c:v", "libx264", "-preset", "veryfast", "-crf", "23"],
                "resolver_status": "resolver_exception",
                "fallback_reason": f"resolver_exception:{type(exc).__name__}",
                "has_h264": False,
                "has_nvenc": False,
                "nvenc_runtime_ok": False,
            }

        has_nvenc = bool(getattr(report, "has_nvenc", False))
        has_h264 = bool(getattr(report, "has_h264", False))
        nvenc_runtime_ok = False

        if has_nvenc:
            nvenc_runtime_ok = self._probe_video_encoder_runtime("h264_nvenc")

        if has_nvenc and nvenc_runtime_ok:
            return {
                "codec": "h264_nvenc",
                "mode": "nvenc",
                "ffmpeg_args": [*_thread_args, "-c:v", "h264_nvenc", "-preset", _render_cfg["nvenc_preset"], "-cq", "23"],
                "resolver_status": str(getattr(report, "status", "")),
                "fallback_reason": None,
                "has_h264": has_h264,
                "has_nvenc": has_nvenc,
                "nvenc_runtime_ok": nvenc_runtime_ok,
            }

        fallback_reason = "nvenc_not_available"
        if has_nvenc and not nvenc_runtime_ok:
            fallback_reason = "nvenc_runtime_probe_failed"
        elif not has_h264:
            fallback_reason = "h264_capability_not_confirmed_using_libx264_best_effort"

        return {
            "codec": "libx264",
            "mode": "cpu_fallback",
            "ffmpeg_args": ["-c:v", "libx264", "-preset", "veryfast", "-crf", "23"],
            "resolver_status": str(getattr(report, "status", "")),
            "fallback_reason": fallback_reason,
            "has_h264": has_h264,
            "has_nvenc": has_nvenc,
            "nvenc_runtime_ok": nvenc_runtime_ok,
        }



    def _strip_hwdownload_from_filter(self, filter_complex: str) -> str:
        clean = str(filter_complex or "")
        for marker in (
            "hwdownload,format=nv12,",
            ",hwdownload,format=nv12",
            "hwdownload,format=yuv420p,",
            ",hwdownload,format=yuv420p",
        ):
            clean = clean.replace(marker, "")
        return clean

    def _strip_hwaccel_from_cmd(self, cmd: list[str]) -> list[str]:
        stripped: list[str] = []
        skip_next = 0

        for part in cmd:
            if skip_next > 0:
                skip_next -= 1
                continue

            if part == "-hwaccel":
                skip_next = 1
                continue

            if part == "-hwaccel_output_format":
                skip_next = 1
                continue

            stripped.append(part)

        return stripped

    def _should_retry_without_hwaccel(self, stderr: str) -> bool:
        lower = str(stderr or "").lower()
        retry_markers = [
            "function not implemented",
            "hwdownload",
            "cuda",
            "hardware",
            "device",
            "invalid argument",
            "no filtered frames",
            "nothing was written",
        ]
        return any(marker in lower for marker in retry_markers)


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
        video_encoder: dict | None = None,
    ) -> None:
        duration = round(segment.duration, 3)
        if duration <= 0:
            raise ValidationError(
                f"Segment {segment.segment_id} ({segment.segment_role}) "
                f"has non-positive duration: {duration}s"
            )

        safe_video_encoder = video_encoder or self._resolve_video_encoder(None)
        video_encoder_args = list(safe_video_encoder.get("ffmpeg_args") or [])

        cmd = [
            self._ffmpeg(), "-y",
            "-ss", str(round(segment.start_time, 3)),
            "-t", str(duration),
            "-hwaccel",
            "cuda",
            "-hwaccel_output_format",
            "cuda",
            "-i", str(source),
            "-filter_complex", filter_complex,
            "-map", out_label,
            "-map", "0:a?",
            "-pix_fmt", "yuv420p",
            *video_encoder_args,
            "-c:a", "aac",
            "-b:a", "192k",
            "-reset_timestamps", "1",
            str(temp_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0 and self._should_retry_without_hwaccel(result.stderr):
            fallback_cmd = self._strip_hwaccel_from_cmd(cmd)

            try:
                filter_index = fallback_cmd.index("-filter_complex")
                fallback_cmd[filter_index + 1] = self._strip_hwdownload_from_filter(
                    fallback_cmd[filter_index + 1]
                )
            except (ValueError, IndexError):
                pass

            result = subprocess.run(fallback_cmd, capture_output=True, text=True)

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
            self._ffmpeg(), "-y",
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
            video_encoder = self._resolve_video_encoder(job)

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
                
                self._extract_segment(source, seg, fc, label, tmp_path, video_encoder)
                seg_paths.append(tmp_path)
                
                print(f"   [OK] Segment fertig!\n")
                print(f"{'='*60}")
                print(f"[DONE] ALLE SEGMENTE GERENDERT - Jetzt zusammenfuegen...")
                print(f"{'='*60}\n")

            concat_path = out_dir / f"{job.job_id}_final.mp4"
            self._concat_segments(seg_paths, concat_path)
            
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

        total_duration = round(sum(self._segment_duration_seconds(s) for s in segments), 3)

        censor_sfx_events = self._build_censor_sfx_events(
            job=job,
            segments=segments,
        )
        censor_sfx_overlay_report = self._apply_censor_sfx_overlay(
            video_path=concat_path,
            events=censor_sfx_events,
            expected_duration_seconds=total_duration,
        )

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
            "censor_sfx_applied": bool(censor_sfx_overlay_report.get("applied")),
            "censor_sfx_events_count": int(censor_sfx_overlay_report.get("applied_count") or 0),
            "censor_sfx_candidate_count": int(censor_sfx_overlay_report.get("candidate_count") or 0),
            "censor_sfx_warnings": list(censor_sfx_overlay_report.get("warnings") or []),
            "censor_sfx_events": [
                {
                    "event_id": event["event_id"],
                    "match_id": event["match_id"],
                    "source_segment_id": event["source_segment_id"],
                    "replacement_sfx": event["replacement_sfx"],
                    "source_start_seconds": event["source_start_seconds"],
                    "source_end_seconds": event["source_end_seconds"],
                    "final_start_seconds": event["final_start_seconds"],
                    "duration_seconds": event["duration_seconds"],
                    "timing_source": event["timing_source"],
                }
                for event in list(censor_sfx_overlay_report.get("events") or [])
            ],
            "codec_video": video_encoder["codec"],
            "video_encoder_mode": video_encoder["mode"],
            "video_encoder_fallback_reason": video_encoder.get("fallback_reason"),
            "video_encoder_resolver_status": video_encoder.get("resolver_status"),
            "video_encoder_has_h264": bool(video_encoder.get("has_h264")),
            "video_encoder_has_nvenc": bool(video_encoder.get("has_nvenc")),
            "video_encoder_nvenc_runtime_ok": bool(video_encoder.get("nvenc_runtime_ok")),
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
