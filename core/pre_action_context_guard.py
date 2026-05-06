from __future__ import annotations

from dataclasses import dataclass, field

from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.cut_indicator import CutIndicator, CutIndicatorResult
from models.timeline_segment import TimelineSegment


PRE_ACTION_CONTEXT_SECONDS = 0.90
PRE_SHOUT_CONTEXT_SECONDS = 1.20
PRE_GOAL_CONTEXT_SECONDS = 1.00
MAX_PRE_CONTEXT_EXPAND_SECONDS = 1.20
MIN_SEGMENT_DURATION_SECONDS = 2.5
MIN_GAP_SECONDS = 0.15

_ACTION_TYPES = frozenset({
    "high_action_burst",
    "sustained_action",
    "facecam_reaction_spike",
})
_GOAL_TYPES = frozenset({"goal_or_save_like_flash"})
_SHOUT_TYPES = frozenset({"shout_like_audio", "group_reaction_like"})


@dataclass
class PreActionContextSummary:
    expanded: int = 0
    shout: int = 0
    goal: int = 0
    action: int = 0
    skipped_overlap: int = 0
    skipped_silence: int = 0
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

        for index, segment in enumerate(ordered):
            previous = ordered[index - 1] if index > 0 else None
            trigger = self._trigger_near_start(segment, indicators)
            if trigger is None:
                continue

            context_seconds, trigger_kind = self._context_for_trigger(trigger)
            context_seconds = min(context_seconds, MAX_PRE_CONTEXT_EXPAND_SECONDS)
            previous_limit = round(previous.end_time + MIN_GAP_SECONDS, 3) if previous else 0.0
            preferred = round(max(0.0, segment.start_time - context_seconds), 3)

            if preferred < previous_limit:
                if segment.start_time - previous_limit < 0.35:
                    preferred = previous_limit
                else:
                    summary.skipped_overlap += 1
                    segment.notes.append("pre_action_context_skipped_overlap")
                    continue

            if preferred >= segment.start_time:
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
                f"pre_action_context_{trigger_kind}={old:.3f}->{segment.start_time:.3f}"
            )
            segment.touch()
            summary.expanded += 1
            if trigger_kind == "shout":
                summary.shout += 1
            elif trigger_kind == "goal":
                summary.goal += 1
            else:
                summary.action += 1
            summary.add_example(
                f"{segment.segment_id} {trigger_kind} start {old:.2f}->{segment.start_time:.2f}"
            )

        ordered = self._cleanup(ordered)
        summary.duration_after = round(sum(segment.duration for segment in ordered), 3)
        print(
            "[TIMELINE-PRE-ACTION-CONTEXT] "
            f"expanded={summary.expanded} "
            f"shout={summary.shout} "
            f"goal={summary.goal} "
            f"action={summary.action} "
            f"skipped_overlap={summary.skipped_overlap} "
            f"skipped_silence={summary.skipped_silence} "
            f"duration_before={summary.duration_before:.3f}s "
            f"duration_after={summary.duration_after:.3f}s"
        )
        if summary.examples:
            print(f"[TIMELINE-PRE-ACTION-CONTEXT] examples={'; '.join(summary.examples)}")
        return ordered, summary

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
            and indicator.end_seconds >= segment.start_time
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


def _overlap_seconds(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))
