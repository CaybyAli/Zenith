from __future__ import annotations

from models.dynamic_edit_plan import DynamicEditPlan
from models.edit_timeline import EditTimeline
from models.music_cue_plan import MusicCuePlan
from models.reframe_plan import ReframePlan


class FinalEditIntegration:
    def _clamp(self, value: float) -> float:
        return round(max(0.0, min(1.0, float(value))), 3)

    def _timeline_start_time(self, timeline: EditTimeline) -> float:
        if not timeline.selected_segments:
            return 0.0
        return round(min(segment.start_time for segment in timeline.selected_segments), 3)

    def _timeline_end_time(self, timeline: EditTimeline) -> float:
        if not timeline.selected_segments:
            return 0.0
        return round(max(segment.end_time for segment in timeline.selected_segments), 3)

    def build(
        self,
        *,
        timeline: EditTimeline,
        reframe_plan: ReframePlan,
        dynamic_edit_plan: DynamicEditPlan,
        music_cue_plan: MusicCuePlan | None = None,
    ) -> dict[str, object]:
        music_plan_score = music_cue_plan.plan_score if music_cue_plan is not None else 0.0
        audio_cues_count = len(music_cue_plan.audio_cues) if music_cue_plan is not None else 0
        audio_mix_count = (
            len(music_cue_plan.audio_mix_instructions)
            if music_cue_plan is not None
            else 0
        )

        integration_score = self._clamp(
            (
                timeline.timeline_score * 0.35
                + reframe_plan.plan_score * 0.20
                + dynamic_edit_plan.plan_score * 0.30
                + music_plan_score * 0.15
            )
        )

        timeline_start_time = self._timeline_start_time(timeline)
        timeline_end_time = self._timeline_end_time(timeline)
        primary_focus_kind = (
            reframe_plan.instructions[0].focus_kind
            if reframe_plan.instructions
            else "unknown"
        )

        used_layers = ["timeline", "reframe", "dynamic"]
        if music_cue_plan is not None:
            used_layers.append("music")

        notes = [
            "Final edit package prepared from timeline, reframe and dynamic layers",
            "Renderer can consume this finish payload in later render integration steps",
        ]

        if music_cue_plan is not None:
            notes[0] = "Final edit package prepared from timeline, reframe, dynamic and music layers"
        else:
            notes.append("Music layer disabled for this channel")

        return {
            "timeline_id": timeline.timeline_id,
            "selected_segments": len(timeline.selected_segments),
            "hook_segment_id": timeline.hook_segment_id,
            "peak_segment_ids": list(timeline.peak_segment_ids),
            "payoff_segment_id": timeline.payoff_segment_id,
            "timeline_start_time": timeline_start_time,
            "timeline_end_time": timeline_end_time,
            "primary_focus_kind": primary_focus_kind,
            "render_strategy": "integrated_timeline_window",
            "reframe_instructions": len(reframe_plan.instructions),
            "reaction_moments": len(dynamic_edit_plan.reaction_moments),
            "zoom_instructions": len(dynamic_edit_plan.zoom_instructions),
            "audio_cues": audio_cues_count,
            "audio_mix_instructions": audio_mix_count,
            "music_enabled": music_cue_plan is not None,
            "integration_score": integration_score,
            "used_layers": used_layers,
            "notes": notes,
        }