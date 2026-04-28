from dataclasses import dataclass
from typing import Any


@dataclass
class ShortsDecision:
    job_id: str
    shorts_count: int
    selected_segments: list[dict[str, Any]]
    decision_reason: str


class ShortsDecisionEngine:
    def _segment_label(self, start: float, end: float) -> str:
        return f"{round(start, 1)}s - {round(end, 1)}s"

    def _dynamic_window_size(self, score: float) -> float:
        """Map a score tier to a segment duration.

        High-scoring moments get 60 s to capture full context.
        Good moments get 45 s.  Decent moments get 30 s.
        """
        if score >= 0.88:
            return 60.0
        if score >= 0.78:
            return 45.0
        return 30.0

    def _build_candidate_segments(self, duration: float) -> list[dict[str, Any]]:
        # Use the minimum useful window (30 s) as the stride anchor so we
        # generate positions for all tiers.  The actual per-segment duration
        # is assigned later in decide() once we know each segment's score.
        candidates = []

        anchor_window = 30.0
        step_size = 10.0

        start = 0.0
        while start + anchor_window <= duration:
            end = start + anchor_window
            candidates.append(
                {
                    "label": self._segment_label(start, end),
                    "start_seconds": round(start, 1),
                    "end_seconds": round(end, 1),
                    "duration_seconds": round(anchor_window, 1),
                }
            )
            start += step_size

        return candidates

    def _score_segment(
        self,
        candidate: dict[str, Any],
        segment_index: int,
        total_segments: int,
        total_duration: float,
    ) -> tuple[float, str]:
        if total_segments <= 1:
            return 0.8, "single_candidate"

        start = float(candidate.get("start_seconds", 0.0))
        end = float(candidate.get("end_seconds", start))
        midpoint = (start + end) / 2.0
        relative_position = midpoint / max(1.0, total_duration)

        intro_zone_end = min(25.0, total_duration * 0.15)
        outro_zone_start = max(0.0, total_duration - min(25.0, total_duration * 0.15))

        if start < intro_zone_end:
            score = 0.52
            reason = "intro_penalty"
        elif end > outro_zone_start:
            score = 0.58
            reason = "outro_penalty"
        elif relative_position < 0.25:
            score = 0.68
            reason = "early_section"
        elif relative_position < 0.70:
            score = 0.90
            reason = "mid_video_priority"
        elif relative_position < 0.88:
            score = 0.80
            reason = "late_mid_section"
        else:
            score = 0.66
            reason = "late_section"

        return round(score, 2), reason

    def _parse_segment(self, segment: dict[str, Any]) -> tuple[float, float]:
        start = float(segment.get("start_seconds", 0.0))
        end = float(segment.get("end_seconds", start))
        return start, end

    def _distance_to_midpoint(self, segment: dict[str, Any], total_duration: float) -> float:
        start, end = self._parse_segment(segment)
        midpoint = (start + end) / 2.0
        video_midpoint = total_duration / 2.0
        return abs(midpoint - video_midpoint)

    def _overlaps_too_much(
        self,
        seg1: dict[str, Any],
        seg2: dict[str, Any],
        total_duration: float,
    ) -> bool:
        start1, end1 = self._parse_segment(seg1)
        start2, end2 = self._parse_segment(seg2)

        if total_duration < 180:
            min_gap = 50.0
        elif total_duration < 360:
            min_gap = 70.0
        else:
            min_gap = 85.0

        if abs(start1 - start2) <= min_gap:
            return True

        overlap_start = max(start1, start2)
        overlap_end = min(end1, end2)

        if overlap_end <= overlap_start:
            return False

        overlap = overlap_end - overlap_start
        len1 = end1 - start1
        len2 = end2 - start2
        shorter = min(len1, len2)

        overlap_ratio = overlap / shorter
        return overlap_ratio > 0.03

    def decide(self, job, analysis_result, edit_decision) -> ShortsDecision:
        duration = analysis_result.duration_seconds

        if duration < 20:
            return ShortsDecision(
                job_id=job.job_id,
                shorts_count=0,
                selected_segments=[],
                decision_reason="Video too short for meaningful shorts",
            )

        candidates = self._build_candidate_segments(duration)

        if not candidates:
            return ShortsDecision(
                job_id=job.job_id,
                shorts_count=0,
                selected_segments=[],
                decision_reason="No valid candidate segments found",
            )

        scored_candidates = []
        for i, candidate in enumerate(candidates):
            score, selection_reason = self._score_segment(
                candidate=candidate,
                segment_index=i,
                total_segments=len(candidates),
                total_duration=duration,
            )

            scored_candidates.append(
                {
                    **candidate,
                    "score": score,
                    "selection_reason": selection_reason,
                }
            )

        scored_candidates.sort(
            key=lambda x: (
                -x["score"],
                self._distance_to_midpoint(x, duration),
                x["start_seconds"],
            )
        )

        if duration < 120:
            max_shorts = 1
        elif duration < 600:
            max_shorts = 2
        else:
            max_shorts = 3

        selected_segments = []

        for candidate in scored_candidates:
            if candidate["score"] < 0.67:
                continue

            too_similar = any(
                self._overlaps_too_much(candidate, selected, duration)
                for selected in selected_segments
            )

            if not too_similar:
                selected_segments.append(candidate)

            if len(selected_segments) >= max_shorts:
                break

        # Apply dynamic duration (30–60 s) based on each segment's score.
        # Higher-scoring moments get more time; end_seconds is clamped to
        # the source duration so we never request past EOF.
        for seg in selected_segments:
            window = self._dynamic_window_size(float(seg["score"]))
            end = min(round(seg["start_seconds"] + window, 1), round(duration, 1))
            seg["end_seconds"] = end
            seg["duration_seconds"] = round(end - seg["start_seconds"], 1)
            seg["label"] = self._segment_label(seg["start_seconds"], end)

        return ShortsDecision(
            job_id=job.job_id,
            shorts_count=len(selected_segments),
            selected_segments=selected_segments,
            decision_reason=(
                f"Selected {len(selected_segments)} structured non-overlapping segments "
                f"from {len(candidates)} candidates using quality rules v2; "
                f"dynamic duration 30–60 s applied"
            ),
        )