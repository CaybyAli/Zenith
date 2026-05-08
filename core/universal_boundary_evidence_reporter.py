from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from models.audio_role_result import AudioRoleResult, AudioRoleWindow
from models.phase_2b_final_review import Phase2BFinalReviewReport
from models.sentence_timeline import SentenceItem, SentenceTimelineResult
from models.timeline_segment import TimelineSegment
from models.transcript_result import TranscriptResult, TranscriptSegment
from models.universal_boundary_evidence import (
    ENGINE,
    UniversalBoundaryEvidence,
    UniversalBoundaryEvidenceReport,
)
from models.universal_context_audit import (
    UniversalContextAuditReport,
    UniversalSegmentContextAudit,
)
from models.universal_moment_result import UniversalMomentResult, UniversalMomentWindow


EDGE_RADIUS_SECONDS = 0.75
SPEECH_LINK_SECONDS = 0.35
MIN_INTERIOR_EDGE_DISTANCE = 0.18
TRANSCRIPT_EXACT_MAX_SECONDS = 4.0
TRANSCRIPT_BROAD_SECONDS = 6.0
SENTENCE_EXACT_MAX_SECONDS = 8.0
SENTENCE_BROAD_SECONDS = 12.0
SPEECH_ROLE_TYPES = {
    "speech_active",
    "secondary_speech_like",
    "shout_like_audio",
    "group_reaction_like",
}
ACTION_MOMENT_TYPES = {"peak_action", "pre_action_tension", "post_peak_reaction"}


@dataclass(frozen=True)
class _TimeItem:
    start: float
    end: float
    kind: str = "unknown"
    score: float = 0.0
    confidence: float = 0.0

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


@dataclass(frozen=True)
class _EdgeEvent:
    found: bool = False
    contains: bool = False
    distance: float | None = None
    relative_position: float | None = None
    duration: float | None = None
    confidence: float = 0.0


@dataclass(frozen=True)
class _SourceCalibration:
    left_near: bool = False
    right_near: bool = False
    crosses: bool = False
    contains_edge: bool = False
    edge_distance_left: float | None = None
    edge_distance_right: float | None = None
    relative_position: float | None = None
    duration: float | None = None
    confidence: float = 0.0
    quality: str = "none"
    mid_span: bool = False
    broad_span: bool = False
    edge_aligned: bool = False


class UniversalBoundaryEvidenceReporter:
    engine = ENGINE

    def build(
        self,
        *,
        job_id: str,
        timeline_segments: list[TimelineSegment],
        transcript_result=None,
        sentence_timeline_result=None,
        audio_role_result=None,
        universal_moment_result=None,
        context_audit_report=None,
        final_review_report=None,
    ) -> UniversalBoundaryEvidenceReport:
        segments = sorted(
            [
                segment
                for segment in (timeline_segments or [])
                if self._seconds(getattr(segment, "end_time", 0.0))
                > self._seconds(getattr(segment, "start_time", 0.0))
            ],
            key=lambda item: (
                self._seconds(getattr(item, "start_time", 0.0)),
                self._seconds(getattr(item, "end_time", 0.0)),
                str(getattr(item, "segment_id", "") or ""),
            ),
        )
        transcript_items = self._transcript_items(transcript_result)
        sentence_items = self._sentence_items(sentence_timeline_result)
        audio_speech_items = self._audio_speech_items(audio_role_result)
        moment_windows = self._moment_windows(universal_moment_result)
        context_report = self._context_report(context_audit_report, job_id=job_id)
        final_report = self._final_review_report(final_review_report, job_id=job_id)
        context_by_id = {
            item.segment_id: item
            for item in context_report.segments
            if item.segment_id
        }
        final_by_id = {
            item.segment_id: item
            for item in final_report.segments
            if item.segment_id
        }

        boundaries: list[UniversalBoundaryEvidence] = []
        for index in range(max(0, len(segments) - 1)):
            left = segments[index]
            right = segments[index + 1]
            boundaries.append(
                self._build_boundary(
                    job_id=job_id,
                    boundary_index=index + 1,
                    left=left,
                    right=right,
                    transcript_items=transcript_items,
                    sentence_items=sentence_items,
                    audio_speech_items=audio_speech_items,
                    moment_windows=moment_windows,
                    left_context=context_by_id.get(left.segment_id),
                    right_context=context_by_id.get(right.segment_id),
                    left_final=final_by_id.get(left.segment_id),
                    right_final=final_by_id.get(right.segment_id),
                )
            )

        report = UniversalBoundaryEvidenceReport(
            job_id=str(job_id or context_report.job_id or final_report.job_id or ""),
            engine=self.engine,
            boundaries=boundaries,
        )
        self._log(report)
        return report

    def _build_boundary(
        self,
        *,
        job_id: str,
        boundary_index: int,
        left: TimelineSegment,
        right: TimelineSegment,
        transcript_items: list[_TimeItem],
        sentence_items: list[_TimeItem],
        audio_speech_items: list[_TimeItem],
        moment_windows: list[UniversalMomentWindow],
        left_context: UniversalSegmentContextAudit | None,
        right_context: UniversalSegmentContextAudit | None,
        left_final: object | None,
        right_final: object | None,
    ) -> UniversalBoundaryEvidence:
        left_end = self._seconds(left.end_time)
        right_start = self._seconds(right.start_time)
        gap = round(max(0.0, right_start - left_end), 3)
        evidence_start = max(0.0, left_end - EDGE_RADIUS_SECONDS)
        evidence_end = right_start + EDGE_RADIUS_SECONDS
        left_window = (evidence_start, left_end)
        right_window = (right_start, evidence_end)

        transcript_calibration = self._calibrate_source(
            transcript_items,
            left_window=left_window,
            right_window=right_window,
            left_end=left_end,
            right_start=right_start,
            kind="transcript",
        )
        sentence_calibration = self._calibrate_source(
            sentence_items,
            left_window=left_window,
            right_window=right_window,
            left_end=left_end,
            right_start=right_start,
            kind="sentence",
        )
        audio_calibration = self._calibrate_source(
            audio_speech_items,
            left_window=left_window,
            right_window=right_window,
            left_end=left_end,
            right_start=right_start,
            kind="audio",
        )

        word_cut_confidence = self._word_cut_confidence(transcript_calibration, audio_calibration)
        sentence_cut_confidence = self._sentence_cut_confidence(sentence_calibration, audio_calibration)
        timestamp_uncertainty = self._timestamp_uncertainty(
            transcript_calibration,
            sentence_calibration,
            audio_calibration,
        )
        audio_speech_confidence = self._audio_speech_confidence(audio_calibration)
        speech_classification = self._speech_boundary_classification(
            transcript_calibration=transcript_calibration,
            sentence_calibration=sentence_calibration,
            audio_calibration=audio_calibration,
            word_cut_confidence=word_cut_confidence,
            sentence_cut_confidence=sentence_cut_confidence,
            timestamp_uncertainty=timestamp_uncertainty,
            audio_speech_confidence=audio_speech_confidence,
        )
        speech_score = self._calibrated_speech_risk_score(
            classification=speech_classification,
            word_cut_confidence=word_cut_confidence,
            sentence_cut_confidence=sentence_cut_confidence,
            timestamp_uncertainty=timestamp_uncertainty,
            audio_speech_confidence=audio_speech_confidence,
        )
        likely_word_cut = word_cut_confidence >= 0.55
        likely_sentence_cut = sentence_cut_confidence >= 0.55
        speech_crosses = (
            transcript_calibration.crosses
            or sentence_calibration.crosses
            or audio_calibration.crosses
        )
        transcript_only_risk = (
            transcript_calibration.quality in {"exact", "likely", "uncertain", "weak"}
            and sentence_calibration.quality == "none"
            and audio_calibration.quality == "none"
        )
        audio_only_risk = speech_classification == "audio_only_near_edge"
        sentence_span_too_broad = sentence_calibration.broad_span

        left_edge_windows = self._windows_near(moment_windows, left_window[0], left_window[1])
        right_edge_windows = self._windows_near(moment_windows, right_window[0], right_window[1])
        action_left = self._has_action(left_edge_windows)
        action_right = self._has_action(right_edge_windows)
        peak_left = self._has_peak(left_edge_windows)
        peak_right = self._has_peak(right_edge_windows)
        tension_left = self._has_tension(left_edge_windows)
        tension_right = self._has_tension(right_edge_windows)
        reaction_left = self._has_reaction(left_edge_windows)
        reaction_right = self._has_reaction(right_edge_windows)
        cut_left = self._has_cut_risk(left_edge_windows)
        cut_right = self._has_cut_risk(right_edge_windows)
        zoom_left = self._has_zoom_risk(left_edge_windows)
        zoom_right = self._has_zoom_risk(right_edge_windows)
        menu_left = self._has_menu_wait(left_edge_windows)
        menu_right = self._has_menu_wait(right_edge_windows)
        boring_left = self._has_boring(left_edge_windows)
        boring_right = self._has_boring(right_edge_windows)

        action_score = self._action_score(
            action_left=action_left,
            action_right=action_right,
            peak_left=peak_left,
            peak_right=peak_right,
            tension_left=tension_left,
            tension_right=tension_right,
            reaction_left=reaction_left,
            reaction_right=reaction_right,
        )
        zoom_score = 0.8 if zoom_left or zoom_right else 0.0
        menu_score = 0.75 if menu_left and menu_right else 0.62 if menu_left or menu_right else 0.0
        boring_score = 0.75 if boring_left and boring_right else 0.62 if boring_left or boring_right else 0.0

        context_warned = self._context_or_final_warned(
            left_context=left_context,
            right_context=right_context,
            left_final=left_final,
            right_final=right_final,
        )
        downgrade_candidate = (
            context_warned
            and speech_classification
            in {"audio_only_near_edge", "weak_speech_evidence", "probably_safe"}
            and action_score < 0.65
            and zoom_score < 0.70
        )
        false_positive_score = self._false_positive_score(
            context_warned=context_warned,
            speech_classification=speech_classification,
            audio_speech_confidence=audio_speech_confidence,
            speech_score=speech_score,
            action_score=action_score,
            zoom_score=zoom_score,
        )
        boundary_type = self._boundary_type(
            speech_classification=speech_classification,
            speech_score=speech_score,
            action_score=action_score,
            zoom_score=zoom_score,
            menu_left=menu_left,
            menu_right=menu_right,
            action_left=action_left or peak_left or tension_left or reaction_left,
            action_right=action_right or peak_right or tension_right or reaction_right,
            boring_left=boring_left,
            boring_right=boring_right,
            gap_seconds=gap,
            false_positive_score=false_positive_score,
        )
        priority = self._priority(
            boundary_type=boundary_type,
            speech_classification=speech_classification,
            audio_speech_confidence=audio_speech_confidence,
            action_score=action_score,
            zoom_score=zoom_score,
            false_positive_score=false_positive_score,
        )
        risk_score = self._risk_score(
            boundary_type=boundary_type,
            speech_score=speech_score,
            action_score=action_score,
            zoom_score=zoom_score,
            menu_score=menu_score,
            boring_score=boring_score,
            false_positive_score=false_positive_score,
        )
        reasons, warnings, notes = self._explain(
            boundary_type=boundary_type,
            speech_classification=speech_classification,
            transcript_quality=transcript_calibration.quality,
            sentence_quality=sentence_calibration.quality,
            context_warned=context_warned,
            likely_word_cut=likely_word_cut,
            likely_sentence_cut=likely_sentence_cut,
            speech_crosses=speech_crosses,
            speech_score=speech_score,
            word_cut_confidence=word_cut_confidence,
            sentence_cut_confidence=sentence_cut_confidence,
            timestamp_uncertainty=timestamp_uncertainty,
            audio_speech_confidence=audio_speech_confidence,
            sentence_span_too_broad=sentence_span_too_broad,
            downgrade_candidate=downgrade_candidate,
            action_score=action_score,
            zoom_score=zoom_score,
            menu_left=menu_left,
            menu_right=menu_right,
            boring_left=boring_left,
            boring_right=boring_right,
            false_positive_score=false_positive_score,
        )

        return UniversalBoundaryEvidence(
            boundary_id=f"{job_id or 'job'}_boundary_{boundary_index:02d}",
            job_id=str(job_id or ""),
            boundary_index=boundary_index,
            left_segment_id=left.segment_id,
            right_segment_id=right.segment_id,
            left_role=left.segment_role,
            right_role=right.segment_role,
            left_end_time=left_end,
            right_start_time=right_start,
            gap_seconds=gap,
            evidence_start_time=evidence_start,
            evidence_end_time=evidence_end,
            edge_radius_seconds=EDGE_RADIUS_SECONDS,
            transcript_left_near_edge=transcript_calibration.left_near,
            transcript_right_near_edge=transcript_calibration.right_near,
            sentence_left_near_edge=sentence_calibration.left_near,
            sentence_right_near_edge=sentence_calibration.right_near,
            audio_speech_left_near_edge=audio_calibration.left_near,
            audio_speech_right_near_edge=audio_calibration.right_near,
            speech_crosses_boundary=speech_crosses,
            sentence_crosses_boundary=sentence_calibration.crosses,
            likely_word_cut=likely_word_cut,
            likely_sentence_cut=likely_sentence_cut,
            transcript_edge_distance_left=transcript_calibration.edge_distance_left,
            transcript_edge_distance_right=transcript_calibration.edge_distance_right,
            sentence_edge_distance_left=sentence_calibration.edge_distance_left,
            sentence_edge_distance_right=sentence_calibration.edge_distance_right,
            audio_edge_distance_left=audio_calibration.edge_distance_left,
            audio_edge_distance_right=audio_calibration.edge_distance_right,
            word_cut_confidence=word_cut_confidence,
            sentence_cut_confidence=sentence_cut_confidence,
            transcript_timestamp_uncertainty=timestamp_uncertainty,
            audio_speech_confidence=audio_speech_confidence,
            calibrated_speech_risk_score=speech_score,
            transcript_evidence_quality=transcript_calibration.quality,
            sentence_evidence_quality=sentence_calibration.quality,
            speech_boundary_classification=speech_classification,
            transcript_only_risk=transcript_only_risk,
            audio_only_risk=audio_only_risk,
            sentence_span_too_broad=sentence_span_too_broad,
            downgrade_candidate=downgrade_candidate,
            action_left_near_edge=action_left,
            action_right_near_edge=action_right,
            peak_left_near_edge=peak_left,
            peak_right_near_edge=peak_right,
            tension_left_near_edge=tension_left,
            tension_right_near_edge=tension_right,
            reaction_left_near_edge=reaction_left,
            reaction_right_near_edge=reaction_right,
            cut_risk_left_near_edge=cut_left,
            cut_risk_right_near_edge=cut_right,
            zoom_risk_left_near_edge=zoom_left,
            zoom_risk_right_near_edge=zoom_right,
            menu_wait_left_near_edge=menu_left,
            menu_wait_right_near_edge=menu_right,
            boring_left_near_edge=boring_left,
            boring_right_near_edge=boring_right,
            speech_evidence_score=speech_score,
            action_evidence_score=action_score,
            zoom_evidence_score=zoom_score,
            menu_evidence_score=menu_score,
            boring_evidence_score=boring_score,
            false_positive_score=false_positive_score,
            boundary_risk_score=risk_score,
            boundary_type=boundary_type,
            priority=priority,
            should_protect_boundary=priority == "real_high"
            or boundary_type in {"real_speech_cut_risk", "action_cut_risk"},
            should_review_boundary=priority in {"real_high", "medium"},
            can_ignore_warning=priority == "false_positive" or boundary_type == "clean",
            needs_transcript_check=speech_classification
            in {
                "real_word_cut",
                "real_sentence_cut",
                "likely_speech_cut",
                "timestamp_uncertain",
                "weak_speech_evidence",
            },
            needs_visual_check=boundary_type in {"action_cut_risk", "zoom_cut_risk", "menu_jump"},
            reasons=reasons,
            warnings=warnings,
            evidence_notes=notes,
        )

    def _calibrate_source(
        self,
        items: list[_TimeItem],
        *,
        left_window: tuple[float, float],
        right_window: tuple[float, float],
        left_end: float,
        right_start: float,
        kind: str,
    ) -> _SourceCalibration:
        left_near = self._near_edge(items, *left_window, edge_time=left_end)
        right_near = self._near_edge(items, *right_window, edge_time=right_start)
        crosses = self._crosses_boundary(items, left_end, right_start)
        left_event = self._edge_event(items, left_end)
        right_event = self._edge_event(items, right_start)
        best_event = self._best_edge_event(left_event, right_event)
        contains_edge = left_event.contains or right_event.contains
        broad_seconds = self._broad_seconds(kind)
        exact_seconds = self._exact_seconds(kind)
        broad_span = bool(best_event.duration is not None and best_event.duration > broad_seconds)
        edge_distance = best_event.distance if best_event.distance is not None else 0.0
        relative = best_event.relative_position
        mid_span = bool(
            contains_edge
            and relative is not None
            and 0.15 <= relative <= 0.85
            and edge_distance >= MIN_INTERIOR_EDGE_DISTANCE
            and best_event.duration is not None
            and best_event.duration <= exact_seconds
        )
        edge_aligned = bool(
            contains_edge
            and (
                relative is None
                or relative < 0.15
                or relative > 0.85
                or edge_distance < MIN_INTERIOR_EDGE_DISTANCE
            )
        )
        confidence = self._score(best_event.confidence)
        quality = self._source_quality(
            left_near=left_near,
            right_near=right_near,
            crosses=crosses,
            contains_edge=contains_edge,
            mid_span=mid_span,
            broad_span=broad_span,
            edge_aligned=edge_aligned,
            confidence=confidence,
        )
        return _SourceCalibration(
            left_near=left_near,
            right_near=right_near,
            crosses=crosses,
            contains_edge=contains_edge,
            edge_distance_left=left_event.distance,
            edge_distance_right=right_event.distance,
            relative_position=relative,
            duration=best_event.duration,
            confidence=confidence,
            quality=quality,
            mid_span=mid_span,
            broad_span=broad_span,
            edge_aligned=edge_aligned,
        )

    def _edge_event(self, items: list[_TimeItem], edge_time: float) -> _EdgeEvent:
        candidates: list[tuple[tuple[float, float, float], _TimeItem, bool, float, float | None]] = []
        start = max(0.0, edge_time - EDGE_RADIUS_SECONDS)
        end = edge_time + EDGE_RADIUS_SECONDS
        for item in items:
            contains = self._contains_time(item, edge_time)
            overlap = self._overlap_seconds(start, end, item.start, item.end)
            outside_distance = max(item.start - edge_time, edge_time - item.end, 0.0)
            if not contains and overlap <= 0.0 and outside_distance > EDGE_RADIUS_SECONDS:
                continue
            if contains:
                distance = min(edge_time - item.start, item.end - edge_time)
                relative = (edge_time - item.start) / item.duration if item.duration > 0 else None
                sort_key = (0.0, -distance, item.duration)
            else:
                distance = outside_distance
                relative = None
                sort_key = (1.0, distance, item.duration)
            candidates.append((sort_key, item, contains, distance, relative))
        if not candidates:
            return _EdgeEvent()
        _, item, contains, distance, relative = sorted(candidates, key=lambda value: value[0])[0]
        return _EdgeEvent(
            found=True,
            contains=contains,
            distance=round(max(0.0, distance), 3),
            relative_position=self._rounded_optional(relative),
            duration=round(item.duration, 3),
            confidence=self._score(max(item.score, item.confidence)),
        )

    def _best_edge_event(self, left_event: _EdgeEvent, right_event: _EdgeEvent) -> _EdgeEvent:
        events = [event for event in (left_event, right_event) if event.found]
        if not events:
            return _EdgeEvent()
        contains = [event for event in events if event.contains]
        if contains:
            return sorted(
                contains,
                key=lambda event: (
                    -(event.distance or 0.0),
                    event.duration or 999.0,
                    -event.confidence,
                ),
            )[0]
        return sorted(
            events,
            key=lambda event: (
                event.distance if event.distance is not None else 999.0,
                event.duration or 999.0,
                -event.confidence,
            ),
        )[0]

    def _source_quality(
        self,
        *,
        left_near: bool,
        right_near: bool,
        crosses: bool,
        contains_edge: bool,
        mid_span: bool,
        broad_span: bool,
        edge_aligned: bool,
        confidence: float,
    ) -> str:
        if not (left_near or right_near or crosses or contains_edge):
            return "none"
        if mid_span and not broad_span and confidence >= 0.70:
            return "exact"
        if mid_span and not broad_span and confidence >= 0.45:
            return "likely"
        if contains_edge and (broad_span or confidence < 0.45 or edge_aligned):
            return "uncertain"
        if crosses and confidence >= 0.45 and not broad_span:
            return "likely"
        if left_near and right_near and confidence >= 0.45:
            return "likely"
        return "weak"

    def _word_cut_confidence(
        self,
        transcript: _SourceCalibration,
        audio: _SourceCalibration,
    ) -> float:
        if transcript.quality == "none":
            return 0.0
        if transcript.mid_span and not transcript.broad_span:
            base = 0.72 if transcript.quality == "exact" else 0.58
        elif transcript.quality == "likely":
            base = 0.48
        elif transcript.quality == "uncertain":
            base = 0.34
        else:
            base = 0.24
        if audio.quality in {"exact", "likely"} or audio.confidence >= 0.55:
            base += 0.18
        elif audio.quality == "weak" or audio.confidence > 0.0:
            base += 0.04
        else:
            base -= 0.10
        if transcript.broad_span:
            base -= 0.18
        if transcript.edge_aligned:
            base -= 0.14
        return self._score(base)

    def _sentence_cut_confidence(
        self,
        sentence: _SourceCalibration,
        audio: _SourceCalibration,
    ) -> float:
        if sentence.quality == "none":
            return 0.0
        if sentence.mid_span and not sentence.broad_span:
            base = 0.78 if sentence.quality == "exact" else 0.64
        elif sentence.quality == "likely":
            base = 0.52
        elif sentence.quality == "uncertain":
            base = 0.38
        else:
            base = 0.26
        if audio.confidence >= 0.55:
            base += 0.08
        if sentence.broad_span:
            base -= 0.22
        if sentence.edge_aligned:
            base -= 0.10
        return self._score(base)

    def _timestamp_uncertainty(
        self,
        transcript: _SourceCalibration,
        sentence: _SourceCalibration,
        audio: _SourceCalibration,
    ) -> float:
        score = 0.0
        if transcript.quality == "uncertain":
            edge_only = transcript.edge_aligned and not transcript.broad_span and transcript.confidence >= 0.45
            score = max(score, 0.42 if edge_only else 0.46)
        if sentence.quality == "uncertain":
            edge_only = sentence.edge_aligned and not sentence.broad_span and sentence.confidence >= 0.45
            score = max(score, 0.44 if edge_only else 0.50)
        if transcript.broad_span:
            score = max(score, 0.56)
        if sentence.broad_span:
            score = max(score, 0.64)
        if transcript.confidence and transcript.confidence < 0.45:
            score = max(score, 0.58)
        if sentence.confidence and sentence.confidence < 0.45:
            score = max(score, 0.58)
        if (
            score > 0.0
            and audio.confidence < 0.35
            and (
                transcript.broad_span
                or sentence.broad_span
                or (transcript.confidence and transcript.confidence < 0.45)
                or (sentence.confidence and sentence.confidence < 0.45)
            )
        ):
            score += 0.05
        if transcript.quality in {"exact", "likely"} and sentence.quality in {"exact", "likely"}:
            score -= 0.12
        return self._score(score)

    def _audio_speech_confidence(self, audio: _SourceCalibration) -> float:
        if audio.quality == "none":
            return 0.0
        base = audio.confidence
        if audio.left_near and audio.right_near:
            base = max(base, 0.62)
        if audio.crosses or audio.contains_edge:
            base = max(base, 0.58)
        return self._score(base)

    def _speech_boundary_classification(
        self,
        *,
        transcript_calibration: _SourceCalibration,
        sentence_calibration: _SourceCalibration,
        audio_calibration: _SourceCalibration,
        word_cut_confidence: float,
        sentence_cut_confidence: float,
        timestamp_uncertainty: float,
        audio_speech_confidence: float,
    ) -> str:
        transcript_present = transcript_calibration.quality != "none"
        sentence_present = sentence_calibration.quality != "none"
        audio_present = audio_calibration.quality != "none" or audio_speech_confidence > 0.0

        if (
            transcript_calibration.mid_span
            and not transcript_calibration.broad_span
            and word_cut_confidence >= 0.78
            and audio_speech_confidence >= 0.50
        ):
            return "real_word_cut"
        if (
            sentence_calibration.mid_span
            and not sentence_calibration.broad_span
            and sentence_cut_confidence >= 0.70
        ):
            return "real_sentence_cut"
        if (
            timestamp_uncertainty >= 0.50
            and (transcript_calibration.broad_span or sentence_calibration.broad_span)
            and (transcript_present or sentence_present)
        ):
            return "timestamp_uncertain"
        if (
            (
                transcript_calibration.quality == "likely"
                and transcript_calibration.left_near
                and transcript_calibration.right_near
            )
            or (
                sentence_calibration.quality == "likely"
                and sentence_calibration.left_near
                and sentence_calibration.right_near
            )
        ):
            return "likely_speech_cut"
        if (
            audio_present
            and audio_speech_confidence >= 0.55
            and (transcript_calibration.left_near or transcript_calibration.right_near
                 or sentence_calibration.left_near or sentence_calibration.right_near)
        ):
            return "likely_speech_cut"
        if audio_present and not transcript_present and not sentence_present:
            return "audio_only_near_edge"
        if (
            timestamp_uncertainty >= 0.50
            and (transcript_present or sentence_present)
            and audio_speech_confidence < 0.55
        ):
            return "timestamp_uncertain"
        if transcript_present or sentence_present or audio_present:
            return "weak_speech_evidence"
        return "probably_safe"

    def _calibrated_speech_risk_score(
        self,
        *,
        classification: str,
        word_cut_confidence: float,
        sentence_cut_confidence: float,
        timestamp_uncertainty: float,
        audio_speech_confidence: float,
    ) -> float:
        if classification == "real_word_cut":
            return self._score(max(0.90, 0.90 + min(word_cut_confidence, audio_speech_confidence) * 0.10))
        if classification == "real_sentence_cut":
            return self._score(max(0.80, 0.80 + sentence_cut_confidence * 0.15))
        if classification == "likely_speech_cut":
            return self._score(0.60 + min(0.20, max(word_cut_confidence, sentence_cut_confidence, audio_speech_confidence) * 0.20))
        if classification == "timestamp_uncertain":
            return self._score(0.40 + min(0.25, timestamp_uncertainty * 0.25))
        if classification == "audio_only_near_edge":
            return self._score(0.35 + min(0.25, audio_speech_confidence * 0.25))
        if classification == "weak_speech_evidence":
            return self._score(0.20 + min(0.25, max(word_cut_confidence, sentence_cut_confidence, audio_speech_confidence) * 0.25))
        if classification == "probably_safe":
            return self._score(0.08 + min(0.17, max(word_cut_confidence, sentence_cut_confidence, audio_speech_confidence) * 0.17))
        return 0.0

    def _broad_seconds(self, kind: str) -> float:
        if kind == "sentence":
            return SENTENCE_BROAD_SECONDS
        if kind == "transcript":
            return TRANSCRIPT_BROAD_SECONDS
        return SENTENCE_BROAD_SECONDS

    def _exact_seconds(self, kind: str) -> float:
        if kind == "sentence":
            return SENTENCE_EXACT_MAX_SECONDS
        if kind == "transcript":
            return TRANSCRIPT_EXACT_MAX_SECONDS
        return SENTENCE_EXACT_MAX_SECONDS

    def _action_score(
        self,
        *,
        action_left: bool,
        action_right: bool,
        peak_left: bool,
        peak_right: bool,
        tension_left: bool,
        tension_right: bool,
        reaction_left: bool,
        reaction_right: bool,
    ) -> float:
        strong_left = peak_left or tension_left or reaction_left
        strong_right = peak_right or tension_right or reaction_right
        if strong_left and strong_right:
            return 0.86
        if strong_left or strong_right:
            return 0.72
        if action_left and action_right:
            return 0.68
        if action_left or action_right:
            return 0.58
        return 0.0

    def _false_positive_score(
        self,
        *,
        context_warned: bool,
        speech_classification: str,
        audio_speech_confidence: float,
        speech_score: float,
        action_score: float,
        zoom_score: float,
    ) -> float:
        if not context_warned:
            return 0.0
        if speech_classification == "probably_safe" and action_score < 0.45 and zoom_score < 0.45:
            return 0.88
        if speech_classification == "weak_speech_evidence" and action_score < 0.45 and zoom_score < 0.45:
            return 0.74
        if speech_classification == "audio_only_near_edge" and audio_speech_confidence < 0.50 and action_score < 0.45 and zoom_score < 0.45:
            return 0.68
        if speech_score < 0.45 and action_score < 0.45 and zoom_score < 0.45:
            return 0.72
        return 0.0

    def _boundary_type(
        self,
        *,
        speech_classification: str,
        speech_score: float,
        action_score: float,
        zoom_score: float,
        menu_left: bool,
        menu_right: bool,
        action_left: bool,
        action_right: bool,
        boring_left: bool,
        boring_right: bool,
        gap_seconds: float,
        false_positive_score: float,
    ) -> str:
        if speech_classification in {"real_word_cut", "real_sentence_cut"} and speech_score >= 0.80:
            return "real_speech_cut_risk"
        if (menu_left and action_right) or (action_left and menu_right):
            return "menu_jump"
        if action_score >= 0.65:
            return "action_cut_risk"
        if zoom_score >= 0.70:
            return "zoom_cut_risk"
        if speech_classification in {
            "likely_speech_cut",
            "timestamp_uncertain",
            "audio_only_near_edge",
            "weak_speech_evidence",
        } and speech_score >= 0.20:
            return "possible_speech_cut_risk"
        if gap_seconds > 0.5 and (boring_left or boring_right or menu_left or menu_right) and speech_score < 0.45 and action_score < 0.45:
            return "boring_gap"
        if false_positive_score >= 0.70:
            return "likely_false_positive"
        if max(speech_score, action_score, zoom_score) < 0.35:
            return "clean"
        return "unknown"

    def _priority(
        self,
        *,
        boundary_type: str,
        speech_classification: str,
        audio_speech_confidence: float,
        action_score: float,
        zoom_score: float,
        false_positive_score: float,
    ) -> str:
        if false_positive_score >= 0.70 or boundary_type == "likely_false_positive":
            return "false_positive"
        if speech_classification in {"real_word_cut", "real_sentence_cut"}:
            return "real_high"
        if boundary_type in {"real_speech_cut_risk", "action_cut_risk", "zoom_cut_risk"}:
            return "real_high"
        if speech_classification in {"likely_speech_cut", "timestamp_uncertain"}:
            return "medium"
        if speech_classification == "audio_only_near_edge":
            return "medium" if audio_speech_confidence >= 0.70 or action_score >= 0.58 or zoom_score >= 0.58 else "low"
        if speech_classification == "weak_speech_evidence":
            return "low"
        if boundary_type in {"menu_jump", "boring_gap"}:
            return "medium"
        if boundary_type == "clean":
            return "low"
        return "unknown"

    def _risk_score(
        self,
        *,
        boundary_type: str,
        speech_score: float,
        action_score: float,
        zoom_score: float,
        menu_score: float,
        boring_score: float,
        false_positive_score: float,
    ) -> float:
        if boundary_type in {"likely_false_positive", "clean"} and false_positive_score >= 0.70:
            return 0.12
        if boundary_type == "clean":
            return 0.0
        return self._score(
            max(
                speech_score,
                action_score,
                zoom_score,
                menu_score * 0.72,
                boring_score * 0.60,
            )
        )

    def _explain(
        self,
        *,
        boundary_type: str,
        speech_classification: str,
        transcript_quality: str,
        sentence_quality: str,
        context_warned: bool,
        likely_word_cut: bool,
        likely_sentence_cut: bool,
        speech_crosses: bool,
        speech_score: float,
        word_cut_confidence: float,
        sentence_cut_confidence: float,
        timestamp_uncertainty: float,
        audio_speech_confidence: float,
        sentence_span_too_broad: bool,
        downgrade_candidate: bool,
        action_score: float,
        zoom_score: float,
        menu_left: bool,
        menu_right: bool,
        boring_left: bool,
        boring_right: bool,
        false_positive_score: float,
    ) -> tuple[list[str], list[str], list[str]]:
        reasons: list[str] = []
        warnings: list[str] = []
        notes: list[str] = []
        if boundary_type == "real_speech_cut_risk":
            if speech_classification == "real_word_cut":
                reasons.append("Transcript and audio evidence indicate a real word cut at the boundary.")
                warnings.append("Boundary transcript evidence: likely real word cut")
            elif speech_classification == "real_sentence_cut":
                reasons.append("Sentence evidence indicates a real sentence cut at the boundary.")
                warnings.append("Boundary transcript evidence: likely real sentence cut")
            else:
                reasons.append("Speech evidence crosses or contains the segment boundary.")
        elif boundary_type == "possible_speech_cut_risk":
            if speech_classification == "timestamp_uncertain":
                reasons.append("Transcript boundary evidence is present, but timestamp precision is uncertain.")
                warnings.append("Boundary transcript evidence: timestamp uncertain")
            elif speech_classification == "audio_only_near_edge":
                reasons.append("Audio speech is near the boundary, but transcript/sentence evidence does not confirm a cut.")
                warnings.append("Boundary transcript evidence: audio-only near edge")
            elif speech_classification == "likely_speech_cut":
                reasons.append("Speech evidence near the boundary is plausible, but no hard word/sentence cut is proven.")
            else:
                reasons.append("Speech evidence is weak near the boundary and should be spot-checked only if other risks agree.")
            warnings.append("Transcript check recommended before trusting this boundary warning.")
        elif boundary_type == "action_cut_risk":
            reasons.append("Peak/action/tension/reaction evidence is near the boundary.")
        elif boundary_type == "zoom_cut_risk":
            reasons.append("Zoom or framing risk evidence is near the boundary.")
        elif boundary_type == "menu_jump":
            reasons.append("Menu/private wait evidence and action evidence meet at the boundary.")
        elif boundary_type == "boring_gap":
            reasons.append("Boundary gap is dominated by boring/menu evidence with weak speech/action evidence.")
        elif boundary_type == "likely_false_positive":
            reasons.append("Context warned about speech, but boundary evidence does not confirm a speech/action/zoom cut.")
            warnings.append("Boundary warning can likely be ignored after spot-check.")
        elif boundary_type == "clean":
            reasons.append("No strong speech, action, zoom, menu-jump, or boring-gap risk found near the boundary.")
        else:
            reasons.append("Boundary evidence is mixed or too weak for a confident classification.")
        if context_warned:
            notes.append("Context/final review had a prior boundary warning.")
        notes.append(f"speech_boundary_classification={speech_classification}")
        notes.append(f"transcript_evidence_quality={transcript_quality}")
        notes.append(f"sentence_evidence_quality={sentence_quality}")
        if likely_word_cut:
            notes.append("Transcript word window contains the boundary time.")
        if likely_sentence_cut:
            notes.append("Sentence window contains the boundary time.")
        if speech_crosses:
            notes.append("Speech evidence crosses or links across the boundary.")
        if action_score >= 0.65:
            notes.append("Action evidence score is high near the boundary.")
        if zoom_score >= 0.70:
            notes.append("Zoom evidence score is high near the boundary.")
        if menu_left or menu_right:
            notes.append("Menu/wait evidence is present near the boundary.")
        if boring_left or boring_right:
            notes.append("Boring/dead-time evidence is present near the boundary.")
        if false_positive_score >= 0.70:
            notes.append("False-positive score is high because edge-local evidence is weak.")
        if sentence_span_too_broad:
            notes.append("Sentence span is too broad for exact boundary evidence.")
        if downgrade_candidate:
            notes.append("Boundary is a downgrade candidate because calibrated speech evidence is weak.")
        if speech_score > 0.0:
            notes.append(f"speech_evidence_score={speech_score:.3f}")
            notes.append(f"word_cut_confidence={word_cut_confidence:.3f}")
            notes.append(f"sentence_cut_confidence={sentence_cut_confidence:.3f}")
            notes.append(f"timestamp_uncertainty={timestamp_uncertainty:.3f}")
            notes.append(f"audio_speech_confidence={audio_speech_confidence:.3f}")
        return self._dedupe(reasons), self._dedupe(warnings), self._dedupe(notes)

    def _context_or_final_warned(
        self,
        *,
        left_context: UniversalSegmentContextAudit | None,
        right_context: UniversalSegmentContextAudit | None,
        left_final: object | None,
        right_final: object | None,
    ) -> bool:
        return any(
            [
                str(getattr(left_context, "next_boundary_type", "") or "") == "speech_cut_risk",
                str(getattr(right_context, "previous_boundary_type", "") or "") == "speech_cut_risk",
                bool(getattr(left_context, "should_protect_next_boundary", False)),
                bool(getattr(right_context, "should_protect_previous_boundary", False)),
                str(getattr(left_final, "next_boundary_type", "") or "") == "speech_cut_risk",
                str(getattr(right_final, "previous_boundary_type", "") or "") == "speech_cut_risk",
                bool(getattr(left_final, "protect_next_boundary", False)),
                bool(getattr(right_final, "protect_previous_boundary", False)),
            ]
        )

    def _near_edge(self, items: list[_TimeItem], start: float, end: float, *, edge_time: float) -> bool:
        return any(
            self._overlap_seconds(start, end, item.start, item.end) > 0.0
            or self._contains_time(item, edge_time)
            for item in items
        )

    def _crosses_boundary(self, items: list[_TimeItem], left_end: float, right_start: float) -> bool:
        if any(item.start < left_end and item.end > right_start for item in items):
            return True
        left_close = any(0.0 <= left_end - item.end <= SPEECH_LINK_SECONDS for item in items)
        right_close = any(0.0 <= item.start - right_start <= SPEECH_LINK_SECONDS for item in items)
        return left_close and right_close

    def _contains_time(self, item: _TimeItem, time_seconds: float) -> bool:
        return item.start < time_seconds < item.end

    def _windows_near(
        self,
        windows: list[UniversalMomentWindow],
        start: float,
        end: float,
    ) -> list[UniversalMomentWindow]:
        return [
            window
            for window in windows
            if self._overlap_seconds(start, end, window.start_seconds, window.end_seconds) > 0.0
        ]

    def _has_action(self, windows: list[UniversalMomentWindow]) -> bool:
        return any(
            max(window.visual_action_score, window.gameplay_motion_score) >= 0.60
            or str(window.moment_type or "") in ACTION_MOMENT_TYPES
            for window in windows
        )

    def _has_peak(self, windows: list[UniversalMomentWindow]) -> bool:
        return any(window.peak_score >= 0.60 or str(window.moment_type or "") == "peak_action" for window in windows)

    def _has_tension(self, windows: list[UniversalMomentWindow]) -> bool:
        return any(
            max(window.tension_score, window.pre_action_score) >= 0.60
            or str(window.moment_type or "") == "pre_action_tension"
            for window in windows
        )

    def _has_reaction(self, windows: list[UniversalMomentWindow]) -> bool:
        return any(
            window.post_peak_reaction_score >= 0.60
            or str(window.moment_type or "") == "post_peak_reaction"
            for window in windows
        )

    def _has_cut_risk(self, windows: list[UniversalMomentWindow]) -> bool:
        return any(window.cut_risk_score >= 0.70 for window in windows)

    def _has_zoom_risk(self, windows: list[UniversalMomentWindow]) -> bool:
        return any(window.zoom_risk_score >= 0.70 or bool(window.zoom_boundary_risk) for window in windows)

    def _has_menu_wait(self, windows: list[UniversalMomentWindow]) -> bool:
        return any(window.menu_wait_score >= 0.70 or bool(window.menu_private_risk) for window in windows)

    def _has_boring(self, windows: list[UniversalMomentWindow]) -> bool:
        return any(max(window.boring_score, window.dead_time_score) >= 0.70 for window in windows)

    def _transcript_items(self, transcript_result: Any) -> list[_TimeItem]:
        if transcript_result is None:
            return []
        if isinstance(transcript_result, dict):
            raw_items = transcript_result.get("segments", [])
        elif isinstance(transcript_result, TranscriptResult):
            raw_items = transcript_result.segments
        else:
            raw_items = getattr(transcript_result, "segments", []) or []
        result: list[_TimeItem] = []
        for item in raw_items:
            if isinstance(item, dict):
                start = item.get("start_seconds", item.get("start_time", 0.0))
                end = item.get("end_seconds", item.get("end_time", start))
                confidence = item.get("confidence", 0.75)
            elif isinstance(item, TranscriptSegment):
                start = item.start_seconds
                end = item.end_seconds
                confidence = item.confidence if item.confidence is not None else 0.75
            else:
                start = getattr(item, "start_seconds", getattr(item, "start_time", 0.0))
                end = getattr(item, "end_seconds", getattr(item, "end_time", start))
                confidence = getattr(item, "confidence", 0.75)
            parsed = self._time_item(start, end, kind="transcript", score=confidence, confidence=confidence)
            if parsed is not None:
                result.append(parsed)
        return sorted(result, key=lambda item: (item.start, item.end))

    def _sentence_items(self, sentence_timeline_result: Any) -> list[_TimeItem]:
        if sentence_timeline_result is None:
            return []
        if isinstance(sentence_timeline_result, dict):
            raw_items = sentence_timeline_result.get("sentences", [])
        elif isinstance(sentence_timeline_result, SentenceTimelineResult):
            raw_items = sentence_timeline_result.sentences
        else:
            raw_items = getattr(sentence_timeline_result, "sentences", []) or []
        result: list[_TimeItem] = []
        for item in raw_items:
            if isinstance(item, dict):
                start = item.get("start_seconds", item.get("start_time", 0.0))
                end = item.get("end_seconds", item.get("end_time", start))
                score = item.get("score", 1.0)
                confidence = item.get("confidence", score)
            elif isinstance(item, SentenceItem):
                start = item.start_seconds
                end = item.end_seconds
                score = item.score
                confidence = item.confidence
            else:
                start = getattr(item, "start_seconds", getattr(item, "start_time", 0.0))
                end = getattr(item, "end_seconds", getattr(item, "end_time", start))
                score = getattr(item, "score", 1.0)
                confidence = getattr(item, "confidence", score)
            parsed = self._time_item(start, end, kind="sentence", score=score, confidence=confidence)
            if parsed is not None:
                result.append(parsed)
        return sorted(result, key=lambda item: (item.start, item.end))

    def _audio_speech_items(self, audio_role_result: Any) -> list[_TimeItem]:
        if audio_role_result is None:
            return []
        if isinstance(audio_role_result, dict):
            raw_items = audio_role_result.get("windows", [])
        elif isinstance(audio_role_result, AudioRoleResult):
            raw_items = audio_role_result.windows
        else:
            raw_items = getattr(audio_role_result, "windows", []) or []
        result: list[_TimeItem] = []
        for item in raw_items:
            if isinstance(item, dict):
                role_type = str(item.get("role_type", "") or "")
                start = item.get("start_seconds", item.get("start_time", 0.0))
                end = item.get("end_seconds", item.get("end_time", start))
                score = item.get("score", 0.0)
                confidence = item.get("confidence", score)
            elif isinstance(item, AudioRoleWindow):
                role_type = item.role_type
                start = item.start_seconds
                end = item.end_seconds
                score = item.score
                confidence = item.confidence
            else:
                role_type = str(getattr(item, "role_type", "") or "")
                start = getattr(item, "start_seconds", getattr(item, "start_time", 0.0))
                end = getattr(item, "end_seconds", getattr(item, "end_time", start))
                score = getattr(item, "score", 0.0)
                confidence = getattr(item, "confidence", score)
            if role_type not in SPEECH_ROLE_TYPES:
                continue
            parsed = self._time_item(start, end, kind=role_type, score=score, confidence=confidence)
            if parsed is not None:
                result.append(parsed)
        return sorted(result, key=lambda item: (item.start, item.end))

    def _moment_windows(self, universal_moment_result: Any) -> list[UniversalMomentWindow]:
        if universal_moment_result is None:
            return []
        if isinstance(universal_moment_result, UniversalMomentResult):
            return sorted(
                [window for window in universal_moment_result.windows if window.end_seconds > window.start_seconds],
                key=lambda item: (item.start_seconds, item.end_seconds, item.window_id),
            )
        if isinstance(universal_moment_result, dict):
            return self._moment_windows(UniversalMomentResult.from_dict(universal_moment_result))
        raw_items = getattr(universal_moment_result, "windows", []) or []
        parsed: list[UniversalMomentWindow] = []
        for item in raw_items:
            if isinstance(item, UniversalMomentWindow):
                parsed.append(item)
            elif isinstance(item, dict):
                parsed.append(UniversalMomentWindow.from_dict(item))
        return sorted(
            [window for window in parsed if window.end_seconds > window.start_seconds],
            key=lambda item: (item.start_seconds, item.end_seconds, item.window_id),
        )

    def _context_report(self, report: Any, *, job_id: str) -> UniversalContextAuditReport:
        if isinstance(report, UniversalContextAuditReport):
            return report
        if isinstance(report, dict):
            return UniversalContextAuditReport.from_dict(report)
        if hasattr(report, "to_dict"):
            return UniversalContextAuditReport.from_dict(report.to_dict())
        return UniversalContextAuditReport(job_id=str(job_id or ""))

    def _final_review_report(self, report: Any, *, job_id: str) -> Phase2BFinalReviewReport:
        if isinstance(report, Phase2BFinalReviewReport):
            return report
        if isinstance(report, dict):
            return Phase2BFinalReviewReport.from_dict(report)
        if hasattr(report, "to_dict"):
            return Phase2BFinalReviewReport.from_dict(report.to_dict())
        return Phase2BFinalReviewReport(job_id=str(job_id or ""))

    def _time_item(
        self,
        start: object,
        end: object,
        *,
        kind: str,
        score: object,
        confidence: object | None = None,
    ) -> _TimeItem | None:
        parsed_start = self._seconds(start)
        parsed_end = self._seconds(end, fallback=parsed_start)
        if parsed_end <= parsed_start:
            return None
        parsed_score = self._score(score)
        return _TimeItem(
            start=parsed_start,
            end=parsed_end,
            kind=str(kind or "unknown"),
            score=parsed_score,
            confidence=self._score(confidence, parsed_score),
        )

    def _overlap_seconds(self, start_a: float, end_a: float, start_b: float, end_b: float) -> float:
        return max(0.0, min(end_a, end_b) - max(start_a, start_b))

    def _seconds(self, value: object, fallback: float = 0.0) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = fallback
        return round(max(0.0, numeric), 3)

    def _score(self, value: object, fallback: float = 0.0) -> float:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            numeric = fallback
        return round(max(0.0, min(1.0, numeric)), 3)

    def _rounded_optional(self, value: object) -> float | None:
        if value is None:
            return None
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return None
        return round(max(0.0, numeric), 3)

    def _dedupe(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            text = str(value or "")
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text)
            if len(result) >= 20:
                break
        return result

    def _log(self, report: UniversalBoundaryEvidenceReport) -> None:
        print(
            "[UNIVERSAL-BOUNDARY-EVIDENCE] "
            f"boundaries={report.total_boundaries} "
            f"high={report.real_high} "
            f"medium={report.medium} "
            f"low={report.low} "
            f"false_positive={report.false_positive} "
            f"clean={report.clean} "
            f"speech_real={report.real_speech_cut_risk} "
            f"speech_possible={report.possible_speech_cut_risk} "
            f"action={report.action_cut_risk} "
            f"zoom={report.zoom_cut_risk} "
            f"avg={report.avg_boundary_risk_score}"
        )
        print(
            "[UNIVERSAL-BOUNDARY-EVIDENCE-CALIBRATED] "
            f"real_word={report.real_word_cut} "
            f"real_sentence={report.real_sentence_cut} "
            f"likely={report.likely_speech_cut} "
            f"uncertain={report.timestamp_uncertain} "
            f"audio_only={report.audio_only_near_edge} "
            f"weak={report.weak_speech_evidence} "
            f"safe={report.probably_safe} "
            f"downgrade={report.downgrade_candidates}"
        )
