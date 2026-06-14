from __future__ import annotations

from pathlib import Path
from typing import Any

from models.music_apply_timeline import MusicApplyTimeline


class MusicApplyProcessor:
    def apply(
        self,
        rendered_video_path: str | Path,
        music_application_plan: Any,
        channel_type: str,
        music_apply_timeline: MusicApplyTimeline | None,
    ) -> dict[str, Any]:
        output_video_path = str(rendered_video_path)

        if music_apply_timeline is None or not music_apply_timeline.segments:
            return {
                "music_applied": False,
                "output_video_path": output_video_path,
            }

        return {
            "music_applied": False,
            "output_video_path": output_video_path,
            "music_apply_timeline_id": music_apply_timeline.timeline_id,
            "music_apply_segment_count": len(music_apply_timeline.segments),
            "music_apply_skeleton_pass_through": True,
        }
