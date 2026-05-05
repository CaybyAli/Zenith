from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable

from models.facecam_reaction_result import FacecamReactionResult, FacecamReactionWindow


class FacecamReactionAnalyzer:
    engine = "facecam-reaction-analyzer-v1"

    def __init__(
        self,
        reaction_threshold: float = 0.24,
        strong_reaction_threshold: float = 0.42,
    ) -> None:
        self.reaction_threshold = float(reaction_threshold)
        self.strong_reaction_threshold = float(strong_reaction_threshold)

    def analyze_frames(
        self,
        frames: Iterable[Any] | None,
        fps: float = 2.0,
        audio_peak_times: Iterable[float] | None = None,
    ) -> FacecamReactionResult:
        frame_list = list(frames or [])
        if len(frame_list) < 2:
            return FacecamReactionResult(
                engine=self.engine,
                skipped_reason="not enough facecam frames",
            )

        safe_fps = max(0.001, float(fps or 2.0))
        audio_peaks = [max(0.0, float(value)) for value in (audio_peak_times or [])]
        windows: list[FacecamReactionWindow] = []

        previous_signature = self._frame_signature(frame_list[0])

        for index, frame in enumerate(frame_list[1:], start=1):
            current_signature = self._frame_signature(frame)

            motion_score = self._signature_difference(previous_signature, current_signature)
            expression_change_score = self._expression_change_score(previous_signature, current_signature)

            start_seconds = round((index - 1) / safe_fps, 3)
            end_seconds = round(index / safe_fps, 3)

            audio_boost = 0.0
            if any(start_seconds <= peak <= end_seconds for peak in audio_peaks):
                audio_boost = 0.12

            reaction_score = self._clamp(
                (motion_score * 0.62)
                + (expression_change_score * 0.30)
                + audio_boost
            )

            if reaction_score >= self.strong_reaction_threshold:
                label = "strong_facecam_reaction"
                reason = "strong visual change in facecam window"
            elif reaction_score >= self.reaction_threshold:
                label = "facecam_reaction"
                reason = "noticeable facecam activity"
            else:
                label = "calm_facecam"
                reason = "low facecam activity"

            if audio_boost:
                reason += " with audio peak boost"

            windows.append(
                FacecamReactionWindow(
                    start_seconds=start_seconds,
                    end_seconds=end_seconds,
                    reaction_score=reaction_score,
                    motion_score=motion_score,
                    expression_change_score=expression_change_score,
                    label=label,
                    reason=reason,
                )
            )

            previous_signature = current_signature

        reaction_windows = [
            window
            for window in windows
            if window.reaction_score >= self.reaction_threshold
        ]

        average_reaction_score = (
            round(sum(window.reaction_score for window in windows) / len(windows), 3)
            if windows
            else 0.0
        )
        max_reaction_score = (
            max(window.reaction_score for window in windows)
            if windows
            else 0.0
        )

        return FacecamReactionResult(
            windows=windows,
            reaction_windows=reaction_windows,
            average_reaction_score=average_reaction_score,
            max_reaction_score=max_reaction_score,
            engine=self.engine,
            skipped_reason=None,
        )

    def analyze_video(
        self,
        video_path: str | Path | None,
        sample_every_seconds: float = 1.0,
        max_frames: int = 160,
    ) -> FacecamReactionResult:
        if not video_path:
            return FacecamReactionResult(
                engine=self.engine,
                skipped_reason="no video_path",
            )

        path = Path(video_path)
        if not path.exists():
            return FacecamReactionResult(
                engine=self.engine,
                skipped_reason=f"video file not found: {path}",
            )

        try:
            import cv2  # type: ignore
        except Exception as exc:
            return FacecamReactionResult(
                engine=self.engine,
                skipped_reason=f"opencv unavailable: {exc}",
            )

        capture = cv2.VideoCapture(str(path))
        if not capture.isOpened():
            return FacecamReactionResult(
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
                    height, width = frame.shape[:2]

                    # 32:9 recordings in Zenith usually keep facecam on the left side.
                    # This is a safe first crop for reaction activity, not identity detection.
                    facecam_width = max(1, int(width * 0.28))
                    facecam_frame = frame[:, :facecam_width]

                    resized = cv2.resize(facecam_frame, (32, 32))
                    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
                    frames.append(gray)

                frame_index += 1
        finally:
            capture.release()

        return self.analyze_frames(
            frames=frames,
            fps=1.0 / max(0.1, float(sample_every_seconds)),
        )

    def _clamp(self, value: float) -> float:
        return round(max(0.0, min(1.0, float(value))), 3)

    def _frame_signature(self, frame: Any) -> list[float]:
        values = self._flatten_numeric_values(frame)

        if not values:
            return [0.0]

        if len(values) > 1024:
            step = max(1, len(values) // 1024)
            values = values[::step][:1024]

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

        return self._clamp(difference)

    def _expression_change_score(
        self,
        previous_signature: list[float],
        current_signature: list[float],
    ) -> float:
        length = min(len(previous_signature), len(current_signature))
        if length <= 0:
            return 0.0

        previous_dark = sum(1 for value in previous_signature[:length] if value < 0.33) / length
        previous_mid = sum(1 for value in previous_signature[:length] if 0.33 <= value < 0.66) / length
        previous_bright = sum(1 for value in previous_signature[:length] if value >= 0.66) / length

        current_dark = sum(1 for value in current_signature[:length] if value < 0.33) / length
        current_mid = sum(1 for value in current_signature[:length] if 0.33 <= value < 0.66) / length
        current_bright = sum(1 for value in current_signature[:length] if value >= 0.66) / length

        histogram_shift = (
            abs(previous_dark - current_dark)
            + abs(previous_mid - current_mid)
            + abs(previous_bright - current_bright)
        ) / 2.0

        return self._clamp(histogram_shift)
