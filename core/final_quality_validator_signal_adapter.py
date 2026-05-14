from __future__ import annotations

from typing import Any, Dict, List


FINAL_QUALITY_SIGNAL_SOURCE = "final_quality_validator"
FINAL_QUALITY_ACTION_HINT = "review_final_quality"


SIGNAL_METADATA = {
    "review_only": True,
    "media_unchanged": True,
    "no_execution_in_2b_43": True,
    "no_render_in_2b_43": True,
    "no_timeline_reorder_in_2b_43": True,
    "no_quality_fix_apply_in_2b_43": True,
}


def build_final_quality_validator_signals(job: Any) -> List[Dict[str, Any]]:
    report = _get_report(job)
    if not report:
        return [
            _signal(
                signal_type="final_quality_failed",
                severity="warning",
                message="Final Quality Report fehlt.",
                metadata={"missing_report": True},
            )
        ]

    signals: List[Dict[str, Any]] = []
    status = str(report.get("status", "")).lower()

    if status == "final_quality_blocked":
        signals.append(
            _signal(
                signal_type="final_quality_blocked",
                severity="blocking",
                message="Final Quality Validator blockiert die Timeline f?r Review.",
                metadata={"status": status},
            )
        )
    elif status == "final_quality_ready_with_warnings":
        signals.append(
            _signal(
                signal_type="final_quality_ready_with_warnings",
                severity="warning",
                message="Final Quality Validator ist bereit, aber mit Warnungen.",
                metadata={"status": status},
            )
        )
    elif status == "final_quality_ready":
        signals.append(
            _signal(
                signal_type="final_quality_ready",
                severity="info",
                message="Final Quality Validator ist bereit.",
                metadata={"status": status},
            )
        )
    else:
        signals.append(
            _signal(
                signal_type="final_quality_failed",
                severity="warning",
                message="Final Quality Validator hat keinen klaren Ready-Status.",
                metadata={"status": status},
            )
        )

    for check in report.get("checks", []):
        signals.extend(_signals_for_check(check))

    return signals


def _signals_for_check(check: Dict[str, Any]) -> List[Dict[str, Any]]:
    status = str(check.get("status", "")).lower()
    category = str(check.get("category", "")).lower()
    check_id = str(check.get("check_id", "")).lower()
    message = str(check.get("message", ""))

    if status not in {"warning", "blocked"}:
        return []

    severity = "blocking" if status == "blocked" else "warning"
    signals: List[Dict[str, Any]] = []

    if category == "audio":
        signals.append(_signal("final_quality_audio_warning", severity, message, {"check_id": check_id}))
    elif category == "video":
        signals.append(_signal("final_quality_video_warning", severity, message, {"check_id": check_id}))
    elif category == "story":
        signals.append(_signal("final_quality_story_warning", severity, message, {"check_id": check_id}))
    elif category == "pacing":
        signals.append(_signal("final_quality_pacing_warning", severity, message, {"check_id": check_id}))
    elif category == "safety":
        signals.append(_signal("final_quality_safety_blocked", severity, message, {"check_id": check_id}))

    specific_type = _specific_signal_type(check_id)
    if specific_type:
        signals.append(_signal(specific_type, severity, message, {"check_id": check_id}))

    return signals


def _specific_signal_type(check_id: str) -> str:
    mapping = {
        "hook_score_strong": "final_quality_hook_weak",
        "emotional_arc_deviation": "final_quality_arc_deviation",
        "pacing_not_monotone": "final_quality_pacing_monotone",
        "breathing_room_present": "final_quality_missing_breathing_room",
        "reaction_shots_reviewed": "final_quality_reaction_placeholder",
        "but_therefore_ratio": "final_quality_weak_story_ratio",
        "no_render_permission": "final_quality_render_not_allowed",
        "no_execution_permission": "final_quality_execution_not_allowed",
    }
    return mapping.get(check_id, "")


def _signal(
    signal_type: str,
    severity: str,
    message: str,
    metadata: Dict[str, Any],
) -> Dict[str, Any]:
    merged_metadata = dict(SIGNAL_METADATA)
    merged_metadata.update(metadata)
    return {
        "source": FINAL_QUALITY_SIGNAL_SOURCE,
        "signal_type": signal_type,
        "type": signal_type,
        "severity": severity,
        "message": message,
        "action_hint": FINAL_QUALITY_ACTION_HINT,
        "metadata": merged_metadata,
    }


def _get_report(job: Any) -> Dict[str, Any]:
    if isinstance(job, dict):
        report = job.get("final_quality_validation_report") or job.get("final_quality_validator")
    else:
        report = getattr(job, "final_quality_validation_report", None) or getattr(job, "final_quality_validator", None)

    if isinstance(report, dict):
        return report

    if hasattr(report, "to_dict"):
        return report.to_dict()

    return {}
