from core.integrity_scanner import IntegrityScanResult
from core.recovery_planner import RecoveryPlanner


def main() -> None:
    scan_result = IntegrityScanResult(
        export_jobs_seen=2,
        rerender_jobs_seen=2,
        rerender_queue_items_seen=2,
    )

    scan_result.add_issue(
        issue_code="orphan_export_folder",
        severity="high",
        scope="export",
        reference_id="gaming_main/job_orphan_001",
        message="Exportordner enthält Artefakte, aber keine job.json",
    )
    scan_result.add_issue(
        issue_code="duplicate_rerender_queue_job",
        severity="medium",
        scope="rerender_queue",
        reference_id="job_dup_001",
        message="Gleiche job_id mehrfach in rerender_queue",
    )
    scan_result.add_issue(
        issue_code="processing_rerender_requires_review",
        severity="medium",
        scope="rerender_jobs",
        reference_id="rer_002",
        message="Rerender-Job steht auf processing und braucht manuelle Prüfung",
    )
    scan_result.add_issue(
        issue_code="missing_short_artifact",
        severity="medium",
        scope="export",
        reference_id="gaming_main/job_broken_001",
        message="Short-Datei fehlt: short_1",
    )

    planner = RecoveryPlanner()
    plan = planner.plan(scan_result)
    plan_dict = plan.to_dict()

    assert len(plan.actions) == 4
    assert plan.safe_actions_count == 1
    assert plan.manual_review_actions_count == 3

    action_map = {action["action_code"]: action for action in plan_dict["actions"]}

    assert "review_orphan_export_folder" in action_map
    assert action_map["review_orphan_export_folder"]["requires_manual_review"] is True

    assert "deduplicate_rerender_queue" in action_map
    assert action_map["deduplicate_rerender_queue"]["safe_to_apply"] is True

    assert "review_stuck_processing_rerender" in action_map
    assert action_map["review_stuck_processing_rerender"]["requires_manual_review"] is True

    assert "remove_or_rebuild_missing_short" in action_map
    assert action_map["remove_or_rebuild_missing_short"]["requires_manual_review"] is True

    print("RECOVERY PLANNER SMOKE TEST PASSED")
    print(
        {
            "actions": len(plan.actions),
            "safe_actions_count": plan.safe_actions_count,
            "manual_review_actions_count": plan.manual_review_actions_count,
        }
    )


if __name__ == "__main__":
    main()