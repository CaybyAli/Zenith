from __future__ import annotations

from dataclasses import dataclass, field

from models.highlight_candidate import HighlightCandidate
from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.cut_indicator import CutIndicator, CutIndicatorResult
from models.round_phase_result import RoundPhase, RoundPhaseResult
from models.timeline_segment import TimelineSegment


PRE_ACTION_CONTEXT_SECONDS = 1.50
PRE_SHOUT_CONTEXT_SECONDS = 1.20
PRE_GOAL_CONTEXT_SECONDS = 1.50
STRONG_ACTION_CONTEXT_SECONDS = 2.00
MAX_PRE_CONTEXT_EXPAND_SECONDS = 2.00
ACTION_BACKFILL_MIN_SECONDS = 2.00
ACTION_BACKFILL_MAX_SECONDS = 4.00
ACTION_BACKFILL_STEP_SECONDS = 0.25
BACKFILL_STOP_OFFSET_SECONDS = 0.10
MIN_SEGMENT_DURATION_SECONDS = 2.5
MIN_GAP_SECONDS = 0.15

_ACTION_TYPES = frozenset({
    "high_action_burst",
    "sustained_action",
    "facecam_reaction_spike",
})
_GOAL_TYPES = frozenset({"goal_or_save_like_flash"})
_SHOUT_TYPES = frozenset({"shout_like_audio", "group_reaction_like"})
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
_STATE_CONTEXT_SECONDS = {
    "possible_goal_or_flash": 3.0,
    "high_motion_action": 2.0,
    "possible_pre_action_context": 2.5,
    "active_gameplay": 1.5,
}
MAX_STATE_BACKFILL_DURATION = {
    "build": 28.0,
    "bridge": 28.0,
    "peak": 35.0,
    "payoff": 35.0,
}


@dataclass
class PreActionContextSummary:
    expanded: int = 0
    shout: int = 0
    goal: int = 0
    action: int = 0
    strong_action_context: int = 0
    smart_backfilled: int = 0
    silence_stop: int = 0
    boundary_stop: int = 0
    phase_stop: int = 0
    skipped_overlap: int = 0
    skipped_silence: int = 0
    gameplay_state_backfilled: int = 0
    goal_state_backfilled: int = 0
    action_state_backfilled: int = 0
    skipped_state_silence: int = 0
    skipped_state_overlap: int = 0
    duration_before: float = 0.0
    duration_after: float = 0.0
    examples: list[str] = field(default_factory=list)

    def add_example(self, text: str) -> None:
        if len(self.examples) < 6:
            self.examples.append(text)


class PreActionContextGuard:
    engine = "pre-action-context-guard-v1"

    def apply(
        self,
        segments: list[TimelineSegment],
        *,
        cut_indicator_result: CutIndicatorResult | None = None,
        audio_role_result: AudioRoleResult | None = None,
        weak_zones: list[HighlightCandidate] | None = None,
        round_phase_result: RoundPhaseResult | None = None,
        gameplay_state_result=None,
    ) -> tuple[list[TimelineSegment], PreActionContextSummary]:
        ordered = sorted(
            (segment for segment in segments if segment.end_time > segment.start_time),
            key=lambda segment: (segment.start_time, segment.end_time, segment.segment_id),
        )
        summary = PreActionContextSummary(
            duration_before=round(sum(segment.duration for segment in ordered), 3)
        )
        indicators = self._indicators(cut_indicator_result)
        audio_windows = self._audio_windows(audio_role_result)
        silence_zones = self._silence_zones(weak_zones)
        state_windows = self._state_windows(gameplay_state_result)

        self._apply_gameplay_state_backfill(
            ordered,
            state_windows,
            audio_windows,
            silence_zones,
            summary,
        )

        for index, segment in enumerate(ordered):
            previous = ordered[index - 1] if index > 0 else None
            trigger = self._trigger_near_start(segment, indicators)
            if trigger is None and segment.segment_role not in {"hook", "peak"}:
                continue
            if trigger is None and not indicators and not audio_windows:
                continue

            if trigger is not None:
                context_seconds, trigger_kind = self._context_for_trigger(trigger)
            else:
                context_seconds, trigger_kind = ACTION_BACKFILL_MAX_SECONDS, segment.segment_role
            if segment.segment_role in {"hook", "peak"} or trigger_kind in {"shout", "goal", "strong_action"}:
                context_seconds = max(context_seconds, ACTION_BACKFILL_MAX_SECONDS)
            context_seconds = min(max(context_seconds, ACTION_BACKFILL_MIN_SECONDS), ACTION_BACKFILL_MAX_SECONDS)
            previous_limit = round(previous.end_time + MIN_GAP_SECONDS, 3) if previous else 0.0
            preferred, stop_reason = self._smart_backfill_start(
                segment,
                previous_limit,
                context_seconds,
                silence_zones,
                round_phase_result,
            )

            if preferred < previous_limit:
                summary.skipped_overlap += 1
                segment.notes.append("pre_action_context_skipped_overlap")
                continue

            if preferred >= segment.start_time:
                continue
            if preferred > round(segment.start_time - ACTION_BACKFILL_MIN_SECONDS, 3):
                segment.notes.append("pre_action_context_skipped_min_backfill")
                continue
            if segment.end_time - preferred < MIN_SEGMENT_DURATION_SECONDS:
                continue
            if self._has_blocking_silence(preferred, segment.start_time, audio_windows):
                summary.skipped_silence += 1
                segment.notes.append("pre_action_context_skipped_silence")
                continue

            old = segment.start_time
            segment.start_time = preferred
            segment.notes.append(
                f"pre_action_context_{trigger_kind}={old:.3f}->{segment.start_time:.3f}:{stop_reason}"
            )
            segment.touch()
            summary.expanded += 1
            summary.smart_backfilled += 1
            if stop_reason == "silence_stop":
                summary.silence_stop += 1
            elif stop_reason == "boundary_stop":
                summary.boundary_stop += 1
            elif stop_reason == "phase_stop":
                summary.phase_stop += 1
            if trigger_kind == "shout":
                summary.shout += 1
            elif trigger_kind == "goal":
                summary.goal += 1
            elif trigger_kind == "strong_action":
                summary.strong_action_context += 1
                summary.action += 1
            else:
                summary.action += 1
            summary.add_example(
                f"{segment.segment_id} {trigger_kind} start {old:.2f}->{segment.start_time:.2f}"
            )
            print(
                "[BACKFILL] "
                f"highlight @{old:.1f}s extended start {old:.1f} -> {segment.start_time:.1f} "
                f"({stop_reason})"
            )

        ordered = self._cleanup(ordered)
        summary.duration_after = round(sum(segment.duration for segment in ordered), 3)
        print(
            "[TIMELINE-PRE-ACTION-CONTEXT] "
            f"expanded={summary.expanded} "
            f"shout={summary.shout} "
            f"goal={summary.goal} "
            f"action={summary.action} "
            f"strong_action_context={summary.strong_action_context} "
            f"smart_backfilled={summary.smart_backfilled} "
            f"silence_stop={summary.silence_stop} "
            f"boundary_stop={summary.boundary_stop} "
            f"phase_stop={summary.phase_stop} "
            f"skipped_overlap={summary.skipped_overlap} "
            f"skipped_silence={summary.skipped_silence} "
            f"gameplay_state_backfilled={summary.gameplay_state_backfilled} "
            f"goal_state_backfilled={summary.goal_state_backfilled} "
            f"action_state_backfilled={summary.action_state_backfilled} "
            f"skipped_state_silence={summary.skipped_state_silence} "
            f"skipped_state_overlap={summary.skipped_state_overlap} "
            f"duration_before={summary.duration_before:.3f}s "
            f"duration_after={summary.duration_after:.3f}s"
        )
        if summary.examples:
            print(f"[TIMELINE-PRE-ACTION-CONTEXT] examples={'; '.join(summary.examples)}")
        return ordered, summary

    def _apply_gameplay_state_backfill(
        self,
        ordered: list[TimelineSegment],
        state_windows: list[object],
        audio_windows: list[AudioRoleWindow],
        silence_zones: list[tuple[float, float]],
        summary: PreActionContextSummary,
    ) -> None:
        if not state_windows:
            return

        for index, segment in enumerate(ordered):
            previous = ordered[index - 1] if index > 0 else None
            previous_limit = round(previous.end_time + MIN_GAP_SECONDS, 3) if previous else 0.0
            state = self._state_trigger_near_start(segment, state_windows)
            if state is None:
                continue

            state_type = self._state_type(state)
            context_seconds = _STATE_CONTEXT_SECONDS[state_type]
            preferred = round(max(0.0, self._state_start(state) - context_seconds), 3)
            preferred = max(preferred, previous_limit)

            if preferred >= segment.start_time:
                continue
            if preferred > previous_limit and previous is not None and preferred < previous_limit:
                summary.skipped_state_overlap += 1
                continue
            if preferred == previous_limit and previous is not None and previous_limit > self._state_start(state) - context_seconds:
                summary.skipped_state_overlap += 1
            if self._bad_state_or_silence_dominates(preferred, segment.start_time, state_windows, audio_windows, silence_zones):
                summary.skipped_state_silence += 1
                segment.notes.append("pre_action_state_backfill_skipped_wait_or_silence")
                continue

            max_duration = MAX_STATE_BACKFILL_DURATION.get(segment.segment_role, 28.0)
            if segment.end_time - preferred > max_duration:
                preferred = round(max(segment.start_time - context_seconds, segment.end_time - max_duration, previous_limit), 3)
                if preferred >= segment.start_time:
                    continue
            if segment.end_time - preferred < MIN_SEGMENT_DURATION_SECONDS:
                continue

            old = segment.start_time
            segment.start_time = preferred
            segment.notes.append(f"pre_action_state_{state_type}={old:.3f}->{preferred:.3f}")
            segment.touch()
            summary.expanded += 1
            summary.gameplay_state_backfilled += 1
            if state_type == "possible_goal_or_flash":
                summary.goal_state_backfilled += 1
                summary.goal += 1
            else:
                summary.action_state_backfilled += 1
                summary.action += 1
            summary.add_example(f"{segment.segment_id} state_{state_type} start {old:.2f}->{preferred:.2f}")

    def _smart_backfill_start(
        self,
        segment: TimelineSegment,
        previous_limit: float,
        context_seconds: float,
        silence_zones: list[tuple[float, float]],
        round_phase_result,
    ) -> tuple[float, str]:
        target = round(max(0.0, segment.start_time - context_seconds), 3)
        preferred = max(target, previous_limit)
        stop_reason = "max_backfill"
        if preferred > target:
            stop_reason = "boundary_stop"

        cursor = segment.start_time
        lower_bound = target
        while cursor > lower_bound:
            window_start = max(lower_bound, round(cursor - ACTION_BACKFILL_STEP_SECONDS, 3))
            silence = self._overlapping_window(window_start, cursor, silence_zones)
            if silence is not None:
                preferred = round(min(segment.start_time, silence[1] + BACKFILL_STOP_OFFSET_SECONDS), 3)
                stop_reason = "silence_stop"
                break
            phase = self._blocking_round_phase(window_start, cursor, round_phase_result)
            if phase is not None:
                preferred = round(min(segment.start_time, phase.end_seconds + BACKFILL_STOP_OFFSET_SECONDS), 3)
                stop_reason = "phase_stop"
                break
            cursor = window_start

        return preferred, stop_reason

    def _trigger_near_start(
        self,
        segment: TimelineSegment,
        indicators: list[CutIndicator],
    ) -> CutIndicator | None:
        candidates = [
            indicator
            for indicator in indicators
            if indicator.indicator_type in (_ACTION_TYPES | _GOAL_TYPES | _SHOUT_TYPES)
            and indicator.score >= 0.55
            and indicator.start_seconds <= segment.start_time + 0.45
            and indicator.end_seconds >= segment.start_time - 2.0
        ]
        if not candidates:
            return None
        priority = {
            "shout_like_audio": 0,
            "group_reaction_like": 0,
            "goal_or_save_like_flash": 1,
            "high_action_burst": 2,
            "sustained_action": 2,
            "facecam_reaction_spike": 2,
        }
        return sorted(
            candidates,
            key=lambda item: (priority.get(item.indicator_type, 3), item.start_seconds),
        )[0]

    def _context_for_trigger(self, indicator: CutIndicator) -> tuple[float, str]:
        if indicator.indicator_type in _SHOUT_TYPES:
            return PRE_SHOUT_CONTEXT_SECONDS, "shout"
        if indicator.indicator_type in _GOAL_TYPES:
            return PRE_GOAL_CONTEXT_SECONDS, "goal"
        if indicator.score >= 0.85:
            return STRONG_ACTION_CONTEXT_SECONDS, "strong_action"
        return PRE_ACTION_CONTEXT_SECONDS, "action"

    def _has_blocking_silence(
        self,
        start: float,
        end: float,
        audio_windows: list[AudioRoleWindow],
    ) -> bool:
        return any(
            window.role_type == "silence_or_dead_air"
            and window.score >= 0.65
            and _overlap_seconds(start, end, window.start_seconds, window.end_seconds) > 0.35
            for window in audio_windows
        )

    def _cleanup(self, segments: list[TimelineSegment]) -> list[TimelineSegment]:
        kept: list[TimelineSegment] = []
        for segment in sorted(segments, key=lambda item: (item.start_time, item.end_time, item.segment_id)):
            if segment.end_time <= segment.start_time:
                continue
            if segment.duration < MIN_SEGMENT_DURATION_SECONDS and segment.segment_role not in {"hook", "peak", "payoff"}:
                continue
            if kept:
                required = round(kept[-1].end_time + MIN_GAP_SECONDS, 3)
                if segment.start_time < required:
                    if segment.end_time - required < MIN_SEGMENT_DURATION_SECONDS:
                        continue
                    segment.start_time = required
                    segment.touch()
            segment.start_time = round(max(0.0, segment.start_time), 3)
            segment.end_time = round(segment.end_time, 3)
            kept.append(segment)
        return kept

    def _indicators(self, result: CutIndicatorResult | None) -> list[CutIndicator]:
        if result is None:
            return []
        return sorted(
            (indicator for indicator in result.indicators if indicator.end_seconds > indicator.start_seconds),
            key=lambda indicator: (indicator.start_seconds, indicator.end_seconds),
        )

    def _audio_windows(self, result: AudioRoleResult | None) -> list[AudioRoleWindow]:
        if result is None:
            return []
        return sorted(
            (window for window in result.windows if window.end_seconds > window.start_seconds),
            key=lambda window: (window.start_seconds, window.end_seconds),
        )

    def _silence_zones(self, weak_zones: list[HighlightCandidate] | None) -> list[tuple[float, float]]:
        zones: list[tuple[float, float]] = []
        for zone in weak_zones or []:
            text = " ".join([zone.candidate_kind, zone.source or "", *zone.notes, *zone.signal_tags]).lower()
            if "silence" not in text:
                continue
            if zone.end_time > zone.start_time:
                zones.append((zone.start_time, zone.end_time))
        return sorted(zones)

    def _overlapping_window(
        self,
        start: float,
        end: float,
        windows: list[tuple[float, float]],
    ) -> tuple[float, float] | None:
        for window_start, window_end in windows:
            if max(start, window_start) < min(end, window_end):
                return window_start, window_end
        return None

    def _blocking_round_phase(
        self,
        start: float,
        end: float,
        round_phase_result: RoundPhaseResult | None,
    ):
        if round_phase_result is None:
            return None
        blocked = {RoundPhase.ROUND_END, RoundPhase.MENU_WAIT, RoundPhase.QUEUE_WAIT}
        for phase in round_phase_result.windows:
            if phase.phase not in blocked:
                continue
            if max(start, phase.start_seconds) < min(end, phase.end_seconds):
                return phase
        return None

    def _state_trigger_near_start(self, segment: TimelineSegment, state_windows: list[object]) -> object | None:
        candidates = [
            state for state in state_windows
            if self._state_type(state) in _GOOD_ACTION_STATES
            and 0.0 <= segment.start_time - self._state_start(state) <= 1.0
        ]
        if not candidates:
            return None
        priority = {
            "possible_goal_or_flash": 0,
            "high_motion_action": 1,
            "possible_pre_action_context": 2,
            "active_gameplay": 3,
        }
        return sorted(candidates, key=lambda state: (priority.get(self._state_type(state), 9), self._state_start(state)))[0]

    def _bad_state_or_silence_dominates(
        self,
        start: float,
        end: float,
        state_windows: list[object],
        audio_windows: list[AudioRoleWindow],
        silence_zones: list[tuple[float, float]],
    ) -> bool:
        duration = max(0.001, end - start)
        bad_state = sum(
            _overlap_seconds(start, end, self._state_start(state), self._state_end(state))
            for state in state_windows
            if self._state_type(state) in _BAD_WAIT_STATES
        )
        audio_silence = sum(
            _overlap_seconds(start, end, window.start_seconds, window.end_seconds)
            for window in audio_windows
            if window.role_type == "silence_or_dead_air" and window.score >= 0.65
        )
        weak_silence = sum(
            _overlap_seconds(start, end, zone_start, zone_end)
            for zone_start, zone_end in silence_zones
        )
        return (bad_state + audio_silence + weak_silence) / duration >= 0.50

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


def _overlap_seconds(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))
