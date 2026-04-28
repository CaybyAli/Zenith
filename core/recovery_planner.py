from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from core.integrity_scanner import IntegrityScanResult


@dataclass(slots=True)
class RecoveryAction:
    source_issue_code: str
    action_code: str
    severity: str
    scope: str
    reference_id: str
    safe_to_apply: bool
    requires_manual_review: bool
    reason: str


@dataclass(slots=True)
class RecoveryPlan:
    actions: list[RecoveryAction] = field(default_factory=list)

    def add_action(
        self,
        *,
        source_issue_code: str,
        action_code: str,
        severity: str,
        scope: str,
        reference_id: str,
        safe_to_apply: bool,
        requires_manual_review: bool,
        reason: str,
    ) -> None:
        self.actions.append(
            RecoveryAction(
                source_issue_code=source_issue_code,
                action_code=action_code,
                severity=severity,
                scope=scope,
                reference_id=reference_id,
                safe_to_apply=safe_to_apply,
                requires_manual_review=requires_manual_review,
                reason=reason,
            )
        )

    @property
    def safe_actions_count(self) -> int:
        return sum(1 for action in self.actions if action.safe_to_apply)

    @property
    def manual_review_actions_count(self) -> int:
        return sum(1 for action in self.actions if action.requires_manual_review)

    def to_dict(self) -> dict[str, Any]:
        return {
            "actions": [
                {
                    "source_issue_code": action.source_issue_code,
                    "action_code": action.action_code,
                    "severity": action.severity,
                    "scope": action.scope,
                    "reference_id": action.reference_id,
                    "safe_to_apply": action.safe_to_apply,
                    "requires_manual_review": action.requires_manual_review,
                    "reason": action.reason,
                }
                for action in self.actions
            ],
            "safe_actions_count": self.safe_actions_count,
            "manual_review_actions_count": self.manual_review_actions_count,
        }


class RecoveryPlanner:
    ISSUE_RULES: dict[str, dict[str, Any]] = {
        "orphan_export_folder": {
            "action_code": "review_orphan_export_folder",
            "safe_to_apply": False,
            "requires_manual_review": True,
        },
        "broken_job_json": {
            "action_code": "quarantine_broken_job_json",
            "safe_to_apply": False,
            "requires_manual_review": True,
        },
        "job_id_mismatch": {
            "action_code": "review_job_id_mismatch",
            "safe_to_apply": False,
            "requires_manual_review": True,
        },
        "missing_video_artifact": {
            "action_code": "rebuild_or_quarantine_job",
            "safe_to_apply": False,
            "requires_manual_review": True,
        },
        "missing_thumbnail_artifact": {
            "action_code": "review_or_regenerate_thumbnail",
            "safe_to_apply": False,
            "requires_manual_review": True,
        },
        "missing_export_video_file": {
            "action_code": "rebuild_missing_export_video",
            "safe_to_apply": False,
            "requires_manual_review": True,
        },
        "invalid_short_entry": {
            "action_code": "review_invalid_short_entry",
            "safe_to_apply": False,
            "requires_manual_review": True,
        },
        "duplicate_short_id": {
            "action_code": "deduplicate_short_entries",
            "safe_to_apply": False,
            "requires_manual_review": True,
        },
        "short_missing_path": {
            "action_code": "remove_or_rebuild_missing_short",
            "safe_to_apply": False,
            "requires_manual_review": True,
        },
        "missing_short_artifact": {
            "action_code": "remove_or_rebuild_missing_short",
            "safe_to_apply": False,
            "requires_manual_review": True,
        },
        "broken_rerender_queue": {
            "action_code": "repair_rerender_queue_file",
            "safe_to_apply": False,
            "requires_manual_review": True,
        },
        "invalid_rerender_queue_format": {
            "action_code": "reset_rerender_queue_format",
            "safe_to_apply": False,
            "requires_manual_review": True,
        },
        "invalid_rerender_queue_entry": {
            "action_code": "remove_invalid_rerender_queue_entry",
            "safe_to_apply": True,
            "requires_manual_review": False,
        },
        "missing_queue_job_id": {
            "action_code": "remove_invalid_rerender_queue_entry",
            "safe_to_apply": True,
            "requires_manual_review": False,
        },
        "duplicate_rerender_queue_job": {
            "action_code": "deduplicate_rerender_queue",
            "safe_to_apply": True,
            "requires_manual_review": False,
        },
        "broken_rerender_jobs": {
            "action_code": "repair_rerender_jobs_file",
            "safe_to_apply": False,
            "requires_manual_review": True,
        },
        "invalid_rerender_jobs_format": {
            "action_code": "reset_rerender_jobs_format",
            "safe_to_apply": False,
            "requires_manual_review": True,
        },
        "invalid_rerender_job_entry": {
            "action_code": "remove_invalid_rerender_job_entry",
            "safe_to_apply": True,
            "requires_manual_review": False,
        },
        "missing_rerender_source_job": {
            "action_code": "review_or_remove_rerender_job",
            "safe_to_apply": False,
            "requires_manual_review": True,
        },
        "processing_rerender_requires_review": {
            "action_code": "review_stuck_processing_rerender",
            "safe_to_apply": False,
            "requires_manual_review": True,
        },
        "duplicate_active_rerender_job": {
            "action_code": "deduplicate_active_rerender_jobs",
            "safe_to_apply": False,
            "requires_manual_review": True,
        },
    }

    def plan(self, scan_result: IntegrityScanResult) -> RecoveryPlan:
        plan = RecoveryPlan()

        for issue in scan_result.issues:
            rule = self.ISSUE_RULES.get(issue.issue_code)

            if rule is None:
                plan.add_action(
                    source_issue_code=issue.issue_code,
                    action_code="manual_review_unknown_issue",
                    severity=issue.severity,
                    scope=issue.scope,
                    reference_id=issue.reference_id,
                    safe_to_apply=False,
                    requires_manual_review=True,
                    reason=issue.message,
                )
                continue

            plan.add_action(
                source_issue_code=issue.issue_code,
                action_code=str(rule["action_code"]),
                severity=issue.severity,
                scope=issue.scope,
                reference_id=issue.reference_id,
                safe_to_apply=bool(rule["safe_to_apply"]),
                requires_manual_review=bool(rule["requires_manual_review"]),
                reason=issue.message,
            )

        return plan