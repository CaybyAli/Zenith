from pathlib import Path
import shutil

from core.maintenance_report_builder import MaintenanceReportBuilder
from storage.local_storage_provider import LocalStorageProvider


def main() -> None:
    provider = LocalStorageProvider()

    base_dir = Path("tmp/maintenance_report_test")
    exports_dir = base_dir / "exports" / "gaming_main"
    rerender_queue_file = base_dir / "rerender_queue.json"
    rerender_jobs_file = base_dir / "rerender_jobs.json"

    if base_dir.exists():
        shutil.rmtree(base_dir)

    (exports_dir / "job_ok_001").mkdir(parents=True, exist_ok=True)
    (exports_dir / "job_old_published_001").mkdir(parents=True, exist_ok=True)
    (exports_dir / "job_orphan_001").mkdir(parents=True, exist_ok=True)

    try:
        (exports_dir / "job_ok_001" / "video.mp4").write_text("video", encoding="utf-8")
        provider.write_json(
            str(exports_dir / "job_ok_001" / "job.json"),
            {
                "job_id": "job_ok_001",
                "video_path": str(exports_dir / "job_ok_001" / "video.mp4"),
                "thumbnail_path": None,
                "publish_status": None,
                "permanently_failed": False,
                "review_status": "pending",
                "is_rerender": False,
                "updated_at": "2026-04-13T10:00:00+00:00",
                "created_at": "2026-04-13T09:00:00+00:00",
                "shorts": [],
            },
            indent=4,
        )

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
                {"job_id": "job_dup_001", "channel_type": "gaming_main", "video_path": "x", "title": "a", "description": "a"},
                {"job_id": "job_dup_001", "channel_type": "gaming_main", "video_path": "x", "title": "b", "description": "b"},
            ],
            indent=4,
        )

        provider.write_json(
            str(rerender_jobs_file),
            [
                {
                    "rerender_job_id": "rer_done_old_001",
                    "source_job_id": "job_source_001",
                    "status": "done",
                    "last_retry_at": "2026-04-01T10:00:00+00:00",
                },
                {
                    "rerender_job_id": "rer_processing_001",
                    "source_job_id": "job_source_002",
                    "status": "processing",
                    "last_retry_at": "2026-04-13T10:00:00+00:00",
                },
            ],
            indent=4,
        )

        builder = MaintenanceReportBuilder(storage_provider=provider)
        report = builder.build(
            exports_base_path=str(base_dir / "exports"),
            rerender_queue_file=str(rerender_queue_file),
            rerender_jobs_file=str(rerender_jobs_file),
        )

        report_dict = report.to_dict()

        assert "integrity" in report_dict
        assert "recovery_plan" in report_dict
        assert "retention_plan" in report_dict

        integrity = report_dict["integrity"]
        recovery_plan = report_dict["recovery_plan"]
        retention_plan = report_dict["retention_plan"]

        assert integrity["export_jobs_seen"] == 2
        assert integrity["rerender_queue_items_seen"] == 2
        assert integrity["rerender_jobs_seen"] == 2
        assert len(integrity["issues"]) >= 3

        recovery_action_codes = {item["action_code"] for item in recovery_plan["actions"]}
        assert "review_orphan_export_folder" in recovery_action_codes
        assert "deduplicate_rerender_queue" in recovery_action_codes
        assert "review_stuck_processing_rerender" in recovery_action_codes

        retention_reference_ids = {item["reference_id"] for item in retention_plan["decisions"]}
        assert "job_old_published_001" in retention_reference_ids
        assert "rer_done_old_001" in retention_reference_ids

        print("MAINTENANCE REPORT BUILDER SMOKE TEST PASSED")
        print(
            {
                "integrity_issues": len(integrity["issues"]),
                "recovery_actions": len(recovery_plan["actions"]),
                "retention_decisions": len(retention_plan["decisions"]),
            }
        )

    finally:
        if base_dir.exists():
            shutil.rmtree(base_dir)


if __name__ == "__main__":
    main()