from pathlib import Path
import shutil

import dashboard
from storage.local_storage_provider import LocalStorageProvider


def main() -> None:
    provider = LocalStorageProvider()

    job_id = "job_dashboard_storage_smoke_001"
    exports_dir = Path("exports") / "gaming_main" / job_id
    jobs_file = Path("tmp/dashboard_storage_test/jobs.json")
    rerender_jobs_file = Path("tmp/dashboard_storage_test/rerender_jobs.json")

    original_job_store_file = dashboard.JOB_STORE_FILE
    original_rerender_jobs_file = dashboard.RERENDER_JOBS_FILE

    if exports_dir.exists():
        shutil.rmtree(exports_dir)

    if jobs_file.parent.exists():
        shutil.rmtree(jobs_file.parent)

    exports_dir.mkdir(parents=True, exist_ok=True)
    jobs_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        provider.write_json(
            str(exports_dir / "job.json"),
            {
                "job_id": job_id,
                "job_type": "gaming",
                "channel_type": "gaming_main",
                "target_format": "short",
                "target_platforms": ["youtube"],
                "status": "routed",
                "mode": "normal",
                "autopublish_class": "manual_only",
                "confidence_score": 0.0,
                "validator_status": "not_validated",
                "review_status": "pending",
                "is_scheduled": False,
                "retry_count": 0,
                "permanently_failed": False,
                "repost_requested": False,
                "repost_count": 0,
                "title": "Dashboard Storage Test",
                "description": "Dashboard storage abstraction smoke test",
                "shorts": [],
            },
            indent=4,
        )

        provider.write_json(
            str(jobs_file),
            {
                "jobs": {
                    job_id: {
                        "job_id": job_id,
                        "review_status": "pending",
                        "is_scheduled": False,
                    }
                }
            },
            indent=4,
        )

        provider.write_json(str(rerender_jobs_file), [], indent=4)

        dashboard.JOB_STORE_FILE = str(jobs_file)
        dashboard.RERENDER_JOBS_FILE = str(rerender_jobs_file)

        loaded_package = dashboard.load_publish_package(
            job_id,
            provider=provider,
        )
        assert loaded_package is not None
        assert loaded_package["job_id"] == job_id

        dashboard.update_job_store_fields(
            job_id,
            {"review_status": "approved"},
            provider=provider,
        )
        updated_store = provider.read_json(str(jobs_file))
        assert updated_store["jobs"][job_id]["review_status"] == "approved"

        dashboard.trigger_rerender(
            job_id,
            provider=provider,
        )
        rerendered_job = provider.read_json(str(exports_dir / "job.json"))
        assert rerendered_job["rerender_requested"] is True

        dashboard.trigger_repost(
            job_id,
            provider=provider,
        )
        reposted_job = provider.read_json(str(exports_dir / "job.json"))
        assert reposted_job["repost_requested"] is True
        assert reposted_job["repost_status"] == "requested"

        rerender_jobs = dashboard.load_rerender_jobs(provider=provider)
        assert isinstance(rerender_jobs, list)
        assert len(rerender_jobs) == 0

        print("DASHBOARD STORAGE PROVIDER SMOKE TEST PASSED")
        print({"job_id": loaded_package["job_id"], "rerender_jobs": len(rerender_jobs)})

    finally:
        dashboard.JOB_STORE_FILE = original_job_store_file
        dashboard.RERENDER_JOBS_FILE = original_rerender_jobs_file

        if exports_dir.exists():
            shutil.rmtree(exports_dir)

        if jobs_file.parent.exists():
            shutil.rmtree(jobs_file.parent)


if __name__ == "__main__":
    main()