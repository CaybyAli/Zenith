from __future__ import annotations

from typing import Any


LEARNING_PATTERN_SIGNAL_SOURCE = "learning_pattern_recognition"
LEARNING_PATTERN_ACTION_HINT = "review_learning_pattern_recognition"

SIGNAL_METADATA = {
    "learning_pattern_recognition_only": True,
    "feedback_trend_analysis_only": True,
    "no_style_dna_file_write_in_2b_64": True,
    "no_profile_change_in_2b_64": True,
    "no_cutting_rule_activation_in_2b_64": True,
    "no_timeline_modify_in_2b_64": True,
    "no_render_trigger_in_2b_64": True,
    "no_publish_in_2b_64": True,
}


def build_learning_pattern_recognition_signals(job: Any) -> list[dict[str, Any]]:
    report = _get_report(job)
    if not report:
        return [
            _signal(
                signal_type="learning_pattern_waiting_for_feedback",
                severity="info",
                message="Learning Pattern Recognition wartet auf Feedback-Daten.",
                metadata={"missing_report": True},
            )
        ]

    signals: list[dict[str, Any]] = []
    status = str(report.get("status", "") or "").lower()

    status_severity = {
        "learning_pattern_waiting_for_feedback": "info",
        "learning_pattern_ready": "info",
        "learning_pattern_ready_with_warnings": "warning",
        "learning_pattern_blocked": "blocking",
        "learning_pattern_failed": "warning",
    }.get(status, "warning")

    signals.append(
        _signal(
            signal_type=status or "learning_pattern_failed",
            severity=status_severity,
            message=f"Learning Pattern Recognition Status: {status or 'unknown'}.",
            metadata={"status": status},
        )
    )

    for trend in list(report.get("trends") or []):
        if not isinstance(trend, dict):
            continue
        trend_type = str(trend.get("trend_type") or "")
        signal_type = "learning_pattern_trend_detected"
        if trend_type == "repeated_issue":
            signal_type = "learning_pattern_repeated_issue_detected"
        elif trend_type == "repeated_success":
            signal_type = "learning_pattern_repeated_success_detected"
        elif trend_type == "mixed_signal":
            signal_type = "learning_pattern_mixed_signal_detected"

        signals.append(
            _signal(
                signal_type=signal_type,
                severity=str(trend.get("severity") or "info"),
                message=(
                    "Learning Pattern Trend erkannt: "
                    f"{trend.get('tag') or trend.get('category') or trend.get('trend_id')}."
                ),
                metadata={
                    "trend_id": trend.get("trend_id"),
                    "trend_type": trend_type,
                    "tag": trend.get("tag"),
                    "category": trend.get("category"),
                    "occurrence_count": trend.get("occurrence_count", 0),
                    "confidence": trend.get("confidence", 0.0),
                },
            )
        )

    for cluster in list(report.get("clusters") or []):
        if not isinstance(cluster, dict):
            continue
        signals.append(
            _signal(
                signal_type="learning_pattern_cluster_detected",
                severity=(
                    "warning"
                    if cluster.get("overfitting_risk") == "high"
                    else "info"
                ),
                message=f"Learning Pattern Cluster erkannt: {cluster.get('cluster_type')}.",
                metadata={
                    "cluster_id": cluster.get("cluster_id"),
                    "cluster_type": cluster.get("cluster_type"),
                    "source_tags": list(cluster.get("source_tags") or []),
                    "affected_parameters": list(
                        cluster.get("affected_parameters") or []
                    ),
                    "confidence": cluster.get("confidence", 0.0),
                    "overfitting_risk": cluster.get("overfitting_risk"),
                    "safe_to_use_for_future_proposal": bool(
                        cluster.get("safe_to_use_for_future_proposal", False)
                    ),
                },
            )
        )

    if str(report.get("overfitting_risk") or "") in {"medium", "high"}:
        signals.append(
            _signal(
                signal_type="learning_pattern_overfitting_risk_detected",
                severity=(
                    "warning"
                    if report.get("overfitting_risk") == "high"
                    else "info"
                ),
                message="Learning Pattern Overfitting Risk wurde erkannt.",
                metadata={"overfitting_risk": report.get("overfitting_risk")},
            )
        )

    if bool(report.get("ready_for_future_style_dna_proposal", False)):
        signals.append(
            _signal(
                signal_type="learning_pattern_ready_for_future_style_dna_proposal",
                severity="info",
                message="Learning Pattern ist nur fuer spaetere Style-DNA-Vorschlaege bereit.",
                metadata={"ready_for_future_style_dna_proposal": True},
            )
        )

    signals.extend(
        [
            _signal(
                signal_type="learning_pattern_style_dna_update_still_not_allowed",
                severity="info",
                message="2B-64 darf Style-DNA nicht aktualisieren.",
                metadata={"can_update_style_dna": False},
            ),
            _signal(
                signal_type="learning_pattern_profile_change_still_not_allowed",
                severity="info",
                message="2B-64 darf kein Profil aendern.",
                metadata={"can_change_profile": False},
            ),
            _signal(
                signal_type="learning_pattern_timeline_modify_still_not_allowed",
                severity="info",
                message="2B-64 darf keine Timeline aendern.",
                metadata={"can_modify_timeline": False},
            ),
            _signal(
                signal_type="learning_pattern_render_trigger_still_not_allowed",
                severity="info",
                message="2B-64 darf keinen Render ausloesen.",
                metadata={"can_trigger_render": False},
            ),
        ]
    )

    return signals


def _get_report(job: Any) -> dict[str, Any]:
    if isinstance(job, dict):
        report = job.get("learning_pattern_recognition_report") or {}
    else:
        report = getattr(job, "learning_pattern_recognition_report", {}) or {}
    return report if isinstance(report, dict) else {}


def _signal(
    *,
    signal_type: str,
    severity: str,
    message: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload_metadata = dict(SIGNAL_METADATA)
    payload_metadata.update(metadata or {})
    return {
        "signal_type": signal_type,
        "source": LEARNING_PATTERN_SIGNAL_SOURCE,
        "severity": severity,
        "message": message,
        "action_hint": LEARNING_PATTERN_ACTION_HINT,
        "metadata": payload_metadata,
    }
