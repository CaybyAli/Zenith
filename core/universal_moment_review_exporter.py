from __future__ import annotations

from pathlib import Path
from typing import Any

from models.universal_moment_debug_report import (
    UniversalMomentDebugReport,
    UniversalMomentSegmentDebug,
)
from models.universal_moment_soft_decision import (
    UniversalMomentSegmentDecision,
    UniversalMomentSoftDecisionReport,
)


class UniversalMomentReviewExporter:
    def write_report(
        self,
        *,
        report,
        output_dir: str | Path,
        filename: str = "universal_moment_review.md",
        soft_decision_report=None,
    ) -> Path:
        parsed_report = self._report(report)
        parsed_soft_report = self._soft_report(soft_decision_report)
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        output_path = target_dir / filename
        output_path.write_text(
            self._markdown(parsed_report, parsed_soft_report),
            encoding="utf-8",
        )
        return output_path

    def _report(self, report: Any) -> UniversalMomentDebugReport:
        if isinstance(report, UniversalMomentDebugReport):
            return report
        if isinstance(report, dict):
            return UniversalMomentDebugReport.from_dict(report)
        if hasattr(report, "to_dict"):
            return UniversalMomentDebugReport.from_dict(report.to_dict())
        return UniversalMomentDebugReport()

    def _soft_report(self, report: Any) -> UniversalMomentSoftDecisionReport | None:
        if report is None:
            return None
        if isinstance(report, UniversalMomentSoftDecisionReport):
            return report
        if isinstance(report, dict):
            return UniversalMomentSoftDecisionReport.from_dict(report)
        if hasattr(report, "to_dict"):
            return UniversalMomentSoftDecisionReport.from_dict(report.to_dict())
        return None

    def _markdown(
        self,
        report: UniversalMomentDebugReport,
        soft_decision_report: UniversalMomentSoftDecisionReport | None = None,
    ) -> str:
        lines: list[str] = [
            "# Universal Moment Review",
            "",
            f"- Job-ID: {report.job_id or 'unknown'}",
            "",
            "## Summary",
            f"- total_segments: {report.total_segments}",
            f"- keep: {report.segments_with_keep_signal}",
            f"- remove: {report.segments_with_remove_signal}",
            f"- confirmed_cut_risk: {report.segments_with_cut_risk}",
            f"- zoom_risk: {report.segments_with_zoom_risk}",
            f"- private: {report.segments_with_private_risk}",
            f"- avg score: {report.avg_segment_moment_score:.3f}",
            "",
        ]

        if soft_decision_report is not None:
            lines.extend(
                [
                    "## Soft Decision Summary",
                    f"- safe_keep: {soft_decision_report.safe_keep}",
                    f"- keep_dominant: {soft_decision_report.keep_dominant}",
                    f"- trim_edges_candidate: {soft_decision_report.trim_edges_candidate}",
                    f"- remove_dominant: {soft_decision_report.remove_dominant}",
                    f"- needs_human_review: {soft_decision_report.needs_human_review}",
                    f"- avg_conflict_score: {soft_decision_report.avg_conflict_score:.3f}",
                    "",
                ]
            )

        decisions_by_id = self._soft_by_id(soft_decision_report)
        for index, segment in enumerate(report.segments, start=1):
            lines.extend(
                self._segment_lines(
                    index,
                    segment,
                    decisions_by_id.get(segment.segment_id),
                )
            )

        return "\n".join(lines).rstrip() + "\n"

    def _segment_lines(
        self,
        index: int,
        segment: UniversalMomentSegmentDebug,
        soft_decision: UniversalMomentSegmentDecision | None = None,
    ) -> list[str]:
        time_range = f"{self._time(segment.start_time)}-{self._time(segment.end_time)}"
        top_types = self._type_counts(segment.top_moment_types)
        diagnosis = segment.diagnosis or ["none"]
        notes = segment.segment_notes or ["none"]

        lines = [
            f"## Segment {index:02d} -- {time_range}",
            f"- Role: {segment.segment_role}",
            f"- Duration: {segment.duration_seconds:.2f}s",
            f"- Verdict: {segment.professional_verdict}",
            f"- Reason: {segment.professional_reason or 'none'}",
            f"- Dominant Type: {segment.dominant_moment_type}",
            f"- Top Moment Types: {top_types}",
            "- Scores:",
            f"  - peak: {segment.avg_peak_score:.3f}",
            f"  - tension: {segment.avg_tension_score:.3f}",
            f"  - speech: {segment.avg_speech_score:.3f}",
            f"  - private: {segment.avg_private_talk_score:.3f}",
            f"  - boring: {segment.avg_boring_score:.3f}",
            f"  - cut risk: {segment.avg_cut_risk_score:.3f}",
            f"  - raw cut risk: {segment.raw_cut_risk_score:.3f}",
            f"  - zoom risk: {segment.avg_zoom_risk_score:.3f}",
            "- Flags:",
            f"  - keep: {self._yes_no(segment.has_keep_signal)}",
            f"  - remove: {self._yes_no(segment.has_remove_signal)}",
            f"  - cut: {self._yes_no(segment.has_cut_risk)}",
            f"  - confirmed_cut_risk_windows: {segment.confirmed_cut_risk_windows}",
            f"  - raw_cut_risk_windows: {segment.raw_cut_risk_windows}",
            f"  - zoom: {self._yes_no(segment.has_zoom_risk)}",
            f"  - private: {self._yes_no(segment.has_private_menu_risk)}",
            f"  - pre: {self._yes_no(segment.has_pre_context_need)}",
            f"  - post: {self._yes_no(segment.has_post_context_need)}",
        ]
        if soft_decision is not None:
            lines.extend(self._soft_decision_lines(soft_decision))
        lines.extend(
            [
                "- Diagnosis:",
                *[f"  - {item}" for item in diagnosis],
                "- Segment Notes:",
                *[f"  - {item}" for item in notes],
                "",
            ]
        )
        return lines

    def _soft_decision_lines(
        self,
        decision: UniversalMomentSegmentDecision,
    ) -> list[str]:
        reasons = decision.reasons or ["none"]
        warnings = decision.warnings or ["none"]
        return [
            "- Soft Decision:",
            f"  - Decision: {decision.soft_decision}",
            f"  - Keep Confidence: {decision.keep_confidence:.3f}",
            f"  - Remove Confidence: {decision.remove_confidence:.3f}",
            f"  - Trim Confidence: {decision.trim_confidence:.3f}",
            f"  - Review Confidence: {decision.review_confidence:.3f}",
            f"  - Conflict Score: {decision.conflict_score:.3f}",
            f"  - Should Not Auto Remove: {self._yes_no(decision.should_not_auto_remove)}",
            "  - Reasons:",
            *[f"    - {item}" for item in reasons],
            "  - Warnings:",
            *[f"    - {item}" for item in warnings],
        ]

    def _soft_by_id(
        self,
        soft_decision_report: UniversalMomentSoftDecisionReport | None,
    ) -> dict[str, UniversalMomentSegmentDecision]:
        if soft_decision_report is None:
            return {}
        return {
            decision.segment_id: decision
            for decision in soft_decision_report.decisions
            if decision.segment_id
        }

    def _time(self, seconds: float) -> str:
        seconds = max(0.0, float(seconds or 0.0))
        minutes = int(seconds // 60)
        remainder = seconds - (minutes * 60)
        return f"{minutes:02d}:{remainder:05.2f}"

    def _type_counts(self, counts: dict[str, int]) -> str:
        if not counts:
            return "none"
        return ", ".join(f"{key}={value}" for key, value in counts.items())

    def _yes_no(self, value: bool) -> str:
        return "yes" if value else "no"
