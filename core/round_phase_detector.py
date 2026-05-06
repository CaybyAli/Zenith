from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from models.analysis_result import AnalysisResult
from models.edit_signal import EditSignal
from models.gameplay_event_result import GameplayEventResult
from models.gameplay_vision_result import GameplayVisionResult, GameplayVisionWindow
from models.job import Job
from models.round_phase_result import RoundPhase, RoundPhaseResult, RoundPhaseWindow
from models.transcript_result import TranscriptResult


ACTIVE_MOTION_THRESHOLD = 0.20
ACTIVE_AUDIO_THRESHOLD = 0.30
LOW_MOTION_THRESHOLD = 0.08
MENU_MOTION_THRESHOLD = 0.05
MENU_AUDIO_THRESHOLD = 0.45
ROUND_END_SECONDS = 3.0
QUEUE_WAIT_MIN_SECONDS = 10.0
COUNTDOWN_LOOKAHEAD_SECONDS = 6.0

_COUNTDOWN_WORDS = frozenset({
    "3",
    "2",
    "1",
    "drei",
    "zwei",
    "eins",
    "countdown",
    "kickoff",
    "anstoss",
    "anstoß",
    "los",
})
_GOAL_WORDS = frozenset({"goal", "tor", "rein", "yeah", "ja", "boom"})


@dataclass
class _Sample:
    start: float
    end: float
    motion: float
    action: float
    audio: float
    silence: bool
    low_motion_signal: bool
    round_dead: bool
    replay: bool
    goal: bool
    kickoff: bool
    transcript_text: str


class RoundPhaseDetector:
    engine = "round-phase-detector-v1"

    def detect(
        self,
        job: Job,
        analysis_result: AnalysisResult,
        edit_signals: list[EditSignal] | None,
        audio_peaks=None,
        transcript_result: TranscriptResult | None = None,
        gameplay_vision_result: GameplayVisionResult | None = None,
        facecam_reaction_result=None,
        gameplay_event_result: GameplayEventResult | None = None,
    ) -> RoundPhaseResult:
        del job, facecam_reaction_result
        duration = max(0.0, float(getattr(analysis_result, "duration_seconds", 0.0) or 0.0))
        vision_windows = list(getattr(gameplay_vision_result, "windows", []) or [])
        if duration <= 0.0 or not vision_windows:
            return RoundPhaseResult(engine=self.engine, skipped_reason="missing_duration_or_vision")

        signals = sorted(edit_signals or [], key=lambda signal: (signal.start_time, signal.end_time))
        event_windows = list(getattr(gameplay_event_result, "windows", []) or [])
        peak_windows = list(self._audio_peak_windows(audio_peaks))
        samples = [
            self._sample_window(window, signals, peak_windows, event_windows, transcript_result)
            for window in vision_windows
            if window.end_seconds > window.start_seconds
        ]
        if not samples:
            return RoundPhaseResult(engine=self.engine, skipped_reason="no_samples")

        labels = self._label_samples(samples)
        raw_runs = self._runs(samples, labels)
        windows = self._convert_low_runs(raw_runs)
        windows = self._merge_adjacent(windows)
        result = RoundPhaseResult(windows=windows, engine=self.engine)
        counts = result.phase_counts
        print(
            "[ROUND-PHASE] "
            f"count={len(result.windows)} "
            f"active={counts.get(RoundPhase.ACTIVE_ROUND.value, 0)} "
            f"goals={counts.get(RoundPhase.GOAL_REPLAY.value, 0)} "
            f"round_end={counts.get(RoundPhase.ROUND_END.value, 0)} "
            f"menu_wait={counts.get(RoundPhase.MENU_WAIT.value, 0)} "
            f"queue_wait={counts.get(RoundPhase.QUEUE_WAIT.value, 0)} "
            f"countdown={counts.get(RoundPhase.COUNTDOWN_KICKOFF.value, 0)}"
        )
        return result

    def _sample_window(
        self,
        window: GameplayVisionWindow,
        signals: list[EditSignal],
        peak_windows: list[tuple[float, float, float]],
        event_windows,
        transcript_result: TranscriptResult | None,
    ) -> _Sample:
        start = window.start_seconds
        end = window.end_seconds
        audio = self._audio_score(start, end, signals, peak_windows)
        text = self._transcript_text(start, end, transcript_result)
        return _Sample(
            start=start,
            end=end,
            motion=window.motion_score,
            action=window.action_score,
            audio=audio,
            silence=self._has_signal(start, end, signals, {"silence_zone"}),
            low_motion_signal=self._has_signal(start, end, signals, {"low_motion_zone"}),
            round_dead=self._has_event(start, end, event_windows, {"round_end_dead_time"}),
            replay=self._has_event(start, end, event_windows, {"replay_like_moment"}),
            goal=self._has_event(start, end, event_windows, {"goal_or_save_like_flash"}),
            kickoff=self._has_event(start, end, event_windows, {"kickoff_like"}),
            transcript_text=text,
        )

    def _label_samples(self, samples: list[_Sample]) -> list[RoundPhase]:
        labels: list[RoundPhase] = []
        seen_active = False
        for sample in samples:
            if sample.kickoff or self._has_countdown_text(sample.transcript_text):
                labels.append(RoundPhase.COUNTDOWN_KICKOFF)
                continue
            if sample.replay or (sample.goal and self._has_goal_text(sample.transcript_text)):
                labels.append(RoundPhase.GOAL_REPLAY)
                continue
            active = (
                sample.motion >= ACTIVE_MOTION_THRESHOLD
                and sample.audio >= ACTIVE_AUDIO_THRESHOLD
            ) or (
                sample.action >= ACTIVE_MOTION_THRESHOLD
                and sample.audio >= ACTIVE_AUDIO_THRESHOLD / 2.0
            )
            if active:
                labels.append(RoundPhase.ACTIVE_ROUND)
                seen_active = True
                continue
            low_like = (
                sample.round_dead
                or sample.low_motion_signal
                or (
                    sample.motion <= LOW_MOTION_THRESHOLD
                    and (
                        sample.silence
                        or sample.audio <= MENU_AUDIO_THRESHOLD
                    )
                )
            )
            if low_like and (seen_active or sample.round_dead):
                labels.append(RoundPhase.MENU_WAIT)
            else:
                labels.append(RoundPhase.UNKNOWN)
        return labels

    def _runs(
        self,
        samples: list[_Sample],
        labels: list[RoundPhase],
    ) -> list[tuple[RoundPhase, list[_Sample]]]:
        runs: list[tuple[RoundPhase, list[_Sample]]] = []
        for sample, label in zip(samples, labels):
            if runs and runs[-1][0] == label and sample.start <= runs[-1][1][-1].end + 0.75:
                runs[-1][1].append(sample)
            else:
                runs.append((label, [sample]))
        return runs

    def _convert_low_runs(self, runs: list[tuple[RoundPhase, list[_Sample]]]) -> list[RoundPhaseWindow]:
        converted: list[RoundPhaseWindow] = []
        for index, (label, samples) in enumerate(runs):
            start = samples[0].start
            end = samples[-1].end
            duration = end - start
            if label != RoundPhase.MENU_WAIT:
                converted.append(self._window(label, start, end, samples))
                continue

            previous_phase = converted[-1].phase if converted else RoundPhase.UNKNOWN
            has_round_dead = any(sample.round_dead for sample in samples)
            if previous_phase in {RoundPhase.ACTIVE_ROUND, RoundPhase.GOAL_REPLAY} or has_round_dead:
                round_end_end = min(end, start + ROUND_END_SECONDS)
                converted.append(
                    RoundPhaseWindow(
                        start,
                        round_end_end,
                        RoundPhase.ROUND_END,
                        0.68 if has_round_dead else 0.58,
                        {"reason": "low_activity_after_active", "round_dead": has_round_dead},
                    )
                )
                if end - round_end_end <= 0.001:
                    continue
                wait_samples = [
                    sample for sample in samples if sample.end > round_end_end
                ]
                wait_phase = self._wait_phase_for_run(round_end_end, end, runs, index)
                converted.append(self._window(wait_phase, round_end_end, end, wait_samples or samples))
            else:
                wait_phase = RoundPhase.QUEUE_WAIT if duration >= QUEUE_WAIT_MIN_SECONDS else RoundPhase.UNKNOWN
                converted.append(self._window(wait_phase, start, end, samples))
        return [window for window in converted if window.end_seconds > window.start_seconds]

    def _wait_phase_for_run(
        self,
        start: float,
        end: float,
        runs: list[tuple[RoundPhase, list[_Sample]]],
        index: int,
    ) -> RoundPhase:
        wait_duration = end - start
        next_run = runs[index + 1] if index + 1 < len(runs) else None
        has_countdown_after = (
            next_run is not None
            and next_run[0] == RoundPhase.COUNTDOWN_KICKOFF
            and next_run[1][0].start - end <= COUNTDOWN_LOOKAHEAD_SECONDS
        )
        if wait_duration >= QUEUE_WAIT_MIN_SECONDS and not has_countdown_after:
            return RoundPhase.QUEUE_WAIT
        return RoundPhase.MENU_WAIT

    def _window(
        self,
        phase: RoundPhase,
        start: float,
        end: float,
        samples: list[_Sample],
    ) -> RoundPhaseWindow:
        if not samples:
            confidence = 0.5
        elif phase == RoundPhase.ACTIVE_ROUND:
            confidence = 0.62 + min(0.25, sum(sample.motion + sample.audio for sample in samples) / len(samples) * 0.2)
        elif phase == RoundPhase.MENU_WAIT:
            confidence = 0.64 + min(0.2, sum(1 for sample in samples if sample.silence or sample.round_dead) / max(1, len(samples)) * 0.2)
        elif phase == RoundPhase.QUEUE_WAIT:
            confidence = 0.62
        elif phase == RoundPhase.COUNTDOWN_KICKOFF:
            confidence = 0.66
        elif phase == RoundPhase.GOAL_REPLAY:
            confidence = 0.64
        elif phase == RoundPhase.ROUND_END:
            confidence = 0.58
        else:
            confidence = 0.45
        return RoundPhaseWindow(
            start,
            end,
            phase,
            confidence,
            {
                "samples": len(samples),
                "avg_motion": round(sum(sample.motion for sample in samples) / max(1, len(samples)), 3),
                "avg_audio": round(sum(sample.audio for sample in samples) / max(1, len(samples)), 3),
                "round_dead": sum(1 for sample in samples if sample.round_dead),
                "silence": sum(1 for sample in samples if sample.silence),
            },
        )

    def _merge_adjacent(self, windows: list[RoundPhaseWindow]) -> list[RoundPhaseWindow]:
        merged: list[RoundPhaseWindow] = []
        for window in windows:
            if (
                merged
                and merged[-1].phase == window.phase
                and window.start_seconds <= merged[-1].end_seconds + 0.75
            ):
                previous = merged[-1]
                total_duration = previous.duration_seconds + window.duration_seconds
                confidence = (
                    previous.confidence * previous.duration_seconds
                    + window.confidence * window.duration_seconds
                ) / max(0.001, total_duration)
                merged[-1] = RoundPhaseWindow(
                    previous.start_seconds,
                    window.end_seconds,
                    previous.phase,
                    confidence,
                    {**previous.evidence, "merged": True},
                )
            else:
                merged.append(window)
        return merged

    def _audio_score(
        self,
        start: float,
        end: float,
        signals: list[EditSignal],
        peak_windows: list[tuple[float, float, float]],
    ) -> float:
        score = 0.0
        for signal in signals:
            if signal.signal_type not in {"audio_peak", "audio_activity"}:
                continue
            if _overlap_seconds(start, end, signal.start_time, signal.end_time) <= 0.0:
                continue
            score = max(score, float(signal.strength or 0.0))
        for peak_start, peak_end, peak_score in peak_windows:
            if _overlap_seconds(start, end, peak_start, peak_end) > 0.0:
                score = max(score, peak_score)
        return round(max(0.0, min(1.0, score)), 3)

    def _audio_peak_windows(self, audio_peaks) -> Iterable[tuple[float, float, float]]:
        for peak in audio_peaks or []:
            start = getattr(peak, "start_seconds", getattr(peak, "start_time", None))
            end = getattr(peak, "end_seconds", getattr(peak, "end_time", None))
            if start is None or end is None:
                continue
            score = getattr(peak, "energy_score", getattr(peak, "strength", 0.7))
            yield float(start), float(end), float(score)

    def _has_signal(self, start: float, end: float, signals: list[EditSignal], signal_types: set[str]) -> bool:
        return any(
            signal.signal_type in signal_types
            and _overlap_seconds(start, end, signal.start_time, signal.end_time) > 0.0
            for signal in signals
        )

    def _has_event(self, start: float, end: float, events, event_types: set[str]) -> bool:
        return any(
            getattr(event, "event_type", "") in event_types
            and _overlap_seconds(start, end, event.start_seconds, event.end_seconds) > 0.0
            for event in events
        )

    def _transcript_text(
        self,
        start: float,
        end: float,
        transcript_result: TranscriptResult | None,
    ) -> str:
        if transcript_result is None:
            return ""
        return " ".join(
            segment.text.lower()
            for segment in transcript_result.segments
            if _overlap_seconds(start, end, segment.start_seconds, segment.end_seconds) > 0.0
        )

    def _has_countdown_text(self, text: str) -> bool:
        words = set(text.lower().replace(",", " ").replace(".", " ").split())
        return bool(words & _COUNTDOWN_WORDS)

    def _has_goal_text(self, text: str) -> bool:
        words = set(text.lower().replace(",", " ").replace(".", " ").split())
        return bool(words & _GOAL_WORDS)


def _overlap_seconds(start_a: float, end_a: float, start_b: float, end_b: float) -> float:
    return max(0.0, min(end_a, end_b) - max(start_a, start_b))
