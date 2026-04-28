import os

from core.vertical_reframe_engine import VerticalReframeEngine


class ShortsGenerator:
    def _parse_segment(self, segment, fallback_duration: float = 45.0) -> dict:
        if isinstance(segment, dict):
            start = float(segment.get("start_seconds", 0.0))

            if segment.get("duration_seconds") is not None:
                duration = max(1.0, float(segment.get("duration_seconds")))
                end = start + duration
            else:
                end = float(segment.get("end_seconds", start + fallback_duration))
                duration = max(1.0, end - start)

            label = str(segment.get("label") or f"{round(start, 1)}s - {round(end, 1)}s")

            return {
                "label": label,
                "start_seconds": round(start, 1),
                "end_seconds": round(end, 1),
                "duration_seconds": round(duration, 1),
                "score": float(segment.get("score", 0.0)),
                "selection_reason": str(segment.get("selection_reason", "unknown")),
            }

        start_text, end_text = [part.strip() for part in str(segment).split("-")]

        start = float(start_text.replace("s", "").strip())

        if end_text == "end":
            end = start + fallback_duration
        else:
            end = float(end_text.replace("s", "").strip())

        duration = max(1.0, end - start)

        return {
            "label": f"{round(start, 1)}s - {round(end, 1)}s",
            "start_seconds": round(start, 1),
            "end_seconds": round(end, 1),
            "duration_seconds": round(duration, 1),
            "score": 0.0,
            "selection_reason": "legacy_string_segment",
        }

    def generate(self, package, shorts_decision, platform_targets=None):
        channel_type = package.channel_type.value

        shorts_dir = os.path.join(
            "exports",
            channel_type,
            package.job_id,
            "shorts",
        )
        os.makedirs(shorts_dir, exist_ok=True)

        created_shorts = []
        source_video_path = getattr(package, "source_video_path", package.video_path)

        resolved_platform_targets = (
            list(platform_targets)
            if platform_targets
            else [package.platform.value]
        )

        sorted_segments = sorted(
            shorts_decision.selected_segments[:shorts_decision.shorts_count],
            key=lambda segment: float(segment.get("start_seconds", 0.0))
        )

        for i, segment in enumerate(sorted_segments):
            short_path = os.path.join(shorts_dir, f"short_{i + 1}.mp4")

            segment_data = self._parse_segment(segment)
            start = segment_data["start_seconds"]
            duration = segment_data["duration_seconds"]

            focus_kind = str(segment_data.get("focus_kind", "auto"))

            VerticalReframeEngine().reframe(
                source_path=source_video_path,
                start_time=start,
                duration=duration,
                output_path=short_path,
                focus_kind=focus_kind,
            )

            created_shorts.append(
                {
                    "short_id": f"short_{i + 1}",
                    "path": short_path,
                    "status": "generated",
                    "review_status": "pending",
                    "platform_targets": resolved_platform_targets,
                    "publish_status": "not_published",
                    "segment": segment_data,
                }
            )

        print(f"[ShortsGenerator] Created {len(created_shorts)} shorts in {shorts_dir}")
        return created_shorts