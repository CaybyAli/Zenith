from __future__ import annotations

from dataclasses import dataclass, field

from models.edit_timeline import EditTimeline
from models.facecam_reaction_result import FacecamReactionResult
from models.framing_instruction import FramingInstruction
from models.reframe_plan import ReframePlan
from models.timeline_segment import TimelineSegment


MAX_FACECAM_ONLY_SECONDS = 4.0
INTRO_WINDOW_SECONDS = 20.0
INTRO_MAX_FACECAM_ONLY_SECONDS = 3.0


@dataclass
class FacecamIntroGuardSummary:
    converted: int = 0
    intro_blocked: int = 0
    limited: int = 0
    no_reaction_blocked: int = 0
    allowed_short_reactions: int = 0
    examples: list[str] = field(default_factory=list)


class FacecamIntroGuard:
    def apply(
        self,
        timeline: EditTimeline,
        reframe_plan: ReframePlan,
        facecam_reaction_result: FacecamReactionResult | None = None,
    ) -> FacecamIntroGuardSummary:
        summary = FacecamIntroGuardSummary()
        segment_lookup = {
            segment.segment_id: segment
            for segment in timeline.selected_segments
        }

        timeline_position = 0.0
        for segment in sorted(
            timeline.selected_segments,
            key=lambda item: (item.start_time, item.end_time),
        ):
            instruction = self._instruction_for_segment(reframe_plan, segment.segment_id)
            if instruction is None:
                timeline_position += segment.duration
                continue

            if instruction.layout_kind != "facecam_emphasis":
                timeline_position += segment.duration
                continue

            in_intro_window = timeline_position < INTRO_WINDOW_SECONDS
            has_short_reaction = self._has_allowed_short_reaction(
                segment,
                facecam_reaction_result,
                max_duration=(
                    INTRO_MAX_FACECAM_ONLY_SECONDS
                    if in_intro_window
                    else MAX_FACECAM_ONLY_SECONDS
                ),
            )

            if has_short_reaction and segment.duration <= (
                INTRO_MAX_FACECAM_ONLY_SECONDS
                if in_intro_window
                else MAX_FACECAM_ONLY_SECONDS
            ):
                instruction.notes.append("facecam_intro_guard_allowed_short_reaction")
                summary.allowed_short_reactions += 1
                timeline_position += segment.duration
                continue

            reasons: list[str] = []
            if in_intro_window:
                reasons.append("intro_facecam_only_blocked")
                summary.intro_blocked += 1
            if segment.duration > MAX_FACECAM_ONLY_SECONDS:
                reasons.append("facecam_only_limited")
                summary.limited += 1
            if not self._has_any_reaction_overlap(segment, facecam_reaction_result):
                reasons.append("facecam_only_blocked_no_reaction")
                summary.no_reaction_blocked += 1

            self._convert_to_balanced(instruction, segment, reasons)
            summary.converted += 1
            self._add_example(
                summary,
                f"{segment.segment_id} {segment.start_time:.2f}-{segment.end_time:.2f} "
                f"facecam_emphasis->balanced_split",
            )
            timeline_position += segment.duration

        reframe_plan.plan_notes.append(
            "Facecam intro guard: "
            f"converted={summary.converted} "
            f"intro_blocked={summary.intro_blocked} "
            f"limited={summary.limited} "
            f"no_reaction_blocked={summary.no_reaction_blocked} "
            f"allowed_short_reactions={summary.allowed_short_reactions}"
        )
        reframe_plan.touch()

        for segment in segment_lookup.values():
            segment.touch()

        return summary

    def _instruction_for_segment(
        self,
        reframe_plan: ReframePlan,
        segment_id: str,
    ) -> FramingInstruction | None:
        for instruction in reframe_plan.instructions:
            if instruction.segment_id == segment_id:
                return instruction
        return None

    def _convert_to_balanced(
        self,
        instruction: FramingInstruction,
        segment: TimelineSegment,
        reasons: list[str],
    ) -> None:
        instruction.focus_kind = "balanced"
        instruction.layout_kind = "balanced_split"
        instruction.crop_window = {"x": 0.5, "y": 0.0, "width": 0.5, "height": 1.0}
        instruction.notes.extend(reasons or ["facecam_only_guarded"])
        instruction.notes.append(
            f"facecam_guard_segment_duration={segment.duration:.3f}"
        )
        instruction.metadata["facecam_intro_guard"] = {
            "converted_to": "balanced_split",
            "reasons": list(reasons),
            "segment_duration": segment.duration,
        }
        instruction.touch()

    def _has_allowed_short_reaction(
        self,
        segment: TimelineSegment,
        facecam_reaction_result: FacecamReactionResult | None,
        *,
        max_duration: float,
    ) -> bool:
        if facecam_reaction_result is None:
            return False

        for window in facecam_reaction_result.reaction_windows:
            if window.reaction_score < 0.55:
                continue
            if window.end_seconds - window.start_seconds > max_duration:
                continue
            if self._overlaps(
                segment.start_time,
                segment.end_time,
                window.start_seconds,
                window.end_seconds,
            ):
                return True
        return False

    def _has_any_reaction_overlap(
        self,
        segment: TimelineSegment,
        facecam_reaction_result: FacecamReactionResult | None,
    ) -> bool:
        if facecam_reaction_result is None:
            return False
        return any(
            self._overlaps(
                segment.start_time,
                segment.end_time,
                window.start_seconds,
                window.end_seconds,
            )
            for window in facecam_reaction_result.reaction_windows
        )

    def _overlaps(
        self,
        start_a: float,
        end_a: float,
        start_b: float,
        end_b: float,
    ) -> bool:
        return max(start_a, start_b) < min(end_a, end_b)

    def _add_example(self, summary: FacecamIntroGuardSummary, example: str) -> None:
        if len(summary.examples) < 3:
            summary.examples.append(example)
