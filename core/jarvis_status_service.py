from __future__ import annotations

from core.feedback_dashboard_service import FeedbackDashboardService
from core.job_loader import JobLoader
from core.kpi_dashboard_service import KpiDashboardService
from core.maintenance_report_builder import MaintenanceReportBuilder
from core.publish_guard_repository import PublishGuardRepository
from core.publish_result_repository import PublishResultRepository
from core.queue_store import QueueStore
from core.runtime_mode_controller import RuntimeModeController
from core.vacation_controller import VacationController
from shared.job_review_view import build_review_card_data
from shared.runtime_modes import RuntimeAction
from storage.base_storage_provider import BaseStorageProvider
from storage.local_storage_provider import LocalStorageProvider


class JarvisStatusService:
    def __init__(
        self,
        storage_provider: BaseStorageProvider | None = None,
        job_loader: JobLoader | None = None,
        kpi_dashboard_service: KpiDashboardService | None = None,
        feedback_dashboard_service: FeedbackDashboardService | None = None,
        runtime_mode_controller: RuntimeModeController | None = None,
        vacation_controller: VacationController | None = None,
        publish_guard_repository: PublishGuardRepository | None = None,
        publish_result_repository: PublishResultRepository | None = None,
        queue_store: QueueStore | None = None,
        maintenance_report_builder: MaintenanceReportBuilder | None = None,
    ) -> None:
        self.storage = storage_provider or LocalStorageProvider()
        self.job_loader = job_loader or JobLoader(storage_provider=self.storage)
        self.kpi_dashboard_service = (
            kpi_dashboard_service
            or KpiDashboardService(storage_provider=self.storage)
        )
        self.feedback_dashboard_service = (
            feedback_dashboard_service
            or FeedbackDashboardService(storage_provider=self.storage)
        )
        self.runtime_mode_controller = (
            runtime_mode_controller or RuntimeModeController()
        )
        self.vacation_controller = vacation_controller or VacationController()
        self.publish_guard_repository = (
            publish_guard_repository
            or PublishGuardRepository(storage_provider=self.storage)
        )
        self.publish_result_repository = (
            publish_result_repository
            or PublishResultRepository(storage_provider=self.storage)
        )
        self.queue_store = queue_store or QueueStore()
        self.maintenance_report_builder = (
            maintenance_report_builder or MaintenanceReportBuilder(storage_provider=self.storage)
        )

    def get_runtime_status(self) -> dict[str, object]:
        state = self.runtime_mode_controller.get_state()
        allowed_actions = sorted(
            action.value
            for action in self.runtime_mode_controller.get_allowed_actions(state.mode)
        )
        all_actions = sorted(action.value for action in RuntimeAction)
        blocked_actions = [
            action_name
            for action_name in all_actions
            if action_name not in allowed_actions
        ]

        return {
            "mode": state.mode.value,
            "updated_at": state.updated_at,
            "allowed_actions": allowed_actions,
            "blocked_actions": blocked_actions,
            "allowed_action_count": len(allowed_actions),
            "blocked_action_count": len(blocked_actions),
        }

    def get_vacation_status(self) -> dict[str, object]:
        state = self.vacation_controller.get_state()
        is_active_now = self.vacation_controller.is_active_now()
        effective_mode = self.vacation_controller.get_effective_mode()

        return {
            "enabled": state.enabled,
            "start_at": state.start_at,
            "end_at": state.end_at,
            "updated_at": state.updated_at,
            "is_active_now": is_active_now,
            "effective_mode": effective_mode.value,
        }

    def get_review_status(self, base_path: str = "exports") -> dict[str, object]:
        jobs = list(self.job_loader.load_all_jobs(base_path=base_path))
        pending_reviews: list[dict[str, object]] = []

        approved_count = 0
        rejected_count = 0
        pending_count = 0

        for job in jobs:
            review_status = str(getattr(job, "review_status", "") or "").strip().lower()

            if review_status == "approved":
                approved_count += 1
            elif review_status == "rejected":
                rejected_count += 1
            elif review_status == "pending":
                pending_count += 1
                card = build_review_card_data(job)
                pending_reviews.append(
                    {
                        "job_id": job.job_id,
                        "title": card["title"],
                        "channel": card["channel"],
                        "final_score": card["final_score"],
                        "recommended_action": card["recommended_action"],
                        "shorts_count": card["shorts_count"],
                    }
                )

        pending_reviews.sort(
            key=lambda item: (
                item["final_score"] is None,
                item["final_score"] if item["final_score"] is not None else 999.0,
            )
        )

        return {
            "total_jobs": len(jobs),
            "pending_count": pending_count,
            "approved_count": approved_count,
            "rejected_count": rejected_count,
            "pending_reviews": pending_reviews[:10],
        }

    def get_kpi_summary(self, base_path: str = "exports") -> dict[str, object]:
        surface = self.kpi_dashboard_service.build_surface(base_path=base_path)

        platform_stats = list(surface.get("platform_stats") or [])
        top_entries = list(surface.get("top_entries") or [])
        low_entries = list(surface.get("low_entries") or [])
        insights = list(surface.get("insights") or [])

        best_platform = platform_stats[0] if platform_stats else None
        weakest_platform = platform_stats[-1] if platform_stats else None
        top_entry = top_entries[0] if top_entries else None
        low_entry = low_entries[0] if low_entries else None

        return {
            "total_entries": int(surface.get("total_entries", 0) or 0),
            "winner_count": int(surface.get("winner_count", 0) or 0),
            "loser_count": int(surface.get("loser_count", 0) or 0),
            "outlier_count": int(surface.get("outlier_count", 0) or 0),
            "best_platform": best_platform,
            "weakest_platform": weakest_platform,
            "top_entry": top_entry,
            "low_entry": low_entry,
            "insights": insights[:5],
            "platform_stats": platform_stats,
            "channel_stats": list(surface.get("channel_stats") or []),
        }

    def get_weak_platforms(self, base_path: str = "exports") -> dict[str, object]:
        kpi_summary = self.get_kpi_summary(base_path=base_path)
        platform_stats = list(kpi_summary.get("platform_stats") or [])

        sorted_platforms = sorted(
            platform_stats,
            key=lambda item: item.get("average_score") or 0.0,
        )

        return {
            "platform_count": len(sorted_platforms),
            "weakest_platform": sorted_platforms[0] if sorted_platforms else None,
            "platforms": sorted_platforms[:5],
        }

    def get_feedback_summary(self, base_path: str = "exports") -> dict[str, object]:
        surface = self.feedback_dashboard_service.build_surface(base_path=base_path)

        category_stats = list(surface.get("category_stats") or [])
        direction_stats = list(surface.get("direction_stats") or [])
        pattern_summaries = list(surface.get("pattern_summaries") or [])
        recent_feedback = list(surface.get("recent_feedback") or [])

        top_category = category_stats[0] if category_stats else None
        top_direction = direction_stats[0] if direction_stats else None
        top_pattern = pattern_summaries[0] if pattern_summaries else None

        return {
            "total_records": int(surface.get("total_records", 0) or 0),
            "top_category": top_category,
            "top_direction": top_direction,
            "top_pattern": top_pattern,
            "category_stats": category_stats,
            "direction_stats": direction_stats,
            "pattern_summaries": pattern_summaries[:5],
            "recent_feedback": recent_feedback[:5],
        }

    def get_queue_status(self) -> dict[str, object]:
        entries = list(self.queue_store.list_queue_entries())

        state_counts: dict[str, int] = {}
        review_counts: dict[str, int] = {}
        blocked_entries: list[dict[str, object]] = []

        for entry in entries:
            queue_state = self._enum_to_value(entry.queue_state)
            review_status = self._enum_to_value(entry.review_status)

            state_counts[queue_state] = state_counts.get(queue_state, 0) + 1
            review_counts[review_status] = review_counts.get(review_status, 0) + 1

            if queue_state == "blocked" or entry.block_reason:
                blocked_entries.append(
                    {
                        "queue_entry_id": entry.queue_entry_id,
                        "topic_label": entry.topic_label,
                        "channel_type": entry.channel_type,
                        "platform": entry.platform,
                        "queue_state": queue_state,
                        "review_status": review_status,
                        "opportunity_score": entry.opportunity_score,
                        "block_reason": entry.block_reason,
                    }
                )

        top_entries = sorted(
            entries,
            key=lambda item: float(item.opportunity_score or 0.0),
            reverse=True,
        )[:10]

        return {
            "total_entries": len(entries),
            "blocked_count": len(blocked_entries),
            "state_counts": [
                {"queue_state": key, "count": value}
                for key, value in sorted(
                    state_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ],
            "review_counts": [
                {"review_status": key, "count": value}
                for key, value in sorted(
                    review_counts.items(),
                    key=lambda item: (-item[1], item[0]),
                )
            ],
            "blocked_entries": blocked_entries[:10],
            "top_entries": [
                {
                    "queue_entry_id": entry.queue_entry_id,
                    "topic_label": entry.topic_label,
                    "channel_type": entry.channel_type,
                    "platform": entry.platform,
                    "queue_state": self._enum_to_value(entry.queue_state),
                    "review_status": self._enum_to_value(entry.review_status),
                    "opportunity_score": entry.opportunity_score,
                }
                for entry in top_entries
            ],
        }

    def get_publish_status(self, base_path: str = "exports") -> dict[str, object]:
        jobs = list(self.job_loader.load_all_jobs(base_path=base_path))

        job_publish_stats = {
            "published_jobs": 0,
            "scheduled_jobs": 0,
            "waiting_for_review_jobs": 0,
            "permanently_failed_jobs": 0,
            "retry_scheduled_jobs": 0,
        }

        platform_publish_counts: dict[str, int] = {}
        recent_publish_results: list[dict[str, object]] = []

        for job in jobs:
            publish_status = str(getattr(job, "publish_status", "") or "").strip().lower()
            review_status = str(getattr(job, "review_status", "") or "").strip().lower()
            retry_status = str(getattr(job, "retry_status", "") or "").strip().lower()

            if publish_status == "published":
                job_publish_stats["published_jobs"] += 1

            if bool(getattr(job, "is_scheduled", False)) or getattr(job, "scheduled_at", None):
                job_publish_stats["scheduled_jobs"] += 1

            if review_status == "pending":
                job_publish_stats["waiting_for_review_jobs"] += 1

            if bool(getattr(job, "permanently_failed", False)):
                job_publish_stats["permanently_failed_jobs"] += 1

            if retry_status == "scheduled_retry":
                job_publish_stats["retry_scheduled_jobs"] += 1

            export_path = self._build_export_path(base_path, job)

            for result in self.publish_result_repository.load_results(export_path):
                result_dict = self._safe_to_dict(result)
                status_name = str(result_dict.get("publish_status") or "unknown").strip().lower()
                platform_name = self._extract_platform_name(result_dict.get("platform"))

                platform_publish_counts[status_name] = (
                    platform_publish_counts.get(status_name, 0) + 1
                )

                recent_publish_results.append(
                    {
                        "job_id": result_dict.get("job_id"),
                        "platform": platform_name,
                        "publish_status": status_name,
                        "message": result_dict.get("message"),
                    }
                )

        sorted_publish_counts = [
            {"publish_status": key, "count": value}
            for key, value in sorted(
                platform_publish_counts.items(),
                key=lambda item: (-item[1], item[0]),
            )
        ]

        return {
            "job_publish_stats": job_publish_stats,
            "publish_result_counts": sorted_publish_counts,
            "recent_publish_results": recent_publish_results[:10],
        }

    def get_blocked_jobs(self, base_path: str = "exports") -> dict[str, object]:
        jobs = list(self.job_loader.load_all_jobs(base_path=base_path))
        blocked_jobs: list[dict[str, object]] = []

        for job in jobs:
            reasons: list[str] = []
            review_status = str(getattr(job, "review_status", "") or "").strip().lower()
            retry_status = str(getattr(job, "retry_status", "") or "").strip().lower()

            if review_status == "pending":
                reasons.append("review_pending")

            if bool(getattr(job, "permanently_failed", False)):
                reasons.append("permanently_failed")

            if retry_status == "scheduled_retry":
                reasons.append("retry_scheduled")

            export_path = self._build_export_path(base_path, job)

            guard_results = self.publish_guard_repository.load_results(export_path)
            guard_statuses = []
            for result in guard_results:
                result_dict = self._safe_to_dict(result)
                result_text = " ".join(
                    str(value).lower()
                    for value in result_dict.values()
                    if value is not None
                )
                if "block" in result_text:
                    reasons.append("publish_guard_blocked")
                    guard_statuses.append(result_dict)

            publish_results = self.publish_result_repository.load_results(export_path)
            publish_statuses = []
            for result in publish_results:
                result_dict = self._safe_to_dict(result)
                status_name = str(result_dict.get("publish_status") or "").strip().lower()
                if status_name == "blocked":
                    reasons.append("publish_blocked")
                publish_statuses.append(result_dict)

            reasons = sorted(set(reasons))

            if not reasons:
                continue

            card = build_review_card_data(job)
            blocked_jobs.append(
                {
                    "job_id": job.job_id,
                    "title": card["title"],
                    "channel": card["channel"],
                    "review_status": review_status or None,
                    "publish_status": str(getattr(job, "publish_status", "") or "").strip().lower() or None,
                    "reasons": reasons,
                    "guard_results": guard_statuses[:5],
                    "publish_results": publish_statuses[:5],
                }
            )

        return {
            "blocked_count": len(blocked_jobs),
            "blocked_jobs": blocked_jobs[:10],
        }

    def get_maintenance_status(
        self,
        *,
        base_path: str = "exports",
        rerender_queue_file: str = "data/rerender_queue.json",
        rerender_jobs_file: str = "data/rerender_jobs.json",
    ) -> dict[str, object]:
        report = self.maintenance_report_builder.build(
            exports_base_path=base_path,
            rerender_queue_file=rerender_queue_file,
            rerender_jobs_file=rerender_jobs_file,
        ).to_dict()

        integrity = dict(report.get("integrity") or {})
        recovery_plan = dict(report.get("recovery_plan") or {})
        retention_plan = dict(report.get("retention_plan") or {})

        integrity_issue_count = self._extract_generic_count(
            integrity,
            direct_keys=[
                "issue_count",
                "issues_count",
                "total_issues",
                "problem_count",
                "problems_count",
            ],
            list_keys=[
                "issues",
                "problems",
                "findings",
                "missing_jobs",
                "missing_files",
                "orphaned_exports",
                "orphaned_jobs",
            ],
        )

        recovery_action_count = self._extract_generic_count(
            recovery_plan,
            direct_keys=[
                "action_count",
                "planned_action_count",
                "recovery_action_count",
            ],
            list_keys=[
                "actions",
                "safe_actions",
                "planned_actions",
                "recovery_actions",
                "items",
            ],
        )

        retention_decision_count = self._extract_generic_count(
            retention_plan,
            direct_keys=[
                "decision_count",
                "planned_decision_count",
                "retention_decision_count",
            ],
            list_keys=[
                "decisions",
                "retention_decisions",
                "planned_actions",
                "items",
            ],
        )

        return {
            "integrity_issue_count": integrity_issue_count,
            "recovery_action_count": recovery_action_count,
            "retention_decision_count": retention_decision_count,
            "integrity": integrity,
            "recovery_plan": recovery_plan,
            "retention_plan": retention_plan,
        }

    def get_warning_cases(
        self,
        base_path: str = "exports",
        *,
        rerender_queue_file: str = "data/rerender_queue.json",
        rerender_jobs_file: str = "data/rerender_jobs.json",
    ) -> dict[str, object]:
        runtime_status = self.get_runtime_status()
        vacation_status = self.get_vacation_status()
        review_status = self.get_review_status(base_path=base_path)
        queue_status = self.get_queue_status()
        kpi_summary = self.get_kpi_summary(base_path=base_path)
        feedback_summary = self.get_feedback_summary(base_path=base_path)
        blocked_jobs = self.get_blocked_jobs(base_path=base_path)
        publish_status = self.get_publish_status(base_path=base_path)
        maintenance_status = self.get_maintenance_status(
            base_path=base_path,
            rerender_queue_file=rerender_queue_file,
            rerender_jobs_file=rerender_jobs_file,
        )

        warning_cases: list[dict[str, object]] = []

        if runtime_status["mode"] != "full_power":
            warning_cases.append(
                {
                    "type": "runtime_restricted",
                    "severity": "medium",
                    "summary": f"Runtime Mode ist {runtime_status['mode']}.",
                }
            )

        if vacation_status["is_active_now"]:
            warning_cases.append(
                {
                    "type": "vacation_active",
                    "severity": "medium",
                    "summary": "Vacation Mode ist aktuell aktiv.",
                }
            )

        if review_status["pending_count"] > 0:
            warning_cases.append(
                {
                    "type": "open_reviews",
                    "severity": "medium",
                    "summary": f"{review_status['pending_count']} Review-Fälle sind offen.",
                }
            )

        if queue_status["blocked_count"] > 0:
            warning_cases.append(
                {
                    "type": "blocked_queue_entries",
                    "severity": "medium",
                    "summary": f"{queue_status['blocked_count']} Queue-Einträge sind blockiert.",
                }
            )

        if blocked_jobs["blocked_count"] > 0:
            warning_cases.append(
                {
                    "type": "blocked_jobs",
                    "severity": "high",
                    "summary": f"{blocked_jobs['blocked_count']} Jobs sind aktuell blockiert.",
                }
            )

        if publish_status["job_publish_stats"]["permanently_failed_jobs"] > 0:
            warning_cases.append(
                {
                    "type": "publish_failures",
                    "severity": "high",
                    "summary": (
                        f"{publish_status['job_publish_stats']['permanently_failed_jobs']} Jobs "
                        f"sind dauerhaft fehlgeschlagen."
                    ),
                }
            )

        if maintenance_status["integrity_issue_count"] > 0:
            warning_cases.append(
                {
                    "type": "maintenance_integrity",
                    "severity": "high",
                    "summary": (
                        f"{maintenance_status['integrity_issue_count']} Integrity-Probleme "
                        f"wurden im Maintenance-Status erkannt."
                    ),
                }
            )

        if kpi_summary["loser_count"] > 0:
            warning_cases.append(
                {
                    "type": "kpi_losers",
                    "severity": "medium",
                    "summary": f"{kpi_summary['loser_count']} KPI-Loser wurden erkannt.",
                }
            )

        if feedback_summary["total_records"] == 0:
            warning_cases.append(
                {
                    "type": "missing_feedback",
                    "severity": "low",
                    "summary": "Noch keine Feedback-Daten vorhanden.",
                }
            )

        if kpi_summary["total_entries"] == 0:
            warning_cases.append(
                {
                    "type": "missing_kpi",
                    "severity": "low",
                    "summary": "Noch keine KPI-Daten vorhanden.",
                }
            )

        return {
            "warning_count": len(warning_cases),
            "warning_cases": warning_cases,
        }

    def get_system_status(
        self,
        base_path: str = "exports",
        *,
        rerender_queue_file: str = "data/rerender_queue.json",
        rerender_jobs_file: str = "data/rerender_jobs.json",
    ) -> dict[str, object]:
        runtime_status = self.get_runtime_status()
        vacation_status = self.get_vacation_status()
        review_status = self.get_review_status(base_path=base_path)
        queue_status = self.get_queue_status()
        kpi_summary = self.get_kpi_summary(base_path=base_path)
        feedback_summary = self.get_feedback_summary(base_path=base_path)
        blocked_jobs = self.get_blocked_jobs(base_path=base_path)
        publish_status = self.get_publish_status(base_path=base_path)
        maintenance_status = self.get_maintenance_status(
            base_path=base_path,
            rerender_queue_file=rerender_queue_file,
            rerender_jobs_file=rerender_jobs_file,
        )
        warning_cases = self.get_warning_cases(
            base_path=base_path,
            rerender_queue_file=rerender_queue_file,
            rerender_jobs_file=rerender_jobs_file,
        )

        warnings = [item["summary"] for item in warning_cases["warning_cases"]]

        return {
            "runtime_status": runtime_status,
            "vacation_status": vacation_status,
            "review_status": review_status,
            "queue_status": queue_status,
            "kpi_summary": kpi_summary,
            "feedback_summary": feedback_summary,
            "blocked_jobs": blocked_jobs,
            "publish_status": publish_status,
            "maintenance_status": maintenance_status,
            "warning_cases": warning_cases,
            "warnings": warnings,
        }

    def _build_export_path(self, base_path: str, job) -> str:
        channel_value = getattr(job.channel_type, "value", job.channel_type)
        return self.storage.join(base_path, str(channel_value), job.job_id)

    def _safe_to_dict(self, value) -> dict[str, object]:
        if hasattr(value, "to_dict"):
            payload = value.to_dict()
            if isinstance(payload, dict):
                return payload

        if isinstance(value, dict):
            return dict(value)

        raw_dict = getattr(value, "__dict__", None)
        if isinstance(raw_dict, dict):
            return dict(raw_dict)

        return {"value": str(value)}

    def _extract_platform_name(self, value) -> str | None:
        if value is None:
            return None

        if hasattr(value, "value"):
            return str(value.value)

        text = str(value)
        if "." in text:
            return text.split(".")[-1]
        return text

    def _enum_to_value(self, value) -> str:
        if hasattr(value, "value"):
            return str(value.value)
        return str(value)

    def _extract_generic_count(
        self,
        payload: dict[str, object],
        *,
        direct_keys: list[str],
        list_keys: list[str],
    ) -> int:
        for key in direct_keys:
            value = payload.get(key)
            if isinstance(value, int):
                return value

        total = 0

        for key in list_keys:
            value = payload.get(key)
            if isinstance(value, list):
                total += len(value)

        return total