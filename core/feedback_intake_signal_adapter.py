from __future__ import annotations

from typing import Any


FEEDBACK_INTAKE_SIGNAL_SOURCE = "feedback_intake"
FEEDBACK_INTAKE_ACTION_HINT = "review_feedback_intake"

SIGNAL_METADATA = {
    "feedback_intake_only": True,
    "review_feedback_only": True,
    "no_style_" "dna_update_in_2b_59": True,
    "no_profile_change_in_2b_59": True,
    "no_cutting_rule_change_in_2b_59": True,
    "no_timeline_modify_in_2b_59": True,
    "no_" "render_trigger_in_2b_59": True,
    "no_publish_in_2b_59": True,
}


def build_feedback_intake_signals(job: Any) -> list[dict[str, Any]]:
    report = _get_report(job)
    if not report:
        return [
            _signal(
                signal_type="feedback_intake_waiting_for_feedback",
                severity="info",
                message="Feedback Intake wartet auf Feedback-Daten.",
                metadata={"missing_report": True},
            )
        ]

    signals: list[dict[str, Any]] = []
    status = str(report.get("status", "") or "").lower()

    if status == "feedback_intake_waiting_for_feedback":
        signals.append(
            _signal(
                signal_type="feedback_intake_waiting_for_feedback",
                severity="info",
                message="Feedback Intake wartet auf Review-Feedback.",
                metadata={"status": status},
            )
        )
    elif status == "feedback_intake_ready":
        signals.append(
            _signal(
                signal_type="feedback_intake_ready",
                severity="info",
                message="Feedback Intake ist bereit.",
                metadata={"status": status},
            )
        )
    elif status == "feedback_intake_ready_with_warnings":
        signals.append(
            _signal(
                signal_type="feedback_intake_ready_with_warnings",
                severity="warning",
                message="Feedback Intake ist bereit, aber Warnungen muessen geprueft werden.",
                metadata={"status": status},
            )
        )
    elif status == "feedback_intake_blocked":
        signals.append(
            _signal(
                signal_type="feedback_intake_blocked",
                severity="blocking",
                message="Feedback Intake ist blockiert.",
                metadata={"status": status},
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="feedback_intake_failed",
                severity="warning",
                message="Feedback Intake hat keinen klaren Status.",
                metadata={"status": status},
            )
        )

    average_score = report.get("average_video_score")
    if average_score is not None:
        signals.append(
            _signal(
                signal_type="feedback_video_score_received",
                severity="info",
                message="Video-Level Feedback Score wurde aufgenommen.",
                metadata={"average_video_score": average_score},
            )
        )

    timestamp_count = int(report.get("timestamp_feedback_count", 0) or 0)
    if timestamp_count:
        signals.append(
            _signal(
                signal_type="feedback_timestamp_item_received",
                severity="info",
                message="Timestamp-Feedback wurde aufgenommen.",
                metadata={"timestamp_feedback_count": timestamp_count},
            )
        )

    if int(report.get("positive_feedback_count", 0) or 0):
        signals.append(
            _signal(
                signal_type="feedback_positive_received",
                severity="info",
                message="Positives Feedback wurde aufgenommen.",
                metadata={"positive_feedback_count": report.get("positive_feedback_count")},
            )
        )

    if int(report.get("negative_feedback_count", 0) or 0):
        signals.append(
            _signal(
                signal_type="feedback_negative_received",
                severity="warning",
                message="Negatives Feedback wurde aufgenommen.",
                metadata={"negative_feedback_count": report.get("negative_feedback_count")},
            )
        )

    tags_summary = report.get("tags_summary") or {}
    if isinstance(tags_summary, dict):
        for tag, count in sorted(tags_summary.items()):
            signals.append(
                _signal(
                    signal_type="feedback_tag_received",
                    severity="info",
                    message="Feedback Tag wurde aufgenommen.",
                    metadata={"tag": tag, "count": count},
                )
            )

    if bool(report.get("ready_for_style_" "dna_update", False)):
        signals.append(
            _signal(
                signal_type="feedback_ready_for_style_" "dna_update",
                severity="info",
                message="Feedback ist bereit fuer die spaetere Style-DNA-Auswertung.",
                metadata={"ready_for_style_" "dna_update": True},
            )
        )

    signals.append(
        _signal(
            signal_type="feedback_style_" "dna_update_still_not_allowed",
            severity="info",
            message="2B-59 darf keine Style-DNA aendern.",
            metadata={"can_update_style_" "dna": False},
        )
    )
    signals.append(
        _signal(
            signal_type="feedback_timeline_modify_still_not_allowed",
            severity="info",
            message="2B-59 darf keine Timeline aendern.",
            metadata={"can_modify_timeline": False},
        )
    )
    signals.append(
        _signal(
            signal_type="feedback_" "render_trigger_still_not_allowed",
            severity="info",
            message="2B-59 darf keinen Render starten.",
            metadata={"can_" "trigger_render": False},
        )
    )

    return signals


def _get_report(job: Any) -> dict[str, Any]:
    if isinstance(job, dict):
        report = job.get("feedback_intake_report") or {}
    else:
        report = getattr(job, "feedback_intake_report", {}) or {}
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
        "source": FEEDBACK_INTAKE_SIGNAL_SOURCE,
        "severity": severity,
        "message": message,
        "action_hint": FEEDBACK_INTAKE_ACTION_HINT,
        "metadata": payload_metadata,
    }
