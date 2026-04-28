from __future__ import annotations

from enum import Enum


class JarvisCommandType(str, Enum):
    SYSTEM_STATUS = "system_status"
    REVIEW_STATUS = "review_status"
    BLOCKED_JOBS = "blocked_jobs"
    WARNING_CASES = "warning_cases"
    QUEUE_STATUS = "queue_status"
    PUBLISH_STATUS = "publish_status"
    KPI_SUMMARY = "kpi_summary"
    WEAK_PLATFORMS = "weak_platforms"
    FEEDBACK_SUMMARY = "feedback_summary"
    RUNTIME_STATUS = "runtime_status"
    VACATION_STATUS = "vacation_status"
    MAINTENANCE_STATUS = "maintenance_status"
    UNKNOWN = "unknown"