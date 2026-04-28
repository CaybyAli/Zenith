from pathlib import Path
import shutil

from core.maintenance_runner import MaintenanceRunner
from storage.local_storage_provider import LocalStorageProvider


def main() -> None:
    provider = LocalStorageProvider()

    base_dir = Path("tmp/maintenance_runner_test")
    exports_dir = base_dir / "exports" / "gaming_main"
    rerender_queue_file = base_dir / "rerender_queue.json"
    rerender_jobs_file = base_dir / "rerender_jobs.json"
    report_output_file = base_dir / "maintenance" / "latest_maintenance_report.json"

    if base_dir.exists():
        shutil.rmtree(base_dir)

    (exports_dir / "job_old_published_001").mkdir(parents=True, exist_ok=True)
    (exports_dir / "job_orphan_001").mkdir(parents=True, exist_ok=True)

    try:
        (exports_dir / "job_old_published_001" / "video.mp4").write_text("video", encoding="utf-8")
        provider.write_json(
            str(exports_dir / "job_old_published_001" / "job.json"),
            {
                "job_id": "job_old_published_001",
                "video_path": str(exports_dir / "job_old_published_001" / "video.mp4"),
                "thumbnail_path": None,
                "publish_status": "published",
                "published_at": "2026-03-01T10:00:00+00:00",
                "permanently_failed": False,
                "review_status": "approved",
                "is_rerender": False,
                "updated_at": "2026-03-01T10:00:00+00:00",
                "created_at": "2026-03-01T09:00:00+00:00",
                "shorts": [],
            },
            indent=4,
        )

        (exports_dir / "job_orphan_001" / "video.mp4").write_text("orphan", encoding="utf-8")

        provider.write_json(
            str(rerender_queue_file),
            [
                {
                    "job_id": "job_dup_001",
                    "channel_type": "gaming_main",
                    "video_path": "a.mp4",
                    "title": "A",
                    "description": "A",
                },
                "invalid-entry",
                {
                    "job_id": "job_dup_001",
                    "channel_type": "gaming_main",
                    "video_path": "b.mp4",
                    "title": "B",
                    "description": "B",
                },
            ],
            indent=4,
        )

        provider.write_json(
            str(rerender_jobs_file),
            [
                {
                    "rerender_job_id": "rer_valid_001",
                    "source_job_id": "job_source_001",
                    "status": "done",
                    "last_retry_at": "2026-04-01T10:00:00+00:00",
                },
                "invalid-rerender-entry",
                {
                    "rerender_job_id": "rer_processing_001",
                    "source_job_id": "job_source_002",
                    "status": "processing",
                    "last_retry_at": "2026-04-13T10:00:00+00:00",
                },
            ],
            indent=4,
        )

        runner = MaintenanceRunner(storage_provider=provider)
        result = runner.run(
            exports_base_path=str(base_dir / "exports"),
            rerender_queue_file=str(rerender_queue_file),
            rerender_jobs_file=str(rerender_jobs_file),
            report_output_path=str(report_output_file),
        )

        queue_after = provider.read_json(str(rerender_queue_file))
        rerender_jobs_after = provider.read_json(str(rerender_jobs_file))
        saved_report = provider.read_json(str(report_output_file))
        result_dict = result.to_dict()

        assert len(queue_after) == 1
        assert queue_after[0]["job_id"] == "job_dup_001"

        assert len(rerender_jobs_after) == 2
        assert rerender_jobs_after[0]["rerender_job_id"] == "rer_valid_001"
        assert rerender_jobs_after[1]["rerender_job_id"] == "rer_processing_001"

        assert result.report_path == str(report_output_file)
        assert saved_report["safe_recovery_execution"]["stats"]["removed_invalid_rerender_queue_entries"] == 1
        assert saved_report["safe_recovery_execution"]["stats"]["removed_duplicate_rerender_queue_entries"] == 1
        assert saved_report["safe_recovery_execution"]["stats"]["removed_invalid_rerender_job_entries"] == 1

        pre_issue_codes = {
            item["issue_code"]
            for item in saved_report["pre_recovery_integrity"]["issues"]
        }
        post_issue_codes = {
            item["issue_code"]
            for item in saved_report["post_recovery_integrity"]["issues"]
        }
        retention_ids = {
            item["reference_id"]
            for item in saved_report["retention_plan"]["decisions"]
        }

        assert "orphan_export_folder" in pre_issue_codes
        assert "duplicate_rerender_queue_job" in pre_issue_codes
        assert "invalid_rerender_job_entry" in pre_issue_codes

        assert "orphan_export_folder" in post_issue_codes
        assert "processing_rerender_requires_review" in post_issue_codes
        assert "duplicate_rerender_queue_job" not in post_issue_codes
        assert "invalid_rerender_job_entry" not in post_issue_codes

        assert "job_old_published_001" in retention_ids
        assert "rer_valid_001" in retention_ids

        assert result_dict["execution_result"]["stats"]["removed_invalid_rerender_queue_entries"] == 1

        print("MAINTENANCE RUNNER SMOKE TEST PASSED")
        print(
            {
                "report_path": result.report_path,
                "pre_issues": len(saved_report["pre_recovery_integrity"]["issues"]),
                "post_issues": len(saved_report["post_recovery_integrity"]["issues"]),
                "retention_decisions": len(saved_report["retention_plan"]["decisions"]),
            }
        )

    finally:
        if base_dir.exists():
            shutil.rmtree(base_dir)


if __name__ == "__main__":
    main()