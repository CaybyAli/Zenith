from pathlib import Path
import shutil

from core.integrity_scanner import IntegrityScanner
from storage.local_storage_provider import LocalStorageProvider


def main() -> None:
    provider = LocalStorageProvider()

    base_dir = Path("tmp/integrity_scanner_test")
    exports_dir = base_dir / "exports" / "gaming_main"
    rerender_queue_file = base_dir / "rerender_queue.json"
    rerender_jobs_file = base_dir / "rerender_jobs.json"

    if base_dir.exists():
        shutil.rmtree(base_dir)

    (exports_dir / "job_ok_001").mkdir(parents=True, exist_ok=True)
    (exports_dir / "job_broken_001").mkdir(parents=True, exist_ok=True)
    (exports_dir / "job_orphan_001").mkdir(parents=True, exist_ok=True)

    try:
        (exports_dir / "job_ok_001" / "video.mp4").write_text("fake-video", encoding="utf-8")
        (exports_dir / "job_ok_001" / "thumbnail.jpg").write_text("fake-thumb", encoding="utf-8")

        provider.write_json(
            str(exports_dir / "job_ok_001" / "job.json"),
            {
                "job_id": "job_ok_001",
                "video_path": str(exports_dir / "job_ok_001" / "video.mp4"),
                "thumbnail_path": str(exports_dir / "job_ok_001" / "thumbnail.jpg"),
                "shorts": [],
            },
            indent=4,
        )

        provider.write_json(
            str(exports_dir / "job_broken_001" / "job.json"),
            {
                "job_id": "job_broken_001",
                "video_path": str(exports_dir / "job_broken_001" / "video.mp4"),
                "thumbnail_path": str(exports_dir / "job_broken_001" / "thumbnail.jpg"),
                "shorts": [
                    {
                        "short_id": "short_1",
                        "path": str(exports_dir / "job_broken_001" / "short_1.mp4"),
                    }
                ],
            },
            indent=4,
        )

        (exports_dir / "job_orphan_001" / "video.mp4").write_text("orphan-video", encoding="utf-8")

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
                    "rerender_job_id": "rer_001",
                    "source_job_id": "job_dup_active_001",
                    "status": "pending",
                },
                {
                    "rerender_job_id": "rer_002",
                    "source_job_id": "job_dup_active_001",
                    "status": "processing",
                },
            ],
            indent=4,
        )

        scanner = IntegrityScanner(storage_provider=provider)
        result = scanner.scan(
            exports_base_path=str(base_dir / "exports"),
            rerender_queue_file=str(rerender_queue_file),
            rerender_jobs_file=str(rerender_jobs_file),
        )

        result_dict = result.to_dict()

        assert result.export_jobs_seen == 2
        assert result.rerender_queue_items_seen == 2
        assert result.rerender_jobs_seen == 2
        assert len(result.issues) >= 5

        issue_codes = {issue["issue_code"] for issue in result_dict["issues"]}

        assert "orphan_export_folder" in issue_codes
        assert "missing_export_video_file" in issue_codes
        assert "missing_thumbnail_artifact" in issue_codes
        assert "missing_short_artifact" in issue_codes
        assert "duplicate_rerender_queue_job" in issue_codes
        assert "duplicate_active_rerender_job" in issue_codes

        print("INTEGRITY SCANNER SMOKE TEST PASSED")
        print(
            {
                "export_jobs_seen": result.export_jobs_seen,
                "rerender_queue_items_seen": result.rerender_queue_items_seen,
                "rerender_jobs_seen": result.rerender_jobs_seen,
                "issues_found": len(result.issues),
            }
        )

    finally:
        if base_dir.exists():
            shutil.rmtree(base_dir)


if __name__ == "__main__":
    main()