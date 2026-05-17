from pathlib import Path
import shutil

from core.integrity_scanner import IntegrityScanResult
from core.recovery_executor import RecoveryExecutor
from core.recovery_planner import RecoveryPlanner
from storage.local_storage_provider import LocalStorageProvider


def main() -> None:
    provider = LocalStorageProvider()

    base_dir = Path("tmp/recovery_executor_test")
    rerender_queue_file = base_dir / "rerender_queue.json"
    rerender_jobs_file = base_dir / "rerender_jobs.json"

    if base_dir.exists():
        shutil.rmtree(base_dir)

    base_dir.mkdir(parents=True, exist_ok=True)

    try:
        provider.write_json(
            str(rerender_queue_file),
            [
                {
                    "job_id": "job_queue_001",
                    "channel_type": "gaming_main",
                    "video_path": "a.mp4",
                    "title": "A",
                    "description": "A",
                },
                "invalid-string-entry",
                {
                    "channel_type": "gaming_main",
                    "video_path": "missing_job_id.mp4",
                    "title": "B",
                    "description": "B",
                },
                {
                    "job_id": "job_queue_001",
                    "channel_type": "gaming_main",
                    "video_path": "dup.mp4",
                    "title": "C",
                    "description": "C",
                },
                {
                    "job_id": "job_queue_002",
                    "channel_type": "gaming_main",
                    "video_path": "d.mp4",
                    "title": "D",
                    "description": "D",
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
                    "status": "pending",
                },
                "invalid-rerender-entry",
                {
                    "rerender_job_id": "rer_invalid_002",
                    "status": "pending",
                },
                {
                    "rerender_job_id": "rer_valid_003",
                    "source_job_id": "job_source_003",
                    "status": "processing",
                },
            ],
            indent=4,
        )

        scan_result = IntegrityScanResult()

        scan_result.add_issue(
            issue_code="invalid_rerender_queue_entry",
            severity="medium",
            scope="rerender_queue",
            reference_id=str(rerender_queue_file),
            message="Queue-Eintrag ist kein Objekt",
        )
        scan_result.add_issue(
            issue_code="missing_queue_job_id",
            severity="medium",
            scope="rerender_queue",
            reference_id=str(rerender_queue_file),
            message="Queue-Eintrag ohne job_id",
        )
        scan_result.add_issue(
            issue_code="duplicate_rerender_queue_job",
            severity="medium",
            scope="rerender_queue",
            reference_id="job_queue_001",
            message="Gleiche job_id mehrfach in rerender_queue",
        )
        scan_result.add_issue(
            issue_code="invalid_rerender_job_entry",
            severity="medium",
            scope="rerender_jobs",
            reference_id=str(rerender_jobs_file),
            message="Rerender-Job-Eintrag ist kein Objekt",
        )

        planner = RecoveryPlanner()
        plan = planner.plan(scan_result)

        executor = RecoveryExecutor(storage_provider=provider)
        execution_result = executor.execute_safe_actions(
            plan,
            rerender_queue_file=str(rerender_queue_file),
            rerender_jobs_file=str(rerender_jobs_file),
        )

        queue_after = provider.read_json(str(rerender_queue_file))
        rerender_jobs_after = provider.read_json(str(rerender_jobs_file))

        assert len(queue_after) == 2
        assert queue_after[0]["job_id"] == "job_queue_001"
        assert queue_after[1]["job_id"] == "job_queue_002"

        assert len(rerender_jobs_after) == 2
        assert rerender_jobs_after[0]["rerender_job_id"] == "rer_valid_001"
        assert rerender_jobs_after[1]["rerender_job_id"] == "rer_valid_003"

        applied_codes = set(execution_result.applied_action_codes)

        assert "remove_invalid_rerender_queue_entry" in applied_codes
        assert "deduplicate_rerender_queue" in applied_codes
        assert "remove_invalid_rerender_job_entry" in applied_codes

        stats = execution_result.stats
        assert stats["removed_invalid_rerender_queue_entries"] == 2
        assert stats["removed_duplicate_rerender_queue_entries"] == 1
        assert stats["removed_invalid_rerender_job_entries"] == 2

        print("RECOVERY EXECUTOR SMOKE TEST PASSED")
        print(
            {
                "applied_action_codes": execution_result.applied_action_codes,
                "changed_files": execution_result.changed_files,
                "stats": execution_result.stats,
            }
        )

    finally:
        if base_dir.exists():
            shutil.rmtree(base_dir)


if __name__ == "__main__":
    main()