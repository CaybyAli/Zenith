from __future__ import annotations

import math
import statistics
from typing import Any


class StyleCaptureAnalyzer:
    def analyze(
        self,
        *,
        video_duration_seconds: float,
        scene_change_boundaries: list[float],
        voice_intensity_distribution: dict[str, float],
        facial_expression_distribution: dict[str, float],
        gameplay_ratio: dict[str, Any],
        speaker_distribution: dict[str, float] | None,
        audio_rms_curve: list[float],
        hook: dict[str, Any],
        transcript: dict[str, Any],
    ) -> dict[str, Any]:
        duration = max(float(video_duration_seconds or 0.0), 0.001)
        boundaries = self._clean_boundaries(scene_change_boundaries, duration)
        cut_density_curve = self._compute_cut_density(duration, boundaries)
        reaction_density = self._compute_reaction_density(
            duration,
            voice_intensity_distribution,
            facial_expression_distribution,
        )
        audio_dynamic_range = self._compute_dynamic_range(audio_rms_curve)
        scene_duration_stats = self._compute_scene_stats(boundaries, duration)
        cut_rhythm = self._compute_cut_rhythm(boundaries)
        intensity_clustering = self._classify_intensity_clustering(
            cut_density_curve,
            reaction_density,
            hook,
        )
        focus_distribution = self._reconstruct_focus_distribution(
            voice_intensity_distribution=voice_intensity_distribution,
            facial_expression_distribution=facial_expression_distribution,
            gameplay_ratio=gameplay_ratio,
            speaker_distribution=speaker_distribution or {},
            duration=duration,
        )

        return {
            "cut_density_curve": cut_density_curve,
            "reaction_density": reaction_density,
            "opening_pattern": self._analyze_opening(
                boundaries,
                voice_intensity_distribution,
                gameplay_ratio,
                hook,
                transcript,
            ),
            "closing_pattern": self._analyze_closing(duration, boundaries, gameplay_ratio),
            "audio_dynamic_range": audio_dynamic_range,
            "scene_duration_stats": scene_duration_stats,
            "intensity_clustering": intensity_clustering,
            "signature_score": self._compute_signature_score(
                cut_density_curve=cut_density_curve,
                reaction_density=reaction_density,
                audio_dynamic_range=audio_dynamic_range,
                scene_duration_stats=scene_duration_stats,
                focus_distribution=focus_distribution,
                hook=hook,
            ),
            "cut_rhythm": cut_rhythm,
            "focus_decision_distribution": focus_distribution,
        }

    def _compute_cut_density(
        self,
        duration: float,
        boundaries: list[float],
        *,
        bin_count: int = 10,
    ) -> list[dict[str, float]]:
        bin_duration = duration / bin_count
        curve: list[dict[str, float]] = []
        for index in range(bin_count):
            start = index * bin_duration
            end = duration if index == bin_count - 1 else (index + 1) * bin_duration
            cuts = [value for value in boundaries if start <= value < end]
            curve.append(
                {
                    "bin_index": index,
                    "start_pct": round(index * (100.0 / bin_count), 3),
                    "end_pct": round((index + 1) * (100.0 / bin_count), 3),
                    "cuts_per_second": round(len(cuts) / max(end - start, 0.001), 6),
                    "cut_count": len(cuts),
                }
            )
        return curve

    def _compute_reaction_density(
        self,
        duration: float,
        voice_distribution: dict[str, float],
        facial_distribution: dict[str, float],
    ) -> dict[str, Any]:
        seconds = max(duration, 1.0)
        voice_peak_pct = float(voice_distribution.get("schreien", 0.0)) + float(
            voice_distribution.get("bruellen", voice_distribution.get("brüllen", 0.0))
        )
        facial_peak_pct = sum(
            float(facial_distribution.get(key, 0.0))
            for key in ("hand_on_mouth", "surprise", "mouth_open_yell", "frustration")
        )
        voice_peak_count = round(seconds * (voice_peak_pct / 100.0))
        facial_peak_count = round(seconds * min(facial_peak_pct, 100.0) / 100.0)
        coincident_count = min(voice_peak_count, facial_peak_count)
        return {
            "voice_peak_count": int(voice_peak_count),
            "facial_peak_count": int(facial_peak_count),
            "coincident_count": int(coincident_count),
            "coincidence_ratio": round(
                coincident_count / max(voice_peak_count, facial_peak_count, 1),
                3,
            ),
        }

    def _analyze_opening(
        self,
        boundaries: list[float],
        voice_distribution: dict[str, float],
        gameplay_ratio: dict[str, Any],
        hook: dict[str, Any],
        transcript: dict[str, Any],
    ) -> dict[str, Any]:
        first_cut = next((value for value in boundaries if value <= 30.0), None)
        hook_class = str(hook.get("pattern_class", "unknown") or "unknown")
        dominant_intensity = self._dominant_voice_intensity(voice_distribution)
        return {
            "starts_with_action": hook_class in {"high_reaction", "exclamation", "action"}
            or float(gameplay_ratio.get("gameplay_percent", 0.0)) >= 70.0,
            "starts_with_question": hook_class == "question"
            or "?" in str(transcript.get("first_10s_text", "")),
            "starts_with_silence": len(str(transcript.get("first_10s_text", "") or "")) < 10,
            "first_cut_at_seconds": round(first_cut, 3) if first_cut is not None else None,
            "voice_intensity_first_5s": dominant_intensity,
            "hook_pattern_class": hook_class,
        }

    def _analyze_closing(
        self,
        duration: float,
        boundaries: list[float],
        gameplay_ratio: dict[str, Any],
    ) -> dict[str, Any]:
        last_cut = boundaries[-1] if boundaries else None
        seconds_before_end = duration - last_cut if last_cut is not None else None
        return {
            "ends_with_action": float(gameplay_ratio.get("gameplay_percent", 0.0)) >= 70.0,
            "ends_with_quiet": float(gameplay_ratio.get("menu_percent", 0.0)) >= 10.0,
            "ends_with_cut": seconds_before_end is not None and seconds_before_end <= 5.0,
            "last_cut_at_seconds_before_end": (
                round(seconds_before_end, 3) if seconds_before_end is not None else None
            ),
        }

    def _compute_dynamic_range(self, rms_curve: list[float]) -> dict[str, Any]:
        values = [float(value) for value in rms_curve or [] if math.isfinite(float(value))]
        if not values:
            return {"lufs_max": 0.0, "lufs_min": 0.0, "range_db": 0.0, "is_dynamic": False}
        maximum = max(values)
        minimum = min(values)
        value_range = maximum - minimum
        return {
            "lufs_max": round(maximum, 3),
            "lufs_min": round(minimum, 3),
            "range_db": round(value_range, 3),
            "is_dynamic": value_range > 15.0,
        }

    def _compute_scene_stats(
        self,
        boundaries: list[float],
        duration: float,
    ) -> dict[str, float]:
        points = [0.0, *boundaries, duration]
        lengths = [max(right - left, 0.0) for left, right in zip(points, points[1:])]
        if not lengths:
            return {
                "mean_seconds": 0.0,
                "median_seconds": 0.0,
                "std_seconds": 0.0,
                "min_seconds": 0.0,
                "max_seconds": 0.0,
            }
        return {
            "mean_seconds": round(statistics.fmean(lengths), 3),
            "median_seconds": round(statistics.median(lengths), 3),
            "std_seconds": round(statistics.pstdev(lengths), 3) if len(lengths) > 1 else 0.0,
            "min_seconds": round(min(lengths), 3),
            "max_seconds": round(max(lengths), 3),
        }

    def _classify_intensity_clustering(
        self,
        cut_density_curve: list[dict[str, float]],
        reaction_density: dict[str, Any],
        hook: dict[str, Any],
    ) -> str:
        counts = [float(item.get("cut_count", 0.0)) for item in cut_density_curve]
        if not counts or sum(counts) <= 0:
            return "even"
        midpoint = len(counts) // 2
        front = sum(counts[:midpoint])
        back = sum(counts[midpoint:])
        mean = statistics.fmean(counts)
        std = statistics.pstdev(counts) if len(counts) > 1 else 0.0
        if max(counts) >= max(4.0, mean + (2.0 * std)):
            return "burst"
        if front >= back * 1.35 or hook.get("pattern_class") in {"high_reaction", "question"}:
            return "front_loaded"
        if back >= front * 1.35:
            return "back_loaded"
        if std <= max(mean * 0.35, 0.2):
            return "even"
        if int(reaction_density.get("coincident_count", 0)) >= 20:
            return "burst"
        return "scattered"

    def _compute_signature_score(
        self,
        *,
        cut_density_curve: list[dict[str, float]],
        reaction_density: dict[str, Any],
        audio_dynamic_range: dict[str, Any],
        scene_duration_stats: dict[str, float],
        focus_distribution: dict[str, Any],
        hook: dict[str, Any],
    ) -> float:
        cut_values = [float(item.get("cuts_per_second", 0.0)) for item in cut_density_curve]
        cut_variance = statistics.pstdev(cut_values) if len(cut_values) > 1 else 0.0
        reaction_score = min(1.0, float(reaction_density.get("coincidence_ratio", 0.0)))
        dynamic_score = min(1.0, float(audio_dynamic_range.get("range_db", 0.0)) / 35.0)
        scene_score = min(1.0, float(scene_duration_stats.get("std_seconds", 0.0)) / 20.0)
        focus_score = abs(float(focus_distribution.get("facecam_pct", 0.0)) - 50.0) / 50.0
        hook_bonus = 0.12 if hook.get("pattern_class") in {"high_reaction", "question"} else 0.03
        score = (
            min(1.0, cut_variance * 8.0) * 0.22
            + reaction_score * 0.22
            + dynamic_score * 0.22
            + scene_score * 0.17
            + focus_score * 0.12
            + hook_bonus
        )
        return round(max(0.0, min(1.0, score)), 3)

    def _compute_cut_rhythm(self, boundaries: list[float]) -> dict[str, Any]:
        if len(boundaries) < 2:
            return {
                "is_rhythmic": False,
                "median_interval_seconds": 0.0,
                "interval_std_seconds": 0.0,
            }
        intervals = [right - left for left, right in zip(boundaries, boundaries[1:])]
        median_interval = statistics.median(intervals)
        interval_std = statistics.pstdev(intervals) if len(intervals) > 1 else 0.0
        return {
            "is_rhythmic": bool(median_interval > 0 and interval_std <= median_interval * 0.35),
            "median_interval_seconds": round(median_interval, 3),
            "interval_std_seconds": round(interval_std, 3),
        }

    def _reconstruct_focus_distribution(
        self,
        *,
        voice_intensity_distribution: dict[str, float],
        facial_expression_distribution: dict[str, float],
        gameplay_ratio: dict[str, Any],
        speaker_distribution: dict[str, float],
        duration: float,
    ) -> dict[str, Any]:
        drop_pct = max(0.0, min(35.0, float(gameplay_ratio.get("menu_percent", 0.0))))
        voice_strong = float(voice_intensity_distribution.get("schreien", 0.0)) + float(
            voice_intensity_distribution.get("bruellen", voice_intensity_distribution.get("brüllen", 0.0))
        )
        expression_strong = sum(
            float(facial_expression_distribution.get(key, 0.0))
            for key in ("surprise", "hand_on_mouth", "mouth_open_yell")
        )
        ali_pct = float(speaker_distribution.get("ali", 0.0))
        friend_pct = float(speaker_distribution.get("friend", 0.0))
        facecam_pct = min(85.0, max(10.0, 25.0 + voice_strong * 1.4 + expression_strong * 0.35 + ali_pct * 0.2))
        gameplay_pct = min(85.0, max(5.0, 100.0 - drop_pct - facecam_pct + friend_pct * 0.25))
        balanced_pct = max(0.0, 100.0 - facecam_pct - gameplay_pct - drop_pct)
        total = max(facecam_pct + gameplay_pct + balanced_pct + drop_pct, 0.001)
        scale = 100.0 / total
        facecam_pct *= scale
        gameplay_pct *= scale
        balanced_pct *= scale
        drop_pct *= scale
        return {
            "facecam_pct": round(facecam_pct, 3),
            "gameplay_pct": round(gameplay_pct, 3),
            "balanced_pct": round(balanced_pct, 3),
            "drop_pct": round(drop_pct, 3),
            "total_decisions": max(1, int(round(duration))),
        }

    def _dominant_voice_intensity(self, distribution: dict[str, float]) -> str:
        aliases = {
            "normal": float(distribution.get("normal", 0.0)),
            "leise_erhoeht": float(
                distribution.get("leise_erhoeht", distribution.get("leise_erhöht", 0.0))
            ),
            "schreien": float(distribution.get("schreien", 0.0)),
            "bruellen": float(distribution.get("bruellen", distribution.get("brüllen", 0.0))),
        }
        return max(aliases.items(), key=lambda item: item[1])[0]

    def _clean_boundaries(self, boundaries: list[float], duration: float) -> list[float]:
        clean = {round(float(value), 3) for value in boundaries or [] if 0.0 < float(value) < duration}
        return sorted(clean)
