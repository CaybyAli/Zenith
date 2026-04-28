from pathlib import Path
import shutil

from core.job_repository import JobRepository
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


class DummyPublishPackage:
    def __init__(self) -> None:
        self.platform_targets = ["youtube"]
        self.title = "Storage Repo Test"
        self.description = "Repo storage abstraction smoke test"


def build_test_job() -> Job:
    return Job(
        job_id="job_repo_storage_smoke_001",
        job_type=JobType.GAMING,
        channel_type=ChannelType.GAMING_MAIN,
        target_format=TargetFormat.SHORT,
        target_platforms=["youtube"],
        status=JobStatus.ROUTED,
        mode=Mode.NORMAL,
        autopublish_class=AutopublishClass.MANUAL_ONLY,
        confidence_score=0.0,
        validator_status=ValidatorStatus.NOT_VALIDATED,
        raw_video_path="inbox/gaming_main/sample.mp4",
    )


def main() -> None:
    export_path = "exports/test_storage_repo/job_repo_storage_smoke_001"
    export_dir = Path(export_path)

    if export_dir.exists():
        shutil.rmtree(export_dir)

    repository = JobRepository(storage_provider=LocalStorageProvider())
    job = build_test_job()
    publish_package = DummyPublishPackage()

    repository.save_job(
        job=job,
        export_path=export_path,
        publish_package=publish_package,
        shorts_paths=[],
    )

    job_file = export_dir / "job.json"
    assert job_file.exists()

    content = job_file.read_text(encoding="utf-8")
    assert '"job_id": "job_repo_storage_smoke_001"' in content
    assert '"title": "Storage Repo Test"' in content
    assert '"description": "Repo storage abstraction smoke test"' in content

    print("JOB REPOSITORY STORAGE PROVIDER SMOKE TEST PASSED")
    print({"job_file": str(job_file)})

    if export_dir.exists():
        shutil.rmtree(export_dir)


if __name__ == "__main__":
    main()