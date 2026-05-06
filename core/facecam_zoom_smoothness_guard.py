from __future__ import annotations

from dataclasses import dataclass, field

from models.dynamic_edit_plan import DynamicEditPlan
from models.edit_timeline import EditTimeline
from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.cut_indicator import CutIndicator, CutIndicatorResult
from models.facecam_reaction_result import FacecamReactionResult
from models.reframe_plan import ReframePlan
from models.timeline_segment import TimelineSegment
from models.zoom_instruction import ZoomInstruction


ZOOM_EDGE_BUFFER_SECONDS = 1.00
FACE_CAM_EDGE_SAFE_SECONDS = ZOOM_EDGE_BUFFER_SECONDS
MIN_FACECAM_ZOOM_DURATION_SECONDS = 1.40
MIN_VERY_STRONG_ZOOM_DURATION_SECONDS = 0.80
MIN_REACTION_SCORE_FOR_FACECAM_ZOOM = 0.70
VERY_STRONG_REACTION_SCORE_FOR_SHORT_ZOOM = 0.85
FACECAM_ZOOM_SMOOTH_BUFFER_SECONDS = 0.80
MAX_POST_ACTION_ZOOM_TAIL_SECONDS = 1.20

_MEANINGFUL_AUDIO_ROLES = frozenset({
    "speech_active",
    "secondary_speech_like",
    "shout_like_audio",
    "group_reaction_like",
    "laugh_like_audio",
})
_ACTION_TAIL_TYPES = frozenset({
    "high_action_burst",
    "goal_or_save_like_flash",
    "group_reaction_like",
})
_MEANINGFUL_INDICATOR_TYPES = frozenset({
    "shout_like_audio",
    "group_reaction_like",
    "laugh_like_audio",
    "hook_sentence",
    "facecam_reaction_spike",
    "high_action_burst",
    "goal_or_save_like_flash",
})
_BAD_WAIT_STATES = frozenset({
    "menu_wait",
    "low_motion_wait",
    "possible_dead_time_after_goal",
    "round_end",
    "replay_like",
    "scoreboard_like",
})
_GOOD_ACTION_STATES = frozenset({
    "active_gameplay",
    "high_motion_action",
    "possible_goal_or_flash",
    "possible_pre_action_context",
})


@dataclass
class FacecamZoomSmoothnessSummary:
    removed: int = 0
    shifted: int = 0
    edge_blocked: int = 0
    short_removed: int = 0
    weak_reaction_removed: int = 0
    silence_removed: int = 0
    tail_trimmed: int = 0
    smooth_buffer_removed: int = 0
    layout_converted: int = 0
    state_zoom_removed: int = 0
    state_zoom_trimmed: int = 0
    state_zoom_protected: int = 0
    zoom_edge_hard_dropped: int = 0
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
        audio_role_result: AudioRoleResult | None = None,
        cut_indicator_result: CutIndicatorResult | None = None,
        reframe_plan: ReframePlan | None = None,
        gameplay_state_result=None,
    ) -> FacecamZoomSmoothnessSummary:
        summary = FacecamZoomSmoothnessSummary()
        raw_zoom_count = len(dynamic_edit_plan.zoom_instructions)
        segment_by_id = {
            segment.segment_id: segment
            for segment in timeline.selected_segments
            if segment.end_time > segment.start_time
        }
        audio_windows = self._audio_windows(audio_role_result)
        indicators = self._indicators(cut_indicator_result)
        state_windows = self._state_windows(gameplay_state_result)

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
                audio_windows,
                indicators,
                state_windows,
                summary,
            )
            if adjusted is not None:
                kept.append(adjusted)

        kept = self._enforce_smooth_buffer(kept, summary)
        dynamic_edit_plan.zoom_instructions = kept
        dynamic_edit_plan.plan_notes.append(
            "Facecam zoom smoothness: "
            f"removed={summary.removed} "
            f"shifted={summary.shifted} "
            f"edge_blocked={summary.edge_blocked} "
            f"short_removed={summary.short_removed} "
            f"weak_reaction_removed={summary.weak_reaction_removed} "
            f"silence_removed={summary.silence_removed} "
            f"tail_trimmed={summary.tail_trimmed} "
            f"state_zoom_removed={summary.state_zoom_removed} "
            f"state_zoom_trimmed={summary.state_zoom_trimmed} "
            f"state_zoom_protected={summary.state_zoom_protected} "
            f"zoom_edge_hard_dropped={summary.zoom_edge_hard_dropped}"
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
            f"[ZOOM-EDGE] dropped {summary.edge_blocked} of {raw_zoom_count} "
            f"zoom instructions (edge buffer {ZOOM_EDGE_BUFFER_SECONDS:.1f}s)"
        )
        print(
            "[FACECAM-ZOOM-SMOOTHNESS] "
            f"removed={summary.removed} "
            f"shifted={summary.shifted} "
            f"edge_blocked={summary.edge_blocked} "
            f"short_removed={summary.short_removed} "
            f"weak_reaction_removed={summary.weak_reaction_removed} "
            f"silence_removed={summary.silence_removed} "
            f"tail_trimmed={summary.tail_trimmed}"
        )
        if summary.examples:
            print(f"[FACECAM-ZOOM-SMOOTHNESS] examples={'; '.join(summary.examples)}")

        return summary

    def _guard_zoom(
        self,
        zoom: ZoomInstruction,
        segment: TimelineSegment,
        facecam_reaction_result: FacecamReactionResult | None,
        audio_windows: list[AudioRoleWindow],
        indicators: list[CutIndicator],
        state_windows: list[object],
        summary: FacecamZoomSmoothnessSummary,
    ) -> ZoomInstruction | None:
        zoom.start_time = round(max(segment.start_time, zoom.start_time), 3)
        zoom.end_time = round(min(segment.end_time, zoom.end_time), 3)

        if zoom.end_time <= zoom.start_time:
            self._remove(summary, "edge_blocked", zoom, "outside_segment")
            return None

        safe_start = round(segment.start_time + FACE_CAM_EDGE_SAFE_SECONDS, 3)
        safe_end = round(segment.end_time - FACE_CAM_EDGE_SAFE_SECONDS, 3)
        if safe_end <= safe_start:
            self._remove(summary, "edge_blocked", zoom, "segment_too_short_for_safe_zoom")
            summary.zoom_edge_hard_dropped += 1
            return None
        if zoom.start_time < safe_start:
            self._remove(summary, "edge_blocked", zoom, "start_edge")
            summary.zoom_edge_hard_dropped += 1
            return None
        if zoom.end_time > safe_end:
            self._remove(summary, "edge_blocked", zoom, "end_edge")
            summary.zoom_edge_hard_dropped += 1
            return None

        if self._state_protects_zoom(zoom, state_windows, audio_windows, indicators):
            summary.state_zoom_protected += 1
        elif self._remove_or_trim_wait_state_zoom(zoom, state_windows, summary):
            return None

        if not self._has_strong_reaction(zoom, segment, facecam_reaction_result):
            self._remove(summary, "weak_reaction_removed", zoom, "weak_reaction")
            return None

        if not self._has_meaningful_audio_or_reaction(
            zoom,
            facecam_reaction_result,
            audio_windows,
            indicators,
        ):
            self._remove(summary, "silence_removed", zoom, "silence_or_no_statement")
            return None

        if (
            zoom.duration < MIN_FACECAM_ZOOM_DURATION_SECONDS
            and zoom.intensity < VERY_STRONG_REACTION_SCORE_FOR_SHORT_ZOOM
        ):
            self._remove(summary, "short_removed", zoom, "short_zoom")
            return None
        if zoom.duration < MIN_VERY_STRONG_ZOOM_DURATION_SECONDS:
            self._remove(summary, "short_removed", zoom, "very_short_zoom")
            return None

        self._trim_post_action_tail(zoom, indicators, audio_windows, facecam_reaction_result, summary)
        if (
            zoom.duration < MIN_FACECAM_ZOOM_DURATION_SECONDS
            and zoom.intensity < VERY_STRONG_REACTION_SCORE_FOR_SHORT_ZOOM
        ):
            self._remove(summary, "short_removed", zoom, "short_after_tail_trim")
            return None

        return zoom

    def _remove_or_trim_wait_state_zoom(
        self,
        zoom: ZoomInstruction,
        state_windows: list[object],
        summary: FacecamZoomSmoothnessSummary,
    ) -> bool:
        if not state_windows or zoom.duration <= 0:
            return False
        bad = self._state_overlap_windows(zoom.start_time, zoom.end_time, state_windows, _BAD_WAIT_STATES)
        bad_overlap = sum(end - start for start, end in bad)
        if bad_overlap <= 0:
            return False
        bad_ratio = bad_overlap / max(zoom.duration, 0.001)
        if bad_ratio >= 0.50:
            self._remove(summary, "state_zoom_removed", zoom, f"gameplay_state_wait {bad_ratio:.2f}")
            return True
        changed = False
        for start, end in bad:
            if start <= zoom.start_time + 0.1:
                proposed_start = round(end, 3)
                if zoom.end_time - proposed_start >= MIN_FACECAM_ZOOM_DURATION_SECONDS:
                    old = zoom.start_time
                    zoom.start_time = proposed_start
                    zoom.notes.append(f"state_zoom_trim_start={old:.3f}->{zoom.start_time:.3f}")
                    summary.state_zoom_trimmed += 1
                    summary.removed += 0
                    changed = True
            if end >= zoom.end_time - 0.1:
                proposed_end = round(start, 3)
                if proposed_end - zoom.start_time >= MIN_FACECAM_ZOOM_DURATION_SECONDS:
                    old = zoom.end_time
                    zoom.end_time = proposed_end
                    zoom.notes.append(f"state_zoom_trim_end={old:.3f}->{zoom.end_time:.3f}")
                    summary.state_zoom_trimmed += 1
                    changed = True
        if changed:
            zoom.touch()
            summary.add_example(f"{zoom.segment_id} state_zoom_trimmed {zoom.start_time:.2f}-{zoom.end_time:.2f}")
        if zoom.duration < MIN_FACECAM_ZOOM_DURATION_SECONDS:
            self._remove(summary, "state_zoom_removed", zoom, "state_trim_too_short")
            return True
        return False

    def _state_protects_zoom(
        self,
        zoom: ZoomInstruction,
        state_windows: list[object],
        audio_windows: list[AudioRoleWindow],
        indicators: list[CutIndicator],
    ) -> bool:
        good_overlap = sum(
            end - start
            for start, end in self._state_overlap_windows(
                zoom.start_time,
                zoom.end_time,
                state_windows,
                _GOOD_ACTION_STATES,
            )
        )
        if good_overlap / max(zoom.duration, 0.001) < 0.20:
            return False
        return self._has_reaction_audio_or_indicator(zoom.start_time, zoom.end_time, audio_windows, indicators)

    def _has_reaction_audio_or_indicator(
        self,
        start: float,
        end: float,
        audio_windows: list[AudioRoleWindow],
        indicators: list[CutIndicator],
    ) -> bool:
        return any(
            window.role_type in {"shout_like_audio", "group_reaction_like", "laugh_like_audio"}
            and self._overlap_seconds(start, end, window.start_seconds, window.end_seconds) >= 0.2
            for window in audio_windows
        ) or any(
            indicator.indicator_type in {"shout_like_audio", "group_reaction_like", "laugh_like_audio"}
            and self._overlap_seconds(start, end, indicator.start_seconds, indicator.end_seconds) >= 0.2
            for indicator in indicators
        )

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

    def _has_meaningful_audio_or_reaction(
        self,
        zoom: ZoomInstruction,
        facecam_reaction_result: FacecamReactionResult | None,
        audio_windows: list[AudioRoleWindow],
        indicators: list[CutIndicator],
    ) -> bool:
        if facecam_reaction_result is not None and any(
            window.reaction_score >= MIN_REACTION_SCORE_FOR_FACECAM_ZOOM
            and self._overlap_seconds(
                zoom.start_time,
                zoom.end_time,
                window.start_seconds,
                window.end_seconds,
            ) >= 0.2
            for window in facecam_reaction_result.reaction_windows
        ):
            return True

        has_audio_context = bool(audio_windows)
        if any(
            window.role_type in _MEANINGFUL_AUDIO_ROLES
            and window.score >= 0.55
            and self._overlap_seconds(
                zoom.start_time,
                zoom.end_time,
                window.start_seconds,
                window.end_seconds,
            ) >= 0.25
            for window in audio_windows
        ):
            return True

        if any(
            indicator.indicator_type in _MEANINGFUL_INDICATOR_TYPES
            and indicator.score >= 0.55
            and self._overlap_seconds(
                zoom.start_time,
                zoom.end_time,
                indicator.start_seconds,
                indicator.end_seconds,
            ) >= 0.2
            for indicator in indicators
        ):
            return True

        if has_audio_context or indicators or facecam_reaction_result is not None:
            return False
        return zoom.intensity >= MIN_REACTION_SCORE_FOR_FACECAM_ZOOM

    def _trim_post_action_tail(
        self,
        zoom: ZoomInstruction,
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        facecam_reaction_result: FacecamReactionResult | None,
        summary: FacecamZoomSmoothnessSummary,
    ) -> None:
        action_windows = [
            indicator
            for indicator in indicators
            if indicator.indicator_type in _ACTION_TAIL_TYPES
            and self._overlap_seconds(
                zoom.start_time,
                zoom.end_time,
                indicator.start_seconds,
                indicator.end_seconds,
            ) > 0.0
        ]
        if not action_windows:
            return
        action_end = max(indicator.end_seconds for indicator in action_windows)
        tail_limit = round(action_end + MAX_POST_ACTION_ZOOM_TAIL_SECONDS, 3)
        if zoom.end_time <= tail_limit:
            return
        if self._has_meaningful_context_after(
            action_end,
            zoom.end_time,
            audio_windows,
            indicators,
            facecam_reaction_result,
        ):
            return
        old_end = zoom.end_time
        zoom.end_time = max(zoom.start_time, tail_limit)
        zoom.notes.append(f"facecam_zoom_tail_trimmed={old_end:.3f}->{zoom.end_time:.3f}")
        zoom.touch()
        summary.tail_trimmed += 1
        summary.add_example(f"{zoom.segment_id} tail_trim {old_end:.2f}->{zoom.end_time:.2f}")

    def _has_meaningful_context_after(
        self,
        start: float,
        end: float,
        audio_windows: list[AudioRoleWindow],
        indicators: list[CutIndicator],
        facecam_reaction_result: FacecamReactionResult | None,
    ) -> bool:
        return any(
            window.role_type in _MEANINGFUL_AUDIO_ROLES
            and window.score >= 0.55
            and self._overlap_seconds(start, end, window.start_seconds, window.end_seconds) >= 0.25
            for window in audio_windows
        ) or any(
            indicator.indicator_type in _MEANINGFUL_INDICATOR_TYPES
            and indicator.score >= 0.55
            and indicator.indicator_type not in _ACTION_TAIL_TYPES
            and self._overlap_seconds(start, end, indicator.start_seconds, indicator.end_seconds) >= 0.2
            for indicator in indicators
        ) or (
            facecam_reaction_result is not None
            and any(
                window.reaction_score >= MIN_REACTION_SCORE_FOR_FACECAM_ZOOM
                and self._overlap_seconds(start, end, window.start_seconds, window.end_seconds) >= 0.2
                for window in facecam_reaction_result.reaction_windows
            )
        )

    def _enforce_smooth_buffer(
        self,
        zooms: list[ZoomInstruction],
        summary: FacecamZoomSmoothnessSummary,
    ) -> list[ZoomInstruction]:
        kept: list[ZoomInstruction] = []
        for zoom in sorted(zooms, key=lambda item: (item.segment_id, item.start_time, item.end_time)):
            if not kept or kept[-1].segment_id != zoom.segment_id:
                kept.append(zoom)
                continue
            previous = kept[-1]
            gap = round(zoom.start_time - previous.end_time, 3)
            if gap >= FACECAM_ZOOM_SMOOTH_BUFFER_SECONDS:
                kept.append(zoom)
                continue
            weaker = zoom if zoom.intensity <= previous.intensity else previous
            stronger = previous if weaker is zoom else zoom
            if weaker is previous:
                kept[-1] = stronger
            summary.removed += 1
            summary.smooth_buffer_removed += 1
            summary.add_example(
                f"{weaker.segment_id} removed smooth_buffer {weaker.start_time:.2f}-{weaker.end_time:.2f}"
            )
        return kept

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
        elif reason_counter == "silence_removed":
            summary.silence_removed += 1
        elif reason_counter == "state_zoom_removed":
            summary.state_zoom_removed += 1
        summary.add_example(f"{zoom.segment_id} removed {reason} {zoom.start_time:.2f}-{zoom.end_time:.2f}")

    def _audio_windows(self, result: AudioRoleResult | None) -> list[AudioRoleWindow]:
        if result is None:
            return []
        return sorted(
            (window for window in result.windows if window.end_seconds > window.start_seconds),
            key=lambda window: (window.start_seconds, window.end_seconds),
        )

    def _indicators(self, result: CutIndicatorResult | None) -> list[CutIndicator]:
        if result is None:
            return []
        return sorted(
            (indicator for indicator in result.indicators if indicator.end_seconds > indicator.start_seconds),
            key=lambda indicator: (indicator.start_seconds, indicator.end_seconds),
        )

    def _overlaps(
        self,
        start_a: float,
        end_a: float,
        start_b: float,
        end_b: float,
    ) -> bool:
        return max(start_a, start_b) < min(end_a, end_b)

    def _overlap_seconds(
        self,
        start_a: float,
        end_a: float,
        start_b: float,
        end_b: float,
    ) -> float:
        return max(0.0, min(end_a, end_b) - max(start_a, start_b))

    def _state_overlap_windows(
        self,
        start: float,
        end: float,
        state_windows: list[object],
        state_types: frozenset[str] | set[str],
    ) -> list[tuple[float, float]]:
        windows: list[tuple[float, float]] = []
        for state in state_windows:
            if self._state_type(state) not in state_types:
                continue
            overlap_start = max(start, self._state_start(state))
            overlap_end = min(end, self._state_end(state))
            if overlap_end > overlap_start:
                windows.append((overlap_start, overlap_end))
        return _merge_windows(windows)

    def _state_windows(self, result) -> list[object]:
        if result is None:
            return []
        windows = result.get("windows", []) if isinstance(result, dict) else getattr(result, "windows", [])
        return sorted(
            [window for window in windows or [] if self._state_end(window) > self._state_start(window)],
            key=lambda window: (self._state_start(window), self._state_end(window), self._state_type(window)),
        )

    def _state_type(self, state: object) -> str:
        return str(state.get("state_type", "") if isinstance(state, dict) else getattr(state, "state_type", ""))

    def _state_start(self, state: object) -> float:
        value = state.get("start_seconds", 0.0) if isinstance(state, dict) else getattr(state, "start_seconds", 0.0)
        return float(value or 0.0)

    def _state_end(self, state: object) -> float:
        value = state.get("end_seconds", 0.0) if isinstance(state, dict) else getattr(state, "end_seconds", 0.0)
        return float(value or 0.0)


def _merge_windows(windows: list[tuple[float, float]]) -> list[tuple[float, float]]:
    merged: list[tuple[float, float]] = []
    for start, end in sorted(windows):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
            continue
        previous_start, previous_end = merged[-1]
        merged[-1] = (previous_start, max(previous_end, end))
    return merged
