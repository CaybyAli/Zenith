from __future__ import annotations

import uuid

from models.job import Job
from models.music_application_plan import MusicApplicationPlan
from models.music_apply_segment import MusicApplySegment
from models.music_apply_timeline import MusicApplyTimeline


class MusicApplyTimelineResolver:
    def _make_timeline_id(self) -> str:
        return f"music_apply_timeline_{uuid.uuid4().hex[:12]}"

    def _make_segment_id(self) -> str:
        return f"music_apply_seg_{uuid.uuid4().hex[:12]}"

    def _clamp(self, value: float) -> float:
        return round(max(0.0, min(1.0, float(value))), 3)

    def build(
        self,
        *,
        job: Job,
        music_application_plan: MusicApplicationPlan | None,
    ) -> MusicApplyTimeline | None:
        if job.channel_type.value != "gaming_main":
            return None

        if music_application_plan is None:
            return None

        ordered = sorted(
            music_application_plan.instructions,
            key=lambda instruction: (
                float(instruction.start_time),
                float(instruction.end_time),
                instruction.asset_id,
            ),
        )

        if not ordered:
            return None

        resolved_segments: list[MusicApplySegment] = []
        last_end = 0.0
        score_parts: list[float] = []

        for instruction in ordered:
            raw_start = float(instruction.start_time)
            raw_end = float(instruction.end_time)

            if raw_end <= raw_start:
                continue

            resolved_start = max(raw_start, last_end)
            resolved_end = raw_end

            if resolved_end <= resolved_start:
                continue

            segment_duration = round(resolved_end - resolved_start, 3)

            resolved_segments.append(
                MusicApplySegment(
                    segment_id=self._make_segment_id(),
                    job_id=job.job_id,
                    asset_id=instruction.asset_id,
                    cue_kind=instruction.cue_kind,
                    source_file_path=instruction.source_file_path,
                    video_start_time=resolved_start,
                    video_end_time=resolved_end,
                    music_offset_start=0.0,
                    music_offset_end=segment_duration,
                    music_level=instruction.music_level,
                    voice_priority=instruction.voice_priority,
                    ducking_required=instruction.ducking_required,
                    fade_in_seconds=instruction.fade_in_seconds,
                    fade_out_seconds=instruction.fade_out_seconds,
                    notes=[
                        f"source_instruction_id={instruction.instruction_id}",
                        f"resolved_duration={segment_duration}",
                    ],
                )
            )

            score_parts.append(
                self._clamp(
                    (float(instruction.music_level) * 0.4)
                    + ((1.0 - abs(float(instruction.voice_priority) - 0.8)) * 0.3)
                    + (0.3 if instruction.ducking_required else 0.15)
                )
            )

            last_end = resolved_end

        if not resolved_segments:
            return None

        timeline_score = round(sum(score_parts) / len(score_parts), 3) if score_parts else 0.0

        return MusicApplyTimeline(
            timeline_id=self._make_timeline_id(),
            job_id=job.job_id,
            channel_type=job.channel_type.value,
            segments=resolved_segments,
            timeline_score=timeline_score,
            notes=[
                f"segments={len(resolved_segments)}",
                "overlap_resolution=sequential_trim",
                "channel_music_apply_enabled=true",
            ],
        )