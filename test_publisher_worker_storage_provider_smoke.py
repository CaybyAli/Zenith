from pathlib import Path
import shutil

import publisher_worker
from storage.local_storage_provider import LocalStorageProvider


def main() -> None:
    provider = LocalStorageProvider()

    base_path = Path("tmp/publisher_worker_storage_test/exports")
    queue_file = Path("tmp/publisher_worker_storage_test/rerender_queue.json")
    job_path = base_path / "gaming_main" / "job_publisher_storage_smoke_001"
    job_file = job_path / "job.json"

    if base_path.parent.exists():
        shutil.rmtree(base_path.parent)

    job_path.mkdir(parents=True, exist_ok=True)

    provider.write_json(
        str(job_file),
        {
            "job_id": "job_publisher_storage_smoke_001",
            "channel_type": "gaming_main",
            "video_path": "exports/gaming_main/job_publisher_storage_smoke_001/video.mp4",
            "title": "Publisher Storage Test",
            "description": "Publisher worker storage abstraction smoke test",
            "rerender_requested": True,
        },
        indent=4,
    )

    job_files = publisher_worker.load_all_job_files(
        base_path=str(base_path),
        provider=provider,
    )
    assert len(job_files) == 1

    job = publisher_worker.load_job_data(job_files[0], provider=provider)
    assert job["job_id"] == "job_publisher_storage_smoke_001"

    publisher_worker.mark_rerender_in_progress(job_files[0], provider=provider)
    updated_job = publisher_worker.load_job_data(job_files[0], provider=provider)
    assert updated_job["rerender_requested"] is False
    assert updated_job["rerender_in_progress"] is True

    publisher_worker.add_to_rerender_queue(
        updated_job,
        queue_file=str(queue_file),
        provider=provider,
    )

    queue = provider.read_json(str(queue_file))
    assert len(queue) == 1
    assert queue[0]["job_id"] == "job_publisher_storage_smoke_001"

    print("PUBLISHER WORKER STORAGE PROVIDER SMOKE TEST PASSED")
    print({"job_files_seen": len(job_files), "queue_items": len(queue)})

    if base_path.parent.exists():
        shutil.rmtree(base_path.parent)


if __name__ == "__main__":
    main()