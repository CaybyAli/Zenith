from __future__ import annotations

from dataclasses import dataclass, field

from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.cut_indicator import CutIndicator, CutIndicatorResult
from models.timeline_segment import TimelineSegment


ROUND_WAIT_MIN_DURATION = 6.0
ROUND_WAIT_MAX_KEEP_IF_SPEECH = 3.0
ROUND_WAIT_LOW_ACTION_THRESHOLD = 0.25
MIN_SEGMENT_DURATION_SECONDS = 2.5
MIN_GAP_SECONDS = 0.15

_PROTECTED_ROLES = frozenset({"hook", "peak", "payoff"})
_TARGET_ROLES = frozenset({"build", "bridge"})
_NEGATIVE_TYPES = frozenset({
    "menu_or_idle",
    "low_gameplay_value",
    "round_end_dead_time",
    "silence_or_dead_air",
    "filler_sentence",
})
_POSITIVE_TYPES = frozenset({
    "high_action_burst",
    "goal_or_save_like_flash",
    "sustained_action",
    "group_reaction_like",
    "shout_like_audio",
    "laugh_like_audio",
    "hook_sentence",
    "facecam_reaction_spike",
})
_SPEECH_TYPES = frozenset({"speech_active", "secondary_speech_like"})
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
class RoundWaitDeadtimeSummary:
    removed: int = 0
    trimmed: int = 0
    after_goal_tail_trimmed: int = 0
    menu_speech_ignored: int = 0
    kept_action: int = 0
    kept_speech: int = 0
    gameplay_state_removed: int = 0
    gameplay_state_trimmed: int = 0
    state_menu_wait_seconds: float = 0.0
    state_dead_wait_seconds: float = 0.0
    protected_by_action_state: int = 0
    duration_before: float = 0.0
    duration_after: float = 0.0
    examples: list[str] = field(default_factory=list)

    def add_example(self, text: str) -> None:
        if len(self.examples) < 6:
            self.examples.append(text)


class RoundWaitDeadtimeGuard:
    engine = "round-wait-deadtime-guard-v1"

    def apply(
        self,
        segments: list[TimelineSegment],
        *,
        cut_indicator_result: CutIndicatorResult | None = None,
        audio_role_result: AudioRoleResult | None = None,
        gameplay_state_result=None,
    ) -> tuple[list[TimelineSegment], RoundWaitDeadtimeSummary]:
        ordered = sorted(
            (segment for segment in segments if segment.end_time > segment.start_time),
            key=lambda segment: (segment.start_time, segment.end_time, segment.segment_id),
        )
        summary = RoundWaitDeadtimeSummary(
            duration_before=round(sum(segment.duration for segment in ordered), 3)
        )
        indicators = self._indicators(cut_indicator_result)
        audio_windows = self._audio_windows(audio_role_result)
        state_windows = self._state_windows(gameplay_state_result)

        kept: list[TimelineSegment] = []
        for segment in ordered:
            if segment.segment_role in _PROTECTED_ROLES:
                kept.append(segment)
                continue
            if segment.segment_role not in _TARGET_ROLES:
                kept.append(segment)
                continue

            state_removed = self._apply_gameplay_state_wait(segment, state_windows, summary)
            if state_removed:
                continue
            if segment.end_time <= segment.start_time:
                continue

            if segment.duration <= ROUND_WAIT_MIN_DURATION:
                kept.append(segment)
                continue

            self._trim_after_goal_tail(segment, indicators, audio_windows, summary)

            has_hard_wait_signal = self._has_hard_wait_signal(segment, indicators)
            has_positive = self._has_positive(segment.start_time, segment.end_time, indicators)
            if has_hard_wait_signal:
                if has_positive:
                    if self._soft_trim_around_positive(segment, indicators, summary):
                        segment.touch()
                    summary.kept_action += 1
                    kept.append(segment)
                    continue
                if self._has_neutral_speech(segment, audio_windows):
                    summary.menu_speech_ignored += 1
                segment.notes.append("round_wait_menu_speech_ignored_removed")
                summary.removed += 1
                summary.add_example(
                    f"{segment.segment_id} removed hard_wait {segment.start_time:.2f}-{segment.end_time:.2f}"
                )
                continue

            if has_positive:
                summary.kept_action += 1
                kept.append(segment)
                continue
            if self._has_valuable_speech(segment, indicators, audio_windows, menu_context=False):
                summary.kept_speech += 1
                kept.append(segment)
                continue

            negative_score = self._negative_score(segment, indicators, audio_windows)
            if negative_score < ROUND_WAIT_LOW_ACTION_THRESHOLD:
                kept.append(segment)
                continue

            if self._should_remove(segment, indicators, audio_windows):
                segment.notes.append("round_wait_deadtime_removed")
                summary.removed += 1
                summary.add_example(
                    f"{segment.segment_id} removed {segment.start_time:.2f}-{segment.end_time:.2f}"
                )
                continue

            if self._trim_edges(segment, indicators, audio_windows, summary):
                segment.touch()
            kept.append(segment)

        kept = self._cleanup(kept)
        summary.duration_after = round(sum(segment.duration for segment in kept), 3)
        print(
            "[TIMELINE-ROUND-WAIT-GUARD] "
            f"removed={summary.removed} "
            f"trimmed={summary.trimmed} "
            f"after_goal_tail_trimmed={summary.after_goal_tail_trimmed} "
            f"menu_speech_ignored={summary.menu_speech_ignored} "
            f"kept_action={summary.kept_action} "
            f"kept_speech={summary.kept_speech} "
            f"gameplay_state_removed={summary.gameplay_state_removed} "
            f"gameplay_state_trimmed={summary.gameplay_state_trimmed} "
            f"protected_by_action_state={summary.protected_by_action_state} "
            f"state_menu_wait_seconds={summary.state_menu_wait_seconds:.3f}s "
            f"state_dead_wait_seconds={summary.state_dead_wait_seconds:.3f}s "
            f"duration_before={summary.duration_before:.3f}s "
            f"duration_after={summary.duration_after:.3f}s"
        )
        if summary.examples:
            print(f"[TIMELINE-ROUND-WAIT-GUARD] examples={'; '.join(summary.examples)}")
        return kept, summary

    def _apply_gameplay_state_wait(
        self,
        segment: TimelineSegment,
        state_windows: list[object],
        summary: RoundWaitDeadtimeSummary,
    ) -> bool:
        if not state_windows or segment.duration <= 0:
            return False

        bad_windows = self._state_overlap_windows(segment, state_windows, _BAD_WAIT_STATES)
        good_overlap = self._state_overlap_seconds(segment, state_windows, _GOOD_ACTION_STATES)
        bad_overlap = sum(end - start for start, end in bad_windows)
        if bad_overlap <= 0.0 and good_overlap <= 0.0:
            return False

        bad_ratio = bad_overlap / max(segment.duration, 0.001)
        good_ratio = good_overlap / max(segment.duration, 0.001)
        summary.state_menu_wait_seconds = round(
            summary.state_menu_wait_seconds
            + self._state_overlap_seconds(segment, state_windows, {"menu_wait", "scoreboard_like"}),
            3,
        )
        summary.state_dead_wait_seconds = round(
            summary.state_dead_wait_seconds
            + self._state_overlap_seconds(
                segment,
                state_windows,
                {"possible_dead_time_after_goal", "round_end", "replay_like", "low_motion_wait"},
            ),
            3,
        )

        if good_ratio >= 0.20:
            summary.protected_by_action_state += 1
            segment.notes.append(f"round_wait_state_protected_action={good_ratio:.3f}")
            return False

        if bad_ratio >= 0.45:
            segment.notes.append(f"round_wait_state_removed_bad={bad_ratio:.3f}")
            summary.removed += 1
            summary.gameplay_state_removed += 1
            summary.add_example(
                f"{segment.segment_id} removed gameplay_state bad={bad_ratio:.2f} good={good_ratio:.2f}"
            )
            return True

        if bad_ratio >= 0.30 and self._trim_state_wait_edges(segment, bad_windows, summary):
            segment.touch()
        return False

    def _trim_state_wait_edges(
        self,
        segment: TimelineSegment,
        bad_windows: list[tuple[float, float]],
        summary: RoundWaitDeadtimeSummary,
    ) -> bool:
        changed = False
        for start, end in bad_windows:
            if start <= segment.start_time + 0.2:
                proposed_start = round(min(end, segment.end_time - MIN_SEGMENT_DURATION_SECONDS), 3)
                if proposed_start > segment.start_time and segment.end_time - proposed_start >= MIN_SEGMENT_DURATION_SECONDS:
                    old = segment.start_time
                    segment.start_time = proposed_start
                    segment.notes.append(f"round_wait_state_trim_start={old:.3f}->{segment.start_time:.3f}")
                    summary.trimmed += 1
                    summary.gameplay_state_trimmed += 1
                    summary.add_example(f"{segment.segment_id} state_trim_start {old:.2f}->{segment.start_time:.2f}")
                    changed = True
            if end >= segment.end_time - 0.2:
                proposed_end = round(max(start, segment.start_time + MIN_SEGMENT_DURATION_SECONDS), 3)
                if proposed_end < segment.end_time and proposed_end - segment.start_time >= MIN_SEGMENT_DURATION_SECONDS:
                    old = segment.end_time
                    segment.end_time = proposed_end
                    segment.notes.append(f"round_wait_state_trim_end={old:.3f}->{segment.end_time:.3f}")
                    summary.trimmed += 1
                    summary.gameplay_state_trimmed += 1
                    summary.add_example(f"{segment.segment_id} state_trim_end {old:.2f}->{segment.end_time:.2f}")
                    changed = True
        return changed

    def _state_overlap_windows(
        self,
        segment: TimelineSegment,
        state_windows: list[object],
        state_types: frozenset[str] | set[str],
    ) -> list[tuple[float, float]]:
        windows: list[tuple[float, float]] = []
        for state in state_windows:
            if self._state_type(state) not in state_types:
                continue
            start = max(segment.start_time, self._state_start(state))
            end = min(segment.end_time, self._state_end(state))
            if end > start:
                windows.append((start, end))
        return _merge_windows(windows)

    def _state_overlap_seconds(
        self,
        segment: TimelineSegment,
        state_windows: list[object],
        state_types: frozenset[str] | set[str],
    ) -> float:
        return round(
            sum(end - start for start, end in self._state_overlap_windows(segment, state_windows, state_types)),
            3,
        )

    def _should_remove(
        self,
        segment: TimelineSegment,
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
    ) -> bool:
        negative_types = {
            indicator.indicator_type
            for indicator in indicators
            if indicator.indicator_type in _NEGATIVE_TYPES
            and _overlap_seconds(
                segment.start_time,
                segment.end_time,
                indicator.start_seconds,
                indicator.end_seconds,
            ) >= 0.5
        }
        if any(
            window.role_type == "silence_or_dead_air"
            and _overlap_seconds(
                segment.start_time,
                segment.end_time,
                window.start_seconds,
                window.end_seconds,
            ) >= 0.5
            for window in audio_windows
        ):
            negative_types.add("silence_or_dead_air")

        coverage = self._negative_coverage(segment, indicators, audio_windows)
        return len(negative_types) >= 2 or coverage >= 0.65

    def _trim_edges(
        self,
        segment: TimelineSegment,
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        summary: RoundWaitDeadtimeSummary,
    ) -> bool:
        changed = False
        windows = self._negative_windows(segment, indicators, audio_windows)
        for start, end in windows:
            if end - start < ROUND_WAIT_MIN_DURATION:
                continue
            if self._has_positive(start, end, indicators):
                continue
            if start <= segment.start_time + 0.6:
                proposed_start = round(min(end, segment.end_time - MIN_SEGMENT_DURATION_SECONDS), 3)
                if proposed_start > segment.start_time and segment.end_time - proposed_start >= MIN_SEGMENT_DURATION_SECONDS:
                    old = segment.start_time
                    segment.start_time = proposed_start
                    segment.notes.append(f"round_wait_trim_start={old:.3f}->{segment.start_time:.3f}")
                    summary.trimmed += 1
                    summary.add_example(f"{segment.segment_id} trim_start {old:.2f}->{segment.start_time:.2f}")
                    changed = True
            if end >= segment.end_time - 0.6:
                proposed_end = round(max(start, segment.start_time + MIN_SEGMENT_DURATION_SECONDS), 3)
                if proposed_end < segment.end_time and proposed_end - segment.start_time >= MIN_SEGMENT_DURATION_SECONDS:
                    old = segment.end_time
                    segment.end_time = proposed_end
                    segment.notes.append(f"round_wait_trim_end={old:.3f}->{segment.end_time:.3f}")
                    summary.trimmed += 1
                    summary.add_example(f"{segment.segment_id} trim_end {old:.2f}->{segment.end_time:.2f}")
                    changed = True
        return changed

    def _soft_trim_around_positive(
        self,
        segment: TimelineSegment,
        indicators: list[CutIndicator],
        summary: RoundWaitDeadtimeSummary,
    ) -> bool:
        windows = [
            indicator
            for indicator in indicators
            if indicator.indicator_type in _POSITIVE_TYPES
            and indicator.score >= 0.55
            and _overlap_seconds(
                segment.start_time,
                segment.end_time,
                indicator.start_seconds,
                indicator.end_seconds,
            ) >= 0.25
        ]
        if not windows:
            return False
        old_start = segment.start_time
        old_end = segment.end_time
        keep_start = round(max(segment.start_time, min(w.start_seconds for w in windows) - 1.0), 3)
        keep_end = round(min(segment.end_time, max(w.end_seconds for w in windows) + 1.5), 3)
        if keep_end - keep_start < MIN_SEGMENT_DURATION_SECONDS:
            center = (keep_start + keep_end) / 2.0
            keep_start = round(max(segment.start_time, center - MIN_SEGMENT_DURATION_SECONDS / 2.0), 3)
            keep_end = round(min(segment.end_time, keep_start + MIN_SEGMENT_DURATION_SECONDS), 3)
        if keep_start <= old_start and keep_end >= old_end:
            return False
        segment.start_time = keep_start
        segment.end_time = keep_end
        segment.notes.append(
            f"round_wait_soft_trim_action={old_start:.3f}-{old_end:.3f}->{keep_start:.3f}-{keep_end:.3f}"
        )
        summary.trimmed += 1
        summary.add_example(
            f"{segment.segment_id} soft_trim {old_start:.2f}-{old_end:.2f}->{keep_start:.2f}-{keep_end:.2f}"
        )
        return True

    def _trim_after_goal_tail(
        self,
        segment: TimelineSegment,
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        summary: RoundWaitDeadtimeSummary,
    ) -> bool:
        action_windows = [
            indicator
            for indicator in indicators
            if indicator.indicator_type in {"goal_or_save_like_flash", "high_action_burst"}
            and _overlap_seconds(
                segment.start_time,
                segment.end_time,
                indicator.start_seconds,
                indicator.end_seconds,
            ) > 0
        ]
        if not action_windows:
            return False
        action_end = max(indicator.end_seconds for indicator in action_windows)
        proposed_end = round(action_end + 1.2, 3)
        if proposed_end >= segment.end_time:
            return False
        if proposed_end - segment.start_time < MIN_SEGMENT_DURATION_SECONDS:
            return False
        if self._has_meaningful_activity_after(proposed_end, segment.end_time, indicators, audio_windows):
            return False
        old_end = segment.end_time
        segment.end_time = proposed_end
        segment.notes.append(f"round_wait_after_goal_tail_trim={old_end:.3f}->{segment.end_time:.3f}")
        summary.trimmed += 1
        summary.after_goal_tail_trimmed += 1
        summary.add_example(f"{segment.segment_id} after_goal_tail {old_end:.2f}->{segment.end_time:.2f}")
        segment.touch()
        return True

    def _negative_score(
        self,
        segment: TimelineSegment,
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
    ) -> float:
        score = 0.0
        for indicator in indicators:
            if indicator.indicator_type not in _NEGATIVE_TYPES:
                continue
            overlap = _overlap_seconds(
                segment.start_time,
                segment.end_time,
                indicator.start_seconds,
                indicator.end_seconds,
            )
            score += (overlap / max(segment.duration, 0.001)) * indicator.score
        for window in audio_windows:
            if window.role_type != "silence_or_dead_air":
                continue
            overlap = _overlap_seconds(
                segment.start_time,
                segment.end_time,
                window.start_seconds,
                window.end_seconds,
            )
            score += (overlap / max(segment.duration, 0.001)) * window.score
        return round(min(1.0, score), 3)

    def _negative_coverage(
        self,
        segment: TimelineSegment,
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
    ) -> float:
        covered = 0.0
        for start, end in self._negative_windows(segment, indicators, audio_windows):
            covered += max(0.0, end - start)
        return min(1.0, covered / max(segment.duration, 0.001))

    def _negative_windows(
        self,
        segment: TimelineSegment,
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
    ) -> list[tuple[float, float]]:
        windows: list[tuple[float, float]] = []
        for indicator in indicators:
            if indicator.indicator_type in _NEGATIVE_TYPES:
                start = max(segment.start_time, indicator.start_seconds)
                end = min(segment.end_time, indicator.end_seconds)
                if end > start:
                    windows.append((start, end))
        for window in audio_windows:
            if window.role_type == "silence_or_dead_air":
                start = max(segment.start_time, window.start_seconds)
                end = min(segment.end_time, window.end_seconds)
                if end > start:
                    windows.append((start, end))
        return _merge_windows(windows)

    def _has_positive(
        self,
        start: float,
        end: float,
        indicators: list[CutIndicator],
    ) -> bool:
        return any(
            indicator.indicator_type in _POSITIVE_TYPES
            and indicator.score >= 0.55
            and _overlap_seconds(start, end, indicator.start_seconds, indicator.end_seconds) >= 0.25
            for indicator in indicators
        )

    def _has_valuable_speech(
        self,
        segment: TimelineSegment,
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        *,
        menu_context: bool,
    ) -> bool:
        if any(
            indicator.indicator_type == "hook_sentence"
            and _overlap_seconds(
                segment.start_time,
                segment.end_time,
                indicator.start_seconds,
                indicator.end_seconds,
            ) > 0
            for indicator in indicators
        ):
            return True
        if menu_context:
            return False

        speech_overlap = sum(
            _overlap_seconds(
                segment.start_time,
                segment.end_time,
                window.start_seconds,
                window.end_seconds,
            )
            for window in audio_windows
            if window.role_type in _SPEECH_TYPES and window.score >= 0.55
        )
        filler_overlap = sum(
            _overlap_seconds(
                segment.start_time,
                segment.end_time,
                indicator.start_seconds,
                indicator.end_seconds,
            )
            for indicator in indicators
            if indicator.indicator_type == "filler_sentence"
        )
        return speech_overlap > ROUND_WAIT_MAX_KEEP_IF_SPEECH and filler_overlap < speech_overlap * 0.5

    def _has_hard_wait_signal(
        self,
        segment: TimelineSegment,
        indicators: list[CutIndicator],
    ) -> bool:
        if segment.duration <= 8.0:
            return False
        return any(
            indicator.indicator_type in {"menu_or_idle", "low_gameplay_value", "round_end_dead_time"}
            and _overlap_seconds(
                segment.start_time,
                segment.end_time,
                indicator.start_seconds,
                indicator.end_seconds,
            ) >= 0.5
            for indicator in indicators
        )

    def _has_neutral_speech(
        self,
        segment: TimelineSegment,
        audio_windows: list[AudioRoleWindow],
    ) -> bool:
        return any(
            window.role_type in _SPEECH_TYPES
            and _overlap_seconds(
                segment.start_time,
                segment.end_time,
                window.start_seconds,
                window.end_seconds,
            ) > 0.25
            for window in audio_windows
        )

    def _has_meaningful_activity_after(
        self,
        start: float,
        end: float,
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
    ) -> bool:
        return any(
            indicator.indicator_type in _POSITIVE_TYPES
            and indicator.indicator_type not in {"goal_or_save_like_flash", "high_action_burst"}
            and _overlap_seconds(start, end, indicator.start_seconds, indicator.end_seconds) >= 0.25
            for indicator in indicators
        ) or any(
            window.role_type in {"speech_active", "secondary_speech_like", "shout_like_audio", "group_reaction_like", "laugh_like_audio"}
            and window.score >= 0.55
            and _overlap_seconds(start, end, window.start_seconds, window.end_seconds) >= 0.3
            for window in audio_windows
        )

    def _cleanup(self, segments: list[TimelineSegment]) -> list[TimelineSegment]:
        kept: list[TimelineSegment] = []
        for segment in sorted(segments, key=lambda item: (item.start_time, item.end_time, item.segment_id)):
            if segment.end_time <= segment.start_time:
                continue
            if segment.duration < MIN_SEGMENT_DURATION_SECONDS and segment.segment_role not in _PROTECTED_ROLES:
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


def _merge_windows(windows: list[tuple[float, float]]) -> list[tuple[float, float]]:
    merged: list[tuple[float, float]] = []
    for start, end in sorted(windows):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
            continue
        prev_start, prev_end = merged[-1]
        merged[-1] = (prev_start, max(prev_end, end))
    return merged
