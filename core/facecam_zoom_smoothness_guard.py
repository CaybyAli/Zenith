from __future__ import annotations

from dataclasses import dataclass, field

from models.dynamic_edit_plan import DynamicEditPlan
from models.edit_timeline import EditTimeline
from models.facecam_reaction_result import FacecamReactionResult
from models.reframe_plan import ReframePlan
from models.timeline_segment import TimelineSegment
from models.zoom_instruction import ZoomInstruction


FACE_CAM_EDGE_SAFE_SECONDS = 0.60
MIN_FACECAM_ZOOM_DURATION_SECONDS = 1.20
MIN_REACTION_SCORE_FOR_FACECAM_ZOOM = 0.70


@dataclass
class FacecamZoomSmoothnessSummary:
    removed: int = 0
    shifted: int = 0
    edge_blocked: int = 0
    short_removed: int = 0
    weak_reaction_removed: int = 0
    layout_converted: int = 0
    examples: list[str] = field(default_factory=list)

    def add_example(self, text: str) -> None:
        if len(self.examples) < 6:
            self.examples.append(text)


class FacecamZoomSmoothnessGuard:
    engine = "facecam-zoom-smoothness-guard-v1"

    def apply(
        self,
        timeline: EditTimeline,
        dynamic_edit_plan: DynamicEditPlan,
        *,
        facecam_reaction_result: FacecamReactionResult | None = None,
        reframe_plan: ReframePlan | None = None,
    ) -> FacecamZoomSmoothnessSummary:
        summary = FacecamZoomSmoothnessSummary()
        segment_by_id = {
            segment.segment_id: segment
            for segment in timeline.selected_segments
            if segment.end_time > segment.start_time
        }

        kept: list[ZoomInstruction] = []
        for zoom in sorted(
            dynamic_edit_plan.zoom_instructions,
            key=lambda item: (item.segment_id, item.start_time, item.end_time),
        ):
            segment = segment_by_id.get(zoom.segment_id)
            if segment is None:
                kept.append(zoom)
                continue

            adjusted = self._guard_zoom(
                zoom,
                segment,
                facecam_reaction_result,
                summary,
            )
            if adjusted is not None:
                kept.append(adjusted)

        dynamic_edit_plan.zoom_instructions = kept
        dynamic_edit_plan.plan_notes.append(
            "Facecam zoom smoothness: "
            f"removed={summary.removed} "
            f"shifted={summary.shifted} "
            f"edge_blocked={summary.edge_blocked} "
            f"short_removed={summary.short_removed} "
            f"weak_reaction_removed={summary.weak_reaction_removed}"
        )
        dynamic_edit_plan.touch()

        if reframe_plan is not None:
            self._stabilize_facecam_layouts(
                timeline,
                reframe_plan,
                facecam_reaction_result,
                summary,
            )

        print(
            "[FACECAM-ZOOM-SMOOTHNESS] "
            f"removed={summary.removed} "
            f"shifted={summary.shifted} "
            f"edge_blocked={summary.edge_blocked} "
            f"short_removed={summary.short_removed} "
            f"weak_reaction_removed={summary.weak_reaction_removed}"
        )
        if summary.examples:
            print(f"[FACECAM-ZOOM-SMOOTHNESS] examples={'; '.join(summary.examples)}")

        return summary

    def _guard_zoom(
        self,
        zoom: ZoomInstruction,
        segment: TimelineSegment,
        facecam_reaction_result: FacecamReactionResult | None,
        summary: FacecamZoomSmoothnessSummary,
    ) -> ZoomInstruction | None:
        zoom.start_time = round(max(segment.start_time, zoom.start_time), 3)
        zoom.end_time = round(min(segment.end_time, zoom.end_time), 3)

        if zoom.end_time <= zoom.start_time:
            self._remove(summary, "edge_blocked", zoom, "outside_segment")
            return None

        if not self._has_strong_reaction(zoom, segment, facecam_reaction_result):
            self._remove(summary, "weak_reaction_removed", zoom, "weak_reaction")
            return None

        if zoom.duration < MIN_FACECAM_ZOOM_DURATION_SECONDS:
            self._remove(summary, "short_removed", zoom, "short_zoom")
            return None

        safe_start = round(segment.start_time + FACE_CAM_EDGE_SAFE_SECONDS, 3)
        safe_end = round(segment.end_time - FACE_CAM_EDGE_SAFE_SECONDS, 3)
        if safe_end <= safe_start:
            self._remove(summary, "edge_blocked", zoom, "segment_too_short_for_safe_zoom")
            return None

        if zoom.start_time < safe_start:
            duration = zoom.duration
            shifted_end = round(safe_start + duration, 3)
            if shifted_end <= safe_end:
                old = zoom.start_time
                zoom.start_time = safe_start
                zoom.end_time = shifted_end
                zoom.notes.append(f"facecam_zoom_smooth_shift_start={old:.3f}->{zoom.start_time:.3f}")
                zoom.touch()
                summary.shifted += 1
                summary.add_example(f"{zoom.segment_id} shifted {old:.2f}->{zoom.start_time:.2f}")
            else:
                self._remove(summary, "edge_blocked", zoom, "start_edge")
                return None

        if zoom.end_time > safe_end:
            old_end = zoom.end_time
            zoom.end_time = safe_end
            if zoom.duration < MIN_FACECAM_ZOOM_DURATION_SECONDS:
                zoom.end_time = old_end
                self._remove(summary, "edge_blocked", zoom, "end_edge")
                return None
            zoom.notes.append(f"facecam_zoom_smooth_trim_end={old_end:.3f}->{zoom.end_time:.3f}")
            zoom.touch()
            summary.shifted += 1
            summary.add_example(f"{zoom.segment_id} trimmed_end {old_end:.2f}->{zoom.end_time:.2f}")

        return zoom

    def _has_strong_reaction(
        self,
        zoom: ZoomInstruction,
        segment: TimelineSegment,
        facecam_reaction_result: FacecamReactionResult | None,
    ) -> bool:
        if zoom.intensity >= MIN_REACTION_SCORE_FOR_FACECAM_ZOOM:
            return True
        if facecam_reaction_result is None:
            return False
        return any(
            window.reaction_score >= MIN_REACTION_SCORE_FOR_FACECAM_ZOOM
            and self._overlaps(
                max(zoom.start_time, segment.start_time),
                min(zoom.end_time, segment.end_time),
                window.start_seconds,
                window.end_seconds,
            )
            for window in facecam_reaction_result.reaction_windows
        )

    def _stabilize_facecam_layouts(
        self,
        timeline: EditTimeline,
        reframe_plan: ReframePlan,
        facecam_reaction_result: FacecamReactionResult | None,
        summary: FacecamZoomSmoothnessSummary,
    ) -> None:
        segment_by_id = {segment.segment_id: segment for segment in timeline.selected_segments}
        for instruction in reframe_plan.instructions:
            if instruction.layout_kind != "facecam_emphasis":
                continue
            segment = segment_by_id.get(instruction.segment_id)
            if segment is None:
                continue
            if self._segment_has_strong_facecam_reaction(segment, facecam_reaction_result):
                continue
            instruction.focus_kind = "balanced"
            instruction.layout_kind = "balanced_split"
            instruction.crop_window = {"x": 0.5, "y": 0.0, "width": 0.5, "height": 1.0}
            instruction.notes.append("facecam_zoom_smooth_layout_stabilized")
            instruction.metadata["facecam_zoom_smoothness"] = {
                "converted_to": "balanced_split",
                "reason": "no_strong_facecam_reaction",
            }
            instruction.touch()
            summary.layout_converted += 1

    def _segment_has_strong_facecam_reaction(
        self,
        segment: TimelineSegment,
        facecam_reaction_result: FacecamReactionResult | None,
    ) -> bool:
        if facecam_reaction_result is None:
            return False
        return any(
            window.reaction_score >= MIN_REACTION_SCORE_FOR_FACECAM_ZOOM
            and self._overlaps(
                segment.start_time,
                segment.end_time,
                window.start_seconds,
                window.end_seconds,
            )
            for window in facecam_reaction_result.reaction_windows
        )

    def _remove(
        self,
        summary: FacecamZoomSmoothnessSummary,
        reason_counter: str,
        zoom: ZoomInstruction,
        reason: str,
    ) -> None:
        summary.removed += 1
        if reason_counter == "edge_blocked":
            summary.edge_blocked += 1
        elif reason_counter == "short_removed":
            summary.short_removed += 1
        elif reason_counter == "weak_reaction_removed":
            summary.weak_reaction_removed += 1
        summary.add_example(f"{zoom.segment_id} removed {reason} {zoom.start_time:.2f}-{zoom.end_time:.2f}")

    def _overlaps(
        self,
        start_a: float,
        end_a: float,
        start_b: float,
        end_b: float,
    ) -> bool:
        return max(start_a, start_b) < min(end_a, end_b)
