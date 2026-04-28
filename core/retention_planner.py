from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def parse_datetime(value: Any) -> datetime | None:
    if value is None:
        return None

    text = str(value).strip()
    if not text:
        return None

    iso_candidate = text.replace("Z", "+00:00")

    try:
        parsed = datetime.fromisoformat(iso_candidate)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d %H:%M", "%d.%m.%Y %H:%M"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue

    return None


@dataclass(slots=True)
class RetentionDecision:
    scope: str
    reference_id: str
    retention_class: str
    action: str
    reason: str
    age_days: int | None
    requires_manual_review: bool


@dataclass(slots=True)
class RetentionPlan:
    decisions: list[RetentionDecision] = field(default_factory=list)

    def add_decision(
        self,
        *,
        scope: str,
        reference_id: str,
        retention_class: str,
        action: str,
        reason: str,
        age_days: int | None,
        requires_manual_review: bool,
    ) -> None:
        self.decisions.append(
            RetentionDecision(
                scope=scope,
                reference_id=reference_id,
                retention_class=retention_class,
                action=action,
                reason=reason,
                age_days=age_days,
                requires_manual_review=requires_manual_review,
            )
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "decisions": [
                {
                    "scope": item.scope,
                    "reference_id": item.reference_id,
                    "retention_class": item.retention_class,
                    "action": item.action,
                    "reason": item.reason,
                    "age_days": item.age_days,
                    "requires_manual_review": item.requires_manual_review,
                }
                for item in self.decisions
            ]
        }


class RetentionPlanner:
    def __init__(
        self,
        *,
        published_review_after_days: int = 30,
        failed_review_after_days: int = 7,
        rerender_done_review_after_days: int = 7,
        rerender_failed_review_after_days: int = 7,
    ) -> None:
        self.published_review_after_days = published_review_after_days
        self.failed_review_after_days = failed_review_after_days
        self.rerender_done_review_after_days = rerender_done_review_after_days
        self.rerender_failed_review_after_days = rerender_failed_review_after_days

    def build_plan(
        self,
        *,
        export_jobs: list[dict[str, Any]],
        rerender_jobs: list[dict[str, Any]],
        now: datetime | None = None,
    ) -> RetentionPlan:
        plan = RetentionPlan()
        effective_now = now or utc_now()

        for job in export_jobs:
            self._evaluate_export_job(job, plan, effective_now)

        for rerender_job in rerender_jobs:
            self._evaluate_rerender_job(rerender_job, plan, effective_now)

        return plan

    def _evaluate_export_job(
        self,
        job: dict[str, Any],
        plan: RetentionPlan,
        effective_now: datetime,
    ) -> None:
        job_id = str(job.get("job_id") or "unknown_job")
        publish_status = str(job.get("publish_status") or "")
        permanently_failed = bool(job.get("permanently_failed", False))
        review_status = str(job.get("review_status") or "")
        is_rerender = bool(job.get("is_rerender", False))

        published_at = parse_datetime(job.get("published_at"))
        updated_at = parse_datetime(job.get("updated_at"))
        created_at = parse_datetime(job.get("created_at"))

        reference_dt = published_at or updated_at or created_at
        age_days = self._compute_age_days(reference_dt, effective_now)

        if publish_status == "published" and age_days is not None and age_days >= self.published_review_after_days:
            plan.add_decision(
                scope="export_job",
                reference_id=job_id,
                retention_class="published_review_candidate",
                action="review_for_retention",
                reason="Veröffentlichter Job ist alt genug für Retention-Prüfung",
                age_days=age_days,
                requires_manual_review=True,
            )
            return

        if permanently_failed and age_days is not None and age_days >= self.failed_review_after_days:
            plan.add_decision(
                scope="export_job",
                reference_id=job_id,
                retention_class="failed_review_candidate",
                action="review_failed_artifacts",
                reason="Dauerhaft fehlgeschlagener Job ist alt genug für Cleanup-Prüfung",
                age_days=age_days,
                requires_manual_review=True,
            )
            return

        if is_rerender and review_status == "pending" and age_days is not None and age_days >= self.failed_review_after_days:
            plan.add_decision(
                scope="export_job",
                reference_id=job_id,
                retention_class="stale_rerender_review_candidate",
                action="review_stale_rerender_result",
                reason="Rerender-Ergebnis liegt lange ungeprüft im Review",
                age_days=age_days,
                requires_manual_review=True,
            )

    def _evaluate_rerender_job(
        self,
        job: dict[str, Any],
        plan: RetentionPlan,
        effective_now: datetime,
    ) -> None:
        rerender_job_id = str(job.get("rerender_job_id") or "unknown_rerender_job")
        status = str(job.get("status") or "")

        last_retry_at = parse_datetime(job.get("last_retry_at"))
        created_like = last_retry_at
        age_days = self._compute_age_days(created_like, effective_now)

        if status == "done" and age_days is not None and age_days >= self.rerender_done_review_after_days:
            plan.add_decision(
                scope="rerender_job",
                reference_id=rerender_job_id,
                retention_class="rerender_done_review_candidate",
                action="review_completed_rerender_record",
                reason="Abgeschlossener Rerender-Job ist alt genug für Listenbereinigung",
                age_days=age_days,
                requires_manual_review=True,
            )
            return

        if status in {"failed_runtime", "failed_missing_source"} and age_days is not None and age_days >= self.rerender_failed_review_after_days:
            plan.add_decision(
                scope="rerender_job",
                reference_id=rerender_job_id,
                retention_class="rerender_failed_review_candidate",
                action="review_failed_rerender_record",
                reason="Fehlgeschlagener Rerender-Job ist alt genug für Listenbereinigung",
                age_days=age_days,
                requires_manual_review=True,
            )

    def _compute_age_days(
        self,
        reference_dt: datetime | None,
        effective_now: datetime,
    ) -> int | None:
        if reference_dt is None:
            return None

        delta = effective_now - reference_dt
        return max(0, delta.days)