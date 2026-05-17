from pathlib import Path
import shutil

import dashboard
from storage.local_storage_provider import LocalStorageProvider


def main() -> None:
    provider = LocalStorageProvider()

    job_id = "job_dashboard_mutation_smoke_001"
    exports_dir = Path("exports") / "gaming_main" / job_id
    jobs_file = Path("tmp/dashboard_storage_mutation_test/jobs.json")

    original_job_store_file = dashboard.JOB_STORE_FILE

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
                "publish_status": None,
                "title": "Dashboard Mutation Test",
                "description": "Dashboard mutation storage smoke test",
                "shorts": [
                    {
                        "short_id": "short_1",
                        "path": "exports/gaming_main/job_dashboard_mutation_smoke_001/short_1.mp4",
                        "status": "generated",
                        "review_status": "pending",
                        "platform_targets": ["youtube"],
                        "publish_status": "not_published",
                        "retry_count": 0,
                        "max_retry_attempts": None,
                        "retry_delay_minutes": None,
                        "next_retry_at": None,
                        "last_retry_at": None,
                        "last_retry_reason": None,
                        "retry_status": None,
                        "permanently_failed": False,
                        "segment": None,
                    },
                    {
                        "short_id": "short_2",
                        "path": "exports/gaming_main/job_dashboard_mutation_smoke_001/short_2.mp4",
                        "status": "generated",
                        "review_status": "approved",
                        "platform_targets": ["youtube"],
                        "publish_status": "not_published",
                        "retry_count": 0,
                        "max_retry_attempts": None,
                        "retry_delay_minutes": None,
                        "next_retry_at": None,
                        "last_retry_at": None,
                        "last_retry_reason": None,
                        "retry_status": None,
                        "permanently_failed": False,
                        "segment": None,
                    },
                ],
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

        dashboard.JOB_STORE_FILE = str(jobs_file)

        dashboard.update_job_status(job_id, "approved", provider=provider)
        after_approve = provider.read_json(str(exports_dir / "job.json"))
        assert after_approve["review_status"] == "approved"

        dashboard.update_single_short_review_status(job_id, "short_1", "approved", provider=provider)
        after_short_approve = provider.read_json(str(exports_dir / "job.json"))
        short_1 = next(item for item in after_short_approve["shorts"] if item["short_id"] == "short_1")
        assert short_1["review_status"] == "approved"

        dashboard.mark_selected_shorts_as_published(job_id, ["short_2"], provider=provider)
        after_short_publish = provider.read_json(str(exports_dir / "job.json"))
        short_2 = next(item for item in after_short_publish["shorts"] if item["short_id"] == "short_2")
        assert short_2["publish_status"] == "published"

        dashboard.schedule_short_retry_or_fail(job_id, "short_1", "test failure", provider=provider)
        after_retry = provider.read_json(str(exports_dir / "job.json"))
        short_1_retry = next(item for item in after_retry["shorts"] if item["short_id"] == "short_1")
        assert short_1_retry["retry_count"] == 1
        assert short_1_retry["retry_status"] == "scheduled_retry"

        dashboard.mark_job_as_published(job_id, provider=provider)
        after_publish = provider.read_json(str(exports_dir / "job.json"))
        assert after_publish["publish_status"] == "published"

        print("DASHBOARD STORAGE PROVIDER MUTATION SMOKE TEST PASSED")
        print({"job_id": job_id, "shorts_count": len(after_publish["shorts"])})

    finally:
        dashboard.JOB_STORE_FILE = original_job_store_file

        if exports_dir.exists():
            shutil.rmtree(exports_dir)

        if jobs_file.parent.exists():
            shutil.rmtree(jobs_file.parent)


if __name__ == "__main__":
    main()