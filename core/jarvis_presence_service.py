from __future__ import annotations

from core.access_context_service import AccessContextService
from core.operations_dashboard_service import OperationsDashboardService
from models.jarvis_presence import JarvisPresence
from shared.ui_theme import UI_THEME


class JarvisPresenceService:
    def __init__(
        self,
        operations_dashboard_service: OperationsDashboardService | None = None,
        access_context_service: AccessContextService | None = None,
    ) -> None:
        self.operations_dashboard_service = (
            operations_dashboard_service or OperationsDashboardService()
        )
        self.access_context_service = (
            access_context_service or AccessContextService()
        )

    def build_presence_surface(
        self,
        *,
        base_path: str = "exports",
        rerender_queue_file: str = "data/rerender_queue.json",
        rerender_jobs_file: str = "data/rerender_jobs.json",
    ) -> dict[str, object]:
        operations_surface = self.operations_dashboard_service.build_operations_surface(
            base_path=base_path,
            rerender_queue_file=rerender_queue_file,
            rerender_jobs_file=rerender_jobs_file,
        )
        actor_context = self.access_context_service.resolve_actor_context()

        warnings = list(
            (operations_surface.get("warnings") or {}).get("warning_cases") or []
        )
        blocked_jobs = list(
            (operations_surface.get("blocked_jobs") or {}).get("blocked_jobs") or []
        )
        review = dict(operations_surface.get("review") or {})
        queue = dict(operations_surface.get("queue") or {})
        publish = dict(operations_surface.get("publish") or {})
        runtime = dict(operations_surface.get("runtime") or {})
        vacation = dict(operations_surface.get("vacation") or {})

        warning_count = len(warnings)
        blocked_count = len(blocked_jobs)
        pending_reviews = int(review.get("pending_count", 0) or 0)
        queue_total = int(queue.get("total_entries", 0) or 0)
        published_jobs = int(
            (publish.get("job_publish_stats") or {}).get("published_jobs", 0) or 0
        )

        presence_state = "stable"
        alert_level = "nominal"
        focus_label = "System Overview"

        if warning_count > 0 or blocked_count > 0:
            presence_state = "alert"
            alert_level = "elevated"
            focus_label = "Warnings and Blockers"
        elif pending_reviews > 0:
            presence_state = "attention"
            alert_level = "watch"
            focus_label = "Review Queue"

        if vacation.get("is_active_now"):
            focus_label = "Vacation Operations"

        status_line = (
            f"Runtime {runtime.get('mode', '-')}"
            f" • Reviews {pending_reviews}"
            f" • Queue {queue_total}"
            f" • Published {published_jobs}"
            f" • Warnings {warning_count}"
        )

        presence = JarvisPresence(
            title=UI_THEME["jarvis_name"],
            subtitle=UI_THEME["labels"]["presence_subtitle"],
            presence_state=presence_state,
            alert_level=alert_level,
            focus_label=focus_label,
            status_line=status_line,
            workspace_label=str(actor_context.workspace_id or "-"),
            actor_label=str(actor_context.actor_id or "-"),
            role_label=str(actor_context.role.value),
            is_remote=bool(actor_context.is_remote),
            highlight_metrics=[
                {"label": "Warnings", "value": warning_count},
                {"label": "Blocked Jobs", "value": blocked_count},
                {"label": "Open Reviews", "value": pending_reviews},
                {"label": "Queue Entries", "value": queue_total},
                {"label": "Published Jobs", "value": published_jobs},
            ],
        )

        return {
            "theme": UI_THEME,
            "presence": presence.to_dict(),
            "operations": operations_surface,
        }