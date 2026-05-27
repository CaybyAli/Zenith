from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

import numpy as np


@dataclass(frozen=True)
class GameplayDetectionPoint:
    timestamp: float
    is_gameplay: bool
    score: float
    signals: dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "is_gameplay": self.is_gameplay,
            "score": self.score,
            "signals": dict(self.signals),
        }


class GameplayMenuDetector:
    def __init__(self, game_profile: Optional[str] = None) -> None:
        self.game_profile = game_profile

    def detect(
        self,
        video_path: str,
        sample_rate_fps: float = 1.0,
        max_samples: int | None = None,
    ) -> list[GameplayDetectionPoint]:
        try:
            import cv2
        except Exception as exc:  # pragma: no cover - local dependency
            raise RuntimeError(f"opencv unavailable: {exc}") from exc

        source = Path(video_path)
        if not source.exists():
            raise FileNotFoundError(f"Gameplay detection source not found: {video_path}")

        capture = cv2.VideoCapture(str(source))
        if not capture.isOpened():
            raise RuntimeError(f"could not open video: {video_path}")

        frames: list[Any] = []
        timestamps: list[float] = []
        try:
            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
            if fps <= 0.0:
                fps = 30.0
            sample_every_frames = max(1, int(round(fps / max(0.1, sample_rate_fps))))
            frame_index = 0
            while True:
                if frame_index % sample_every_frames != 0:
                    ok = capture.grab()
                    if not ok:
                        break
                    frame_index += 1
                    continue

                ok, frame = capture.read()
                if not ok:
                    break

                frames.append(cv2.resize(frame, (160, 90)))
                timestamps.append(frame_index / fps)
                frame_index += 1

                if max_samples is not None and len(frames) >= max_samples:
                    break
        finally:
            capture.release()

        return self.detect_frames(frames, timestamps=timestamps)

    def detect_frames(
        self,
        frames: list[Any],
        timestamps: list[float] | None = None,
    ) -> list[GameplayDetectionPoint]:
        if not frames:
            return []

        prepared = [self._prepare_frame(frame) for frame in frames]
        motion_values = self._motion_values(prepared)
        color_values = [self._color_variance(frame) for frame in frames]
        edge_values = [self._edge_density(gray) for gray in prepared]

        motion_scores = _normalize(motion_values)
        color_scores = _normalize(color_values)
        edge_scores = _normalize(edge_values)

        points: list[GameplayDetectionPoint] = []
        for index, _frame in enumerate(frames):
            timestamp = (
                float(timestamps[index])
                if timestamps is not None and index < len(timestamps)
                else float(index)
            )
            motion = motion_scores[index]
            color = color_scores[index]
            edge = edge_scores[index]
            game_specific = self._game_specific_score(
                color_variance=color_values[index],
                edge_density=edge_values[index],
            )
            raw_score = (
                (motion * 0.55)
                + (edge * 0.30)
                + (color * 0.15)
                + (game_specific * 0.10)
            )
            score = max(0.0, min(1.0, raw_score ** 0.5))
            points.append(
                GameplayDetectionPoint(
                    timestamp=round(timestamp, 3),
                    is_gameplay=score > 0.5,
                    score=round(score, 3),
                    signals={
                        "motion": round(motion, 3),
                        "audio_activity": 0.0,
                        "color_variance": round(color, 3),
                        "edge_density": round(edge, 3),
                        "game_specific": round(game_specific, 3),
                    },
                )
            )

        return points

    def distribution(self, points: list[GameplayDetectionPoint]) -> dict[str, float]:
        if not points:
            return {"gameplay": 0.0, "menu": 0.0}
        gameplay_count = sum(1 for point in points if point.is_gameplay)
        total = float(len(points))
        return {
            "gameplay": round((gameplay_count / total) * 100.0, 3),
            "menu": round(((len(points) - gameplay_count) / total) * 100.0, 3),
        }

    def _prepare_frame(self, frame: Any) -> np.ndarray:
        try:
            import cv2
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"opencv unavailable: {exc}") from exc

        resized = cv2.resize(frame, (160, 90))
        return cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

    def _motion_values(self, gray_frames: list[np.ndarray]) -> list[float]:
        values = [0.0]
        for previous, current in zip(gray_frames, gray_frames[1:]):
            diff = np.abs(current.astype(np.float32) - previous.astype(np.float32))
            values.append(float(np.mean(diff)) / 255.0)
        return values

    def _color_variance(self, frame: Any) -> float:
        resized = np.asarray(frame, dtype=np.float32)
        if resized.size == 0:
            return 0.0
        return float(np.mean(np.std(resized.reshape(-1, 3), axis=0))) / 128.0

    def _edge_density(self, gray_frame: np.ndarray) -> float:
        try:
            import cv2
        except Exception as exc:  # pragma: no cover
            raise RuntimeError(f"opencv unavailable: {exc}") from exc

        edges = cv2.Canny(gray_frame, 80, 160)
        return float(np.count_nonzero(edges)) / float(edges.size or 1)

    def _game_specific_score(self, *, color_variance: float, edge_density: float) -> float:
        if self.game_profile != "rocket_league":
            return 0.0
        return max(0.0, min(1.0, (color_variance * 0.7) + (edge_density * 2.0)))


def _normalize(values: list[float]) -> list[float]:
    if not values:
        return []

    minimum = min(values)
    maximum = max(values)
    span = maximum - minimum
    if span <= 1e-9:
        if maximum > 0.0:
            return [1.0 for _ in values]
        return [0.0 for _ in values]

    return [max(0.0, min(1.0, (value - minimum) / span)) for value in values]
