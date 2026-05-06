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
    "hook_sentence",
    "facecam_reaction_spike",
})
_SPEECH_TYPES = frozenset({"speech_active", "secondary_speech_like"})


@dataclass
class RoundWaitDeadtimeSummary:
    removed: int = 0
    trimmed: int = 0
    kept_action: int = 0
    kept_speech: int = 0
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

        kept: list[TimelineSegment] = []
        for segment in ordered:
            if segment.segment_role in _PROTECTED_ROLES:
                kept.append(segment)
                continue
            if segment.segment_role not in _TARGET_ROLES or segment.duration <= ROUND_WAIT_MIN_DURATION:
                kept.append(segment)
                continue
            if self._has_positive(segment.start_time, segment.end_time, indicators):
                summary.kept_action += 1
                kept.append(segment)
                continue
            if self._has_valuable_speech(segment, indicators, audio_windows):
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
            f"kept_action={summary.kept_action} "
            f"kept_speech={summary.kept_speech} "
            f"duration_before={summary.duration_before:.3f}s "
            f"duration_after={summary.duration_after:.3f}s"
        )
        if summary.examples:
            print(f"[TIMELINE-ROUND-WAIT-GUARD] examples={'; '.join(summary.examples)}")
        return kept, summary

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
