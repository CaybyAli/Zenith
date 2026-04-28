from __future__ import annotations

import uuid

from models.edit_signal import EditSignal
from models.edit_timeline import EditTimeline
from models.job import Job
from models.reaction_moment import ReactionMoment
from models.reframe_plan import ReframePlan


class ReactionMomentDetector:
    def _make_moment_id(self) -> str:
        return f"moment_{uuid.uuid4().hex[:12]}"

    def _clamp(self, value: float) -> float:
        return round(max(0.0, min(1.0, float(value))), 3)

    def _overlaps(
        self,
        start_a: float,
        end_a: float,
        start_b: float,
        end_b: float,
    ) -> bool:
        return max(start_a, start_b) < min(end_a, end_b)

    def _reaction_kind(
        self,
        *,
        segment_role: str,
        focus_kind: str,
        signal_type: str,
    ) -> str:
        if segment_role == "hook":
            return "hook_reaction"

        if segment_role == "peak":
            return "peak_reaction"

        if focus_kind == "facecam":
            return "facecam_reaction"

        if focus_kind == "gameplay":
            return "gameplay_reaction"

        if signal_type == "audio_peak":
            return "audio_emphasis"

        return "motion_emphasis"

    def detect(
        self,
        *,
        job: Job,
        timeline: EditTimeline,
        edit_signals: list[EditSignal],
        reframe_plan: ReframePlan,
    ) -> list[ReactionMoment]:
        instruction_by_segment = {
            instruction.segment_id: instruction
            for instruction in reframe_plan.instructions
        }

        moments: list[ReactionMoment] = []

        for segment in timeline.selected_segments:
            instruction = instruction_by_segment.get(segment.segment_id)
            focus_kind = instruction.focus_kind if instruction else "unknown"

            segment_signals = [
                signal
                for signal in edit_signals
                if signal.signal_type in {"audio_peak", "motion_peak", "audio_activity"}
                and self._overlaps(
                    segment.start_time,
                    segment.end_time,
                    signal.start_time,
                    signal.end_time,
                )
            ]

            if not segment_signals:
                continue

            segment_signals = sorted(
                segment_signals,
                key=lambda signal: (
                    -signal.strength,
                    signal.start_time,
                    signal.end_time,
                ),
            )

            selected_signals: list[EditSignal] = []

            for signal in segment_signals:
                too_similar = any(
                    self._overlaps(
                        signal.start_time,
                        signal.end_time,
                        existing.start_time,
                        existing.end_time,
                    )
                    for existing in selected_signals
                )

                if not too_similar:
                    selected_signals.append(signal)

                if len(selected_signals) >= 2:
                    break

            for signal in selected_signals:
                start_time = max(segment.start_time, signal.start_time)
                end_time = min(segment.end_time, signal.end_time)

                intensity = self._clamp(
                    (signal.strength * 0.7) + (segment.selection_score * 0.3)
                )
                confidence = self._clamp(
                    (signal.confidence * 0.65)
                    + ((instruction.metadata.get("focus_confidence", 0.5) if instruction else 0.5) * 0.35)
                )

                reaction_kind = self._reaction_kind(
                    segment_role=segment.segment_role,
                    focus_kind=focus_kind,
                    signal_type=signal.signal_type,
                )

                moments.append(
                    ReactionMoment(
                        moment_id=self._make_moment_id(),
                        job_id=job.job_id,
                        timeline_id=timeline.timeline_id,
                        segment_id=segment.segment_id,
                        start_time=round(start_time, 3),
                        end_time=round(end_time, 3),
                        reaction_kind=reaction_kind,
                        intensity=intensity,
                        confidence=confidence,
                        notes=[
                            f"segment_role={segment.segment_role}",
                            f"focus_kind={focus_kind}",
                            f"signal_type={signal.signal_type}",
                        ],
                    )
                )

        return sorted(
            moments,
            key=lambda moment: (moment.start_time, moment.end_time, moment.reaction_kind),
        )