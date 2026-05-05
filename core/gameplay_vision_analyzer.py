from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable

from models.gameplay_vision_result import GameplayVisionResult, GameplayVisionWindow


DEFAULT_WIDTH = 64
DEFAULT_HEIGHT = 36
DEFAULT_SAMPLE_EVERY_SECONDS = 0.5
DEFAULT_ACTION_THRESHOLD = 0.12
DEFAULT_SCENE_CHANGE_THRESHOLD = 0.18
HIGH_MOTION_DIFF_THRESHOLD = 0.08


class GameplayVisionAnalyzer:
    engine = "gameplay-vision-analyzer-v1"

    def __init__(
        self,
        action_threshold: float | None = None,
        scene_change_threshold: float | None = None,
        width: int | None = None,
        height: int | None = None,
        sample_every_seconds: float | None = None,
    ) -> None:
        self.action_threshold = self._float_from_env(
            "ZENITH_VISION_ACTION_THRESHOLD",
            DEFAULT_ACTION_THRESHOLD if action_threshold is None else action_threshold,
        )
        self.scene_change_threshold = self._float_from_env(
            "ZENITH_VISION_SCENE_CHANGE_THRESHOLD",
            DEFAULT_SCENE_CHANGE_THRESHOLD if scene_change_threshold is None else scene_change_threshold,
        )
        self.width = self._int_from_env("ZENITH_VISION_WIDTH", DEFAULT_WIDTH if width is None else width)
        self.height = self._int_from_env("ZENITH_VISION_HEIGHT", DEFAULT_HEIGHT if height is None else height)
        self.sample_every_seconds = self._float_from_env(
            "ZENITH_VISION_SAMPLE_SECONDS",
            DEFAULT_SAMPLE_EVERY_SECONDS if sample_every_seconds is None else sample_every_seconds,
        )

    def analyze_frames(
        self,
        frames: Iterable[Any] | None,
        fps: float = 2.0,
    ) -> GameplayVisionResult:
        frame_list = list(frames or [])
        if len(frame_list) < 2:
            return GameplayVisionResult(
                engine=self.engine,
                skipped_reason="not enough frames",
            )

        safe_fps = max(0.001, float(fps or 2.0))
        windows: list[GameplayVisionWindow] = []

        previous_signature = self._frame_signature(frame_list[0])

        for index, frame in enumerate(frame_list[1:], start=1):
            current_signature = self._frame_signature(frame)
            motion_score, high_motion_ratio, scene_change_score = self._motion_features(
                previous_signature,
                current_signature,
            )

            action_score = self._clamp(
                (motion_score * 0.55)
                + (high_motion_ratio * 0.30)
                + (scene_change_score * 0.15)
            )

            start_seconds = round((index - 1) / safe_fps, 3)
            end_seconds = round(index / safe_fps, 3)

            if scene_change_score >= self.scene_change_threshold:
                label = "scene_change"
                reason = "large visual difference between sampled frames"
            elif action_score >= self.action_threshold:
                label = "action_candidate"
                reason = "high motion/action level between sampled frames"
            else:
                label = "calm"
                reason = "low visual change between sampled frames"

            windows.append(
                GameplayVisionWindow(
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                    motion_score=motion_score,
                    action_score=action_score,
                    scene_change_score=scene_change_score,
                    label=label,
                    reason=reason,
                )
            )

            previous_signature = current_signature

        action_windows = [
            window
            for window in windows
            if window.action_score >= self.action_threshold
            or window.scene_change_score >= self.scene_change_threshold
        ]

        if windows:
            average_action_score = round(
                sum(window.action_score for window in windows) / len(windows),
                3,
            )
            max_action_score = max(window.action_score for window in windows)
        else:
            average_action_score = 0.0
            max_action_score = 0.0

        return GameplayVisionResult(
            windows=windows,
            action_windows=action_windows,
            average_action_score=average_action_score,
            max_action_score=max_action_score,
            engine=self.engine,
            skipped_reason=None,
        )

    def analyze_video(
        self,
        video_path: str | Path | None,
        sample_every_seconds: float | None = None,
        max_frames: int = 160,
    ) -> GameplayVisionResult:
        if not video_path:
            return GameplayVisionResult(
                engine=self.engine,
                skipped_reason="no video_path",
            )

        path = Path(video_path)
        if not path.exists():
            return GameplayVisionResult(
                engine=self.engine,
                skipped_reason=f"video file not found: {path}",
            )

        try:
            import cv2  # type: ignore
        except Exception as exc:
            return GameplayVisionResult(
                engine=self.engine,
                skipped_reason=f"opencv unavailable: {exc}",
            )

        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            return GameplayVisionResult(
                engine=self.engine,
                skipped_reason=f"could not open video: {path}",
            )

        frames: list[Any] = []
        effective_sample_seconds = max(
            0.1,
            float(self.sample_every_seconds if sample_every_seconds is None else sample_every_seconds),
        )

        try:
            fps = float(capture.get(cv2.CAP_PROP_FPS) or 25.0)
            sample_step = max(1, int(round(fps * effective_sample_seconds)))
            frame_index = 0

            while len(frames) < max(1, int(max_frames)):
                ok, frame = capture.read()
                if not ok:
                    break

                if frame_index % sample_step == 0:
                    resized = cv2.resize(frame, (self.width, self.height))
                    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
                    frames.append(gray)

                frame_index += 1
        finally:
            capture.release()

        result = self.analyze_frames(
            frames=frames,
            fps=1.0 / effective_sample_seconds,
        )
        print(
            "[GAMEPLAY-VISION] "
            f"threshold={self.action_threshold:.3f} "
            f"scene_threshold={self.scene_change_threshold:.3f} "
            f"sample_seconds={effective_sample_seconds:.3f} "
            f"resolution={self.width}x{self.height} "
            f"windows={len(result.windows)} "
            f"action_windows={len(result.action_windows)} "
            f"avg={result.average_action_score} "
            f"max={result.max_action_score}"
        )
        return result

    def _frame_signature(self, frame: Any) -> list[float]:
        values = self._flatten_numeric_values(frame)

        if not values:
            return [0.0]

        max_value = max(max(values), 1.0)
        if max_value > 1.0:
            return [round(max(0.0, min(1.0, value / 255.0)), 4) for value in values]

        return [round(max(0.0, min(1.0, value)), 4) for value in values]

    def _flatten_numeric_values(self, item: Any) -> list[float]:
        if item is None:
            return []

        if isinstance(item, (int, float)):
            return [float(item)]

        if isinstance(item, bytes):
            return [float(value) for value in item]

        if hasattr(item, "flatten"):
            try:
                return [float(value) for value in item.flatten().tolist()]
            except Exception:
                pass

        if isinstance(item, dict):
            values: list[float] = []
            for value in item.values():
                values.extend(self._flatten_numeric_values(value))
            return values

        if isinstance(item, Iterable) and not isinstance(item, (str, bytes)):
            values: list[float] = []
            for value in item:
                values.extend(self._flatten_numeric_values(value))
            return values

        return []

    def _signature_difference(
        self,
        previous_signature: list[float],
        current_signature: list[float],
    ) -> float:
        length = min(len(previous_signature), len(current_signature))
        if length <= 0:
            return 0.0

        difference = sum(
            abs(previous_signature[index] - current_signature[index])
            for index in range(length)
        ) / length

        return round(max(0.0, min(1.0, difference)), 3)

    def _motion_features(
        self,
        previous_signature: list[float],
        current_signature: list[float],
    ) -> tuple[float, float, float]:
        length = min(len(previous_signature), len(current_signature))
        if length <= 0:
            return 0.0, 0.0, 0.0

        diffs = [
            abs(previous_signature[index] - current_signature[index])
            for index in range(length)
        ]
        motion_score = self._clamp(sum(diffs) / length)
        high_motion_count = sum(diff >= HIGH_MOTION_DIFF_THRESHOLD for diff in diffs)
        high_motion_ratio = self._clamp(high_motion_count / length)
        strong_motion_average = (
            sum(diff for diff in diffs if diff >= HIGH_MOTION_DIFF_THRESHOLD)
            / max(1, high_motion_count)
        )
        scene_change_score = self._clamp((motion_score * 0.60) + (strong_motion_average * 0.40))
        return motion_score, high_motion_ratio, scene_change_score

    def _clamp(self, value: float) -> float:
        return round(max(0.0, min(1.0, float(value))), 3)

    def _float_from_env(self, name: str, fallback: float) -> float:
        try:
            return float(os.environ.get(name, fallback))
        except (TypeError, ValueError):
            return float(fallback)

    def _int_from_env(self, name: str, fallback: int) -> int:
        try:
            return max(1, int(os.environ.get(name, fallback)))
        except (TypeError, ValueError):
            return max(1, int(fallback))
