from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.facial_expression_analyzer import FacialExpression, FacialExpressionPoint
from core.gameplay_menu_detector import GameplayDetectionPoint
from core.voice_intensity_analyzer import VoiceIntensity, VoiceIntensityPoint
from models.transcript_result import TranscriptSegment


@dataclass(frozen=True)
class FocusDecision:
    timestamp: float
    focus_target: str
    facecam_zoom: float
    gameplay_zoom: float
    facecam_opacity: float
    reasoning: str
    confidence: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": round(float(self.timestamp), 3),
            "focus_target": self.focus_target,
            "facecam_zoom": round(float(self.facecam_zoom), 3),
            "gameplay_zoom": round(float(self.gameplay_zoom), 3),
            "facecam_opacity": round(float(self.facecam_opacity), 3),
            "reasoning": self.reasoning,
            "confidence": round(float(self.confidence), 3),
        }


class FocusSwitchEngine:
    DEFAULT_STYLE_DNA_PATH = Path("video_configs/gaming_pairs_style_dna.json")
    DEFAULT_NORMAL_GAMEPLAY_CONFIDENCE = 0.55

    def __init__(self, style_dna_path: str | Path | None = None) -> None:
        self.style_dna_path = Path(style_dna_path) if style_dna_path else self.DEFAULT_STYLE_DNA_PATH
        self._style_dna: dict[str, Any] = {}
        self._style_dna_consumption: dict[str, Any] = self._load_style_dna_consumption()

    def _load_style_dna_consumption(self) -> dict[str, Any]:
        report: dict[str, Any] = {
            "loaded": False,
            "path": str(self.style_dna_path),
            "content_type": None,
            "normal_voice_gameplay_confidence_before": self.DEFAULT_NORMAL_GAMEPLAY_CONFIDENCE,
            "normal_voice_gameplay_confidence_after": self.DEFAULT_NORMAL_GAMEPLAY_CONFIDENCE,
            "normal_voice_gameplay_ratio": None,
            "changed_decision": None,
            "reason": "style_dna_missing",
        }

        try:
            if not self.style_dna_path.exists():
                return report

            data = json.loads(self.style_dna_path.read_text(encoding="utf-8"))
            self._style_dna = data if isinstance(data, dict) else {}

            content_type = str(self._style_dna.get("content_type") or "")
            report["content_type"] = content_type
            if content_type != "gaming_pairs":
                report["reason"] = f"unsupported_content_type:{content_type}"
                return report

            normal_counts = (
                self._style_dna
                .get("correlations", {})
                .get("voice_intensity_to_focus", {})
                .get("counts", {})
                .get("normal", {})
            )

            if isinstance(normal_counts, dict) and normal_counts:
                gameplay_count = int(normal_counts.get("gameplay", 0) or 0)
                facecam_count = int(normal_counts.get("facecam", 0) or 0)
            else:
                focus_distribution = self._style_dna.get("focus_decision_distribution", {})
                if not isinstance(focus_distribution, dict):
                    focus_distribution = {}
                gameplay_count = int(focus_distribution.get("gameplay", 0) or 0)
                facecam_count = int(focus_distribution.get("facecam", 0) or 0)

            total = gameplay_count + facecam_count
            ratio = (gameplay_count / total) if total else 0.0

            report["loaded"] = True
            report["normal_voice_gameplay_ratio"] = round(ratio, 3)

            if ratio >= 0.70:
                report["normal_voice_gameplay_confidence_after"] = 0.65
                report["changed_decision"] = (
                    "no_speech_normal_voice_gameplay_focus confidence 0.55->0.65 "
                    f"because style_dna normal voice maps to gameplay ratio={ratio:.3f}"
                )
                report["reason"] = "gaming_pairs_style_dna_normal_voice_gameplay_bias"
            else:
                report["reason"] = "gaming_pairs_style_dna_loaded_without_threshold_change"

            return report
        except Exception as exc:
            report["reason"] = f"style_dna_load_error:{exc}"
            return report

    def style_dna_consumption_report(self) -> dict[str, Any]:
        return dict(self._style_dna_consumption)

    def _normal_voice_gameplay_confidence(self) -> float:
        try:
            return float(
                self._style_dna_consumption.get(
                    "normal_voice_gameplay_confidence_after",
                    self.DEFAULT_NORMAL_GAMEPLAY_CONFIDENCE,
                )
            )
        except (TypeError, ValueError):
            return self.DEFAULT_NORMAL_GAMEPLAY_CONFIDENCE

    FRIEND_REACTION_KEYWORDS = frozenset(
        {
            "boah",
            "krass",
            "alter",
            "diggah",
            "digger",
            "wallah",
            "oida",
            "junge",
            "bro",
            "alta",
            "hahaha",
            "haha",
            "lol",
            "lmao",
            "ahaha",
            "was",
            "wtf",
            "omg",
            "oh",
            "wow",
            "nein",
            "ja",
            "nice",
            "geil",
            "sick",
            "fett",
            "stark",
            "nee",
            "ne",
            "nah",
            "fuck",
            "scheisse",
            "schei\u00dfe",
        }
    )
    STRONG_EXPRESSIONS = {
        FacialExpression.SURPRISE,
        FacialExpression.HAND_ON_MOUTH,
    }

    def decide(
        self,
        voice_intensity: list[VoiceIntensityPoint],
        facial_expressions: list[FacialExpressionPoint],
        speaker_segments: list[TranscriptSegment],
        gameplay_points: list[GameplayDetectionPoint],
        clip_duration: float | None = None,
    ) -> list[FocusDecision]:
        duration = self._duration(
            voice_intensity=voice_intensity,
            facial_expressions=facial_expressions,
            speaker_segments=speaker_segments,
            gameplay_points=gameplay_points,
            clip_duration=clip_duration,
        )
        if duration <= 0.0:
            return []

        decisions: list[FocusDecision] = []
        for second in range(0, int(math.ceil(duration))):
            timestamp = float(second)
            decisions.append(
                self._decide_second(
                    timestamp=timestamp,
                    voice_intensity=voice_intensity,
                    facial_expressions=facial_expressions,
                    speaker_segments=speaker_segments,
                    gameplay_points=gameplay_points,
                )
            )

        return decisions

    def summarize(self, decisions: list[FocusDecision]) -> dict[str, Any]:
        counts = Counter(decision.focus_target for decision in decisions)
        total = float(len(decisions) or 1)
        return {
            "decision_count": len(decisions),
            "focus_counts": dict(sorted(counts.items())),
            "focus_distribution": {
                key: round((value / total) * 100.0, 3)
                for key, value in sorted(counts.items())
            },
            "friend_reaction_count": sum(
                1 for decision in decisions if "friend_keyword" in decision.reasoning
            ),
            "ali_strong_count": sum(
                1 for decision in decisions if "ali_voice_intensity" in decision.reasoning
            ),
            "drop_count": counts.get("drop", 0),
        }

    def write_decision_log(
        self,
        decisions: list[FocusDecision],
        output_path: str | Path,
    ) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "engine": "focus-switch-engine-v1",
            "summary": self.summarize(decisions),
            "style_dna_consumption": self.style_dna_consumption_report(),
            "focus_decisions": [decision.to_dict() for decision in decisions],
        }
        with path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        return path

    def _decide_second(
        self,
        *,
        timestamp: float,
        voice_intensity: list[VoiceIntensityPoint],
        facial_expressions: list[FacialExpressionPoint],
        speaker_segments: list[TranscriptSegment],
        gameplay_points: list[GameplayDetectionPoint],
    ) -> FocusDecision:
        gameplay = _nearest_by_timestamp(timestamp, gameplay_points, max_distance=0.75)
        if gameplay is not None and gameplay.score < 0.3:
            return FocusDecision(
                timestamp=timestamp,
                focus_target="drop",
                facecam_zoom=1.0,
                gameplay_zoom=1.0,
                facecam_opacity=0.0,
                reasoning=f"gameplay_score_below_drop_threshold score={gameplay.score:.3f}",
                confidence=0.95,
            )

        active_segments = _active_segments(timestamp, speaker_segments)
        ali_speaking = any(segment.speaker == "ali" for segment in active_segments)
        friend_segments = [
            segment for segment in active_segments if segment.speaker == "friend"
        ]
        friend_speaking = bool(friend_segments)

        voice = _nearest_by_timestamp(timestamp, voice_intensity, max_distance=0.75)
        if voice is not None and voice.speaker == "ali" and voice.intensity > VoiceIntensity.NORMAL:
            ali_speaking = True

        if (
            ali_speaking
            and voice is not None
            and voice.speaker == "ali"
            and voice.intensity >= VoiceIntensity.SCHREIEN
        ):
            zoom = 1.8 if voice.intensity >= VoiceIntensity.BRUELLEN else 1.5
            return FocusDecision(
                timestamp=timestamp,
                focus_target="facecam",
                facecam_zoom=zoom,
                gameplay_zoom=1.0,
                facecam_opacity=1.0,
                reasoning=f"ali_voice_intensity_{voice.intensity.label}",
                confidence=0.9 if voice.intensity == VoiceIntensity.SCHREIEN else 0.95,
            )

        expression_point = _nearest_by_timestamp(
            timestamp,
            facial_expressions,
            max_distance=0.75,
        )
        expression, expression_confidence = self._strong_expression(expression_point)
        if ali_speaking and expression is not None:
            zoom = 2.5 if expression == FacialExpression.SURPRISE else 2.0
            return FocusDecision(
                timestamp=timestamp,
                focus_target="facecam",
                facecam_zoom=zoom,
                gameplay_zoom=1.0,
                facecam_opacity=1.0,
                reasoning=f"ali_expression_{expression.value}",
                confidence=max(0.7, expression_confidence),
            )

        keyword = self._friend_keyword(friend_segments)
        if friend_speaking and keyword:
            return FocusDecision(
                timestamp=timestamp,
                focus_target="gameplay",
                facecam_zoom=1.0,
                gameplay_zoom=1.3,
                facecam_opacity=0.3,
                reasoning=f"friend_keyword_{keyword}",
                confidence=0.75,
            )

        if friend_speaking:
            return FocusDecision(
                timestamp=timestamp,
                focus_target="balanced",
                facecam_zoom=1.0,
                gameplay_zoom=1.0,
                facecam_opacity=0.7,
                reasoning="friend_speaking_no_keyword",
                confidence=0.65,
            )

        if not active_segments and (
            voice is None or voice.intensity == VoiceIntensity.NORMAL
        ):
            confidence = self._normal_voice_gameplay_confidence()
            style_reason = self._style_dna_consumption.get("reason", "style_dna_not_loaded")
            return FocusDecision(
                timestamp=timestamp,
                focus_target="gameplay",
                facecam_zoom=1.0,
                gameplay_zoom=1.0,
                facecam_opacity=0.7,
                reasoning=(
                    "no_speech_normal_voice_gameplay_focus "
                    f"style_dna_reason={style_reason}"
                ),
                confidence=confidence,
            )

        return FocusDecision(
            timestamp=timestamp,
            focus_target="facecam",
            facecam_zoom=1.0,
            gameplay_zoom=1.0,
            facecam_opacity=1.0,
            reasoning="default_facecam",
            confidence=0.5,
        )

    def _strong_expression(
        self,
        point: FacialExpressionPoint | None,
    ) -> tuple[FacialExpression | None, float]:
        if point is None:
            return None, 0.0
        best_expression: FacialExpression | None = None
        best_confidence = 0.0
        for expression in point.expressions:
            if expression not in self.STRONG_EXPRESSIONS:
                continue
            confidence = float(point.confidence_by_expression.get(expression, 1.0))
            if confidence > best_confidence:
                best_expression = expression
                best_confidence = confidence
        return best_expression, best_confidence

    def _friend_keyword(self, segments: list[TranscriptSegment]) -> str | None:
        for segment in segments:
            text = str(segment.text or "").lower()
            tokens = set(re.findall(r"[\w\u00c0-\u024f]+", text, flags=re.UNICODE))
            for keyword in sorted(self.FRIEND_REACTION_KEYWORDS, key=len, reverse=True):
                if len(keyword) <= 3:
                    if keyword in tokens:
                        return keyword
                elif keyword in text or keyword in tokens:
                    return keyword
        return None

    def _duration(
        self,
        *,
        voice_intensity: list[VoiceIntensityPoint],
        facial_expressions: list[FacialExpressionPoint],
        speaker_segments: list[TranscriptSegment],
        gameplay_points: list[GameplayDetectionPoint],
        clip_duration: float | None,
    ) -> float:
        candidates = [float(clip_duration or 0.0)]
        candidates.extend(float(point.timestamp) + 1.0 for point in voice_intensity)
        candidates.extend(float(point.timestamp) + 1.0 for point in facial_expressions)
        candidates.extend(float(point.timestamp) + 1.0 for point in gameplay_points)
        candidates.extend(float(segment.end_seconds) for segment in speaker_segments)
        return max(candidates)


def focus_decision_log_path(job_id: str, base_dir: str | Path = "data/jobs") -> Path:
    safe_id = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(job_id or "job")).strip("_")
    return Path(base_dir) / f"{safe_id}_focus_decision_log.json"


def _active_segments(
    timestamp: float,
    segments: list[TranscriptSegment],
) -> list[TranscriptSegment]:
    return [
        segment
        for segment in segments
        if float(segment.start_seconds) <= timestamp < float(segment.end_seconds)
    ]


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
