from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from models.final_quality_validator import (
    CHECK_BLOCKED,
    CHECK_PASSED,
    CHECK_SKIPPED,
    CHECK_WARNING,
    FINAL_QUALITY_READY_WITH_WARNINGS,
    SEVERITY_BLOCKING,
    SEVERITY_INFO,
    SEVERITY_WARNING,
    FinalQualityCheck,
    FinalQualitySuggestion,
    FinalQualityValidationReport,
)


BLOCK7_METADATA = {
    "phase": "2B-43",
    "block": "block7_story_pacing",
    "review_only": True,
    "final_quality_validator_only": True,
    "media_unchanged": True,
    "no_execution_in_2b_43": True,
    "no_render_in_2b_43": True,
    "no_timeline_reorder_in_2b_43": True,
    "no_quality_fix_apply_in_2b_43": True,
}


class FinalQualityValidator:
    def __init__(
        self,
        min_hook_score: float = 0.80,
        max_arc_deviation: float = 0.20,
        min_but_therefore_ratio: float = 0.60,
        min_clip_duration_sec: float = 0.50,
        max_loading_screen_sec: float = 2.0,
        max_silence_sec: float = 0.40,
    ) -> None:
        self.min_hook_score = min_hook_score
        self.max_arc_deviation = max_arc_deviation
        self.min_but_therefore_ratio = min_but_therefore_ratio
        self.min_clip_duration_sec = min_clip_duration_sec
        self.max_loading_screen_sec = max_loading_screen_sec
        self.max_silence_sec = max_silence_sec

    def validate(self, job: Any) -> FinalQualityValidationReport:
        job_id = str(self._get(job, "job_id", self._get(job, "id", "unknown")))
        timeline_items = self._timeline_items(job)

        report = FinalQualityValidationReport(
            report_id=f"final_quality_{job_id}",
            job_id=job_id,
            status=FINAL_QUALITY_READY_WITH_WARNINGS,
            metadata=dict(BLOCK7_METADATA),
        )

        report.checks.extend(
            [
                self._check_timeline_items(timeline_items),
                self._check_hook_present(job),
                self._check_hook_score(job),
                self._check_emotional_arc(job),
                self._check_pattern_interrupts(job),
                self._check_reaction_shots(job),
                self._check_but_therefore_ratio(job),
                self._check_pacing_not_monotone(job),
                self._check_breathing_room(job),
                self._check_no_short_clips(timeline_items),
                self._check_no_long_loading_screen(job, timeline_items),
                self._check_no_long_silence(job),
                self._check_sentence_boundary(job),
                self._check_censor_protection(job),
                self._check_protected_items(job),
                self._check_continuity_override(job),
                self._check_block6_safety(job),
                self._check_no_render_permission(job),
                self._check_no_execution_permission(job),
            ]
        )

        report.suggestions = self._build_suggestions(report.checks)
        self._score_report(report)
        report.recalculate_counts()
        return report

    def _build_suggestions(self, checks: List[FinalQualityCheck]) -> List[FinalQualitySuggestion]:
        suggestions: List[FinalQualitySuggestion] = []
        index = 1
        for check in checks:
            if check.status not in {CHECK_WARNING, CHECK_BLOCKED}:
                continue
            suggestions.append(
                FinalQualitySuggestion(
                    suggestion_id=f"final_quality_suggestion_{index}",
                    suggestion_type="review_final_quality",
                    category=check.category,
                    severity=check.severity,
                    reason=check.message,
                    review_required=True,
                    can_auto_apply=False,
                    metadata={
                        "check_id": check.check_id,
                        "review_only": True,
                        "media_unchanged": True,
                        "no_execution_in_2b_43": True,
                    },
                )
            )
            index += 1
        return suggestions

    def _score_report(self, report: FinalQualityValidationReport) -> None:
        report.audio_score = self._category_score(report.checks, "audio")
        report.video_score = self._category_score(report.checks, "video")
        report.story_score = self._category_score(report.checks, "story")
        report.pacing_score = self._category_score(report.checks, "pacing")
        report.safety_score = self._category_score(report.checks, "safety")

        category_scores = [
            report.audio_score,
            report.video_score,
            report.story_score,
            report.pacing_score,
            report.safety_score,
        ]
        usable_scores = [score for score in category_scores if score >= 0.0]
        report.overall_quality_score = round(sum(usable_scores) / max(len(usable_scores), 1), 4)
        report.recommendation = "review_final_quality"

    def _category_score(self, checks: List[FinalQualityCheck], category: str) -> float:
        relevant = [check for check in checks if check.category == category and check.status != CHECK_SKIPPED]
        if not relevant:
            return 0.0
        return round(sum(max(0.0, min(1.0, check.score)) for check in relevant) / len(relevant), 4)

    def _check(
        self,
        check_id: str,
        category: str,
        check_name: str,
        status: str,
        severity: str,
        score: float,
        message: str,
        evidence: Optional[Dict[str, Any]] = None,
        review_required: bool = False,
        blocking: bool = False,
    ) -> FinalQualityCheck:
        return FinalQualityCheck(
            check_id=check_id,
            category=category,
            check_name=check_name,
            status=status,
            severity=severity,
            score=score,
            message=message,
            evidence=evidence or {},
            review_required=review_required,
            blocking=blocking,
            metadata=dict(BLOCK7_METADATA),
        )

    def _check_timeline_items(self, timeline_items: List[Dict[str, Any]]) -> FinalQualityCheck:
        if timeline_items:
            return self._check(
                "timeline_items_present",
                "safety",
                "Timeline items vorhanden",
                CHECK_PASSED,
                SEVERITY_INFO,
                1.0,
                "Review-Timeline enth?lt Items.",
                {"item_count": len(timeline_items)},
            )
        return self._check(
            "timeline_items_present",
            "safety",
            "Timeline items vorhanden",
            CHECK_WARNING,
            SEVERITY_WARNING,
            0.25,
            "Keine Review-Timeline-Items gefunden.",
            {"item_count": 0},
            review_required=True,
        )

    def _check_hook_present(self, job: Any) -> FinalQualityCheck:
        selected = self._get(job, "hook_selected_candidate")
        hook_report = self._dict(self._get(job, "hook_identification_report"))
        candidates = self._list(hook_report.get("candidates") or self._get(job, "hook_candidates"))

        if selected or candidates:
            return self._check(
                "hook_present",
                "story",
                "Hook vorhanden",
                CHECK_PASSED,
                SEVERITY_INFO,
                1.0,
                "Hook-Kandidat ist vorhanden.",
                {"has_selected_hook": bool(selected), "candidate_count": len(candidates)},
            )

        return self._check(
            "hook_present",
            "story",
            "Hook vorhanden",
            CHECK_WARNING,
            SEVERITY_WARNING,
            0.35,
            "Kein Hook-Kandidat gefunden.",
            {"has_selected_hook": False, "candidate_count": 0},
            review_required=True,
        )

    def _check_hook_score(self, job: Any) -> FinalQualityCheck:
        score = self._first_number(
            self._deep_get(self._get(job, "hook_selected_candidate"), ["hook_score", "score", "final_score"]),
            self._deep_get(self._get(job, "hook_identification_report"), ["hook_score", "best_score", "selected_score"]),
        )
        if score is None:
            return self._check(
                "hook_score_strong",
                "story",
                "Hook Score stark",
                CHECK_SKIPPED,
                SEVERITY_INFO,
                0.0,
                "Keine Hook-Score-Daten vorhanden.",
            )

        if score >= self.min_hook_score:
            return self._check(
                "hook_score_strong",
                "story",
                "Hook Score stark",
                CHECK_PASSED,
                SEVERITY_INFO,
                1.0,
                "Hook Score ist stark genug.",
                {"hook_score": score, "minimum": self.min_hook_score},
            )

        return self._check(
            "hook_score_strong",
            "story",
            "Hook Score stark",
            CHECK_WARNING,
            SEVERITY_WARNING,
            max(score, 0.0),
            "Hook Score ist unter Zielwert.",
            {"hook_score": score, "minimum": self.min_hook_score},
            review_required=True,
        )

    def _check_emotional_arc(self, job: Any) -> FinalQualityCheck:
        arc_report = self._dict(self._get(job, "emotional_arc_report"))
        deviation = self._first_number(
            arc_report.get("average_deviation"),
            arc_report.get("avg_deviation"),
            arc_report.get("deviation"),
            arc_report.get("target_curve_deviation"),
        )

        if deviation is None:
            deviation = self._calculate_arc_deviation(self._list(self._get(job, "emotional_arc_points")))

        if deviation is None:
            return self._check(
                "emotional_arc_deviation",
                "story",
                "Emotional Arc Abweichung",
                CHECK_SKIPPED,
                SEVERITY_INFO,
                0.0,
                "Keine Emotional-Arc-Daten vorhanden.",
            )

        if deviation <= self.max_arc_deviation:
            return self._check(
                "emotional_arc_deviation",
                "story",
                "Emotional Arc Abweichung",
                CHECK_PASSED,
                SEVERITY_INFO,
                1.0,
                "Emotional Arc bleibt nah an der Zielkurve.",
                {"average_deviation": deviation, "maximum": self.max_arc_deviation},
            )

        return self._check(
            "emotional_arc_deviation",
            "story",
            "Emotional Arc Abweichung",
            CHECK_WARNING,
            SEVERITY_WARNING,
            max(0.0, 1.0 - deviation),
            "Emotional Arc weicht zu stark von der Zielkurve ab.",
            {"average_deviation": deviation, "maximum": self.max_arc_deviation},
            review_required=True,
        )

    def _check_pattern_interrupts(self, job: Any) -> FinalQualityCheck:
        pattern_report = self._dict(self._get(job, "pattern_interrupt_report"))
        windows = self._list(self._get(job, "pattern_interrupt_windows"))

        status = str(pattern_report.get("status", "")).lower()
        monotony_risk = self._truthy(pattern_report.get("monotony_risk")) or self._truthy(pattern_report.get("pacing_monotone_risk"))

        if pattern_report and status not in {"failed", "blocked"} and (windows or not monotony_risk):
            return self._check(
                "pattern_interrupts_present",
                "story",
                "Pattern Interrupts vorhanden",
                CHECK_PASSED,
                SEVERITY_INFO,
                1.0,
                "Pattern-Interrupt-Pr?fung ist vorhanden.",
                {"window_count": len(windows), "status": status},
            )

        return self._check(
            "pattern_interrupts_present",
            "story",
            "Pattern Interrupts vorhanden",
            CHECK_WARNING,
            SEVERITY_WARNING,
            0.45,
            "Pattern Interrupts fehlen oder Monotonie-Risiko ist offen.",
            {"window_count": len(windows), "status": status, "monotony_risk": monotony_risk},
            review_required=True,
        )

    def _check_reaction_shots(self, job: Any) -> FinalQualityCheck:
        reaction_report = self._dict(self._get(job, "reaction_shot_placement_report"))
        placements = self._list(self._get(job, "reaction_shot_placements"))
        placeholder_count = int(self._first_number(reaction_report.get("placeholder_count"), 0) or 0)

        if placeholder_count > 0:
            return self._check(
                "reaction_shots_reviewed",
                "story",
                "Reaction Shots gepr?ft",
                CHECK_WARNING,
                SEVERITY_WARNING,
                0.55,
                "Reaction-Shot-Platzhalter brauchen Review.",
                {"placeholder_count": placeholder_count, "placement_count": len(placements)},
                review_required=True,
            )

        if reaction_report or placements:
            return self._check(
                "reaction_shots_reviewed",
                "story",
                "Reaction Shots gepr?ft",
                CHECK_PASSED,
                SEVERITY_INFO,
                1.0,
                "Reaction-Shot-Vorschl?ge sind vorhanden.",
                {"placeholder_count": placeholder_count, "placement_count": len(placements)},
            )

        return self._check(
            "reaction_shots_reviewed",
            "story",
            "Reaction Shots gepr?ft",
            CHECK_SKIPPED,
            SEVERITY_INFO,
            0.0,
            "Keine Reaction-Shot-Daten vorhanden.",
        )

    def _check_but_therefore_ratio(self, job: Any) -> FinalQualityCheck:
        story_report = self._dict(self._get(job, "but_therefore_story_report"))
        ratio = self._first_number(
            story_report.get("but_therefore_ratio"),
            story_report.get("strong_story_ratio"),
            story_report.get("ratio"),
        )

        if ratio is None:
            ratio = self._calculate_story_ratio(self._list(self._get(job, "story_transitions")))

        if ratio is None:
            return self._check(
                "but_therefore_ratio",
                "story",
                "But/Therefore Ratio",
                CHECK_SKIPPED,
                SEVERITY_INFO,
                0.0,
                "Keine But/Therefore-Daten vorhanden.",
            )

        if ratio >= self.min_but_therefore_ratio:
            return self._check(
                "but_therefore_ratio",
                "story",
                "But/Therefore Ratio",
                CHECK_PASSED,
                SEVERITY_INFO,
                1.0,
                "But/Therefore Ratio ist stark genug.",
                {"ratio": ratio, "minimum": self.min_but_therefore_ratio},
            )

        return self._check(
            "but_therefore_ratio",
            "story",
            "But/Therefore Ratio",
            CHECK_WARNING,
            SEVERITY_WARNING,
            max(0.0, ratio),
            "But/Therefore Ratio ist zu schwach.",
            {"ratio": ratio, "minimum": self.min_but_therefore_ratio},
            review_required=True,
        )

    def _check_pacing_not_monotone(self, job: Any) -> FinalQualityCheck:
        pacing_report = self._dict(self._get(job, "dynamic_pacing_report"))
        monotony_score = self._first_number(pacing_report.get("monotony_score"), pacing_report.get("monotone_score"))
        monotony_risk = self._truthy(pacing_report.get("monotony_risk")) or self._truthy(pacing_report.get("pacing_monotone_risk"))

        if monotony_risk or (monotony_score is not None and monotony_score >= 0.60):
            return self._check(
                "pacing_not_monotone",
                "pacing",
                "Pacing nicht monoton",
                CHECK_WARNING,
                SEVERITY_WARNING,
                0.45,
                "Pacing wirkt zu monoton.",
                {"monotony_score": monotony_score, "monotony_risk": monotony_risk},
                review_required=True,
            )

        if pacing_report:
            return self._check(
                "pacing_not_monotone",
                "pacing",
                "Pacing nicht monoton",
                CHECK_PASSED,
                SEVERITY_INFO,
                1.0,
                "Pacing hat keine starke Monotonie-Warnung.",
                {"monotony_score": monotony_score, "monotony_risk": monotony_risk},
            )

        return self._check(
            "pacing_not_monotone",
            "pacing",
            "Pacing nicht monoton",
            CHECK_SKIPPED,
            SEVERITY_INFO,
            0.0,
            "Keine Dynamic-Pacing-Daten vorhanden.",
        )

    def _check_breathing_room(self, job: Any) -> FinalQualityCheck:
        pacing_report = self._dict(self._get(job, "dynamic_pacing_report"))
        breathing_score = self._first_number(pacing_report.get("breathing_room_score"), pacing_report.get("breathing_score"))
        missing = self._truthy(pacing_report.get("missing_breathing_room"))

        if missing or (breathing_score is not None and breathing_score < 0.50):
            return self._check(
                "breathing_room_present",
                "pacing",
                "Breathing Room vorhanden",
                CHECK_WARNING,
                SEVERITY_WARNING,
                0.45,
                "Breathing Room fehlt oder ist zu schwach.",
                {"breathing_room_score": breathing_score, "missing_breathing_room": missing},
                review_required=True,
            )

        if pacing_report:
            return self._check(
                "breathing_room_present",
                "pacing",
                "Breathing Room vorhanden",
                CHECK_PASSED,
                SEVERITY_INFO,
                1.0,
                "Breathing Room ist ausreichend.",
                {"breathing_room_score": breathing_score, "missing_breathing_room": missing},
            )

        return self._check(
            "breathing_room_present",
            "pacing",
            "Breathing Room vorhanden",
            CHECK_SKIPPED,
            SEVERITY_INFO,
            0.0,
            "Keine Breathing-Room-Daten vorhanden.",
        )

    def _check_no_short_clips(self, timeline_items: List[Dict[str, Any]]) -> FinalQualityCheck:
        short_items = []
        for item in timeline_items:
            duration = self._duration(item)
            if duration is not None and duration < self.min_clip_duration_sec:
                short_items.append({"item_id": item.get("item_id") or item.get("id"), "duration_sec": duration})

        if short_items:
            return self._check(
                "no_short_clips",
                "video",
                "Keine extrem kurzen Clips",
                CHECK_WARNING,
                SEVERITY_WARNING,
                0.50,
                "Review-Timeline enth?lt extrem kurze Clips.",
                {"short_items": short_items, "minimum": self.min_clip_duration_sec},
                review_required=True,
            )

        if timeline_items:
            return self._check(
                "no_short_clips",
                "video",
                "Keine extrem kurzen Clips",
                CHECK_PASSED,
                SEVERITY_INFO,
                1.0,
                "Keine extrem kurzen Clips gefunden.",
                {"minimum": self.min_clip_duration_sec},
            )

        return self._check(
            "no_short_clips",
            "video",
            "Keine extrem kurzen Clips",
            CHECK_SKIPPED,
            SEVERITY_INFO,
            0.0,
            "Keine Timeline-Items f?r Clip-L?ngenpr?fung vorhanden.",
        )

    def _check_no_long_loading_screen(self, job: Any, timeline_items: List[Dict[str, Any]]) -> FinalQualityCheck:
        loading_items = []
        screen_report = self._dict(self._get(job, "screen_classification_report"))
        candidates = timeline_items + self._list(screen_report.get("items"))

        for item in candidates:
            label = str(item.get("label") or item.get("screen_type") or item.get("classification") or "").lower()
            duration = self._duration(item)
            if "loading" in label and duration is not None and duration > self.max_loading_screen_sec:
                loading_items.append({"item_id": item.get("item_id") or item.get("id"), "duration_sec": duration})

        if loading_items:
            return self._check(
                "no_long_loading_screen",
                "video",
                "Keine langen Loading Screens",
                CHECK_WARNING,
                SEVERITY_WARNING,
                0.55,
                "Loading-Screen ist l?nger als Profil-Grenze.",
                {"loading_items": loading_items, "maximum": self.max_loading_screen_sec},
                review_required=True,
            )

        if candidates:
            return self._check(
                "no_long_loading_screen",
                "video",
                "Keine langen Loading Screens",
                CHECK_PASSED,
                SEVERITY_INFO,
                1.0,
                "Keine zu langen Loading-Screens gefunden.",
                {"maximum": self.max_loading_screen_sec},
            )

        return self._check(
            "no_long_loading_screen",
            "video",
            "Keine langen Loading Screens",
            CHECK_SKIPPED,
            SEVERITY_INFO,
            0.0,
            "Keine Screen-Classification-Daten vorhanden.",
        )

    def _check_no_long_silence(self, job: Any) -> FinalQualityCheck:
        silence_items = self._list(self._get(job, "silence_segments")) + self._list(self._deep_get(self._get(job, "silence_detection_report"), ["segments"]))
        long_items = []
        for item in silence_items:
            duration = self._duration(item)
            if duration is not None and duration > self.max_silence_sec:
                long_items.append({"duration_sec": duration, "start_sec": self._number(item.get("start_seconds") or item.get("start"))})

        if long_items:
            return self._check(
                "no_long_silence",
                "audio",
                "Keine langen Silence-Segmente",
                CHECK_WARNING,
                SEVERITY_WARNING,
                0.55,
                "Lange Silence-Segmente brauchen Review.",
                {"long_silence_items": long_items, "maximum": self.max_silence_sec},
                review_required=True,
            )

        if silence_items:
            return self._check(
                "no_long_silence",
                "audio",
                "Keine langen Silence-Segmente",
                CHECK_PASSED,
                SEVERITY_INFO,
                1.0,
                "Keine zu langen Silence-Segmente gefunden.",
                {"maximum": self.max_silence_sec},
            )

        return self._check(
            "no_long_silence",
            "audio",
            "Keine langen Silence-Segmente",
            CHECK_SKIPPED,
            SEVERITY_INFO,
            0.0,
            "Keine Silence-Daten vorhanden.",
        )

    def _check_sentence_boundary(self, job: Any) -> FinalQualityCheck:
        continuity = self._dict(self._get(job, "continuity_check_report"))
        sentence = self._dict(self._get(job, "sentence_boundary_report"))
        violation = (
            self._truthy(continuity.get("sentence_boundary_violation"))
            or self._truthy(sentence.get("sentence_boundary_violation"))
            or self._truthy(sentence.get("cut_mid_sentence"))
            or self._truthy(sentence.get("cut_mid_word"))
        )

        if violation:
            return self._check(
                "no_sentence_boundary_violation",
                "audio",
                "Keine Satzgrenzen-Verletzung",
                CHECK_BLOCKED,
                SEVERITY_BLOCKING,
                0.0,
                "Bekanntes Risiko: Schnitt mitten im Wort oder Satz.",
                {"continuity": continuity, "sentence_boundary": sentence},
                review_required=True,
                blocking=True,
            )

        if continuity or sentence:
            return self._check(
                "no_sentence_boundary_violation",
                "audio",
                "Keine Satzgrenzen-Verletzung",
                CHECK_PASSED,
                SEVERITY_INFO,
                1.0,
                "Keine Satzgrenzen-Verletzung gemeldet.",
            )

        return self._check(
            "no_sentence_boundary_violation",
            "audio",
            "Keine Satzgrenzen-Verletzung",
            CHECK_SKIPPED,
            SEVERITY_INFO,
            0.0,
            "Keine Satzgrenzen-Daten vorhanden.",
        )

    def _check_censor_protection(self, job: Any) -> FinalQualityCheck:
        safety = self._dict(self._get(job, "timeline_safety_validator_report"))
        missing = self._truthy(safety.get("censor_protection_missing")) or self._truthy(safety.get("censor_loss"))
        if missing:
            return self._check(
                "no_censor_loss",
                "safety",
                "Kein Censor-Schutz-Verlust",
                CHECK_BLOCKED,
                SEVERITY_BLOCKING,
                0.0,
                "Censor-Schutz fehlt oder ist gef?hrdet.",
                {"timeline_safety_validator_report": safety},
                review_required=True,
                blocking=True,
            )
        return self._check(
            "no_censor_loss",
            "safety",
            "Kein Censor-Schutz-Verlust",
            CHECK_PASSED,
            SEVERITY_INFO,
            1.0,
            "Kein Censor-Schutz-Verlust gemeldet.",
            {"timeline_safety_validator_report_present": bool(safety)},
        )

    def _check_protected_items(self, job: Any) -> FinalQualityCheck:
        safety = self._dict(self._get(job, "timeline_safety_validator_report"))
        danger = self._truthy(safety.get("protected_item_danger")) or self._truthy(safety.get("protected_loss"))
        if danger:
            return self._check(
                "no_protected_loss",
                "safety",
                "Kein Protected-Item-Verlust",
                CHECK_BLOCKED,
                SEVERITY_BLOCKING,
                0.0,
                "Protected-Items sind gef?hrdet.",
                {"timeline_safety_validator_report": safety},
                review_required=True,
                blocking=True,
            )
        return self._check(
            "no_protected_loss",
            "safety",
            "Kein Protected-Item-Verlust",
            CHECK_PASSED,
            SEVERITY_INFO,
            1.0,
            "Protected-Items bleiben gesch?tzt.",
            {"timeline_safety_validator_report_present": bool(safety)},
        )

    def _check_continuity_override(self, job: Any) -> FinalQualityCheck:
        safety = self._dict(self._get(job, "timeline_safety_validator_report"))
        continuity = self._dict(self._get(job, "continuity_check_report"))
        override = self._truthy(safety.get("continuity_block_override")) or self._truthy(continuity.get("block_override"))
        if override:
            return self._check(
                "no_continuity_block_override",
                "safety",
                "Kein Continuity-Block-Override",
                CHECK_BLOCKED,
                SEVERITY_BLOCKING,
                0.0,
                "Continuity Block wird ignoriert.",
                {"timeline_safety_validator_report": safety, "continuity_check_report": continuity},
                review_required=True,
                blocking=True,
            )
        return self._check(
            "no_continuity_block_override",
            "safety",
            "Kein Continuity-Block-Override",
            CHECK_PASSED,
            SEVERITY_INFO,
            1.0,
            "Kein Continuity-Block-Override gemeldet.",
        )

    def _check_block6_safety(self, job: Any) -> FinalQualityCheck:
        safety = self._dict(self._get(job, "timeline_safety_validator_report"))
        status = str(safety.get("status", "")).lower()
        blocked = status in {"blocked", "timeline_safety_blocked", "safety_blocked"} or self._truthy(safety.get("blocking"))
        allows_next = self._truthy(safety.get("can_render")) or self._truthy(safety.get("can_execute_timeline"))

        if blocked or allows_next:
            return self._check(
                "block6_safety_not_overridden",
                "safety",
                "Block-6 Safety nicht ?berschrieben",
                CHECK_BLOCKED,
                SEVERITY_BLOCKING,
                0.0,
                "Block-6 Safety ist blockiert oder wird gef?hrlich ?berschrieben.",
                {"status": status, "can_render": safety.get("can_render"), "can_execute_timeline": safety.get("can_execute_timeline")},
                review_required=True,
                blocking=True,
            )

        return self._check(
            "block6_safety_not_overridden",
            "safety",
            "Block-6 Safety nicht ?berschrieben",
            CHECK_PASSED,
            SEVERITY_INFO,
            1.0,
            "Block-6 Safety wird nicht ?berschrieben.",
            {"status": status},
        )

    def _check_no_render_permission(self, job: Any) -> FinalQualityCheck:
        dangerous = self._find_truthy_keys(job, ["can_render"])
        if dangerous:
            return self._check(
                "no_render_permission",
                "safety",
                "Keine Render-Erlaubnis",
                CHECK_BLOCKED,
                SEVERITY_BLOCKING,
                0.0,
                "Gef?hrliches Render-Flag ist True.",
                {"truthy_keys": dangerous},
                review_required=True,
                blocking=True,
            )
        return self._check(
            "no_render_permission",
            "safety",
            "Keine Render-Erlaubnis",
            CHECK_PASSED,
            SEVERITY_INFO,
            1.0,
            "Keine Render-Erlaubnis gesetzt.",
        )

    def _check_no_execution_permission(self, job: Any) -> FinalQualityCheck:
        dangerous = self._find_truthy_keys(
            job,
            [
                "can_apply_fixes",
                "can_execute_timeline",
                "can_reorder_timeline",
                "can_trim",
                "can_extend",
                "can_insert_effects",
            ],
        )
        if dangerous:
            return self._check(
                "no_execution_permission",
                "safety",
                "Keine Ausf?hrungs-Erlaubnis",
                CHECK_BLOCKED,
                SEVERITY_BLOCKING,
                0.0,
                "Gef?hrliches Ausf?hrungs-Flag ist True.",
                {"truthy_keys": dangerous},
                review_required=True,
                blocking=True,
            )
        return self._check(
            "no_execution_permission",
            "safety",
            "Keine Ausf?hrungs-Erlaubnis",
            CHECK_PASSED,
            SEVERITY_INFO,
            1.0,
            "Keine Ausf?hrungs-Erlaubnis gesetzt.",
        )

    def _timeline_items(self, job: Any) -> List[Dict[str, Any]]:
        direct = self._list(self._get(job, "review_timeline_plan_items"))
        if direct:
            return direct

        plan = self._dict(self._get(job, "review_timeline_plan"))
        for key in ("items", "timeline_items", "plan_items"):
            items = self._list(plan.get(key))
            if items:
                return items

        package = self._dict(self._get(job, "review_timeline_dashboard_package"))
        for key in ("items", "timeline_items", "plan_items"):
            items = self._list(package.get(key))
            if items:
                return items

        return []

    def _duration(self, item: Dict[str, Any]) -> Optional[float]:
        duration = self._number(item.get("duration_seconds") or item.get("duration_sec") or item.get("duration"))
        if duration is not None:
            return duration
        start = self._number(item.get("start_seconds") or item.get("start_sec") or item.get("start"))
        end = self._number(item.get("end_seconds") or item.get("end_sec") or item.get("end"))
        if start is not None and end is not None:
            return max(0.0, end - start)
        return None

    def _calculate_arc_deviation(self, points: List[Dict[str, Any]]) -> Optional[float]:
        deviations = []
        for point in points:
            actual = self._number(point.get("actual") or point.get("score") or point.get("emotion_score"))
            target = self._number(point.get("target") or point.get("target_score"))
            if actual is not None and target is not None:
                deviations.append(abs(actual - target))
        if not deviations:
            return None
        return round(sum(deviations) / len(deviations), 4)

    def _calculate_story_ratio(self, transitions: List[Dict[str, Any]]) -> Optional[float]:
        if not transitions:
            return None
        strong = 0
        for transition in transitions:
            kind = str(transition.get("transition_type") or transition.get("type") or "").lower()
            if kind in {"but", "therefore"}:
                strong += 1
        return round(strong / len(transitions), 4)

    def _find_truthy_keys(self, job: Any, keys: Iterable[str]) -> List[str]:
        found = []
        for key in keys:
            if self._truthy(self._get(job, key)):
                found.append(key)

        for report_key in [
            "timeline_approval_gate_report",
            "timeline_safety_validator_report",
            "review_timeline_dashboard_package_report",
            "final_quality_validation_report",
        ]:
            data = self._dict(self._get(job, report_key))
            for key in keys:
                if self._truthy(data.get(key)):
                    found.append(f"{report_key}.{key}")
        return found

    def _get(self, obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def _dict(self, value: Any) -> Dict[str, Any]:
        if isinstance(value, dict):
            return value
        if hasattr(value, "to_dict"):
            return value.to_dict()
        return {}

    def _list(self, value: Any) -> List[Dict[str, Any]]:
        if not value:
            return []
        if isinstance(value, list):
            return [item if isinstance(item, dict) else self._dict(item) for item in value]
        return []

    def _deep_get(self, value: Any, keys: Iterable[str]) -> Optional[Any]:
        data = self._dict(value)
        for key in keys:
            if key in data:
                return data.get(key)
        return None

    def _number(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _first_number(self, *values: Any) -> Optional[float]:
        for value in values:
            number = self._number(value)
            if number is not None:
                return number
        return None

    def _truthy(self, value: Any) -> bool:
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes", "y", "blocked", "failed"}
        return bool(value)


def validate_final_quality(job: Any) -> FinalQualityValidationReport:
    return FinalQualityValidator().validate(job)
