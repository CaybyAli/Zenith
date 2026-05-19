from __future__ import annotations

from types import SimpleNamespace

from core.longform_timeline_builder import (
    LONGFORM_PRIMARY_SCORE_FLOOR,
    LongformTimelineBuilder,
    YOUTUBE_MIN_DURATION,
)
from models.highlight_candidate import HighlightCandidate


def _candidate(candidate_id: str, start: float, end: float, score: float = 0.70) -> HighlightCandidate:
    return HighlightCandidate(
        candidate_id=candidate_id,
        job_id="job_p2_fix3d",
        start_time=start,
        end_time=end,
        highlight_score=score,
        candidate_kind="action_peak",
        confidence=0.80,
        signal_tags=["mid_zone"],
        source="test",
        notes=["synthetic"],
    )


def _weak(candidate_id: str, start: float, end: float) -> HighlightCandidate:
    return HighlightCandidate(
        candidate_id=candidate_id,
        job_id="job_p2_fix3d",
        start_time=start,
        end_time=end,
        highlight_score=0.80,
        candidate_kind="drop_zone",
        confidence=0.80,
        signal_tags=["mid_zone"],
        source="test",
        notes=["weak"],
    )


def _item(candidate_id: str, start: float, end: float, score: float, notes: list[str] | None = None) -> dict:
    return {
        "candidate": SimpleNamespace(
            candidate_id=candidate_id,
            start_time=start,
            end_time=end,
        ),
        "selection_score": score,
        "notes": list(notes or []),
    }


def _duration(items: list[dict]) -> float:
    return sum(
        max(0.0, item["candidate"].end_time - item["candidate"].start_time)
        for item in items
    )


def test_heavy_weak_penalty_lowers_score_but_does_not_zero_it() -> None:
    builder = LongformTimelineBuilder()
    candidate = _candidate("heavy_score", 100.0, 114.0)
    weak_zone = _weak("weak_full", 100.0, 114.0)

    clean_score, clean_notes = builder._score_candidate_for_longform(candidate, [])
    penalized_score, penalized_notes = builder._score_candidate_for_longform(candidate, [weak_zone])

    assert "heavy_weak_zone_penalty" in penalized_notes
    assert "heavy_weak_zone_penalty" not in clean_notes
    assert 0.0 < penalized_score < clean_score
    assert round(clean_score - penalized_score, 2) == 0.40
    assert penalized_score < LONGFORM_PRIMARY_SCORE_FLOOR


def test_heavy_weak_penalty_note_is_not_a_dedupe_killswitch() -> None:
    builder = LongformTimelineBuilder()
    item = _item(
        "heavy_but_usable",
        0.0,
        60.0,
        0.32,
        ["heavy_weak_zone_penalty"],
    )

    selected = builder._dedupe_and_select(
        [item],
        target_duration=60.0,
        max_segments=12,
    )

    assert len(selected) == 1
    assert selected[0]["candidate"].candidate_id == "heavy_but_usable"
    assert _duration(selected) == 60.0


def test_heavy_penalized_reserve_candidates_can_reach_480s_floor() -> None:
    builder = LongformTimelineBuilder()

    primary_candidates = [
        _candidate(f"primary_{index}", index * 90.0, index * 90.0 + 80.0)
        for index in range(4)
    ]

    heavy_candidates = [
        _candidate(
            f"heavy_reserve_{index}",
            400.0 + index * 90.0,
            400.0 + index * 90.0 + 80.0,
        )
        for index in range(3)
    ]
    weak_zones = [
        _weak(
            f"weak_{index}",
            400.0 + index * 90.0,
            400.0 + index * 90.0 + 80.0,
        )
        for index in range(3)
    ]

    primary_items: list[dict] = []
    reserve_items: list[dict] = []

    for candidate in primary_candidates + heavy_candidates:
        score, notes = builder._score_candidate_for_longform(candidate, weak_zones)
        item = {
            "candidate": candidate,
            "selection_score": score,
            "notes": list(notes),
        }
        if score < LONGFORM_PRIMARY_SCORE_FLOOR:
            item["notes"].append("duration_floor_reserve")
            reserve_items.append(item)
        else:
            primary_items.append(item)

    assert len(primary_items) == 4
    assert len(reserve_items) == 3
    assert _duration(primary_items) < YOUTUBE_MIN_DURATION

    selected = builder._dedupe_and_select(
        primary_items,
        target_duration=YOUTUBE_MIN_DURATION,
        max_segments=100,
        reserve_candidates=reserve_items,
        duration_floor=YOUTUBE_MIN_DURATION,
    )

    assert _duration(selected) >= YOUTUBE_MIN_DURATION
    assert any("heavy_weak_zone_penalty" in item["notes"] for item in selected)


def test_overlap_and_minimum_duration_protection_still_work() -> None:
    builder = LongformTimelineBuilder()

    overlapping = [
        _item("first", 0.0, 20.0, 0.90),
        _item("overlap", 2.0, 18.0, 0.80),
    ]

    selected_overlap = builder._dedupe_and_select(
        overlapping,
        target_duration=40.0,
        max_segments=12,
    )

    assert len(selected_overlap) == 1
    assert selected_overlap[0]["candidate"].candidate_id == "first"

    too_short = [
        _item("too_short", 100.0, 102.5, 0.95),
    ]

    selected_short = builder._dedupe_and_select(
        too_short,
        target_duration=10.0,
        max_segments=12,
    )

    assert selected_short == []
