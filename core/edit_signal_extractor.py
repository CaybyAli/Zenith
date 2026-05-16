from __future__ import annotations

import math
import uuid
from pathlib import Path

import numpy as np
from moviepy import AudioFileClip, VideoFileClip

from models.analysis_result import AnalysisResult
from models.edit_signal import EditSignal
from models.job import Job
from shared.errors import ValidationError


class EditSignalExtractor:
    """
    Render-path signal extractor for the legacy longform cut chain.

    These compact EditSignal values feed HighlightSelector, which builds the
    highlight_candidates and weak_zones consumed by LongformTimelineBuilder.
    The resulting EditTimeline.selected_segments are the render source of
    truth. This extractor is separate from unified_edit_signal_registry.py;
    the registry is an audit/review aggregation and is not read by the
    current FinalRenderDriver path.

    AGGRESSIVE FIX - Schwellwerte + Step-Sizes optimiert
    
    Ziel: 85-92% Video-Retention
    
    ÄNDERUNGEN:
    - audio_peak: 0.72 → 0.50 (TOP 50%)
    - motion_peak: 0.68 → 0.45 (TOP 55%)
    - Audio Step: 2.0s → 1.0s (doppelte Coverage, weniger Lücken!)
    - Video Step: 2.5s → 1.5s (bessere Coverage)
    """
    
    def _make_signal_id(self) -> str:
        return f"sig_{uuid.uuid4().hex[:12]}"

    def _safe_strength(self, value: float) -> float:
        return round(max(0.0, min(1.0, float(value))), 3)

    def _build_position_tags(
        self,
        start_time: float,
        end_time: float,
        duration_seconds: float,
    ) -> list[str]:
        midpoint = (start_time + end_time) / 2.0
        relative = midpoint / max(duration_seconds, 1.0)

        tags: list[str] = []

        if relative <= 0.15:
            tags.append("intro_zone")
        elif relative >= 0.85:
            tags.append("outro_zone")
        else:
            tags.append("mid_zone")

        if relative <= 0.33:
            tags.append("early_section")
        elif relative <= 0.66:
            tags.append("middle_section")
        else:
            tags.append("late_section")

        return tags

    def _prepare_motion_frame(
        self,
        frame,
        target_width: int = 320,
    ):
        array = np.asarray(frame, dtype=np.float32)

        if array.ndim != 3:
            return array

        height, width = array.shape[:2]

        if width <= 0 or height <= 0:
            return array

        stride = max(1, int(width / target_width))
        reduced = array[::stride, ::stride]

        return reduced

    def _extract_audio_energy_signals(
        self,
        *,
        job: Job,
        audio_path: str,
        duration_seconds: float,
        window_size: float = 4.0,
        step_size: float = 1.0,  # GEÄNDERT: 2.0 → 1.0s (weniger Lücken!)
    ) -> list[EditSignal]:
        signals: list[EditSignal] = []

        try:
            with AudioFileClip(audio_path) as audio_clip:
                if not audio_clip.duration or audio_clip.duration <= 0:
                    return []

                effective_duration = min(float(audio_clip.duration), duration_seconds)
                start_time = 0.0
                window_energy_rows: list[tuple[float, float, float]] = []

                while start_time < effective_duration:
                    end_time = min(start_time + window_size, effective_duration)
                    segment = audio_clip.subclipped(start_time, end_time)
                    frame = segment.to_soundarray(fps=22050)

                    if frame is None or len(frame) == 0:
                        rms = 0.0
                    else:
                        total = 0.0
                        count = 0
                        for row in frame:
                            if hasattr(row, "__len__"):
                                for value in row:
                                    total += float(value) * float(value)
                                    count += 1
                            else:
                                total += float(row) * float(row)
                                count += 1

                        rms = math.sqrt(total / count) if count else 0.0

                    window_energy_rows.append((start_time, end_time, rms))
                    start_time += step_size

                if not window_energy_rows:
                    return []

                max_rms = max(row[2] for row in window_energy_rows) or 1.0

                for start_time, end_time, rms in window_energy_rows:
                    strength = self._safe_strength(rms / max_rms)

                    # GEÄNDERT: 0.72 → 0.50 (TOP 50% werden Peaks!)
                    if strength >= 0.50:
                        signal_type = "audio_peak"
                        notes = [f"High audio energy detected ({strength:.3f})"]
                    elif strength <= 0.12:
                        signal_type = "silence_zone"
                        notes = [f"Very low audio energy detected ({strength:.3f})"]
                    else:
                        signal_type = "audio_activity"
                        notes = [f"Normal audio activity detected ({strength:.3f})"]

                    signals.append(
                        EditSignal(
                            signal_id=self._make_signal_id(),
                            job_id=job.job_id,
                            start_time=round(start_time, 3),
                            end_time=round(end_time, 3),
                            signal_type=signal_type,
                            strength=strength,
                            confidence=0.72,
                            tags=self._build_position_tags(
                                start_time=start_time,
                                end_time=end_time,
                                duration_seconds=duration_seconds,
                            ),
                            source="edit_signal_extractor.audio",
                            notes=notes,
                            metadata={
                                "window_size": window_size,
                                "step_size": step_size,
                                "raw_rms": round(rms, 6),
                            },
                        )
                    )

                return signals

        except Exception as exc:
            raise ValidationError(f"Could not extract audio edit signals: {exc}") from exc

    def _extract_video_activity_signals(
        self,
        *,
        job: Job,
        video_path: str,
        duration_seconds: float,
        window_size: float = 5.0,
        step_size: float = 1.5,  # GEÄNDERT: 2.5 → 1.5s (weniger Lücken!)
    ) -> list[EditSignal]:
        signals: list[EditSignal] = []

        try:
            with VideoFileClip(video_path) as clip:
                if not clip.duration or clip.duration <= 0:
                    return []

                effective_duration = min(float(clip.duration), duration_seconds)
                start_time = 0.0
                window_rows: list[tuple[float, float, float]] = []

                while start_time < effective_duration:
                    end_time = min(start_time + window_size, effective_duration)
                    sample_start = min(start_time, max(0.0, effective_duration - 0.05))
                    sample_middle = min(
                        (start_time + end_time) / 2.0,
                        max(0.0, effective_duration - 0.05),
                    )

                    frame_a = self._prepare_motion_frame(clip.get_frame(sample_start))
                    frame_b = self._prepare_motion_frame(clip.get_frame(sample_middle))

                    if frame_a.shape != frame_b.shape:
                        min_height = min(frame_a.shape[0], frame_b.shape[0])
                        min_width = min(frame_a.shape[1], frame_b.shape[1])
                        frame_a = frame_a[:min_height, :min_width]
                        frame_b = frame_b[:min_height, :min_width]

                    if frame_a.size == 0 or frame_b.size == 0:
                        motion_score = 0.0
                    else:
                        motion_score = float(
                            np.mean(np.abs(frame_a - frame_b)) / 255.0
                        )

                    window_rows.append((start_time, end_time, motion_score))
                    start_time += step_size

                if not window_rows:
                    return []

                max_motion = max(row[2] for row in window_rows) or 1.0

                for start_time, end_time, motion_score in window_rows:
                    strength = self._safe_strength(motion_score / max_motion)

                    # GEÄNDERT: 0.68 → 0.45 (TOP 55% werden Peaks!)
                    if strength >= 0.45:
                        signal_type = "motion_peak"
                        notes = [f"High visual activity detected ({strength:.3f})"]
                    elif strength <= 0.10:
                        signal_type = "low_motion_zone"
                        notes = [f"Low visual activity detected ({strength:.3f})"]
                    else:
                        signal_type = "motion_activity"
                        notes = [f"Normal visual activity detected ({strength:.3f})"]

                    signals.append(
                        EditSignal(
                            signal_id=self._make_signal_id(),
                            job_id=job.job_id,
                            start_time=round(start_time, 3),
                            end_time=round(end_time, 3),
                            signal_type=signal_type,
                            strength=strength,
                            confidence=0.64,
                            tags=self._build_position_tags(
                                start_time=start_time,
                                end_time=end_time,
                                duration_seconds=duration_seconds,
                            ),
                            source="edit_signal_extractor.video",
                            notes=notes,
                            metadata={
                                "window_size": window_size,
                                "step_size": step_size,
                                "raw_motion_score": round(motion_score, 6),
                                "sampling_mode": "downscaled_vectorized",
                                "target_width": 320,
                            },
                        )
                    )

                return signals

        except Exception as exc:
            raise ValidationError(f"Could not extract video edit signals: {exc}") from exc

    def extract(self, job: Job, analysis_result: AnalysisResult) -> list[EditSignal]:
        if not job.raw_video_path:
            raise ValidationError("EditSignalExtractor needs raw_video_path")

        source_path = Path(job.raw_video_path)
        if not source_path.exists() or not source_path.is_file():
            raise ValidationError(f"Video file not found: {job.raw_video_path}")

        if analysis_result.duration_seconds <= 0:
            raise ValidationError("Analysis result must contain a positive duration")

        signals: list[EditSignal] = []

        signals.append(
            EditSignal(
                signal_id=self._make_signal_id(),
                job_id=job.job_id,
                start_time=0.0,
                end_time=round(float(analysis_result.duration_seconds), 3),
                signal_type="duration_context",
                strength=1.0,
                confidence=1.0,
                tags=["global_context"],
                source="edit_signal_extractor.analysis",
                notes=[
                    f"Video duration is {analysis_result.duration_seconds:.2f} seconds",
                    f"Usable for shorts: {analysis_result.usable_for_shorts}",
                    f"Usable for longform: {analysis_result.usable_for_longform}",
                ],
                metadata={
                    "duration_seconds": round(float(analysis_result.duration_seconds), 3),
                    "file_size_bytes": int(analysis_result.file_size_bytes),
                },
            )
        )

        signals.extend(
            self._extract_audio_energy_signals(
                job=job,
                audio_path=str(source_path),
                duration_seconds=float(analysis_result.duration_seconds),
            )
        )

        signals.extend(
            self._extract_video_activity_signals(
                job=job,
                video_path=str(source_path),
                duration_seconds=float(analysis_result.duration_seconds),
            )
        )

        return sorted(
            signals,
            key=lambda signal: (signal.start_time, signal.end_time, signal.signal_type),
        )
