from pathlib import Path
import subprocess

from models.job import Job
from models.thumbnail_package import ThumbnailPackage
from shared.errors import ValidationError


class ThumbnailForge:
    def generate(self, job: Job, final_video_path: str) -> ThumbnailPackage:
        video_path = Path(final_video_path)

        if not video_path.exists():
            raise ValidationError(f"Final video not found for thumbnail generation: {video_path}")

        output_dir = video_path.parent
        base_name = video_path.stem

        variants = [
            output_dir / f"{base_name}_thumb1.jpg",
            output_dir / f"{base_name}_thumb2.jpg",
            output_dir / f"{base_name}_thumb3.jpg",
        ]

        scores = [0.6, 0.8, 0.7]

        output_dir.mkdir(parents=True, exist_ok=True)

        ffmpeg_path = r"D:\Tools\ffmpeg\bin\ffmpeg.exe"
        ffprobe_path = r"D:\Tools\ffmpeg\bin\ffprobe.exe"

        probe_command = [
            ffprobe_path,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]

        probe_result = subprocess.run(probe_command, capture_output=True, text=True)

        if probe_result.returncode != 0:
            raise ValidationError(f"Could not read video duration: {probe_result.stderr}")

        try:
            duration = float(probe_result.stdout.strip())
        except ValueError as exc:
            raise ValidationError("Could not parse video duration for thumbnail generation") from exc

        safe_points = [
            max(0.1, duration * 0.2),
            max(0.1, duration * 0.5),
            max(0.1, duration * 0.8),
        ]

        timestamps = [f"{min(point, max(0.1, duration - 0.1)):.2f}" for point in safe_points]

        for variant_path, timestamp in zip(variants, timestamps):
            command = [
                ffmpeg_path,
                "-y",
                "-ss",
                timestamp,
                "-i",
                str(video_path),
                "-frames:v",
                "1",
                str(variant_path),
            ]

            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode != 0:
                raise ValidationError(f"Thumbnail generation failed: {result.stderr}")

        best_index = scores.index(max(scores))

        return ThumbnailPackage(
            job_id=job.job_id,
            selected_thumbnail=str(variants[best_index]),
            thumbnail_variants=[str(path) for path in variants],
            thumbnail_scores=scores,
            selected_index=best_index,
        )