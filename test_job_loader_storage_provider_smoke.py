from pathlib import Path
import shutil

from core.job_loader import JobLoader
from storage.local_storage_provider import LocalStorageProvider


def main() -> None:
    base_path = Path("exports/test_loader_storage")
    channel_path = base_path / "gaming_main"
    job_path = channel_path / "job_loader_storage_smoke_001"
    job_file = job_path / "job.json"

    if base_path.exists():
        shutil.rmtree(base_path)

    job_path.mkdir(parents=True, exist_ok=True)

    job_file.write_text(
        """
{
    "job_id": "job_loader_storage_smoke_001",
    "job_type": "gaming",
    "channel_type": "gaming_main",
    "target_format": "short",
    "target_platforms": ["youtube"],
    "status": "routed",
    "mode": "normal",
    "autopublish_class": "manual_only",
    "confidence_score": 0.0,
    "validator_status": "not_validated",
    "raw_video_path": "inbox/gaming_main/sample.mp4",
    "review_status": "pending",
    "is_scheduled": false,
    "retry_count": 0,
    "permanently_failed": false,
    "repost_requested": false,
    "repost_count": 0,
    "shorts": []
}
""".strip(),
        encoding="utf-8",
    )

    loader = JobLoader(storage_provider=LocalStorageProvider())
    jobs = loader.load_all_jobs(str(base_path))

    assert len(jobs) == 1
    assert jobs[0].job_id == "job_loader_storage_smoke_001"
    assert jobs[0].channel_type.value == "gaming_main"

    print("JOB LOADER STORAGE PROVIDER SMOKE TEST PASSED")
    print({"job_id": jobs[0].job_id, "loaded_count": len(jobs)})

    if base_path.exists():
        shutil.rmtree(base_path)


if __name__ == "__main__":
    main()