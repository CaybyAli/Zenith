from __future__ import annotations

from typing import Any

from core.style_dna_persistence_gate import build_style_dna_persistence_gate_report


class StyleDNAPersistenceGateRunner:
    def run(self, job: Any) -> dict[str, Any]:
        report = build_style_dna_persistence_gate_report(job)
        gate = dict(report.get("gate") or {})
        write_intent = dict(gate.get("write_intent") or {})

        _assign(job, "style_dna_persistence_gate_report", report)
        _assign(job, "style_dna_persistence_gate", gate)
        _assign(job, "style_dna_persistence_status", report.get("status"))

        _assign(
            job,
            "style_dna_persistence_requested_status",
            gate.get("requested_status") or _get(
                job,
                "style_dna_persistence_requested_status",
                "pending_write_review",
            ),
        )
        _assign(job, "style_dna_persistence_approved_by", gate.get("approved_by"))
        _assign(job, "style_dna_persistence_comment", gate.get("comment"))

        _assign(job, "style_dna_persistence_write_intent", write_intent)
        _assign(
            job,
            "style_dna_persistence_write_preview_hash",
            write_intent.get("write_preview_hash"),
        )
        _assign(
            job,
            "style_dna_persistence_target_path_hint",
            write_intent.get("target_path_hint"),
        )
        _assign(
            job,
            "style_dna_persistence_backup_required",
            bool(write_intent.get("backup_required", True)),
        )

        _assign(
            job,
            "style_dna_persistence_write_permission_ready_for_future",
            bool(report.get("write_permission_ready_for_future", False)),
        )

        _assign(job, "style_dna_persistence_can_write_style_dna", False)
        _assign(job, "style_dna_persistence_can_apply_style_dna", False)
        _assign(job, "style_dna_persistence_can_update_profile", False)
        _assign(job, "style_dna_persistence_can_change_cutting_rules", False)
        _assign(job, "style_dna_persistence_can_modify_timeline", False)
        _assign(job, "style_dna_persistence_can_trigger_render", False)
        _assign(job, "style_dna_persistence_can_publish", False)

        _assign(
            job,
            "style_dna_persistence_warnings",
            list(report.get("warnings") or []),
        )
        _assign(
            job,
            "style_dna_persistence_blocking_reasons",
            list(report.get("blocking_reasons") or []),
        )
        _assign(
            job,
            "style_dna_persistence_recommendation",
            report.get("recommendation"),
        )

        return report


def run_style_dna_persistence_gate_for_job(job: Any) -> dict[str, Any]:
    return StyleDNAPersistenceGateRunner().run(job)


def _assign(job: Any, key: str, value: Any) -> None:
    if isinstance(job, dict):
        job[key] = value
        return
    setattr(job, key, value)


def _get(job: Any, key: str, default: Any = None) -> Any:
    if isinstance(job, dict):
        return job.get(key, default)
    return getattr(job, key, default)
