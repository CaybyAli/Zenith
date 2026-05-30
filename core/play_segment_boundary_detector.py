from __future__ import annotations

import json
import math
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np

from models.play_segment import (
    PLAY_SEGMENT_INTENSITIES,
    PLAY_SEGMENT_STATES,
    PlaySegment,
    PlaySegmentDetectionResult,
    PlaySignalWindow,
    clamp01,
)


FORBIDDEN_CORE_TERMS = (
    "goal",
    "kickoff",
    "scoreboard",
    "round_end",
    "rocket_league",
    "fortnite",
    "minecraft",
    "league_of_legends",
    "low_motion_wait",
)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except Exception:
        return default
    if not math.isfinite(number):
        return default
    return number


def _percentile(values: Iterable[float], percentile: float, default: float = 0.0) -> float:
    cleaned = [float(v) for v in values if math.isfinite(float(v))]
    if not cleaned:
        return default
    return float(np.percentile(np.asarray(cleaned, dtype=np.float32), percentile))


def _tool_path(name: str) -> str:
    found = shutil.which(name)
    if found:
        return found
    candidate = Path("D:/Tools/ffmpeg/bin") / f"{name}.exe"
    if candidate.exists():
        return str(candidate)
    return name


def assert_neutral_taxonomy() -> None:
    all_terms = " ".join(list(PLAY_SEGMENT_STATES) + list(PLAY_SEGMENT_INTENSITIES)).lower()
    leaked = [term for term in FORBIDDEN_CORE_TERMS if term in all_terms]
    if leaked:
        raise AssertionError(f"forbidden core taxonomy terms leaked: {leaked}")


class PlaySegmentBoundaryDetector:
    """Game-agnostic active-vs-idle detector.

    The detector does not know game names and does not emit game-specific states.
    It combines visual motion, real audio activity, audio peaks, scene stability,
    edge stability, and color stability into neutral timeline states.
    """

    def __init__(
        self,
        window_seconds: float = 2.0,
        visual_sample_seconds: float = 1.0,
        audio_sample_rate: int = 16000,
    ) -> None:
        assert_neutral_taxonomy()
        self.window_seconds = max(1.0, float(window_seconds))
        self.visual_sample_seconds = max(0.5, float(visual_sample_seconds))
        self.audio_sample_rate = int(audio_sample_rate)

    def detect(
        self,
        video_path: str | Path,
        max_duration_seconds: Optional[float] = None,
        include_raw_windows: bool = False,
    ) -> PlaySegmentDetectionResult:
        path = Path(video_path)
        if not path.exists():
            raise FileNotFoundError(str(path))

        duration = self._probe_duration(path)
        analyzed_duration = duration
        if max_duration_seconds is not None:
            analyzed_duration = min(duration, max(0.0, float(max_duration_seconds)))

        warnings: List[str] = []
        if analyzed_duration <= 0:
            warnings.append("empty_or_unreadable_duration")
            return PlaySegmentDetectionResult(
                video_path=str(path),
                video_duration_seconds=duration,
                analyzed_duration_seconds=0.0,
                window_seconds=self.window_seconds,
                taxonomy=list(PLAY_SEGMENT_STATES),
                intensity_values=list(PLAY_SEGMENT_INTENSITIES),
                raw_windows=[],
                segments=[],
                review_candidates={},
                warnings=warnings,
            )

        audio_metrics, audio_warnings = self._extract_audio_metrics(path, analyzed_duration)
        warnings.extend(audio_warnings)

        visual_metrics, visual_warnings = self._extract_visual_metrics(path, analyzed_duration)
        warnings.extend(visual_warnings)

        raw_windows = self._classify_windows(analyzed_duration, audio_metrics, visual_metrics)
        raw_windows = self._smooth_short_flicker(raw_windows)
        raw_windows = self._apply_head_intro_guard(raw_windows)
        raw_windows = self._apply_tail_dead_time_guard(raw_windows)
        raw_windows = self._smooth_short_flicker(raw_windows)
        segments = self._consolidate_windows(raw_windows)
        segments = self._merge_short_segments(segments)
        candidates = self._build_review_candidates(raw_windows)

        return PlaySegmentDetectionResult(
            video_path=str(path),
            video_duration_seconds=duration,
            analyzed_duration_seconds=analyzed_duration,
            window_seconds=self.window_seconds,
            taxonomy=list(PLAY_SEGMENT_STATES),
            intensity_values=list(PLAY_SEGMENT_INTENSITIES),
            raw_windows=raw_windows if include_raw_windows else [],
            segments=segments,
            review_candidates=candidates,
            warnings=warnings,
        )

    def write_json(
        self,
        result: PlaySegmentDetectionResult,
        output_path: str | Path,
        include_raw_windows: bool = False,
    ) -> None:
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(result.to_dict(include_raw_windows=include_raw_windows), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def _probe_duration(self, video_path: Path) -> float:
        cmd = [
            _tool_path("ffprobe"),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=nokey=1:noprint_wrappers=1",
            str(video_path),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if proc.returncode != 0:
            raise RuntimeError(f"ffprobe failed for {video_path}: {proc.stderr}")
        return max(0.0, _safe_float(proc.stdout.strip(), 0.0))

    def _extract_audio_metrics(
        self,
        video_path: Path,
        analyzed_duration: float,
    ) -> Tuple[Dict[int, Dict[str, float]], List[str]]:
        warnings: List[str] = []
        window_count = max(1, int(math.ceil(analyzed_duration / self.window_seconds)))
        empty = {
            idx: {"audio_activity": 0.0, "audio_peak_score": 0.0}
            for idx in range(window_count)
        }

        cmd = [
            _tool_path("ffmpeg"),
            "-v",
            "error",
            "-i",
            str(video_path),
            "-t",
            f"{analyzed_duration:.3f}",
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(self.audio_sample_rate),
            "-f",
            "s16le",
            "-",
        ]
        proc = subprocess.run(cmd, capture_output=True)
        if proc.returncode != 0 or not proc.stdout:
            warnings.append("real_audio_unavailable_audio_features_zeroed")
            return empty, warnings

        samples = np.frombuffer(proc.stdout, dtype=np.int16).astype(np.float32) / 32768.0
        if samples.size == 0:
            warnings.append("real_audio_empty_audio_features_zeroed")
            return empty, warnings

        window_rms: List[float] = []
        window_peak: List[float] = []

        for idx in range(window_count):
            start_sample = int(idx * self.window_seconds * self.audio_sample_rate)
            end_sample = int(min(samples.size, (idx + 1) * self.window_seconds * self.audio_sample_rate))
            chunk = samples[start_sample:end_sample]
            if chunk.size == 0:
                window_rms.append(0.0)
                window_peak.append(0.0)
                continue
            abs_chunk = np.abs(chunk)
            rms = float(np.sqrt(np.mean(np.square(chunk))))
            peak = float(np.max(abs_chunk))
            window_rms.append(rms)
            window_peak.append(peak)

        rms_ref = max(_percentile([v for v in window_rms if v > 0.0001], 90, 0.01), 0.01)
        peak_ref = max(_percentile([v for v in window_peak if v > 0.001], 95, 0.05), 0.05)

        metrics: Dict[int, Dict[str, float]] = {}
        for idx, (rms, peak) in enumerate(zip(window_rms, window_peak)):
            metrics[idx] = {
                "audio_activity": clamp01(rms / (rms_ref * 1.10)),
                "audio_peak_score": clamp01(peak / peak_ref),
            }

        if max(item["audio_activity"] for item in metrics.values()) <= 0.001:
            warnings.append("audio_activity_effectively_zero_check_audio_streams")

        return metrics, warnings

    def _extract_visual_metrics(
        self,
        video_path: Path,
        analyzed_duration: float,
    ) -> Tuple[Dict[int, Dict[str, float]], List[str]]:
        warnings: List[str] = []
        window_count = max(1, int(math.ceil(analyzed_duration / self.window_seconds)))
        defaults = {
            idx: {
                "motion_raw": 0.0,
                "scene_raw": 0.0,
                "edge_density": 0.0,
                "edge_delta_raw": 0.0,
                "color_delta_raw": 0.0,
            }
            for idx in range(window_count)
        }

        try:
            import cv2  # type: ignore
        except Exception as exc:
            warnings.append(f"cv2_unavailable_visual_features_zeroed:{type(exc).__name__}")
            return self._normalize_visual_defaults(defaults), warnings

        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            warnings.append("opencv_could_not_open_video_visual_features_zeroed")
            return self._normalize_visual_defaults(defaults), warnings

        samples: List[Dict[str, Any]] = []
        t = 0.0
        while t < analyzed_duration:
            cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
            ok, frame = cap.read()
            if not ok or frame is None:
                t += self.visual_sample_seconds
                continue

            height, width = frame.shape[:2]
            target_width = 192
            scale = target_width / max(1, width)
            target_height = max(64, int(height * scale))
            small = cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA)
            gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
            edges = cv2.Canny(gray, 60, 160)
            samples.append(
                {
                    "time": t,
                    "gray": gray,
                    "hsv_mean": hsv.reshape(-1, 3).mean(axis=0),
                    "edges": edges,
                    "edge_density": float(np.mean(edges > 0)),
                }
            )
            t += self.visual_sample_seconds

        cap.release()

        if len(samples) < 2:
            warnings.append("too_few_visual_samples_visual_features_zeroed")
            return self._normalize_visual_defaults(defaults), warnings

        per_window: Dict[int, Dict[str, List[float]]] = {
            idx: {
                "motion_raw": [],
                "scene_raw": [],
                "edge_density": [],
                "edge_delta_raw": [],
                "color_delta_raw": [],
            }
            for idx in range(window_count)
        }

        for sample in samples:
            idx = min(window_count - 1, int(sample["time"] // self.window_seconds))
            per_window[idx]["edge_density"].append(float(sample["edge_density"]))

        for previous, current in zip(samples, samples[1:]):
            idx = min(window_count - 1, int(current["time"] // self.window_seconds))

            gray_diff = float(np.mean(np.abs(current["gray"].astype(np.float32) - previous["gray"].astype(np.float32))) / 255.0)
            edge_diff = float(np.mean(np.abs(current["edges"].astype(np.float32) - previous["edges"].astype(np.float32))) / 255.0)
            color_diff = float(np.mean(np.abs(current["hsv_mean"].astype(np.float32) - previous["hsv_mean"].astype(np.float32))) / 255.0)

            per_window[idx]["motion_raw"].append(gray_diff)
            per_window[idx]["scene_raw"].append(gray_diff)
            per_window[idx]["edge_delta_raw"].append(edge_diff)
            per_window[idx]["color_delta_raw"].append(color_diff)

        raw_metrics: Dict[int, Dict[str, float]] = {}
        for idx, values in per_window.items():
            raw_metrics[idx] = {
                key: float(np.mean(val)) if val else 0.0
                for key, val in values.items()
            }

        return self._normalize_visual_defaults(raw_metrics), warnings

    def _normalize_visual_defaults(self, raw_metrics: Dict[int, Dict[str, float]]) -> Dict[int, Dict[str, float]]:
        motion_ref = max(_percentile((m["motion_raw"] for m in raw_metrics.values()), 85, 0.015), 0.008)
        scene_ref = max(_percentile((m["scene_raw"] for m in raw_metrics.values()), 95, 0.030), 0.012)
        edge_ref = max(_percentile((m["edge_delta_raw"] for m in raw_metrics.values()), 90, 0.020), 0.008)
        color_ref = max(_percentile((m["color_delta_raw"] for m in raw_metrics.values()), 90, 0.020), 0.006)
        density_ref = max(_percentile((m["edge_density"] for m in raw_metrics.values()), 90, 0.050), 0.015)

        normalized: Dict[int, Dict[str, float]] = {}
        for idx, metric in raw_metrics.items():
            motion_score = clamp01(metric.get("motion_raw", 0.0) / motion_ref)
            scene_change_score = clamp01(metric.get("scene_raw", 0.0) / scene_ref)
            edge_stability = 1.0 - clamp01(metric.get("edge_delta_raw", 0.0) / edge_ref)
            color_stability = 1.0 - clamp01(metric.get("color_delta_raw", 0.0) / color_ref)
            visual_richness = clamp01(metric.get("edge_density", 0.0) / density_ref)
            visual_stability = 1.0 - scene_change_score
            normalized[idx] = {
                "motion_score": motion_score,
                "scene_change_score": scene_change_score,
                "visual_stability": clamp01(visual_stability),
                "edge_stability": clamp01(edge_stability),
                "color_stability": clamp01(color_stability),
                "visual_richness": visual_richness,
            }
        return normalized

    def _classify_windows(
        self,
        analyzed_duration: float,
        audio_metrics: Dict[int, Dict[str, float]],
        visual_metrics: Dict[int, Dict[str, float]],
    ) -> List[PlaySignalWindow]:
        window_count = max(1, int(math.ceil(analyzed_duration / self.window_seconds)))
        windows: List[PlaySignalWindow] = []

        for idx in range(window_count):
            start = idx * self.window_seconds
            end = min(analyzed_duration, (idx + 1) * self.window_seconds)
            audio = audio_metrics.get(idx, {})
            visual = visual_metrics.get(idx, {})

            motion = clamp01(audio.get("motion_score", visual.get("motion_score", 0.0)))
            audio_activity = clamp01(audio.get("audio_activity", 0.0))
            audio_peak = clamp01(audio.get("audio_peak_score", 0.0))
            scene_change = clamp01(visual.get("scene_change_score", 0.0))
            visual_stability = clamp01(visual.get("visual_stability", 0.0))
            edge_stability = clamp01(visual.get("edge_stability", 0.0))
            color_stability = clamp01(visual.get("color_stability", 0.0))
            visual_richness = clamp01(visual.get("visual_richness", 0.0))

            stability_bundle = (visual_stability + edge_stability + color_stability) / 3.0
            sustained_audio = audio_activity >= 0.18
            quiet_active_rule = motion <= 0.36 and sustained_audio and stability_bundle >= 0.44

            active_score = clamp01(
                (motion * 0.28)
                + (audio_activity * 0.25)
                + (audio_peak * 0.08)
                + (visual_stability * 0.12)
                + (edge_stability * 0.08)
                + (color_stability * 0.07)
                + (visual_richness * 0.12)
            )

            idle_score = clamp01(
                ((1.0 - motion) * 0.28)
                + ((1.0 - audio_activity) * 0.28)
                + (visual_stability * 0.22)
                + ((1.0 - visual_richness) * 0.12)
                + ((1.0 - audio_peak) * 0.10)
            )

            transition_score = clamp01(
                (scene_change * 0.42)
                + ((1.0 - audio_activity) * 0.22)
                + ((1.0 - edge_stability) * 0.18)
                + ((1.0 - color_stability) * 0.18)
            )

            if quiet_active_rule or active_score >= 0.53:
                state = "active_play"
            elif transition_score >= 0.60 and active_score < 0.58:
                state = "transition_dead_time"
            elif idle_score >= 0.52:
                state = "intro_menu_lobby"
            else:
                state = "unknown"

            if state == "active_play":
                if active_score >= 0.72 or motion >= 0.72 or audio_peak >= 0.84:
                    intensity = "high"
                elif active_score >= 0.58 or motion >= 0.48 or audio_activity >= 0.48:
                    intensity = "medium"
                else:
                    intensity = "low"
            else:
                intensity = "unknown"

            confidence_gap = abs(active_score - max(idle_score, transition_score))
            confidence = clamp01(0.48 + confidence_gap)
            if quiet_active_rule:
                confidence = max(confidence, 0.66)

            evidence = {
                "formula": "active=0.28*motion+0.25*audio_activity+0.08*audio_peak+0.12*visual_stability+0.08*edge_stability+0.07*color_stability+0.12*visual_richness",
                "active_score": round(active_score, 4),
                "idle_score": round(idle_score, 4),
                "transition_score": round(transition_score, 4),
                "quiet_active_rule": bool(quiet_active_rule),
                "sustained_audio": bool(sustained_audio),
                "stability_bundle": round(stability_bundle, 4),
                "visual_richness": round(visual_richness, 4),
            }

            window_warnings: List[str] = []
            if audio_activity <= 0.001:
                window_warnings.append("audio_activity_zero_for_window")

            windows.append(
                PlaySignalWindow(
                    start_seconds=start,
                    end_seconds=end,
                    motion_score=motion,
                    audio_activity=audio_activity,
                    audio_peak_score=audio_peak,
                    scene_change_score=scene_change,
                    visual_stability=visual_stability,
                    edge_stability=edge_stability,
                    color_stability=color_stability,
                    state=state,
                    intensity=intensity,
                    confidence=confidence,
                    evidence=evidence,
                    warnings=window_warnings,
                )
            )

        return windows

    def _copy_window_with_state(
        self,
        window: PlaySignalWindow,
        state: str,
        intensity: str = "unknown",
        confidence_floor: float = 0.62,
        evidence_key: str = "state_guard",
    ) -> PlaySignalWindow:
        return PlaySignalWindow(
            start_seconds=window.start_seconds,
            end_seconds=window.end_seconds,
            motion_score=window.motion_score,
            audio_activity=window.audio_activity,
            audio_peak_score=window.audio_peak_score,
            scene_change_score=window.scene_change_score,
            visual_stability=window.visual_stability,
            edge_stability=window.edge_stability,
            color_stability=window.color_stability,
            state=state,
            intensity=intensity if state == "active_play" else "unknown",
            confidence=max(window.confidence, confidence_floor),
            evidence={**window.evidence, evidence_key: True},
            warnings=list(window.warnings),
        )

    def _window_share(
        self,
        windows: List[PlaySignalWindow],
        start_idx: int,
        end_idx: int,
        wanted_state: str,
    ) -> float:
        chunk = windows[max(0, start_idx) : min(len(windows), end_idx)]
        total = sum(item.duration_seconds for item in chunk)
        if total <= 0:
            return 0.0
        wanted = sum(item.duration_seconds for item in chunk if item.state == wanted_state)
        return wanted / total

    def _non_active_share(
        self,
        windows: List[PlaySignalWindow],
        start_idx: int,
        end_idx: int,
    ) -> float:
        chunk = windows[max(0, start_idx) : min(len(windows), end_idx)]
        total = sum(item.duration_seconds for item in chunk)
        if total <= 0:
            return 0.0
        non_active = sum(item.duration_seconds for item in chunk if item.state != "active_play")
        return non_active / total

    def _apply_head_intro_guard(self, windows: List[PlaySignalWindow]) -> List[PlaySignalWindow]:
        if not windows:
            return windows

        total_duration = windows[-1].end_seconds
        if total_duration <= 0:
            return windows

        min_head_seconds = min(16.0, total_duration * 0.50)
        min_head_idx = min(len(windows) - 1, int(math.floor(min_head_seconds / self.window_seconds)))

        # Game-agnostic start rule:
        # A real gameplay start must be sustained after the candidate.
        # For longer videos, noisy intro montages are rejected when the previous minute
        # was already active-looking. This avoids accepting loud menus, trailers, or recaps.
        first_horizon = max(30.0, min(180.0, total_duration * 0.25))
        long_horizon = max(first_horizon, min(300.0, total_duration - min_head_seconds))
        first_horizon_windows = max(1, int(math.ceil(first_horizon / self.window_seconds)))
        long_horizon_windows = max(1, int(math.ceil(long_horizon / self.window_seconds)))
        early_30_windows = max(1, int(math.ceil(30.0 / self.window_seconds)))
        early_90_windows = max(1, int(math.ceil(90.0 / self.window_seconds)))
        early_300_windows = max(1, int(math.ceil(min(300.0, total_duration) / self.window_seconds)))
        prev_minute_windows = max(1, int(math.ceil(60.0 / self.window_seconds)))
        prev_short_windows = max(1, int(math.ceil(20.0 / self.window_seconds)))

        start_idx: Optional[int] = None
        start_evidence: Dict[str, float] = {}

        for idx in range(min_head_idx, len(windows)):
            nearby = windows[idx : min(len(windows), idx + 4)]
            if not any(item.state == "active_play" for item in nearby):
                continue

            first_share = self._window_share(windows, idx, idx + first_horizon_windows, "active_play")
            long_share = self._window_share(windows, idx, idx + long_horizon_windows, "active_play")
            early_30_share = self._window_share(windows, idx, idx + early_30_windows, "active_play")
            early_90_share = self._window_share(windows, idx, idx + early_90_windows, "active_play")
            early_300_share = self._window_share(windows, idx, idx + early_300_windows, "active_play")
            prev_active_share = self._window_share(windows, idx - prev_minute_windows, idx, "active_play")
            prev_non_active_short = self._non_active_share(windows, idx - prev_short_windows, idx)

            early_start_allowed = windows[idx].start_seconds <= 30.0

            # Game-agnostic early burst:
            # Accept a clean early gameplay start when the next 30/90s are active enough,
            # but the next 300s are not overwhelmingly active. This separates a real
            # early gameplay start from long noisy intro/menu/recap sequences.
            early_burst_start = (
                early_start_allowed
                and 0.50 <= early_30_share <= 0.65
                and early_90_share >= 0.55
                and early_300_share <= 0.48
            )

            previous_context_clean = (
                early_start_allowed
                or (prev_active_share <= 0.30 and prev_non_active_short >= 0.50)
            )

            sustained_start = (
                first_share >= 0.54
                and long_share >= 0.64
                and previous_context_clean
            )

            if early_burst_start or sustained_start:
                start_idx = idx
                start_evidence = {
                    "head_sustained_first_horizon_active_share": round(first_share, 4),
                    "head_sustained_long_horizon_active_share": round(long_share, 4),
                    "head_early_30_active_share": round(early_30_share, 4),
                    "head_early_90_active_share": round(early_90_share, 4),
                    "head_early_300_active_share": round(early_300_share, 4),
                    "head_previous_minute_active_share": round(prev_active_share, 4),
                    "head_previous_short_non_active_share": round(prev_non_active_short, 4),
                    "head_early_burst_start": bool(early_burst_start),
                    "head_sustained_start": bool(sustained_start),
                    "head_start_seconds": round(windows[idx].start_seconds, 3),
                }
                break

        if start_idx is None:
            active_indices = [idx for idx, w in enumerate(windows) if w.state == "active_play"]
            if not active_indices:
                return windows
            start_idx = max(min_head_idx, active_indices[0])
            start_evidence = {"head_guard_fallback_start_seconds": round(windows[start_idx].start_seconds, 3)}

        guarded: List[PlaySignalWindow] = []
        for idx, window in enumerate(windows):
            if idx < start_idx:
                guarded.append(
                    self._copy_window_with_state(
                        window,
                        state="intro_menu_lobby",
                        intensity="unknown",
                        confidence_floor=0.66,
                        evidence_key="sustained_head_intro_guard",
                    )
                )
            elif idx == start_idx:
                guarded.append(
                    PlaySignalWindow(
                        start_seconds=window.start_seconds,
                        end_seconds=window.end_seconds,
                        motion_score=window.motion_score,
                        audio_activity=window.audio_activity,
                        audio_peak_score=window.audio_peak_score,
                        scene_change_score=window.scene_change_score,
                        visual_stability=window.visual_stability,
                        edge_stability=window.edge_stability,
                        color_stability=window.color_stability,
                        state=window.state,
                        intensity=window.intensity,
                        confidence=window.confidence,
                        evidence={**window.evidence, **start_evidence},
                        warnings=list(window.warnings),
                    )
                )
            else:
                guarded.append(window)

        return guarded

    def _apply_tail_dead_time_guard(self, windows: List[PlaySignalWindow]) -> List[PlaySignalWindow]:
        if not windows:
            return windows

        total_duration = windows[-1].end_seconds
        if total_duration < 120.0:
            return windows

        tail_seconds = min(28.0, max(12.0, total_duration * 0.02))
        tail_start = max(0.0, total_duration - tail_seconds)
        tail_windows = [window for window in windows if window.end_seconds > tail_start]

        # If the ending already contains non-active evidence, suppress active flicker
        # inside that final tail. This catches end screens/outros/dead-time without game names.
        tail_has_non_active = any(window.state != "active_play" for window in tail_windows)
        if not tail_has_non_active:
            return windows

        guarded: List[PlaySignalWindow] = []
        for window in windows:
            if window.end_seconds > tail_start and window.state == "active_play":
                guarded.append(
                    self._copy_window_with_state(
                        window,
                        state="transition_dead_time",
                        intensity="unknown",
                        confidence_floor=0.68,
                        evidence_key="tail_dead_time_guard",
                    )
                )
            else:
                guarded.append(window)
        return guarded

    def _smooth_short_flicker(self, windows: List[PlaySignalWindow]) -> List[PlaySignalWindow]:
        if len(windows) < 3:
            return windows

        smoothed = list(windows)
        for idx in range(1, len(windows) - 1):
            previous = smoothed[idx - 1]
            current = smoothed[idx]
            nxt = smoothed[idx + 1]
            if previous.state == nxt.state and current.state != previous.state and current.duration_seconds <= self.window_seconds + 0.01:
                smoothed[idx] = PlaySignalWindow(
                    start_seconds=current.start_seconds,
                    end_seconds=current.end_seconds,
                    motion_score=current.motion_score,
                    audio_activity=current.audio_activity,
                    audio_peak_score=current.audio_peak_score,
                    scene_change_score=current.scene_change_score,
                    visual_stability=current.visual_stability,
                    edge_stability=current.edge_stability,
                    color_stability=current.color_stability,
                    state=previous.state,
                    intensity=previous.intensity if previous.state == "active_play" else "unknown",
                    confidence=max(0.50, min(previous.confidence, nxt.confidence)),
                    evidence={**current.evidence, "short_flicker_smoothed_to": previous.state},
                    warnings=list(current.warnings),
                )
        return smoothed

    def _consolidate_windows(self, windows: List[PlaySignalWindow]) -> List[PlaySegment]:
        if not windows:
            return []

        segments: List[PlaySegment] = []
        current_state = windows[0].state
        current_intensity = windows[0].intensity
        start = windows[0].start_seconds
        bucket: List[PlaySignalWindow] = []

        def flush(end: float) -> None:
            if not bucket:
                return
            confidence = float(np.mean([w.confidence for w in bucket]))
            source_counts = {
                "windows": len(bucket),
                "active_votes": sum(1 for w in bucket if w.state == "active_play"),
                "intro_menu_lobby_votes": sum(1 for w in bucket if w.state == "intro_menu_lobby"),
                "transition_dead_time_votes": sum(1 for w in bucket if w.state == "transition_dead_time"),
                "replay_break_votes": sum(1 for w in bucket if w.state == "replay_break"),
                "unknown_votes": sum(1 for w in bucket if w.state == "unknown"),
                "audio_activity_votes": sum(1 for w in bucket if w.audio_activity >= 0.18),
                "motion_votes": sum(1 for w in bucket if w.motion_score >= 0.35),
                "stable_scene_votes": sum(1 for w in bucket if w.visual_stability >= 0.45),
            }
            avg_motion = float(np.mean([w.motion_score for w in bucket]))
            avg_audio = float(np.mean([w.audio_activity for w in bucket]))
            avg_stability = float(np.mean([(w.visual_stability + w.edge_stability + w.color_stability) / 3.0 for w in bucket]))
            warnings = sorted({warning for w in bucket for warning in w.warnings})
            segments.append(
                PlaySegment(
                    start_seconds=start,
                    end_seconds=end,
                    state=current_state,
                    intensity=current_intensity if current_state == "active_play" else "unknown",
                    confidence=confidence,
                    evidence={
                        "avg_motion_score": round(avg_motion, 4),
                        "avg_audio_activity": round(avg_audio, 4),
                        "avg_stability_bundle": round(avg_stability, 4),
                    },
                    source_signal_counts=source_counts,
                    warnings=warnings,
                )
            )

        for window in windows:
            wanted_intensity = window.intensity if window.state == "active_play" else "unknown"
            if bucket and (window.state != current_state or wanted_intensity != current_intensity):
                flush(bucket[-1].end_seconds)
                start = window.start_seconds
                bucket = []
                current_state = window.state
                current_intensity = wanted_intensity
            bucket.append(window)

        flush(windows[-1].end_seconds)
        return segments

    def _merge_short_segments(self, segments: List[PlaySegment]) -> List[PlaySegment]:
        if len(segments) < 3:
            return segments

        merged = list(segments)
        changed = True
        while changed:
            changed = False
            next_segments: List[PlaySegment] = []
            idx = 0
            while idx < len(merged):
                if 0 < idx < len(merged) - 1:
                    previous = next_segments[-1]
                    current = merged[idx]
                    nxt = merged[idx + 1]
                    if (
                        current.duration_seconds <= max(4.0, self.window_seconds * 2.0)
                        and previous.state == nxt.state
                    ):
                        combined = PlaySegment(
                            start_seconds=previous.start_seconds,
                            end_seconds=nxt.end_seconds,
                            state=previous.state,
                            intensity=previous.intensity,
                            confidence=float(np.mean([previous.confidence, current.confidence, nxt.confidence])),
                            evidence={
                                **previous.evidence,
                                "merged_short_middle_segment_seconds": round(current.duration_seconds, 3),
                            },
                            source_signal_counts={
                                key: previous.source_signal_counts.get(key, 0)
                                + current.source_signal_counts.get(key, 0)
                                + nxt.source_signal_counts.get(key, 0)
                                for key in set(previous.source_signal_counts) | set(current.source_signal_counts) | set(nxt.source_signal_counts)
                            },
                            warnings=sorted(set(previous.warnings + current.warnings + nxt.warnings)),
                        )
                        next_segments[-1] = combined
                        idx += 2
                        changed = True
                        continue
                next_segments.append(merged[idx])
                idx += 1
            merged = next_segments

        final: List[PlaySegment] = []
        for segment in merged:
            if final and final[-1].state == segment.state and final[-1].intensity == segment.intensity:
                previous = final[-1]
                final[-1] = PlaySegment(
                    start_seconds=previous.start_seconds,
                    end_seconds=segment.end_seconds,
                    state=previous.state,
                    intensity=previous.intensity,
                    confidence=float(np.mean([previous.confidence, segment.confidence])),
                    evidence=previous.evidence,
                    source_signal_counts={
                        key: previous.source_signal_counts.get(key, 0) + segment.source_signal_counts.get(key, 0)
                        for key in set(previous.source_signal_counts) | set(segment.source_signal_counts)
                    },
                    warnings=sorted(set(previous.warnings + segment.warnings)),
                )
            else:
                final.append(segment)
        return final

    def _build_review_candidates(self, windows: List[PlaySignalWindow]) -> Dict[str, List[Dict[str, Any]]]:
        def top_items(predicate: Any, score_key: Any) -> List[Dict[str, Any]]:
            candidates = [window for window in windows if predicate(window)]
            candidates.sort(key=score_key, reverse=True)
            return [
                {
                    "start_seconds": round(item.start_seconds, 3),
                    "end_seconds": round(item.end_seconds, 3),
                    "state": item.state,
                    "intensity": item.intensity,
                    "confidence": round(item.confidence, 4),
                    "motion_score": round(item.motion_score, 4),
                    "audio_activity": round(item.audio_activity, 4),
                    "visual_stability": round(item.visual_stability, 4),
                    "evidence": item.evidence,
                }
                for item in candidates[:3]
            ]

        return {
            "low_motion_high_audio_candidate": top_items(
                lambda w: w.motion_score <= 0.35 and w.audio_activity >= 0.35,
                lambda w: w.audio_activity - w.motion_score,
            ),
            "low_motion_stable_scene_candidate": top_items(
                lambda w: w.motion_score <= 0.35 and w.visual_stability >= 0.55,
                lambda w: w.visual_stability - w.motion_score,
            ),
            "possible_quiet_active_play_candidate": top_items(
                lambda w: w.motion_score <= 0.42
                and w.audio_activity >= 0.18
                and ((w.visual_stability + w.edge_stability + w.color_stability) / 3.0) >= 0.44,
                lambda w: w.confidence + w.audio_activity,
            ),
        }
