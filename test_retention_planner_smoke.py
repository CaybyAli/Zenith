from datetime import datetime, timezone

from core.retention_planner import RetentionPlanner


def main() -> None:
    planner = RetentionPlanner(
        published_review_after_days=30,
        failed_review_after_days=7,
        rerender_done_review_after_days=7,
        rerender_failed_review_after_days=7,
    )

    now = datetime(2026, 4, 14, 12, 0, 0, tzinfo=timezone.utc)

    export_jobs = [
        {
            "job_id": "job_published_old_001",
            "publish_status": "published",
            "published_at": "2026-03-01T10:00:00+00:00",
            "updated_at": "2026-03-01T10:00:00+00:00",
            "created_at": "2026-03-01T09:00:00+00:00",
            "permanently_failed": False,
            "review_status": "approved",
            "is_rerender": False,
        },
        {
            "job_id": "job_failed_old_001",
            "publish_status": "failed",
            "updated_at": "2026-04-01T10:00:00+00:00",
            "created_at": "2026-03-30T09:00:00+00:00",
            "permanently_failed": True,
            "review_status": "rejected",
            "is_rerender": False,
        },
        {
            "job_id": "job_rerender_stale_001",
            "publish_status": None,
            "updated_at": "2026-04-01T10:00:00+00:00",
            "created_at": "2026-04-01T09:00:00+00:00",
            "permanently_failed": False,
            "review_status": "pending",
            "is_rerender": True,
        },
        {
            "job_id": "job_recent_001",
            "publish_status": "published",
            "published_at": "2026-04-12T10:00:00+00:00",
            "updated_at": "2026-04-12T10:00:00+00:00",
            "created_at": "2026-04-12T09:00:00+00:00",
            "permanently_failed": False,
            "review_status": "approved",
            "is_rerender": False,
        },
    ]

    rerender_jobs = [
        {
            "rerender_job_id": "rer_done_old_001",
            "status": "done",
            "last_retry_at": "2026-04-01T10:00:00+00:00",
        },
        {
            "rerender_job_id": "rer_failed_old_001",
            "status": "failed_runtime",
            "last_retry_at": "2026-04-02T10:00:00+00:00",
        },
        {
            "rerender_job_id": "rer_recent_001",
            "status": "done",
            "last_retry_at": "2026-04-13T10:00:00+00:00",
        },
    ]

    plan = planner.build_plan(
        export_jobs=export_jobs,
        rerender_jobs=rerender_jobs,
        now=now,
    )
    plan_dict = plan.to_dict()

    assert len(plan.decisions) == 5

    decisions_by_id = {item["reference_id"]: item for item in plan_dict["decisions"]}

    assert decisions_by_id["job_published_old_001"]["retention_class"] == "published_review_candidate"
    assert decisions_by_id["job_failed_old_001"]["retention_class"] == "failed_review_candidate"
    assert decisions_by_id["job_rerender_stale_001"]["retention_class"] == "stale_rerender_review_candidate"
    assert decisions_by_id["rer_done_old_001"]["retention_class"] == "rerender_done_review_candidate"
    assert decisions_by_id["rer_failed_old_001"]["retention_class"] == "rerender_failed_review_candidate"

    assert "job_recent_001" not in decisions_by_id
    assert "rer_recent_001" not in decisions_by_id

    print("RETENTION PLANNER SMOKE TEST PASSED")
    print({"decisions": len(plan.decisions)})


if __name__ == "__main__":
    main()