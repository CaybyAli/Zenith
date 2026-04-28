from __future__ import annotations

from core.music_cue_engine import MusicCueEngine
from models.dynamic_edit_plan import DynamicEditPlan
from models.edit_timeline import EditTimeline
from models.job import Job
from models.reaction_moment import ReactionMoment
from models.timeline_segment import TimelineSegment
from shared.enums import (
    AutopublishClass,
    ChannelType,
    JobStatus,
    JobType,
    Mode,
    TargetFormat,
    ValidatorStatus,
)


def build_job() -> Job:
    return Job(
        job_id="job_music_cue_engine_smoke",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_UNCUT,
        target_format=TargetFormat.LONGFORM,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="inbox/gaming_uncut/sample.mp4",
    )


def main() -> None:
    job = build_job()

    segment_1 = TimelineSegment(
        segment_id="seg_001",
        job_id=job.job_id,
        candidate_id="cand_001",
        start_time=10.0,
        end_time=24.0,
        segment_role="hook",
        selection_score=0.90,
        notes=[],
        source="test",
    )
    segment_2 = TimelineSegment(
        segment_id="seg_002",
        job_id=job.job_id,
        candidate_id="cand_002",
        start_time=50.0,
        end_time=72.0,
        segment_role="peak",
        selection_score=0.93,
        notes=[],
        source="test",
    )

    timeline = EditTimeline(
        timeline_id="timeline_001",
        job_id=job.job_id,
        target_duration=420.0,
        selected_segments=[segment_1, segment_2],
        hook_segment_id=segment_1.segment_id,
        peak_segment_ids=[segment_2.segment_id],
        payoff_segment_id=segment_2.segment_id,
        timeline_score=0.89,
        timeline_notes=[],
    )

    dynamic_plan = DynamicEditPlan(
        plan_id="dynamic_001",
        job_id=job.job_id,
        timeline_id=timeline.timeline_id,
        reaction_moments=[
            ReactionMoment(
                moment_id="moment_001",
                job_id=job.job_id,
                timeline_id=timeline.timeline_id,
                segment_id="seg_001",
                start_time=11.0,
                end_time=13.0,
                reaction_kind="hook_reaction",
                intensity=0.88,
                confidence=0.84,
                notes=[],
            ),
            ReactionMoment(
                moment_id="moment_002",
                job_id=job.job_id,
                timeline_id=timeline.timeline_id,
                segment_id="seg_002",
                start_time=54.0,
                end_time=57.0,
                reaction_kind="peak_reaction",
                intensity=0.92,
                confidence=0.87,
                notes=[],
            ),
        ],
        zoom_instructions=[],
        pacing_hints=[
            {"segment_id": "seg_001", "hint_kind": "fast_open", "strength": 0.80, "notes": []},
            {"segment_id": "seg_002", "hint_kind": "impact_emphasis", "strength": 0.86, "notes": []},
        ],
        plan_score=0.89,
        plan_notes=[],
    )

    cues = MusicCueEngine().build_cues(
        job=job,
        timeline=timeline,
        dynamic_edit_plan=dynamic_plan,
    )

    assert len(cues) == 2
    assert cues[0].cue_kind == "intro_bed"
    assert cues[1].cue_kind == "peak_hit"
    assert all(cue.intensity >= 0.50 for cue in cues)

    print("MUSIC CUE ENGINE SMOKE TEST PASSED")
    print(
        {
            "audio_cues": len(cues),
            "cue_kinds": [cue.cue_kind for cue in cues],
            "intensities": [cue.intensity for cue in cues],
        }
    )


if __name__ == "__main__":
    main()