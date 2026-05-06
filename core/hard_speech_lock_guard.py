from __future__ import annotations

from dataclasses import dataclass, field

from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.cut_indicator import CutIndicator, CutIndicatorResult
from models.gameplay_state_result import GameplayStateResult, GameplayStateWindow
from models.sentence_timeline import SentenceItem, SentenceTimelineResult
from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult, TranscriptSegment


MIN_SEGMENT_DURATION_SECONDS = 2.5
MIN_GAP_SECONDS = 0.15
WORD_START_PREROLL_SECONDS = 0.25
WORD_END_POSTROLL_SECONDS = 0.35
WORD_END_TRIM_BACK_SECONDS = 0.20
MAX_WORD_END_EXPAND_SECONDS = 3.0
SENTENCE_START_PREROLL_SECONDS = 0.25
SENTENCE_END_POSTROLL_SECONDS = 0.45
MAX_SENTENCE_EDGE_EXPAND_SECONDS = 1.50
PHRASE_POSTROLL_SECONDS = 0.50
SHOUT_POSTROLL_SECONDS = 0.70
SECONDARY_START_PREROLL_SECONDS = 0.25
SECONDARY_END_POSTROLL_SECONDS = 0.35
MICRO_CUT_GAP_SECONDS = 2.0
SHORT_USELESS_MAX_SECONDS = 3.0

_PROTECTED_ROLES = frozenset({"hook", "peak", "payoff"})
_PHRASE_LOCK_TEXT = (
    "parade",
    "leo",
    "alles gut",
    "oh gott",
    "wichtig",
    "verstehe",
    "warum siehst du",
    "nicht",
)
_SECONDARY_LOCK_TYPES = frozenset({
    "secondary_speech_like",
    "speech_active",
    "group_reaction_like",
})
_SHOUT_TYPES = frozenset({
    "shout_like_audio",
    "group_reaction_like",
    "laugh_like_audio",
})
_ACTION_INDICATOR_TYPES = frozenset({
    "high_action_burst",
    "goal_or_save_like_flash",
    "possible_goal_or_flash",
    "possible_pre_action_context",
    "sustained_action",
})
_GOAL_OR_FLASH_TYPES = frozenset({
    "goal_or_save_like_flash",
    "possible_goal_or_flash",
})
_GOOD_ACTION_STATES = frozenset({
    "active_gameplay",
    "high_motion_action",
    "possible_goal_or_flash",
    "possible_pre_action_context",
})


@dataclass
class HardSpeechLockSummary:
    word_start_locked: int = 0
    word_end_locked: int = 0
    word_end_trimmed_back: int = 0
    word_lock_removed: int = 0
    sentence_start_locked: int = 0
    sentence_end_locked: int = 0
    sentence_end_trimmed_back: int = 0
    phrase_locked: int = 0
    shout_locked: int = 0
    secondary_start_locked: int = 0
    secondary_end_locked: int = 0
    secondary_removed: int = 0
    micro_cuts_merged: int = 0
    micro_cuts_removed: int = 0
    micro_gaps_closed: int = 0
    short_useless_removed: int = 0
    action_preroll_locked: int = 0
    shout_preroll_locked: int = 0
    duration_before: float = 0.0
    duration_after: float = 0.0
    examples: list[str] = field(default_factory=list)

    @property
    def word_locked(self) -> int:
        return self.word_start_locked + self.word_end_locked + self.word_end_trimmed_back

    @property
    def sentence_locked(self) -> int:
        return (
            self.sentence_start_locked
            + self.sentence_end_locked
            + self.sentence_end_trimmed_back
        )

    @property
    def secondary_locked(self) -> int:
        return self.secondary_start_locked + self.secondary_end_locked

    @property
    def micro_fixed(self) -> int:
        return self.micro_cuts_merged + self.micro_cuts_removed + self.micro_gaps_closed

    def add_example(self, text: str) -> None:
        if len(self.examples) < 8:
            self.examples.append(text)

    def to_dict(self) -> dict[str, object]:
        return {
            "word_start_locked": self.word_start_locked,
            "word_end_locked": self.word_end_locked,
            "word_end_trimmed_back": self.word_end_trimmed_back,
            "word_lock_removed": self.word_lock_removed,
            "word_locked": self.word_locked,
            "sentence_start_locked": self.sentence_start_locked,
            "sentence_end_locked": self.sentence_end_locked,
            "sentence_end_trimmed_back": self.sentence_end_trimmed_back,
            "sentence_locked": self.sentence_locked,
            "phrase_locked": self.phrase_locked,
            "shout_locked": self.shout_locked,
            "secondary_start_locked": self.secondary_start_locked,
            "secondary_end_locked": self.secondary_end_locked,
            "secondary_removed": self.secondary_removed,
            "secondary_locked": self.secondary_locked,
            "micro_cuts_merged": self.micro_cuts_merged,
            "micro_cuts_removed": self.micro_cuts_removed,
            "micro_gaps_closed": self.micro_gaps_closed,
            "micro_fixed": self.micro_fixed,
            "short_useless_removed": self.short_useless_removed,
            "action_preroll_locked": self.action_preroll_locked,
            "shout_preroll_locked": self.shout_preroll_locked,
            "duration_before": self.duration_before,
            "duration_after": self.duration_after,
            "examples": list(self.examples),
        }


class HardSpeechLockGuard:
    engine = "hard-speech-lock-guard-v1"

    def apply(
        self,
        selected_segments: list[TimelineSegment],
        *,
        transcript_result: TranscriptResult | None = None,
        sentence_timeline_result: SentenceTimelineResult | None = None,
        audio_role_result: AudioRoleResult | None = None,
        cut_indicator_result: CutIndicatorResult | None = None,
        gameplay_state_result: GameplayStateResult | None = None,
    ) -> tuple[list[TimelineSegment], HardSpeechLockSummary]:
        ordered = sorted(
            (segment for segment in selected_segments if segment.end_time > segment.start_time),
            key=lambda segment: (segment.start_time, segment.end_time, segment.segment_id),
        )
        summary = HardSpeechLockSummary(
            duration_before=round(sum(segment.duration for segment in ordered), 3)
        )

        transcripts = self._transcripts(transcript_result)
        sentences = self._sentences(sentence_timeline_result)
        audio_windows = self._audio_windows(audio_role_result)
        indicators = self._indicators(cut_indicator_result)
        state_windows = self._state_windows(gameplay_state_result)

        ordered = self._apply_hard_edge_locks(
            ordered,
            transcripts,
            sentences,
            audio_windows,
            indicators,
            summary,
        )
        self._apply_action_preroll(ordered, indicators, audio_windows, state_windows, summary)
        self._kill_micro_cuts(
            ordered,
            transcripts,
            sentences,
            audio_windows,
            indicators,
            state_windows,
            summary,
        )
        ordered = self._remove_short_useless_blocks(
            ordered,
            transcripts,
            sentences,
            audio_windows,
            indicators,
            state_windows,
            summary,
        )
        ordered = self._final_cleanup(ordered, summary)
        summary.duration_after = round(sum(segment.duration for segment in ordered), 3)
        return ordered, summary

    def _apply_hard_edge_locks(
        self,
        segments: list[TimelineSegment],
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
        audio_windows: list[AudioRoleWindow],
        indicators: list[CutIndicator],
        summary: HardSpeechLockSummary,
    ) -> list[TimelineSegment]:
        removed_ids: set[str] = set()
        for index, segment in enumerate(segments):
            if segment.segment_id in removed_ids:
                continue
            previous = self._previous_kept(segments, index, removed_ids)
            next_segment = self._next_kept(segments, index, removed_ids)

            start_source = self._containing_transcript(segment.start_time, transcripts)
            if start_source is not None:
                desired = round(max(0.0, start_source.start_seconds - WORD_START_PREROLL_SECONDS), 3)
                if self._lock_start(segment, previous, desired, "hard_word_start", summary):
                    summary.word_start_locked += 1
                    summary.add_example(
                        f"{segment.segment_id} start {segment.start_time:.2f} word_start_lock"
                    )

            sentence_start = self._containing_sentence(segment.start_time, sentences)
            if sentence_start is not None:
                desired = round(max(0.0, sentence_start.start_seconds - SENTENCE_START_PREROLL_SECONDS), 3)
                if self._lock_start(segment, previous, desired, "hard_sentence_start", summary):
                    summary.sentence_start_locked += 1

            secondary_start = self._containing_audio_window(segment.start_time, audio_windows, _SECONDARY_LOCK_TYPES)
            if secondary_start is not None:
                desired = round(max(0.0, secondary_start.start_seconds - SECONDARY_START_PREROLL_SECONDS), 3)
                if self._lock_start(segment, previous, desired, "hard_secondary_start", summary):
                    summary.secondary_start_locked += 1

            end_source = self._containing_transcript(segment.end_time, transcripts)
            if end_source is not None:
                phrase = self._has_phrase_text(end_source.text)
                postroll = max(WORD_END_POSTROLL_SECONDS, PHRASE_POSTROLL_SECONDS if phrase else 0.0)
                desired = round(end_source.end_seconds + postroll, 3)
                if desired - segment.end_time <= MAX_WORD_END_EXPAND_SECONDS or phrase:
                    if self._lock_end(segment, next_segment, desired, "hard_word_end", summary):
                        summary.word_end_locked += 1
                        if phrase:
                            summary.phrase_locked += 1
                else:
                    trimmed = self._trim_end_before_source(
                        segment,
                        end_source.start_seconds,
                        "hard_word_end_trimmed_back",
                    )
                    if trimmed:
                        summary.word_end_trimmed_back += 1
                    elif self._mark_removed_for_lock(segment, removed_ids, "hard_word_lock_removed"):
                        summary.word_lock_removed += 1

            sentence_end = self._containing_sentence(segment.end_time, sentences)
            if sentence_end is not None:
                desired = round(sentence_end.end_seconds + SENTENCE_END_POSTROLL_SECONDS, 3)
                if desired - segment.end_time <= MAX_SENTENCE_EDGE_EXPAND_SECONDS:
                    if self._lock_end(segment, next_segment, desired, "hard_sentence_end", summary):
                        summary.sentence_end_locked += 1
                else:
                    trimmed = self._trim_end_before_source(
                        segment,
                        sentence_end.start_seconds,
                        "hard_sentence_end_trimmed_back",
                    )
                    if trimmed:
                        summary.sentence_end_trimmed_back += 1

            secondary_end = self._containing_audio_window(segment.end_time, audio_windows, _SECONDARY_LOCK_TYPES)
            if secondary_end is not None:
                desired = round(secondary_end.end_seconds + SECONDARY_END_POSTROLL_SECONDS, 3)
                if self._lock_end(segment, next_segment, desired, "hard_secondary_end", summary):
                    summary.secondary_end_locked += 1
                elif self._mark_removed_for_lock(segment, removed_ids, "hard_secondary_lock_removed"):
                    summary.secondary_removed += 1

            shout_end = self._containing_or_near_indicator(segment.end_time, indicators, _SHOUT_TYPES, near=0.25)
            if shout_end is not None:
                desired = round(shout_end.end_seconds + SHOUT_POSTROLL_SECONDS, 3)
                if self._lock_end(segment, next_segment, desired, "hard_shout_end", summary):
                    summary.shout_locked += 1

            shout_audio_end = self._containing_audio_window(segment.end_time, audio_windows, _SHOUT_TYPES)
            if shout_audio_end is not None:
                desired = round(shout_audio_end.end_seconds + SHOUT_POSTROLL_SECONDS, 3)
                if self._lock_end(segment, next_segment, desired, "hard_shout_audio_end", summary):
                    summary.shout_locked += 1

            phrase_near_end = self._phrase_source_touching_end(segment.end_time, transcripts, sentences)
            if phrase_near_end is not None:
                desired = round(_source_end(phrase_near_end) + PHRASE_POSTROLL_SECONDS, 3)
                if self._lock_end(segment, next_segment, desired, "hard_phrase_end", summary):
                    summary.phrase_locked += 1

            segment.start_time = round(max(0.0, segment.start_time), 3)
            segment.end_time = round(segment.end_time, 3)
            segment.touch()

        return [segment for segment in segments if segment.segment_id not in removed_ids]

    def _lock_start(
        self,
        segment: TimelineSegment,
        previous: TimelineSegment | None,
        desired_start: float,
        note_prefix: str,
        summary: HardSpeechLockSummary,
    ) -> bool:
        desired_start = round(max(0.0, desired_start), 3)
        if desired_start >= segment.start_time:
            return False
        if segment.end_time - desired_start < MIN_SEGMENT_DURATION_SECONDS:
            return False

        if previous is not None and desired_start < previous.end_time:
            trim_prev_end = round(desired_start - MIN_GAP_SECONDS, 3)
            if (
                previous.segment_role not in _PROTECTED_ROLES
                and trim_prev_end - previous.start_time >= MIN_SEGMENT_DURATION_SECONDS
            ):
                old_prev_end = previous.end_time
                previous.end_time = trim_prev_end
                previous.notes.append(
                    f"{note_prefix}_trim_previous={old_prev_end:.3f}->{previous.end_time:.3f}"
                )
                previous.touch()
            else:
                desired_start = round(previous.end_time, 3)
                if desired_start >= segment.start_time:
                    return False
                if segment.end_time - desired_start < MIN_SEGMENT_DURATION_SECONDS:
                    return False

        old = segment.start_time
        segment.start_time = desired_start
        segment.notes.append(f"{note_prefix}={old:.3f}->{desired_start:.3f}")
        segment.touch()
        return True

    def _lock_end(
        self,
        segment: TimelineSegment,
        next_segment: TimelineSegment | None,
        desired_end: float,
        note_prefix: str,
        summary: HardSpeechLockSummary,
    ) -> bool:
        desired_end = round(desired_end, 3)
        if desired_end <= segment.end_time:
            return False
        if desired_end - segment.start_time < MIN_SEGMENT_DURATION_SECONDS:
            return False

        if next_segment is not None and desired_end > next_segment.start_time:
            shifted_start = round(desired_end, 3)
            if next_segment.end_time - shifted_start >= MIN_SEGMENT_DURATION_SECONDS:
                old_next_start = next_segment.start_time
                next_segment.start_time = shifted_start
                next_segment.notes.append(
                    f"{note_prefix}_shift_next={old_next_start:.3f}->{next_segment.start_time:.3f}"
                )
                next_segment.touch()
            else:
                return False

        old = segment.end_time
        segment.end_time = desired_end
        segment.notes.append(f"{note_prefix}={old:.3f}->{desired_end:.3f}")
        segment.touch()
        summary.add_example(f"{segment.segment_id} end {old:.2f}->{desired_end:.2f} {note_prefix}")
        return True

    def _trim_end_before_source(
        self,
        segment: TimelineSegment,
        source_start: float,
        note_prefix: str,
    ) -> bool:
        trim_back = round(max(0.0, source_start - WORD_END_TRIM_BACK_SECONDS), 3)
        if trim_back >= segment.end_time:
            return False
        if trim_back - segment.start_time < MIN_SEGMENT_DURATION_SECONDS:
            return False
        old = segment.end_time
        segment.end_time = trim_back
        segment.notes.append(f"{note_prefix}={old:.3f}->{trim_back:.3f}")
        segment.touch()
        return True

    def _mark_removed_for_lock(
        self,
        segment: TimelineSegment,
        removed_ids: set[str],
        note: str,
    ) -> bool:
        if segment.segment_role in _PROTECTED_ROLES:
            segment.notes.append(f"{note}_skipped_protected_role")
            return False
        segment.notes.append(note)
        removed_ids.add(segment.segment_id)
        return True

    def _apply_action_preroll(
        self,
        segments: list[TimelineSegment],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        state_windows: list[GameplayStateWindow],
        summary: HardSpeechLockSummary,
    ) -> None:
        for index, segment in enumerate(segments):
            previous = segments[index - 1] if index > 0 else None
            trigger = self._earliest_action_trigger(segment, indicators, audio_windows, state_windows)
            if trigger is None:
                continue
            trigger_start, trigger_type = trigger
            if trigger_type == "shout":
                preroll = 1.2
            elif trigger_type == "goal":
                preroll = 1.5
            else:
                preroll = 1.0
            desired = round(max(0.0, trigger_start - preroll), 3)
            if desired >= segment.start_time:
                continue
            if self._lock_start(segment, previous, desired, f"hard_{trigger_type}_preroll", summary):
                if trigger_type == "shout":
                    summary.shout_preroll_locked += 1
                else:
                    summary.action_preroll_locked += 1

    def _kill_micro_cuts(
        self,
        segments: list[TimelineSegment],
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
        audio_windows: list[AudioRoleWindow],
        indicators: list[CutIndicator],
        state_windows: list[GameplayStateWindow],
        summary: HardSpeechLockSummary,
    ) -> None:
        for index in range(len(segments) - 1):
            current = segments[index]
            next_segment = segments[index + 1]
            if current.end_time <= current.start_time or next_segment.end_time <= next_segment.start_time:
                continue
            gap = round(next_segment.start_time - current.end_time, 3)
            if gap < 0.0 or gap >= MICRO_CUT_GAP_SECONDS:
                continue
            if self._bad_wait_dominates(current.end_time, next_segment.start_time, state_windows, audio_windows, indicators):
                continue

            if self._continuous_speech_or_action(
                current.end_time,
                next_segment.start_time,
                transcripts,
                sentences,
                audio_windows,
                indicators,
                state_windows,
            ) or gap <= 1.25:
                old_end = current.end_time
                current.end_time = round(next_segment.start_time, 3)
                current.notes.append(f"hard_micro_gap_closed={old_end:.3f}->{current.end_time:.3f}")
                current.touch()
                summary.micro_gaps_closed += 1
                summary.add_example(f"{current.segment_id} micro_gap_closed gap={gap:.2f}")

    def _remove_short_useless_blocks(
        self,
        segments: list[TimelineSegment],
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
        audio_windows: list[AudioRoleWindow],
        indicators: list[CutIndicator],
        state_windows: list[GameplayStateWindow],
        summary: HardSpeechLockSummary,
    ) -> list[TimelineSegment]:
        kept: list[TimelineSegment] = []
        for segment in segments:
            if segment.duration >= SHORT_USELESS_MAX_SECONDS:
                kept.append(segment)
                continue
            if segment.segment_role not in {"build", "bridge"}:
                kept.append(segment)
                continue
            if self._segment_has_speech_or_action(segment, transcripts, sentences, audio_windows, indicators, state_windows):
                kept.append(segment)
                continue
            segment.notes.append("hard_short_useless_removed")
            summary.short_useless_removed += 1
            summary.add_example(f"{segment.segment_id} removed short_useless {segment.start_time:.2f}-{segment.end_time:.2f}")
        return kept

    def _final_cleanup(
        self,
        segments: list[TimelineSegment],
        summary: HardSpeechLockSummary,
    ) -> list[TimelineSegment]:
        kept: list[TimelineSegment] = []
        for segment in sorted(segments, key=lambda item: (item.start_time, item.end_time, item.segment_id)):
            if segment.end_time <= segment.start_time:
                continue
            if segment.start_time < 0.0:
                segment.start_time = 0.0
            if segment.duration < MIN_SEGMENT_DURATION_SECONDS and segment.segment_role not in _PROTECTED_ROLES:
                segment.notes.append("hard_final_short_removed")
                summary.micro_cuts_removed += 1
                continue
            if kept and segment.start_time < kept[-1].end_time:
                required_start = round(kept[-1].end_time, 3)
                if segment.end_time - required_start >= MIN_SEGMENT_DURATION_SECONDS:
                    old_start = segment.start_time
                    segment.start_time = required_start
                    segment.notes.append(f"hard_overlap_start_clamped={old_start:.3f}->{segment.start_time:.3f}")
                    segment.touch()
                elif kept[-1].segment_role not in _PROTECTED_ROLES:
                    trim_prev = round(segment.start_time - MIN_GAP_SECONDS, 3)
                    if trim_prev - kept[-1].start_time >= MIN_SEGMENT_DURATION_SECONDS:
                        old_prev_end = kept[-1].end_time
                        kept[-1].end_time = trim_prev
                        kept[-1].notes.append(f"hard_overlap_prev_trim={old_prev_end:.3f}->{trim_prev:.3f}")
                        kept[-1].touch()
                    else:
                        segment.notes.append("hard_overlap_short_removed")
                        summary.micro_cuts_removed += 1
                        continue
                else:
                    segment.notes.append("hard_overlap_short_removed")
                    summary.micro_cuts_removed += 1
                    continue
            segment.start_time = round(max(0.0, segment.start_time), 3)
            segment.end_time = round(segment.end_time, 3)
            if segment.end_time <= segment.start_time:
                continue
            kept.append(segment)
        return kept

    def _earliest_action_trigger(
        self,
        segment: TimelineSegment,
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        state_windows: list[GameplayStateWindow],
    ) -> tuple[float, str] | None:
        candidates: list[tuple[float, str]] = []
        for indicator in indicators:
            if not _overlaps(segment.start_time, segment.end_time, indicator.start_seconds, indicator.end_seconds):
                continue
            if indicator.indicator_type in _SHOUT_TYPES:
                candidates.append((indicator.start_seconds, "shout"))
            elif indicator.indicator_type in _GOAL_OR_FLASH_TYPES:
                candidates.append((indicator.start_seconds, "goal"))
            elif indicator.indicator_type in _ACTION_INDICATOR_TYPES:
                candidates.append((indicator.start_seconds, "action"))
        for window in audio_windows:
            if window.role_type in _SHOUT_TYPES and _overlaps(segment.start_time, segment.end_time, window.start_seconds, window.end_seconds):
                candidates.append((window.start_seconds, "shout"))
        for state in state_windows:
            if not _overlaps(segment.start_time, segment.end_time, state.start_seconds, state.end_seconds):
                continue
            if state.state_type == "possible_goal_or_flash":
                candidates.append((state.start_seconds, "goal"))
            elif state.state_type in _GOOD_ACTION_STATES:
                candidates.append((state.start_seconds, "action"))
        if not candidates:
            return None
        return sorted(candidates, key=lambda item: (item[0], item[1]))[0]

    def _segment_has_speech_or_action(
        self,
        segment: TimelineSegment,
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
        audio_windows: list[AudioRoleWindow],
        indicators: list[CutIndicator],
        state_windows: list[GameplayStateWindow],
    ) -> bool:
        return (
            self._overlap_any(segment.start_time, segment.end_time, transcripts)
            or self._overlap_any(segment.start_time, segment.end_time, sentences)
            or any(
                window.role_type in (_SECONDARY_LOCK_TYPES | _SHOUT_TYPES)
                and _overlap_seconds(segment.start_time, segment.end_time, window.start_seconds, window.end_seconds) >= 0.2
                for window in audio_windows
            )
            or any(
                indicator.indicator_type in (_ACTION_INDICATOR_TYPES | _SHOUT_TYPES | {"hook_sentence"})
                and _overlap_seconds(segment.start_time, segment.end_time, indicator.start_seconds, indicator.end_seconds) >= 0.2
                for indicator in indicators
            )
            or any(
                state.state_type in _GOOD_ACTION_STATES
                and _overlap_seconds(segment.start_time, segment.end_time, state.start_seconds, state.end_seconds) >= 0.2
                for state in state_windows
            )
        )

    def _continuous_speech_or_action(
        self,
        start: float,
        end: float,
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
        audio_windows: list[AudioRoleWindow],
        indicators: list[CutIndicator],
        state_windows: list[GameplayStateWindow],
    ) -> bool:
        if end <= start:
            return True
        probe_start = max(0.0, start - 0.50)
        probe_end = end + 0.50
        return (
            self._overlap_any(probe_start, probe_end, transcripts)
            or self._overlap_any(probe_start, probe_end, sentences)
            or any(
                window.role_type in (_SECONDARY_LOCK_TYPES | _SHOUT_TYPES)
                and _overlap_seconds(probe_start, probe_end, window.start_seconds, window.end_seconds) > 0.0
                for window in audio_windows
            )
            or any(
                indicator.indicator_type in (_ACTION_INDICATOR_TYPES | _SHOUT_TYPES)
                and _overlap_seconds(probe_start, probe_end, indicator.start_seconds, indicator.end_seconds) > 0.0
                for indicator in indicators
            )
            or any(
                state.state_type in _GOOD_ACTION_STATES
                and _overlap_seconds(probe_start, probe_end, state.start_seconds, state.end_seconds) > 0.0
                for state in state_windows
            )
        )

    def _bad_wait_dominates(
        self,
        start: float,
        end: float,
        state_windows: list[GameplayStateWindow],
        audio_windows: list[AudioRoleWindow],
        indicators: list[CutIndicator],
    ) -> bool:
        if end <= start:
            return False
        duration = max(0.001, end - start)
        bad_state_types = {
            "menu_wait",
            "low_motion_wait",
            "possible_dead_time_after_goal",
            "round_end",
            "replay_like",
            "scoreboard_like",
        }
        wait_indicator_types = {
            "menu_or_idle",
            "low_gameplay_value",
            "round_end_dead_time",
            "silence_or_dead_air",
        }
        bad = sum(
            _overlap_seconds(start, end, state.start_seconds, state.end_seconds)
            for state in state_windows
            if state.state_type in bad_state_types
        )
        bad += sum(
            _overlap_seconds(start, end, window.start_seconds, window.end_seconds)
            for window in audio_windows
            if window.role_type == "silence_or_dead_air"
        )
        bad += sum(
            _overlap_seconds(start, end, indicator.start_seconds, indicator.end_seconds)
            for indicator in indicators
            if indicator.indicator_type in wait_indicator_types
        )
        return bad / duration >= 0.75

    def _overlap_any(
        self,
        start: float,
        end: float,
        sources: list[TranscriptSegment] | list[SentenceItem],
    ) -> bool:
        return any(
            _overlap_seconds(start, end, source.start_seconds, source.end_seconds) >= 0.2
            for source in sources
        )

    def _phrase_source_touching_end(
        self,
        boundary: float,
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
    ) -> TranscriptSegment | SentenceItem | None:
        for source in [*transcripts, *sentences]:
            if not self._has_phrase_text(getattr(source, "text", "")):
                continue
            if source.start_seconds <= boundary <= source.end_seconds + 0.25:
                return source
        return None

    def _containing_transcript(
        self,
        boundary: float,
        transcripts: list[TranscriptSegment],
    ) -> TranscriptSegment | None:
        for source in transcripts:
            if source.start_seconds < boundary < source.end_seconds:
                return source
        return None

    def _containing_sentence(
        self,
        boundary: float,
        sentences: list[SentenceItem],
    ) -> SentenceItem | None:
        for source in sentences:
            if source.start_seconds < boundary < source.end_seconds:
                return source
        return None

    def _containing_audio_window(
        self,
        boundary: float,
        audio_windows: list[AudioRoleWindow],
        role_types: frozenset[str],
    ) -> AudioRoleWindow | None:
        for window in audio_windows:
            if window.role_type in role_types and window.start_seconds < boundary < window.end_seconds:
                return window
        return None

    def _containing_or_near_indicator(
        self,
        boundary: float,
        indicators: list[CutIndicator],
        indicator_types: frozenset[str],
        *,
        near: float,
    ) -> CutIndicator | None:
        for indicator in indicators:
            if indicator.indicator_type not in indicator_types:
                continue
            if indicator.start_seconds < boundary < indicator.end_seconds:
                return indicator
            if indicator.start_seconds <= boundary + near and indicator.end_seconds >= boundary - near:
                return indicator
        return None

    def _previous_kept(
        self,
        segments: list[TimelineSegment],
        index: int,
        removed_ids: set[str],
    ) -> TimelineSegment | None:
        for previous_index in range(index - 1, -1, -1):
            candidate = segments[previous_index]
            if candidate.segment_id not in removed_ids:
                return candidate
        return None

    def _next_kept(
        self,
        segments: list[TimelineSegment],
        index: int,
        removed_ids: set[str],
    ) -> TimelineSegment | None:
        for next_index in range(index + 1, len(segments)):
            candidate = segments[next_index]
            if candidate.segment_id not in removed_ids:
                return candidate
        return None

    def _has_phrase_text(self, text: str) -> bool:
        lowered = (text or "").lower()
        return any(phrase in lowered for phrase in _PHRASE_LOCK_TEXT)

    def _transcripts(self, result: TranscriptResult | None) -> list[TranscriptSegment]:
        if result is None:
            return []
        return sorted(
            (source for source in result.segments if source.end_seconds > source.start_seconds),
            key=lambda source: (source.start_seconds, source.end_seconds),
        )

    def _sentences(self, result: SentenceTimelineResult | None) -> list[SentenceItem]:
        if result is None:
            return []
        return sorted(
            (source for source in result.sentences if source.end_seconds > source.start_seconds),
            key=lambda source: (source.start_seconds, source.end_seconds),
        )

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


def _source_end(source: TranscriptSegment | SentenceItem) -> float:
    return float(getattr(source, "end_seconds", 0.0) or 0.0)


def _overlap_seconds(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))


def _overlaps(start_a: float, end_a: float, start_b: float, end_b: float) -> bool:
    return _overlap_seconds(start_a, end_a, start_b, end_b) > 0.0
