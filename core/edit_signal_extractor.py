from __future__ import annotations

import math
import uuid
from pathlib import Path
from typing import Any

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

    def _job_attr(self, job: Any, name: str, default: Any = None) -> Any:
        if isinstance(job, dict):
            return job.get(name, default)
        return getattr(job, name, default)

    def _item_value(self, item: Any, *names: str, default: Any = None) -> Any:
        for name in names:
            if isinstance(item, dict) and name in item:
                return item.get(name)
            if not isinstance(item, dict) and hasattr(item, name):
                return getattr(item, name)
        return default

    def _safe_float_or_none(self, value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _safe_bool(self, value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y", "silent"}
        return False

    def _rows_from_payload(
        self,
        payload: Any,
        keys: tuple[str, ...],
    ) -> list[Any]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, tuple):
            return list(payload)
        if isinstance(payload, dict):
            for key in keys:
                rows = payload.get(key)
                if isinstance(rows, list):
                    return rows
            return []
        if payload is not None:
            for key in keys:
                rows = getattr(payload, key, None)
                if isinstance(rows, list):
                    return rows
        return []

    def _nested_payload(self, payload: Any, *names: str) -> Any:
        current = payload
        for name in names:
            if current is None:
                return None
            if isinstance(current, dict):
                current = current.get(name)
            else:
                current = getattr(current, name, None)
        return current

    def _time_bounds_from_item(
        self,
        item: Any,
        *,
        duration_seconds: float,
        fallback_window_seconds: float,
    ) -> tuple[float, float] | None:
        start = self._safe_float_or_none(
            self._item_value(item, "start_seconds", "start_time", "start")
        )
        end = self._safe_float_or_none(
            self._item_value(item, "end_seconds", "end_time", "end")
        )
        center = self._safe_float_or_none(
            self._item_value(item, "center_seconds", "time_seconds", "time", "timestamp")
        )

        if start is None and end is None and center is None:
            return None

        if start is None:
            if center is None:
                start = 0.0
            else:
                start = center - (fallback_window_seconds / 2.0)
        if end is None:
            if center is not None:
                end = center + (fallback_window_seconds / 2.0)
            else:
                end = start + fallback_window_seconds

        start = max(0.0, min(float(start), duration_seconds))
        end = max(0.0, min(float(end), duration_seconds))
        if end <= start:
            end = min(duration_seconds, start + fallback_window_seconds)

        if end <= start:
            return None

        return round(start, 3), round(end, 3)

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

    def _select_cached_audio_rows(self, job: Job) -> tuple[list[Any], str | None]:
        sources: list[tuple[str, Any, tuple[str, ...]]] = [
            (
                "rms_energy_context_timeline",
                self._job_attr(job, "rms_energy_context_timeline"),
                ("energy_timeline", "points"),
            ),
            (
                "rms_energy_context_adapter",
                self._job_attr(job, "rms_energy_context_adapter"),
                ("energy_timeline", "points"),
            ),
            (
                "rms_energy_timeline_result",
                self._job_attr(job, "rms_energy_timeline_result"),
                ("points", "energy_timeline"),
            ),
            (
                "rms_energy_report.energy_timeline_result",
                self._nested_payload(
                    self._job_attr(job, "rms_energy_report"),
                    "energy_timeline_result",
                ),
                ("points", "energy_timeline"),
            ),
            (
                "rms_energy_run_report.energy_timeline_result",
                self._nested_payload(
                    self._job_attr(job, "rms_energy_run_report"),
                    "energy_timeline_result",
                ),
                ("points", "energy_timeline"),
            ),
        ]

        for source_name, payload, keys in sources:
            rows = self._rows_from_payload(payload, keys)
            if rows:
                return rows, source_name

        return [], None

    def _extract_cached_audio_energy_signals(
        self,
        *,
        job: Job,
        duration_seconds: float,
        bucket_seconds: float = 1.0,
        window_seconds: float = 4.0,
    ) -> list[EditSignal]:
        rows, source_name = self._select_cached_audio_rows(job)
        if not rows:
            return []

        buckets: dict[int, dict[str, Any]] = {}
        bucket_seconds = max(0.25, float(bucket_seconds))
        effective_duration = max(0.0, float(duration_seconds))

        for row in rows:
            bounds = self._time_bounds_from_item(
                row,
                duration_seconds=effective_duration,
                fallback_window_seconds=0.01,
            )
            if bounds is None:
                continue
            start_time, end_time = bounds
            midpoint = (start_time + end_time) / 2.0
            bucket_index = int(midpoint // bucket_seconds)

            energy = self._safe_float_or_none(
                self._item_value(
                    row,
                    "energy_score",
                    "normalized_energy",
                    "rms",
                    "score",
                    "strength",
                )
            )
            if energy is None:
                continue

            energy = self._safe_strength(energy)
            is_silent = self._safe_bool(self._item_value(row, "is_silent", default=False))

            bucket = buckets.setdefault(
                bucket_index,
                {
                    "sum": 0.0,
                    "count": 0,
                    "max": 0.0,
                    "silent_count": 0,
                    "rms_max": 0.0,
                },
            )
            bucket["sum"] += energy
            bucket["count"] += 1
            bucket["max"] = max(float(bucket["max"]), energy)
            if is_silent:
                bucket["silent_count"] += 1
            rms_value = self._safe_float_or_none(self._item_value(row, "rms"))
            if rms_value is not None:
                bucket["rms_max"] = max(float(bucket["rms_max"]), rms_value)

        if not buckets:
            return []

        signals: list[EditSignal] = []
        job_id = str(self._job_attr(job, "job_id", "unknown_job"))

        span_bucket_count = max(1, int(round(max(bucket_seconds, window_seconds) / bucket_seconds)))

        for bucket_index in sorted(buckets):
            span_buckets = [
                buckets[index]
                for index in range(bucket_index, bucket_index + span_bucket_count)
                if index in buckets
            ]
            if not span_buckets:
                continue
            bucket = {
                "sum": sum(float(item["sum"]) for item in span_buckets),
                "count": sum(int(item["count"]) for item in span_buckets),
                "max": max(float(item["max"]) for item in span_buckets),
                "silent_count": sum(int(item["silent_count"]) for item in span_buckets),
                "rms_max": max(float(item["rms_max"]) for item in span_buckets),
            }
            count = max(1, int(bucket["count"]))
            avg_energy = float(bucket["sum"]) / count
            max_energy = float(bucket["max"])
            silent_ratio = float(bucket["silent_count"]) / count
            strength = self._safe_strength(max(avg_energy, max_energy * 0.75))
            start_time = round(bucket_index * bucket_seconds, 3)
            end_time = round(min(start_time + window_seconds, effective_duration), 3)
            if end_time <= start_time:
                continue

            if strength <= 0.06 or (silent_ratio >= 0.95 and max_energy <= 0.12):
                signal_type = "silence_zone"
                notes = [f"Cached low audio energy detected ({strength:.3f})"]
            elif strength >= 0.50 or max_energy >= 0.85:
                signal_type = "audio_peak"
                notes = [f"Cached high audio energy detected ({strength:.3f})"]
            else:
                signal_type = "audio_activity"
                notes = [f"Cached normal audio activity detected ({strength:.3f})"]

            signals.append(
                EditSignal(
                    signal_id=self._make_signal_id(),
                    job_id=job_id,
                    start_time=start_time,
                    end_time=end_time,
                    signal_type=signal_type,
                    strength=strength,
                    confidence=0.74,
                    tags=self._build_position_tags(
                        start_time=start_time,
                        end_time=end_time,
                        duration_seconds=effective_duration,
                    ),
                    source="edit_signal_extractor.cached_audio",
                    notes=notes,
                    metadata={
                        "cache_source": source_name,
                        "bucket_seconds": bucket_seconds,
                        "window_seconds": window_seconds,
                        "point_count": count,
                        "avg_energy": round(avg_energy, 6),
                        "max_energy": round(max_energy, 6),
                        "silent_ratio": round(silent_ratio, 6),
                        "raw_rms_max": round(float(bucket["rms_max"]), 6),
                    },
                )
            )

        return signals

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

    def _select_cached_video_rows(self, job: Job) -> tuple[list[Any], str | None]:
        sources: list[tuple[str, Any, tuple[str, ...]]] = [
            (
                "motion_analysis_segments",
                self._job_attr(job, "motion_analysis_segments"),
                ("motion_segments", "segments"),
            ),
            (
                "motion_analysis_report.motion_segments",
                self._job_attr(job, "motion_analysis_report"),
                ("motion_segments", "segments"),
            ),
            (
                "visual_energy_segments",
                self._job_attr(job, "visual_energy_segments"),
                ("visual_energy_segments", "segments"),
            ),
            (
                "visual_energy_report.visual_energy_segments",
                self._job_attr(job, "visual_energy_report"),
                ("visual_energy_segments", "segments"),
            ),
            (
                "motion_analysis_points",
                self._job_attr(job, "motion_analysis_points"),
                ("motion_points", "points"),
            ),
            (
                "visual_energy_points",
                self._job_attr(job, "visual_energy_points"),
                ("visual_energy_points", "points"),
            ),
        ]

        for source_name, payload, keys in sources:
            rows = self._rows_from_payload(payload, keys)
            if rows:
                return rows, source_name

        return [], None

    def _video_strength_from_row(self, row: Any) -> float | None:
        values = [
            self._safe_float_or_none(
                self._item_value(
                    row,
                    "max_motion_score",
                    "avg_motion_score",
                    "motion_score",
                    "raw_motion_value",
                )
            ),
            self._safe_float_or_none(
                self._item_value(
                    row,
                    "max_visual_energy_score",
                    "avg_visual_energy_score",
                    "visual_energy_score",
                    "combined_video_score",
                    "score",
                    "strength",
                )
            ),
        ]
        numeric = [value for value in values if value is not None]
        if not numeric:
            return None
        return self._safe_strength(max(numeric))

    def _extract_cached_video_activity_signals(
        self,
        *,
        job: Job,
        duration_seconds: float,
        fallback_window_seconds: float = 1.5,
    ) -> list[EditSignal]:
        rows, source_name = self._select_cached_video_rows(job)
        if not rows:
            return []

        effective_duration = max(0.0, float(duration_seconds))
        signals: list[EditSignal] = []
        job_id = str(self._job_attr(job, "job_id", "unknown_job"))

        for row in rows:
            bounds = self._time_bounds_from_item(
                row,
                duration_seconds=effective_duration,
                fallback_window_seconds=fallback_window_seconds,
            )
            if bounds is None:
                continue
            start_time, end_time = bounds
            strength = self._video_strength_from_row(row)
            if strength is None:
                continue

            classification = str(
                self._item_value(row, "classification", "label", default="")
            ).strip().lower()

            if classification in {
                "high_motion",
                "high_visual_energy",
                "peak_visual_energy",
            } or strength >= 0.45:
                signal_type = "motion_peak"
                notes = [f"Cached high visual activity detected ({strength:.3f})"]
            elif classification in {
                "static",
                "low_motion",
                "dead_visual_candidate",
                "low_visual_energy",
                "technical_warning",
            } or strength <= 0.10:
                signal_type = "low_motion_zone"
                notes = [f"Cached low visual activity detected ({strength:.3f})"]
            else:
                signal_type = "motion_activity"
                notes = [f"Cached normal visual activity detected ({strength:.3f})"]

            signals.append(
                EditSignal(
                    signal_id=self._make_signal_id(),
                    job_id=job_id,
                    start_time=start_time,
                    end_time=end_time,
                    signal_type=signal_type,
                    strength=strength,
                    confidence=0.66,
                    tags=self._build_position_tags(
                        start_time=start_time,
                        end_time=end_time,
                        duration_seconds=effective_duration,
                    ),
                    source="edit_signal_extractor.cached_video",
                    notes=notes,
                    metadata={
                        "cache_source": source_name,
                        "classification": classification,
                        "fallback_window_seconds": fallback_window_seconds,
                    },
                )
            )

        return signals

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

        cached_audio_signals = self._extract_cached_audio_energy_signals(
            job=job,
            duration_seconds=float(analysis_result.duration_seconds),
        )
        if cached_audio_signals:
            signals.extend(cached_audio_signals)
        else:
            signals.extend(
                self._extract_audio_energy_signals(
                    job=job,
                    audio_path=str(source_path),
                    duration_seconds=float(analysis_result.duration_seconds),
                )
            )

        cached_video_signals = self._extract_cached_video_activity_signals(
            job=job,
            duration_seconds=float(analysis_result.duration_seconds),
        )
        if cached_video_signals:
            signals.extend(cached_video_signals)
        else:
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
