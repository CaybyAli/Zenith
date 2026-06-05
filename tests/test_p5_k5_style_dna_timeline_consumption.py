from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.longform_timeline_builder import LongformTimelineBuilder
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


JOB_ID = "job_p5_k5_style_dna_timeline_consumption"


def _make_job() -> Job:
    return Job(
        job_id=JOB_ID,
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.LONGFORM,
        target_platforms=[],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.9,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="inbox/gaming_main/k5_style_dna_timeline.mp4",
    )


def _make_analysis() -> AnalysisResult:
    return AnalysisResult(
        job_id=JOB_ID,
        duration_seconds=120.0,
        file_size_bytes=123456,
        usable_for_shorts=True,
        usable_for_longform=True,
        analysis_confidence=0.9,
        notes=[],
    )


def _candidate(
    candidate_id: str,
    *,
    start: float,
    duration: float,
    highlight_score: float,
) -> HighlightCandidate:
    return HighlightCandidate(
        candidate_id=candidate_id,
        job_id=JOB_ID,
        start_time=start,
        end_time=start + duration,
        highlight_score=highlight_score,
        candidate_kind="unknown",
        confidence=0.5,
        signal_tags=[],
        source="k5_style_dna_timeline_test",
        notes=[],
    )


def _style_profile(target: float = 6.25) -> dict:
    return {
        "style_dna_pacing_decision": {
            "loaded": True,
            "target_clip_seconds": target,
            "pacing_profile": "fast",
            "confidence": 1.0,
        },
        "profile": {
            "duration_rules": {
                "KEEP": {"target": target},
                "REVIEW_KEEP": {"target": target},
                "REVIEW_TRIM": {"target": target},
                "UNKNOWN_REVIEW": {"target": target},
            }
        },
    }


def test_style_dna_target_changes_longform_candidate_score_order() -> None:
    builder = LongformTimelineBuilder()

    near_style_duration = _candidate(
        "near_style_duration",
        start=10.0,
        duration=6.25,
        highlight_score=0.60,
    )
    far_style_duration = _candidate(
        "far_style_duration",
        start=30.0,
        duration=18.0,
        highlight_score=0.63,
    )

    base_near_score, base_near_notes = builder._score_candidate_for_longform(
        near_style_duration,
        [],
    )
    base_far_score, base_far_notes = builder._score_candidate_for_longform(
        far_style_duration,
        [],
    )

    assert base_far_score > base_near_score
    assert "style_dna_timeline_influence_applied" not in base_near_notes
    assert "style_dna_timeline_influence_applied" not in base_far_notes

    target_clip_seconds = builder._extract_style_dna_target_clip_seconds(
        _style_profile(6.25)
    )

    style_near_score, style_near_notes = builder._score_candidate_for_longform(
        near_style_duration,
        [],
        style_dna_target_clip_seconds=target_clip_seconds,
    )
    style_far_score, style_far_notes = builder._score_candidate_for_longform(
        far_style_duration,
        [],
        style_dna_target_clip_seconds=target_clip_seconds,
    )

    assert style_near_score > style_far_score
    assert style_near_score > base_near_score
    assert style_far_score == base_far_score
    assert "style_dna_timeline_influence_applied" in style_near_notes
    assert any(
        note == "style_dna_target_clip_seconds=6.250"
        for note in style_near_notes
    )
    assert "style_dna_timeline_influence_applied" not in style_far_notes


def test_without_style_dna_keeps_longform_score_backward_compatible() -> None:
    builder = LongformTimelineBuilder()
    candidate = _candidate(
        "backward_compatible_candidate",
        start=10.0,
        duration=6.25,
        highlight_score=0.60,
    )

    default_score, default_notes = builder._score_candidate_for_longform(
        candidate,
        [],
    )
    explicit_none_score, explicit_none_notes = builder._score_candidate_for_longform(
        candidate,
        [],
        style_dna_target_clip_seconds=None,
    )

    assert explicit_none_score == default_score
    assert explicit_none_notes == default_notes
    assert "style_dna_timeline_influence_applied" not in explicit_none_notes


def test_style_dna_build_adds_timeline_metadata_without_render() -> None:
    builder = LongformTimelineBuilder()
    timeline = builder.build(
        job=_make_job(),
        analysis_result=_make_analysis(),
        highlight_candidates=[
            _candidate(
                "timeline_metadata_candidate",
                start=10.0,
                duration=6.25,
                highlight_score=0.60,
            )
        ],
        weak_zones=[],
        style_dna_pacing_profile=_style_profile(6.25),
    )

    assert timeline.selected_segments
    assert any(
        "style_dna_timeline_influence_applied" in segment.notes
        for segment in timeline.selected_segments
    )
    assert any(
        note.startswith("Style-DNA timeline influence: applied=True")
        for note in timeline.timeline_notes
    )
    assert any(
        "target_clip_seconds=6.250" in note
        for note in timeline.timeline_notes
    )


def test_gaming_pipeline_passes_style_dna_profile_to_longform_builder() -> None:
    pipeline_path = ROOT / "core" / "gaming_pipeline.py"
    text = pipeline_path.read_text(encoding="utf-8")

    assert "_clip_duration_report_for_timeline = getattr(job, \"clip_duration_report\", None)" in text
    assert "_style_dna_timeline_profile = _clip_duration_metadata_for_timeline" in text
    assert "style_dna_pacing_profile=_style_dna_timeline_profile" in text
