from __future__ import annotations

import uuid

from models.dynamic_edit_plan import DynamicEditPlan
from models.edit_timeline import EditTimeline
from models.job import Job
from models.reaction_moment import ReactionMoment
from models.reframe_plan import ReframePlan
from models.zoom_instruction import ZoomInstruction


class ZoomPacingEngine:
    def _make_plan_id(self) -> str:
        return f"dynamic_{uuid.uuid4().hex[:12]}"

    def _make_zoom_id(self) -> str:
        return f"zoom_{uuid.uuid4().hex[:12]}"

    def _clamp(self, value: float) -> float:
        return round(max(0.0, min(1.0, float(value))), 3)

    def _zoom_kind(
        self,
        *,
        reaction_kind: str,
        focus_kind: str,
    ) -> str:
        if reaction_kind == "hook_reaction":
            return "hook_push"

        if reaction_kind == "peak_reaction":
            if focus_kind == "gameplay":
                return "punch_in_gameplay"
            if focus_kind == "facecam":
                return "punch_in_facecam"
            return "peak_push"

        if focus_kind == "facecam":
            return "punch_in_facecam"

        if focus_kind == "gameplay":
            return "punch_in_gameplay"

        return "hold_frame"

    def _build_pacing_hints(
        self,
        timeline: EditTimeline,
        reaction_moments: list[ReactionMoment],
    ) -> list[dict]:
        moments_by_segment: dict[str, list[ReactionMoment]] = {}

        for moment in reaction_moments:
            moments_by_segment.setdefault(moment.segment_id, []).append(moment)

        hints: list[dict] = []

        for segment in timeline.selected_segments:
            segment_moments = moments_by_segment.get(segment.segment_id, [])
            avg_intensity = (
                sum(moment.intensity for moment in segment_moments) / len(segment_moments)
                if segment_moments
                else 0.0
            )

            if segment.segment_role == "hook":
                hint_kind = "fast_open"
                strength = self._clamp(max(0.72, avg_intensity))
                notes = ["opening should feel immediate"]
            elif segment.segment_role == "peak":
                hint_kind = "impact_emphasis"
                strength = self._clamp(max(0.78, avg_intensity))
                notes = ["peak should feel sharp and high-energy"]
            elif segment.segment_role == "build":
                hint_kind = "steady_ramp"
                strength = self._clamp(max(0.60, avg_intensity))
                notes = ["build should increase momentum without chaos"]
            elif segment.segment_role == "bridge":
                hint_kind = "controlled_breath"
                strength = self._clamp(max(0.48, avg_intensity))
                notes = ["bridge can breathe but should not feel dead"]
            elif segment.segment_role == "payoff":
                hint_kind = "clean_release"
                strength = self._clamp(max(0.58, avg_intensity))
                notes = ["payoff should resolve cleanly"]
            else:
                hint_kind = "balanced_flow"
                strength = self._clamp(max(0.50, avg_intensity))
                notes = ["keep balanced pacing"]

            hints.append(
                {
                    "segment_id": segment.segment_id,
                    "hint_kind": hint_kind,
                    "strength": strength,
                    "notes": notes,
                }
            )

        return hints

    def build_plan(
        self,
        *,
        job: Job,
        timeline: EditTimeline,
        reframe_plan: ReframePlan,
        reaction_moments: list[ReactionMoment],
    ) -> DynamicEditPlan:
        instruction_by_segment = {
            instruction.segment_id: instruction
            for instruction in reframe_plan.instructions
        }

        zoom_instructions: list[ZoomInstruction] = []

        for moment in reaction_moments:
            instruction = instruction_by_segment.get(moment.segment_id)
            focus_kind = instruction.focus_kind if instruction else "balanced"

            zoom_kind = self._zoom_kind(
                reaction_kind=moment.reaction_kind,
                focus_kind=focus_kind,
            )
            intensity = self._clamp(
                (moment.intensity * 0.75) + (moment.confidence * 0.25)
            )

            zoom_instructions.append(
                ZoomInstruction(
                    instruction_id=self._make_zoom_id(),
                    job_id=job.job_id,
                    timeline_id=timeline.timeline_id,
                    segment_id=moment.segment_id,
                    moment_id=moment.moment_id,
                    zoom_kind=zoom_kind,
                    focus_kind=focus_kind,
                    intensity=intensity,
                    start_time=moment.start_time,
                    end_time=moment.end_time,
                    notes=[
                        f"reaction_kind={moment.reaction_kind}",
                        f"focus_kind={focus_kind}",
                    ],
                )
            )

        pacing_hints = self._build_pacing_hints(
            timeline,
            reaction_moments,
        )

        raw_scores: list[float] = [zoom.intensity for zoom in zoom_instructions]
        raw_scores.extend(float(item["strength"]) for item in pacing_hints)

        plan_score = self._clamp(
            sum(raw_scores) / len(raw_scores) if raw_scores else 0.0
        )

        return DynamicEditPlan(
            plan_id=self._make_plan_id(),
            job_id=job.job_id,
            timeline_id=timeline.timeline_id,
            reaction_moments=reaction_moments,
            zoom_instructions=zoom_instructions,
            pacing_hints=pacing_hints,
            plan_score=plan_score,
            plan_notes=[
                f"reaction_moments={len(reaction_moments)}",
                f"zoom_instructions={len(zoom_instructions)}",
                f"pacing_hints={len(pacing_hints)}",
            ],
        )