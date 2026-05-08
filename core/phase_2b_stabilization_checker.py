from __future__ import annotations

from pathlib import Path
from typing import Any

from models.phase_2b_final_review import Phase2BFinalReviewReport
from models.phase_2b_stabilization_result import (
    ENGINE,
    Phase2BStabilizationResult,
)
from models.universal_boundary_evidence import UniversalBoundaryEvidenceReport


class Phase2BStabilizationChecker:
    engine = ENGINE

    def check(
        self,
        *,
        job_id: str,
        job_dir: str | Path | None = None,
        export_dir: str | Path | None = None,
        timeline_segments=None,
        final_review_report=None,
        boundary_evidence_report=None,
        validator_result=None,
        render_path: str | Path | None = None,
    ) -> Phase2BStabilizationResult:
        job_id = str(job_id or "")
        paths = self._candidate_dirs(job_dir, export_dir)

        timeline, timeline_errors = self._timeline_state(timeline_segments)
        final_review = self._final_review_report(final_review_report)
        boundary_report = self._boundary_report(boundary_evidence_report)
        validator_state = self._validator_state(validator_result)

        final_review_segments = self._total(final_review, "segments", "total_segments")
        boundary_count = self._total(boundary_report, "boundaries", "total_boundaries")
        high_priority_reviews = self._int_attr(final_review, "high_priority_reviews")
        medium_priority_reviews = self._int_attr(final_review, "medium_priority_reviews")

        universal_moment_debug_exists = self._artifact_exists(
            paths, job_id, "universal_moment_debug.json"
        )
        universal_soft_decision_exists = self._artifact_exists(
            paths, job_id, "universal_moment_soft_decision.json"
        )
        universal_role_audit_exists = self._artifact_exists(
            paths, job_id, "universal_role_decision_audit.json"
        )
        universal_context_audit_exists = self._artifact_exists(
            paths, job_id, "universal_context_audit.json"
        )
        universal_boundary_evidence_exists = self._artifact_exists(
            paths, job_id, "universal_boundary_evidence.json"
        ) or boundary_count > 0
        final_review_exists = self._artifact_exists(
            paths, job_id, "phase_2b_final_review.json"
        ) or final_review_segments > 0
        review_markdown_exists = self._artifact_exists(
            paths, job_id, "universal_moment_review.md"
        )
        render_exists = self._render_exists(render_path, paths, job_id)
        export_exists = self._export_exists(render_path, paths, job_id)

        timeline_exists = len(timeline) > 0 and not timeline_errors
        segment_count_mismatch = self._segment_count_mismatch(
            len(timeline),
            final_review_segments,
        )
        high_boundary_review_warning = high_priority_reviews > 0
        transcript_boundary_precision_warning = self._transcript_precision_warning(
            boundary_report,
            high_priority_reviews,
        )
        missing_thumbnail_known_warning = validator_state["failed_only_thumbnail"]
        validator_failed_only_thumbnail = validator_state["failed_only_thumbnail"]

        notes: list[str] = []
        notes.extend(timeline_errors)
        if segment_count_mismatch:
            notes.append(
                "Final review segment count does not match the timeline closely enough."
            )
        if validator_state["failed_other"]:
            notes.append(f"Validator failed: {validator_state['reason']}")
        if render_path and render_exists and not self._has_export_mp4(paths, job_id):
            notes.append(
                "Final render exists; pipeline runner is responsible for copying the versioned export."
            )

        missing_artifacts = [
            name
            for name, exists in {
                "universal_moment_debug.json": universal_moment_debug_exists,
                "universal_moment_soft_decision.json": universal_soft_decision_exists,
                "universal_role_decision_audit.json": universal_role_audit_exists,
                "universal_context_audit.json": universal_context_audit_exists,
                "universal_boundary_evidence.json": universal_boundary_evidence_exists,
                "phase_2b_final_review.json": final_review_exists,
                "universal_moment_review.md": review_markdown_exists,
                "final mp4": export_exists,
            }.items()
            if not exists
        ]
        if missing_artifacts:
            notes.append("Missing Phase 2.B artifacts: " + ", ".join(missing_artifacts))

        critical_ok = (
            timeline_exists
            and render_exists
            and export_exists
            and final_review_exists
            and universal_moment_debug_exists
            and universal_soft_decision_exists
            and universal_role_audit_exists
            and universal_context_audit_exists
            and universal_boundary_evidence_exists
            and review_markdown_exists
            and not segment_count_mismatch
            and not validator_state["failed_other"]
        )

        known_open_items: list[str] = []
        if missing_thumbnail_known_warning:
            known_open_items.append(
                "Missing thumbnail remains a known Phase 2.C/package validation item."
            )
        if high_boundary_review_warning:
            known_open_items.append(
                "High-priority boundary reviews remain manual QA signals, not automatic cuts."
            )
        if transcript_boundary_precision_warning:
            known_open_items.append(
                "Transcript boundary precision can be improved later without changing Phase 2.B cuts."
            )

        warning_count = sum(
            [
                missing_thumbnail_known_warning,
                high_boundary_review_warning,
                transcript_boundary_precision_warning,
            ]
        )
        if critical_ok and warning_count:
            status = "passed_with_known_warnings"
        elif critical_ok:
            status = "passed"
        else:
            status = "failed"

        result = Phase2BStabilizationResult(
            job_id=job_id,
            status=status,
            timeline_exists=timeline_exists,
            render_exists=render_exists,
            export_exists=export_exists,
            final_review_exists=final_review_exists,
            universal_moment_debug_exists=universal_moment_debug_exists,
            universal_soft_decision_exists=universal_soft_decision_exists,
            universal_role_audit_exists=universal_role_audit_exists,
            universal_context_audit_exists=universal_context_audit_exists,
            universal_boundary_evidence_exists=universal_boundary_evidence_exists,
            review_markdown_exists=review_markdown_exists,
            validator_failed_only_thumbnail=validator_failed_only_thumbnail,
            timeline_segments=len(timeline),
            final_review_segments=final_review_segments,
            boundary_count=boundary_count,
            high_priority_reviews=high_priority_reviews,
            medium_priority_reviews=medium_priority_reviews,
            missing_thumbnail_known_warning=missing_thumbnail_known_warning,
            high_boundary_review_warning=high_boundary_review_warning,
            transcript_boundary_precision_warning=transcript_boundary_precision_warning,
            phase_2b_ready_to_close=critical_ok,
            next_phase_recommendation=self._next_phase_recommendation(critical_ok),
            known_open_items=known_open_items,
            notes=notes,
        )
        self._log(result)
        return result

    def write_markdown(
        self,
        *,
        result: Phase2BStabilizationResult,
        output_dir: str | Path,
        filename: str = "phase_2b_stabilization_review.md",
    ) -> Path:
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / filename
        path.write_text(self._markdown(result), encoding="utf-8")
        return path

    def _candidate_dirs(
        self,
        job_dir: str | Path | None,
        export_dir: str | Path | None,
    ) -> list[Path]:
        paths: list[Path] = []
        for raw in (export_dir, job_dir):
            if raw is None:
                continue
            path = Path(raw)
            if path not in paths:
                paths.append(path)
        return paths

    def _artifact_exists(self, paths: list[Path], job_id: str, filename: str) -> bool:
        prefixed = f"{job_id}_{filename}" if job_id else filename
        for directory in paths:
            if (directory / filename).exists() or (directory / prefixed).exists():
                return True
        return False

    def _render_exists(
        self,
        render_path: str | Path | None,
        paths: list[Path],
        job_id: str,
    ) -> bool:
        if render_path and Path(render_path).exists():
            return True
        if not job_id:
            return False
        return any((directory / f"{job_id}_final.mp4").exists() for directory in paths)

    def _export_exists(
        self,
        render_path: str | Path | None,
        paths: list[Path],
        job_id: str,
    ) -> bool:
        return self._has_export_mp4(paths, job_id) or (
            bool(render_path) and Path(render_path).exists()
        )

    def _has_export_mp4(self, paths: list[Path], job_id: str) -> bool:
        expected = f"{job_id}_final.mp4" if job_id else ""
        for directory in paths:
            if expected and (directory / expected).exists():
                return True
            try:
                if any(path.is_file() for path in directory.glob("*final*.mp4")):
                    return True
                if any(path.is_file() for path in directory.glob("*.mp4")):
                    return True
            except OSError:
                continue
        return False

    def _timeline_state(self, timeline_segments: Any) -> tuple[list[tuple[float, float]], list[str]]:
        raw_segments = self._raw_segments(timeline_segments)
        parsed: list[tuple[float, float]] = []
        errors: list[str] = []
        previous_start: float | None = None
        previous_end: float | None = None
        for index, segment in enumerate(raw_segments):
            start = self._float_value(segment, "start_time")
            end = self._float_value(segment, "end_time")
            if end <= start:
                errors.append(f"Timeline segment {index} has non-positive duration.")
            if previous_start is not None and start < previous_start - 0.001:
                errors.append(f"Timeline segment {index} starts before the previous segment.")
            if previous_end is not None and start < previous_end - 0.001:
                errors.append(f"Timeline segment {index} overlaps the previous segment.")
            parsed.append((start, end))
            previous_start = start
            previous_end = end
        if not parsed:
            errors.append("Timeline has no selected segments.")
        return parsed, errors

    def _raw_segments(self, timeline_segments: Any) -> list[Any]:
        if timeline_segments is None:
            return []
        if isinstance(timeline_segments, dict):
            if isinstance(timeline_segments.get("selected_segments"), list):
                return list(timeline_segments["selected_segments"])
            if isinstance(timeline_segments.get("segments"), list):
                return list(timeline_segments["segments"])
        selected = getattr(timeline_segments, "selected_segments", None)
        if selected is not None:
            return list(selected or [])
        try:
            return list(timeline_segments or [])
        except TypeError:
            return []

    def _float_value(self, item: Any, key: str) -> float:
        raw = item.get(key, 0.0) if isinstance(item, dict) else getattr(item, key, 0.0)
        try:
            return round(float(raw), 3)
        except (TypeError, ValueError):
            return 0.0

    def _final_review_report(self, report: Any) -> Phase2BFinalReviewReport | None:
        if report is None:
            return None
        if isinstance(report, Phase2BFinalReviewReport):
            return report
        if isinstance(report, dict):
            return Phase2BFinalReviewReport.from_dict(report)
        if hasattr(report, "to_dict"):
            return Phase2BFinalReviewReport.from_dict(report.to_dict())
        return None

    def _boundary_report(self, report: Any) -> UniversalBoundaryEvidenceReport | None:
        if report is None:
            return None
        if isinstance(report, UniversalBoundaryEvidenceReport):
            return report
        if isinstance(report, dict):
            return UniversalBoundaryEvidenceReport.from_dict(report)
        if hasattr(report, "to_dict"):
            return UniversalBoundaryEvidenceReport.from_dict(report.to_dict())
        return None

    def _total(self, report: Any, list_name: str, total_name: str) -> int:
        if report is None:
            return 0
        total = self._int_attr(report, total_name)
        if total:
            return total
        return len(getattr(report, list_name, []) or [])

    def _int_attr(self, item: Any, name: str) -> int:
        if item is None:
            return 0
        raw = item.get(name, 0) if isinstance(item, dict) else getattr(item, name, 0)
        try:
            return max(0, int(raw or 0))
        except (TypeError, ValueError):
            return 0

    def _segment_count_mismatch(self, timeline_count: int, review_count: int) -> bool:
        if timeline_count <= 0 or review_count <= 0:
            return False
        tolerance = max(1, round(timeline_count * 0.1))
        return abs(timeline_count - review_count) > tolerance

    def _transcript_precision_warning(
        self,
        boundary_report: UniversalBoundaryEvidenceReport | None,
        high_priority_reviews: int,
    ) -> bool:
        if boundary_report is None or boundary_report.total_boundaries <= 0:
            return False
        return any(
            [
                high_priority_reviews > 0,
                boundary_report.real_high > 0,
                boundary_report.real_word_cut > 0,
                boundary_report.real_sentence_cut > 0,
                boundary_report.likely_speech_cut > 0,
                boundary_report.timestamp_uncertain > 0,
            ]
        )

    def _validator_state(self, validator_result: Any) -> dict[str, Any]:
        if validator_result is None:
            return {
                "failed": False,
                "failed_only_thumbnail": False,
                "failed_other": False,
                "reason": "validator not provided",
            }
        if isinstance(validator_result, dict):
            status = str(validator_result.get("validator_status", validator_result.get("status", "")))
            reason = str(validator_result.get("reason", ""))
            issues = list(validator_result.get("blocking_issues") or [])
        else:
            status = str(
                getattr(
                    validator_result,
                    "validator_status",
                    getattr(validator_result, "status", ""),
                )
            )
            reason = str(getattr(validator_result, "reason", ""))
            issues = list(getattr(validator_result, "blocking_issues", []) or [])

        text_parts = [reason, *[str(issue) for issue in issues]]
        combined = " ; ".join(part for part in text_parts if part)
        failed = status.lower() in {"failed", "fail", "error"} or bool(issues)
        non_thumbnail_issues = [
            part
            for part in text_parts
            if part and "missing thumbnail" not in part.lower()
        ]
        failed_only_thumbnail = (
            failed
            and "missing thumbnail" in combined.lower()
            and not non_thumbnail_issues
        )
        return {
            "failed": failed,
            "failed_only_thumbnail": failed_only_thumbnail,
            "failed_other": failed and not failed_only_thumbnail,
            "reason": combined or "not provided",
        }

    def _next_phase_recommendation(self, ready: bool) -> str:
        if ready:
            return (
                "Proceed to Phase 2.C packaging/thumbnail validation while preserving "
                "Phase 2.B diagnostics."
            )
        return "Do not close Phase 2.B until failed stabilization checks are resolved."

    def _markdown(self, result: Phase2BStabilizationResult) -> str:
        warnings = result.known_open_items or ["none"]
        notes = result.notes or ["none"]
        lines = [
            "# Phase 2.B Stabilization",
            "",
            f"- Job-ID: {result.job_id or 'unknown'}",
            f"- Status: {result.status}",
            f"- Ready to Close: {self._yes_no(result.phase_2b_ready_to_close)}",
            f"- Timeline Segments: {result.timeline_segments}",
            f"- Final Review Segments: {result.final_review_segments}",
            f"- Boundary Count: {result.boundary_count}",
            f"- High Priority Reviews: {result.high_priority_reviews}",
            f"- Medium Priority Reviews: {result.medium_priority_reviews}",
            "",
            "## Artifacts",
            f"- Timeline: {self._yes_no(result.timeline_exists)}",
            f"- Render: {self._yes_no(result.render_exists)}",
            f"- Export: {self._yes_no(result.export_exists)}",
            f"- Final Review: {self._yes_no(result.final_review_exists)}",
            f"- Universal Moment Debug: {self._yes_no(result.universal_moment_debug_exists)}",
            f"- Universal Soft Decision: {self._yes_no(result.universal_soft_decision_exists)}",
            f"- Universal Role Audit: {self._yes_no(result.universal_role_audit_exists)}",
            f"- Universal Context Audit: {self._yes_no(result.universal_context_audit_exists)}",
            f"- Universal Boundary Evidence: {self._yes_no(result.universal_boundary_evidence_exists)}",
            f"- Review Markdown: {self._yes_no(result.review_markdown_exists)}",
            "",
            "## Known Warnings",
            f"- Missing Thumbnail: {self._yes_no(result.missing_thumbnail_known_warning)}",
            f"- High Boundary Review: {self._yes_no(result.high_boundary_review_warning)}",
            f"- Transcript Boundary Precision: {self._yes_no(result.transcript_boundary_precision_warning)}",
            "",
            "## Open Items",
            *[f"- {item}" for item in warnings],
            "",
            "## Next Phase Recommendation",
            f"- {result.next_phase_recommendation or 'none'}",
            "",
            "## Notes",
            *[f"- {item}" for item in notes],
            "",
        ]
        return "\n".join(lines)

    def _yes_no(self, value: bool) -> str:
        return "yes" if value else "no"

    def _log(self, result: Phase2BStabilizationResult) -> None:
        artifact_total = 8
        artifact_passed = sum(
            [
                result.universal_moment_debug_exists,
                result.universal_soft_decision_exists,
                result.universal_role_audit_exists,
                result.universal_context_audit_exists,
                result.universal_boundary_evidence_exists,
                result.final_review_exists,
                result.review_markdown_exists,
                result.export_exists,
            ]
        )
        warning_count = sum(
            [
                result.missing_thumbnail_known_warning,
                result.high_boundary_review_warning,
                result.transcript_boundary_precision_warning,
            ]
        )
        print(
            "[PHASE-2B-STABILIZATION] "
            f"status={result.status} "
            f"ready={str(result.phase_2b_ready_to_close).lower()} "
            f"artifacts={artifact_passed}/{artifact_total} "
            f"timeline_segments={result.timeline_segments} "
            f"final_review_segments={result.final_review_segments} "
            f"warnings={warning_count}"
        )
