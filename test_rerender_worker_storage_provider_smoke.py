from pathlib import Path
import shutil

import rerender_worker
from core.runtime_mode_controller import RuntimeModeController
from core.vacation_controller import VacationController
from storage.local_storage_provider import LocalStorageProvider


def main() -> None:
    provider = LocalStorageProvider()

    base_dir = Path("tmp/rerender_worker_storage_test")
    queue_file = base_dir / "rerender_queue.json"
    rerender_jobs_file = base_dir / "rerender_jobs.json"
    runtime_state_file = base_dir / "runtime_mode_test.json"
    vacation_state_file = base_dir / "vacation_state_test.json"

    original_runtime_controller = rerender_worker.runtime_mode_controller
    original_vacation_controller = rerender_worker.vacation_controller

    if base_dir.exists():
        shutil.rmtree(base_dir)

    base_dir.mkdir(parents=True, exist_ok=True)

    try:
        rerender_worker.runtime_mode_controller = RuntimeModeController(
            state_path=str(runtime_state_file)
        )
        rerender_worker.runtime_mode_controller.set_mode("full_power")

        rerender_worker.vacation_controller = VacationController(
            state_path=str(vacation_state_file)
        )
        rerender_worker.vacation_controller.set_enabled(False)

        provider.write_json(
            str(queue_file),
            [
                {
                    "job_id": "job_rerender_storage_smoke_001",
                    "channel_type": "gaming_main",
                    "video_path": "exports/gaming_main/job_rerender_storage_smoke_001/video.mp4",
                    "title": "Rerender Storage Test",
                    "description": "Rerender worker storage abstraction smoke test",
                }
            ],
            indent=4,
        )

        rerender_worker.create_rerender_job_from_queue(
            queue_file=str(queue_file),
            rerender_jobs_file=str(rerender_jobs_file),
            provider=provider,
        )

        queue_after = provider.read_json(str(queue_file))
        rerender_jobs = provider.read_json(str(rerender_jobs_file))

        assert len(queue_after) == 0
        assert len(rerender_jobs) == 1
        assert rerender_jobs[0]["source_job_id"] == "job_rerender_storage_smoke_001"
        assert rerender_jobs[0]["status"] == "pending"

        print("RERENDER WORKER STORAGE PROVIDER SMOKE TEST PASSED")
        print({"queue_after": len(queue_after), "rerender_jobs": len(rerender_jobs)})

    finally:
        rerender_worker.runtime_mode_controller = original_runtime_controller
        rerender_worker.vacation_controller = original_vacation_controller

        if base_dir.exists():
            shutil.rmtree(base_dir)


if __name__ == "__main__":
    main()