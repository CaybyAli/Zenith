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
LOW_VALUE_BRIDGE_MAX_SECONDS = 8.0
LOW_VALUE_BRIDGE_SCORE_THRESHOLD = 0.50
MAX_CONTEXT_EXPAND_SECONDS = 1.50
MIN_SEGMENT_DURATION_SECONDS = 2.5

_NEGATIVE_INDICATOR_TYPES = frozenset({
    "round_end_dead_time", "silence_or_dead_air", "low_gameplay_value",
    "filler_sentence", "menu_or_idle",
})
_STRONG_POSITIVE_INDICATOR_TYPES = frozenset({
    "goal_or_save_like_flash", "high_action_burst", "hook_sentence", "group_reaction_like",
})
_REACTION_INDICATOR_TYPES = frozenset({
    "goal_or_save_like_flash", "high_action_burst", "facecam_reaction_spike",
    "shock_like", "group_reaction_like", "shout_like_audio",
})
_SECONDARY_SPEECH_ROLES = frozenset({
    "secondary_speech_like", "speech_active",
})
_PROTECTED_ROLES = frozenset({"hook", "payoff", "peak"})


@dataclass
class FinalCutSeamSummary:
    mini_seams_fixed: int = 0
    speech_start_adjusted: int = 0
    speech_end_adjusted: int = 0
    reaction_context_expanded: int = 0
    secondary_speech_protected: int = 0
    low_value_segments_removed: int = 0
    important_context_expanded: int = 0
    duration_before: float = 0.0
    duration_after: float = 0.0
    examples: list[str] = field(default_factory=list)

    def add_example(self, text: str) -> None:
        if len(self.examples) < 8:
            self.examples.append(text)


def _overlap_seconds(a_start: float, a_end: float, b_start: float, b_end: float) -> float:
    return max(0.0, min(a_end, b_end) - max(a_start, b_start))


class FinalCutSeamGuard:
    engine = "final-cut-seam-guard-v1"

    def apply(
        self,
        segments: list[TimelineSegment],
        *,
        transcript_result: TranscriptResult | None = None,
        sentence_timeline_result: SentenceTimelineResult | None = None,
        audio_role_result: AudioRoleResult | None = None,
        cut_indicator_result: CutIndicatorResult | None = None,
        cut_scoring_profile=None,
    ) -> tuple[list[TimelineSegment], FinalCutSeamSummary]:
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

        # E) Low-Value Bridge Pruner — remove unwanted segments first
        ordered = self._prune_low_value_bridges(ordered, indicators, summary)
        if not ordered:
            summary.duration_after = 0.0
            return ordered, summary

        # A) Word-Cut / Sentence-Seam Protection
        self._apply_seam_speech_protection(ordered, transcripts, sentences, summary)

        # C) Reaction Context Guard
        self._apply_reaction_context(ordered, indicators, audio_windows, summary)

        # F) Important Context Protection
        self._apply_important_context(ordered, indicators, summary)

        # D) Secondary Speech Hold
        self._apply_secondary_speech_hold(ordered, audio_windows, summary)

        # B) Mini-Seam Gap Guard
        self._fix_mini_seams(ordered, summary)

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

            has_negative = any(
                ind.indicator_type in _NEGATIVE_INDICATOR_TYPES
                and _overlap_seconds(seg.start_time, seg.end_time, ind.start_seconds, ind.end_seconds) > 0
                for ind in indicators
            )
            if not has_negative:
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

            seg.notes.append("seam_low_value_bridge_removed")
            summary.low_value_segments_removed += 1
            summary.add_example(f"{seg.segment_id} removed low_value_bridge {seg.start_time:.2f}-{seg.end_time:.2f}")

        return kept

    # ── A) Word-Cut / Sentence-Seam Protection ────────────────────────────────

    def _apply_seam_speech_protection(
        self,
        segments: list[TimelineSegment],
        transcripts: list[TranscriptSegment],
        sentences: list[SentenceItem],
        summary: FinalCutSeamSummary,
    ) -> None:
        if not transcripts and not sentences:
            return
        for idx, seg in enumerate(segments):
            prev = segments[idx - 1] if idx > 0 else None
            nxt = segments[idx + 1] if idx + 1 < len(segments) else None
            self._protect_segment_start(seg, prev, transcripts, sentences, summary)
            self._protect_segment_end(seg, nxt, transcripts, sentences, summary)
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
        src_start = src.start_seconds if isinstance(src, TranscriptSegment) else src.start_seconds
        preferred = round(max(0.0, src_start - WORD_CUT_PROTECTION_SECONDS), 3)
        if preferred >= seg.start_time:
            seg.notes.append("seam_start_skipped_already_before")
            return
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
        summary: FinalCutSeamSummary,
    ) -> None:
        boundary = seg.end_time
        src = _find_containing_transcript(boundary, transcripts) or _find_containing_sentence(boundary, sentences)
        if src is None:
            return
        src_end = src.end_seconds if isinstance(src, TranscriptSegment) else src.end_seconds
        preferred = round(src_end + WORD_CUT_PROTECTION_SECONDS, 3)
        if preferred <= seg.end_time:
            seg.notes.append("seam_end_skipped_already_after")
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

    # ── C) Reaction Context Guard ─────────────────────────────────────────────

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

            # Guard: don't pull into strong dead-air
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
            # Segment has strong action in its first 2s
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

            # Find positive indicator just before the segment
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

            # Check if end is inside a secondary speech window
            end_window = _find_containing_audio_window(seg.end_time, speech_windows)
            if end_window is not None:
                preferred_end = round(end_window.end_seconds + SECONDARY_SPEECH_HOLD_SECONDS, 3)
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

            # Check if start is inside a secondary speech window
            prev = segments[idx - 1] if idx > 0 else None
            start_window = _find_containing_audio_window(seg.start_time, speech_windows)
            if start_window is not None:
                preferred_start = round(max(0.0, start_window.start_seconds - SECONDARY_SPEECH_HOLD_SECONDS), 3)
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

    # ── B) Mini-Seam Gap Guard ────────────────────────────────────────────────

    def _fix_mini_seams(
        self,
        segments: list[TimelineSegment],
        summary: FinalCutSeamSummary,
    ) -> None:
        for idx in range(len(segments) - 1):
            seg_a = segments[idx]
            seg_b = segments[idx + 1]
            gap = round(seg_b.start_time - seg_a.end_time, 4)
            if gap >= MIN_SEAM_GAP_SECONDS:
                continue

            required_start = round(seg_a.end_time + MIN_SEAM_GAP_SECONDS, 3)
            if seg_b.end_time - required_start < MIN_SEGMENT_DURATION_SECONDS:
                # Would make seg_b too short — mark for removal in final cleanup
                seg_b.notes.append(f"seam_mini_too_short_after_fix_{seg_a.segment_id}")
                summary.mini_seams_fixed += 1
                summary.add_example(f"{seg_b.segment_id} mini_seam too_short gap={gap:.3f}")
                continue

            old = seg_b.start_time
            seg_b.start_time = required_start
            seg_b.notes.append(f"seam_mini_gap_fixed={old:.3f}->{required_start:.3f}")
            seg_b.touch()
            summary.mini_seams_fixed += 1
            summary.add_example(f"{seg_b.segment_id} start {old:.2f}->{required_start:.2f} mini_seam_fix")

    # ── G) Final Cleanup ──────────────────────────────────────────────────────

    def _final_cleanup(self, segments: list[TimelineSegment]) -> list[TimelineSegment]:
        ordered = sorted(
            segments,
            key=lambda s: (s.start_time, s.end_time, s.segment_id),
        )
        kept: list[TimelineSegment] = []
        for seg in ordered:
            # Remove if flagged as too-short after mini-seam fix
            if any("seam_mini_too_short_after_fix" in n for n in seg.notes):
                if seg.duration < MIN_SEGMENT_DURATION_SECONDS:
                    continue

            # Remove negative-duration / zero-duration segments
            if seg.end_time <= seg.start_time:
                continue

            # Remove segments that are now too short (unless protected role)
            if seg.duration < MIN_SEGMENT_DURATION_SECONDS and seg.segment_role not in _PROTECTED_ROLES:
                continue

            # Resolve overlaps with previous
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


def _find_containing_transcript(
    t: float,
    transcripts: list[TranscriptSegment],
) -> TranscriptSegment | None:
    for seg in transcripts:
        if seg.start_seconds < t < seg.end_seconds:
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


def _find_containing_audio_window(
    t: float,
    windows: list[AudioRoleWindow],
) -> AudioRoleWindow | None:
    for w in windows:
        if w.start_seconds < t < w.end_seconds:
            return w
    return None
