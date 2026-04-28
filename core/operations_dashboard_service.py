from __future__ import annotations

from core.authorization_service import AuthorizationService
from core.jarvis_status_service import JarvisStatusService
from storage.base_storage_provider import BaseStorageProvider
from storage.local_storage_provider import LocalStorageProvider


class OperationsDashboardService:
    def __init__(
        self,
        storage_provider: BaseStorageProvider | None = None,
        jarvis_status_service: JarvisStatusService | None = None,
        authorization_service: AuthorizationService | None = None,
    ) -> None:
        self.storage = storage_provider or LocalStorageProvider()
        self.jarvis_status_service = (
            jarvis_status_service
            or JarvisStatusService(storage_provider=self.storage)
        )
        self.authorization_service = authorization_service or AuthorizationService()

    def build_operations_surface(
        self,
        *,
        base_path: str = "exports",
        rerender_queue_file: str = "data/rerender_queue.json",
        rerender_jobs_file: str = "data/rerender_jobs.json",
    ) -> dict[str, object]:
        system_status = self.jarvis_status_service.get_system_status(
            base_path=base_path,
            rerender_queue_file=rerender_queue_file,
            rerender_jobs_file=rerender_jobs_file,
        )

        runtime_status = dict(system_status.get("runtime_status") or {})
        vacation_status = dict(system_status.get("vacation_status") or {})
        review_status = dict(system_status.get("review_status") or {})
        queue_status = dict(system_status.get("queue_status") or {})
        publish_status = dict(system_status.get("publish_status") or {})
        kpi_summary = dict(system_status.get("kpi_summary") or {})
        feedback_summary = dict(system_status.get("feedback_summary") or {})
        blocked_jobs = dict(system_status.get("blocked_jobs") or {})
        maintenance_status = dict(system_status.get("maintenance_status") or {})
        warning_cases = dict(system_status.get("warning_cases") or {})

        return {
            "overview": self._build_overview_surface(
                runtime_status=runtime_status,
                vacation_status=vacation_status,
                review_status=review_status,
                queue_status=queue_status,
                publish_status=publish_status,
                blocked_jobs=blocked_jobs,
                maintenance_status=maintenance_status,
                warning_cases=warning_cases,
            ),
            "runtime": runtime_status,
            "vacation": vacation_status,
            "review": review_status,
            "queue": queue_status,
            "publish": publish_status,
            "kpi": kpi_summary,
            "feedback": feedback_summary,
            "blocked_jobs": blocked_jobs,
            "maintenance": maintenance_status,
            "warnings": warning_cases,
            "access_policy": self._build_access_policy_surface(),
            "jarvis_panel": self._build_jarvis_panel_surface(),
        }

    def _build_overview_surface(
        self,
        *,
        runtime_status: dict[str, object],
        vacation_status: dict[str, object],
        review_status: dict[str, object],
        queue_status: dict[str, object],
        publish_status: dict[str, object],
        blocked_jobs: dict[str, object],
        maintenance_status: dict[str, object],
        warning_cases: dict[str, object],
    ) -> dict[str, object]:
        job_publish_stats = dict(publish_status.get("job_publish_stats") or {})

        cards = [
            {
                "label": "Runtime Mode",
                "value": runtime_status.get("mode") or "-",
                "hint": f'Blocked Actions: {runtime_status.get("blocked_action_count", 0)}',
            },
            {
                "label": "Vacation",
                "value": (
                    "active_now"
                    if vacation_status.get("is_active_now")
                    else "armed"
                    if vacation_status.get("enabled")
                    else "inactive"
                ),
                "hint": f'Effective Mode: {vacation_status.get("effective_mode") or "-"}',
            },
            {
                "label": "Open Reviews",
                "value": int(review_status.get("pending_count", 0) or 0),
                "hint": f'Total Jobs: {review_status.get("total_jobs", 0)}',
            },
            {
                "label": "Queue Entries",
                "value": int(queue_status.get("total_entries", 0) or 0),
                "hint": f'Blocked Queue: {queue_status.get("blocked_count", 0)}',
            },
            {
                "label": "Published Jobs",
                "value": int(job_publish_stats.get("published_jobs", 0) or 0),
                "hint": f'Scheduled: {job_publish_stats.get("scheduled_jobs", 0)}',
            },
            {
                "label": "Blocked Jobs",
                "value": int(blocked_jobs.get("blocked_count", 0) or 0),
                "hint": f'Warnings: {warning_cases.get("warning_count", 0)}',
            },
            {
                "label": "Maintenance",
                "value": int(maintenance_status.get("integrity_issue_count", 0) or 0),
                "hint": (
                    f'Recovery: {maintenance_status.get("recovery_action_count", 0)} '
                    f'| Retention: {maintenance_status.get("retention_decision_count", 0)}'
                ),
            },
        ]

        return {
            "cards": cards,
            "top_warnings": list(warning_cases.get("warning_cases") or [])[:5],
            "top_blocked_jobs": list(blocked_jobs.get("blocked_jobs") or [])[:5],
            "top_pending_reviews": list(review_status.get("pending_reviews") or [])[:5],
        }

    def _build_access_policy_surface(self) -> dict[str, object]:
        role_matrix = self.authorization_service.build_role_capability_matrix()

        return {
            "roles": role_matrix,
            "role_count": len(role_matrix),
        }

    def _build_jarvis_panel_surface(self) -> dict[str, object]:
        return {
            "placeholder": "z. B. Wie ist der Systemstatus?",
            "example_commands": [
                "Wie ist der Systemstatus?",
                "Was muss ich heute reviewen?",
                "Welche Jobs sind blockiert?",
                "Zeig mir Warnfälle.",
                "Wie ist der Queue Status?",
                "Wie ist der Publish Status?",
                "Welche Plattform ist schwach?",
                "Wie ist der Maintenance Status?",
            ],
        }