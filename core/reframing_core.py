from __future__ import annotations

import uuid

from core.facecam_gameplay_separator import FacecamGameplaySeparator
from models.edit_timeline import EditTimeline
from models.framing_instruction import FramingInstruction
from models.highlight_candidate import HighlightCandidate
from models.job import Job
from models.reframe_plan import ReframePlan


class ReframingCore:
    def __init__(self) -> None:
        self.separator = FacecamGameplaySeparator()

    def _make_plan_id(self) -> str:
        return f"reframe_{uuid.uuid4().hex[:12]}"

    def _make_instruction_id(self) -> str:
        return f"frame_{uuid.uuid4().hex[:12]}"

    def _clamp_score(self, value: float) -> float:
        return round(max(0.0, min(1.0, float(value))), 3)

    def _layout_kind_for_focus(
        self,
        focus_kind: str,
        *,
        target_aspect_ratio: str,
    ) -> str:
        if target_aspect_ratio == "16:9":
            if focus_kind == "facecam":
                return "facecam_emphasis"
            if focus_kind == "gameplay":
                return "gameplay_crop"
            if focus_kind == "balanced":
                return "balanced_split"
            return "full_gameplay"

        if target_aspect_ratio == "9:16":
            return "vertical_safe_focus"

        return "full_gameplay"

    def _crop_window(
        self,
        focus_kind: str,
        *,
        target_aspect_ratio: str,
) -> dict[str, float]:
        if target_aspect_ratio == "16:9":
            if focus_kind == "facecam":
            # Nur Facecam (linke Hälfte des 32:9 Source)
                return {"x": 0.0, "y": 0.0, "width": 0.5, "height": 1.0}
            if focus_kind == "gameplay":
            # Nur Gameplay (rechte Hälfte des 32:9 Source)
                return {"x": 0.5, "y": 0.0, "width": 0.5, "height": 1.0}
            if focus_kind == "balanced":
            # Basis = Gameplay, Facecam kommt als PiP drüber (siehe Bug 2)
                return {"x": 0.5, "y": 0.0, "width": 0.5, "height": 1.0}
            return {"x": 0.5, "y": 0.0, "width": 0.5, "height": 1.0}

    # ... 9:16 Block bleibt erstmal unangetastet ...

        if target_aspect_ratio == "9:16":
            if focus_kind == "facecam":
                return {"x": 0.05, "y": 0.05, "width": 0.30, "height": 0.90}
            if focus_kind == "gameplay":
                return {"x": 0.34, "y": 0.05, "width": 0.30, "height": 0.90}
            if focus_kind == "balanced":
                return {"x": 0.24, "y": 0.05, "width": 0.36, "height": 0.90}
            return {"x": 0.28, "y": 0.05, "width": 0.34, "height": 0.90}

        return {"x": 0.0, "y": 0.0, "width": 1.0, "height": 1.0}

    def build_plan(
        self,
        job: Job,
        timeline: EditTimeline,
        highlight_candidates: list[HighlightCandidate],
        *,
        source_aspect_ratio: str = "32:9",
        primary_target_aspect_ratio: str = "16:9",
        secondary_target_aspect_ratio: str | None = "9:16",
    ) -> ReframePlan:
        candidate_lookup = {
            candidate.candidate_id: candidate
            for candidate in highlight_candidates
        }

        instructions: list[FramingInstruction] = []
        confidences: list[float] = []

        for segment in timeline.selected_segments:
            candidate = candidate_lookup.get(segment.candidate_id)
            separation = self.separator.classify_segment(segment, candidate)

            focus_kind = str(separation["focus_kind"])
            confidence = float(separation["confidence"])
            notes = list(separation["notes"])

            primary_layout_kind = self._layout_kind_for_focus(
                focus_kind,
                target_aspect_ratio=primary_target_aspect_ratio,
            )
            primary_crop_window = self._crop_window(
                focus_kind,
                target_aspect_ratio=primary_target_aspect_ratio,
            )

            secondary_layout_kind = (
                self._layout_kind_for_focus(
                    focus_kind,
                    target_aspect_ratio=secondary_target_aspect_ratio,
                )
                if secondary_target_aspect_ratio
                else None
            )
            secondary_crop_window = (
                self._crop_window(
                    focus_kind,
                    target_aspect_ratio=secondary_target_aspect_ratio,
                )
                if secondary_target_aspect_ratio
                else None
            )

            instruction = FramingInstruction(
                instruction_id=self._make_instruction_id(),
                job_id=job.job_id,
                timeline_id=timeline.timeline_id,
                segment_id=segment.segment_id,
                focus_kind=focus_kind,
                layout_kind=primary_layout_kind,
                source_aspect_ratio=source_aspect_ratio,
                target_aspect_ratio=primary_target_aspect_ratio,
                crop_window=primary_crop_window,
                notes=notes + [f"segment_role={segment.segment_role}"],
                metadata={
                    "focus_confidence": round(confidence, 3),
                    "candidate_id": segment.candidate_id,
                    "secondary_target_aspect_ratio": secondary_target_aspect_ratio,
                    "secondary_layout_kind": secondary_layout_kind,
                    "secondary_crop_window": secondary_crop_window,
                },
            )
            instructions.append(instruction)
            confidences.append(confidence)

        plan_score = self._clamp_score(
            sum(confidences) / len(confidences) if confidences else 0.0
        )

        return ReframePlan(
            plan_id=self._make_plan_id(),
            job_id=job.job_id,
            timeline_id=timeline.timeline_id,
            source_aspect_ratio=source_aspect_ratio,
            primary_target_aspect_ratio=primary_target_aspect_ratio,
            secondary_target_aspect_ratio=secondary_target_aspect_ratio,
            instructions=instructions,
            plan_notes=[
                f"Built {len(instructions)} framing instructions",
                f"Primary target: {primary_target_aspect_ratio}",
                f"Secondary target: {secondary_target_aspect_ratio}",
            ],
            plan_score=plan_score,
        )