from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass(frozen=True)
class FaceLandmarks:
    landmarks: list[tuple[float, float]]
    bounding_box: tuple[int, int, int, int]
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "landmarks": [list(point) for point in self.landmarks],
            "bounding_box": list(self.bounding_box),
            "confidence": self.confidence,
        }


@dataclass(frozen=True)
class FaceDetectionPoint:
    timestamp: float
    detected: bool
    landmarks: Optional[FaceLandmarks] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "detected": self.detected,
            "landmarks": self.landmarks.to_dict() if self.landmarks else None,
        }


class MediaPipeFaceDetector:
    def __init__(
        self,
        min_detection_confidence: float = 0.5,
        max_num_faces: int = 1,
        facecam_region: str = "auto",
        model_asset_path: str | Path = "assets/models/mediapipe/face_landmarker.task",
    ) -> None:
        self.min_detection_confidence = float(min_detection_confidence)
        self.max_num_faces = int(max_num_faces)
        self.facecam_region = str(facecam_region or "right_half")
        self.model_asset_path = Path(model_asset_path)

        os.environ.setdefault("MEDIAPIPE_DISABLE_TELEMETRY", "1")
        os.environ.setdefault("GLOG_minloglevel", "2")

        try:
            import mediapipe as mp
        except Exception as exc:  # pragma: no cover - depends on local package
            raise RuntimeError(f"mediapipe unavailable: {exc}") from exc

        self._mp = mp
        self._api_mode = "tasks"
        self.face_mesh = None

        if hasattr(mp, "solutions") and hasattr(mp.solutions, "face_mesh"):
            self._api_mode = "solutions"
            self.face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=self.max_num_faces,
                refine_landmarks=True,
                min_detection_confidence=self.min_detection_confidence,
                min_tracking_confidence=0.5,
            )
        else:
            if not self.model_asset_path.exists():
                raise FileNotFoundError(
                    f"MediaPipe face landmarker model missing: {self.model_asset_path}"
                )
            self.face_mesh = mp.tasks.vision.FaceLandmarker.create_from_options(
                mp.tasks.vision.FaceLandmarkerOptions(
                    base_options=mp.tasks.BaseOptions(
                        model_asset_path=str(self.model_asset_path)
                    ),
                    running_mode=mp.tasks.vision.RunningMode.IMAGE,
                    num_faces=self.max_num_faces,
                    min_face_detection_confidence=self.min_detection_confidence,
                    min_face_presence_confidence=0.5,
                    min_tracking_confidence=0.5,
                )
            )

    def close(self) -> None:
        close = getattr(self.face_mesh, "close", None)
        if callable(close):
            close()

    def detect_in_frame(
        self,
        frame_bgr: Any,
        timestamp: float = 0.0,
    ) -> FaceDetectionPoint:
        try:
            import cv2
        except Exception as exc:  # pragma: no cover - local dependency
            raise RuntimeError(f"opencv unavailable: {exc}") from exc

        if frame_bgr is None or not hasattr(frame_bgr, "shape"):
            return FaceDetectionPoint(timestamp=float(timestamp), detected=False)

        height, width = frame_bgr.shape[:2]
        if height <= 0 or width <= 0:
            return FaceDetectionPoint(timestamp=float(timestamp), detected=False)

        for roi_x, roi_y, roi_w, roi_h in self._candidate_rois(width, height):
            roi = frame_bgr[roi_y : roi_y + roi_h, roi_x : roi_x + roi_w]
            if roi.size == 0:
                continue

            rgb = cv2.cvtColor(roi, cv2.COLOR_BGR2RGB)
            result = self._detect_landmarks(rgb, timestamp=timestamp)
            multi_face_landmarks = (
                getattr(result, "multi_face_landmarks", None)
                or getattr(result, "face_landmarks", None)
                or []
            )
            if not multi_face_landmarks:
                continue

            primary = multi_face_landmarks[0]
            raw_landmarks = list(getattr(primary, "landmark", primary) or [])
            if not raw_landmarks:
                continue

            points: list[tuple[float, float]] = []
            for landmark in raw_landmarks:
                x = (roi_x + (float(landmark.x) * roi_w)) / width
                y = (roi_y + (float(landmark.y) * roi_h)) / height
                points.append((max(0.0, min(1.0, x)), max(0.0, min(1.0, y))))

            xs = [point[0] for point in points]
            ys = [point[1] for point in points]
            x_min = int(max(0.0, min(xs)) * width)
            y_min = int(max(0.0, min(ys)) * height)
            x_max = int(min(1.0, max(xs)) * width)
            y_max = int(min(1.0, max(ys)) * height)

            box = (
                x_min,
                y_min,
                max(1, x_max - x_min),
                max(1, y_max - y_min),
            )
            confidence = self._landmark_confidence(points)

            return FaceDetectionPoint(
                timestamp=float(timestamp),
                detected=True,
                landmarks=FaceLandmarks(
                    landmarks=points,
                    bounding_box=box,
                    confidence=confidence,
                ),
            )

        return FaceDetectionPoint(timestamp=float(timestamp), detected=False)

    def detect_in_video(
        self,
        video_path: str,
        sample_rate_fps: float = 5.0,
        max_samples: int | None = None,
    ) -> list[FaceDetectionPoint]:
        try:
            import cv2
        except Exception as exc:  # pragma: no cover - local dependency
            raise RuntimeError(f"opencv unavailable: {exc}") from exc

        source = Path(video_path)
        if not source.exists():
            raise FileNotFoundError(f"Face detection source not found: {video_path}")

        capture = cv2.VideoCapture(str(source))
        if not capture.isOpened():
            raise RuntimeError(f"could not open video: {video_path}")

        points: list[FaceDetectionPoint] = []
        try:
            fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
            if fps <= 0.0:
                fps = 30.0
            sample_rate = max(0.1, float(sample_rate_fps))
            sample_every_frames = max(1, int(round(fps / sample_rate)))

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

                timestamp = frame_index / fps
                points.append(self.detect_in_frame(frame, timestamp=timestamp))
                frame_index += 1

                if max_samples is not None and len(points) >= max_samples:
                    break
        finally:
            capture.release()

        return points

    def _facecam_roi(self, width: int, height: int) -> tuple[int, int, int, int]:
        if self.facecam_region == "full":
            return 0, 0, width, height

        if self.facecam_region == "right_third":
            x = int(width * 0.66)
            return x, 0, width - x, height

        if self.facecam_region == "right_half":
            x = int(width * 0.50)
            return x, 0, width - x, height

        if self.facecam_region == "left_third":
            return 0, 0, max(1, int(width * 0.34)), height

        return 0, 0, width, height

    def _candidate_rois(self, width: int, height: int) -> list[tuple[int, int, int, int]]:
        if self.facecam_region == "auto":
            regions = ["right_half", "left_third", "full"]
            return [self._roi_for_region(region, width, height) for region in regions]
        return [self._roi_for_region(self.facecam_region, width, height)]

    def _roi_for_region(
        self,
        region: str,
        width: int,
        height: int,
    ) -> tuple[int, int, int, int]:
        original = self.facecam_region
        try:
            self.facecam_region = region
            return self._facecam_roi(width, height)
        finally:
            self.facecam_region = original

    def _detect_landmarks(self, rgb: Any, timestamp: float) -> Any:
        if self._api_mode == "solutions":
            return self.face_mesh.process(rgb)

        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        return self.face_mesh.detect(image)

    def _landmark_confidence(self, points: list[tuple[float, float]]) -> float:
        if len(points) >= 478:
            return 1.0
        if len(points) >= 468:
            return 0.98
        return max(0.0, min(1.0, len(points) / 468.0))
