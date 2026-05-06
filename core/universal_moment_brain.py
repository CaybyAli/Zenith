from __future__ import annotations

import math
from collections.abc import Iterable
from typing import Any

from models.universal_moment_result import (
    ENGINE,
    UniversalMomentResult,
    UniversalMomentWindow,
)


DEFAULT_WINDOW_SECONDS = 0.5
CRITICAL_WINDOW_SECONDS = 0.25

SPEECH_ROLE_TYPES = {"speech_active"}
SECONDARY_SPEECH_ROLE_TYPES = {"secondary_speech_like", "group_speech"}
SHOUT_ROLE_TYPES = {"shout_like_audio", "group_reaction_like", "laugh_like_audio"}
REACTION_ROLE_TYPES = {"group_reaction_like", "laugh_like_audio", "shout_like_audio"}
SILENCE_ROLE_TYPES = {"silence_or_dead_air"}
SPEECH_CUT_RISK_TYPES = {"speech_cut_risk_audio"}

ACTION_EVENT_TYPES = {"high_action_burst", "sustained_action", "kickoff_like"}
GOAL_EVENT_TYPES = {"goal_or_save_like_flash", "possible_goal_or_flash"}
WAIT_EVENT_TYPES = {"menu_or_idle", "low_gameplay_value"}
DEAD_EVENT_TYPES = {"round_end_dead_time"}
REPLAY_EVENT_TYPES = {"replay_like_moment", "scene_change_moment"}

ACTION_STATE_TYPES = {"active_gameplay", "high_motion_action"}
PRE_ACTION_STATE_TYPES = {"possible_pre_action_context"}
GOAL_STATE_TYPES = {"possible_goal_or_flash", "goal_or_save_like_flash"}
WAIT_STATE_TYPES = {"menu_wait", "queue_wait", "low_motion_wait", "scoreboard_like"}
DEAD_STATE_TYPES = {"possible_dead_time_after_goal", "round_end", "replay_like"}

MENU_PHASE_TYPES = {"menu_wait", "queue_wait"}
WAIT_PHASE_TYPES = {"menu_wait", "queue_wait", "countdown_kickoff"}
ACTIVE_PHASE_TYPES = {"active_round"}
DEAD_PHASE_TYPES = {"round_end", "goal_replay"}
PRE_ACTION_PHASE_TYPES = {"countdown_kickoff"}

POSITIVE_FACE_TYPES = {
    "facecam_reaction_spike",
    "facecam_motion_spike",
    "expression_change_like",
    "mouth_open_like",
    "smile_like",
    "shock_like",
    "laugh_like_face",
    "head_movement_like",
    "thumbnail_face_candidate",
}
NEGATIVE_FACE_TYPES = {"low_facecam_value"}

ZOOM_HINT_TYPES = {
    "zoom_risk",
    "zoom_boundary_risk",
    "facecam_zoom_risk",
    "facecam_reaction",
    "facecam_reaction_spike",
    "thumbnail_face_candidate",
    "shock_like",
    "low_facecam_value",
}
CUT_RISK_HINT_TYPES = {
    "speech_cut_risk_audio",
    "incomplete_sentence",
    "cut_risk",
    "speech_boundary_risk",
    "micro_gap",
}


class UniversalMomentBrain:
    engine = ENGINE

    def analyze(
        self,
        *,
        duration_seconds: float | None = None,
        transcript_result=None,
        sentence_timeline_result=None,
        audio_role_result=None,
        gameplay_vision_result=None,
        gameplay_event_result=None,
        gameplay_state_result=None,
        facecam_reaction_result=None,
        facecam_emotion_result=None,
        cut_indicator_result=None,
        round_phase_result=None,
    ) -> UniversalMomentResult:
        signals = {
            "transcript": self._transcript_rows(transcript_result),
            "sentences": self._sentence_rows(sentence_timeline_result),
            "audio": self._audio_rows(audio_role_result),
            "vision": self._vision_rows(gameplay_vision_result),
            "events": self._event_rows(gameplay_event_result),
            "states": self._state_rows(gameplay_state_result),
            "facecam": self._facecam_rows(facecam_reaction_result),
            "emotions": self._emotion_rows(facecam_emotion_result),
            "cuts": self._cut_rows(cut_indicator_result),
            "phases": self._phase_rows(round_phase_result),
        }
        duration = self._resolve_duration(duration_seconds, signals)
        if duration <= 0.0:
            result = UniversalMomentResult(engine=self.engine)
            self._log_summary(result)
            return result

        peak_markers = self._peak_markers(signals)
        critical_ranges = self._critical_ranges(signals, peak_markers)

        windows: list[UniversalMomentWindow] = []
        for index, (start, end) in enumerate(self._adaptive_windows(duration, critical_ranges)):
            window_signals = {
                name: self._overlapping_rows(rows, start, end)
                for name, rows in signals.items()
            }
            windows.append(
                self._build_window(
                    index=index,
                    start=start,
                    end=end,
                    signals=window_signals,
                    peak_markers=peak_markers,
                )
            )

        result = UniversalMomentResult(windows=windows, engine=self.engine)
        self._log_summary(result)
        return result

    def _build_window(
        self,
        *,
        index: int,
        start: float,
        end: float,
        signals: dict[str, list[dict[str, Any]]],
        peak_markers: list[dict[str, Any]],
    ) -> UniversalMomentWindow:
        transcript_rows = signals["transcript"]
        sentence_rows = signals["sentences"]
        audio_rows = signals["audio"]
        vision_rows = signals["vision"]
        event_rows = signals["events"]
        state_rows = signals["states"]
        facecam_rows = signals["facecam"]
        emotion_rows = signals["emotions"]
        cut_rows = signals["cuts"]
        phase_rows = signals["phases"]

        primary_speech_score = self._primary_speech_score(transcript_rows, sentence_rows, audio_rows)
        secondary_speech_score = self._max_type_score(audio_rows, SECONDARY_SPEECH_ROLE_TYPES)
        shout_score = max(
            self._max_type_score(audio_rows, SHOUT_ROLE_TYPES),
            self._sentence_shout_score(sentence_rows),
            self._max_type_score(cut_rows, SHOUT_ROLE_TYPES | {"exclamation_sentence", "hook_sentence"}),
        )
        speech_score = self._clamp(
            max(primary_speech_score, secondary_speech_score * 0.9, shout_score * 0.85)
        )

        gameplay_motion_score = max(
            self._max_field(vision_rows, "motion_score"),
            self._max_field(state_rows, "motion_score"),
        )
        scene_change_score = max(
            self._max_field(vision_rows, "scene_change_score"),
            self._max_field(state_rows, "scene_change_score"),
            self._max_type_score(event_rows, {"scene_change_moment"}),
            self._max_type_score(cut_rows, {"scene_change"}),
        )
        visual_action_score = self._visual_action_score(vision_rows, event_rows, state_rows, cut_rows)

        reaction_score = max(
            self._max_field(facecam_rows, "reaction_score"),
            self._max_type_score(audio_rows, REACTION_ROLE_TYPES),
            self._max_type_score(cut_rows, {"facecam_reaction", *REACTION_ROLE_TYPES}),
        )
        facecam_emotion_score = max(
            self._max_type_score(emotion_rows, POSITIVE_FACE_TYPES),
            self._max_type_score(cut_rows, POSITIVE_FACE_TYPES),
        )

        menu_wait_score = self._menu_wait_score(state_rows, event_rows, cut_rows, phase_rows)
        dead_time_score = self._dead_time_score(audio_rows, state_rows, event_rows, cut_rows, phase_rows)
        goal_score = self._goal_score(event_rows, state_rows, cut_rows)

        future_peak_score, future_peak_gap = self._future_peak(end, peak_markers)
        previous_peak_score, previous_peak_gap = self._previous_peak(start, peak_markers)

        pre_action_score = max(
            self._max_type_score(state_rows, PRE_ACTION_STATE_TYPES),
            self._max_type_score(event_rows, {"kickoff_like"}),
            self._max_type_score(phase_rows, PRE_ACTION_PHASE_TYPES, field="confidence"),
        )
        if future_peak_score > 0.0 and future_peak_gap <= 4.0:
            proximity = max(0.0, 1.0 - (future_peak_gap / 4.0))
            pre_action_score = max(pre_action_score, future_peak_score * proximity * 0.88)

        tension_score = self._clamp(
            max(
                pre_action_score,
                min(1.0, (visual_action_score * 0.40) + (speech_score * 0.20) + (future_peak_score * 0.45)),
            )
        )
        if future_peak_score <= 0.0:
            tension_score = max(pre_action_score, min(tension_score, 0.48))

        high_action_event_score = self._max_type_score(event_rows, ACTION_EVENT_TYPES)
        peak_score = self._clamp(
            max(
                goal_score,
                high_action_event_score * 0.85,
                visual_action_score * 0.80,
                min(1.0, (visual_action_score * 0.62) + (shout_score * 0.25) + (reaction_score * 0.20)),
            )
        )

        post_peak_reaction_score = 0.0
        if previous_peak_score > 0.0 and previous_peak_gap <= 4.0:
            reactionish = max(reaction_score, facecam_emotion_score, shout_score)
            if reactionish > 0.0:
                post_peak_reaction_score = self._clamp(
                    max(reactionish, reactionish * 0.75 + previous_peak_score * 0.25)
                )

        silence_score = self._max_type_score(audio_rows, SILENCE_ROLE_TYPES)
        private_talk_score = 0.0
        if speech_score > 0.0 and menu_wait_score > 0.0:
            private_talk_score = self._clamp(
                (speech_score * 0.52)
                + (menu_wait_score * 0.58)
                + ((1.0 - visual_action_score) * 0.18)
                - (max(peak_score, reaction_score) * 0.28)
            )

        no_value_score = self._clamp(1.0 - max(speech_score, visual_action_score, peak_score, reaction_score, shout_score))
        boring_score = self._clamp(
            max(menu_wait_score * 0.68, dead_time_score * 0.62, silence_score * 0.72)
            + (no_value_score * 0.46)
        )

        speech_boundary_score = self._speech_boundary_score(start, end, transcript_rows, sentence_rows, audio_rows, cut_rows)
        micro_gap_score = self._micro_gap_score(start, end, audio_rows, cut_rows)
        action_boundary_score = self._action_boundary_score(start, end, event_rows, state_rows, cut_rows)
        zoom_risk_score = self._zoom_risk_score(start, end, facecam_rows, emotion_rows, cut_rows, peak_score, reaction_score)
        cut_risk_score = self._clamp(
            max(
                speech_boundary_score,
                micro_gap_score,
                action_boundary_score * 0.85,
                self._explicit_cut_risk_score(cut_rows),
                zoom_risk_score * 0.45,
            )
        )

        moment_score = self._moment_score(
            speech_score=speech_score,
            visual_action_score=visual_action_score,
            shout_score=shout_score,
            reaction_score=reaction_score,
            facecam_emotion_score=facecam_emotion_score,
            tension_score=tension_score,
            peak_score=peak_score,
            post_peak_reaction_score=post_peak_reaction_score,
            boring_score=boring_score,
            private_talk_score=private_talk_score,
            dead_time_score=dead_time_score,
        )

        speech_boundary_risk = speech_boundary_score >= 0.55
        zoom_boundary_risk = zoom_risk_score >= 0.55
        menu_private_risk = private_talk_score >= 0.58
        action_context_risk = pre_action_score >= 0.52 or action_boundary_score >= 0.55

        moment_type = self._moment_type(
            visual_action_score=visual_action_score,
            speech_score=speech_score,
            menu_wait_score=menu_wait_score,
            private_talk_score=private_talk_score,
            tension_score=tension_score,
            peak_score=peak_score,
            post_peak_reaction_score=post_peak_reaction_score,
            boring_score=boring_score,
            cut_risk_score=cut_risk_score,
            zoom_risk_score=zoom_risk_score,
        )

        should_keep = (
            peak_score >= 0.55
            or post_peak_reaction_score >= 0.55
            or tension_score >= 0.58
            or visual_action_score >= 0.62
            or shout_score >= 0.62
            or reaction_score >= 0.68
            or (speech_score >= 0.55 and menu_wait_score < 0.45 and boring_score < 0.65)
        )
        should_remove = (
            not should_keep
            and (
                (boring_score >= 0.70 and speech_score < 0.35 and visual_action_score < 0.35)
                or (private_talk_score >= 0.70 and visual_action_score < 0.35 and peak_score < 0.45)
            )
        )
        needs_pre_context = (
            moment_type == "pre_action_tension"
            or peak_score >= 0.55
            or action_context_risk
        )
        needs_post_context = peak_score >= 0.55 or post_peak_reaction_score >= 0.55

        source_signals = self._source_signals(signals)
        source_notes = self._source_notes(signals)
        confidence = self._confidence(signals, moment_score)

        return UniversalMomentWindow(
            window_id=f"umw_{index:06d}",
            start_seconds=start,
            end_seconds=end,
            duration_seconds=end - start,
            visual_action_score=visual_action_score,
            gameplay_motion_score=gameplay_motion_score,
            scene_change_score=scene_change_score,
            speech_score=speech_score,
            primary_speech_score=primary_speech_score,
            secondary_speech_score=secondary_speech_score,
            shout_score=shout_score,
            reaction_score=reaction_score,
            facecam_emotion_score=facecam_emotion_score,
            menu_wait_score=menu_wait_score,
            dead_time_score=dead_time_score,
            private_talk_score=private_talk_score,
            tension_score=tension_score,
            pre_action_score=pre_action_score,
            peak_score=peak_score,
            post_peak_reaction_score=post_peak_reaction_score,
            boring_score=boring_score,
            cut_risk_score=cut_risk_score,
            zoom_risk_score=zoom_risk_score,
            moment_score=moment_score,
            moment_type=moment_type,
            should_keep=should_keep,
            should_remove=should_remove,
            needs_pre_context=needs_pre_context,
            needs_post_context=needs_post_context,
            speech_boundary_risk=speech_boundary_risk,
            zoom_boundary_risk=zoom_boundary_risk,
            menu_private_risk=menu_private_risk,
            action_context_risk=action_context_risk,
            source_signals=source_signals,
            source_notes=source_notes,
            confidence=confidence,
            metadata={
                "previous_peak_gap_seconds": round(previous_peak_gap, 3) if previous_peak_score else None,
                "future_peak_gap_seconds": round(future_peak_gap, 3) if future_peak_score else None,
                "signal_counts": {name: len(rows) for name, rows in signals.items()},
            },
        )

    def _moment_type(
        self,
        *,
        visual_action_score: float,
        speech_score: float,
        menu_wait_score: float,
        private_talk_score: float,
        tension_score: float,
        peak_score: float,
        post_peak_reaction_score: float,
        boring_score: float,
        cut_risk_score: float,
        zoom_risk_score: float,
    ) -> str:
        if cut_risk_score >= 0.70 and peak_score < 0.55:
            return "cut_risk"
        if zoom_risk_score >= 0.70 and peak_score < 0.55 and post_peak_reaction_score < 0.55:
            return "zoom_risk"
        if menu_wait_score >= 0.55 and speech_score >= 0.42 and visual_action_score < 0.45:
            return "private_menu_talk"
        if menu_wait_score >= 0.55 and visual_action_score < 0.40:
            return "boring_wait" if boring_score >= 0.62 else "menu_wait"
        if peak_score >= 0.55:
            return "peak_action"
        if post_peak_reaction_score >= 0.55:
            return "post_peak_reaction"
        if tension_score >= 0.52:
            return "pre_action_tension"
        if speech_score >= 0.45 and visual_action_score < 0.45:
            return "speech_context"
        if visual_action_score >= 0.45:
            return "active_gameplay"
        if boring_score >= 0.62:
            return "boring_wait"
        if cut_risk_score >= 0.55:
            return "cut_risk"
        if zoom_risk_score >= 0.55:
            return "zoom_risk"
        return "unknown"

    def _moment_score(self, **scores: float) -> float:
        positive = max(
            scores["peak_score"],
            scores["post_peak_reaction_score"] * 0.92,
            scores["tension_score"] * 0.86,
            scores["visual_action_score"] * 0.74,
            scores["reaction_score"] * 0.70,
            scores["facecam_emotion_score"] * 0.62,
            scores["shout_score"] * 0.72,
            scores["speech_score"] * 0.44,
        )
        negative = max(
            scores["boring_score"] * 0.34,
            scores["private_talk_score"] * 0.24,
            scores["dead_time_score"] * 0.22,
        )
        return self._clamp(positive - min(0.36, negative))

    def _primary_speech_score(
        self,
        transcript_rows: list[dict[str, Any]],
        sentence_rows: list[dict[str, Any]],
        audio_rows: list[dict[str, Any]],
    ) -> float:
        transcript_score = max(
            (max(0.45, row["confidence"] * 0.72) for row in transcript_rows),
            default=0.0,
        )
        sentence_score = max(
            (
                max(0.50, row["score"])
                for row in sentence_rows
                if row["type"] not in {"filler", "incomplete"}
            ),
            default=0.0,
        )
        audio_score = self._max_type_score(audio_rows, SPEECH_ROLE_TYPES)
        return self._clamp(max(transcript_score, sentence_score, audio_score))

    def _sentence_shout_score(self, sentence_rows: list[dict[str, Any]]) -> float:
        score = 0.0
        for row in sentence_rows:
            text = str(row.get("text", "")).lower()
            if row["type"] in {"exclamation", "hook"}:
                score = max(score, max(0.60, row["score"]))
            if "!" in text or any(term in text for term in ("alter", "junge", "wtf", "oh mein gott")):
                score = max(score, 0.68)
        return self._clamp(score)

    def _visual_action_score(
        self,
        vision_rows: list[dict[str, Any]],
        event_rows: list[dict[str, Any]],
        state_rows: list[dict[str, Any]],
        cut_rows: list[dict[str, Any]],
    ) -> float:
        vision_score = max(
            (
                max(row["action_score"] * 1.65, row["motion_score"] * 1.15, row["scene_change_score"] * 1.05)
                for row in vision_rows
            ),
            default=0.0,
        )
        event_score = self._max_type_score(event_rows, ACTION_EVENT_TYPES | GOAL_EVENT_TYPES)
        state_score = max(
            self._max_type_score(state_rows, ACTION_STATE_TYPES | GOAL_STATE_TYPES),
            self._max_field(state_rows, "visual_activity_score"),
        )
        cut_score = self._max_type_score(cut_rows, {"gameplay_action", "high_action_burst", "sustained_action", *GOAL_EVENT_TYPES})
        return self._clamp(max(vision_score, event_score, state_score, cut_score))

    def _menu_wait_score(
        self,
        state_rows: list[dict[str, Any]],
        event_rows: list[dict[str, Any]],
        cut_rows: list[dict[str, Any]],
        phase_rows: list[dict[str, Any]],
    ) -> float:
        return self._clamp(
            max(
                self._max_type_score(state_rows, WAIT_STATE_TYPES),
                self._max_type_score(event_rows, WAIT_EVENT_TYPES),
                self._max_type_score(cut_rows, {"menu_or_idle", "low_gameplay_value", "low_motion"}),
                self._max_type_score(phase_rows, MENU_PHASE_TYPES | PRE_ACTION_PHASE_TYPES, field="confidence"),
            )
        )

    def _dead_time_score(
        self,
        audio_rows: list[dict[str, Any]],
        state_rows: list[dict[str, Any]],
        event_rows: list[dict[str, Any]],
        cut_rows: list[dict[str, Any]],
        phase_rows: list[dict[str, Any]],
    ) -> float:
        return self._clamp(
            max(
                self._max_type_score(audio_rows, SILENCE_ROLE_TYPES),
                self._max_type_score(state_rows, DEAD_STATE_TYPES),
                self._max_type_score(event_rows, DEAD_EVENT_TYPES | REPLAY_EVENT_TYPES),
                self._max_type_score(cut_rows, {"silence", "silence_or_dead_air", *DEAD_EVENT_TYPES}),
                self._max_type_score(phase_rows, DEAD_PHASE_TYPES, field="confidence"),
            )
        )

    def _goal_score(
        self,
        event_rows: list[dict[str, Any]],
        state_rows: list[dict[str, Any]],
        cut_rows: list[dict[str, Any]],
    ) -> float:
        return self._clamp(
            max(
                self._max_type_score(event_rows, GOAL_EVENT_TYPES),
                self._max_type_score(state_rows, GOAL_STATE_TYPES),
                self._max_type_score(cut_rows, GOAL_EVENT_TYPES),
            )
        )

    def _speech_boundary_score(
        self,
        start: float,
        end: float,
        transcript_rows: list[dict[str, Any]],
        sentence_rows: list[dict[str, Any]],
        audio_rows: list[dict[str, Any]],
        cut_rows: list[dict[str, Any]],
    ) -> float:
        explicit = max(
            self._max_type_score(audio_rows, SPEECH_CUT_RISK_TYPES),
            self._max_type_score(cut_rows, SPEECH_CUT_RISK_TYPES | {"speech_boundary_risk"}),
        )
        boundary = self._boundary_score(start, end, [*transcript_rows, *sentence_rows], tolerance=0.16)
        return self._clamp(max(explicit, boundary))

    def _micro_gap_score(
        self,
        start: float,
        end: float,
        audio_rows: list[dict[str, Any]],
        cut_rows: list[dict[str, Any]],
    ) -> float:
        score = 0.0
        for row in [*audio_rows, *cut_rows]:
            row_type = row["type"]
            if row_type not in {"silence_or_dead_air", "silence", "micro_gap", "low_motion"}:
                continue
            duration = row["end"] - row["start"]
            if duration <= 0.70 and self._overlap_seconds(start, end, row["start"], row["end"]) > 0.0:
                score = max(score, max(0.55, row.get("score", 0.0)))
        return self._clamp(score)

    def _action_boundary_score(
        self,
        start: float,
        end: float,
        event_rows: list[dict[str, Any]],
        state_rows: list[dict[str, Any]],
        cut_rows: list[dict[str, Any]],
    ) -> float:
        rows = [
            row
            for row in [*event_rows, *state_rows, *cut_rows]
            if row["type"] in ACTION_EVENT_TYPES | GOAL_EVENT_TYPES | ACTION_STATE_TYPES | GOAL_STATE_TYPES
        ]
        return self._clamp(self._boundary_score(start, end, rows, tolerance=0.12) * 0.82)

    def _zoom_risk_score(
        self,
        start: float,
        end: float,
        facecam_rows: list[dict[str, Any]],
        emotion_rows: list[dict[str, Any]],
        cut_rows: list[dict[str, Any]],
        peak_score: float,
        reaction_score: float,
    ) -> float:
        explicit = max(
            self._max_type_score(cut_rows, ZOOM_HINT_TYPES | {"facecam_reaction"}),
            self._max_type_score(emotion_rows, ZOOM_HINT_TYPES),
        )
        type_hint = max(
            (
                row["score"]
                for row in cut_rows
                if "zoom" in row["type"] or "edge" in row["type"]
            ),
            default=0.0,
        )
        face_edge = self._boundary_score(start, end, [*facecam_rows, *emotion_rows], tolerance=0.14)
        face_signal = max(
            self._max_field(facecam_rows, "reaction_score"),
            self._max_type_score(emotion_rows, POSITIVE_FACE_TYPES | NEGATIVE_FACE_TYPES),
        )
        missing_reaction_near_peak = 0.55 if peak_score >= 0.60 and reaction_score < 0.08 else 0.0
        return self._clamp(max(explicit, type_hint, face_edge * max(0.55, face_signal), missing_reaction_near_peak))

    def _explicit_cut_risk_score(self, cut_rows: list[dict[str, Any]]) -> float:
        score = self._max_type_score(cut_rows, CUT_RISK_HINT_TYPES)
        for row in cut_rows:
            row_type = row["type"]
            if "zoom" in row_type or "facecam" in row_type:
                continue
            if "cut_risk" in row_type or "boundary" in row_type or "micro_gap" in row_type:
                score = max(score, row["score"])
        return self._clamp(score)

    def _boundary_score(
        self,
        start: float,
        end: float,
        rows: list[dict[str, Any]],
        *,
        tolerance: float,
    ) -> float:
        score = 0.0
        for row in rows:
            boundaries = (row["start"], row["end"])
            for boundary in boundaries:
                on_edge = (
                    abs(start - boundary) <= tolerance
                    or abs(end - boundary) <= tolerance
                    or start <= boundary <= end
                )
                if on_edge:
                    score = max(score, max(0.62, row.get("score", row.get("confidence", 0.0))))
        return self._clamp(score)

    def _confidence(self, signals: dict[str, list[dict[str, Any]]], moment_score: float) -> float:
        confidences = [
            row.get("confidence", row.get("score", 0.0))
            for rows in signals.values()
            for row in rows
        ]
        if not confidences:
            return self._clamp(moment_score * 0.5)
        avg = sum(self._clamp(value) for value in confidences) / len(confidences)
        return self._clamp(max(avg, moment_score * 0.7))

    def _source_signals(self, signals: dict[str, list[dict[str, Any]]]) -> list[str]:
        values: list[str] = []
        for rows in signals.values():
            for row in rows:
                values.append(f"{row['source']}:{row['type']}:{row['id']}")
        return list(dict.fromkeys(values))[:16]

    def _source_notes(self, signals: dict[str, list[dict[str, Any]]]) -> list[str]:
        notes: list[str] = []
        for rows in signals.values():
            for row in rows:
                note = row.get("note") or row.get("text")
                if note:
                    notes.append(str(note).strip()[:140])
        return list(dict.fromkeys(note for note in notes if note))[:10]

    def _future_peak(self, end: float, peak_markers: list[dict[str, Any]]) -> tuple[float, float]:
        candidates = [
            (marker["score"], marker["start"] - end)
            for marker in peak_markers
            if marker["start"] >= end
        ]
        if not candidates:
            return 0.0, math.inf
        score, gap = min(candidates, key=lambda item: item[1])
        return self._clamp(score), max(0.0, gap)

    def _previous_peak(self, start: float, peak_markers: list[dict[str, Any]]) -> tuple[float, float]:
        candidates = [
            (marker["score"], start - marker["end"])
            for marker in peak_markers
            if marker["end"] <= start
        ]
        if not candidates:
            return 0.0, math.inf
        score, gap = min(candidates, key=lambda item: item[1])
        return self._clamp(score), max(0.0, gap)

    def _peak_markers(self, signals: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for row in [*signals["events"], *signals["states"], *signals["cuts"]]:
            if row["type"] in GOAL_EVENT_TYPES | GOAL_STATE_TYPES:
                rows.append({"start": row["start"], "end": row["end"], "score": max(0.70, row["score"]), "type": row["type"]})
            elif row["type"] in ACTION_EVENT_TYPES and row["score"] >= 0.70:
                rows.append({"start": row["start"], "end": row["end"], "score": row["score"] * 0.85, "type": row["type"]})
        return sorted(rows, key=lambda item: (item["start"], item["end"], item["type"]))

    def _critical_ranges(
        self,
        signals: dict[str, list[dict[str, Any]]],
        peak_markers: list[dict[str, Any]],
    ) -> list[tuple[float, float]]:
        ranges: list[tuple[float, float]] = []
        for marker in peak_markers:
            ranges.append((marker["start"] - 2.0, marker["end"] + 2.0))

        critical_types = (
            SHOUT_ROLE_TYPES
            | REACTION_ROLE_TYPES
            | SPEECH_CUT_RISK_TYPES
            | ACTION_EVENT_TYPES
            | GOAL_EVENT_TYPES
            | ACTION_STATE_TYPES
            | GOAL_STATE_TYPES
            | PRE_ACTION_STATE_TYPES
            | POSITIVE_FACE_TYPES
            | ZOOM_HINT_TYPES
        )
        for group_name, rows in signals.items():
            for row in rows:
                row_type = row["type"]
                if (
                    row_type in critical_types
                    or row.get("score", 0.0) >= 0.72
                    or (group_name == "facecam" and row.get("reaction_score", 0.0) >= 0.24)
                    or "risk" in row_type
                    or "boundary" in row_type
                ):
                    ranges.append((row["start"] - 1.0, row["end"] + 1.0))
                if group_name in {"transcript", "sentences"}:
                    ranges.append((row["start"] - 0.35, row["start"] + 0.35))
                    ranges.append((row["end"] - 0.35, row["end"] + 0.35))

        return self._merge_ranges(ranges)

    def _adaptive_windows(
        self,
        duration: float,
        critical_ranges: list[tuple[float, float]],
    ) -> list[tuple[float, float]]:
        times = {0.0, round(duration, 3)}
        step = DEFAULT_WINDOW_SECONDS
        cursor = 0.0
        while cursor < duration:
            times.add(round(min(duration, cursor), 3))
            cursor += step

        for start, end in critical_ranges:
            start = max(0.0, start)
            end = min(duration, end)
            if end <= start:
                continue
            cursor = math.floor(start / CRITICAL_WINDOW_SECONDS) * CRITICAL_WINDOW_SECONDS
            while cursor <= end:
                times.add(round(max(0.0, min(duration, cursor)), 3))
                cursor += CRITICAL_WINDOW_SECONDS
            times.add(round(start, 3))
            times.add(round(end, 3))

        ordered = sorted(times)
        windows: list[tuple[float, float]] = []
        for left, right in zip(ordered, ordered[1:]):
            left = round(left, 3)
            right = round(right, 3)
            if right > left:
                windows.append((left, right))
        return windows

    def _resolve_duration(
        self,
        duration_seconds: float | None,
        signals: dict[str, list[dict[str, Any]]],
    ) -> float:
        explicit = self._safe_float(duration_seconds, 0.0)
        if explicit > 0:
            return round(explicit, 3)
        max_end = max(
            (row["end"] for rows in signals.values() for row in rows),
            default=0.0,
        )
        return round(max(0.0, max_end), 3)

    def _transcript_rows(self, transcript_result: object) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for index, segment in enumerate(self._iter_items(self._get(transcript_result, "segments", default=[]))):
            text = " ".join(str(self._get(segment, "text", default="") or "").split())
            start, end = self._start_end(segment)
            if not text or end <= start:
                continue
            confidence = self._clamp(self._get(segment, "confidence", default=0.72), 0.72)
            rows.append(
                self._row(
                    source="transcript",
                    row_id=f"transcript_{index:06d}",
                    row_type="speech_segment",
                    start=start,
                    end=end,
                    score=max(0.45, confidence * 0.72),
                    confidence=confidence,
                    text=text,
                    note=f"transcript: {text[:100]}",
                )
            )
        return rows

    def _sentence_rows(self, sentence_timeline_result: object) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for index, sentence in enumerate(self._iter_items(self._get(sentence_timeline_result, "sentences", default=[]))):
            text = " ".join(str(self._get(sentence, "text", default="") or "").split())
            start, end = self._start_end(sentence)
            if not text or end <= start:
                continue
            row_type = str(self._get(sentence, "sentence_kind", default="normal") or "normal")
            score = self._clamp(self._get(sentence, "score", default=0.45), 0.45)
            confidence = self._clamp(self._get(sentence, "confidence", default=0.75), 0.75)
            rows.append(
                self._row(
                    source="sentence",
                    row_id=str(self._get(sentence, "sentence_id", default=f"sentence_{index:06d}") or f"sentence_{index:06d}"),
                    row_type=row_type,
                    start=start,
                    end=end,
                    score=max(score, 0.50 if row_type not in {"filler", "incomplete"} else score),
                    confidence=confidence,
                    text=text,
                    note=f"sentence:{row_type}: {text[:100]}",
                )
            )
        return rows

    def _audio_rows(self, audio_role_result: object) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for index, window in enumerate(self._iter_items(self._get(audio_role_result, "windows", default=[]))):
            start, end = self._start_end(window)
            if end <= start:
                continue
            row_type = str(self._get(window, "role_type", default="unknown") or "unknown")
            rows.append(
                self._row(
                    source="audio",
                    row_id=str(self._get(window, "window_id", default=f"audio_{index:06d}") or f"audio_{index:06d}"),
                    row_type=row_type,
                    start=start,
                    end=end,
                    score=self._clamp(self._get(window, "score", default=0.0)),
                    confidence=self._clamp(self._get(window, "confidence", default=0.0)),
                    note=str(self._get(window, "reason", default=row_type) or row_type),
                    metadata=dict(self._get(window, "metadata", default={}) or {}),
                )
            )
        return rows

    def _vision_rows(self, gameplay_vision_result: object) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for index, window in enumerate(self._iter_items(self._get(gameplay_vision_result, "windows", default=[]))):
            start, end = self._start_end(window)
            if end <= start:
                continue
            action_score = self._clamp(self._get(window, "action_score", default=0.0))
            motion_score = self._clamp(self._get(window, "motion_score", default=0.0))
            scene_change_score = self._clamp(self._get(window, "scene_change_score", default=0.0))
            label = str(self._get(window, "label", default="unknown") or "unknown")
            row = self._row(
                source="vision",
                row_id=f"vision_{index:06d}",
                row_type=label,
                start=start,
                end=end,
                score=max(action_score, motion_score, scene_change_score),
                confidence=0.62,
                note=str(self._get(window, "reason", default=label) or label),
            )
            row.update(
                {
                    "action_score": action_score,
                    "motion_score": motion_score,
                    "scene_change_score": scene_change_score,
                }
            )
            rows.append(row)
        return rows

    def _event_rows(self, gameplay_event_result: object) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for index, window in enumerate(self._iter_items(self._get(gameplay_event_result, "windows", default=[]))):
            start, end = self._start_end(window)
            if end <= start:
                continue
            row_type = str(self._get(window, "event_type", default="unknown") or "unknown")
            rows.append(
                self._row(
                    source="gameplay_event",
                    row_id=str(self._get(window, "event_id", default=f"event_{index:06d}") or f"event_{index:06d}"),
                    row_type=row_type,
                    start=start,
                    end=end,
                    score=self._clamp(self._get(window, "score", default=0.0)),
                    confidence=self._clamp(self._get(window, "confidence", default=0.0)),
                    note=str(self._get(window, "reason", default=row_type) or row_type),
                    metadata=dict(self._get(window, "metadata", default={}) or {}),
                )
            )
        return rows

    def _state_rows(self, gameplay_state_result: object) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for index, window in enumerate(self._iter_items(self._get(gameplay_state_result, "windows", default=[]))):
            start, end = self._start_end(window)
            if end <= start:
                continue
            row_type = str(self._get(window, "state_type", default="unknown") or "unknown")
            row = self._row(
                source="gameplay_state",
                row_id=str(self._get(window, "window_id", default=f"state_{index:06d}") or f"state_{index:06d}"),
                row_type=row_type,
                start=start,
                end=end,
                score=self._clamp(self._get(window, "score", default=0.0)),
                confidence=self._clamp(self._get(window, "confidence", default=0.0)),
                note=str(self._get(window, "reason", default=row_type) or row_type),
                metadata=dict(self._get(window, "metadata", default={}) or {}),
            )
            row.update(
                {
                    "motion_score": self._clamp(self._get(window, "motion_score", default=0.0)),
                    "scene_change_score": self._clamp(self._get(window, "scene_change_score", default=0.0)),
                    "visual_activity_score": self._clamp(self._get(window, "visual_activity_score", default=0.0)),
                }
            )
            rows.append(row)
        return rows

    def _facecam_rows(self, facecam_reaction_result: object) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for index, window in enumerate(self._iter_items(self._get(facecam_reaction_result, "windows", default=[]))):
            start, end = self._start_end(window)
            if end <= start:
                continue
            label = str(self._get(window, "label", default="unknown") or "unknown")
            reaction_score = self._clamp(self._get(window, "reaction_score", default=0.0))
            row = self._row(
                source="facecam",
                row_id=f"facecam_{index:06d}",
                row_type=label,
                start=start,
                end=end,
                score=reaction_score,
                confidence=0.66 if reaction_score >= 0.24 else 0.44,
                note=str(self._get(window, "reason", default=label) or label),
            )
            row.update(
                {
                    "reaction_score": reaction_score,
                    "motion_score": self._clamp(self._get(window, "motion_score", default=0.0)),
                    "expression_change_score": self._clamp(self._get(window, "expression_change_score", default=0.0)),
                }
            )
            rows.append(row)
        return rows

    def _emotion_rows(self, facecam_emotion_result: object) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for index, window in enumerate(self._iter_items(self._get(facecam_emotion_result, "windows", default=[]))):
            start, end = self._start_end(window)
            if end <= start:
                continue
            row_type = str(self._get(window, "emotion_type", default="unknown") or "unknown")
            rows.append(
                self._row(
                    source="facecam_emotion",
                    row_id=str(self._get(window, "emotion_id", default=f"emotion_{index:06d}") or f"emotion_{index:06d}"),
                    row_type=row_type,
                    start=start,
                    end=end,
                    score=self._clamp(self._get(window, "score", default=0.0)),
                    confidence=self._clamp(self._get(window, "confidence", default=0.0)),
                    note=str(self._get(window, "reason", default=row_type) or row_type),
                    metadata=dict(self._get(window, "metadata", default={}) or {}),
                )
            )
        return rows

    def _cut_rows(self, cut_indicator_result: object) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for index, indicator in enumerate(self._iter_items(self._get(cut_indicator_result, "indicators", default=[]))):
            start, end = self._start_end(indicator)
            if end <= start:
                continue
            row_type = str(self._get(indicator, "indicator_type", default="unknown") or "unknown")
            rows.append(
                self._row(
                    source="cut_indicator",
                    row_id=str(self._get(indicator, "indicator_id", default=f"cut_{index:06d}") or f"cut_{index:06d}"),
                    row_type=row_type,
                    start=start,
                    end=end,
                    score=self._clamp(self._get(indicator, "score", default=0.0)),
                    confidence=self._clamp(self._get(indicator, "confidence", default=0.0)),
                    note=str(self._get(indicator, "reason", default=row_type) or row_type),
                    metadata=dict(self._get(indicator, "metadata", default={}) or {}),
                )
            )
        return rows

    def _phase_rows(self, round_phase_result: object) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for index, phase in enumerate(self._iter_items(self._get(round_phase_result, "windows", default=[]))):
            start, end = self._start_end(phase)
            if end <= start:
                continue
            raw_phase = self._get(phase, "phase", default="unknown")
            phase_value = getattr(raw_phase, "value", raw_phase)
            row_type = str(phase_value or "unknown")
            confidence = self._clamp(self._get(phase, "confidence", default=0.0))
            rows.append(
                self._row(
                    source="round_phase",
                    row_id=f"phase_{index:06d}",
                    row_type=row_type,
                    start=start,
                    end=end,
                    score=confidence,
                    confidence=confidence,
                    note=f"round_phase:{row_type}",
                    metadata=dict(self._get(phase, "evidence", default={}) or {}),
                )
            )
        return rows

    def _row(
        self,
        *,
        source: str,
        row_id: str,
        row_type: str,
        start: float,
        end: float,
        score: float,
        confidence: float,
        text: str = "",
        note: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return {
            "source": source,
            "id": row_id,
            "type": str(row_type or "unknown"),
            "start": round(max(0.0, start), 3),
            "end": round(max(start, end), 3),
            "score": self._clamp(score),
            "confidence": self._clamp(confidence),
            "text": text,
            "note": note,
            "metadata": dict(metadata or {}),
        }

    def _overlapping_rows(
        self,
        rows: list[dict[str, Any]],
        start: float,
        end: float,
    ) -> list[dict[str, Any]]:
        return [
            row
            for row in rows
            if self._overlap_seconds(start, end, row["start"], row["end"]) > 0.0
        ]

    def _max_type_score(
        self,
        rows: list[dict[str, Any]],
        row_types: set[str],
        *,
        field: str = "score",
    ) -> float:
        return self._clamp(
            max(
                (self._clamp(row.get(field, row.get("score", 0.0))) for row in rows if row["type"] in row_types),
                default=0.0,
            )
        )

    def _max_field(self, rows: list[dict[str, Any]], field: str) -> float:
        return self._clamp(max((self._clamp(row.get(field, 0.0)) for row in rows), default=0.0))

    def _merge_ranges(self, ranges: list[tuple[float, float]]) -> list[tuple[float, float]]:
        clean = sorted((max(0.0, start), max(0.0, end)) for start, end in ranges if end > start)
        if not clean:
            return []
        merged: list[tuple[float, float]] = []
        current_start, current_end = clean[0]
        for start, end in clean[1:]:
            if start <= current_end:
                current_end = max(current_end, end)
                continue
            merged.append((current_start, current_end))
            current_start, current_end = start, end
        merged.append((current_start, current_end))
        return merged

    def _iter_items(self, value: object) -> list[Any]:
        if value is None:
            return []
        if isinstance(value, dict):
            return list(value.values())
        if isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            return list(value)
        return []

    def _get(self, item: object, *names: str, default: object = None) -> object:
        if isinstance(item, dict):
            for name in names:
                if name in item:
                    return item[name]
            return default
        for name in names:
            value = getattr(item, name, None)
            if value is not None:
                return value
        return default

    def _start_end(self, item: object) -> tuple[float, float]:
        start = max(0.0, self._safe_float(self._get(item, "start_seconds", "start_time", default=0.0)))
        end = max(start, self._safe_float(self._get(item, "end_seconds", "end_time", default=start), start))
        return round(start, 3), round(end, 3)

    def _safe_float(self, value: object, fallback: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return fallback

    def _clamp(self, value: object, fallback: float = 0.0) -> float:
        return round(max(0.0, min(1.0, self._safe_float(value, fallback))), 3)

    def _overlap_seconds(self, start_a: float, end_a: float, start_b: float, end_b: float) -> float:
        return max(0.0, min(end_a, end_b) - max(start_a, start_b))

    def _log_summary(self, result: UniversalMomentResult) -> None:
        print(
            "[UNIVERSAL-MOMENT-BRAIN] "
            f"windows={result.total_windows} "
            f"keep={result.keep_windows} "
            f"remove={result.remove_windows} "
            f"cut_risk={result.cut_risk_windows} "
            f"zoom_risk={result.zoom_risk_windows} "
            f"avg={result.avg_moment_score} "
            f"max={result.max_moment_score}"
        )
        type_counts: dict[str, int] = {}
        for window in result.windows:
            type_counts[window.moment_type] = type_counts.get(window.moment_type, 0) + 1
        print(
            "[UNIVERSAL-MOMENT-BRAIN] "
            "top_types "
            f"active={type_counts.get('active_gameplay', 0)} "
            f"peak={type_counts.get('peak_action', 0)} "
            f"menu={type_counts.get('menu_wait', 0)} "
            f"private={type_counts.get('private_menu_talk', 0)} "
            f"boring={type_counts.get('boring_wait', 0)} "
            f"tension={type_counts.get('pre_action_tension', 0)}"
        )
