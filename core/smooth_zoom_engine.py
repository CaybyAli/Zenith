from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Iterable

from core.facial_expression_analyzer import FacialExpression, FacialExpressionPoint
from core.gameplay_menu_detector import GameplayDetectionPoint
from core.voice_intensity_analyzer import VoiceIntensity, VoiceIntensityPoint
from models.transcript_result import TranscriptSegment


TARGET_FACECAM = "facecam"
TARGET_GAMEPLAY = "gameplay"
TARGET_BALANCED = "balanced"


def clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def ease_in_out_cubic(t: float) -> float:
    t = clamp01(t)
    return 4 * t**3 if t < 0.5 else 1 - pow(-2 * t + 2, 3) / 2


def ease_out_quad(t: float) -> float:
    t = clamp01(t)
    return 1 - (1 - t) * (1 - t)


def linear(t: float) -> float:
    return clamp01(t)


def easing_value(easing: str, t: float) -> float:
    if easing in {"ease_in_out", "ease_in_out_cubic"}:
        return ease_in_out_cubic(t)
    if easing in {"ease_out", "ease_out_quad"}:
        return ease_out_quad(t)
    return linear(t)


@dataclass(frozen=True)
class ZoomKeyframe:
    timestamp: float
    zoom_factor: float
    target: str
    easing: str = "linear"

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": round(float(self.timestamp), 3),
            "zoom_factor": round(float(self.zoom_factor), 3),
            "target": self.target,
            "easing": self.easing,
        }


@dataclass
class ZoomCurve:
    keyframes: list[ZoomKeyframe]

    def __post_init__(self) -> None:
        self.keyframes = _dedupe_keyframes(self.keyframes)

    def interpolate(self, t: float) -> tuple[float, str]:
        if not self.keyframes:
            return 1.0, TARGET_BALANCED

        timestamp = float(t)
        keyframes = self.keyframes
        if timestamp <= keyframes[0].timestamp:
            first = keyframes[0]
            return float(first.zoom_factor), first.target
        if timestamp >= keyframes[-1].timestamp:
            last = keyframes[-1]
            return float(last.zoom_factor), last.target

        for left, right in zip(keyframes, keyframes[1:]):
            if left.timestamp <= timestamp <= right.timestamp:
                span = max(right.timestamp - left.timestamp, 1e-6)
                raw_progress = (timestamp - left.timestamp) / span
                progress = easing_value(right.easing, raw_progress)
                zoom = left.zoom_factor + (right.zoom_factor - left.zoom_factor) * progress
                target = right.target if raw_progress >= 0.5 else left.target
                return round(float(zoom), 3), target

        last = keyframes[-1]
        return float(last.zoom_factor), last.target

    def to_dict(self) -> dict[str, Any]:
        return {"keyframes": [keyframe.to_dict() for keyframe in self.keyframes]}

    @property
    def max_zoom(self) -> float:
        if not self.keyframes:
            return 1.0
        return round(max(keyframe.zoom_factor for keyframe in self.keyframes), 3)

    @property
    def targets(self) -> list[str]:
        return sorted({keyframe.target for keyframe in self.keyframes})


class SmoothZoomEngine:
    VOICE_ZOOM_BY_INTENSITY = {
        VoiceIntensity.NORMAL: 1.0,
        VoiceIntensity.LEISE_ERHOEHT: 1.2,
        VoiceIntensity.SCHREIEN: 1.5,
        VoiceIntensity.BRUELLEN: 1.8,
    }
    VOICE_EASING_BY_INTENSITY = {
        VoiceIntensity.NORMAL: "linear",
        VoiceIntensity.LEISE_ERHOEHT: "ease_in_out_cubic",
        VoiceIntensity.SCHREIEN: "ease_in_out_cubic",
        VoiceIntensity.BRUELLEN: "ease_out_quad",
    }
    EXPRESSION_ZOOM = {
        FacialExpression.DIRECT_GAZE: (1.5, "ease_in_out_cubic"),
        FacialExpression.HAND_ON_MOUTH: (2.0, "ease_in_out_cubic"),
        FacialExpression.EYEBROW_RAISED: (1.3, "ease_in_out_cubic"),
        FacialExpression.SURPRISE: (2.5, "ease_out_quad"),
        FacialExpression.FRUSTRATION: (2.0, "ease_in_out_cubic"),
        FacialExpression.MOUTH_OPEN_YELL: (1.8, "ease_out_quad"),
    }
    FRIEND_REACTION_KEYWORDS = {
        "hahaha",
        "haha",
        "lol",
        "boah",
        "krass",
        "alter",
        "ne",
        "was",
        "oh",
        "wtf",
        "omg",
        "geil",
        "nice",
    }

    def build_curve_from_triggers(
        self,
        voice_intensity: list[VoiceIntensityPoint],
        facial_expressions: list[FacialExpressionPoint],
        speaker_segments: list[TranscriptSegment],
        gameplay_points: list[GameplayDetectionPoint],
        clip_duration: float,
    ) -> ZoomCurve:
        duration = max(float(clip_duration or 0.0), self._infer_duration(
            voice_intensity,
            facial_expressions,
            speaker_segments,
            gameplay_points,
        ))
        if duration <= 0.0:
            return ZoomCurve([ZoomKeyframe(0.0, 1.0, TARGET_BALANCED, "linear")])

        sample_times = self._sample_times(duration, voice_intensity, facial_expressions, speaker_segments)
        keyframes = [ZoomKeyframe(0.0, 1.0, TARGET_BALANCED, "linear")]

        for timestamp in sample_times:
            target, zoom, easing = self._desired_state_at(
                timestamp=timestamp,
                voice_intensity=voice_intensity,
                facial_expressions=facial_expressions,
                speaker_segments=speaker_segments,
                gameplay_points=gameplay_points,
            )
            previous = keyframes[-1]
            if (
                abs(previous.zoom_factor - zoom) >= 0.03
                or previous.target != target
                or previous.easing != easing
            ):
                keyframes.append(
                    ZoomKeyframe(
                        timestamp=round(timestamp, 3),
                        zoom_factor=round(zoom, 3),
                        target=target,
                        easing=easing,
                    )
                )

        if keyframes[-1].timestamp < duration:
            keyframes.append(
                ZoomKeyframe(
                    timestamp=round(duration, 3),
                    zoom_factor=1.0,
                    target=TARGET_BALANCED,
                    easing="ease_in_out_cubic",
                )
            )

        return ZoomCurve(self.enforce_no_hard_jumps(ZoomCurve(keyframes)).keyframes)

    def enforce_no_hard_jumps(
        self,
        curve: ZoomCurve,
        *,
        max_zoom_delta: float = 0.5,
        min_seconds: float = 0.5,
    ) -> ZoomCurve:
        if len(curve.keyframes) < 2:
            return curve

        adjusted: list[ZoomKeyframe] = [curve.keyframes[0]]
        for keyframe in curve.keyframes[1:]:
            previous = adjusted[-1]
            delta = abs(keyframe.zoom_factor - previous.zoom_factor)
            gap = keyframe.timestamp - previous.timestamp
            timestamp = keyframe.timestamp
            if delta > max_zoom_delta and gap < min_seconds:
                timestamp = previous.timestamp + min_seconds
            if timestamp < previous.timestamp:
                timestamp = previous.timestamp
            adjusted.append(
                ZoomKeyframe(
                    timestamp=round(timestamp, 3),
                    zoom_factor=keyframe.zoom_factor,
                    target=keyframe.target,
                    easing=keyframe.easing,
                )
            )

        return ZoomCurve(adjusted)

    def find_hard_jumps(
        self,
        curve: ZoomCurve,
        *,
        max_zoom_delta: float = 0.5,
        min_seconds: float = 0.5,
    ) -> list[dict[str, float]]:
        jumps: list[dict[str, float]] = []
        for left, right in zip(curve.keyframes, curve.keyframes[1:]):
            delta = abs(right.zoom_factor - left.zoom_factor)
            gap = right.timestamp - left.timestamp
            if delta > max_zoom_delta and gap < min_seconds:
                jumps.append(
                    {
                        "from": left.timestamp,
                        "to": right.timestamp,
                        "seconds": round(gap, 3),
                        "zoom_delta": round(delta, 3),
                    }
                )
        return jumps

    def summarize(self, curve: ZoomCurve) -> dict[str, Any]:
        return {
            "keyframe_count": len(curve.keyframes),
            "max_zoom": curve.max_zoom,
            "targets": curve.targets,
            "hard_jump_count": len(self.find_hard_jumps(curve)),
        }

    def to_ffmpeg_filter(self, curve: ZoomCurve, fps: int = 60) -> str:
        if not curve.keyframes:
            return "null"

        zoom_expr = self._zoom_expression(curve)
        return (
            "crop="
            f"w='iw/({zoom_expr})':"
            f"h='ih/({zoom_expr})':"
            f"x='(iw-iw/({zoom_expr}))/2':"
            f"y='(ih-ih/({zoom_expr}))/2',"
            f"scale=iw:ih,fps={int(fps)}"
        )

    def _desired_state_at(
        self,
        *,
        timestamp: float,
        voice_intensity: list[VoiceIntensityPoint],
        facial_expressions: list[FacialExpressionPoint],
        speaker_segments: list[TranscriptSegment],
        gameplay_points: list[GameplayDetectionPoint],
    ) -> tuple[str, float, str]:
        friend_reaction = self._friend_reaction_at(timestamp, speaker_segments)
        gameplay = self._nearest_gameplay(timestamp, gameplay_points)
        if friend_reaction and (gameplay is None or gameplay.score >= 0.35):
            return TARGET_GAMEPLAY, 1.3, "ease_in_out_cubic"

        voice = self._nearest_voice(timestamp, voice_intensity)
        voice_zoom = 1.0
        easing = "linear"
        if voice is not None and voice.speaker == "ali":
            voice_zoom = self.VOICE_ZOOM_BY_INTENSITY.get(voice.intensity, 1.0)
            easing = self.VOICE_EASING_BY_INTENSITY.get(voice.intensity, "linear")

        expression_zoom, expression_easing = self._expression_zoom_at(
            timestamp,
            facial_expressions,
        )
        if expression_zoom > voice_zoom:
            return TARGET_FACECAM, expression_zoom, expression_easing

        if voice_zoom > 1.0:
            return TARGET_FACECAM, voice_zoom, easing

        if gameplay is not None and not gameplay.is_gameplay:
            return TARGET_GAMEPLAY, 1.0, "linear"

        return TARGET_BALANCED, 1.0, "linear"

    def _expression_zoom_at(
        self,
        timestamp: float,
        points: list[FacialExpressionPoint],
    ) -> tuple[float, str]:
        point = _nearest_by_timestamp(timestamp, points, max_distance=0.75)
        if point is None:
            return 1.0, "linear"

        best_zoom = 1.0
        best_easing = "linear"
        for expression in point.expressions:
            if expression == FacialExpression.NEUTRAL:
                continue
            zoom, easing = self.EXPRESSION_ZOOM.get(expression, (1.0, "linear"))
            confidence = point.confidence_by_expression.get(expression, 1.0)
            scaled_zoom = 1.0 + ((zoom - 1.0) * max(0.35, min(1.0, confidence)))
            if scaled_zoom > best_zoom:
                best_zoom = scaled_zoom
                best_easing = easing
        return round(best_zoom, 3), best_easing

    def _nearest_voice(
        self,
        timestamp: float,
        points: list[VoiceIntensityPoint],
    ) -> VoiceIntensityPoint | None:
        return _nearest_by_timestamp(timestamp, points, max_distance=0.75)

    def _nearest_gameplay(
        self,
        timestamp: float,
        points: list[GameplayDetectionPoint],
    ) -> GameplayDetectionPoint | None:
        return _nearest_by_timestamp(timestamp, points, max_distance=0.75)

    def _friend_reaction_at(
        self,
        timestamp: float,
        speaker_segments: list[TranscriptSegment],
    ) -> bool:
        for segment in speaker_segments:
            if segment.speaker != "friend":
                continue
            if segment.start_seconds <= timestamp <= segment.end_seconds:
                text = (segment.text or "").lower()
                return any(keyword in text for keyword in self.FRIEND_REACTION_KEYWORDS)
        return False

    def _sample_times(
        self,
        duration: float,
        voice_intensity: list[VoiceIntensityPoint],
        facial_expressions: list[FacialExpressionPoint],
        speaker_segments: list[TranscriptSegment],
    ) -> list[float]:
        times = {0.0, round(duration, 3)}
        times.update(float(second) for second in range(0, int(math.ceil(duration)) + 1))
        times.update(float(point.timestamp) for point in voice_intensity)
        times.update(float(point.timestamp) for point in facial_expressions)
        for segment in speaker_segments:
            times.add(float(segment.start_seconds))
            times.add(float(segment.end_seconds))
        return sorted(round(time, 3) for time in times if 0.0 <= time <= duration)

    def _infer_duration(
        self,
        voice_intensity: list[VoiceIntensityPoint],
        facial_expressions: list[FacialExpressionPoint],
        speaker_segments: list[TranscriptSegment],
        gameplay_points: list[GameplayDetectionPoint],
    ) -> float:
        candidates = [0.0]
        candidates.extend(float(point.timestamp) + 1.0 for point in voice_intensity)
        candidates.extend(float(point.timestamp) + 1.0 for point in facial_expressions)
        candidates.extend(float(segment.end_seconds) for segment in speaker_segments)
        candidates.extend(float(point.timestamp) + 1.0 for point in gameplay_points)
        return max(candidates)

    def _zoom_expression(self, curve: ZoomCurve) -> str:
        keyframes = curve.keyframes
        expression = f"{keyframes[-1].zoom_factor:.3f}"
        for left, right in reversed(list(zip(keyframes, keyframes[1:]))):
            if right.timestamp <= left.timestamp:
                continue
            progress = f"((t-{left.timestamp:.3f})/{(right.timestamp - left.timestamp):.3f})"
            eased = self._ffmpeg_easing_expression(right.easing, progress)
            segment_expr = (
                f"({left.zoom_factor:.3f}+"
                f"({right.zoom_factor:.3f}-{left.zoom_factor:.3f})*"
                f"{eased})"
            )
            expression = (
                f"if(between(t,{left.timestamp:.3f},{right.timestamp:.3f}),"
                f"{segment_expr},{expression})"
            )
        return expression

    def _ffmpeg_easing_expression(self, easing: str, progress_expr: str) -> str:
        p = f"min(max({progress_expr},0),1)"
        if easing in {"ease_out", "ease_out_quad"}:
            return f"(1-(1-{p})*(1-{p}))"
        if easing in {"ease_in_out", "ease_in_out_cubic"}:
            return (
                f"if(lt({p},0.5),"
                f"4*{p}*{p}*{p},"
                f"1-pow(-2*{p}+2,3)/2)"
            )
        return p


def _dedupe_keyframes(keyframes: Iterable[ZoomKeyframe]) -> list[ZoomKeyframe]:
    by_timestamp: dict[float, ZoomKeyframe] = {}
    for keyframe in keyframes:
        timestamp = round(float(keyframe.timestamp), 3)
        by_timestamp[timestamp] = ZoomKeyframe(
            timestamp=timestamp,
            zoom_factor=round(max(1.0, float(keyframe.zoom_factor)), 3),
            target=keyframe.target or TARGET_BALANCED,
            easing=keyframe.easing or "linear",
        )
    return [by_timestamp[timestamp] for timestamp in sorted(by_timestamp)]


def _nearest_by_timestamp(
    timestamp: float,
    points: list[Any],
    *,
    max_distance: float,
) -> Any | None:
    if not points:
        return None
    nearest = min(points, key=lambda point: abs(float(point.timestamp) - timestamp))
    if abs(float(nearest.timestamp) - timestamp) <= max_distance:
        return nearest
    return None
