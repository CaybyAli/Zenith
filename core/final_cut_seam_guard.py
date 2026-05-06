from __future__ import annotations

from dataclasses import dataclass, field

from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult, TranscriptSegment
from models.sentence_timeline import SentenceItem, SentenceTimelineResult
from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.cut_indicator import CutIndicator, CutIndicatorResult


# ── Parameters ────────────────────────────────────────────────────────────────
MIN_SEAM_GAP_SECONDS = 0.15
MIN_NATURAL_PREROLL_SECONDS = 0.20
MAX_NATURAL_PREROLL_SECONDS = 0.35
WORD_CUT_PROTECTION_SECONDS = 0.25
REACTION_CONTEXT_PREROLL_SECONDS = 1.00
SECONDARY_SPEECH_HOLD_SECONDS = 0.35
SPEECH_END_LOCK_HOLD_SECONDS = 0.50
SHOUT_END_LOCK_HOLD_SECONDS = 0.60
PHRASE_END_LOCK_HOLD_SECONDS = 0.70
MAX_SPEECH_END_LOCK_EXPAND_SECONDS = 1.50
SPEECH_END_LOCK_NEAR_SECONDS = 0.25
LOW_VALUE_BRIDGE_MAX_SECONDS = 8.0
LOW_VALUE_BRIDGE_SCORE_THRESHOLD = 0.62
MAX_CONTEXT_EXPAND_SECONDS = 1.50
MIN_SEGMENT_DURATION_SECONDS = 2.5

MAX_SPEECH_EDGE_EXPAND_SECONDS = 1.20
MAX_SECONDARY_SPEECH_EXPAND_SECONDS = 1.00
MAX_REACTION_CONTEXT_EXPAND_SECONDS = 1.00
MAX_SEGMENT_DURATION_AFTER_SEAM_SECONDS = 22.0
MAX_BRIDGE_DURATION_AFTER_SEAM_SECONDS = 14.0
MINI_SEAM_DETECT_THRESHOLD = 0.45
MINI_SEAM_TARGET_GAP_SECONDS = 0.20
MENU_DEAD_TIME_MIN_SECONDS = 10.0

_NEGATIVE_INDICATOR_TYPES = frozenset({
    "round_end_dead_time", "silence_or_dead_air", "low_gameplay_value",
    "filler_sentence", "menu_or_idle",
})
_STRONG_POSITIVE_INDICATOR_TYPES = frozenset({
    "goal_or_save_like_flash", "high_action_burst", "hook_sentence", "group_reaction_like",
    "laugh_like_audio",
})
_STRONG_POSITIVE_FOR_MENU = frozenset({
    "goal_or_save_like_flash", "high_action_burst", "hook_sentence", "group_reaction_like",
    "sustained_action",
})
_MENU_DEAD_TIME_INDICATOR_TYPES = frozenset({
    "menu_or_idle", "low_gameplay_value", "round_end_dead_time",
    "silence_or_dead_air", "filler_sentence",
})
_REACTION_INDICATOR_TYPES = frozenset({
    "goal_or_save_like_flash", "high_action_burst", "facecam_reaction_spike",
    "shock_like", "group_reaction_like", "shout_like_audio", "laugh_like_audio",
})
_SECONDARY_SPEECH_ROLES = frozenset({
    "secondary_speech_like", "speech_active",
})
_PROTECTED_ROLES = frozenset({"hook", "payoff", "peak"})
_SHOUT_END_TYPES = frozenset({"shout_like_audio", "group_reaction_like", "laugh_like_audio"})
_PHRASE_LOCK_TEXT = (
    "alles gut",
    "oh gott",
    "nein",
    "warte",
    "wichtig",
)
_GOOD_ACTION_STATES = frozenset({
    "active_gameplay",
    "high_motion_action",
    "possible_goal_or_flash",
    "possible_pre_action_context",
})


@dataclass
class FinalCutSeamSummary:
    mini_seams_fixed: int = 0
    speech_start_adjusted: int = 0
    speech_end_adjusted: int = 0
    speech_end_trimmed_back: int = 0
    reaction_context_expanded: int = 0
    secondary_speech_protected: int = 0
    low_value_segments_removed: int = 0
    important_context_expanded: int = 0
    menu_dead_time_removed: int = 0
    menu_dead_time_trimmed: int = 0
    speech_end_locked: int = 0
    shout_end_locked: int = 0
    phrase_end_locked: int = 0
    seam_state_protected: int = 0
    duration_before: float = 0.0
    duration_after: float = 0.0
    examples: list[str] = field(default_factory=list)

    def add_example(self, text: str) -> None:
        if len(self.examples) < 8:
            self.examples.append(text)


def _overlap_seconds(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


class FinalCutSeamGuard:
    engine = "final-cut-seam-guard-v2"

    def apply(
        self,
        segments: list[TimelineSegment],
        *,
        transcript_result: TranscriptResult | None = None,
        sentence_timeline_result: SentenceTimelineResult | None = None,
        audio_role_result: AudioRoleResult | None = None,
        cut_indicator_result: CutIndicatorResult | None = None,
        cut_scoring_profile=None,
        gameplay_state_result=None,
    ) -> tuple[list[TimelineSegment], FinalCutSeamSummary]:
        del cut_scoring_profile
        ordered = sorted(
            (s for s in segments if s.end_time > s.start_time),
            key=lambda s: (s.start_time, s.end_time, s.segment_id),
        )
        summary = FinalCutSeamSummary(
            duration_before=round(sum(s.duration for s in ordered), 3)
        )

        transcripts = _sorted_transcripts(transcript_result)
        sentences = _sorted_sentences(sentence_timeline_result)
        audio_windows = _sorted_audio_windows(audio_role_result)
        indicators = _sorted_indicators(cut_indicator_result)
        state_windows = _sorted_state_windows(gameplay_state_result)

        # E) Low-Value Bridge Pruner
        ordered = self._prune_low_value_bridges(ordered, indicators, summary)
        if not ordered:
            summary.duration_after = 0.0
            return ordered, summary

        # C) Menu / Dead-Time Pruner
        ordered = self._prune_menu_dead_time(ordered, indicators, summary)
        if not ordered:
            summary.duration_after = 0.0
            return ordered, summary

        # A) Word-Cut / Sentence-Seam Protection
        self._apply_seam_speech_protection(ordered, transcripts, sentences, indicators, state_windows, summary)

        # Reaction Context Guard
        self._apply_reaction_context(ordered, indicators, audio_windows, summary)

        # F) Important Context Protection
        self._apply_important_context(ordered, indicators, summary)

        # D) Secondary Speech Hold
        self._apply_secondary_speech_hold(ordered, audio_windows, summary)

        # H) Stronger speech / shout / phrase end locks
        self._apply_speech_end_locks(
            ordered,
            transcripts,
            sentences,
            audio_windows,
            indicators,
            state_windows,
            summary,
        )

        # B) Mini-Seam Gap Guard
        self._fix_mini_seams(ordered, summary, transcripts, sentences)

        # Post-seam: prune long bridges that are still too long without strong action
        ordered = self._post_seam_duration_prune(ordered, indicators, summary)

        # G) Final cleanup — enforce invariants
        ordered = self._final_cleanup(ordered)

        summary.duration_after = round(sum(s.duration for s in ordered), 3)
        return ordered, summary

    # ── E) Low-Value Bridge Pruner ────────────────────────────────────────────

    def _prune_low_value_bridges(
        self,
        segments: list[TimelineSegment],
        indicators: list[CutIndicator],
        summary: FinalCutSeamSummary,
    ) -> list[TimelineSegment]:
        kept: list[TimelineSegment] = []
        for seg in segments:
            if seg.segment_role in _PROTECTED_ROLES:
                kept.append(seg)
                continue
            if seg.segment_role not in ("build", "bridge"):
                kept.append(seg)
                continue
            if seg.duration <= LOW_VALUE_BRIDGE_MAX_SECONDS:
                kept.append(seg)
                continue
            if seg.selection_score >= LOW_VALUE_BRIDGE_SCORE_THRESHOLD:
                kept.append(seg)
                continue

            # duration > 8s and score < 0.62: keep only if strong positive action present
            has_strong_positive = any(
                ind.indicator_type in _STRONG_POSITIVE_INDICATOR_TYPES
                and _overlap_seconds(seg.start_time, seg.end_time, ind.start_seconds, ind.end_seconds) > 0
                for ind in indicators
            )
            if has_strong_positive:
                kept.append(seg)
                continue

            seg.notes.append("seam_low_value_bridge_removed")
            summary.low_value_segments_removed += 1
            summary.add_example(
                f"{seg.segment_id} removed low_value_bridge {seg.start_time:.2f}-{seg.end_time:.2f}"
            )

        return kept

    # ── C) Menu / Dead-Time Pruner ────────────────────────────────────────────

    def _prune_menu_dead_time(
        self,
        segments: list[TimelineSegment],
        indicators: list[CutIndicator],
        summary: FinalCutSeamSummary,
    ) -> list[TimelineSegment]:
        kept: list[TimelineSegment] = []
        for seg in segments:
            if seg.segment_role in _PROTECTED_ROLES:
                kept.append(seg)
                continue
            if seg.segment_role not in ("build", "bridge"):
                kept.append(seg)
                continue
            if seg.duration <= MENU_DEAD_TIME_MIN_SECONDS:
                kept.append(seg)
                continue

            has_menu_negative = any(
                ind.indicator_type in _MENU_DEAD_TIME_INDICATOR_TYPES
                and _overlap_seconds(seg.start_time, seg.end_time, ind.start_seconds, ind.end_seconds) > 0
                for ind in indicators
            )
            if not has_menu_negative:
                kept.append(seg)
                continue

            has_strong_positive = any(
                ind.indicator_type in _STRONG_POSITIVE_FOR_MENU
                and _overlap_seconds(seg.start_time, seg.end_time, ind.start_seconds, ind.end_seconds) > 0
                for ind in indicators
            )
            if has_strong_positive:
                kept.append(seg)
                continue

            seg.notes.append("seam_menu_dead_time_removed")
            summary.menu_dead_time_removed += 1
            summary.add_example(
                f"{seg.segment_id} removed menu_dead_time {seg.start_time:.2f}-{seg.end_time:.2f}"
            )

        return kept

    # ── A) Word-Cut / Sentence-Seam Protection ────────────────────────────────

    def _apply_seam_speech_protection(
        self,
        segments: list[TimelineSegment],
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
        indicators: list[CutIndicator],
        state_windows: list[object],
        summary: FinalCutSeamSummary,
    ) -> None:
        if not transcripts and not sentences:
            return
        for idx, seg in enumerate(segments):
            prev = segments[idx - 1] if idx > 0 else None
            nxt = segments[idx + 1] if idx + 1 < len(segments) else None
            self._protect_segment_start(seg, prev, transcripts, sentences, summary)
            self._protect_segment_end(seg, nxt, transcripts, sentences, indicators, state_windows, summary)
            seg.start_time = round(max(0.0, seg.start_time), 3)
            seg.end_time = round(seg.end_time, 3)
            seg.touch()

    def _protect_segment_start(
        self,
        seg: TimelineSegment,
        prev: TimelineSegment | None,
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
        summary: FinalCutSeamSummary,
    ) -> None:
        boundary = seg.start_time
        src = _find_containing_transcript(boundary, transcripts) or _find_containing_sentence(boundary, sentences)
        if src is None:
            return
        src_start = src.start_seconds
        preferred = round(max(0.0, src_start - WORD_CUT_PROTECTION_SECONDS), 3)
        if preferred >= seg.start_time:
            seg.notes.append("seam_start_skipped_already_before")
            return
        # Cap expansion
        preferred = round(max(preferred, seg.start_time - MAX_SPEECH_EDGE_EXPAND_SECONDS), 3)
        prev_limit = round(prev.end_time + MIN_SEAM_GAP_SECONDS, 3) if prev else 0.0
        if preferred < prev_limit:
            seg.notes.append("seam_start_skipped_overlap")
            return
        if seg.end_time - preferred < MIN_SEGMENT_DURATION_SECONDS:
            seg.notes.append("seam_start_skipped_duration")
            return
        old = seg.start_time
        seg.start_time = preferred
        seg.notes.append(f"seam_speech_start={old:.3f}->{preferred:.3f}")
        summary.speech_start_adjusted += 1
        summary.add_example(f"{seg.segment_id} start {old:.2f}->{preferred:.2f} speech_pre_roll")

    def _protect_segment_end(
        self,
        seg: TimelineSegment,
        nxt: TimelineSegment | None,
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
        indicators: list[CutIndicator],
        state_windows: list[object],
        summary: FinalCutSeamSummary,
    ) -> None:
        boundary = seg.end_time
        src = _find_containing_transcript(boundary, transcripts) or _find_containing_sentence(boundary, sentences)
        if src is None:
            return
        src_end = src.end_seconds
        src_start = src.start_seconds
        preferred = round(src_end + WORD_CUT_PROTECTION_SECONDS, 3)
        if preferred <= seg.end_time:
            seg.notes.append("seam_end_skipped_already_after")
            return

        expansion = preferred - seg.end_time
        if expansion > MAX_SPEECH_EDGE_EXPAND_SECONDS:
            if _has_state_or_shout_protection(
                seg.end_time,
                min(preferred, seg.end_time + MAX_SPEECH_EDGE_EXPAND_SECONDS),
                indicators,
                state_windows,
            ):
                capped = round(seg.end_time + MAX_SPEECH_EDGE_EXPAND_SECONDS, 3)
                nxt_limit = round(nxt.start_time - MIN_SEAM_GAP_SECONDS, 3) if nxt else None
                if nxt_limit is None or capped <= nxt_limit:
                    old = seg.end_time
                    seg.end_time = capped
                    seg.notes.append(f"seam_state_protected_end={old:.3f}->{capped:.3f}")
                    seg.touch()
                    summary.speech_end_adjusted += 1
                    summary.seam_state_protected += 1
                    summary.add_example(f"{seg.segment_id} end {old:.2f}->{capped:.2f} state_protected")
                return
            # Cut before the word starts instead of extending past it
            trim_back = round(src_start - WORD_CUT_PROTECTION_SECONDS, 3)
            if trim_back > seg.start_time + MIN_SEGMENT_DURATION_SECONDS:
                old = seg.end_time
                seg.end_time = trim_back
                seg.notes.append(f"seam_speech_end_trimmed_back={old:.3f}->{trim_back:.3f}")
                summary.speech_end_trimmed_back += 1
                summary.add_example(f"{seg.segment_id} end {old:.2f}->{trim_back:.2f} trim_back")
            else:
                seg.notes.append("seam_end_skipped_expansion_too_large")
            return

        nxt_limit = round(nxt.start_time - MIN_SEAM_GAP_SECONDS, 3) if nxt else None
        if nxt_limit is not None and preferred > nxt_limit:
            seg.notes.append("seam_end_skipped_overlap")
            return
        if preferred - seg.start_time < MIN_SEGMENT_DURATION_SECONDS:
            seg.notes.append("seam_end_skipped_duration")
            return
        old = seg.end_time
        seg.end_time = preferred
        seg.notes.append(f"seam_speech_end={old:.3f}->{preferred:.3f}")
        summary.speech_end_adjusted += 1
        summary.add_example(f"{seg.segment_id} end {old:.2f}->{preferred:.2f} speech_post_roll")

    # ── Reaction Context Guard ────────────────────────────────────────────────

    def _apply_reaction_context(
        self,
        segments: list[TimelineSegment],
        indicators: list[CutIndicator],
        audio_windows: list[AudioRoleWindow],
        summary: FinalCutSeamSummary,
    ) -> None:
        for idx, seg in enumerate(segments):
            prev = segments[idx - 1] if idx > 0 else None
            prev_limit = round(prev.end_time + MIN_SEAM_GAP_SECONDS, 3) if prev else 0.0

            look_back = seg.start_time
            look_start = max(0.0, look_back - REACTION_CONTEXT_PREROLL_SECONDS)

            reaction_ind = [
                ind for ind in indicators
                if ind.indicator_type in _REACTION_INDICATOR_TYPES
                and ind.start_seconds >= look_start
                and ind.start_seconds < look_back
            ]
            if not reaction_ind:
                continue

            earliest = min(ind.start_seconds for ind in reaction_ind)
            preferred = round(max(prev_limit, max(0.0, earliest - MIN_NATURAL_PREROLL_SECONDS)), 3)

            if preferred >= seg.start_time:
                continue
            if preferred < prev_limit:
                continue
            if seg.end_time - preferred < MIN_SEGMENT_DURATION_SECONDS:
                continue

            # Cap expansion
            max_start = round(seg.start_time - MAX_REACTION_CONTEXT_EXPAND_SECONDS, 3)
            if preferred < max_start:
                preferred = max_start

            dead_overlap = any(
                w.role_type == "silence_or_dead_air"
                and w.score >= 0.65
                and _overlap_seconds(preferred, seg.start_time, w.start_seconds, w.end_seconds) > 0.3
                for w in audio_windows
            )
            if dead_overlap:
                seg.notes.append("seam_reaction_skipped_dead_air")
                continue

            old = seg.start_time
            seg.start_time = preferred
            seg.notes.append(f"seam_reaction_context={old:.3f}->{preferred:.3f}")
            seg.touch()
            summary.reaction_context_expanded += 1
            summary.add_example(f"{seg.segment_id} start {old:.2f}->{preferred:.2f} reaction_context")

    # ── F) Important Context Protection ───────────────────────────────────────

    def _apply_important_context(
        self,
        segments: list[TimelineSegment],
        indicators: list[CutIndicator],
        summary: FinalCutSeamSummary,
    ) -> None:
        for idx, seg in enumerate(segments):
            has_action_start = any(
                ind.indicator_type in _STRONG_POSITIVE_INDICATOR_TYPES
                and ind.start_seconds < seg.start_time + 2.0
                and _overlap_seconds(seg.start_time, seg.start_time + 2.0,
                                     ind.start_seconds, ind.end_seconds) > 0
                for ind in indicators
            )
            if not has_action_start:
                continue

            prev = segments[idx - 1] if idx > 0 else None
            prev_limit = round(prev.end_time + MIN_SEAM_GAP_SECONDS, 3) if prev else 0.0

            look_start = max(prev_limit, seg.start_time - MAX_CONTEXT_EXPAND_SECONDS)

            context_ind = [
                ind for ind in indicators
                if ind.polarity == "positive"
                and ind.start_seconds >= look_start
                and ind.end_seconds <= seg.start_time
            ]
            if not context_ind:
                continue

            preferred = round(max(prev_limit, min(ind.start_seconds for ind in context_ind) - MIN_NATURAL_PREROLL_SECONDS), 3)
            if preferred >= seg.start_time:
                continue
            if preferred < prev_limit:
                continue
            if seg.end_time - preferred < MIN_SEGMENT_DURATION_SECONDS:
                continue

            old = seg.start_time
            seg.start_time = preferred
            seg.notes.append(f"seam_important_context={old:.3f}->{preferred:.3f}")
            seg.touch()
            summary.important_context_expanded += 1
            summary.add_example(f"{seg.segment_id} start {old:.2f}->{preferred:.2f} important_context")

    # ── D) Secondary Speech Hold ──────────────────────────────────────────────

    def _apply_secondary_speech_hold(
        self,
        segments: list[TimelineSegment],
        audio_windows: list[AudioRoleWindow],
        summary: FinalCutSeamSummary,
    ) -> None:
        speech_windows = [w for w in audio_windows if w.role_type in _SECONDARY_SPEECH_ROLES]
        if not speech_windows:
            return

        for idx, seg in enumerate(segments):
            nxt = segments[idx + 1] if idx + 1 < len(segments) else None

            end_window = _find_containing_audio_window(seg.end_time, speech_windows)
            if end_window is not None:
                preferred_end = round(end_window.end_seconds + SECONDARY_SPEECH_HOLD_SECONDS, 3)
                preferred_end = min(preferred_end, seg.end_time + MAX_SECONDARY_SPEECH_EXPAND_SECONDS)
                if preferred_end > seg.end_time:
                    nxt_limit = round(nxt.start_time - MIN_SEAM_GAP_SECONDS, 3) if nxt else None
                    if (
                        (nxt_limit is None or preferred_end <= nxt_limit)
                        and preferred_end - seg.start_time >= MIN_SEGMENT_DURATION_SECONDS
                    ):
                        old = seg.end_time
                        seg.end_time = preferred_end
                        seg.notes.append(f"seam_secondary_speech_end={old:.3f}->{preferred_end:.3f}")
                        seg.touch()
                        summary.secondary_speech_protected += 1
                        summary.add_example(f"{seg.segment_id} end {old:.2f}->{preferred_end:.2f} secondary_speech_hold")

            prev = segments[idx - 1] if idx > 0 else None
            start_window = _find_containing_audio_window(seg.start_time, speech_windows)
            if start_window is not None:
                preferred_start = round(max(0.0, start_window.start_seconds - SECONDARY_SPEECH_HOLD_SECONDS), 3)
                preferred_start = max(preferred_start, seg.start_time - MAX_SECONDARY_SPEECH_EXPAND_SECONDS)
                if preferred_start < seg.start_time:
                    prev_limit = round(prev.end_time + MIN_SEAM_GAP_SECONDS, 3) if prev else 0.0
                    if (
                        preferred_start >= prev_limit
                        and seg.end_time - preferred_start >= MIN_SEGMENT_DURATION_SECONDS
                    ):
                        old = seg.start_time
                        seg.start_time = preferred_start
                        seg.notes.append(f"seam_secondary_speech_start={old:.3f}->{preferred_start:.3f}")
                        seg.touch()
                        summary.secondary_speech_protected += 1
                        summary.add_example(f"{seg.segment_id} start {old:.2f}->{preferred_start:.2f} secondary_speech_hold")

    def _apply_speech_end_locks(
        self,
        segments: list[TimelineSegment],
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
        audio_windows: list[AudioRoleWindow],
        indicators: list[CutIndicator],
        state_windows: list[object],
        summary: FinalCutSeamSummary,
    ) -> None:
        for idx, seg in enumerate(segments):
            nxt = segments[idx + 1] if idx + 1 < len(segments) else None

            source = (
                _find_containing_transcript(seg.end_time, transcripts)
                or _find_near_end_transcript(seg.end_time, transcripts)
                or _find_containing_sentence(seg.end_time, sentences)
                or _find_near_end_sentence(seg.end_time, sentences)
            )
            if source is not None:
                hold = PHRASE_END_LOCK_HOLD_SECONDS if _has_phrase_lock_text(getattr(source, "text", "")) else SPEECH_END_LOCK_HOLD_SECONDS
                counter = "phrase" if hold == PHRASE_END_LOCK_HOLD_SECONDS else "speech"
                preferred = round(source.end_seconds + hold, 3)
                self._lock_segment_end(
                    seg,
                    nxt,
                    preferred,
                    counter,
                    indicators,
                    state_windows,
                    summary,
                )

            audio_source = _find_containing_audio_window(seg.end_time, [
                window for window in audio_windows if window.role_type in _SECONDARY_SPEECH_ROLES
            ])
            if audio_source is not None:
                preferred = round(audio_source.end_seconds + SPEECH_END_LOCK_HOLD_SECONDS, 3)
                self._lock_segment_end(seg, nxt, preferred, "speech", indicators, state_windows, summary)

            shout_windows = [
                indicator
                for indicator in indicators
                if indicator.indicator_type in _SHOUT_END_TYPES
                and indicator.start_seconds <= seg.end_time + SPEECH_END_LOCK_NEAR_SECONDS
                and indicator.end_seconds >= seg.end_time - 1.0
            ]
            if shout_windows:
                preferred = round(max(ind.end_seconds for ind in shout_windows) + SHOUT_END_LOCK_HOLD_SECONDS, 3)
                self._lock_segment_end(seg, nxt, preferred, "shout", indicators, state_windows, summary)

    def _lock_segment_end(
        self,
        seg: TimelineSegment,
        nxt: TimelineSegment | None,
        preferred: float,
        lock_kind: str,
        indicators: list[CutIndicator],
        state_windows: list[object],
        summary: FinalCutSeamSummary,
    ) -> None:
        if preferred <= seg.end_time:
            return
        max_preferred = round(seg.end_time + MAX_SPEECH_END_LOCK_EXPAND_SECONDS, 3)
        if preferred > max_preferred:
            if _has_state_or_shout_protection(seg.end_time, max_preferred, indicators, state_windows):
                preferred = max_preferred
                summary.seam_state_protected += 1
            else:
                trim_back = self._safe_trim_back_for_long_speech(seg, indicators)
                if trim_back is not None:
                    old = seg.end_time
                    seg.end_time = trim_back
                    seg.notes.append(f"seam_speech_lock_trim_back={old:.3f}->{trim_back:.3f}")
                    summary.speech_end_trimmed_back += 1
                    summary.add_example(f"{seg.segment_id} end {old:.2f}->{trim_back:.2f} lock_trim_back")
                return
        if preferred - seg.start_time < MIN_SEGMENT_DURATION_SECONDS:
            return
        if nxt is not None:
            required_next = round(preferred + MIN_SEAM_GAP_SECONDS, 3)
            if nxt.start_time < required_next:
                if nxt.end_time - required_next < MIN_SEGMENT_DURATION_SECONDS:
                    return
                nxt.start_time = required_next
                nxt.notes.append(f"seam_lock_next_start_shifted={required_next:.3f}")
                nxt.touch()
        old = seg.end_time
        seg.end_time = preferred
        seg.notes.append(f"seam_{lock_kind}_end_locked={old:.3f}->{preferred:.3f}")
        seg.touch()
        if lock_kind == "shout":
            summary.shout_end_locked += 1
        elif lock_kind == "phrase":
            summary.phrase_end_locked += 1
        else:
            summary.speech_end_locked += 1
        summary.add_example(f"{seg.segment_id} end {old:.2f}->{preferred:.2f} {lock_kind}_lock")

    def _safe_trim_back_for_long_speech(
        self,
        seg: TimelineSegment,
        indicators: list[CutIndicator],
    ) -> float | None:
        trim_back = round(seg.end_time - 0.20, 3)
        if trim_back <= seg.start_time + MIN_SEGMENT_DURATION_SECONDS:
            return None
        has_action = any(
            indicator.indicator_type in _STRONG_POSITIVE_FOR_MENU
            and _overlap_seconds(trim_back, seg.end_time, indicator.start_seconds, indicator.end_seconds) > 0
            for indicator in indicators
        )
        if has_action:
            return None
        return trim_back

    # ── B) Mini-Seam Gap Guard ────────────────────────────────────────────────

    def _fix_mini_seams(
        self,
        segments: list[TimelineSegment],
        summary: FinalCutSeamSummary,
        transcripts: list[TranscriptSegment] | None = None,
        sentences: list[SentenceItem] | None = None,
    ) -> None:
        transcripts = transcripts or []
        sentences = sentences or []
        for idx in range(len(segments) - 1):
            seg_a = segments[idx]
            seg_b = segments[idx + 1]
            gap = round(seg_b.start_time - seg_a.end_time, 4)
            if gap >= MINI_SEAM_DETECT_THRESHOLD:
                continue

            # Try sentence-aligned start for seg_b
            preferred: float | None = None
            src = (
                _find_containing_transcript(seg_b.start_time, transcripts)
                or _find_containing_sentence(seg_b.start_time, sentences)
            )
            if src is not None:
                src_start = src.start_seconds
                sentence_start = round(max(0.0, src_start - WORD_CUT_PROTECTION_SECONDS), 3)
                if sentence_start > seg_a.end_time + MIN_SEAM_GAP_SECONDS:
                    preferred = sentence_start

            target = round(seg_a.end_time + MINI_SEAM_TARGET_GAP_SECONDS, 3)
            if preferred is None or preferred < target:
                preferred = target

            # Skip if no adjustment needed
            if preferred <= seg_b.start_time:
                continue

            if seg_b.end_time - preferred < MIN_SEGMENT_DURATION_SECONDS:
                if seg_b.segment_role not in _PROTECTED_ROLES:
                    seg_b.notes.append(f"seam_mini_too_short_after_fix_{seg_a.segment_id}")
                    summary.mini_seams_fixed += 1
                    summary.add_example(f"{seg_b.segment_id} mini_seam too_short gap={gap:.3f}")
                continue

            old = seg_b.start_time
            seg_b.start_time = preferred
            seg_b.notes.append(f"seam_mini_gap_fixed={old:.3f}->{preferred:.3f}")
            seg_b.touch()
            summary.mini_seams_fixed += 1
            summary.add_example(f"{seg_b.segment_id} start {old:.2f}->{preferred:.2f} mini_seam_fix")

    # ── Post-Seam Duration Prune ──────────────────────────────────────────────

    def _post_seam_duration_prune(
        self,
        segments: list[TimelineSegment],
        indicators: list[CutIndicator],
        summary: FinalCutSeamSummary,
    ) -> list[TimelineSegment]:
        kept: list[TimelineSegment] = []
        for seg in segments:
            if seg.segment_role in _PROTECTED_ROLES:
                kept.append(seg)
                continue
            if seg.segment_role not in ("build", "bridge"):
                kept.append(seg)
                continue
            if seg.duration <= MAX_BRIDGE_DURATION_AFTER_SEAM_SECONDS:
                kept.append(seg)
                continue

            has_strong_positive = any(
                ind.indicator_type in _STRONG_POSITIVE_INDICATOR_TYPES
                and _overlap_seconds(seg.start_time, seg.end_time, ind.start_seconds, ind.end_seconds) > 0
                for ind in indicators
            )
            if has_strong_positive:
                kept.append(seg)
                continue

            seg.notes.append("seam_long_bridge_post_seam_removed")
            summary.low_value_segments_removed += 1
            summary.add_example(
                f"{seg.segment_id} removed long_bridge_post_seam {seg.duration:.1f}s"
            )

        return kept

    # ── G) Final Cleanup ──────────────────────────────────────────────────────

    def _final_cleanup(self, segments: list[TimelineSegment]) -> list[TimelineSegment]:
        ordered = sorted(
            segments,
            key=lambda s: (s.start_time, s.end_time, s.segment_id),
        )
        kept: list[TimelineSegment] = []
        for seg in ordered:
            if any("seam_mini_too_short_after_fix" in n for n in seg.notes):
                if seg.duration < MIN_SEGMENT_DURATION_SECONDS:
                    continue

            if seg.end_time <= seg.start_time:
                continue

            if seg.duration < MIN_SEGMENT_DURATION_SECONDS and seg.segment_role not in _PROTECTED_ROLES:
                continue

            if kept:
                prev = kept[-1]
                if seg.start_time < prev.end_time + MIN_SEAM_GAP_SECONDS:
                    required = round(prev.end_time + MIN_SEAM_GAP_SECONDS, 3)
                    if seg.end_time - required < MIN_SEGMENT_DURATION_SECONDS:
                        continue
                    seg.start_time = required
                    seg.touch()

            seg.start_time = round(max(0.0, seg.start_time), 3)
            seg.end_time = round(seg.end_time, 3)
            kept.append(seg)

        return kept


# ── Helpers ────────────────────────────────────────────────────────────────────

def _sorted_transcripts(transcript_result: TranscriptResult | None) -> list[TranscriptSegment]:
    if transcript_result is None:
        return []
    return sorted(
        (s for s in transcript_result.segments if s.end_seconds > s.start_seconds),
        key=lambda s: (s.start_seconds, s.end_seconds),
    )


def _sorted_sentences(sentence_timeline_result: SentenceTimelineResult | None) -> list[SentenceItem]:
    if sentence_timeline_result is None:
        return []
    return sorted(
        (s for s in sentence_timeline_result.sentences if s.end_seconds > s.start_seconds),
        key=lambda s: (s.start_seconds, s.end_seconds),
    )


def _sorted_audio_windows(audio_role_result: AudioRoleResult | None) -> list[AudioRoleWindow]:
    if audio_role_result is None:
        return []
    return sorted(
        (w for w in audio_role_result.windows if w.end_seconds > w.start_seconds),
        key=lambda w: (w.start_seconds, w.end_seconds),
    )


def _sorted_indicators(cut_indicator_result: CutIndicatorResult | None) -> list[CutIndicator]:
    if cut_indicator_result is None:
        return []
    return sorted(
        (i for i in cut_indicator_result.indicators if i.end_seconds > i.start_seconds),
        key=lambda i: (i.start_seconds, i.end_seconds),
    )


def _sorted_state_windows(gameplay_state_result) -> list[object]:
    if gameplay_state_result is None:
        return []
    windows = (
        gameplay_state_result.get("windows", [])
        if isinstance(gameplay_state_result, dict)
        else getattr(gameplay_state_result, "windows", [])
    )
    return sorted(
        [window for window in windows or [] if _state_end(window) > _state_start(window)],
        key=lambda window: (_state_start(window), _state_end(window), _state_type(window)),
    )


def _state_type(state: object) -> str:
    return str(state.get("state_type", "") if isinstance(state, dict) else getattr(state, "state_type", ""))


def _state_start(state: object) -> float:
    value = state.get("start_seconds", 0.0) if isinstance(state, dict) else getattr(state, "start_seconds", 0.0)
    return float(value or 0.0)


def _state_end(state: object) -> float:
    value = state.get("end_seconds", 0.0) if isinstance(state, dict) else getattr(state, "end_seconds", 0.0)
    return float(value or 0.0)


def _has_state_or_shout_protection(
    start: float,
    end: float,
    indicators: list[CutIndicator],
    state_windows: list[object],
) -> bool:
    protection_start = max(0.0, start - 1.0)
    return any(
        _state_type(state) in _GOOD_ACTION_STATES
        and _overlap_seconds(protection_start, end, _state_start(state), _state_end(state)) > 0.0
        for state in state_windows
    ) or any(
        indicator.indicator_type in _SHOUT_END_TYPES
        and _overlap_seconds(protection_start, end, indicator.start_seconds, indicator.end_seconds) > 0.0
        for indicator in indicators
    )


def _find_containing_transcript(
    t: float,
    transcripts: list[TranscriptSegment],
) -> TranscriptSegment | None:
    for seg in transcripts:
        if seg.start_seconds < t < seg.end_seconds:
            return seg
    return None


def _find_near_end_transcript(
    t: float,
    transcripts: list[TranscriptSegment],
) -> TranscriptSegment | None:
    for seg in transcripts:
        if seg.start_seconds <= t <= seg.end_seconds + SPEECH_END_LOCK_NEAR_SECONDS:
            if abs(seg.end_seconds - t) <= SPEECH_END_LOCK_NEAR_SECONDS:
                return seg
    return None


def _find_containing_sentence(
    t: float,
    sentences: list[SentenceItem],
) -> SentenceItem | None:
    for s in sentences:
        if s.start_seconds < t < s.end_seconds:
            return s
    return None


def _find_near_end_sentence(
    t: float,
    sentences: list[SentenceItem],
) -> SentenceItem | None:
    for s in sentences:
        if s.start_seconds <= t <= s.end_seconds + SPEECH_END_LOCK_NEAR_SECONDS:
            if abs(s.end_seconds - t) <= SPEECH_END_LOCK_NEAR_SECONDS:
                return s
    return None


def _find_containing_audio_window(
    t: float,
    windows: list[AudioRoleWindow],
) -> AudioRoleWindow | None:
    for w in windows:
        if w.start_seconds < t < w.end_seconds:
            return w
    return None


def _has_phrase_lock_text(text: str) -> bool:
    lowered = (text or "").lower()
    return any(phrase in lowered for phrase in _PHRASE_LOCK_TEXT)
