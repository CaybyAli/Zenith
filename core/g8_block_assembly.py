
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping


YOUTUBE_MIN_DURATION_SECONDS = 480.0
G8_MIN_PREFERRED_SECONDS = 720.0
G8_PREFERRED_TARGET_SECONDS = 900.0
G8_MAX_SECONDS = 1200.0
DEFAULT_BRIDGE_SECONDS = 8.0
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
            "blocks": [block.to_dict() for block in self.blocks],
            "selected_blocks": [block.to_dict() for block in self.selected_blocks],
            "timeline_segments": [segment.to_dict() for segment in self.timeline_segments],
            "notes": list(self.notes),
        }


class G8BlockAssemblyPlanner:
    """Builds a review-only longform timeline plan from G6 play segments plus optional G7a trims."""

    engine = "g8-block-assembly-planner-v1"

    def __init__(self, bridge_seconds: float = DEFAULT_BRIDGE_SECONDS) -> None:
        self.bridge_seconds = max(0.0, float(bridge_seconds))

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
        blocks: list[G8Block] = []
        current: list[G8SourceSpan] = []
        pending_bridge: list[G8SourceSpan] = []

        def bridge_ok(spans: list[G8SourceSpan]) -> bool:
            if not spans:
                return True
            if any(span.state not in BRIDGE_STATES for span in spans):
                return False
            return sum(span.duration_seconds for span in spans) <= self.bridge_seconds

        def close_current() -> None:
            nonlocal current
            if not current:
                return
            active_ranges = _merge_ranges(
                (span.start_seconds, span.end_seconds)
                for span in current
                if span.is_active
            )
            if not active_ranges:
                current = []
                return
            block_start = active_ranges[0][0]
            block_end = active_ranges[-1][1]
            source_spans = [
                span
                for span in current
                if span.end_seconds > block_start and span.start_seconds < block_end
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
                    keep_active_budget_seconds=round(sum(end - start for start, end in active_ranges), 3),
                    quality_score=0.0,
                    quality_source="unscored",
                )
            )
            current = []

        for segment in play_segments:
            if segment.is_active:
                if not current:
                    current = [segment]
                    pending_bridge = []
                    continue
                if pending_bridge:
                    if bridge_ok(pending_bridge):
                        current.extend(pending_bridge)
                    else:
                        close_current()
                        current = []
                    pending_bridge = []
                current.append(segment)
                continue

            if not current:
                continue

            pending_bridge.append(segment)
            if not bridge_ok(pending_bridge):
                close_current()
                pending_bridge = []

        close_current()
        return blocks

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

