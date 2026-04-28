from __future__ import annotations

import uuid

from models.audio_cue import AudioCue
from models.dynamic_edit_plan import DynamicEditPlan
from models.edit_timeline import EditTimeline
from models.job import Job


class MusicCueEngine:
    def _make_cue_id(self) -> str:
        return f"cue_{uuid.uuid4().hex[:12]}"

    def _clamp(self, value: float) -> float:
        return round(max(0.0, min(1.0, float(value))), 3)

    def _cue_kind_for_segment(
        self,
        *,
        segment_role: str,
        avg_reaction_intensity: float,
        pacing_hint_kind: str | None,
    ) -> str:
        if segment_role == "hook":
            return "intro_bed"

        if segment_role == "peak":
            return "peak_hit"

        if segment_role == "build":
            return "build_up"

        if segment_role == "bridge":
            if avg_reaction_intensity < 0.45:
                return "calm_bed"
            return "transition_bed"

        if segment_role == "payoff":
            if pacing_hint_kind == "clean_release":
                return "calm_bed"
            return "tension_bed"

        return "transition_bed"

    def build_cues(
        self,
        *,
        job: Job,
        timeline: EditTimeline,
        dynamic_edit_plan: DynamicEditPlan,
    ) -> list[AudioCue]:
        moments_by_segment: dict[str, list] = {}
        for moment in dynamic_edit_plan.reaction_moments:
            moments_by_segment.setdefault(moment.segment_id, []).append(moment)

        pacing_by_segment: dict[str, dict] = {
            hint["segment_id"]: hint
            for hint in dynamic_edit_plan.pacing_hints
            if isinstance(hint, dict) and hint.get("segment_id")
        }

        cues: list[AudioCue] = []

        for segment in timeline.selected_segments:
            segment_moments = moments_by_segment.get(segment.segment_id, [])
            pacing_hint = pacing_by_segment.get(segment.segment_id, {})

            avg_reaction_intensity = (
                sum(moment.intensity for moment in segment_moments) / len(segment_moments)
                if segment_moments
                else 0.0
            )
            pacing_strength = float(pacing_hint.get("strength", 0.0))
            pacing_hint_kind = pacing_hint.get("hint_kind")

            cue_kind = self._cue_kind_for_segment(
                segment_role=segment.segment_role,
                avg_reaction_intensity=avg_reaction_intensity,
                pacing_hint_kind=pacing_hint_kind,
            )

            intensity = self._clamp(
                (segment.selection_score * 0.45)
                + (avg_reaction_intensity * 0.35)
                + (pacing_strength * 0.20)
            )

            priority = self._clamp(
                (0.55 * segment.selection_score)
                + (0.25 * avg_reaction_intensity)
                + (0.20 * pacing_strength)
            )

            cues.append(
                AudioCue(
                    cue_id=self._make_cue_id(),
                    job_id=job.job_id,
                    timeline_id=timeline.timeline_id,
                    segment_id=segment.segment_id,
                    cue_kind=cue_kind,
                    start_time=segment.start_time,
                    end_time=segment.end_time,
                    intensity=intensity,
                    priority=priority,
                    notes=[
                        f"segment_role={segment.segment_role}",
                        f"avg_reaction_intensity={round(avg_reaction_intensity, 3)}",
                        f"pacing_hint_kind={pacing_hint_kind}",
                    ],
                )
            )

        return cues