from __future__ import annotations

from core.jarvis_command_parser import JarvisCommandParser
from core.jarvis_response_builder import JarvisResponseBuilder
from core.jarvis_status_service import JarvisStatusService
from models.jarvis_response import JarvisResponse
from shared.jarvis_enums import JarvisCommandType


class JarvisCommandService:
    def __init__(
        self,
        parser: JarvisCommandParser | None = None,
        status_service: JarvisStatusService | None = None,
        response_builder: JarvisResponseBuilder | None = None,
    ) -> None:
        self.parser = parser or JarvisCommandParser()
        self.status_service = status_service or JarvisStatusService()
        self.response_builder = response_builder or JarvisResponseBuilder()

    def handle_command(
        self,
        raw_text: str,
        *,
        base_path: str = "exports",
        rerender_queue_file: str = "data/rerender_queue.json",
        rerender_jobs_file: str = "data/rerender_jobs.json",
    ) -> JarvisResponse:
        command = self.parser.parse(raw_text)

        if command.command_type == JarvisCommandType.UNKNOWN:
            return self.response_builder.build_unknown_response(raw_text)

        if command.command_type == JarvisCommandType.SYSTEM_STATUS:
            payload = self.status_service.get_system_status(
                base_path=base_path,
                rerender_queue_file=rerender_queue_file,
                rerender_jobs_file=rerender_jobs_file,
            )
            runtime_status = payload["runtime_status"]
            vacation_status = payload["vacation_status"]
            review_status = payload["review_status"]
            queue_status = payload["queue_status"]
            kpi_summary = payload["kpi_summary"]
            feedback_summary = payload["feedback_summary"]
            maintenance_status = payload["maintenance_status"]

            return self.response_builder.build_simple_response(
                command_type=command.command_type,
                title="Zenith Systemstatus",
                summary=(
                    f"Runtime = {runtime_status['mode']}, "
                    f"Vacation aktiv = {vacation_status['is_active_now']}, "
                    f"offene Reviews = {review_status['pending_count']}, "
                    f"Queue-Einträge = {queue_status['total_entries']}, "
                    f"KPI-Einträge = {kpi_summary['total_entries']}, "
                    f"Feedback-Records = {feedback_summary['total_records']}."
                ),
                details=[
                    f"Runtime Last Change: {runtime_status['updated_at']}",
                    f"Vacation Effective Mode: {vacation_status['effective_mode']}",
                    f"Review Counts: pending={review_status['pending_count']}, approved={review_status['approved_count']}, rejected={review_status['rejected_count']}",
                    f"Queue: total={queue_status['total_entries']}, blocked={queue_status['blocked_count']}",
                    f"KPI Counts: winners={kpi_summary['winner_count']}, losers={kpi_summary['loser_count']}, outliers={kpi_summary['outlier_count']}",
                    f"Blocked Jobs: {payload['blocked_jobs']['blocked_count']}",
                    f"Warning Cases: {payload['warning_cases']['warning_count']}",
                    f"Maintenance Integrity Issues: {maintenance_status['integrity_issue_count']}",
                ],
                warnings=list(payload["warnings"]),
                evidence_sections=[
                    {"section": "runtime_status", "data": runtime_status},
                    {"section": "vacation_status", "data": vacation_status},
                    {"section": "review_status", "data": review_status},
                    {"section": "queue_status", "data": queue_status},
                    {"section": "kpi_summary", "data": kpi_summary},
                    {"section": "feedback_summary", "data": feedback_summary},
                    {"section": "blocked_jobs", "data": payload["blocked_jobs"]},
                    {"section": "publish_status", "data": payload["publish_status"]},
                    {"section": "maintenance_status", "data": maintenance_status},
                    {"section": "warning_cases", "data": payload["warning_cases"]},
                ],
                recommended_next_steps=[
                    "Prüfe offene Review-Fälle.",
                    "Prüfe Queue-Blocker, blockierte Jobs und Warnfälle.",
                    "Prüfe KPI-Loser, Feedback-Muster und Maintenance-Status.",
                ],
            )

        if command.command_type == JarvisCommandType.REVIEW_STATUS:
            payload = self.status_service.get_review_status(base_path=base_path)
            pending_reviews = list(payload["pending_reviews"])

            review_details = [
                f"{item['job_id']} | {item['title']} | Channel={item['channel']} | Score={item['final_score']} | Shorts={item['shorts_count']}"
                for item in pending_reviews[:5]
            ]

            return self.response_builder.build_simple_response(
                command_type=command.command_type,
                title="Review Status",
                summary=(
                    f"{payload['pending_count']} offene Reviews bei "
                    f"{payload['total_jobs']} Gesamtjobs."
                ),
                details=review_details or ["Keine offenen Review-Fälle gefunden."],
                warnings=[
                    f"{payload['pending_count']} Review-Fälle warten auf Entscheidung."
                ] if payload["pending_count"] > 0 else [],
                evidence_sections=[
                    {"section": "review_status", "data": payload},
                ],
                recommended_next_steps=[
                    "Offene Jobs im Dashboard prüfen und freigeben oder ablehnen.",
                ],
            )

        if command.command_type == JarvisCommandType.BLOCKED_JOBS:
            payload = self.status_service.get_blocked_jobs(base_path=base_path)

            details = [
                f"{item['job_id']} | {item['title']} | Channel={item['channel']} | Reasons={', '.join(item['reasons'])}"
                for item in payload["blocked_jobs"][:10]
            ]

            return self.response_builder.build_simple_response(
                command_type=command.command_type,
                title="Blocked Jobs",
                summary=f"{payload['blocked_count']} Jobs sind aktuell blockiert.",
                details=details or ["Keine blockierten Jobs gefunden."],
                warnings=[
                    f"{payload['blocked_count']} blockierte Jobs erkannt."
                ] if payload["blocked_count"] > 0 else [],
                evidence_sections=[
                    {"section": "blocked_jobs", "data": payload},
                ],
                recommended_next_steps=[
                    "Review-Pending, Guard-Blocker und Retry-Fälle prüfen.",
                ],
            )

        if command.command_type == JarvisCommandType.WARNING_CASES:
            payload = self.status_service.get_warning_cases(
                base_path=base_path,
                rerender_queue_file=rerender_queue_file,
                rerender_jobs_file=rerender_jobs_file,
            )

            details = [
                f"{item['severity']} | {item['type']} | {item['summary']}"
                for item in payload["warning_cases"]
            ]

            return self.response_builder.build_simple_response(
                command_type=command.command_type,
                title="Warnfälle",
                summary=f"{payload['warning_count']} Warnfälle erkannt.",
                details=details or ["Keine Warnfälle gefunden."],
                warnings=[item["summary"] for item in payload["warning_cases"]],
                evidence_sections=[
                    {"section": "warning_cases", "data": payload},
                ],
                recommended_next_steps=[
                    "Warnfälle nach severity priorisieren und abarbeiten.",
                ],
            )

        if command.command_type == JarvisCommandType.QUEUE_STATUS:
            payload = self.status_service.get_queue_status()

            details = [
                f"Queue State: {item['queue_state']} ({item['count']})"
                for item in payload["state_counts"]
            ]
            details.extend(
                [
                    f"Review State: {item['review_status']} ({item['count']})"
                    for item in payload["review_counts"]
                ]
            )
            details.extend(
                [
                    f"Top Queue Entry: {item['queue_entry_id']} | {item['topic_label']} | Score={item['opportunity_score']} | State={item['queue_state']}"
                    for item in payload["top_entries"][:5]
                ]
            )

            return self.response_builder.build_simple_response(
                command_type=command.command_type,
                title="Queue Status",
                summary=(
                    f"{payload['total_entries']} Queue-Einträge geladen, "
                    f"davon {payload['blocked_count']} blockiert."
                ),
                details=details or ["Keine Queue-Einträge vorhanden."],
                warnings=[
                    f"{payload['blocked_count']} Queue-Einträge sind blockiert."
                ] if payload["blocked_count"] > 0 else [],
                evidence_sections=[
                    {"section": "queue_status", "data": payload},
                ],
                recommended_next_steps=[
                    "Blockierte Queue-Einträge und Opportunity-Scores prüfen.",
                ],
            )

        if command.command_type == JarvisCommandType.PUBLISH_STATUS:
            payload = self.status_service.get_publish_status(base_path=base_path)
            job_stats = payload["job_publish_stats"]

            details = [
                f"Published Jobs: {job_stats['published_jobs']}",
                f"Scheduled Jobs: {job_stats['scheduled_jobs']}",
                f"Waiting For Review Jobs: {job_stats['waiting_for_review_jobs']}",
                f"Permanently Failed Jobs: {job_stats['permanently_failed_jobs']}",
                f"Retry Scheduled Jobs: {job_stats['retry_scheduled_jobs']}",
            ]

            for item in payload["publish_result_counts"][:5]:
                details.append(
                    f"Publish Result Status: {item['publish_status']} ({item['count']})"
                )

            return self.response_builder.build_simple_response(
                command_type=command.command_type,
                title="Publish Status",
                summary=(
                    f"Published={job_stats['published_jobs']}, "
                    f"Scheduled={job_stats['scheduled_jobs']}, "
                    f"WaitingReview={job_stats['waiting_for_review_jobs']}."
                ),
                details=details,
                warnings=[
                    f"{job_stats['permanently_failed_jobs']} Jobs sind dauerhaft fehlgeschlagen."
                ] if job_stats["permanently_failed_jobs"] > 0 else [],
                evidence_sections=[
                    {"section": "publish_status", "data": payload},
                ],
                recommended_next_steps=[
                    "Failed- und Waiting-For-Review-Fälle prüfen.",
                ],
            )

        if command.command_type == JarvisCommandType.KPI_SUMMARY:
            payload = self.status_service.get_kpi_summary(base_path=base_path)
            best_platform = payload["best_platform"]
            top_entry = payload["top_entry"]

            details = [
                f"Winner Count: {payload['winner_count']}",
                f"Loser Count: {payload['loser_count']}",
                f"Outlier Count: {payload['outlier_count']}",
            ]

            if best_platform:
                details.append(
                    f"Beste Plattform: {best_platform['platform']} | Ø Score={best_platform['average_score']}"
                )

            if top_entry:
                details.append(
                    f"Top Variant: {top_entry['variant_id']} | Platform={top_entry['target_platform']} | Score={top_entry['performance_score']}"
                )

            return self.response_builder.build_simple_response(
                command_type=command.command_type,
                title="KPI Summary",
                summary=(
                    f"{payload['total_entries']} KPI-Einträge geladen. "
                    f"Winners={payload['winner_count']}, Losers={payload['loser_count']}."
                ),
                details=details,
                warnings=[],
                evidence_sections=[
                    {"section": "kpi_summary", "data": payload},
                ],
                recommended_next_steps=[
                    "Top-Varianten verstärken und Low-Performer prüfen.",
                ],
            )

        if command.command_type == JarvisCommandType.WEAK_PLATFORMS:
            payload = self.status_service.get_weak_platforms(base_path=base_path)
            weakest_platform = payload["weakest_platform"]

            details = [
                f"{item['platform']} | Entries={item['entry_count']} | Ø Score={item['average_score']}"
                for item in payload["platforms"]
            ]

            summary = "Keine Plattformdaten vorhanden."
            warnings: list[str] = []

            if weakest_platform:
                summary = (
                    f"Schwächste Plattform aktuell: {weakest_platform['platform']} "
                    f"mit Ø Score {weakest_platform['average_score']}."
                )
                warnings.append(
                    f"Plattform mit niedrigster aktueller Durchschnittsleistung: {weakest_platform['platform']}."
                )

            return self.response_builder.build_simple_response(
                command_type=command.command_type,
                title="Weak Platforms",
                summary=summary,
                details=details or ["Keine Plattformdaten vorhanden."],
                warnings=warnings,
                evidence_sections=[
                    {"section": "weak_platforms", "data": payload},
                ],
                recommended_next_steps=[
                    "Schwächste Plattform mit Titeln, Hook und Packaging gegenprüfen.",
                ],
            )

        if command.command_type == JarvisCommandType.FEEDBACK_SUMMARY:
            payload = self.status_service.get_feedback_summary(base_path=base_path)

            details = [
                f"Top Category: {payload['top_category']['category']} ({payload['top_category']['count']})"
                for _ in [0]
                if payload["top_category"]
            ]

            if payload["top_direction"]:
                details.append(
                    f"Top Direction: {payload['top_direction']['direction']} ({payload['top_direction']['count']})"
                )

            if payload["top_pattern"]:
                details.append(
                    f"Top Pattern: {payload['top_pattern']['category']} | {payload['top_pattern']['direction']} | Count={payload['top_pattern']['item_count']}"
                )

            return self.response_builder.build_simple_response(
                command_type=command.command_type,
                title="Feedback Summary",
                summary=f"{payload['total_records']} Feedback-Records geladen.",
                details=details or ["Noch keine Feedback-Daten vorhanden."],
                warnings=[],
                evidence_sections=[
                    {"section": "feedback_summary", "data": payload},
                ],
                recommended_next_steps=[
                    "Wiederkehrende Feedback-Muster gegen KPI und Review abgleichen.",
                ],
            )

        if command.command_type == JarvisCommandType.RUNTIME_STATUS:
            payload = self.status_service.get_runtime_status()

            return self.response_builder.build_simple_response(
                command_type=command.command_type,
                title="Runtime Status",
                summary=(
                    f"Runtime Mode ist {payload['mode']} mit "
                    f"{payload['allowed_action_count']} erlaubten Aktionen."
                ),
                details=[
                    f"Last Change: {payload['updated_at']}",
                    f"Allowed Actions: {', '.join(payload['allowed_actions']) or '-'}",
                    f"Blocked Actions: {', '.join(payload['blocked_actions']) or '-'}",
                ],
                warnings=[],
                evidence_sections=[
                    {"section": "runtime_status", "data": payload},
                ],
                recommended_next_steps=[
                    "Bei blockierten Pipelines Runtime Mode prüfen.",
                ],
            )

        if command.command_type == JarvisCommandType.VACATION_STATUS:
            payload = self.status_service.get_vacation_status()

            return self.response_builder.build_simple_response(
                command_type=command.command_type,
                title="Vacation Status",
                summary=(
                    f"Vacation enabled = {payload['enabled']}, "
                    f"active_now = {payload['is_active_now']}, "
                    f"effective_mode = {payload['effective_mode']}."
                ),
                details=[
                    f"Start At: {payload['start_at'] or '-'}",
                    f"End At: {payload['end_at'] or '-'}",
                    f"Updated At: {payload['updated_at']}",
                ],
                warnings=[
                    "Vacation Mode ist aktuell live."
                ] if payload["is_active_now"] else [],
                evidence_sections=[
                    {"section": "vacation_status", "data": payload},
                ],
                recommended_next_steps=[
                    "Vacation Window und effective mode prüfen.",
                ],
            )

        if command.command_type == JarvisCommandType.MAINTENANCE_STATUS:
            payload = self.status_service.get_maintenance_status(
                base_path=base_path,
                rerender_queue_file=rerender_queue_file,
                rerender_jobs_file=rerender_jobs_file,
            )

            return self.response_builder.build_simple_response(
                command_type=command.command_type,
                title="Maintenance Status",
                summary=(
                    f"Integrity-Issues={payload['integrity_issue_count']}, "
                    f"Recovery-Actions={payload['recovery_action_count']}, "
                    f"Retention-Decisions={payload['retention_decision_count']}."
                ),
                details=[
                    f"Integrity Issue Count: {payload['integrity_issue_count']}",
                    f"Recovery Action Count: {payload['recovery_action_count']}",
                    f"Retention Decision Count: {payload['retention_decision_count']}",
                ],
                warnings=[
                    f"{payload['integrity_issue_count']} Maintenance-Integrity-Probleme erkannt."
                ] if payload["integrity_issue_count"] > 0 else [],
                evidence_sections=[
                    {"section": "maintenance_status", "data": payload},
                ],
                recommended_next_steps=[
                    "Integrity-Befunde, Recovery-Plan und Retention-Plan prüfen.",
                ],
            )

        return self.response_builder.build_recognized_but_unwired_response(
            command_type=command.command_type,
            raw_text=raw_text,
        )