from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.pre_action_context_guard import PreActionContextGuard
from models.cut_indicator import CutIndicator, CutIndicatorResult
from models.highlight_candidate import HighlightCandidate
from models.timeline_segment import TimelineSegment


def _segment() -> TimelineSegment:
    return TimelineSegment(
        segment_id="seg_backfill",
        job_id="job_action_context_backfill_smoke",
        candidate_id="cand_backfill",
        start_time=10.5,
        end_time=16.0,
        segment_role="peak",
        selection_score=0.9,
    )


def _action_indicator() -> CutIndicator:
    return CutIndicator(
        indicator_id="ind_action_10_5",
        indicator_type="high_action_burst",
        start_seconds=10.5,
        end_seconds=11.5,
        score=0.9,
        confidence=0.85,
        source="action_context_backfill_smoke",
        reason="synthetic action",
        polarity="positive",
        channel_scope="all",
    )


def _silence_zone() -> HighlightCandidate:
    return HighlightCandidate(
        candidate_id="weak_silence_7_8",
        job_id="job_action_context_backfill_smoke",
        start_time=7.0,
        end_time=8.0,
        highlight_score=0.8,
        candidate_kind="drop_zone",
        confidence=0.8,
        signal_tags=["silence_zone"],
        source="highlight_selector.weak_zones",
        notes=["silence_zone_detected"],
    )


def test_action_context_backfill_smoke() -> None:
    result, summary = PreActionContextGuard().apply(
        [_segment()],
        cut_indicator_result=CutIndicatorResult(indicators=[_action_indicator()]),
        weak_zones=[_silence_zone()],
    )

    assert len(result) == 1
    assert 8.1 <= result[0].start_time <= 8.5
    assert summary.smart_backfilled == 1
    assert summary.silence_stop == 1
    print("ACTION CONTEXT BACKFILL SMOKE TEST PASSED")


if __name__ == "__main__":
    test_action_context_backfill_smoke()
