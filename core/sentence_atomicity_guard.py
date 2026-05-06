from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.cut_indicator import CutIndicator, CutIndicatorResult
from models.gameplay_state_result import GameplayStateResult, GameplayStateWindow
from models.round_phase_result import RoundPhaseResult, RoundPhaseWindow
from models.sentence_timeline import SentenceItem, SentenceTimelineResult
from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult, TranscriptSegment


MIN_SEGMENT_DURATION_SECONDS = 2.5
MICRO_SEGMENT_SECONDS = 2.0
MICRO_GAP_SECONDS = 1.25
SENTENCE_START_PREROLL_SECONDS = 0.20
SENTENCE_END_POSTROLL_SECONDS = 0.35
SECONDARY_START_PREROLL_SECONDS = 0.20
SECONDARY_END_POSTROLL_SECONDS = 0.35
MAX_SENTENCE_START_EXPAND_SECONDS = 5.0
MAX_WAIT_START_EXPAND_SECONDS = 1.25
MAX_SENTENCE_END_EXPAND_SECONDS = 1.50
MAX_ACTION_LEAD_SEARCH_SECONDS = 8.0
MAX_ROUND_START_ACTION_LOOKAHEAD_SECONDS = 8.0

_PROTECTED_ROLES = frozenset({"hook", "peak", "payoff"})
_WAIT_STATES = frozenset({
    "menu_wait",
    "queue_wait",
    "low_motion_wait",
    "possible_dead_time_after_goal",
    "round_end",
    "replay_like",
    "scoreboard_like",
})
_ROUND_START_WAIT_STATES = frozenset({
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
_STRONG_ACTION_STATES = frozenset({
    "high_motion_action",
    "possible_goal_or_flash",
})
_ROUND_START_WAIT_PHASES = frozenset({
    "menu_wait",
    "queue_wait",
    "countdown_kickoff",
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
_HIGH_ACTION_INDICATOR_TYPES = frozenset({
    "high_action_burst",
    "sustained_action",
})
_SHOUT_AUDIO_TYPES = frozenset({
    "shout_like_audio",
    "group_reaction_like",
    "laugh_like_audio",
})
_SECONDARY_SPEECH_TYPES = frozenset({
    "secondary_speech_like",
    "group_speech",
    "group_reaction_like",
    "speech_active",
})
_WAIT_INDICATOR_TYPES = frozenset({
    "menu_or_idle",
    "low_gameplay_value",
    "round_end_dead_time",
    "silence_or_dead_air",
    "filler_sentence",
})


class _SpeechSource(Protocol):
    start_seconds: float
    end_seconds: float
    text: str


@dataclass
class SentenceAtomicitySummary:
    sentence_start_fixed: int = 0
    sentence_end_fixed: int = 0
    sentence_partial_removed: int = 0
    secondary_sentence_fixed: int = 0
    secondary_sentence_removed: int = 0
    micro_segments_removed: int = 0
    micro_segments_merged: int = 0
    action_lead_trimmed: int = 0
    round_start_action_protected: int = 0
    duration_before: float = 0.0
    duration_after: float = 0.0
    examples: list[str] = field(default_factory=list)

    def add_example(self, text: str) -> None:
        if len(self.examples) < 8:
            self.examples.append(text)

    def to_dict(self) -> dict[str, object]:
        return {
            "sentence_start_fixed": self.sentence_start_fixed,
            "sentence_end_fixed": self.sentence_end_fixed,
            "sentence_partial_removed": self.sentence_partial_removed,
            "secondary_sentence_fixed": self.secondary_sentence_fixed,
            "secondary_sentence_removed": self.secondary_sentence_removed,
            "micro_segments_removed": self.micro_segments_removed,
            "micro_segments_merged": self.micro_segments_merged,
            "action_lead_trimmed": self.action_lead_trimmed,
            "round_start_action_protected": self.round_start_action_protected,
            "duration_before": self.duration_before,
            "duration_after": self.duration_after,
            "examples": list(self.examples),
        }


class SentenceAtomicityGuard:
    engine = "sentence-atomicity-guard-v1"

    def apply(
        self,
        segments: list[TimelineSegment],
        *,
        transcript_result: TranscriptResult | None = None,
        sentence_timeline_result: SentenceTimelineResult | None = None,
        audio_role_result: AudioRoleResult | None = None,
        cut_indicator_result: CutIndicatorResult | None = None,
        gameplay_state_result: GameplayStateResult | None = None,
        round_phase_result: RoundPhaseResult | None = None,
    ) -> tuple[list[TimelineSegment], SentenceAtomicitySummary]:
        ordered = sorted(
            (segment for segment in segments if segment.end_time > segment.start_time),
            key=lambda segment: (segment.start_time, segment.end_time, segment.segment_id),
        )
        summary = SentenceAtomicitySummary(
            duration_before=round(sum(segment.duration for segment in ordered), 3)
        )

        transcripts = self._transcripts(transcript_result)
        sentences = self._sentences(sentence_timeline_result)
        sources = self._speech_sources(transcripts, sentences)
        audio_windows = self._audio_windows(audio_role_result)
        indicators = self._indicators(cut_indicator_result)
        states = self._state_windows(gameplay_state_result)
        phases = self._phase_windows(round_phase_result)

        self._restore_round_start_action_lead(ordered, states, phases, indicators, audio_windows, summary)
        self._fix_speech_edges(ordered, sources, audio_windows, states, phases, indicators, summary)
        self._trim_long_action_leads(ordered, sources, states, phases, indicators, audio_windows, summary)
        self._fix_speech_edges(ordered, sources, audio_windows, states, phases, indicators, summary)
        ordered = self._remove_or_merge_micro_segments(
            ordered,
            sources,
            audio_windows,
            states,
            indicators,
            summary,
        )
        self._close_micro_gaps(ordered, sources, audio_windows, states, indicators, phases, summary)
        ordered = self._cleanup(ordered, states, indicators, audio_windows, summary)

        summary.duration_after = round(sum(segment.duration for segment in ordered), 3)
        return ordered, summary

    def _restore_round_start_action_lead(
        self,
        segments: list[TimelineSegment],
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        summary: SentenceAtomicitySummary,
    ) -> None:
        for index, segment in enumerate(segments):
            if segment.end_time <= segment.start_time:
                continue
            trigger = self._first_action_trigger(
                segment.start_time,
                min(segment.end_time, segment.start_time + 2.0),
                states,
                indicators,
                audio_windows,
            )
            if trigger is None:
                continue
            trigger_start, trigger_kind = trigger
            lookback_start = max(0.0, trigger_start - MAX_ROUND_START_ACTION_LOOKAHEAD_SECONDS)
            wait_overlap = self._round_start_wait_overlap(lookback_start, trigger_start, states, phases, indicators)
            if wait_overlap < 1.0:
                continue
            desired = round(max(0.0, trigger_start - self._lead_seconds(trigger_kind)), 3)
            if desired >= segment.start_time:
                summary.round_start_action_protected += 1
                continue
            previous = self._previous_valid(segments, index)
            if not self._can_move_start(
                segment,
                previous,
                desired,
                states,
                phases,
                indicators,
                audio_windows,
                allow_small_wait_pullback=True,
            ):
                summary.round_start_action_protected += 1
                continue
            old = segment.start_time
            segment.start_time = desired
            segment.notes.append(f"sentence_atomicity_round_action_lead={old:.3f}->{desired:.3f}")
            segment.touch()
            summary.round_start_action_protected += 1
            summary.add_example(f"{segment.segment_id} start {old:.2f}->{desired:.2f} round_action_lead")

    def _fix_speech_edges(
        self,
        segments: list[TimelineSegment],
        sources: list[_SpeechSource],
        audio_windows: list[AudioRoleWindow],
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
        summary: SentenceAtomicitySummary,
    ) -> None:
        for index, segment in enumerate(segments):
            if segment.end_time <= segment.start_time:
                continue
            previous = self._previous_valid(segments, index)
            next_segment = self._next_valid(segments, index)
            self._fix_sentence_start(segment, previous, sources, states, phases, indicators, audio_windows, summary)
            if segment.end_time <= segment.start_time:
                continue
            self._fix_sentence_end(segment, next_segment, sources, states, phases, indicators, audio_windows, summary)
            if segment.end_time <= segment.start_time:
                continue
            self._fix_secondary_start(segment, previous, audio_windows, states, phases, indicators, summary)
            if segment.end_time <= segment.start_time:
                continue
            self._fix_secondary_end(segment, next_segment, audio_windows, states, phases, indicators, summary)

    def _fix_sentence_start(
        self,
        segment: TimelineSegment,
        previous: TimelineSegment | None,
        sources: list[_SpeechSource],
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        summary: SentenceAtomicitySummary,
    ) -> None:
        source = self._containing_source(segment.start_time, sources)
        if source is None:
            return
        if segment.start_time - source.start_seconds <= 0.12:
            return
        desired = round(max(0.0, source.start_seconds - SENTENCE_START_PREROLL_SECONDS), 3)
        if self._can_move_start(
            segment,
            previous,
            desired,
            states,
            phases,
            indicators,
            audio_windows,
            allow_small_wait_pullback=True,
        ):
            old = segment.start_time
            segment.start_time = desired
            segment.notes.append(f"sentence_atomicity_start={old:.3f}->{desired:.3f}")
            segment.touch()
            summary.sentence_start_fixed += 1
            summary.add_example(f"{segment.segment_id} start {old:.2f}->{desired:.2f} sentence_atomicity")
            return

        if self._trim_past_source_start(segment, source, states, indicators, audio_windows, summary):
            return
        if not self._has_strong_protection(
            max(segment.start_time, source.start_seconds),
            min(segment.end_time, source.end_seconds),
            states,
            indicators,
            audio_windows,
        ):
            segment.notes.append("sentence_atomicity_partial_start_removed")
            segment.end_time = segment.start_time
            summary.sentence_partial_removed += 1
            summary.add_example(f"{segment.segment_id} removed partial_sentence_start")

    def _fix_sentence_end(
        self,
        segment: TimelineSegment,
        next_segment: TimelineSegment | None,
        sources: list[_SpeechSource],
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        summary: SentenceAtomicitySummary,
    ) -> None:
        source = self._containing_source(segment.end_time, sources)
        if source is None:
            return
        if source.end_seconds - segment.end_time <= 0.12:
            return
        desired = round(source.end_seconds + SENTENCE_END_POSTROLL_SECONDS, 3)
        expansion = desired - segment.end_time
        if (
            expansion <= MAX_SENTENCE_END_EXPAND_SECONDS
            and self._can_move_end(
                segment,
                next_segment,
                desired,
                states,
                phases,
                indicators,
                audio_windows,
            )
        ):
            old = segment.end_time
            segment.end_time = desired
            segment.notes.append(f"sentence_atomicity_end={old:.3f}->{desired:.3f}")
            segment.touch()
            summary.sentence_end_fixed += 1
            summary.add_example(f"{segment.segment_id} end {old:.2f}->{desired:.2f} sentence_atomicity")
            return

        trim_end = round(max(segment.start_time, source.start_seconds - SENTENCE_START_PREROLL_SECONDS), 3)
        if trim_end < segment.end_time and trim_end - segment.start_time >= MIN_SEGMENT_DURATION_SECONDS:
            old = segment.end_time
            segment.end_time = trim_end
            segment.notes.append(f"sentence_atomicity_partial_end_trim={old:.3f}->{trim_end:.3f}")
            segment.touch()
            summary.sentence_partial_removed += 1
            summary.add_example(f"{segment.segment_id} end {old:.2f}->{trim_end:.2f} partial_sentence_removed")
            return
        if not self._has_strong_protection(
            max(segment.start_time, source.start_seconds),
            min(segment.end_time, source.end_seconds),
            states,
            indicators,
            audio_windows,
        ):
            segment.notes.append("sentence_atomicity_partial_end_removed")
            segment.end_time = segment.start_time
            summary.sentence_partial_removed += 1
            summary.add_example(f"{segment.segment_id} removed partial_sentence_end")

    def _fix_secondary_start(
        self,
        segment: TimelineSegment,
        previous: TimelineSegment | None,
        audio_windows: list[AudioRoleWindow],
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
        summary: SentenceAtomicitySummary,
    ) -> None:
        window = self._containing_secondary_window(segment.start_time, audio_windows)
        if window is None or segment.start_time - window.start_seconds <= 0.12:
            return
        desired = round(max(0.0, window.start_seconds - SECONDARY_START_PREROLL_SECONDS), 3)
        if self._can_move_start(
            segment,
            previous,
            desired,
            states,
            phases,
            indicators,
            audio_windows,
            allow_small_wait_pullback=True,
        ):
            old = segment.start_time
            segment.start_time = desired
            segment.notes.append(f"sentence_atomicity_secondary_start={old:.3f}->{desired:.3f}")
            segment.touch()
            summary.secondary_sentence_fixed += 1
            summary.add_example(f"{segment.segment_id} start {old:.2f}->{desired:.2f} secondary_atomicity")
            return

        if self._trim_past_window_start(segment, window, states, indicators, audio_windows, summary):
            return
        if not self._has_strong_protection(
            max(segment.start_time, window.start_seconds),
            min(segment.end_time, window.end_seconds),
            states,
            indicators,
            audio_windows,
        ):
            segment.notes.append("sentence_atomicity_secondary_start_removed")
            segment.end_time = segment.start_time
            summary.secondary_sentence_removed += 1
            summary.add_example(f"{segment.segment_id} removed secondary_partial_start")

    def _fix_secondary_end(
        self,
        segment: TimelineSegment,
        next_segment: TimelineSegment | None,
        audio_windows: list[AudioRoleWindow],
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
        summary: SentenceAtomicitySummary,
    ) -> None:
        window = self._containing_secondary_window(segment.end_time, audio_windows)
        if window is None or window.end_seconds - segment.end_time <= 0.12:
            return
        desired = round(window.end_seconds + SECONDARY_END_POSTROLL_SECONDS, 3)
        if self._can_move_end(segment, next_segment, desired, states, phases, indicators, audio_windows):
            old = segment.end_time
            segment.end_time = desired
            segment.notes.append(f"sentence_atomicity_secondary_end={old:.3f}->{desired:.3f}")
            segment.touch()
            summary.secondary_sentence_fixed += 1
            summary.add_example(f"{segment.segment_id} end {old:.2f}->{desired:.2f} secondary_atomicity")
            return

        trim_end = round(max(segment.start_time, window.start_seconds - SECONDARY_START_PREROLL_SECONDS), 3)
        if trim_end < segment.end_time and trim_end - segment.start_time >= MIN_SEGMENT_DURATION_SECONDS:
            old = segment.end_time
            segment.end_time = trim_end
            segment.notes.append(f"sentence_atomicity_secondary_end_trim={old:.3f}->{trim_end:.3f}")
            segment.touch()
            summary.secondary_sentence_removed += 1
            summary.add_example(f"{segment.segment_id} end {old:.2f}->{trim_end:.2f} secondary_partial_removed")
            return
        if not self._has_strong_protection(
            max(segment.start_time, window.start_seconds),
            min(segment.end_time, window.end_seconds),
            states,
            indicators,
            audio_windows,
        ):
            segment.notes.append("sentence_atomicity_secondary_end_removed")
            segment.end_time = segment.start_time
            summary.secondary_sentence_removed += 1
            summary.add_example(f"{segment.segment_id} removed secondary_partial_end")

    def _trim_long_action_leads(
        self,
        segments: list[TimelineSegment],
        sources: list[_SpeechSource],
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        summary: SentenceAtomicitySummary,
    ) -> None:
        for segment in segments:
            if segment.end_time <= segment.start_time:
                continue
            trigger = self._first_action_trigger(
                segment.start_time,
                min(segment.end_time, segment.start_time + MAX_ACTION_LEAD_SEARCH_SECONDS),
                states,
                indicators,
                audio_windows,
            )
            if trigger is None:
                continue
            trigger_start, trigger_kind = trigger
            max_lead = self._lead_seconds(trigger_kind)
            if trigger_start - segment.start_time <= max_lead + 0.20:
                continue
            trim_target = round(max(segment.start_time, trigger_start - max_lead), 3)
            protects_round_start_action = (
                self._round_start_wait_overlap(segment.start_time, trigger_start, states, phases, indicators) >= 1.0
            )
            if not self._boring_dominates(segment.start_time, trim_target, states, phases, indicators, audio_windows):
                continue
            trim_target = self._avoid_partial_speech_trim(trim_target, trigger_start, sources)
            if trim_target <= segment.start_time + 0.05:
                continue
            if segment.end_time - trim_target < MIN_SEGMENT_DURATION_SECONDS:
                continue
            old = segment.start_time
            segment.start_time = trim_target
            segment.notes.append(f"sentence_atomicity_action_lead_trim={old:.3f}->{trim_target:.3f}")
            segment.touch()
            summary.action_lead_trimmed += 1
            if protects_round_start_action:
                summary.round_start_action_protected += 1
            summary.add_example(f"{segment.segment_id} trimmed lead {old:.2f}->{trim_target:.2f} action_lead")

    def _remove_or_merge_micro_segments(
        self,
        segments: list[TimelineSegment],
        sources: list[_SpeechSource],
        audio_windows: list[AudioRoleWindow],
        states: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        summary: SentenceAtomicitySummary,
    ) -> list[TimelineSegment]:
        kept: list[TimelineSegment] = []
        for segment in sorted(segments, key=lambda item: (item.start_time, item.end_time, item.segment_id)):
            if segment.end_time <= segment.start_time:
                continue
            if segment.duration >= MICRO_SEGMENT_SECONDS:
                kept.append(segment)
                continue
            if self._segment_is_protected(segment, states, indicators, audio_windows):
                kept.append(segment)
                continue
            previous = kept[-1] if kept else None
            if (
                previous is not None
                and segment.start_time - previous.end_time < MICRO_GAP_SECONDS
                and self._continuous_sentence_or_action(previous.end_time, segment.end_time, sources, audio_windows, states, indicators)
            ):
                old_end = previous.end_time
                previous.end_time = round(segment.end_time, 3)
                previous.notes.append(f"sentence_atomicity_micro_merge={old_end:.3f}->{previous.end_time:.3f}")
                previous.touch()
                summary.micro_segments_merged += 1
                summary.add_example(f"{segment.segment_id} merged micro_segment")
                continue
            segment.notes.append("sentence_atomicity_micro_removed")
            summary.micro_segments_removed += 1
            summary.add_example(f"{segment.segment_id} removed micro_segment {segment.start_time:.2f}-{segment.end_time:.2f}")
        return kept

    def _close_micro_gaps(
        self,
        segments: list[TimelineSegment],
        sources: list[_SpeechSource],
        audio_windows: list[AudioRoleWindow],
        states: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        phases: list[RoundPhaseWindow],
        summary: SentenceAtomicitySummary,
    ) -> None:
        for index in range(len(segments) - 1):
            current = segments[index]
            next_segment = segments[index + 1]
            if current.end_time <= current.start_time or next_segment.end_time <= next_segment.start_time:
                continue
            gap = round(next_segment.start_time - current.end_time, 3)
            if gap < 0.0 or gap >= MICRO_GAP_SECONDS:
                continue
            if self._boring_dominates(current.end_time, next_segment.start_time, states, phases, indicators, audio_windows):
                continue
            if not self._continuous_sentence_or_action(current.end_time, next_segment.start_time, sources, audio_windows, states, indicators):
                continue
            old = current.end_time
            current.end_time = round(next_segment.start_time, 3)
            current.notes.append(f"sentence_atomicity_micro_gap_closed={old:.3f}->{current.end_time:.3f}")
            current.touch()
            summary.micro_segments_merged += 1
            summary.add_example(f"{current.segment_id} closed micro_gap {gap:.2f}s")

    def _cleanup(
        self,
        segments: list[TimelineSegment],
        states: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        summary: SentenceAtomicitySummary,
    ) -> list[TimelineSegment]:
        kept: list[TimelineSegment] = []
        for segment in sorted(segments, key=lambda item: (item.start_time, item.end_time, item.segment_id)):
            if segment.end_time <= segment.start_time:
                continue
            segment.start_time = round(max(0.0, segment.start_time), 3)
            segment.end_time = round(segment.end_time, 3)
            if (
                segment.duration < MIN_SEGMENT_DURATION_SECONDS
                and not self._segment_is_protected(segment, states, indicators, audio_windows)
            ):
                segment.notes.append("sentence_atomicity_final_short_removed")
                summary.micro_segments_removed += 1
                continue
            if kept and segment.start_time < kept[-1].end_time:
                required_start = round(kept[-1].end_time, 3)
                if segment.end_time - required_start >= MIN_SEGMENT_DURATION_SECONDS or self._segment_is_protected(segment, states, indicators, audio_windows):
                    old = segment.start_time
                    segment.start_time = required_start
                    segment.notes.append(f"sentence_atomicity_overlap_clamped={old:.3f}->{required_start:.3f}")
                    segment.touch()
                else:
                    segment.notes.append("sentence_atomicity_overlap_removed")
                    summary.micro_segments_removed += 1
                    continue
            if segment.end_time > segment.start_time:
                kept.append(segment)
        return kept

    def _can_move_start(
        self,
        segment: TimelineSegment,
        previous: TimelineSegment | None,
        desired: float,
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        *,
        allow_small_wait_pullback: bool,
    ) -> bool:
        desired = round(max(0.0, desired), 3)
        if desired >= segment.start_time:
            return False
        if segment.start_time - desired > MAX_SENTENCE_START_EXPAND_SECONDS:
            return False
        if previous is not None and desired < previous.end_time:
            return False
        if segment.end_time - desired < MIN_SEGMENT_DURATION_SECONDS:
            return False
        if segment.end_time - desired > 45.0:
            return False
        if self._boring_dominates(desired, segment.start_time, states, phases, indicators, audio_windows):
            if not allow_small_wait_pullback or segment.start_time - desired > MAX_WAIT_START_EXPAND_SECONDS:
                if not self._has_strong_protection(desired, segment.start_time, states, indicators, audio_windows):
                    return False
        return True

    def _can_move_end(
        self,
        segment: TimelineSegment,
        next_segment: TimelineSegment | None,
        desired: float,
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
    ) -> bool:
        desired = round(desired, 3)
        if desired <= segment.end_time:
            return False
        if desired - segment.end_time > MAX_SENTENCE_END_EXPAND_SECONDS:
            return False
        if next_segment is not None and desired > next_segment.start_time:
            return False
        if desired - segment.start_time < MIN_SEGMENT_DURATION_SECONDS:
            return False
        if self._boring_dominates(segment.end_time, desired, states, phases, indicators, audio_windows):
            if not self._has_strong_protection(segment.end_time, desired, states, indicators, audio_windows):
                return False
        return True

    def _trim_past_source_start(
        self,
        segment: TimelineSegment,
        source: _SpeechSource,
        states: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        summary: SentenceAtomicitySummary,
    ) -> bool:
        clean_start = round(source.end_seconds + SENTENCE_END_POSTROLL_SECONDS, 3)
        if clean_start <= segment.start_time:
            return False
        if segment.end_time - clean_start < MIN_SEGMENT_DURATION_SECONDS:
            return False
        if self._has_strong_protection(source.start_seconds, source.end_seconds, states, indicators, audio_windows):
            return False
        old = segment.start_time
        segment.start_time = clean_start
        segment.notes.append(f"sentence_atomicity_partial_start_skip={old:.3f}->{clean_start:.3f}")
        segment.touch()
        summary.sentence_partial_removed += 1
        summary.add_example(f"{segment.segment_id} start {old:.2f}->{clean_start:.2f} partial_sentence_removed")
        return True

    def _trim_past_window_start(
        self,
        segment: TimelineSegment,
        window: AudioRoleWindow,
        states: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        summary: SentenceAtomicitySummary,
    ) -> bool:
        clean_start = round(window.end_seconds + SECONDARY_END_POSTROLL_SECONDS, 3)
        if clean_start <= segment.start_time:
            return False
        if segment.end_time - clean_start < MIN_SEGMENT_DURATION_SECONDS:
            return False
        if self._has_strong_protection(window.start_seconds, window.end_seconds, states, indicators, audio_windows):
            return False
        old = segment.start_time
        segment.start_time = clean_start
        segment.notes.append(f"sentence_atomicity_secondary_start_skip={old:.3f}->{clean_start:.3f}")
        segment.touch()
        summary.secondary_sentence_removed += 1
        summary.add_example(f"{segment.segment_id} start {old:.2f}->{clean_start:.2f} secondary_partial_removed")
        return True

    def _first_action_trigger(
        self,
        start: float,
        end: float,
        states: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
    ) -> tuple[float, str] | None:
        candidates: list[tuple[float, str, int]] = []
        for indicator in indicators:
            if not (start <= indicator.start_seconds < end):
                continue
            if indicator.indicator_type in _GOAL_INDICATOR_TYPES:
                candidates.append((indicator.start_seconds, "goal", 0))
            elif indicator.indicator_type in _SHOUT_AUDIO_TYPES:
                candidates.append((indicator.start_seconds, "shout", 1))
            elif indicator.indicator_type in _HIGH_ACTION_INDICATOR_TYPES:
                candidates.append((indicator.start_seconds, "high_action", 2))
            elif indicator.indicator_type in _ACTION_INDICATOR_TYPES:
                candidates.append((indicator.start_seconds, "action", 3))
        for window in audio_windows:
            if window.role_type in _SHOUT_AUDIO_TYPES and start <= window.start_seconds < end:
                candidates.append((window.start_seconds, "shout", 1))
        for state in states:
            if not (start <= state.start_seconds < end):
                continue
            if state.state_type == "possible_goal_or_flash":
                candidates.append((state.start_seconds, "goal", 0))
            elif state.state_type == "high_motion_action":
                candidates.append((state.start_seconds, "high_action", 2))
            elif state.state_type in _ACTION_STATES:
                candidates.append((state.start_seconds, "action", 3))
        if not candidates:
            return None
        trigger_start, trigger_kind, _ = sorted(candidates, key=lambda item: (item[0], item[2]))[0]
        return trigger_start, trigger_kind

    def _lead_seconds(self, trigger_kind: str) -> float:
        if trigger_kind == "goal":
            return 1.50
        if trigger_kind == "shout":
            return 1.20
        if trigger_kind == "high_action":
            return 1.50
        return 1.00

    def _avoid_partial_speech_trim(
        self,
        proposed: float,
        trigger_start: float,
        sources: list[_SpeechSource],
    ) -> float:
        adjusted = proposed
        for source in sources:
            if not (source.start_seconds < adjusted < source.end_seconds):
                continue
            if source.end_seconds <= trigger_start - 0.20:
                adjusted = round(source.end_seconds + SENTENCE_END_POSTROLL_SECONDS, 3)
            else:
                adjusted = round(max(0.0, source.start_seconds - SENTENCE_START_PREROLL_SECONDS), 3)
        return adjusted

    def _containing_source(self, boundary: float, sources: list[_SpeechSource]) -> _SpeechSource | None:
        for source in sources:
            if source.start_seconds < boundary < source.end_seconds:
                return source
        return None

    def _containing_secondary_window(
        self,
        boundary: float,
        audio_windows: list[AudioRoleWindow],
    ) -> AudioRoleWindow | None:
        for window in audio_windows:
            if window.role_type in _SECONDARY_SPEECH_TYPES and window.start_seconds < boundary < window.end_seconds:
                return window
        return None

    def _segment_is_protected(
        self,
        segment: TimelineSegment,
        states: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
    ) -> bool:
        return segment.segment_role in _PROTECTED_ROLES or self._has_strong_protection(
            segment.start_time,
            segment.end_time,
            states,
            indicators,
            audio_windows,
        )

    def _has_strong_protection(
        self,
        start: float,
        end: float,
        states: list[GameplayStateWindow],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
    ) -> bool:
        if end <= start:
            return False
        return (
            any(
                indicator.indicator_type in (_GOAL_INDICATOR_TYPES | _HIGH_ACTION_INDICATOR_TYPES | _SHOUT_AUDIO_TYPES)
                and _overlap_seconds(start, end, indicator.start_seconds, indicator.end_seconds) >= 0.20
                for indicator in indicators
            )
            or any(
                window.role_type in _SHOUT_AUDIO_TYPES
                and _overlap_seconds(start, end, window.start_seconds, window.end_seconds) >= 0.20
                for window in audio_windows
            )
            or any(
                (
                    state.state_type in _STRONG_ACTION_STATES
                    or (
                        state.state_type == "active_gameplay"
                        and max(state.motion_score, state.visual_activity_score, state.score) >= 0.75
                    )
                )
                and _overlap_seconds(start, end, state.start_seconds, state.end_seconds) >= 0.20
                for state in states
            )
        )

    def _continuous_sentence_or_action(
        self,
        start: float,
        end: float,
        sources: list[_SpeechSource],
        audio_windows: list[AudioRoleWindow],
        states: list[GameplayStateWindow],
        indicators: list[CutIndicator],
    ) -> bool:
        if end <= start:
            return True
        probe_start = max(0.0, start - 0.20)
        probe_end = end + 0.20
        return (
            any(source.start_seconds <= probe_start and source.end_seconds >= probe_end for source in sources)
            or any(
                window.role_type in (_SECONDARY_SPEECH_TYPES | _SHOUT_AUDIO_TYPES)
                and _overlap_seconds(probe_start, probe_end, window.start_seconds, window.end_seconds) > 0.0
                for window in audio_windows
            )
            or self._has_strong_protection(probe_start, probe_end, states, indicators, audio_windows)
        )

    def _round_start_wait_overlap(
        self,
        start: float,
        end: float,
        states: list[GameplayStateWindow],
        phases: list[RoundPhaseWindow],
        indicators: list[CutIndicator],
    ) -> float:
        windows: list[tuple[float, float]] = []
        windows.extend((state.start_seconds, state.end_seconds) for state in states if state.state_type in _ROUND_START_WAIT_STATES)
        windows.extend((phase.start_seconds, phase.end_seconds) for phase in phases if self._phase_value(phase) in _ROUND_START_WAIT_PHASES)
        windows.extend((indicator.start_seconds, indicator.end_seconds) for indicator in indicators if indicator.indicator_type in {"menu_or_idle", "low_gameplay_value", "silence_or_dead_air"})
        return _overlap_merged_seconds(start, end, windows)

    def _boring_dominates(
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
        windows: list[tuple[float, float]] = []
        windows.extend((state.start_seconds, state.end_seconds) for state in states if state.state_type in _WAIT_STATES)
        windows.extend((phase.start_seconds, phase.end_seconds) for phase in phases if self._phase_value(phase) in _WAIT_PHASES)
        windows.extend((indicator.start_seconds, indicator.end_seconds) for indicator in indicators if indicator.indicator_type in _WAIT_INDICATOR_TYPES)
        windows.extend((window.start_seconds, window.end_seconds) for window in audio_windows if window.role_type == "silence_or_dead_air")
        overlap = _overlap_merged_seconds(start, end, windows)
        return overlap / max(end - start, 0.001) >= 0.50

    def _previous_valid(self, segments: list[TimelineSegment], index: int) -> TimelineSegment | None:
        for previous_index in range(index - 1, -1, -1):
            previous = segments[previous_index]
            if previous.end_time > previous.start_time:
                return previous
        return None

    def _next_valid(self, segments: list[TimelineSegment], index: int) -> TimelineSegment | None:
        for next_index in range(index + 1, len(segments)):
            next_segment = segments[next_index]
            if next_segment.end_time > next_segment.start_time:
                return next_segment
        return None

    def _speech_sources(
        self,
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
    ) -> list[_SpeechSource]:
        # Sentence timeline entries are usually broader and closer to viewer perception.
        sources: list[_SpeechSource] = list(sentences) + list(transcripts)
        return sorted(
            (source for source in sources if source.end_seconds > source.start_seconds),
            key=lambda source: (source.start_seconds, -(source.end_seconds - source.start_seconds), source.end_seconds),
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

    def _audio_windows(self, result: AudioRoleResult | None) -> list[AudioRoleWindow]:
        if result is None:
            return []
        return sorted(
            (window for window in result.windows if window.end_seconds > window.start_seconds),
            key=lambda window: (window.start_seconds, window.end_seconds, window.role_type),
        )

    def _indicators(self, result: CutIndicatorResult | None) -> list[CutIndicator]:
        if result is None:
            return []
        return sorted(
            (indicator for indicator in result.indicators if indicator.end_seconds > indicator.start_seconds),
            key=lambda indicator: (indicator.start_seconds, indicator.end_seconds, indicator.indicator_type),
        )

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
