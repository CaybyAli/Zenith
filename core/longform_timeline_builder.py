from __future__ import annotations

import uuid

from models.analysis_result import AnalysisResult
from models.edit_timeline import EditTimeline
from models.highlight_candidate import HighlightCandidate
from models.job import Job
from models.timeline_segment import TimelineSegment
from shared.errors import ValidationError


class LongformTimelineBuilder:
    def _make_timeline_id(self) -> str:
        return f"timeline_{uuid.uuid4().hex[:12]}"

    def _make_segment_id(self) -> str:
        return f"seg_{uuid.uuid4().hex[:12]}"

    def _clamp_score(self, value: float) -> float:
        return round(max(0.0, min(1.0, float(value))), 3)

    def _overlap_ratio(
        self,
        start_a: float,
        end_a: float,
        start_b: float,
        end_b: float,
    ) -> float:
        overlap_start = max(start_a, start_b)
        overlap_end = min(end_a, end_b)

        if overlap_end <= overlap_start:
            return 0.0

        overlap = overlap_end - overlap_start
        shorter = max(0.001, min(end_a - start_a, end_b - start_b))
        return overlap / shorter

    def _build_target_duration(self, duration_seconds: float) -> float:
        if duration_seconds <= 0:
            raise ValidationError("Timeline builder needs positive duration")

        # KURZE Videos: Fast alles behalten
        if duration_seconds <= 300:  # < 5 Min
            return round(duration_seconds * 0.95, 3)  # 95% behalten
        
        # MITTLERE Videos: Meiste behalten
        if duration_seconds <= 900:  # 5-15 Min
            return round(duration_seconds * 0.85, 3)  # 85% behalten
        
        # LANGE Videos: Auf 10-15 Min kürzen
        if duration_seconds <= 3600:  # 15-60 Min
            return round(min(900.0, duration_seconds * 0.40), 3)  # Max 15 Min
        
        # SEHR LANGE Videos: Auf 15 Min kürzen
        return 900.0  # Max 15 Min

    def _score_candidate_for_longform(
        self,
        candidate: HighlightCandidate,
        weak_zones: list[HighlightCandidate],
    ) -> tuple[float, list[str]]:
        score = 0.0
        notes: list[str] = []

        score += candidate.highlight_score * 0.72
        score += candidate.confidence * 0.18

        if candidate.candidate_kind == "action_peak":
            score += 0.08
            notes.append("action_peak_bonus")
        elif candidate.candidate_kind == "speech_peak":
            score += 0.06
            notes.append("speech_peak_bonus")

        if "intro_zone" in candidate.signal_tags:
            score += 0.05
            notes.append("hook_potential_bonus")

        if "outro_zone" in candidate.signal_tags:
            score -= 0.03
            notes.append("outro_penalty")

        weak_overlap = 0.0
        for weak_zone in weak_zones:
            weak_overlap = max(
                weak_overlap,
                self._overlap_ratio(
                    candidate.start_time,
                    candidate.end_time,
                    weak_zone.start_time,
                    weak_zone.end_time,
                ),
            )

        if weak_overlap >= 0.50:
            score -= 0.
            notes.append("heavy_weak_zone_penalty")
        elif weak_overlap >= 0.20:
            score -= 0.20
            notes.append("partial_weak_zone_penalty")

        return self._clamp_score(score), notes

    def _dedupe_and_select(
        self,
        scored_candidates: list[dict],
        *,
        target_duration: float,
        max_segments: int,
    ) -> list[dict]:
        selected: list[dict] = []
        selected_duration = 0.0

        sorted_candidates = sorted(
            scored_candidates,
            key=lambda item: (
                -item["selection_score"],
                item["candidate"].start_time,
                item["candidate"].end_time,
            ),
        )


        for item in sorted_candidates:
            candidate = item["candidate"]

            heavy_weak_penalty = "heavy_weak_zone_penalty" in item["notes"]
            if heavy_weak_penalty:
                continue

            overlaps_existing = any(
                self._overlap_ratio(
                    candidate.start_time,
                    candidate.end_time,
                    existing["candidate"].start_time,
                    existing["candidate"].end_time,
                ) >= 0.70
                for existing in selected
            )

            if overlaps_existing:
                continue
# Trim overlapping segments
            trimmed_invalid = False
            for existing in selected:
                existing_cand = existing["candidate"]
                
                # Check if current candidate overlaps with existing
                if candidate.end_time > existing_cand.start_time and candidate.start_time < existing_cand.end_time:
                    # Overlap detected - trim current candidate to start after existing ends
                    if candidate.start_time < existing_cand.end_time:
                        candidate.start_time = existing_cand.end_time
                        
                        # If trimmed segment is now invalid or too short, mark for skip
                        if candidate.end_time <= candidate.start_time:
                            trimmed_invalid = True
                            break
                        if candidate.end_time - candidate.start_time < 3.0:
                            trimmed_invalid = True
                            break

            if trimmed_invalid:
                continue

            selected.append(item)
            selected_duration += candidate.end_time - candidate.start_time

            if len(selected) >= max_segments:
                break

            if selected_duration >= target_duration * 0.92:
                break

        return sorted(
            selected,
            key=lambda item: (item["candidate"].start_time, item["candidate"].end_time),
        )
    def _resolve_peak_index(self, selected_items: list[dict]) -> int | None:
        if len(selected_items) < 3:
            return None

        middle_indices = list(range(1, len(selected_items) - 1))
        if not middle_indices:
            return None

        return max(
            middle_indices,
            key=lambda index: selected_items[index]["selection_score"],
        )

    def build(
        self,
        job: Job,
        analysis_result: AnalysisResult,
        highlight_candidates: list[HighlightCandidate],
        weak_zones: list[HighlightCandidate] | None = None,
    ) -> EditTimeline:
        if analysis_result.duration_seconds <= 0:
            raise ValidationError("Timeline builder needs positive duration")

        if not highlight_candidates:
            raise ValidationError("Timeline builder needs highlight candidates")

        weak_zones = weak_zones or []
        target_duration = self._build_target_duration(analysis_result.duration_seconds)

# Segment-Limits basierend auf Video-Länge
        if analysis_result.duration_seconds >= 3600:
            max_segments = 25  # 1h+ Videos
        elif analysis_result.duration_seconds >= 1800:
            max_segments = 20  # 30-60 Min Videos
        elif analysis_result.duration_seconds >= 900:
            max_segments = 15  # 15-30 Min Videos
        elif analysis_result.duration_seconds >= 300:
            max_segments = 12  # 5-15 Min Videos
        else:
            max_segments = 20  # < 5 Min: VIELE Segmente (fast alles)

        scored_candidates: list[dict] = []
        for candidate in highlight_candidates:
            selection_score, notes = self._score_candidate_for_longform(
                candidate,
                weak_zones,
            )

            if selection_score < 0.45:
                continue

            scored_candidates.append(
                {
                    "candidate": candidate,
                    "selection_score": selection_score,
                    "notes": notes,
                }
            )

        if not scored_candidates:
            raise ValidationError("No usable longform candidates after scoring")

        selected_items = self._dedupe_and_select(
            scored_candidates,
            target_duration=target_duration,
            max_segments=max_segments,
        )

        if not selected_items:
            raise ValidationError("No longform segments selected")

        peak_index = self._resolve_peak_index(selected_items)

        selected_segments: list[TimelineSegment] = []
        peak_segment_ids: list[str] = []

        for index, item in enumerate(selected_items):
            candidate = item["candidate"]

            if index == 0:
                segment_role = "hook"
            elif index == len(selected_items) - 1 and len(selected_items) > 1:
                segment_role = "payoff"
            elif peak_index is not None and index == peak_index:
                segment_role = "peak"
            elif peak_index is not None and index < peak_index:
                segment_role = "build"
            else:
                segment_role = "bridge"

            segment = TimelineSegment(
                segment_id=self._make_segment_id(),
                job_id=job.job_id,
                candidate_id=candidate.candidate_id,
                start_time=round(candidate.start_time, 3),
                end_time=round(candidate.end_time, 3),
                segment_role=segment_role,
                selection_score=item["selection_score"],
                notes=item["notes"] + [f"candidate_kind={candidate.candidate_kind}"],
                source="longform_timeline_builder",
            )
            selected_segments.append(segment)

            if segment_role == "peak":
                peak_segment_ids.append(segment.segment_id)

        hook_segment_id = selected_segments[0].segment_id if selected_segments else None
        payoff_segment_id = selected_segments[-1].segment_id if selected_segments else None
        timeline_score = round(
            sum(segment.selection_score for segment in selected_segments) / len(selected_segments),
            3,
        )

        timeline_notes = [
            f"Selected {len(selected_segments)} segments from {len(highlight_candidates)} candidates",
            f"Target duration: {target_duration:.2f}s",
            f"Weak zones considered: {len(weak_zones)}",
        ]

        return EditTimeline(
            timeline_id=self._make_timeline_id(),
            job_id=job.job_id,
            target_duration=target_duration,
            selected_segments=selected_segments,
            hook_segment_id=hook_segment_id,
            peak_segment_ids=peak_segment_ids,
            payoff_segment_id=payoff_segment_id,
            timeline_score=timeline_score,
            timeline_notes=timeline_notes,
        )