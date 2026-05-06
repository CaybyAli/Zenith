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
MIN_FINAL_GAP_SECONDS = 0.18
MICRO_CUT_GAP_SECONDS = 1.25
BORING_WAIT_MIN_SECONDS = 3.0
LONG_WAIT_MIN_SECONDS = 6.0
ROUND_START_GRACE_SECONDS = 10.0
ROUND_END_PROTECTION_SECONDS = 12.0
ACTION_CONTEXT_BACKFILL_SECONDS = 2.5
MAX_SAFE_TRIM_SECONDS = 12.0
SPEECH_IMPORTANCE_THRESHOLD = 0.65

_PROTECTED_ROLES = frozenset({"hook", "peak", "payoff"})
_TARGET_ROLES = frozenset({"build", "bridge"})
_WAIT_STATES = frozenset({
    "menu_wait",
    "low_motion_wait",
    "possible_dead_time_after_goal",
    "round_end",
    "replay_like",
    "scoreboard_like",
})
_ROUND_START_STATES = frozenset({
    "menu_wait",
    "low_motion_wait",
    "possible_dead_time_after_goal",
    "round_end",
    "replay_like",
    "scoreboard_like",
})
_ACTION_STATES = frozenset({
    "active_gameplay",
    "high_motion_action",
    "possible_goal_or_flash",
    "possible_pre_action_context",
})
_STRONG_ACTION_STATES = frozenset({
    "active_gameplay",
    "high_motion_action",
    "possible_goal_or_flash",
})
_SPEECH_BLOCKING_WAIT_STATES = frozenset({
    "menu_wait",
    "low_motion_wait",
    "possible_dead_time_after_goal",
})
_WAIT_PHASES = frozenset({
    "menu_wait",
    "queue_wait",
    "countdown_kickoff",
    "round_end",
})
_ROUND_START_PHASES = frozenset({
    "menu_wait",
    "queue_wait",
    "countdown_kickoff",
})
_ROUND_END_PHASES = frozenset({"round_end", "goal_replay"})
_WAIT_INDICATOR_TYPES = frozenset({
    "menu_or_idle",
    "low_gameplay_value",
    "round_end_dead_time",
    "silence_or_dead_air",
    "filler_sentence",
})
_ACTION_INDICATOR_TYPES = frozenset({
    "high_action_burst",
    "goal_or_save_like_flash",
    "sustained_action",
    "facecam_reaction_spike",
})
_GOAL_INDICATOR_TYPES = frozenset({"goal_or_save_like_flash"})
_SHOUT_TYPES = frozenset({
    "shout_like_audio",
    "group_reaction_like",
    "laugh_like_audio",
})
_IMPORTANT_AUDIO_TYPES = frozenset({
    "shout_like_audio",
    "group_reaction_like",
    "laugh_like_audio",
    "secondary_speech_like",
})
_NEUTRAL_SPEECH_TYPES = frozenset({"speech_active"})
_IMPORTANT_PHRASES = (
    "leo",
    "parade",
    "alles gut",
    "oh gott",
    "wichtig",
    "verstehe",
    "warum siehst du",
    "nicht",
    "scheisse",
    "scheiße",
    "was",
    "nein",
)


@dataclass
class SpeechSafePacingSummary:
    micro_gaps_closed: int = 0
    micro_gaps_spaced: int = 0
    micro_segments_removed: int = 0
    boring_wait_removed: int = 0
    boring_wait_trimmed: int = 0
    neutral_speech_ignored: int = 0
    round_end_context_expanded: int = 0
    round_end_protected: int = 0
    round_start_wait_trimmed: int = 0
    round_start_wait_removed: int = 0
    action_context_expanded: int = 0
    duration_before: float = 0.0
    duration_after: float = 0.0
    examples: list[str] = field(default_factory=list)

    @property
    def micro_fixed(self) -> int:
        return self.micro_gaps_closed + self.micro_gaps_spaced + self.micro_segments_removed

    def add_example(self, text: str) -> None:
        if len(self.examples) < 8:
            self.examples.append(text)

    def to_dict(self) -> dict[str, object]:
        return {
            "micro_gaps_closed": self.micro_gaps_closed,
            "micro_gaps_spaced": self.micro_gaps_spaced,
            "micro_segments_removed": self.micro_segments_removed,
            "micro_fixed": self.micro_fixed,
            "boring_wait_removed": self.boring_wait_removed,
            "boring_wait_trimmed": self.boring_wait_trimmed,
            "neutral_speech_ignored": self.neutral_speech_ignored,
            "round_end_context_expanded": self.round_end_context_expanded,
            "round_end_protected": self.round_end_protected,
            "round_start_wait_trimmed": self.round_start_wait_trimmed,
            "round_start_wait_removed": self.round_start_wait_removed,
            "action_context_expanded": self.action_context_expanded,
            "duration_before": self.duration_before,
            "duration_after": self.duration_after,
            "examples": list(self.examples),
        }


class SpeechSafePacingGuard:
    engine = "speech-safe-pacing-guard-v1"

    def apply(
        self,
        selected_segments: list[TimelineSegment],
        *,
        gameplay_state_result: GameplayStateResult | None = None,
        round_phase_result: RoundPhaseResult | None = None,
        cut_indicator_result: CutIndicatorResult | None = None,
        audio_role_result: AudioRoleResult | None = None,
        transcript_result: TranscriptResult | None = None,
        sentence_timeline_result: SentenceTimelineResult | None = None,
    ) -> tuple[list[TimelineSegment], SpeechSafePacingSummary]:
        ordered = sorted(
            (segment for segment in selected_segments if segment.end_time > segment.start_time),
            key=lambda segment: (segment.start_time, segment.end_time, segment.segment_id),
        )
        summary = SpeechSafePacingSummary(
            duration_before=round(sum(segment.duration for segment in ordered), 3)
        )
        states = self._state_windows(gameplay_state_result)
        phases = self._phase_windows(round_phase_result)
        indicators = self._indicators(cut_indicator_result)
        audio_windows = self._audio_windows(audio_role_result)
        transcripts = self._transcripts(transcript_result)
        sentences = self._sentences(sentence_timeline_result)

        self._protect_round_end_tension(ordered, states, phases, indicators, audio_windows, summary)
        self._trim_round_start_wait(ordered, states, phases, indicators, audio_windows, transcripts, sentences, summary)
        self._expand_action_context(ordered, states, phases, indicators, audio_windows, summary)
        ordered = self._trim_or_remove_boring_waits(
            ordered,
            states,
            phases,
            indicators,
            audio_windows,
            transcripts,
            sentences,
            summary,
        )
        self._kill_final_micro_cuts(ordered, states, indicators, audio_windows, transcripts, sentences, summary)
        ordered = self._final_cleanup(ordered, summary)
        summary.duration_after = round(sum(segment.duration for segment in ordered), 3)
        return ordered, summary

    def _protect_round_end_tension(
        self,
        segments: list[TimelineSegment],
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        summary: SpeechSafePacingSummary,
    ) -> None:
        for index, segment in enumerate(segments):
            if not self._has_round_end_window(segment.start_time, segment.end_time, states, phases):
                continue
            if not self._has_recent_strong_action(
                segment.start_time,
                states,
                indicators,
                audio_windows,
                lookback_seconds=ROUND_END_PROTECTION_SECONDS,
            ):
                continue
            summary.round_end_protected += 1
            previous = segments[index - 1] if index > 0 else None
            previous_limit = previous.end_time if previous is not None else 0.0
            preferred = round(max(previous_limit, max(0.0, segment.start_time - ACTION_CONTEXT_BACKFILL_SECONDS)), 3)
            if preferred >= segment.start_time:
                continue
            if segment.end_time - preferred < MIN_SEGMENT_DURATION_SECONDS:
                continue
            old = segment.start_time
            segment.start_time = preferred
            segment.notes.append(f"pacing_round_end_context={old:.3f}->{preferred:.3f}")
            segment.touch()
            summary.round_end_context_expanded += 1
            summary.add_example(f"{segment.segment_id} expanded round_end {old:.2f}->{preferred:.2f}")

    def _trim_round_start_wait(
        self,
        segments: list[TimelineSegment],
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
        summary: SpeechSafePacingSummary,
    ) -> None:
        for segment in segments:
            if segment.segment_role not in _TARGET_ROLES:
                continue
            action_start = self._first_action_start(segment.start_time, segment.end_time, states, indicators)
            if action_start is None:
                continue
            wait_end = min(action_start, segment.end_time)
            wait_duration = wait_end - segment.start_time
            if wait_duration < ROUND_START_GRACE_SECONDS:
                continue
            wait_overlap = self._round_start_wait_overlap(segment.start_time, wait_end, states, phases, indicators, audio_windows)
            if wait_overlap < LONG_WAIT_MIN_SECONDS:
                continue
            if self._has_important_speech(
                segment.start_time,
                wait_end,
                states,
                phases,
                transcripts,
                sentences,
                audio_windows,
                indicators,
            ):
                continue
            if self._has_neutral_speech(segment.start_time, wait_end, audio_windows, indicators):
                summary.neutral_speech_ignored += 1
            preferred = round(max(segment.start_time, action_start - 1.0), 3)
            if preferred <= segment.start_time:
                continue
            if segment.end_time - preferred >= MIN_SEGMENT_DURATION_SECONDS:
                old = segment.start_time
                segment.start_time = preferred
                segment.notes.append(f"pacing_round_start_trim={old:.3f}->{preferred:.3f}")
                segment.touch()
                summary.round_start_wait_trimmed += 1
                summary.add_example(f"{segment.segment_id} trimmed round_start {old:.2f}->{preferred:.2f}")
            elif segment.segment_role not in _PROTECTED_ROLES:
                segment.end_time = segment.start_time
                segment.notes.append("pacing_round_start_removed")
                summary.round_start_wait_removed += 1
                summary.add_example(f"{segment.segment_id} removed round_start_wait")

    def _expand_action_context(
        self,
        segments: list[TimelineSegment],
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        summary: SpeechSafePacingSummary,
    ) -> None:
        for index, segment in enumerate(segments):
            previous = segments[index - 1] if index > 0 else None
            previous_limit = previous.end_time if previous is not None else 0.0
            trigger_start = self._action_trigger_near_start(segment, states, indicators, audio_windows)
            if trigger_start is None:
                continue
            preferred = round(max(previous_limit, max(0.0, trigger_start - ACTION_CONTEXT_BACKFILL_SECONDS)), 3)
            if preferred >= segment.start_time:
                continue
            if segment.start_time - preferred > MAX_SAFE_TRIM_SECONDS:
                preferred = round(segment.start_time - MAX_SAFE_TRIM_SECONDS, 3)
            if self._round_start_wait_overlap(preferred, segment.start_time, states, phases, indicators, audio_windows) > 0.0:
                continue
            if self._wait_or_silence_dominates(preferred, segment.start_time, states, phases, indicators, audio_windows):
                continue
            if segment.end_time - preferred < MIN_SEGMENT_DURATION_SECONDS:
                continue
            old = segment.start_time
            segment.start_time = preferred
            segment.notes.append(f"pacing_action_context={old:.3f}->{preferred:.3f}")
            segment.touch()
            summary.action_context_expanded += 1
            summary.add_example(f"{segment.segment_id} expanded action {old:.2f}->{preferred:.2f}")

    def _trim_or_remove_boring_waits(
        self,
        segments: list[TimelineSegment],
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
        summary: SpeechSafePacingSummary,
    ) -> list[TimelineSegment]:
        kept: list[TimelineSegment] = []
        for segment in segments:
            if segment.end_time <= segment.start_time:
                continue
            if segment.segment_role not in _TARGET_ROLES or segment.duration < BORING_WAIT_MIN_SECONDS:
                kept.append(segment)
                continue
            if self._has_strong_action(segment.start_time, segment.end_time, states, indicators, audio_windows):
                kept.append(segment)
                continue
            if self._has_round_end_tension(segment, states, phases, indicators, audio_windows):
                summary.round_end_protected += 1
                kept.append(segment)
                continue

            wait_overlap = self._wait_overlap(segment.start_time, segment.end_time, states, phases, indicators, audio_windows)
            wait_ratio = wait_overlap / max(segment.duration, 0.001)
            if wait_overlap < BORING_WAIT_MIN_SECONDS or wait_ratio < 0.45:
                kept.append(segment)
                continue

            important_windows = self._important_speech_windows(
                segment.start_time,
                segment.end_time,
                states,
                phases,
                transcripts,
                sentences,
                audio_windows,
                indicators,
            )
            if not important_windows:
                if self._has_neutral_speech(segment.start_time, segment.end_time, audio_windows, indicators):
                    summary.neutral_speech_ignored += 1
                segment.notes.append(f"pacing_boring_wait_removed={wait_ratio:.3f}")
                summary.boring_wait_removed += 1
                summary.add_example(f"{segment.segment_id} removed boring_wait")
                continue

            keep_start = round(max(segment.start_time, min(start for start, _ in important_windows) - 0.25), 3)
            keep_end = round(min(segment.end_time, max(end for _, end in important_windows) + 0.35), 3)
            if keep_end - keep_start < MIN_SEGMENT_DURATION_SECONDS:
                kept.append(segment)
                continue
            if keep_start <= segment.start_time + 0.05 and keep_end >= segment.end_time - 0.05:
                kept.append(segment)
                continue
            old_start = segment.start_time
            old_end = segment.end_time
            segment.start_time = keep_start
            segment.end_time = keep_end
            segment.notes.append(
                f"pacing_boring_wait_trim={old_start:.3f}-{old_end:.3f}->{keep_start:.3f}-{keep_end:.3f}"
            )
            segment.touch()
            summary.boring_wait_trimmed += 1
            summary.add_example(f"{segment.segment_id} trimmed boring_wait {old_start:.2f}-{old_end:.2f}->{keep_start:.2f}-{keep_end:.2f}")
            kept.append(segment)
        return kept

    def _kill_final_micro_cuts(
        self,
        segments: list[TimelineSegment],
        states: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
        summary: SpeechSafePacingSummary,
    ) -> None:
        for index in range(len(segments) - 1):
            current = segments[index]
            next_segment = segments[index + 1]
            if current.end_time <= current.start_time or next_segment.end_time <= next_segment.start_time:
                continue
            gap = round(next_segment.start_time - current.end_time, 3)
            if gap < 0.0 or gap >= MICRO_CUT_GAP_SECONDS:
                continue
            if self._continuous_speech_or_action(current.end_time, next_segment.start_time, states, indicators, audio_windows, transcripts, sentences):
                old = current.end_time
                current.end_time = round(next_segment.start_time, 3)
                current.notes.append(f"pacing_micro_gap_closed={old:.3f}->{current.end_time:.3f}")
                current.touch()
                summary.micro_gaps_closed += 1
                summary.add_example(f"{current.segment_id} closed micro_gap {gap:.2f}s")
                continue
            if gap >= MIN_FINAL_GAP_SECONDS:
                continue
            required = round(current.end_time + MIN_FINAL_GAP_SECONDS, 3)
            if next_segment.end_time - required >= MIN_SEGMENT_DURATION_SECONDS:
                old_start = next_segment.start_time
                next_segment.start_time = required
                next_segment.notes.append(f"pacing_micro_gap_spaced={old_start:.3f}->{required:.3f}")
                next_segment.touch()
                summary.micro_gaps_spaced += 1
                summary.add_example(f"{next_segment.segment_id} spaced micro_gap {gap:.2f}s")
            elif next_segment.segment_role not in _PROTECTED_ROLES:
                next_segment.end_time = next_segment.start_time
                next_segment.notes.append("pacing_micro_segment_removed")
                summary.micro_segments_removed += 1
                summary.add_example(f"{next_segment.segment_id} removed micro_segment")

    def _final_cleanup(
        self,
        segments: list[TimelineSegment],
        summary: SpeechSafePacingSummary,
    ) -> list[TimelineSegment]:
        kept: list[TimelineSegment] = []
        for segment in sorted(segments, key=lambda item: (item.start_time, item.end_time, item.segment_id)):
            if segment.end_time <= segment.start_time:
                continue
            segment.start_time = round(max(0.0, segment.start_time), 3)
            segment.end_time = round(segment.end_time, 3)
            if segment.duration < MIN_SEGMENT_DURATION_SECONDS and segment.segment_role not in _PROTECTED_ROLES:
                summary.micro_segments_removed += 1
                segment.notes.append("pacing_final_short_removed")
                continue
            if kept and segment.start_time < kept[-1].end_time:
                required_start = round(kept[-1].end_time, 3)
                if segment.end_time - required_start >= MIN_SEGMENT_DURATION_SECONDS:
                    old_start = segment.start_time
                    segment.start_time = required_start
                    segment.notes.append(f"pacing_overlap_clamped={old_start:.3f}->{required_start:.3f}")
                    segment.touch()
                elif segment.segment_role not in _PROTECTED_ROLES:
                    summary.micro_segments_removed += 1
                    segment.notes.append("pacing_overlap_removed")
                    continue
                else:
                    prev_end = round(segment.start_time, 3)
                    if kept[-1].segment_role not in _PROTECTED_ROLES and prev_end - kept[-1].start_time >= MIN_SEGMENT_DURATION_SECONDS:
                        kept[-1].end_time = prev_end
                        kept[-1].notes.append(f"pacing_overlap_prev_trim={prev_end:.3f}")
                        kept[-1].touch()
                    else:
                        summary.micro_segments_removed += 1
                        segment.notes.append("pacing_overlap_protected_removed")
                        continue
            segment.touch()
            kept.append(segment)
        return kept

    def _first_action_start(
        self,
        start: float,
        end: float,
        states: list[GameplayStateWindow],
        indicators: list[CutIndicator],
    ) -> float | None:
        starts: list[float] = [
            state.start_seconds
            for state in states
            if state.state_type in _STRONG_ACTION_STATES and start < state.start_seconds < end
        ]
        starts.extend(
            indicator.start_seconds
            for indicator in indicators
            if indicator.indicator_type in (_ACTION_INDICATOR_TYPES | _SHOUT_TYPES)
            and start < indicator.start_seconds < end
        )
        return min(starts) if starts else None

    def _action_trigger_near_start(
        self,
        segment: TimelineSegment,
        states: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
    ) -> float | None:
        candidates: list[float] = []
        window_start = max(0.0, segment.start_time - 1.0)
        window_end = segment.start_time + 1.0
        candidates.extend(
            state.start_seconds
            for state in states
            if state.state_type in _ACTION_STATES
            and window_start <= state.start_seconds <= window_end
        )
        candidates.extend(
            indicator.start_seconds
            for indicator in indicators
            if indicator.indicator_type in (_ACTION_INDICATOR_TYPES | _SHOUT_TYPES)
            and window_start <= indicator.start_seconds <= window_end
        )
        candidates.extend(
            window.start_seconds
            for window in audio_windows
            if window.role_type in _SHOUT_TYPES
            and window_start <= window.start_seconds <= window_end
        )
        return min(candidates) if candidates else None

    def _wait_overlap(
        self,
        start: float,
        end: float,
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
    ) -> float:
        windows: list[tuple[float, float]] = []
        windows.extend((state.start_seconds, state.end_seconds) for state in states if state.state_type in _WAIT_STATES)
        windows.extend((phase.start_seconds, phase.end_seconds) for phase in phases if self._phase_value(phase) in _WAIT_PHASES)
        windows.extend((indicator.start_seconds, indicator.end_seconds) for indicator in indicators if indicator.indicator_type in _WAIT_INDICATOR_TYPES)
        windows.extend((window.start_seconds, window.end_seconds) for window in audio_windows if window.role_type == "silence_or_dead_air")
        return _overlap_merged_seconds(start, end, windows)

    def _round_start_wait_overlap(
        self,
        start: float,
        end: float,
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
    ) -> float:
        windows: list[tuple[float, float]] = []
        windows.extend((state.start_seconds, state.end_seconds) for state in states if state.state_type in _ROUND_START_STATES)
        windows.extend((phase.start_seconds, phase.end_seconds) for phase in phases if self._phase_value(phase) in _ROUND_START_PHASES)
        windows.extend((indicator.start_seconds, indicator.end_seconds) for indicator in indicators if indicator.indicator_type in {"menu_or_idle", "low_gameplay_value", "silence_or_dead_air"})
        windows.extend((window.start_seconds, window.end_seconds) for window in audio_windows if window.role_type == "silence_or_dead_air")
        return _overlap_merged_seconds(start, end, windows)

    def _wait_or_silence_dominates(
        self,
        start: float,
        end: float,
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
    ) -> bool:
        if end <= start:
            return False
        overlap = self._wait_overlap(start, end, states, phases, indicators, audio_windows)
        return overlap / max(end - start, 0.001) >= 0.50

    def _has_strong_action(
        self,
        start: float,
        end: float,
        states: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
    ) -> bool:
        return any(
            state.state_type in _STRONG_ACTION_STATES
            and _overlap_seconds(start, end, state.start_seconds, state.end_seconds) >= 0.25
            for state in states
        ) or any(
            indicator.indicator_type in (_ACTION_INDICATOR_TYPES | _SHOUT_TYPES)
            and _overlap_seconds(start, end, indicator.start_seconds, indicator.end_seconds) >= 0.25
            for indicator in indicators
        ) or any(
            window.role_type in _SHOUT_TYPES
            and _overlap_seconds(start, end, window.start_seconds, window.end_seconds) >= 0.25
            for window in audio_windows
        )

    def _has_round_end_tension(
        self,
        segment: TimelineSegment,
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
    ) -> bool:
        if not self._has_round_end_window(segment.start_time, segment.end_time, states, phases):
            return False
        return self._has_recent_strong_action(
            segment.start_time,
            states,
            indicators,
            audio_windows,
            lookback_seconds=ROUND_END_PROTECTION_SECONDS,
        )

    def _has_round_end_window(
        self,
        start: float,
        end: float,
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
    ) -> bool:
        return any(
            state.state_type in {"round_end", "possible_dead_time_after_goal"}
            and _overlap_seconds(start, end, state.start_seconds, state.end_seconds) > 0.0
            for state in states
        ) or any(
            self._phase_value(phase) in _ROUND_END_PHASES
            and _overlap_seconds(start, end, phase.start_seconds, phase.end_seconds) > 0.0
            for phase in phases
        )

    def _has_recent_strong_action(
        self,
        boundary: float,
        states: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        *,
        lookback_seconds: float,
    ) -> bool:
        start = max(0.0, boundary - lookback_seconds)
        return any(
            state.state_type in _STRONG_ACTION_STATES
            and _overlap_seconds(start, boundary, state.start_seconds, state.end_seconds) > 0.0
            for state in states
        ) or any(
            indicator.indicator_type in (_ACTION_INDICATOR_TYPES | _SHOUT_TYPES)
            and _overlap_seconds(start, boundary, indicator.start_seconds, indicator.end_seconds) > 0.0
            for indicator in indicators
        ) or any(
            window.role_type in _SHOUT_TYPES
            and _overlap_seconds(start, boundary, window.start_seconds, window.end_seconds) > 0.0
            for window in audio_windows
        )

    def _has_important_speech(
        self,
        start: float,
        end: float,
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
        audio_windows: list[AudioRoleWindow],
        indicators: list[CutIndicator],
    ) -> bool:
        return bool(
            self._important_speech_windows(
                start,
                end,
                states,
                phases,
                transcripts,
                sentences,
                audio_windows,
                indicators,
            )
        )

    def _important_speech_windows(
        self,
        start: float,
        end: float,
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
        audio_windows: list[AudioRoleWindow],
        indicators: list[CutIndicator],
    ) -> list[tuple[float, float]]:
        windows: list[tuple[float, float]] = []
        for transcript in transcripts:
            if _overlap_seconds(start, end, transcript.start_seconds, transcript.end_seconds) <= 0.0:
                continue
            if self._speech_blocked_by_wait(
                transcript.start_seconds,
                transcript.end_seconds,
                states,
                phases,
                indicators,
                audio_windows,
            ):
                continue
            confidence = transcript.confidence if transcript.confidence is not None else 0.0
            if confidence >= SPEECH_IMPORTANCE_THRESHOLD or self._has_important_phrase(transcript.text):
                windows.append((transcript.start_seconds, transcript.end_seconds))
        for sentence in sentences:
            if _overlap_seconds(start, end, sentence.start_seconds, sentence.end_seconds) <= 0.0:
                continue
            if self._speech_blocked_by_wait(
                sentence.start_seconds,
                sentence.end_seconds,
                states,
                phases,
                indicators,
                audio_windows,
            ):
                continue
            if (
                sentence.score >= SPEECH_IMPORTANCE_THRESHOLD
                and sentence.confidence >= SPEECH_IMPORTANCE_THRESHOLD
                and sentence.sentence_kind != "filler"
            ) or self._has_important_phrase(sentence.text):
                windows.append((sentence.start_seconds, sentence.end_seconds))
        for window in audio_windows:
            if window.role_type in _IMPORTANT_AUDIO_TYPES and _overlap_seconds(start, end, window.start_seconds, window.end_seconds) > 0.0:
                if self._speech_blocked_by_wait(
                    window.start_seconds,
                    window.end_seconds,
                    states,
                    phases,
                    indicators,
                    audio_windows,
                ):
                    continue
                if max(window.score, window.confidence) >= SPEECH_IMPORTANCE_THRESHOLD:
                    windows.append((window.start_seconds, window.end_seconds))
        for indicator in indicators:
            if indicator.indicator_type in _SHOUT_TYPES and _overlap_seconds(start, end, indicator.start_seconds, indicator.end_seconds) > 0.0:
                if max(indicator.score, indicator.confidence) >= SPEECH_IMPORTANCE_THRESHOLD:
                    windows.append((indicator.start_seconds, indicator.end_seconds))
        return _merge_windows(windows)

    def _has_neutral_speech(
        self,
        start: float,
        end: float,
        audio_windows: list[AudioRoleWindow],
        indicators: list[CutIndicator],
    ) -> bool:
        return any(
            window.role_type in _NEUTRAL_SPEECH_TYPES
            and _overlap_seconds(start, end, window.start_seconds, window.end_seconds) > 0.25
            for window in audio_windows
        ) or any(
            indicator.indicator_type in {"speech_active", "speech_segment", "filler_sentence"}
            and _overlap_seconds(start, end, indicator.start_seconds, indicator.end_seconds) > 0.25
            for indicator in indicators
        )

    def _continuous_speech_or_action(
        self,
        start: float,
        end: float,
        states: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
    ) -> bool:
        if end <= start:
            return True
        probe_start = max(0.0, start - 0.35)
        probe_end = end + 0.35
        if self._has_strong_action(probe_start, probe_end, states, indicators, audio_windows):
            return True
        if self._wait_overlap(probe_start, probe_end, states, [], indicators, audio_windows) / max(probe_end - probe_start, 0.001) >= 0.50:
            return False
        return any(
            _overlap_seconds(probe_start, probe_end, item.start_seconds, item.end_seconds) > 0.0
            for item in [*transcripts, *sentences]
        ) or any(
            window.role_type in (_IMPORTANT_AUDIO_TYPES | _NEUTRAL_SPEECH_TYPES)
            and _overlap_seconds(probe_start, probe_end, window.start_seconds, window.end_seconds) > 0.0
            for window in audio_windows
        )

    def _speech_blocked_by_wait(
        self,
        start: float,
        end: float,
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
    ) -> bool:
        overlap_start = max(0.0, start)
        overlap_end = max(overlap_start, end)
        duration = max(overlap_end - overlap_start, 0.001)
        bad_wait = _overlap_merged_seconds(
            overlap_start,
            overlap_end,
            [
                (state.start_seconds, state.end_seconds)
                for state in states
                if state.state_type in _SPEECH_BLOCKING_WAIT_STATES
            ]
            + [
                (phase.start_seconds, phase.end_seconds)
                for phase in phases
                if self._phase_value(phase) in {"menu_wait", "queue_wait"}
            ],
        )
        if bad_wait / duration < 0.50:
            return False
        return not self._has_strong_action(overlap_start, overlap_end, states, indicators, audio_windows)

    def _has_important_phrase(self, text: str) -> bool:
        lowered = (text or "").lower()
        return any(phrase in lowered for phrase in _IMPORTANT_PHRASES)

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
