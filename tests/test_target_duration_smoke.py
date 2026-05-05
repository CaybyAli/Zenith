from __future__ import annotations

from dataclasses import MISSING, fields, is_dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, get_args, get_origin, get_type_hints

from core.longform_timeline_builder import LongformTimelineBuilder
from models.analysis_result import AnalysisResult
from models.edit_timeline import EditTimeline
from models.highlight_candidate import HighlightCandidate
from models.job import Job
from models.timeline_segment import TimelineSegment


JOB_ID = "job_target_duration_smoke"
SOURCE_DURATION_SECONDS = 470.0


def _unwrap_type(annotation: Any) -> Any:
    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is None:
        return annotation

    if origin is list:
        return list

    if origin is dict:
        return dict

    non_none_args = [arg for arg in args if arg is not type(None)]
    if non_none_args:
        return _unwrap_type(non_none_args[0])

    return annotation


def _enum_value(enum_cls: type[Enum], field_name: str) -> Enum:
    field_lower = field_name.lower()

    preferred_terms = {
        "channel": ["gaming_main", "gaming"],
        "target": ["longform"],
        "format": ["longform"],
        "pipeline": ["gaming_pipeline", "gaming"],
        "job_type": ["gaming"],
        "type": ["gaming"],
        "mode": ["normal"],
        "status": ["pending", "new", "created"],
    }

    terms = []
    for key, values in preferred_terms.items():
        if key in field_lower:
            terms.extend(values)

    members = list(enum_cls)

    for term in terms:
        for member in members:
            if term in member.name.lower() or term in str(member.value).lower():
                return member

    return members[0]


def _default_required_value(field_name: str, annotation: Any) -> Any:
    clean_type = _unwrap_type(annotation)
    name = field_name.lower()

    if name == "job_id":
        return JOB_ID

    if name in {"duration_seconds", "duration"}:
        return SOURCE_DURATION_SECONDS

    if "path" in name:
        return "inbox/gaming_main/target_duration_smoke.mp4"

    if "file" in name and clean_type is str:
        return "target_duration_smoke.mp4"

    if "channel" in name and isinstance(clean_type, type) and issubclass(clean_type, Enum):
        return _enum_value(clean_type, field_name)

    if isinstance(clean_type, type) and issubclass(clean_type, Enum):
        return _enum_value(clean_type, field_name)

    if clean_type is str:
        return f"smoke_{field_name}"

    if clean_type is int:
        if "width" in name:
            return 1920
        if "height" in name:
            return 1080
        if "size" in name:
            return 123456
        return 1

    if clean_type is float:
        if "fps" in name:
            return 30.0
        if "score" in name or "confidence" in name:
            return 0.9
        return 1.0

    if clean_type is bool:
        return True

    if clean_type is list:
        return []

    if clean_type is dict:
        return {}

    if clean_type is Path:
        return Path("inbox/gaming_main/target_duration_smoke.mp4")

    if clean_type is datetime:
        return datetime.now(timezone.utc)

    return None


def _make_model(model_cls: type, **overrides: Any) -> Any:
    assert is_dataclass(model_cls), f"{model_cls.__name__} must be a dataclass"

    try:
        type_hints = get_type_hints(model_cls)
    except Exception:
        type_hints = {}

    kwargs = {}

    for item in fields(model_cls):
        if not item.init:
            continue

        if item.name in overrides:
            kwargs[item.name] = overrides[item.name]
            continue

        if item.default is not MISSING:
            continue

        if item.default_factory is not MISSING:  # type: ignore[attr-defined]
            continue

        annotation = type_hints.get(item.name, item.type)
        kwargs[item.name] = _default_required_value(item.name, annotation)

    return model_cls(**kwargs)


def _make_job() -> Job:
    return _make_model(Job, job_id=JOB_ID)


def _make_analysis_result(duration_seconds: float) -> AnalysisResult:
    return _make_model(
        AnalysisResult,
        job_id=JOB_ID,
        duration_seconds=duration_seconds,
    )


def _make_candidate(
    index: int,
    *,
    start_time: float,
    duration: float,
    highlight_score: float,
    confidence: float,
    candidate_kind: str,
    signal_tags: list[str] | None = None,
) -> HighlightCandidate:
    return HighlightCandidate(
        candidate_id=f"cand_{index:03d}",
        job_id=JOB_ID,
        start_time=round(start_time, 3),
        end_time=round(start_time + duration, 3),
        highlight_score=highlight_score,
        confidence=confidence,
        candidate_kind=candidate_kind,
        signal_tags=signal_tags or [],
        source="target_duration_smoke",
    )


def _make_high_quality_candidates(count: int = 40) -> list[HighlightCandidate]:
    candidates = []

    for index in range(count):
        candidates.append(
            _make_candidate(
                index,
                start_time=8.0 + (index * 11.0),
                duration=10.0,
                highlight_score=0.90,
                confidence=0.95,
                candidate_kind="action_peak",
                signal_tags=["intro_zone"] if index == 0 else [],
            )
        )

    return candidates


def _make_low_quality_sparse_candidates(count: int = 12) -> list[HighlightCandidate]:
    candidates = []

    for index in range(count):
        candidates.append(
            _make_candidate(
                index,
                start_time=8.0 + (index * 32.0),
                duration=10.0,
                highlight_score=0.55,
                confidence=0.35,
                candidate_kind="unknown",
                signal_tags=[],
            )
        )

    return candidates


def _assert_valid_timeline(timeline: EditTimeline, source_duration: float) -> None:
    assert isinstance(timeline, EditTimeline)
    assert timeline.selected_segments, "Timeline must contain selected_segments"
    assert timeline.target_duration > 0
    assert timeline.target_duration <= source_duration
    assert timeline.total_selected_duration > 0
    assert timeline.total_selected_duration <= timeline.target_duration + 15.0
    assert 0.0 <= timeline.timeline_score <= 1.0

    for segment in timeline.selected_segments:
        assert isinstance(segment, TimelineSegment)
        assert segment.start_time >= 0
        assert segment.end_time > segment.start_time
        assert segment.duration > 0
        assert 0.0 <= segment.selection_score <= 1.0


def _score_candidates(
    builder: LongformTimelineBuilder,
    candidates: list[HighlightCandidate],
) -> list[dict]:
    scored = []

    for candidate in candidates:
        selection_score, notes = builder._score_candidate_for_longform(candidate, [])
        if selection_score >= 0.45:
            scored.append(
                {
                    "candidate": candidate,
                    "selection_score": selection_score,
                    "notes": notes,
                }
            )

    assert scored, "Scored candidates must not be empty"
    return scored


def main() -> None:
    builder = LongformTimelineBuilder()
    job = _make_job()
    analysis_result = _make_analysis_result(SOURCE_DURATION_SECONDS)

    high_quality_timeline = builder.build(
        job=job,
        analysis_result=analysis_result,
        highlight_candidates=_make_high_quality_candidates(),
    )

    low_quality_timeline = builder.build(
        job=job,
        analysis_result=analysis_result,
        highlight_candidates=_make_low_quality_sparse_candidates(),
    )

    _assert_valid_timeline(high_quality_timeline, SOURCE_DURATION_SECONDS)
    _assert_valid_timeline(low_quality_timeline, SOURCE_DURATION_SECONDS)

    assert high_quality_timeline.target_duration == round(SOURCE_DURATION_SECONDS * 0.92, 3)
    assert low_quality_timeline.target_duration == round(SOURCE_DURATION_SECONDS * 0.40, 3)

    assert high_quality_timeline.target_duration > low_quality_timeline.target_duration
    assert len(high_quality_timeline.selected_segments) > len(low_quality_timeline.selected_segments)
    assert high_quality_timeline.total_selected_duration > low_quality_timeline.total_selected_duration

    short_target_items = builder._dedupe_and_select(
        _score_candidates(builder, _make_high_quality_candidates()),
        target_duration=80.0,
        max_segments=12,
    )

    long_target_items = builder._dedupe_and_select(
        _score_candidates(builder, _make_high_quality_candidates()),
        target_duration=220.0,
        max_segments=22,
    )

    short_selected_duration = sum(
        item["candidate"].end_time - item["candidate"].start_time
        for item in short_target_items
    )
    long_selected_duration = sum(
        item["candidate"].end_time - item["candidate"].start_time
        for item in long_target_items
    )

    assert len(short_target_items) < len(long_target_items)
    assert short_selected_duration < long_selected_duration
    assert short_selected_duration <= 95.0
    assert long_selected_duration >= 200.0

    youtube_min_analysis = _make_analysis_result(900.0)
    youtube_min_timeline = builder.build(
        job=job,
        analysis_result=youtube_min_analysis,
        highlight_candidates=_make_low_quality_sparse_candidates(count=12),
    )

    _assert_valid_timeline(youtube_min_timeline, 900.0)
    assert youtube_min_timeline.target_duration == 480.0

    print("TARGET DURATION SMOKE TEST PASSED")


if __name__ == "__main__":
    main()
