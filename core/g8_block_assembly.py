
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


YOUTUBE_MIN_DURATION_SECONDS = 480.0
G8_MIN_PREFERRED_SECONDS = 720.0
G8_PREFERRED_TARGET_SECONDS = 900.0
G8_MAX_SECONDS = 1200.0
DEFAULT_BRIDGE_SECONDS = 8.0
DEFAULT_ROUND_GAP_SECONDS = 45.0
DEFAULT_LOBBY_MIN_SECONDS = 5.0
DEFAULT_LOBBY_BOUNDARY_MIN_ACTIVE_SECONDS = 80.0
DEFAULT_MIN_STANDALONE_BLOCK_SECONDS = 12.0
ANTI_OVERCUT_TOLERANCE_SECONDS = 0.5

ACTIVE_STATE = "active_play"
BRIDGE_STATES = {"transition_dead_time", "replay_break", "intro_menu_lobby", "unknown"}
TRIM_DECISIONS = {"trimmable_low_engagement", "frozen_or_paused"}
KEEP_DECISIONS = {"keep_active"}


def _round_seconds(value: float) -> float:
    return round(max(0.0, float(value)), 3)


def _clamp01(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 3)


def _field(item: Any, *names: str, default: Any = None) -> Any:
    for name in names:
        if isinstance(item, Mapping) and name in item:
            return item[name]
        if hasattr(item, name):
            return getattr(item, name)
    return default


def _duration(start: float, end: float) -> float:
    return max(0.0, float(end) - float(start))


def _overlap_seconds(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(float(end_a), float(end_b)) - max(float(start_a), float(start_b)))


def _merge_ranges(ranges: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    ordered = sorted(
        (_round_seconds(start), _round_seconds(end))
        for start, end in ranges
        if float(end) > float(start)
    )
    merged: list[list[float]] = []
    for start, end in ordered:
        if not merged or start > merged[-1][1]:
            merged.append([start, end])
        else:
            merged[-1][1] = max(merged[-1][1], end)
    return [(round(start, 3), round(end, 3)) for start, end in merged]


def _subtract_ranges(
    source_ranges: Iterable[tuple[float, float]],
    cut_ranges: Iterable[tuple[float, float]],
) -> list[tuple[float, float]]:
    remaining = _merge_ranges(source_ranges)
    cuts = _merge_ranges(cut_ranges)
    for cut_start, cut_end in cuts:
        next_remaining: list[tuple[float, float]] = []
        for start, end in remaining:
            if cut_end <= start or cut_start >= end:
                next_remaining.append((start, end))
                continue
            if start < cut_start:
                next_remaining.append((start, min(cut_start, end)))
            if cut_end < end:
                next_remaining.append((max(cut_end, start), end))
        remaining = next_remaining
    return _merge_ranges(remaining)


def _complement_ranges(
    start: float,
    end: float,
    kept_ranges: Iterable[tuple[float, float]],
) -> list[tuple[float, float]]:
    cursor = float(start)
    gaps: list[tuple[float, float]] = []
    for keep_start, keep_end in _merge_ranges(kept_ranges):
        if keep_start > cursor:
            gaps.append((round(cursor, 3), round(keep_start, 3)))
        cursor = max(cursor, keep_end)
    if cursor < end:
        gaps.append((round(cursor, 3), round(float(end), 3)))
    return [(gap_start, gap_end) for gap_start, gap_end in gaps if gap_end > gap_start]


def _covered_seconds_by_ranges(
    start: float,
    end: float,
    cover_ranges: Iterable[tuple[float, float]],
) -> float:
    clipped = []
    for cover_start, cover_end in cover_ranges:
        overlap_start = max(float(start), float(cover_start))
        overlap_end = min(float(end), float(cover_end))
        if overlap_end > overlap_start:
            clipped.append((overlap_start, overlap_end))
    return round(sum(range_end - range_start for range_start, range_end in _merge_ranges(clipped)), 3)


@dataclass(frozen=True)
class G8SourceSpan:
    start_seconds: float
    end_seconds: float
    state: str
    intensity: str = "unknown"
    confidence: float = 0.0
    source: str = "g6"
    decision: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration_seconds(self) -> float:
        return round(max(0.0, self.end_seconds - self.start_seconds), 3)

    @property
    def is_active(self) -> bool:
        return self.state == ACTIVE_STATE

    def to_dict(self) -> dict[str, Any]:
        data = {
            "start_seconds": _round_seconds(self.start_seconds),
            "end_seconds": _round_seconds(self.end_seconds),
            "duration_seconds": self.duration_seconds,
            "state": self.state,
            "intensity": self.intensity,
            "confidence": _clamp01(self.confidence),
            "source": self.source,
        }
        if self.decision is not None:
            data["decision"] = self.decision
        if self.metadata:
            data["metadata"] = dict(self.metadata)
        return data


@dataclass
class G8Block:
    block_id: str
    start_seconds: float
    end_seconds: float
    source_spans: list[G8SourceSpan]
    active_ranges: list[tuple[float, float]]
    trim_ranges: list[tuple[float, float]]
    keep_ranges: list[tuple[float, float]]
    keep_active_budget_seconds: float
    quality_score: float
    quality_source: str
    selected: bool = False
    rank: int | None = None

    @property
    def duration_seconds(self) -> float:
        return round(max(0.0, self.end_seconds - self.start_seconds), 3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_id": self.block_id,
            "rank": self.rank,
            "selected": self.selected,
            "start_seconds": _round_seconds(self.start_seconds),
            "end_seconds": _round_seconds(self.end_seconds),
            "duration_seconds": self.duration_seconds,
            "keep_active_budget_seconds": round(self.keep_active_budget_seconds, 3),
            "quality_score": _clamp01(self.quality_score),
            "quality_source": self.quality_source,
            "active_ranges": [
                {"start_seconds": start, "end_seconds": end, "duration_seconds": round(end - start, 3)}
                for start, end in self.active_ranges
            ],
            "trim_ranges": [
                {"start_seconds": start, "end_seconds": end, "duration_seconds": round(end - start, 3)}
                for start, end in self.trim_ranges
            ],
            "keep_ranges": [
                {"start_seconds": start, "end_seconds": end, "duration_seconds": round(end - start, 3)}
                for start, end in self.keep_ranges
            ],
            "source_spans": [span.to_dict() for span in self.source_spans],
        }


@dataclass(frozen=True)
class G8TimelinePlanSegment:
    segment_id: str
    block_id: str
    start_seconds: float
    end_seconds: float
    state: str
    keep_decision: str
    source: str = "g8_block_assembly"

    @property
    def duration_seconds(self) -> float:
        return round(max(0.0, self.end_seconds - self.start_seconds), 3)

    def to_dict(self) -> dict[str, Any]:
        return {
            "segment_id": self.segment_id,
            "block_id": self.block_id,
            "start_seconds": _round_seconds(self.start_seconds),
            "end_seconds": _round_seconds(self.end_seconds),
            "duration_seconds": self.duration_seconds,
            "state": self.state,
            "keep_decision": self.keep_decision,
            "source": self.source,
        }


@dataclass(frozen=True)
class G8AntiOvercutIssue:
    block_id: str
    gap_start_seconds: float
    gap_end_seconds: float
    active_overlap_seconds: float
    trim_covered_seconds: float
    uncovered_active_seconds: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "block_id": self.block_id,
            "gap_start_seconds": _round_seconds(self.gap_start_seconds),
            "gap_end_seconds": _round_seconds(self.gap_end_seconds),
            "active_overlap_seconds": round(self.active_overlap_seconds, 3),
            "trim_covered_seconds": round(self.trim_covered_seconds, 3),
            "uncovered_active_seconds": round(self.uncovered_active_seconds, 3),
            "reason": self.reason,
        }


@dataclass
class G8AssemblyPlan:
    plan_id: str
    label: str
    status: str
    bridge_seconds: float
    round_gap_seconds: float
    lobby_min_seconds: float
    lobby_boundary_min_active_seconds: float
    target_duration_seconds: float
    available_keep_active_budget_seconds: float
    selected_keep_active_budget_seconds: float
    planned_output_duration_seconds: float
    old_performance_cap_seconds: float
    old_performance_stop_92_seconds: float
    performance_cap_removed_for_longform: bool
    blocks: list[G8Block]
    selected_blocks: list[G8Block]
    timeline_segments: list[G8TimelinePlanSegment]
    anti_overcut_issues: list[G8AntiOvercutIssue]
    minimum_standalone_block_filter: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    @property
    def anti_overcut_fail_count(self) -> int:
        return len(self.anti_overcut_issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "label": self.label,
            "engine": "g8-block-assembly-planner-v1",
            "status": self.status,
            "bridge_seconds": round(self.bridge_seconds, 3),
            "round_gap_seconds": round(self.round_gap_seconds, 3),
            "lobby_min_seconds": round(self.lobby_min_seconds, 3),
            "lobby_boundary_min_active_seconds": round(self.lobby_boundary_min_active_seconds, 3),
            "duration_contract": {
                "youtube_floor_seconds": YOUTUBE_MIN_DURATION_SECONDS,
                "preferred_min_seconds": G8_MIN_PREFERRED_SECONDS,
                "preferred_target_seconds": G8_PREFERRED_TARGET_SECONDS,
                "ceiling_seconds": G8_MAX_SECONDS,
                "available_keep_active_budget_seconds": round(self.available_keep_active_budget_seconds, 3),
                "selected_keep_active_budget_seconds": round(self.selected_keep_active_budget_seconds, 3),
                "target_duration_seconds": round(self.target_duration_seconds, 3),
                "planned_output_duration_seconds": round(self.planned_output_duration_seconds, 3),
            },
            "old_vs_new": {
                "old_performance_cap_seconds": round(self.old_performance_cap_seconds, 3),
                "old_performance_stop_92_seconds": round(self.old_performance_stop_92_seconds, 3),
                "new_planned_output_duration_seconds": round(self.planned_output_duration_seconds, 3),
                "performance_cap_removed_for_longform": self.performance_cap_removed_for_longform,
            },
            "anti_overcut_audit": {
                "fail_count": self.anti_overcut_fail_count,
                "tolerance_seconds": ANTI_OVERCUT_TOLERANCE_SECONDS,
                "issues": [issue.to_dict() for issue in self.anti_overcut_issues],
            },
            "minimum_standalone_block_filter": dict(self.minimum_standalone_block_filter or {}),
            "blocks": [block.to_dict() for block in self.blocks],
            "selected_blocks": [block.to_dict() for block in self.selected_blocks],
            "timeline_segments": [segment.to_dict() for segment in self.timeline_segments],
            "notes": list(self.notes),
        }


class G8BlockAssemblyPlanner:
    """Builds a review-only longform timeline plan from G6 play segments plus optional G7a trims."""

    engine = "g8-block-assembly-planner-v1"

    def __init__(
        self,
        bridge_seconds: float = DEFAULT_BRIDGE_SECONDS,
        min_standalone_block_seconds: float = DEFAULT_MIN_STANDALONE_BLOCK_SECONDS,
        round_gap_seconds: float = DEFAULT_ROUND_GAP_SECONDS,
        lobby_min_seconds: float = DEFAULT_LOBBY_MIN_SECONDS,
        lobby_boundary_min_active_seconds: float = DEFAULT_LOBBY_BOUNDARY_MIN_ACTIVE_SECONDS,
    ) -> None:
        self.bridge_seconds = max(0.0, float(bridge_seconds))
        self.min_standalone_block_seconds = max(
            0.0,
            float(min_standalone_block_seconds),
        )
        self.round_gap_seconds = max(0.0, float(round_gap_seconds))
        self.lobby_min_seconds = max(0.0, float(lobby_min_seconds))
        self.lobby_boundary_min_active_seconds = max(0.0, float(lobby_boundary_min_active_seconds))

    def build_plan(
        self,
        *,
        label: str,
        play_segments: Iterable[Any],
        g7a_spans: Iterable[Any] | None = None,
        highlights: Iterable[Any] | None = None,
    ) -> G8AssemblyPlan:
        normalized_segments = self.normalize_play_segments(play_segments)
        trim_spans = self.normalize_g7a_trim_spans(g7a_spans or [])
        highlight_spans = self.normalize_highlights(highlights or [])

        blocks = self.build_blocks(normalized_segments)
        for block in blocks:
            block.trim_ranges = self._trim_ranges_for_block(block, trim_spans)
            block.keep_ranges = _subtract_ranges(block.active_ranges, block.trim_ranges)
            block.keep_active_budget_seconds = round(
                sum(end - start for start, end in block.keep_ranges),
                3,
            )
            block.quality_score, block.quality_source = self._score_block(block, highlight_spans)

        blocks = [block for block in blocks if block.keep_active_budget_seconds > 0.0]
        blocks, minimum_filter_report = self.apply_minimum_standalone_block_filter(blocks)
        ranked_blocks = sorted(
            blocks,
            key=lambda block: (-block.quality_score, -block.keep_active_budget_seconds, block.start_seconds),
        )
        for index, block in enumerate(ranked_blocks, start=1):
            block.rank = index

        available_budget = round(sum(block.keep_active_budget_seconds for block in blocks), 3)
        selected_blocks, target_duration, status, notes = self._select_blocks(
            ranked_blocks,
            available_budget,
        )
        if int(minimum_filter_report.get("discarded_count", 0) or 0) > 0:
            notes.append("g8_1_min_standalone_filter_discarded_isolated_micro_blocks")
        if bool(minimum_filter_report.get("after_budget_below_720", False)):
            notes.append("g8_1_less_viable_content_after_min_standalone_filter")
        notes.append(
            "g8_2_state_aware_round_gap_lookahead_enabled "
            f"round_gap_seconds={self.round_gap_seconds:.3f} "
            f"lobby_min_seconds={self.lobby_min_seconds:.3f} "
            f"lobby_boundary_min_active_seconds={self.lobby_boundary_min_active_seconds:.3f}"
        )
        selected_blocks = sorted(selected_blocks, key=lambda block: (block.start_seconds, block.end_seconds))
        for block in blocks:
            block.selected = block in selected_blocks

        timeline_segments = self._timeline_segments_from_blocks(selected_blocks)
        planned_duration = round(sum(segment.duration_seconds for segment in timeline_segments), 3)
        selected_budget = round(sum(block.keep_active_budget_seconds for block in selected_blocks), 3)

        issues = self.audit_active_play_gaps(
            selected_blocks=selected_blocks,
            timeline_segments=timeline_segments,
            trim_spans=trim_spans,
        )

        if issues:
            status = "anti_overcut_failed"
        elif available_budget < G8_MIN_PREFERRED_SECONDS:
            status = "planned_below_720_not_enough_keep_active_budget"
        elif planned_duration >= G8_MIN_PREFERRED_SECONDS:
            status = "planned"
        else:
            status = "planned_below_720_selected_budget"

        return G8AssemblyPlan(
            plan_id=f"g8_plan_{uuid.uuid4().hex[:12]}",
            label=str(label),
            status=status,
            bridge_seconds=self.bridge_seconds,
            round_gap_seconds=self.round_gap_seconds,
            lobby_min_seconds=self.lobby_min_seconds,
            lobby_boundary_min_active_seconds=self.lobby_boundary_min_active_seconds,
            target_duration_seconds=round(target_duration, 3),
            available_keep_active_budget_seconds=available_budget,
            selected_keep_active_budget_seconds=selected_budget,
            planned_output_duration_seconds=planned_duration,
            old_performance_cap_seconds=540.0,
            old_performance_stop_92_seconds=round(540.0 * 0.92, 3),
            performance_cap_removed_for_longform=True,
            blocks=sorted(blocks, key=lambda block: (block.start_seconds, block.end_seconds)),
            selected_blocks=selected_blocks,
            timeline_segments=timeline_segments,
            anti_overcut_issues=issues,
            minimum_standalone_block_filter=minimum_filter_report,
            notes=notes,
        )

    def normalize_play_segments(self, play_segments: Iterable[Any]) -> list[G8SourceSpan]:
        normalized: list[G8SourceSpan] = []
        for item in play_segments:
            start = _field(item, "start_seconds", "start_time", "start", default=None)
            end = _field(item, "end_seconds", "end_time", "end", default=None)
            if start is None or end is None:
                continue
            if float(end) <= float(start):
                continue
            state = str(_field(item, "state", "state_type", "phase", default="unknown") or "unknown")
            intensity = str(_field(item, "intensity", default="unknown") or "unknown")
            confidence = float(_field(item, "confidence", "score", default=0.0) or 0.0)
            evidence = _field(item, "evidence", "metadata", default={})
            normalized.append(
                G8SourceSpan(
                    start_seconds=_round_seconds(start),
                    end_seconds=_round_seconds(end),
                    state=state,
                    intensity=intensity,
                    confidence=_clamp01(confidence),
                    source="g6_play_segment",
                    metadata=dict(evidence or {}) if isinstance(evidence, Mapping) else {},
                )
            )
        return sorted(normalized, key=lambda span: (span.start_seconds, span.end_seconds, span.state))

    def normalize_g7a_trim_spans(self, g7a_spans: Iterable[Any]) -> list[G8SourceSpan]:
        normalized: list[G8SourceSpan] = []
        for item in g7a_spans:
            start = _field(item, "start_seconds", "start_time", "start", default=None)
            end = _field(item, "end_seconds", "end_time", "end", default=None)
            if start is None or end is None:
                continue
            if float(end) <= float(start):
                continue
            decision = str(
                _field(
                    item,
                    "decision",
                    "g7a_decision",
                    "classification",
                    "label",
                    "state",
                    "state_type",
                    "type",
                    default="",
                )
                or ""
            )
            if decision not in TRIM_DECISIONS:
                continue
            normalized.append(
                G8SourceSpan(
                    start_seconds=_round_seconds(start),
                    end_seconds=_round_seconds(end),
                    state=ACTIVE_STATE,
                    confidence=float(_field(item, "confidence", "score", default=1.0) or 1.0),
                    source="g7a_trim_span",
                    decision=decision,
                    metadata={"raw_decision": decision},
                )
            )
        return sorted(normalized, key=lambda span: (span.start_seconds, span.end_seconds, span.decision or ""))

    def normalize_highlights(self, highlights: Iterable[Any]) -> list[G8SourceSpan]:
        normalized: list[G8SourceSpan] = []
        for item in highlights:
            start = _field(item, "start_seconds", "start_time", "start", default=None)
            end = _field(item, "end_seconds", "end_time", "end", default=None)
            if start is None or end is None:
                continue
            if float(end) <= float(start):
                continue
            score = float(_field(item, "selection_score", "highlight_score", "score", default=0.0) or 0.0)
            normalized.append(
                G8SourceSpan(
                    start_seconds=_round_seconds(start),
                    end_seconds=_round_seconds(end),
                    state="highlight_quality",
                    confidence=_clamp01(score),
                    source="highlight_quality",
                    metadata={
                        "candidate_id": str(_field(item, "candidate_id", "id", default="")),
                        "score": _clamp01(score),
                    },
                )
            )
        return sorted(normalized, key=lambda span: (span.start_seconds, span.end_seconds))

    def build_blocks(self, play_segments: list[G8SourceSpan]) -> list[G8Block]:
        """
        G8.2 state-aware round-end lookahead block builder.

        A block bridges a non-active gap only when:
        - the next active_play is within round_gap_seconds, and
        - the gap does not contain a real lobby boundary.

        A real lobby boundary requires:
        - cumulative intro_menu_lobby overlap >= lobby_min_seconds, and
        - enough active round context before that lobby
          (lobby_boundary_min_active_seconds).

        This avoids false G6 lobby blips splitting a live round.
        """
        ordered = sorted(
            play_segments,
            key=lambda span: (span.start_seconds, span.end_seconds, span.state),
        )
        active_spans = [span for span in ordered if span.is_active]
        if not active_spans:
            return []

        blocks: list[G8Block] = []
        current_active: list[G8SourceSpan] = []

        def non_active_spans_between(gap_start: float, gap_end: float) -> list[G8SourceSpan]:
            return [
                span
                for span in ordered
                if not span.is_active
                and span.end_seconds > gap_start
                and span.start_seconds < gap_end
            ]

        def cumulative_intro_lobby_seconds(
            spans: list[G8SourceSpan],
            gap_start: float,
            gap_end: float,
        ) -> float:
            lobby_ranges = []
            for span in spans:
                if span.state != "intro_menu_lobby":
                    continue
                start = max(gap_start, span.start_seconds)
                end = min(gap_end, span.end_seconds)
                if end > start:
                    lobby_ranges.append((start, end))
            return round(sum(end - start for start, end in _merge_ranges(lobby_ranges)), 3)

        def current_active_budget_seconds() -> float:
            return round(
                sum(max(0.0, span.end_seconds - span.start_seconds) for span in current_active),
                3,
            )

        def close_current() -> None:
            nonlocal current_active
            if not current_active:
                return

            active_ranges = _merge_ranges(
                (span.start_seconds, span.end_seconds)
                for span in current_active
            )
            if not active_ranges:
                current_active = []
                return

            block_start = active_ranges[0][0]
            block_end = active_ranges[-1][1]
            source_spans = [
                span
                for span in ordered
                if span.end_seconds > block_start
                and span.start_seconds < block_end
            ]

            blocks.append(
                G8Block(
                    block_id=f"g8_block_{len(blocks) + 1:03d}",
                    start_seconds=block_start,
                    end_seconds=block_end,
                    source_spans=source_spans,
                    active_ranges=active_ranges,
                    trim_ranges=[],
                    keep_ranges=active_ranges,
                    keep_active_budget_seconds=round(
                        sum(end - start for start, end in active_ranges),
                        3,
                    ),
                    quality_score=0.0,
                    quality_source="unscored",
                )
            )
            current_active = []

        current_active = [active_spans[0]]

        for next_active in active_spans[1:]:
            previous_active = current_active[-1]
            gap_start = previous_active.end_seconds
            gap_end = next_active.start_seconds
            gap_to_next_active = round(max(0.0, gap_end - gap_start), 3)

            gap_spans = non_active_spans_between(gap_start, gap_end)
            lobby_seconds = cumulative_intro_lobby_seconds(gap_spans, gap_start, gap_end)
            active_budget_before_lobby = current_active_budget_seconds()

            has_real_lobby_boundary = (
                lobby_seconds >= self.lobby_min_seconds
                and active_budget_before_lobby >= self.lobby_boundary_min_active_seconds
            )

            if (not has_real_lobby_boundary) and gap_to_next_active <= self.round_gap_seconds:
                current_active.append(next_active)
                continue

            close_current()
            current_active = [next_active]

        close_current()
        return blocks


    def apply_minimum_standalone_block_filter(
        self,
        blocks: list[G8Block],
    ) -> tuple[list[G8Block], dict[str, Any]]:
        ordered_blocks = sorted(
            blocks,
            key=lambda block: (block.start_seconds, block.end_seconds),
        )
        before_blocks = [block.to_dict() for block in ordered_blocks]
        before_budget = round(
            sum(block.keep_active_budget_seconds for block in ordered_blocks),
            3,
        )

        if self.min_standalone_block_seconds <= 0.0:
            return ordered_blocks, {
                "enabled": False,
                "min_standalone_block_seconds": self.min_standalone_block_seconds,
                "bridge_seconds": self.bridge_seconds,
                "before_block_count": len(before_blocks),
                "after_block_count": len(before_blocks),
                "before_available_keep_active_budget_seconds": before_budget,
                "after_available_keep_active_budget_seconds": before_budget,
                "budget_delta_seconds": 0.0,
                "discarded_count": 0,
                "expanded_count": 0,
                "kept_connected_micro_count": 0,
                "after_budget_below_720": before_budget < G8_MIN_PREFERRED_SECONDS,
                "before_blocks": before_blocks,
                "after_blocks": before_blocks,
                "actions": [],
            }

        kept_blocks: list[G8Block] = []
        actions: list[dict[str, Any]] = []

        for index, block in enumerate(ordered_blocks):
            is_micro = (
                block.keep_active_budget_seconds < self.min_standalone_block_seconds
            )
            isolated, previous_gap, next_gap = self._standalone_isolation_info(
                index,
                ordered_blocks,
            )

            if not is_micro:
                kept_blocks.append(block)
                continue

            if not isolated:
                kept_blocks.append(block)
                actions.append(
                    {
                        "block_id": block.block_id,
                        "action": "kept_connected_micro_block",
                        "reason": "micro_block_has_neighbor_within_bridge_distance",
                        "start_seconds": _round_seconds(block.start_seconds),
                        "end_seconds": _round_seconds(block.end_seconds),
                        "keep_active_budget_seconds": round(
                            block.keep_active_budget_seconds,
                            3,
                        ),
                        "min_standalone_block_seconds": round(
                            self.min_standalone_block_seconds,
                            3,
                        ),
                        "previous_gap_seconds": previous_gap,
                        "next_gap_seconds": next_gap,
                    }
                )
                continue

            before_micro_budget = block.keep_active_budget_seconds
            expanded = self._try_context_extend_micro_block(block)

            if expanded and block.keep_active_budget_seconds >= self.min_standalone_block_seconds:
                kept_blocks.append(block)
                actions.append(
                    {
                        "block_id": block.block_id,
                        "action": "expanded_isolated_micro_block",
                        "reason": "direct_adjacent_untrimmed_active_play_context_available",
                        "start_seconds": _round_seconds(block.start_seconds),
                        "end_seconds": _round_seconds(block.end_seconds),
                        "before_keep_active_budget_seconds": round(before_micro_budget, 3),
                        "after_keep_active_budget_seconds": round(
                            block.keep_active_budget_seconds,
                            3,
                        ),
                        "min_standalone_block_seconds": round(
                            self.min_standalone_block_seconds,
                            3,
                        ),
                        "previous_gap_seconds": previous_gap,
                        "next_gap_seconds": next_gap,
                    }
                )
                continue

            actions.append(
                {
                    "block_id": block.block_id,
                    "action": "discarded_isolated_micro_block",
                    "reason": "isolated_micro_block_below_minimum_without_adjacent_untrimmed_active_play_context",
                    "start_seconds": _round_seconds(block.start_seconds),
                    "end_seconds": _round_seconds(block.end_seconds),
                    "keep_active_budget_seconds": round(
                        block.keep_active_budget_seconds,
                        3,
                    ),
                    "quality_score": _clamp01(block.quality_score),
                    "quality_source": block.quality_source,
                    "quality_does_not_override_minimum_standalone_duration": True,
                    "min_standalone_block_seconds": round(
                        self.min_standalone_block_seconds,
                        3,
                    ),
                    "previous_gap_seconds": previous_gap,
                    "next_gap_seconds": next_gap,
                }
            )

        after_blocks = [block.to_dict() for block in kept_blocks]
        after_budget = round(
            sum(block.keep_active_budget_seconds for block in kept_blocks),
            3,
        )

        return kept_blocks, {
            "enabled": True,
            "min_standalone_block_seconds": round(
                self.min_standalone_block_seconds,
                3,
            ),
            "bridge_seconds": round(self.bridge_seconds, 3),
            "before_block_count": len(before_blocks),
            "after_block_count": len(after_blocks),
            "before_available_keep_active_budget_seconds": before_budget,
            "after_available_keep_active_budget_seconds": after_budget,
            "budget_delta_seconds": round(after_budget - before_budget, 3),
            "discarded_count": sum(
                1
                for action in actions
                if action.get("action") == "discarded_isolated_micro_block"
            ),
            "expanded_count": sum(
                1
                for action in actions
                if action.get("action") == "expanded_isolated_micro_block"
            ),
            "kept_connected_micro_count": sum(
                1
                for action in actions
                if action.get("action") == "kept_connected_micro_block"
            ),
            "after_budget_below_720": after_budget < G8_MIN_PREFERRED_SECONDS,
            "before_blocks": before_blocks,
            "after_blocks": after_blocks,
            "actions": actions,
        }

    def _standalone_isolation_info(
        self,
        index: int,
        blocks: list[G8Block],
    ) -> tuple[bool, float | None, float | None]:
        block = blocks[index]
        previous_gap: float | None = None
        next_gap: float | None = None

        if index > 0:
            previous_gap = round(block.start_seconds - blocks[index - 1].end_seconds, 3)
        if index + 1 < len(blocks):
            next_gap = round(blocks[index + 1].start_seconds - block.end_seconds, 3)

        has_close_previous = (
            previous_gap is not None
            and previous_gap >= 0.0
            and previous_gap <= self.bridge_seconds
        )
        has_close_next = (
            next_gap is not None
            and next_gap >= 0.0
            and next_gap <= self.bridge_seconds
        )
        return (not has_close_previous and not has_close_next), previous_gap, next_gap

    def _try_context_extend_micro_block(self, block: G8Block) -> bool:
        """Only extends from active_play already present in the block and not covered by G7a trim."""
        candidate_active_ranges = _merge_ranges(
            (span.start_seconds, span.end_seconds)
            for span in block.source_spans
            if span.is_active
        )
        candidate_keep_ranges = _subtract_ranges(
            candidate_active_ranges,
            block.trim_ranges,
        )
        candidate_budget = round(
            sum(end - start for start, end in candidate_keep_ranges),
            3,
        )

        if candidate_budget <= block.keep_active_budget_seconds:
            return False
        if candidate_budget < self.min_standalone_block_seconds:
            return False

        block.active_ranges = candidate_active_ranges
        block.keep_ranges = candidate_keep_ranges
        block.keep_active_budget_seconds = candidate_budget
        if candidate_keep_ranges:
            block.start_seconds = candidate_keep_ranges[0][0]
            block.end_seconds = candidate_keep_ranges[-1][1]
        return True


    def audit_active_play_gaps(
        self,
        *,
        selected_blocks: list[G8Block],
        timeline_segments: list[G8TimelinePlanSegment],
        trim_spans: list[G8SourceSpan],
    ) -> list[G8AntiOvercutIssue]:
        issues: list[G8AntiOvercutIssue] = []
        trim_ranges = [(span.start_seconds, span.end_seconds) for span in trim_spans]

        for block in selected_blocks:
            kept_for_block = [
                (segment.start_seconds, segment.end_seconds)
                for segment in timeline_segments
                if segment.block_id == block.block_id
            ]
            gaps = _complement_ranges(block.start_seconds, block.end_seconds, kept_for_block)
            for gap_start, gap_end in gaps:
                active_overlap = _covered_seconds_by_ranges(gap_start, gap_end, block.active_ranges)
                if active_overlap <= ANTI_OVERCUT_TOLERANCE_SECONDS:
                    continue
                trim_covered = _covered_seconds_by_ranges(gap_start, gap_end, trim_ranges)
                uncovered = round(max(0.0, active_overlap - trim_covered), 3)
                if uncovered > ANTI_OVERCUT_TOLERANCE_SECONDS:
                    issues.append(
                        G8AntiOvercutIssue(
                            block_id=block.block_id,
                            gap_start_seconds=gap_start,
                            gap_end_seconds=gap_end,
                            active_overlap_seconds=active_overlap,
                            trim_covered_seconds=trim_covered,
                            uncovered_active_seconds=uncovered,
                            reason="timeline_gap_removes_active_play_without_full_g7a_trim_coverage",
                        )
                    )
        return issues

    def _trim_ranges_for_block(
        self,
        block: G8Block,
        trim_spans: list[G8SourceSpan],
    ) -> list[tuple[float, float]]:
        ranges: list[tuple[float, float]] = []
        for trim in trim_spans:
            for active_start, active_end in block.active_ranges:
                start = max(active_start, trim.start_seconds)
                end = min(active_end, trim.end_seconds)
                if end > start:
                    ranges.append((start, end))
        return _merge_ranges(ranges)

    def _score_block(
        self,
        block: G8Block,
        highlights: list[G8SourceSpan],
    ) -> tuple[float, str]:
        weighted_score = 0.0
        weighted_seconds = 0.0
        for highlight in highlights:
            overlap = _overlap_seconds(
                block.start_seconds,
                block.end_seconds,
                highlight.start_seconds,
                highlight.end_seconds,
            )
            if overlap <= 0:
                continue
            weighted_score += highlight.confidence * overlap
            weighted_seconds += overlap

        if weighted_seconds > 0:
            return _clamp01(weighted_score / weighted_seconds), "highlight_quality_overlap"

        active_spans = [span for span in block.source_spans if span.is_active]
        if not active_spans:
            return 0.0, "no_active_spans"
        confidence_score = sum(span.confidence for span in active_spans) / len(active_spans)
        intensity_bonus = 0.0
        for span in active_spans:
            if span.intensity == "high":
                intensity_bonus += 0.10
            elif span.intensity == "medium":
                intensity_bonus += 0.05
        intensity_bonus = intensity_bonus / max(1, len(active_spans))
        return _clamp01(confidence_score + intensity_bonus), "g6_confidence_intensity_fallback"

    def _select_blocks(
        self,
        ranked_blocks: list[G8Block],
        available_budget: float,
    ) -> tuple[list[G8Block], float, str, list[str]]:
        notes: list[str] = []
        if available_budget <= 0.0:
            return [], 0.0, "no_keep_active_budget", ["No active_play budget available."]

        if available_budget < G8_MIN_PREFERRED_SECONDS:
            notes.append("available_keep_active_budget_below_720_target_equals_budget")
            return list(ranked_blocks), available_budget, "below_720_not_enough_content", notes

        if available_budget <= G8_MAX_SECONDS:
            notes.append("available_keep_active_budget_between_720_and_1200_select_all")
            return list(ranked_blocks), available_budget, "select_all_available_budget", notes

        selected: list[G8Block] = []
        selected_budget = 0.0
        target = G8_PREFERRED_TARGET_SECONDS

        for block in ranked_blocks:
            next_budget = selected_budget + block.keep_active_budget_seconds
            if selected_budget >= target:
                break
            if next_budget <= G8_MAX_SECONDS:
                selected.append(block)
                selected_budget = next_budget
                continue
            if selected_budget < G8_MIN_PREFERRED_SECONDS:
                selected.append(block)
                selected_budget = next_budget
                notes.append("single_or_required_block_pushes_over_1200_manual_review")
            break

        if not selected:
            selected = [ranked_blocks[0]]
            selected_budget = selected[0].keep_active_budget_seconds
            notes.append("fallback_selected_best_block")

        notes.append("performance_eco_power_profile_does_not_cap_editorial_longform_duration")
        return selected, min(G8_MAX_SECONDS, max(G8_MIN_PREFERRED_SECONDS, selected_budget)), "selected_best_blocks_900_to_1200", notes

    def _timeline_segments_from_blocks(
        self,
        selected_blocks: list[G8Block],
    ) -> list[G8TimelinePlanSegment]:
        timeline_segments: list[G8TimelinePlanSegment] = []
        for block in selected_blocks:
            for start, end in block.keep_ranges:
                if end <= start:
                    continue
                timeline_segments.append(
                    G8TimelinePlanSegment(
                        segment_id=f"g8_seg_{len(timeline_segments) + 1:04d}",
                        block_id=block.block_id,
                        start_seconds=_round_seconds(start),
                        end_seconds=_round_seconds(end),
                        state=ACTIVE_STATE,
                        keep_decision="keep_active",
                    )
                )
        return sorted(timeline_segments, key=lambda segment: (segment.start_seconds, segment.end_seconds))

