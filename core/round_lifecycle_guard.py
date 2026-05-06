from __future__ import annotations

from dataclasses import dataclass, field

from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.cut_indicator import CutIndicator, CutIndicatorResult
from models.gameplay_state_result import GameplayStateResult, GameplayStateWindow
from models.round_phase_result import RoundPhaseResult, RoundPhaseWindow
from models.sentence_timeline import SentenceTimelineResult
from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult

ENGINE = "round-lifecycle-guard-v1"

MIN_SEGMENT_DURATION = 2.5
BORING_MIN_DURATION = 1.5
PRE_GOAL_PROTECT_FULL = 2.0
PRE_GOAL_PROTECT_BURST = 1.5
POST_GOAL_PROTECT = 2.0
POST_GOAL_REACTION_EXTEND = 0.7
TRUE_ROUND_START_LOOKAHEAD = 12.0
TRUE_ROUND_START_PREROLL = 2.0
MENU_WAIT_DOMINANT_RATIO = 0.65
MENU_FORCE_REMOVE_RATIO = 0.85
ACTION_GUARD_RATIO = 0.20

_WAIT_STATES = frozenset({
    "menu_wait",
    "queue_wait",
    "low_motion_wait",
    "possible_dead_time_after_goal",
})
_ACTION_STATES = frozenset({
    "active_gameplay",
    "high_motion_action",
    "possible_goal_or_flash",
    "possible_pre_action_context",
})
_GOAL_STATES = frozenset({
    "goal_or_save_like_flash",
    "possible_goal_or_flash",
})
_TRUE_ROUND_START_STATES = frozenset({
    "active_gameplay",
    "high_motion_action",
    "possible_goal_or_flash",
    "possible_pre_action_context",
})
_BORING_BLOCKED_STATES = frozenset({
    "active_gameplay",
    "high_motion_action",
    "possible_goal_or_flash",
    "goal_or_save_like_flash",
})
_MENU_PHASES = frozenset({
    "menu_wait",
    "queue_wait",
})
_WAIT_PHASES = frozenset({
    "menu_wait",
    "queue_wait",
    "countdown_kickoff",
    "round_end",
})
_ACTION_INDICATOR_TYPES = frozenset({
    "high_action_burst",
    "goal_or_save_like_flash",
    "possible_goal_or_flash",
    "sustained_action",
    "shout_like_audio",
    "group_reaction_like",
})
_GOAL_INDICATOR_TYPES = frozenset({
    "goal_or_save_like_flash",
    "possible_goal_or_flash",
})
_BURST_INDICATOR_TYPES = frozenset({
    "high_action_burst",
})
_REACTION_AUDIO_TYPES = frozenset({
    "shout_like_audio",
    "group_reaction_like",
    "speech_active",
})
_SPEECH_AUDIO_TYPES = frozenset({
    "speech_active",
    "secondary_speech_like",
    "shout_like_audio",
    "group_reaction_like",
})
_PROTECTED_ROLES = frozenset({"hook", "peak", "payoff"})


@dataclass
class RoundLifecycleSummary:
    menu_removed: int = 0
    menu_trimmed: int = 0
    round_start_shifted: int = 0
    pre_goal_expanded: int = 0
    post_goal_extended: int = 0
    boring_removed: int = 0
    boring_trimmed: int = 0
    invariant_overlap_removed: int = 0
    invariant_backjump_removed: int = 0
    invariant_micro_removed: int = 0
    duration_before: float = 0.0
    duration_after: float = 0.0
    examples: list[str] = field(default_factory=list)

    def add_example(self, text: str) -> None:
        if len(self.examples) < 8:
            self.examples.append(text)


class RoundLifecycleGuard:
    """
    Round lifecycle guard: enforces menu removal, true round start,
    pre/post goal protection, and boring gap trimming.
    """

    def apply(
        self,
        selected_segments: list[TimelineSegment],
        *,
        gameplay_state_result: GameplayStateResult | None = None,
        round_phase_result: RoundPhaseResult | None = None,
        cut_indicator_result: CutIndicatorResult | None = None,
        audio_role_result: AudioRoleResult | None = None,
        sentence_timeline_result: SentenceTimelineResult | None = None,
        transcript_result: TranscriptResult | None = None,
    ) -> tuple[list[TimelineSegment], RoundLifecycleSummary]:
        summary = RoundLifecycleSummary()

        if not selected_segments:
            return selected_segments, summary

        summary.duration_before = round(sum(s.duration for s in selected_segments), 3)

        state_windows = gameplay_state_result.windows if gameplay_state_result else []
        phase_windows = round_phase_result.windows if round_phase_result else []
        indicators = cut_indicator_result.indicators if cut_indicator_result else []
        audio_windows = audio_role_result.windows if audio_role_result else []

        segments = sorted(selected_segments, key=lambda s: (s.start_time, s.end_time))

        # A) Menu Wait Hard Removal
        segments = self._remove_menu_wait(
            segments, state_windows, phase_windows, indicators, summary
        )
        if not segments:
            summary.duration_after = 0.0
            self._log(summary)
            return segments, summary

        # B) True Round Start
        segments = self._fix_true_round_start(
            segments, state_windows, phase_windows, indicators, summary
        )

        # Find all goal events for C/D protection
        goal_events = self._find_goal_events(state_windows, indicators)

        # C) Pre-Goal Tension Expansion
        segments = self._expand_pre_goal(
            segments, state_windows, indicators, goal_events, summary
        )

        # D) Post-Goal Reaction Extension
        segments = self._extend_post_goal(
            segments, audio_windows, goal_events, summary
        )

        # E) Boring Gap Trim
        segments = self._trim_boring_gaps(
            segments, state_windows, indicators, audio_windows, goal_events, summary
        )

        # F) Final Invariants
        segments = self._apply_final_invariants(segments, summary)

        summary.duration_after = round(sum(s.duration for s in segments), 3)
        self._log(summary)
        return segments, summary

    # -------------------------------------------------------------------------
    # Rule A: Menu Wait Hard Removal
    # -------------------------------------------------------------------------

    def _remove_menu_wait(
        self,
        segments: list[TimelineSegment],
        state_windows: list[GameplayStateWindow],
        phase_windows: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
        summary: RoundLifecycleSummary,
    ) -> list[TimelineSegment]:
        result = []
        for seg in segments:
            wait_frac = self._compute_wait_ratio(seg, state_windows, phase_windows)
            action_frac = self._compute_action_ratio(seg, state_windows, indicators)
            is_protected = seg.segment_role in _PROTECTED_ROLES

            # Force remove: extremely wait-dominant, no action (even protected roles)
            if wait_frac >= MENU_FORCE_REMOVE_RATIO and action_frac < 0.10:
                summary.menu_removed += 1
                summary.add_example(
                    f"menu_force_removed seg={seg.segment_id[:8]} "
                    f"t={seg.start_time:.1f}-{seg.end_time:.1f} "
                    f"wait={wait_frac:.2f}"
                )
                continue

            # Normal remove: menu dominant + low action, not a protected role with real action
            if wait_frac >= MENU_WAIT_DOMINANT_RATIO and action_frac < ACTION_GUARD_RATIO:
                if is_protected and action_frac >= 0.05:
                    # Protected roles: shift start to action instead of removing
                    new_start = self._find_first_action_start(
                        seg.start_time, seg.end_time, state_windows, indicators
                    )
                    if new_start is not None and new_start > seg.start_time + 0.3:
                        old_start = seg.start_time
                        seg.start_time = round(new_start, 3)
                        seg.touch()
                        summary.round_start_shifted += 1
                        summary.add_example(
                            f"menu_start_shifted(protected) seg={seg.segment_id[:8]} "
                            f"t={old_start:.1f}->{seg.start_time:.1f}"
                        )
                else:
                    summary.menu_removed += 1
                    summary.add_example(
                        f"menu_removed seg={seg.segment_id[:8]} "
                        f"t={seg.start_time:.1f}-{seg.end_time:.1f} "
                        f"wait={wait_frac:.2f} action={action_frac:.2f}"
                    )
                    continue

            # Partial trim: leading wait section → count as round_start_shifted
            elif wait_frac >= 0.30 and action_frac >= ACTION_GUARD_RATIO:
                state_at_start = self._state_at(seg.start_time, state_windows)
                phase_at_start = self._phase_at(seg.start_time, phase_windows)
                starts_in_wait = (
                    (state_at_start is not None and state_at_start.state_type in _WAIT_STATES)
                    or (phase_at_start is not None and phase_at_start.phase.value in _MENU_PHASES)
                )
                if starts_in_wait:
                    new_start = self._find_first_action_start(
                        seg.start_time, seg.end_time, state_windows, indicators
                    )
                    if new_start is not None and new_start > seg.start_time + 0.5:
                        old_start = seg.start_time
                        seg.start_time = round(new_start, 3)
                        seg.touch()
                        summary.round_start_shifted += 1
                        summary.add_example(
                            f"menu_leading_trimmed seg={seg.segment_id[:8]} "
                            f"t={old_start:.1f}->{seg.start_time:.1f}"
                        )

            result.append(seg)
        return result

    # -------------------------------------------------------------------------
    # Rule B: True Round Start Fix
    # -------------------------------------------------------------------------

    def _fix_true_round_start(
        self,
        segments: list[TimelineSegment],
        state_windows: list[GameplayStateWindow],
        phase_windows: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
        summary: RoundLifecycleSummary,
    ) -> list[TimelineSegment]:
        for seg in segments:
            state_at_start = self._state_at(seg.start_time, state_windows)
            phase_at_start = self._phase_at(seg.start_time, phase_windows)

            starts_in_wait = (
                (state_at_start is not None and state_at_start.state_type in _WAIT_STATES)
                or (phase_at_start is not None and phase_at_start.phase.value in _WAIT_PHASES)
            )

            if not starts_in_wait:
                continue

            # Find first real action within segment
            first_action = self._find_first_action_start(
                seg.start_time, seg.end_time, state_windows, indicators
            )
            if first_action is None:
                continue

            # Check for goal event within first 12 seconds
            lookahead_end = seg.start_time + TRUE_ROUND_START_LOOKAHEAD
            first_goal = self._find_first_goal_in_range(
                seg.start_time, lookahead_end, state_windows, indicators
            )

            if first_goal is not None:
                # Start at least PRE_GOAL_PROTECT before the goal
                target_start = first_goal - TRUE_ROUND_START_PREROLL
                # Clamp: must be within segment and not before first_action if possible
                target_start = max(seg.start_time, target_start)
                new_start = min(first_action, target_start)
                new_start = max(seg.start_time, new_start)
            else:
                new_start = first_action

            if new_start > seg.start_time + 0.3:
                old_start = seg.start_time
                seg.start_time = round(new_start, 3)
                seg.touch()
                summary.round_start_shifted += 1
                suffix = f"goal_at={first_goal:.1f}" if first_goal is not None else "action_start"
                summary.add_example(
                    f"round_start_shifted seg={seg.segment_id[:8]} "
                    f"t={old_start:.1f}->{seg.start_time:.1f} {suffix}"
                )

        return segments

    # -------------------------------------------------------------------------
    # Rule C: Pre-Goal Tension Expansion
    # -------------------------------------------------------------------------

    def _expand_pre_goal(
        self,
        segments: list[TimelineSegment],
        state_windows: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        goal_events: list[float],
        summary: RoundLifecycleSummary,
    ) -> list[TimelineSegment]:
        for i, seg in enumerate(segments):
            prev_end = segments[i - 1].end_time if i > 0 else 0.0

            for goal_t in goal_events:
                if goal_t < seg.start_time or goal_t > seg.end_time + 0.5:
                    continue

                # Determine protection distance
                is_burst = self._is_burst_only_goal(goal_t, state_windows, indicators)
                protect_dist = PRE_GOAL_PROTECT_BURST if is_burst else PRE_GOAL_PROTECT_FULL

                target_start = goal_t - protect_dist
                if target_start >= seg.start_time:
                    continue

                # Only expand if there's room (no overlap with previous segment)
                allowed_start = max(prev_end + 0.1, target_start)
                if allowed_start < seg.start_time - 0.3:
                    old_start = seg.start_time
                    seg.start_time = round(allowed_start, 3)
                    seg.touch()
                    summary.pre_goal_expanded += 1
                    summary.add_example(
                        f"pre_goal_expanded seg={seg.segment_id[:8]} "
                        f"t={old_start:.1f}->{seg.start_time:.1f} "
                        f"goal_at={goal_t:.1f}"
                    )
                    break

        return segments

    # -------------------------------------------------------------------------
    # Rule D: Post-Goal Reaction Extension
    # -------------------------------------------------------------------------

    def _extend_post_goal(
        self,
        segments: list[TimelineSegment],
        audio_windows: list[AudioRoleWindow],
        goal_events: list[float],
        summary: RoundLifecycleSummary,
    ) -> list[TimelineSegment]:
        for i, seg in enumerate(segments):
            next_start = segments[i + 1].start_time if i + 1 < len(segments) else float("inf")

            for goal_t in goal_events:
                if goal_t < seg.start_time or goal_t >= seg.end_time:
                    continue

                # Minimum post-goal end
                min_end = goal_t + POST_GOAL_PROTECT

                # Find reaction audio end after goal
                reaction_end = self._find_reaction_audio_end(goal_t, seg.end_time + 5.0, audio_windows)
                if reaction_end is not None:
                    target_end = reaction_end + POST_GOAL_REACTION_EXTEND
                else:
                    target_end = min_end

                target_end = max(min_end, target_end)

                if target_end <= seg.end_time:
                    continue

                # Clamp to not overlap next segment
                allowed_end = min(next_start - 0.1, target_end)
                if allowed_end > seg.end_time + 0.3:
                    old_end = seg.end_time
                    seg.end_time = round(allowed_end, 3)
                    seg.touch()
                    summary.post_goal_extended += 1
                    summary.add_example(
                        f"post_goal_extended seg={seg.segment_id[:8]} "
                        f"t={old_end:.1f}->{seg.end_time:.1f} "
                        f"goal_at={goal_t:.1f}"
                    )
                    break

        return segments

    # -------------------------------------------------------------------------
    # Rule E: Boring Gap Trim
    # -------------------------------------------------------------------------

    def _trim_boring_gaps(
        self,
        segments: list[TimelineSegment],
        state_windows: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        goal_events: list[float],
        summary: RoundLifecycleSummary,
    ) -> list[TimelineSegment]:
        result = []
        for seg in segments:
            # Check if entire segment is boring
            if self._is_entirely_boring(seg, state_windows, indicators, audio_windows, goal_events):
                if seg.segment_role not in _PROTECTED_ROLES:
                    summary.boring_removed += 1
                    summary.add_example(
                        f"boring_removed seg={seg.segment_id[:8]} "
                        f"t={seg.start_time:.1f}-{seg.end_time:.1f}"
                    )
                    continue
                result.append(seg)
                continue

            old_start = seg.start_time
            old_end = seg.end_time
            trimmed = False

            # Trim leading boring region
            leading_boring_end = self._find_leading_boring_end(
                seg, state_windows, indicators, audio_windows, goal_events
            )
            if leading_boring_end is not None and leading_boring_end > seg.start_time + BORING_MIN_DURATION:
                new_start = min(leading_boring_end, seg.end_time - MIN_SEGMENT_DURATION)
                if new_start > seg.start_time + 0.3:
                    seg.start_time = round(new_start, 3)
                    seg.touch()
                    trimmed = True

            # Trim trailing boring region
            trailing_boring_start = self._find_trailing_boring_start(
                seg, state_windows, indicators, audio_windows, goal_events
            )
            if trailing_boring_start is not None and trailing_boring_start < seg.end_time - BORING_MIN_DURATION:
                new_end = max(trailing_boring_start, seg.start_time + MIN_SEGMENT_DURATION)
                if new_end < seg.end_time - 0.3:
                    seg.end_time = round(new_end, 3)
                    seg.touch()
                    trimmed = True

            if trimmed:
                if seg.duration < MIN_SEGMENT_DURATION and seg.segment_role not in _PROTECTED_ROLES:
                    summary.boring_removed += 1
                    summary.add_example(
                        f"boring_removed_after_trim seg={seg.segment_id[:8]} "
                        f"t={old_start:.1f}-{old_end:.1f}"
                    )
                    continue
                summary.boring_trimmed += 1
                summary.add_example(
                    f"boring_trimmed seg={seg.segment_id[:8]} "
                    f"t={old_start:.1f}-{old_end:.1f} "
                    f"->{seg.start_time:.1f}-{seg.end_time:.1f}"
                )

            result.append(seg)
        return result

    def _is_entirely_boring(
        self,
        seg: TimelineSegment,
        state_windows: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        goal_events: list[float],
    ) -> bool:
        # Check if any interesting activity overlaps the segment
        for w in state_windows:
            if w.end_seconds <= seg.start_time or w.start_seconds >= seg.end_time:
                continue
            if w.state_type in _BORING_BLOCKED_STATES:
                return False

        for ind in indicators:
            if ind.end_seconds <= seg.start_time or ind.start_seconds >= seg.end_time:
                continue
            if ind.indicator_type in _ACTION_INDICATOR_TYPES:
                return False

        for aw in audio_windows:
            if aw.end_seconds <= seg.start_time or aw.start_seconds >= seg.end_time:
                continue
            if aw.role_type in _SPEECH_AUDIO_TYPES:
                return False

        # Check goal protection
        for goal_t in goal_events:
            if goal_t + POST_GOAL_PROTECT > seg.start_time and goal_t - PRE_GOAL_PROTECT_FULL < seg.end_time:
                return False

        return True

    def _find_leading_boring_end(
        self,
        seg: TimelineSegment,
        state_windows: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        goal_events: list[float],
    ) -> float | None:
        """Find the end of the boring region at the start of the segment."""
        first_interesting = self._find_first_interesting(
            seg.start_time, seg.end_time, state_windows, indicators, audio_windows, goal_events
        )
        if first_interesting is None:
            return None
        gap = first_interesting - seg.start_time
        if gap >= BORING_MIN_DURATION:
            return first_interesting
        return None

    def _find_trailing_boring_start(
        self,
        seg: TimelineSegment,
        state_windows: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        goal_events: list[float],
    ) -> float | None:
        """Find the start of the boring region at the end of the segment."""
        last_interesting = self._find_last_interesting(
            seg.start_time, seg.end_time, state_windows, indicators, audio_windows, goal_events
        )
        if last_interesting is None:
            return None
        gap = seg.end_time - last_interesting
        if gap >= BORING_MIN_DURATION:
            return last_interesting
        return None

    def _find_first_interesting(
        self,
        t_from: float,
        t_to: float,
        state_windows: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        goal_events: list[float],
    ) -> float | None:
        candidates: list[float] = []

        for w in state_windows:
            if w.end_seconds <= t_from or w.start_seconds >= t_to:
                continue
            if w.state_type in _BORING_BLOCKED_STATES:
                candidates.append(max(w.start_seconds, t_from))

        for ind in indicators:
            if ind.end_seconds <= t_from or ind.start_seconds >= t_to:
                continue
            if ind.indicator_type in _ACTION_INDICATOR_TYPES:
                candidates.append(max(ind.start_seconds, t_from))

        for aw in audio_windows:
            if aw.end_seconds <= t_from or aw.start_seconds >= t_to:
                continue
            if aw.role_type in _SPEECH_AUDIO_TYPES:
                candidates.append(max(aw.start_seconds, t_from))

        for goal_t in goal_events:
            protect_start = goal_t - PRE_GOAL_PROTECT_FULL
            if protect_start < t_to and goal_t + POST_GOAL_PROTECT > t_from:
                candidates.append(max(protect_start, t_from))

        return min(candidates) if candidates else None

    def _find_last_interesting(
        self,
        t_from: float,
        t_to: float,
        state_windows: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        goal_events: list[float],
    ) -> float | None:
        candidates: list[float] = []

        for w in state_windows:
            if w.end_seconds <= t_from or w.start_seconds >= t_to:
                continue
            if w.state_type in _BORING_BLOCKED_STATES:
                candidates.append(min(w.end_seconds, t_to))

        for ind in indicators:
            if ind.end_seconds <= t_from or ind.start_seconds >= t_to:
                continue
            if ind.indicator_type in _ACTION_INDICATOR_TYPES:
                candidates.append(min(ind.end_seconds, t_to))

        for aw in audio_windows:
            if aw.end_seconds <= t_from or aw.start_seconds >= t_to:
                continue
            if aw.role_type in _SPEECH_AUDIO_TYPES:
                candidates.append(min(aw.end_seconds, t_to))

        for goal_t in goal_events:
            protect_end = goal_t + POST_GOAL_PROTECT
            if protect_end > t_from and goal_t - PRE_GOAL_PROTECT_FULL < t_to:
                candidates.append(min(protect_end, t_to))

        return max(candidates) if candidates else None

    # -------------------------------------------------------------------------
    # Rule F: Final Invariants
    # -------------------------------------------------------------------------

    def _apply_final_invariants(
        self,
        segments: list[TimelineSegment],
        summary: RoundLifecycleSummary,
    ) -> list[TimelineSegment]:
        if not segments:
            return segments

        segments.sort(key=lambda s: (s.start_time, s.end_time))

        # Remove backjumps and fix overlaps
        without_jumps: list[TimelineSegment] = []
        last_end = -1.0
        for seg in segments:
            if seg.end_time <= seg.start_time:
                summary.invariant_micro_removed += 1
                continue
            if seg.start_time < last_end - 0.2:
                summary.invariant_backjump_removed += 1
                summary.add_example(
                    f"backjump_removed seg={seg.segment_id[:8]} "
                    f"t={seg.start_time:.1f} last_end={last_end:.1f}"
                )
                continue
            if seg.start_time < last_end:
                seg.start_time = round(last_end, 3)
                seg.touch()
                summary.invariant_overlap_removed += 1
            without_jumps.append(seg)
            last_end = seg.end_time

        # Remove micro segments
        final: list[TimelineSegment] = []
        for seg in without_jumps:
            if seg.duration < MIN_SEGMENT_DURATION and seg.segment_role not in _PROTECTED_ROLES:
                summary.invariant_micro_removed += 1
                summary.add_example(
                    f"invariant_micro_removed seg={seg.segment_id[:8]} "
                    f"dur={seg.duration:.2f}s role={seg.segment_role}"
                )
                continue
            final.append(seg)

        return final

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------

    def _compute_wait_ratio(
        self,
        seg: TimelineSegment,
        state_windows: list[GameplayStateWindow],
        phase_windows: list[RoundPhaseWindow],
    ) -> float:
        if seg.duration <= 0:
            return 0.0
        wait_secs = 0.0
        for w in state_windows:
            if w.end_seconds <= seg.start_time or w.start_seconds >= seg.end_time:
                continue
            if w.state_type in _WAIT_STATES:
                overlap = min(w.end_seconds, seg.end_time) - max(w.start_seconds, seg.start_time)
                wait_secs += max(0.0, overlap)
        for pw in phase_windows:
            if pw.end_seconds <= seg.start_time or pw.start_seconds >= seg.end_time:
                continue
            if pw.phase.value in _MENU_PHASES:
                overlap = min(pw.end_seconds, seg.end_time) - max(pw.start_seconds, seg.start_time)
                wait_secs += max(0.0, overlap)
        return min(1.0, wait_secs / seg.duration)

    def _compute_action_ratio(
        self,
        seg: TimelineSegment,
        state_windows: list[GameplayStateWindow],
        indicators: list[CutIndicator],
    ) -> float:
        if seg.duration <= 0:
            return 0.0
        action_secs = 0.0
        for w in state_windows:
            if w.end_seconds <= seg.start_time or w.start_seconds >= seg.end_time:
                continue
            if w.state_type in _ACTION_STATES | _GOAL_STATES:
                overlap = min(w.end_seconds, seg.end_time) - max(w.start_seconds, seg.start_time)
                action_secs += max(0.0, overlap)
        for ind in indicators:
            if ind.end_seconds <= seg.start_time or ind.start_seconds >= seg.end_time:
                continue
            if ind.indicator_type in _ACTION_INDICATOR_TYPES:
                overlap = min(ind.end_seconds, seg.end_time) - max(ind.start_seconds, seg.start_time)
                action_secs += max(0.0, overlap)
        return min(1.0, action_secs / seg.duration)

    def _phase_at(self, t: float, phase_windows: list[RoundPhaseWindow]) -> RoundPhaseWindow | None:
        for pw in phase_windows:
            if pw.start_seconds <= t < pw.end_seconds:
                return pw
        return None

    def _state_at(self, t: float, state_windows: list[GameplayStateWindow]) -> GameplayStateWindow | None:
        for w in state_windows:
            if w.start_seconds <= t < w.end_seconds:
                return w
        return None

    def _find_goal_events(
        self,
        state_windows: list[GameplayStateWindow],
        indicators: list[CutIndicator],
    ) -> list[float]:
        goals: set[float] = set()
        for w in state_windows:
            if w.state_type in _GOAL_STATES:
                goals.add(round(w.start_seconds, 3))
        for ind in indicators:
            if ind.indicator_type in _GOAL_INDICATOR_TYPES:
                goals.add(round(ind.start_seconds, 3))
        return sorted(goals)

    def _find_first_action_start(
        self,
        seg_start: float,
        seg_end: float,
        state_windows: list[GameplayStateWindow],
        indicators: list[CutIndicator],
    ) -> float | None:
        candidates: list[float] = []
        for w in state_windows:
            if w.end_seconds <= seg_start or w.start_seconds >= seg_end:
                continue
            if w.state_type in _TRUE_ROUND_START_STATES | _GOAL_STATES:
                candidates.append(max(w.start_seconds, seg_start))
        for ind in indicators:
            if ind.end_seconds <= seg_start or ind.start_seconds >= seg_end:
                continue
            if ind.indicator_type in _ACTION_INDICATOR_TYPES:
                candidates.append(max(ind.start_seconds, seg_start))
        return min(candidates) if candidates else None

    def _find_first_goal_in_range(
        self,
        t_from: float,
        t_to: float,
        state_windows: list[GameplayStateWindow],
        indicators: list[CutIndicator],
    ) -> float | None:
        candidates: list[float] = []
        for w in state_windows:
            if w.state_type in _GOAL_STATES and t_from <= w.start_seconds < t_to:
                candidates.append(w.start_seconds)
        for ind in indicators:
            if ind.indicator_type in _GOAL_INDICATOR_TYPES and t_from <= ind.start_seconds < t_to:
                candidates.append(ind.start_seconds)
        return min(candidates) if candidates else None

    def _is_burst_only_goal(
        self,
        goal_t: float,
        state_windows: list[GameplayStateWindow],
        indicators: list[CutIndicator],
    ) -> bool:
        # Returns True if the goal event is only recognized as high_action_burst
        # (not as goal_or_save_like_flash or possible_goal_or_flash)
        for w in state_windows:
            if w.start_seconds <= goal_t < w.end_seconds:
                if w.state_type in {"goal_or_save_like_flash", "possible_goal_or_flash"}:
                    return False
        for ind in indicators:
            if ind.start_seconds <= goal_t < ind.end_seconds:
                if ind.indicator_type in {"goal_or_save_like_flash", "possible_goal_or_flash"}:
                    return False
        return True

    def _find_reaction_audio_end(
        self,
        goal_t: float,
        search_until: float,
        audio_windows: list[AudioRoleWindow],
    ) -> float | None:
        candidates: list[float] = []
        for aw in audio_windows:
            if aw.start_seconds >= goal_t and aw.start_seconds < search_until:
                if aw.role_type in _REACTION_AUDIO_TYPES:
                    candidates.append(aw.end_seconds)
        return max(candidates) if candidates else None

    def _log(self, summary: RoundLifecycleSummary) -> None:
        print(
            "[TIMELINE-ROUND-LIFECYCLE] "
            f"menu_removed={summary.menu_removed} "
            f"round_start_shifted={summary.round_start_shifted} "
            f"pre_goal_expanded={summary.pre_goal_expanded} "
            f"post_goal_extended={summary.post_goal_extended} "
            f"boring_removed={summary.boring_removed} "
            f"boring_trimmed={summary.boring_trimmed} "
            f"duration_before={summary.duration_before:.3f}s "
            f"duration_after={summary.duration_after:.3f}s"
        )
        if summary.examples:
            print(f"[TIMELINE-ROUND-LIFECYCLE] examples={'; '.join(summary.examples)}")
