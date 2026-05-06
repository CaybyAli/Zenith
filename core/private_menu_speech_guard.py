from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.cut_indicator import CutIndicator, CutIndicatorResult
from models.gameplay_state_result import GameplayStateResult, GameplayStateWindow
from models.round_phase_result import RoundPhaseResult, RoundPhaseWindow
from models.sentence_timeline import SentenceItem, SentenceTimelineResult
from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult, TranscriptSegment


MIN_SEGMENT_DURATION_SECONDS = 2.5
WAIT_DOMINANT_RATIO = 0.50
TRAILING_WAIT_MIN_SECONDS = 2.0
ROUND_END_LOOKBACK_SECONDS = 8.0

_PROTECTED_ROLES = frozenset({"hook", "peak", "payoff"})
_PRIVATE_WAIT_STATES = frozenset({
    "menu_wait",
    "queue_wait",
    "low_motion_wait",
    "possible_dead_time_after_goal",
})
_BROAD_WAIT_STATES = frozenset({
    "menu_wait",
    "queue_wait",
    "low_motion_wait",
    "possible_dead_time_after_goal",
    "round_end",
    "replay_like",
    "scoreboard_like",
})
_ROUND_END_STATES = frozenset({"round_end"})
_ACTION_STATES = frozenset({
    "active_gameplay",
    "high_motion_action",
    "possible_goal_or_flash",
    "possible_pre_action_context",
})
_TRUE_ROUND_START_STATES = frozenset({
    "active_gameplay",
    "high_motion_action",
    "possible_goal_or_flash",
})
_PRIVATE_WAIT_PHASES = frozenset({
    "menu_wait",
    "queue_wait",
    "countdown_kickoff",
})
_BROAD_WAIT_PHASES = frozenset({
    "menu_wait",
    "queue_wait",
    "countdown_kickoff",
    "round_end",
})
_ROUND_END_PHASES = frozenset({"round_end"})
_ACTION_INDICATOR_TYPES = frozenset({
    "high_action_burst",
    "goal_or_save_like_flash",
    "possible_goal_or_flash",
    "sustained_action",
    "shout_like_audio",
    "group_reaction_like",
})
_TRUE_ROUND_START_INDICATOR_TYPES = frozenset({
    "high_action_burst",
    "goal_or_save_like_flash",
    "shout_like_audio",
    "group_reaction_like",
})
_ACTION_AUDIO_TYPES = frozenset({"shout_like_audio", "group_reaction_like"})
_NEUTRAL_SPEECH_TYPES = frozenset({"speech_active", "secondary_speech_like"})
_WAIT_INDICATOR_TYPES = frozenset({
    "menu_or_idle",
    "low_gameplay_value",
    "round_end_dead_time",
    "silence_or_dead_air",
    "filler_sentence",
})


@dataclass
class PrivateMenuSpeechSummary:
    removed: int = 0
    trimmed: int = 0
    round_start_shifted: int = 0
    menu_sentences_removed: int = 0
    active_speech_kept: int = 0
    round_end_protected: int = 0
    overlap_fixed: int = 0
    short_removed: int = 0
    duration_before: float = 0.0
    duration_after: float = 0.0
    examples: list[str] = field(default_factory=list)

    def add_example(self, text: str) -> None:
        if len(self.examples) < 8:
            self.examples.append(text)

    def to_dict(self) -> dict[str, object]:
        return {
            "removed": self.removed,
            "trimmed": self.trimmed,
            "round_start_shifted": self.round_start_shifted,
            "menu_sentences_removed": self.menu_sentences_removed,
            "active_speech_kept": self.active_speech_kept,
            "round_end_protected": self.round_end_protected,
            "overlap_fixed": self.overlap_fixed,
            "short_removed": self.short_removed,
            "duration_before": self.duration_before,
            "duration_after": self.duration_after,
            "examples": list(self.examples),
        }


class PrivateMenuSpeechGuard:
    engine = "private-menu-speech-guard-v1"

    def apply(
        self,
        selected_segments: list[TimelineSegment],
        *,
        gameplay_state_result: GameplayStateResult | None = None,
        round_phase_result: RoundPhaseResult | None = None,
        audio_role_result: AudioRoleResult | None = None,
        cut_indicator_result: CutIndicatorResult | None = None,
        transcript_result: TranscriptResult | None = None,
        sentence_timeline_result: SentenceTimelineResult | None = None,
    ) -> tuple[list[TimelineSegment], PrivateMenuSpeechSummary]:
        ordered = sorted(
            (segment for segment in selected_segments if segment.end_time > segment.start_time),
            key=lambda segment: (segment.start_time, segment.end_time, segment.segment_id),
        )
        summary = PrivateMenuSpeechSummary(
            duration_before=round(sum(segment.duration for segment in ordered), 3)
        )
        states = self._state_windows(gameplay_state_result)
        phases = self._phase_windows(round_phase_result)
        audio_windows = self._audio_windows(audio_role_result)
        indicators = self._indicators(cut_indicator_result)
        transcripts = self._transcripts(transcript_result)
        sentences = self._sentences(sentence_timeline_result)

        kept: list[TimelineSegment] = []
        for segment in ordered:
            original_start = segment.start_time
            original_end = segment.end_time
            self._shift_true_round_start(
                segment,
                states,
                phases,
                indicators,
                audio_windows,
                transcripts,
                sentences,
                summary,
            )
            if segment.end_time <= segment.start_time:
                summary.removed += 1
                summary.add_example(f"{segment.segment_id} removed true_round_start_too_short")
                continue

            round_tension_end = self._round_end_tension_end(
                segment.start_time,
                segment.end_time,
                states,
                phases,
                indicators,
                audio_windows,
            )
            if round_tension_end is not None:
                summary.round_end_protected += 1

            self._trim_trailing_private_wait(
                segment,
                states,
                phases,
                indicators,
                audio_windows,
                transcripts,
                sentences,
                summary,
                protected_until=round_tension_end,
            )
            if segment.end_time <= segment.start_time:
                summary.removed += 1
                summary.add_example(f"{segment.segment_id} removed trailing_wait_too_short")
                continue

            duration = max(segment.duration, 0.001)
            broad_wait_ratio = self._broad_wait_overlap(segment.start_time, segment.end_time, states, phases, indicators) / duration
            private_wait_ratio = self._private_wait_overlap(segment.start_time, segment.end_time, states, phases, indicators) / duration
            state_phase_wait_ratio = self._state_phase_broad_wait_overlap(segment.start_time, segment.end_time, states, phases) / duration
            has_action = self._has_action(segment.start_time, segment.end_time, states, indicators, audio_windows)
            has_speech = self._has_speech(segment.start_time, segment.end_time, audio_windows, transcripts, sentences)

            if (
                not has_action
                and broad_wait_ratio >= WAIT_DOMINANT_RATIO
                and (has_speech or state_phase_wait_ratio >= WAIT_DOMINANT_RATIO)
            ):
                if has_speech or private_wait_ratio > 0.0:
                    summary.menu_sentences_removed += self._menu_sentence_count(
                        segment.start_time,
                        segment.end_time,
                        states,
                        phases,
                        transcripts,
                        sentences,
                    )
                segment.notes.append(f"private_menu_speech_removed={broad_wait_ratio:.3f}")
                summary.removed += 1
                summary.add_example(
                    f"{segment.segment_id} removed private_menu_speech {segment.start_time:.2f}-{segment.end_time:.2f}"
                )
                continue

            if has_speech and self._has_speech_with_action(segment.start_time, segment.end_time, states, indicators, audio_windows, transcripts, sentences):
                summary.active_speech_kept += 1

            if segment.start_time != original_start or segment.end_time != original_end:
                segment.touch()
            kept.append(segment)

        kept = self._cleanup(kept, summary)
        summary.duration_after = round(sum(segment.duration for segment in kept), 3)
        return kept, summary

    def _shift_true_round_start(
        self,
        segment: TimelineSegment,
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
        summary: PrivateMenuSpeechSummary,
    ) -> None:
        action_start = self._first_true_action_start(segment.start_time, segment.end_time, states, indicators, audio_windows)
        if action_start is None or action_start <= segment.start_time + 0.05:
            return
        wait_overlap = self._round_start_wait_overlap(segment.start_time, action_start, states, phases, indicators)
        if wait_overlap / max(action_start - segment.start_time, 0.001) < 0.45:
            return

        proposed = round(action_start, 3)
        proposed, removed_sentences = self._skip_menu_origin_sentence(
            proposed,
            states,
            phases,
            transcripts,
            sentences,
        )
        if segment.end_time - proposed < MIN_SEGMENT_DURATION_SECONDS:
            summary.menu_sentences_removed += removed_sentences + self._menu_sentence_count(
                segment.start_time,
                segment.end_time,
                states,
                phases,
                transcripts,
                sentences,
            )
            segment.notes.append("private_menu_round_start_removed_too_short")
            segment.end_time = segment.start_time
            return

        old = segment.start_time
        segment.start_time = proposed
        segment.notes.append(f"private_menu_true_round_start={old:.3f}->{proposed:.3f}")
        summary.trimmed += 1
        summary.round_start_shifted += 1
        summary.menu_sentences_removed += removed_sentences + self._menu_sentence_count(
            old,
            proposed,
            states,
            phases,
            transcripts,
            sentences,
        )
        summary.add_example(f"{segment.segment_id} start {old:.2f}->{proposed:.2f} true_round_start")

    def _trim_trailing_private_wait(
        self,
        segment: TimelineSegment,
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
        summary: PrivateMenuSpeechSummary,
        *,
        protected_until: float | None,
    ) -> None:
        tail_start = self._trailing_private_wait_start(segment.start_time, segment.end_time, states, phases, indicators)
        if tail_start is None:
            return
        if protected_until is not None and tail_start < protected_until:
            tail_start = protected_until
        tail_start = round(tail_start, 3)
        if segment.end_time - tail_start < TRAILING_WAIT_MIN_SECONDS:
            return
        if self._has_action(tail_start, segment.end_time, states, indicators, audio_windows):
            return
        if tail_start - segment.start_time < MIN_SEGMENT_DURATION_SECONDS:
            return
        old_end = segment.end_time
        segment.end_time = tail_start
        segment.notes.append(f"private_menu_tail_trim={old_end:.3f}->{tail_start:.3f}")
        summary.trimmed += 1
        summary.menu_sentences_removed += self._menu_sentence_count(
            tail_start,
            old_end,
            states,
            phases,
            transcripts,
            sentences,
        )
        summary.add_example(f"{segment.segment_id} end {old_end:.2f}->{tail_start:.2f} private_wait_tail")

    def _cleanup(
        self,
        segments: list[TimelineSegment],
        summary: PrivateMenuSpeechSummary,
    ) -> list[TimelineSegment]:
        kept: list[TimelineSegment] = []
        for segment in sorted(segments, key=lambda item: (item.start_time, item.end_time, item.segment_id)):
            if segment.end_time <= segment.start_time:
                continue
            segment.start_time = round(max(0.0, segment.start_time), 3)
            segment.end_time = round(segment.end_time, 3)
            if segment.duration < MIN_SEGMENT_DURATION_SECONDS and segment.segment_role not in _PROTECTED_ROLES:
                segment.notes.append("private_menu_short_removed")
                summary.short_removed += 1
                summary.removed += 1
                continue
            if kept and segment.start_time < kept[-1].end_time:
                required = round(kept[-1].end_time, 3)
                if segment.end_time - required >= MIN_SEGMENT_DURATION_SECONDS:
                    old = segment.start_time
                    segment.start_time = required
                    segment.notes.append(f"private_menu_overlap_clamped={old:.3f}->{required:.3f}")
                    segment.touch()
                    summary.trimmed += 1
                    summary.overlap_fixed += 1
                elif segment.segment_role not in _PROTECTED_ROLES:
                    segment.notes.append("private_menu_overlap_removed")
                    summary.removed += 1
                    summary.overlap_fixed += 1
                    continue
                else:
                    previous_end = round(segment.start_time, 3)
                    previous = kept[-1]
                    if previous.segment_role not in _PROTECTED_ROLES and previous_end - previous.start_time >= MIN_SEGMENT_DURATION_SECONDS:
                        previous.end_time = previous_end
                        previous.notes.append(f"private_menu_overlap_prev_trim={previous_end:.3f}")
                        previous.touch()
                        summary.trimmed += 1
                        summary.overlap_fixed += 1
                    else:
                        segment.notes.append("private_menu_protected_overlap_removed")
                        summary.removed += 1
                        summary.overlap_fixed += 1
                        continue
            kept.append(segment)
        return kept

    def _first_true_action_start(
        self,
        start: float,
        end: float,
        states: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
    ) -> float | None:
        candidates: list[float] = []
        candidates.extend(
            state.start_seconds
            for state in states
            if state.state_type in _TRUE_ROUND_START_STATES
            and start < state.start_seconds < end
        )
        candidates.extend(
            indicator.start_seconds
            for indicator in indicators
            if indicator.indicator_type in _TRUE_ROUND_START_INDICATOR_TYPES
            and start < indicator.start_seconds < end
        )
        candidates.extend(
            window.start_seconds
            for window in audio_windows
            if window.role_type in _ACTION_AUDIO_TYPES
            and start < window.start_seconds < end
        )
        return min(candidates) if candidates else None

    def _trailing_private_wait_start(
        self,
        start: float,
        end: float,
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
    ) -> float | None:
        windows = self._private_wait_windows(states, phases, indicators)
        for window_start, window_end in reversed(_merge_windows(windows)):
            if window_end < end - 0.2:
                continue
            if window_start <= start + 0.05:
                continue
            return max(start, window_start)
        return None

    def _round_end_tension_end(
        self,
        start: float,
        end: float,
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
    ) -> float | None:
        round_windows: list[tuple[float, float]] = []
        round_windows.extend((state.start_seconds, state.end_seconds) for state in states if state.state_type in _ROUND_END_STATES)
        round_windows.extend((phase.start_seconds, phase.end_seconds) for phase in phases if self._phase_value(phase) in _ROUND_END_PHASES)
        protected_ends: list[float] = []
        for round_start, round_end in round_windows:
            if _overlap_seconds(start, end, round_start, round_end) <= 0.0:
                continue
            lookback_start = max(0.0, round_start - ROUND_END_LOOKBACK_SECONDS)
            if self._has_action(lookback_start, round_start, states, indicators, audio_windows):
                protected_ends.append(min(end, round_end))
        return max(protected_ends) if protected_ends else None

    def _has_action(
        self,
        start: float,
        end: float,
        states: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
    ) -> bool:
        return any(
            state.state_type in _ACTION_STATES
            and _overlap_seconds(start, end, state.start_seconds, state.end_seconds) >= 0.2
            for state in states
        ) or any(
            indicator.indicator_type in _ACTION_INDICATOR_TYPES
            and _overlap_seconds(start, end, indicator.start_seconds, indicator.end_seconds) >= 0.2
            for indicator in indicators
        ) or any(
            window.role_type in _ACTION_AUDIO_TYPES
            and _overlap_seconds(start, end, window.start_seconds, window.end_seconds) >= 0.2
            for window in audio_windows
        )

    def _has_speech(
        self,
        start: float,
        end: float,
        audio_windows: list[AudioRoleWindow],
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
    ) -> bool:
        return any(
            window.role_type in _NEUTRAL_SPEECH_TYPES
            and _overlap_seconds(start, end, window.start_seconds, window.end_seconds) >= 0.2
            for window in audio_windows
        ) or any(
            _overlap_seconds(start, end, item.start_seconds, item.end_seconds) >= 0.2
            for item in [*transcripts, *sentences]
        )

    def _has_speech_with_action(
        self,
        start: float,
        end: float,
        states: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
    ) -> bool:
        action_windows = self._action_windows(states, indicators, audio_windows)
        speech_windows: list[tuple[float, float]] = []
        speech_windows.extend(
            (window.start_seconds, window.end_seconds)
            for window in audio_windows
            if window.role_type in _NEUTRAL_SPEECH_TYPES
        )
        speech_windows.extend((item.start_seconds, item.end_seconds) for item in [*transcripts, *sentences])
        for speech_start, speech_end in speech_windows:
            if _overlap_seconds(start, end, speech_start, speech_end) <= 0.0:
                continue
            if any(
                _overlap_seconds(
                    max(start, speech_start),
                    min(end, speech_end),
                    action_start,
                    action_end,
                ) >= 0.2
                for action_start, action_end in action_windows
            ):
                return True
        return False

    def _private_wait_overlap(
        self,
        start: float,
        end: float,
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
    ) -> float:
        return _overlap_merged_seconds(start, end, self._private_wait_windows(states, phases, indicators))

    def _broad_wait_overlap(
        self,
        start: float,
        end: float,
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
    ) -> float:
        windows: list[tuple[float, float]] = []
        windows.extend((state.start_seconds, state.end_seconds) for state in states if state.state_type in _BROAD_WAIT_STATES)
        windows.extend((phase.start_seconds, phase.end_seconds) for phase in phases if self._phase_value(phase) in _BROAD_WAIT_PHASES)
        windows.extend((indicator.start_seconds, indicator.end_seconds) for indicator in indicators if indicator.indicator_type in _WAIT_INDICATOR_TYPES)
        return _overlap_merged_seconds(start, end, windows)

    def _state_phase_broad_wait_overlap(
        self,
        start: float,
        end: float,
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
    ) -> float:
        windows: list[tuple[float, float]] = []
        windows.extend((state.start_seconds, state.end_seconds) for state in states if state.state_type in _BROAD_WAIT_STATES)
        windows.extend((phase.start_seconds, phase.end_seconds) for phase in phases if self._phase_value(phase) in _BROAD_WAIT_PHASES)
        return _overlap_merged_seconds(start, end, windows)

    def _round_start_wait_overlap(
        self,
        start: float,
        end: float,
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
    ) -> float:
        return self._private_wait_overlap(start, end, states, phases, indicators)

    def _private_wait_windows(
        self,
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
    ) -> list[tuple[float, float]]:
        windows: list[tuple[float, float]] = []
        windows.extend((state.start_seconds, state.end_seconds) for state in states if state.state_type in _PRIVATE_WAIT_STATES)
        windows.extend((phase.start_seconds, phase.end_seconds) for phase in phases if self._phase_value(phase) in _PRIVATE_WAIT_PHASES)
        windows.extend((indicator.start_seconds, indicator.end_seconds) for indicator in indicators if indicator.indicator_type in _WAIT_INDICATOR_TYPES)
        return windows

    def _action_windows(
        self,
        states: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
    ) -> list[tuple[float, float]]:
        windows: list[tuple[float, float]] = []
        windows.extend((state.start_seconds, state.end_seconds) for state in states if state.state_type in _ACTION_STATES)
        windows.extend((indicator.start_seconds, indicator.end_seconds) for indicator in indicators if indicator.indicator_type in _ACTION_INDICATOR_TYPES)
        windows.extend((window.start_seconds, window.end_seconds) for window in audio_windows if window.role_type in _ACTION_AUDIO_TYPES)
        return _merge_windows(windows)

    def _menu_sentence_count(
        self,
        start: float,
        end: float,
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
    ) -> int:
        count = 0
        for item in [*transcripts, *sentences]:
            item_start = max(start, item.start_seconds)
            item_end = min(end, item.end_seconds)
            if item_end <= item_start:
                continue
            wait_overlap = _overlap_merged_seconds(
                item_start,
                item_end,
                [
                    (state.start_seconds, state.end_seconds)
                    for state in states
                    if state.state_type in _PRIVATE_WAIT_STATES
                ]
                + [
                    (phase.start_seconds, phase.end_seconds)
                    for phase in phases
                    if self._phase_value(phase) in _PRIVATE_WAIT_PHASES
                ],
            )
            if wait_overlap / max(item_end - item_start, 0.001) >= WAIT_DOMINANT_RATIO:
                count += 1
        return count

    def _skip_menu_origin_sentence(
        self,
        proposed: float,
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
    ) -> tuple[float, int]:
        shifted = proposed
        removed = 0
        for item in sorted([*transcripts, *sentences], key=lambda source: (source.start_seconds, source.end_seconds)):
            if not (item.start_seconds < shifted < item.end_seconds):
                continue
            wait_overlap = _overlap_merged_seconds(
                item.start_seconds,
                shifted,
                [
                    (state.start_seconds, state.end_seconds)
                    for state in states
                    if state.state_type in _PRIVATE_WAIT_STATES
                ]
                + [
                    (phase.start_seconds, phase.end_seconds)
                    for phase in phases
                    if self._phase_value(phase) in _PRIVATE_WAIT_PHASES
                ],
            )
            if wait_overlap / max(shifted - item.start_seconds, 0.001) < WAIT_DOMINANT_RATIO:
                continue
            shifted = round(max(shifted, item.end_seconds), 3)
            removed += 1
        return shifted, removed

    def _state_windows(self, result: GameplayStateResult | None) -> list[GameplayStateWindow]:
        if result is None:
            return []
        windows = result.get("windows", []) if isinstance(result, dict) else getattr(result, "windows", [])
        parsed: list[GameplayStateWindow] = []
        for window in windows or []:
            state = window if isinstance(window, GameplayStateWindow) else GameplayStateWindow.from_dict(window)
            if state.end_seconds > state.start_seconds:
                parsed.append(state)
        return sorted(parsed, key=lambda state: (state.start_seconds, state.end_seconds, state.state_type))

    def _phase_windows(self, result: RoundPhaseResult | None) -> list[RoundPhaseWindow]:
        if result is None:
            return []
        windows = result.get("windows", []) if isinstance(result, dict) else getattr(result, "windows", [])
        parsed: list[RoundPhaseWindow] = []
        for window in windows or []:
            if isinstance(window, RoundPhaseWindow):
                phase = window
            elif isinstance(window, dict):
                phase = RoundPhaseWindow(
                    start_seconds=window.get("start_seconds", 0.0),
                    end_seconds=window.get("end_seconds", window.get("start_seconds", 0.0)),
                    phase=window.get("phase", "unknown"),
                    confidence=window.get("confidence", 0.0),
                    evidence=dict(window.get("evidence") or {}),
                )
            else:
                continue
            if phase.end_seconds > phase.start_seconds:
                parsed.append(phase)
        return sorted(parsed, key=lambda phase: (phase.start_seconds, phase.end_seconds, self._phase_value(phase)))

    def _phase_value(self, phase: RoundPhaseWindow) -> str:
        value = phase.phase
        if isinstance(value, Enum):
            return str(value.value)
        return str(value)

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

    def _transcripts(self, result: TranscriptResult | None) -> list[TranscriptSegment]:
        if result is None:
            return []
        return sorted(
            (segment for segment in result.segments if segment.end_seconds > segment.start_seconds),
            key=lambda segment: (segment.start_seconds, segment.end_seconds),
        )

    def _sentences(self, result: SentenceTimelineResult | None) -> list[SentenceItem]:
        if result is None:
            return []
        return sorted(
            (sentence for sentence in result.sentences if sentence.end_seconds > sentence.start_seconds),
            key=lambda sentence: (sentence.start_seconds, sentence.end_seconds),
        )


def _overlap_seconds(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def _merge_windows(windows: list[tuple[float, float]]) -> list[tuple[float, float]]:
    merged: list[tuple[float, float]] = []
    for start, end in sorted((s, e) for s, e in windows if e > s):
        if not merged or start > merged[-1][1]:
            merged.append((start, end))
            continue
        previous_start, previous_end = merged[-1]
        merged[-1] = (previous_start, max(previous_end, end))
    return merged


def _overlap_merged_seconds(start: float, end: float, windows: list[tuple[float, float]]) -> float:
    return round(
        sum(
            _overlap_seconds(start, end, window_start, window_end)
            for window_start, window_end in _merge_windows(windows)
        ),
        3,
    )
