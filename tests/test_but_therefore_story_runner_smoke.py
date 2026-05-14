from __future__ import annotations

from core.but_therefore_story_runner import (
    run_but_therefore_story_for_job,
    store_but_therefore_story_run_report_to_job,
)
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


def _job() -> Job:
    return Job(
        job_id="job_story_runner_smoke",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.LONGFORM,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        review_timeline_plan_items=[
            {
                "item_id": "but_1",
                "segment_id": "seg_but",
                "start_seconds": 0.0,
                "end_seconds": 3.0,
                "text": "Aber plötzlich clutch fail no way",
                "hook_score": 0.95,
            },
            {
                "item_id": "therefore_1",
                "segment_id": "seg_therefore",
                "start_seconds": 3.0,
                "end_seconds": 6.0,
                "text": "Deshalb danach jetzt ist die Folge klar",
            },
        ],
    )


def test_runner_writes_story_fields_to_job():
    job = _job()

    report = run_but_therefore_story_for_job(job)
    store_but_therefore_story_run_report_to_job(job, report)

    assert job.but_therefore_story_report
    assert job.but_therefore_story
    assert job.but_therefore_story_status in {
        "story_analysis_ready",
        "story_analysis_ready_with_warnings",
    }

    assert job.story_total_moments == 2
    assert job.story_but_count >= 1
    assert job.story_therefore_count >= 1
    assert job.story_moments
    assert job.story_transitions
    assert isinstance(job.story_suggestions, list)

    assert job.story_review_required is True
    assert job.story_can_apply_changes is False
    assert job.story_can_remove_and_moments is False
    assert job.story_can_reorder_timeline is False
    assert job.story_can_trim is False
    assert job.story_can_extend is False
    assert job.story_can_render is False


def test_job_from_dict_loads_story_fields_and_keeps_safety_false():
    job = _job()
    report = run_but_therefore_story_for_job(job)
    store_but_therefore_story_run_report_to_job(job, report)

    payload = job.to_dict()
    payload["story_can_apply_changes"] = True
    payload["story_can_remove_and_moments"] = True
    payload["story_can_reorder_timeline"] = True
    payload["story_can_trim"] = True
    payload["story_can_extend"] = True
    payload["story_can_render"] = True

    loaded = Job.from_dict(payload)

    assert loaded.but_therefore_story_report
    assert loaded.but_therefore_story_status == job.but_therefore_story_status
    assert loaded.story_total_moments == job.story_total_moments
    assert loaded.story_moments
    assert loaded.story_transitions

    assert loaded.story_can_apply_changes is False
    assert loaded.story_can_remove_and_moments is False
    assert loaded.story_can_reorder_timeline is False
    assert loaded.story_can_trim is False
    assert loaded.story_can_extend is False
    assert loaded.story_can_render is False
