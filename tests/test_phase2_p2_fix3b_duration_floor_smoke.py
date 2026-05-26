from __future__ import annotations

from types import SimpleNamespace

import pytest

from core.longform_timeline_builder import LongformTimelineBuilder, YOUTUBE_MIN_DURATION
from core.power_profile import PowerProfile
from models.analysis_result import AnalysisResult
from models.highlight_candidate import HighlightCandidate
from models.job import Job
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)
from shared.errors import ValidationError


def _duration(items: list[dict]) -> float:
    return sum(
        max(0.0, item["candidate"].end_time - item["candidate"].start_time)
        for item in items
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


def _job() -> Job:
    return Job(
        job_id="job_p2_fix3b_duration_floor",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.LONGFORM,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="inbox/gaming_main/sample.mp4",
    )


def _analysis(duration: float = 900.0) -> AnalysisResult:
    return AnalysisResult(
        job_id="job_p2_fix3b_duration_floor",
        duration_seconds=duration,
        file_size_bytes=123456789,
        usable_for_shorts=True,
        usable_for_longform=True,
        analysis_confidence=0.9,
        notes=["p2-fix-3b duration floor smoke"],
    )


def _candidate(candidate_id: str, start: float, end: float, score: float = 0.86) -> HighlightCandidate:
    return HighlightCandidate(
        candidate_id=candidate_id,
        job_id="job_p2_fix3b_duration_floor",
        start_time=start,
        end_time=end,
        highlight_score=score,
        candidate_kind="action_peak",
        confidence=0.86,
        signal_tags=["duration_floor_test"],
        source="test",
        notes=["synthetic duration floor candidate"],
    )


def test_floor_keeps_selecting_primary_candidates_until_480s() -> None:
    builder = LongformTimelineBuilder()
    primary = [
        _item(f"primary_{index}", index * 50.0, index * 50.0 + 45.0, 0.82)
        for index in range(12)
    ]

    selected = builder._dedupe_and_select(
        primary,
        target_duration=YOUTUBE_MIN_DURATION,
        max_segments=100,
        duration_floor=YOUTUBE_MIN_DURATION,
    )

    assert _duration(selected) >= YOUTUBE_MIN_DURATION


def test_floor_uses_reserve_candidates_when_primary_pool_is_short() -> None:
    builder = LongformTimelineBuilder()
    primary = [
        _item(f"primary_{index}", index * 70.0, index * 70.0 + 60.0, 0.72)
        for index in range(4)
    ]
    reserve = [
        _item(
            f"reserve_{index}",
            400.0 + index * 70.0,
            400.0 + index * 70.0 + 60.0,
            0.38,
            ["duration_floor_reserve"],
        )
        for index in range(5)
    ]

    selected = builder._dedupe_and_select(
        primary,
        target_duration=YOUTUBE_MIN_DURATION,
        max_segments=100,
        reserve_candidates=reserve,
        duration_floor=YOUTUBE_MIN_DURATION,
    )

    assert _duration(selected) >= YOUTUBE_MIN_DURATION
    assert any("duration_floor_reserve" in item["notes"] for item in selected)


def test_build_raises_validation_error_when_480s_floor_unreachable() -> None:
    builder = LongformTimelineBuilder()
    candidates = [
        _candidate(f"too_short_{index}", index * 80.0, index * 80.0 + 60.0)
        for index in range(4)
    ]

    with pytest.raises(ValidationError, match="Longform floor 480s unreachable"):
        builder.build(
            job=_job(),
            analysis_result=_analysis(900.0),
            highlight_candidates=candidates,
            weak_zones=[],
        )


def test_upper_cap_stays_at_or_below_1200s() -> None:
    builder = LongformTimelineBuilder()
    scored = [
        _item(f"long_{index}", index * 11.0, index * 11.0 + 10.0, 0.92)
        for index in range(400)
    ]

    target = builder._build_target_duration(3600.0, scored)
    selected = builder._dedupe_and_select(
        scored,
        target_duration=target,
        max_segments=100,
        duration_floor=YOUTUBE_MIN_DURATION,
    )

    assert target <= 1200.0
    assert _duration(selected) <= 1200.0


def test_performance_power_profile_caps_longform_target_to_720s() -> None:
    builder = LongformTimelineBuilder()
    job = SimpleNamespace(power_profile=PowerProfile.PERFORMANCE)

    capped = builder._apply_power_profile_target_duration_cap(
        job,
        target_duration=1200.0,
        source_duration_seconds=1476.0,
    )

    assert capped == 720.0


def test_eco_power_profile_caps_longform_target_to_540s() -> None:
    builder = LongformTimelineBuilder()
    job = SimpleNamespace(power_profile=PowerProfile.ECO)

    capped = builder._apply_power_profile_target_duration_cap(
        job,
        target_duration=1200.0,
        source_duration_seconds=1476.0,
    )

    assert capped == 540.0


def test_balanced_power_profile_keeps_longform_target_uncapped() -> None:
    builder = LongformTimelineBuilder()
    job = SimpleNamespace(power_profile=PowerProfile.BALANCED)

    capped = builder._apply_power_profile_target_duration_cap(
        job,
        target_duration=1200.0,
        source_duration_seconds=1476.0,
    )

    assert capped == 1200.0
