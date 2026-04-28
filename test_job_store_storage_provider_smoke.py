from pathlib import Path

from core.job_store import JobStore
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
from storage.local_storage_provider import LocalStorageProvider


def build_test_job() -> Job:
    return Job(
        job_id="job_storage_smoke_001",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube"],
        status=JobStatus.CREATED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="inbox/gaming_main/sample.mp4",
    )


def main() -> None:
    test_db_path = "data/test_jobs_storage_smoke.json"
    test_file = Path(test_db_path)

    if test_file.exists():
        test_file.unlink()

    store = JobStore(
        db_path=test_db_path,
        storage_provider=LocalStorageProvider(),
    )

    job = build_test_job()
    store.create_job(job)

    loaded_job = store.get_job(job.job_id)
    assert loaded_job.job_id == "job_storage_smoke_001"
    assert loaded_job.channel_type == ChannelType.GAMING_MAIN

    loaded_job.review_status = "approved"
    store.update_job(loaded_job)

    listed_jobs = store.list_jobs()
    assert len(listed_jobs) == 1
    assert listed_jobs[0].review_status == "approved"

    print("JOB STORE STORAGE PROVIDER SMOKE TEST PASSED")
    print({"job_id": listed_jobs[0].job_id, "review_status": listed_jobs[0].review_status})

    if test_file.exists():
        test_file.unlink()


if __name__ == "__main__":
    main()