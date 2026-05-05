from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from core.longform_timeline_builder import LongformTimelineBuilder
from models.analysis_result import AnalysisResult
from models.energy_curve_result import EnergyCurvePoint, EnergyCurveResult
from models.facecam_reaction_result import FacecamReactionResult, FacecamReactionWindow
from models.gameplay_vision_result import GameplayVisionResult, GameplayVisionWindow
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


JOB_ID = "job_analysis_scoring_integration_smoke"


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
        raw_video_path="inbox/gaming_main/analysis_scoring_smoke.mp4",
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


def _make_candidate() -> HighlightCandidate:
    return HighlightCandidate(
        candidate_id="cand_analysis_scoring",
        job_id=JOB_ID,
        start_time=10.0,
        end_time=20.0,
        highlight_score=0.58,
        candidate_kind="action_peak",
        confidence=0.72,
        signal_tags=[],
        source="smoke",
        notes=[],
    )


def _make_energy_result() -> EnergyCurveResult:
    point = EnergyCurvePoint(
        point_id="energy_peak",
        job_id=JOB_ID,
        start_seconds=12.0,
        end_seconds=18.0,
        energy_score=0.9,
        signal_count=3,
    )
    return EnergyCurveResult(
        curve_id="curve_smoke",
        job_id=JOB_ID,
        points=[point],
        peak_points=[point],
        average_energy=0.5,
        max_energy=0.9,
    )


def _make_vision_result() -> GameplayVisionResult:
    window = GameplayVisionWindow(
        start_seconds=11.0,
        end_seconds=19.0,
        motion_score=0.8,
        action_score=0.88,
        scene_change_score=0.4,
        label="action",
        reason="smoke action overlap",
    )
    return GameplayVisionResult(
        windows=[window],
        action_windows=[window],
        average_action_score=0.88,
        max_action_score=0.88,
    )


def _make_facecam_result() -> FacecamReactionResult:
    window = FacecamReactionWindow(
        start_seconds=12.0,
        end_seconds=18.0,
        reaction_score=0.86,
        motion_score=0.7,
        expression_change_score=0.8,
        label="reaction",
        reason="smoke reaction overlap",
    )
    return FacecamReactionResult(
        windows=[window],
        reaction_windows=[window],
        average_reaction_score=0.86,
        max_reaction_score=0.86,
    )


def test_analysis_scoring_integration_smoke() -> None:
    builder = LongformTimelineBuilder()
    candidate = _make_candidate()

    base_score, base_notes = builder._score_candidate_for_longform(candidate, [])
    energy_score, energy_notes = builder._score_candidate_for_longform(
        candidate,
        [],
        energy_curve_result=_make_energy_result(),
    )
    vision_score, vision_notes = builder._score_candidate_for_longform(
        candidate,
        [],
        gameplay_vision_result=_make_vision_result(),
    )
    facecam_score, facecam_notes = builder._score_candidate_for_longform(
        candidate,
        [],
        facecam_reaction_result=_make_facecam_result(),
    )
    combined_score, combined_notes = builder._score_candidate_for_longform(
        candidate,
        [],
        energy_curve_result=_make_energy_result(),
        gameplay_vision_result=_make_vision_result(),
        facecam_reaction_result=_make_facecam_result(),
    )

    assert 0.0 <= base_score <= 1.0
    assert base_score < energy_score < combined_score <= 1.0
    assert base_score < vision_score < combined_score <= 1.0
    assert base_score < facecam_score < combined_score <= 1.0
    assert "energy_boost" in energy_notes
    assert "vision_boost" in vision_notes
    assert "facecam_boost" in facecam_notes
    assert "multi_analysis_boost" in combined_notes

    timeline = builder.build(
        job=_make_job(),
        analysis_result=_make_analysis(),
        highlight_candidates=[_make_candidate()],
        weak_zones=[],
        energy_curve_result=_make_energy_result(),
        gameplay_vision_result=_make_vision_result(),
        facecam_reaction_result=_make_facecam_result(),
    )

    assert timeline.selected_segments
    segment = timeline.selected_segments[0]
    assert 0.0 <= segment.selection_score <= 1.0
    assert {"energy_boost", "vision_boost", "facecam_boost"}.issubset(segment.notes)
    assert any("Analysis boosts:" in note for note in timeline.timeline_notes)

    print(f"base_score={base_score}")
    print(f"energy_score={energy_score}")
    print(f"vision_score={vision_score}")
    print(f"facecam_score={facecam_score}")
    print(f"combined_score={combined_score}")
    print("ANALYSIS SCORING INTEGRATION SMOKE TEST PASSED")


if __name__ == "__main__":
    test_analysis_scoring_integration_smoke()
