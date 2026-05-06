from __future__ import annotations

import uuid

from models.analysis_result import AnalysisResult
from models.energy_curve_result import EnergyCurveResult
from models.facecam_reaction_result import FacecamReactionResult
from models.gameplay_vision_result import GameplayVisionResult
from models.edit_timeline import EditTimeline
from models.highlight_candidate import HighlightCandidate
from models.job import Job
from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult
from core.final_timeline_guard import FinalTimelineGuard
from core.final_cut_safety_guard import FinalCutSafetyGuard
from core.final_timeline_quality_guard import FinalTimelineQualityGuard
from core.final_cut_seam_guard import FinalCutSeamGuard
from core.round_wait_deadtime_guard import RoundWaitDeadtimeGuard
from core.pre_action_context_guard import PreActionContextGuard
from core.silence_timeline_trimmer import SilenceTimelineTrimmer
from core.story_timeline_organizer import StoryTimelineOrganizer
from core.transcript_boundary_guard import TranscriptBoundaryGuard
from core.multi_indicator_score_fusion import MultiIndicatorScoreFusion
from models.sentence_timeline import SentenceTimelineResult
from models.audio_role_result import AudioRoleResult
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

    def _build_target_duration(
        self,
        duration_seconds: float,
        scored_candidates: list[dict],
    ) -> float:
        """
        Intelligente Timeline-Retention basierend auf Content-Qualität!
        
        Analysiert die Qualität der Highlights (Scores, Density) und passt
        die Retention entsprechend an:
        - Viel guter Content (hohe Scores, viele Highlights) → 85-95% behalten
        - Mittlerer Content → 60-70% behalten  
        - Viel Bullshit (niedrige Scores, wenig Highlights) → 35-45% behalten
        """
        if duration_seconds <= 0:
            raise ValidationError("Timeline builder needs positive duration")
        
        if not scored_candidates:
            # Fallback: Keine Highlights → Minimum behalten
            print("[TIMELINE-QUALITY] WARNING: No scored candidates, using minimum retention")
            return round(duration_seconds * 0.40, 3)
        
        # 1️⃣ ANALYSIERE HIGHLIGHT-QUALITÄT
        total_highlights = len(scored_candidates)
        avg_score = sum(item["selection_score"] for item in scored_candidates) / total_highlights
        highlight_density = total_highlights / (duration_seconds / 10.0)  # Highlights pro 10s
        
        # 2️⃣ KATEGORISIERE VIDEO-QUALITÄT
        if avg_score >= 0.70 and highlight_density >= 0.8:
            quality_category = "excellent"  # 🔥 Viel guter Content
            retention_factor = 0.92
        elif avg_score >= 0.55 and highlight_density >= 0.5:
            quality_category = "good"  # ✅ Normaler Content
            retention_factor = 0.75
        elif avg_score >= 0.45 and highlight_density >= 0.3:
            quality_category = "medium"  # 🤷 Durchschnitt
            retention_factor = 0.60
        else:
            quality_category = "low"  # 💩 Viel Bullshit
            retention_factor = 0.40
        
        # 3️⃣ BERECHNE TARGET DURATION (Qualität + Länge)
        if duration_seconds <= 300:  # Kurze Videos (< 5 Min)
            target = duration_seconds * retention_factor
        elif duration_seconds <= 1800:  # Mittlere Videos (5-30 Min)
            target = min(1200.0, duration_seconds * retention_factor)  # Max 20 Min
        else:  # Lange Videos (> 30 Min)
            # Bei langen Videos: Etwas aggressiver kürzen
            adjusted_factor = max(0.35, retention_factor - 0.10)
            target = min(1200.0, duration_seconds * adjusted_factor)  # Max 20 Min
        
        # 4️⃣ YOUTUBE-MONETARISIERUNG: Garantiere MINIMUM 8 Minuten! 💰
        # Mid-Roll-Ads brauchen mindestens 8 Min (480s)
        YOUTUBE_MIN_DURATION = 480.0  # 8 Minuten
        if target < YOUTUBE_MIN_DURATION and duration_seconds >= YOUTUBE_MIN_DURATION:
            target = YOUTUBE_MIN_DURATION
            print(f"[TIMELINE-YOUTUBE] WARNING: Erhoehen auf {YOUTUBE_MIN_DURATION}s (8 Min) fuer Monetarisierung!")
        
        # 5️⃣ DEBUG-OUTPUT
        print(f"[TIMELINE-QUALITY] Highlights: {total_highlights}, Avg Score: {avg_score:.2f}, Density: {highlight_density:.2f}")
        print(f"[TIMELINE-QUALITY] Category: {quality_category}, Retention: {retention_factor*100:.0f}%")
        print(f"[TIMELINE-QUALITY] Duration: {duration_seconds:.0f}s -> Target: {target:.0f}s ({target/duration_seconds*100:.0f}%)")
        
        return round(target, 3)

    def _score_candidate_for_longform(
        self,
        candidate: HighlightCandidate,
        weak_zones: list[HighlightCandidate],
        *,
        energy_curve_result: EnergyCurveResult | None = None,
        gameplay_vision_result: GameplayVisionResult | None = None,
        facecam_reaction_result: FacecamReactionResult | None = None,
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

        energy_overlap = self._max_energy_peak_overlap(candidate, energy_curve_result)
        if energy_overlap >= 0.30:
            score += 0.10
            notes.append("energy_boost")

        vision_overlap = self._max_gameplay_action_overlap(candidate, gameplay_vision_result)
        if vision_overlap >= 0.30:
            score += 0.10
            notes.append("vision_boost")

        facecam_overlap = self._max_facecam_reaction_overlap(candidate, facecam_reaction_result)
        if facecam_overlap >= 0.30:
            score += 0.10
            notes.append("facecam_boost")

        boost_count = sum(
            note in notes
            for note in ("energy_boost", "vision_boost", "facecam_boost")
        )
        if boost_count >= 2:
            score += 0.04
            notes.append("multi_analysis_boost")

        return self._clamp_score(score), notes

    def _max_energy_peak_overlap(
        self,
        candidate: HighlightCandidate,
        energy_curve_result: EnergyCurveResult | None,
    ) -> float:
        if energy_curve_result is None:
            return 0.0

        return max(
            (
                self._overlap_ratio(
                    candidate.start_time,
                    candidate.end_time,
                    point.start_seconds,
                    point.end_seconds,
                )
                for point in energy_curve_result.peak_points
                if point.energy_score >= 0.65
            ),
            default=0.0,
        )

    def _max_gameplay_action_overlap(
        self,
        candidate: HighlightCandidate,
        gameplay_vision_result: GameplayVisionResult | None,
    ) -> float:
        if gameplay_vision_result is None:
            return 0.0

        return max(
            (
                self._overlap_ratio(
                    candidate.start_time,
                    candidate.end_time,
                    window.start_seconds,
                    window.end_seconds,
                )
                for window in gameplay_vision_result.action_windows
                if window.action_score >= 0.55
            ),
            default=0.0,
        )

    def _max_facecam_reaction_overlap(
        self,
        candidate: HighlightCandidate,
        facecam_reaction_result: FacecamReactionResult | None,
    ) -> float:
        if facecam_reaction_result is None:
            return 0.0

        return max(
            (
                self._overlap_ratio(
                    candidate.start_time,
                    candidate.end_time,
                    window.start_seconds,
                    window.end_seconds,
                )
                for window in facecam_reaction_result.reaction_windows
                if window.reaction_score >= 0.55
            ),
            default=0.0,
        )

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
        energy_curve_result: EnergyCurveResult | None = None,
        gameplay_vision_result: GameplayVisionResult | None = None,
        facecam_reaction_result: FacecamReactionResult | None = None,
        transcript_result: TranscriptResult | None = None,
        cut_indicator_result=None,
        cut_scoring_profile=None,
        sentence_timeline_result: SentenceTimelineResult | None = None,
        audio_role_result: AudioRoleResult | None = None,
    ) -> EditTimeline:
        if analysis_result.duration_seconds <= 0:
            raise ValidationError("Timeline builder needs positive duration")

        if not highlight_candidates:
            raise ValidationError("Timeline builder needs highlight candidates")

        weak_zones = weak_zones or []

        # 1️⃣ ERST SCOREN: Highlights bewerten
        scored_candidates: list[dict] = []
        _fusion_engine = (
            MultiIndicatorScoreFusion()
            if (cut_indicator_result is not None and cut_scoring_profile is not None)
            else None
        )
        _fusion_stats: list[dict] = []

        for candidate in highlight_candidates:
            selection_score, notes = self._score_candidate_for_longform(
                candidate,
                weak_zones,
                energy_curve_result=energy_curve_result,
                gameplay_vision_result=gameplay_vision_result,
                facecam_reaction_result=facecam_reaction_result,
            )

            if _fusion_engine is not None:
                fusion_result = _fusion_engine.fuse(
                    start=candidate.start_time,
                    end=candidate.end_time,
                    base_score=selection_score,
                    cut_indicator_result=cut_indicator_result,
                    cut_scoring_profile=cut_scoring_profile,
                )
                selection_score = fusion_result["fused_score"]
                notes = notes + fusion_result["notes"]
                _fusion_stats.append(fusion_result)

            if selection_score < 0.45:
                continue

            scored_candidates.append(
                {
                    "candidate": candidate,
                    "selection_score": selection_score,
                    "notes": notes,
                }
            )

        if _fusion_stats:
            _f_boosted = sum(1 for r in _fusion_stats if r["positive_delta"] > 0)
            _f_penalized = sum(1 for r in _fusion_stats if r["negative_delta"] < 0)
            _f_avg = round(
                sum(r["indicator_delta"] for r in _fusion_stats) / len(_fusion_stats), 4
            )
            _f_max_pos = round(max(r["positive_delta"] for r in _fusion_stats), 4)
            _f_max_neg = round(min(r["negative_delta"] for r in _fusion_stats), 4)
            print(
                f"[TIMELINE-INDICATOR-FUSION] "
                f"boosted={_f_boosted} penalized={_f_penalized} "
                f"avg_delta={_f_avg:+.4f} "
                f"max_positive={_f_max_pos:.4f} "
                f"max_negative={_f_max_neg:.4f}"
            )
            _fusion_note = (
                f"Indicator fusion: "
                f"boosted={_f_boosted} penalized={_f_penalized} "
                f"avg_delta={_f_avg:+.4f} "
                f"max_positive={_f_max_pos:.4f} "
                f"max_negative={_f_max_neg:.4f}"
            )
        else:
            _fusion_note = None

        if not scored_candidates:
            raise ValidationError("No usable longform candidates after scoring")

        # 2️⃣ DANN TARGET DURATION: Intelligente Retention basierend auf Qualität! 🔥
        target_duration = self._build_target_duration(
            analysis_result.duration_seconds,
            scored_candidates,  # Jetzt MIT Qualitäts-Analyse!
        )

        # 3️⃣ MAX SEGMENTS: Dynamisch basierend auf TARGET DURATION! 🎯
        # Pro Segment ca. 10-14s → max_segments = target / 10s (mit Puffer)
        # Minimum: 12 Segmente, Maximum: 100 Segmente
        calculated_max = int(target_duration / 10.0)
        max_segments = max(12, min(100, calculated_max))
        
        print(f"[TIMELINE-SEGMENTS] Target: {target_duration:.0f}s -> Max Segments: {max_segments}")

        # 3️⃣ SELEKTION: Beste Highlights auswählen
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

        boundary_summary = TranscriptBoundaryGuard().apply(
            selected_segments,
            transcript_result,
        )
        print(
            "[TIMELINE-BOUNDARY] "
            f"adjusted_start={boundary_summary.adjusted_start} "
            f"adjusted_end={boundary_summary.adjusted_end} "
            f"skipped={boundary_summary.skipped}"
        )
        if boundary_summary.examples:
            print(f"[TIMELINE-BOUNDARY] examples={'; '.join(boundary_summary.examples)}")

        selected_segments, silence_summary = SilenceTimelineTrimmer().apply(
            selected_segments,
            weak_zones,
        )
        print(
            "[TIMELINE-SILENCE] "
            f"removed={silence_summary.removed} "
            f"trimmed_start={silence_summary.trimmed_start} "
            f"trimmed_end={silence_summary.trimmed_end} "
            f"skipped_middle={silence_summary.skipped_middle} "
            f"duration_before={silence_summary.duration_before:.3f}s "
            f"duration_after={silence_summary.duration_after:.3f}s"
        )
        if silence_summary.examples:
            print(f"[TIMELINE-SILENCE] examples={'; '.join(silence_summary.examples)}")

        if not selected_segments:
            raise ValidationError("No longform segments selected after silence trimming")

        selected_segments, story_summary = StoryTimelineOrganizer().apply(selected_segments)
        print(
            "[TIMELINE-STORY] "
            f"hook={story_summary.hook_segment_id or 'none'} "
            f"peaks={len(story_summary.peak_segment_ids)} "
            f"bridges={story_summary.bridge_count} "
            f"builds={story_summary.build_count} "
            f"payoff={story_summary.payoff_segment_id or 'none'} "
            f"duplicates_removed={story_summary.duplicates_removed} "
            f"near_duplicates_removed={story_summary.near_duplicates_removed}"
        )
        if story_summary.examples:
            print(f"[TIMELINE-STORY] examples={'; '.join(story_summary.examples)}")

        if not selected_segments:
            raise ValidationError("No longform segments selected after story dedupe")

        selected_segments, final_guard_summary = FinalTimelineGuard().apply(selected_segments)
        print(
            "[TIMELINE-FINAL-GUARD] "
            f"backjumps_fixed={final_guard_summary.backjumps_fixed} "
            f"overlaps_removed={final_guard_summary.overlaps_removed} "
            f"near_duplicates_removed={final_guard_summary.near_duplicates_removed} "
            f"trimmed={final_guard_summary.trimmed} "
            f"removed={final_guard_summary.removed} "
            f"duration_before={final_guard_summary.duration_before:.3f}s "
            f"duration_after={final_guard_summary.duration_after:.3f}s"
        )
        if final_guard_summary.examples:
            print(f"[TIMELINE-FINAL-GUARD] examples={'; '.join(final_guard_summary.examples)}")

        if not selected_segments:
            raise ValidationError("No longform segments selected after final timeline guard")

        selected_segments, cut_safety_summary = FinalCutSafetyGuard().apply(
            selected_segments,
            transcript_result,
        )
        print(
            "[TIMELINE-CUT-SAFETY] "
            f"adjusted_start={cut_safety_summary.adjusted_start} "
            f"adjusted_end={cut_safety_summary.adjusted_end} "
            f"skipped_start={cut_safety_summary.skipped_start} "
            f"skipped_end={cut_safety_summary.skipped_end} "
            f"duration_before={cut_safety_summary.duration_before:.3f}s "
            f"duration_after={cut_safety_summary.duration_after:.3f}s"
        )
        if cut_safety_summary.examples:
            print(f"[TIMELINE-CUT-SAFETY] examples={'; '.join(cut_safety_summary.examples)}")

        if not selected_segments:
            raise ValidationError("No longform segments selected after final cut safety guard")

        selected_segments, quality_summary = FinalTimelineQualityGuard().apply(
            selected_segments,
            transcript_result=transcript_result,
            weak_zones=weak_zones,
        )
        print(
            "[TIMELINE-QUALITY-GUARD] "
            f"micro_removed={quality_summary.micro_removed} "
            f"peak_micro_allowed={quality_summary.peak_micro_allowed} "
            f"speech_start_adjusted={quality_summary.speech_start_adjusted} "
            f"speech_end_adjusted={quality_summary.speech_end_adjusted} "
            f"silence_edge_trimmed={quality_summary.silence_edge_trimmed} "
            f"duration_before={quality_summary.duration_before:.3f}s "
            f"duration_after={quality_summary.duration_after:.3f}s"
        )
        if quality_summary.examples:
            print(f"[TIMELINE-QUALITY-GUARD] examples={'; '.join(quality_summary.examples)}")

        if not selected_segments:
            raise ValidationError("No longform segments selected after final quality guard")

        selected_segments, seam_summary = FinalCutSeamGuard().apply(
            selected_segments,
            transcript_result=transcript_result,
            sentence_timeline_result=sentence_timeline_result,
            audio_role_result=audio_role_result,
            cut_indicator_result=cut_indicator_result,
        )
        print(
            "[TIMELINE-SEAM-GUARD] "
            f"mini_fixed={seam_summary.mini_seams_fixed} "
            f"speech_adjusted={seam_summary.speech_start_adjusted + seam_summary.speech_end_adjusted} "
            f"speech_end_trimmed_back={seam_summary.speech_end_trimmed_back} "
            f"reaction_context={seam_summary.reaction_context_expanded} "
            f"secondary_speech={seam_summary.secondary_speech_protected} "
            f"speech_end_locked={seam_summary.speech_end_locked} "
            f"shout_end_locked={seam_summary.shout_end_locked} "
            f"phrase_end_locked={seam_summary.phrase_end_locked} "
            f"low_value_removed={seam_summary.low_value_segments_removed} "
            f"menu_dead_time_removed={seam_summary.menu_dead_time_removed} "
            f"important_context={seam_summary.important_context_expanded} "
            f"duration_before={seam_summary.duration_before:.3f}s "
            f"duration_after={seam_summary.duration_after:.3f}s"
        )
        if seam_summary.examples:
            print(f"[TIMELINE-SEAM-GUARD] examples={'; '.join(seam_summary.examples)}")

        if not selected_segments:
            raise ValidationError("No longform segments selected after seam guard")

        selected_segments, round_wait_summary = RoundWaitDeadtimeGuard().apply(
            selected_segments,
            cut_indicator_result=cut_indicator_result,
            audio_role_result=audio_role_result,
        )

        if not selected_segments:
            raise ValidationError("No longform segments selected after round-wait guard")

        selected_segments, pre_action_summary = PreActionContextGuard().apply(
            selected_segments,
            cut_indicator_result=cut_indicator_result,
            audio_role_result=audio_role_result,
        )

        if not selected_segments:
            raise ValidationError("No longform segments selected after pre-action context guard")

        peak_segment_ids = [
            segment.segment_id
            for segment in selected_segments
            if segment.segment_role == "peak"
        ]
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
            "Boundary guard: "
            f"adjusted_start={boundary_summary.adjusted_start} "
            f"adjusted_end={boundary_summary.adjusted_end} "
            f"skipped={boundary_summary.skipped}",
            "Silence trim: "
            f"removed={silence_summary.removed} "
            f"trimmed_start={silence_summary.trimmed_start} "
            f"trimmed_end={silence_summary.trimmed_end} "
            f"skipped_middle={silence_summary.skipped_middle} "
            f"duration_before={silence_summary.duration_before:.3f}s "
            f"duration_after={silence_summary.duration_after:.3f}s",
            "Story order: "
            f"hook={story_summary.hook_segment_id or 'none'} "
            f"peaks={len(story_summary.peak_segment_ids)} "
            f"bridges={story_summary.bridge_count} "
            f"builds={story_summary.build_count} "
            f"payoff={story_summary.payoff_segment_id or 'none'} "
            f"duplicates_removed={story_summary.duplicates_removed} "
            f"near_duplicates_removed={story_summary.near_duplicates_removed}",
            "Final guard: "
            f"backjumps_fixed={final_guard_summary.backjumps_fixed} "
            f"overlaps_removed={final_guard_summary.overlaps_removed} "
            f"near_duplicates_removed={final_guard_summary.near_duplicates_removed} "
            f"trimmed={final_guard_summary.trimmed} "
            f"removed={final_guard_summary.removed} "
            f"duration_before={final_guard_summary.duration_before:.3f}s "
            f"duration_after={final_guard_summary.duration_after:.3f}s",
            "Final cut safety: "
            f"adjusted_start={cut_safety_summary.adjusted_start} "
            f"adjusted_end={cut_safety_summary.adjusted_end} "
            f"skipped_start={cut_safety_summary.skipped_start} "
            f"skipped_end={cut_safety_summary.skipped_end} "
            f"duration_before={cut_safety_summary.duration_before:.3f}s "
            f"duration_after={cut_safety_summary.duration_after:.3f}s",
            "Final quality guard: "
            f"micro_removed={quality_summary.micro_removed} "
            f"peak_micro_allowed={quality_summary.peak_micro_allowed} "
            f"speech_start_adjusted={quality_summary.speech_start_adjusted} "
            f"speech_end_adjusted={quality_summary.speech_end_adjusted} "
            f"silence_edge_trimmed={quality_summary.silence_edge_trimmed} "
            f"duration_before={quality_summary.duration_before:.3f}s "
            f"duration_after={quality_summary.duration_after:.3f}s",
            "Seam guard: "
            f"mini_fixed={seam_summary.mini_seams_fixed} "
            f"speech_adjusted={seam_summary.speech_start_adjusted + seam_summary.speech_end_adjusted} "
            f"speech_end_trimmed_back={seam_summary.speech_end_trimmed_back} "
            f"reaction_context={seam_summary.reaction_context_expanded} "
            f"secondary_speech={seam_summary.secondary_speech_protected} "
            f"speech_end_locked={seam_summary.speech_end_locked} "
            f"shout_end_locked={seam_summary.shout_end_locked} "
            f"phrase_end_locked={seam_summary.phrase_end_locked} "
            f"low_value_removed={seam_summary.low_value_segments_removed} "
            f"menu_dead_time_removed={seam_summary.menu_dead_time_removed} "
            f"duration_before={seam_summary.duration_before:.3f}s "
            f"duration_after={seam_summary.duration_after:.3f}s",
            "Round wait guard: "
            f"removed={round_wait_summary.removed} "
            f"trimmed={round_wait_summary.trimmed} "
            f"after_goal_tail_trimmed={round_wait_summary.after_goal_tail_trimmed} "
            f"menu_speech_ignored={round_wait_summary.menu_speech_ignored} "
            f"kept_action={round_wait_summary.kept_action} "
            f"kept_speech={round_wait_summary.kept_speech} "
            f"duration_before={round_wait_summary.duration_before:.3f}s "
            f"duration_after={round_wait_summary.duration_after:.3f}s",
            "Pre action context: "
            f"expanded={pre_action_summary.expanded} "
            f"shout={pre_action_summary.shout} "
            f"goal={pre_action_summary.goal} "
            f"action={pre_action_summary.action} "
            f"strong_action_context={pre_action_summary.strong_action_context} "
            f"skipped_overlap={pre_action_summary.skipped_overlap} "
            f"skipped_silence={pre_action_summary.skipped_silence} "
            f"duration_before={pre_action_summary.duration_before:.3f}s "
            f"duration_after={pre_action_summary.duration_after:.3f}s",
        ]

        boost_counts = self._count_analysis_boosts(selected_segments)
        timeline_notes.append(
            "Analysis boosts: "
            f"energy={boost_counts['energy_boost']} "
            f"vision={boost_counts['vision_boost']} "
            f"facecam={boost_counts['facecam_boost']}"
        )
        if _fusion_note:
            timeline_notes.append(_fusion_note)
        boosted_segments = sum(
            any(
                note in segment.notes
                for note in ("energy_boost", "vision_boost", "facecam_boost")
            )
            for segment in selected_segments
        )
        top_boosts = [
            f"{segment.segment_id}:{'+'.join(note for note in segment.notes if note.endswith('_boost'))}"
            for segment in selected_segments
            if any(note.endswith("_boost") for note in segment.notes)
        ][:5]
        print(
            "[TIMELINE-SCORING] "
            f"boosted_segments={boosted_segments} "
            f"energy={boost_counts['energy_boost']} "
            f"vision={boost_counts['vision_boost']} "
            f"facecam={boost_counts['facecam_boost']}"
        )
        if top_boosts:
            print(f"[TIMELINE-SCORING] top_boosts={','.join(top_boosts)}")

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

    def _count_analysis_boosts(self, selected_segments: list[TimelineSegment]) -> dict[str, int]:
        return {
            "energy_boost": sum("energy_boost" in segment.notes for segment in selected_segments),
            "vision_boost": sum("vision_boost" in segment.notes for segment in selected_segments),
            "facecam_boost": sum("facecam_boost" in segment.notes for segment in selected_segments),
        }
