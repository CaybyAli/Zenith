from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from models.gameplay_vision_result import GameplayVisionResult, GameplayVisionWindow


class GameplayVisionAnalyzer:
    engine = "gameplay-vision-analyzer-v1"

    def __init__(
        self,
        action_threshold: float = 0.28,
        scene_change_threshold: float = 0.45,
    ) -> None:
        self.action_threshold = float(action_threshold)
        self.scene_change_threshold = float(scene_change_threshold)

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
            motion_score = self._signature_difference(previous_signature, current_signature)

            scene_change_score = (
                motion_score
                if motion_score >= self.scene_change_threshold
                else round(motion_score * 0.45, 3)
            )

            action_score = round((motion_score * 0.75) + (scene_change_score * 0.25), 3)

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
        sample_every_seconds: float = 1.0,
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

        try:
            fps = float(capture.get(cv2.CAP_PROP_FPS) or 25.0)
            sample_step = max(1, int(round(fps * max(0.1, float(sample_every_seconds)))))
            frame_index = 0

            while len(frames) < max(1, int(max_frames)):
                ok, frame = capture.read()
                if not ok:
                    break

                if frame_index % sample_step == 0:
                    resized = cv2.resize(frame, (32, 18))
                    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
                    frames.append(gray)

                frame_index += 1
        finally:
            capture.release()

        return self.analyze_frames(
            frames=frames,
            fps=1.0 / max(0.1, float(sample_every_seconds)),
        )

    def _frame_signature(self, frame: Any) -> list[float]:
        values = self._flatten_numeric_values(frame)

        if not values:
            return [0.0]

        if len(values) > 576:
            step = max(1, len(values) // 576)
            values = values[::step][:576]

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
